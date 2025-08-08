from __future__ import annotations

import datetime
import time
import sys
import logging
from collections import namedtuple
from enum import Enum
from logging.handlers import RotatingFileHandler
import os
import traceback
import configparser

import requests
import signal
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance

from service.audio_service import AudioService
from service.music_detector import MusicDetector
from service.shazam_service import ShazamService
from service.weather_service import WeatherService

SongInfo = namedtuple('SongInfo', ['title', 'artist', 'album_art', 'offset', 'song_duration'])


class ViewState(Enum):
    CLEAN = 0
    PLAYING = 1
    NOTHING_PLAYING = 2
    UNKNOWN = 5


class ShazampiEinkDisplay:
    def __init__(self, delay=120, recording_duration=10):
        signal.signal(signal.SIGTERM, self._handle_sigterm)
        self.delay = delay
        self.recording_duration = recording_duration

        # Configuration for the matrix
        self.config = configparser.ConfigParser()
        self.config.read(os.path.join(os.path.dirname(__file__), '..', 'config', 'eink_options.ini'))
        # set shazampi lib logger
        logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S',
                            filename=self.config.get('DEFAULT', 'shazampi_log'), level=logging.INFO)
        logger = logging.getLogger('shazampi_logger')
        # automatically deletes logs more than 2000 bytes
        handler = RotatingFileHandler(self.config.get('DEFAULT', 'shazampi_log'), maxBytes=2000, backupCount=3)
        logger.addHandler(handler)

        # setup services
        self.audio_service = AudioService()
        self.music_detector = MusicDetector(self.recording_duration)
        self.shazam_service = ShazamService()

        openweathermap_api_key = self.config.get('DEFAULT', 'openweathermap_api_key')
        geo_coordinates = self.config.get('DEFAULT', 'geo_coordinates')
        units = self.config.get('DEFAULT', 'units')

        # delay
        if self.config.has_option('DEFAULT', 'delay_override'):
            self.delay = int(self.config.get('DEFAULT', 'delay_override'))

        self.weather_service = WeatherService(api_key=openweathermap_api_key,
                                              geo_coordinates=geo_coordinates,
                                              units=units)

        # prep some vars before entering service loop
        self.pic_counter = 0
        self.current_view = ViewState.UNKNOWN
        self.logger = self._init_logger()
        self.logger.info('Service instance created')
        if self.config.get('DEFAULT', 'model') == 'inky':
            from inky.auto import auto
            from inky.inky_uc8159 import CLEAN
            self.inky_auto = auto
            self.inky_clean = CLEAN
            self.logger.info('Loading Pimoroni inky lib')
        if self.config.get('DEFAULT', 'model') == 'inky-phat':
            from inky.auto import auto
            from inky.inky_uc8159 import CLEAN
            self.inky_auto = auto
            self.inky_clean = CLEAN
            self.logger.info('Loading Pimoroni inky lib')
        if self.config.get('DEFAULT', 'model') == 'waveshare4':
            from lib import epd4in01f
            self.wave4 = epd4in01f
            self.logger.info('Loading Waveshare 4" lib')

    def _init_logger(self):
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)
        stdout_handler = logging.StreamHandler()
        stdout_handler.setLevel(logging.DEBUG)
        stdout_handler.setFormatter(logging.Formatter('Shazampi eInk Display - %(message)s'))
        logger.addHandler(stdout_handler)
        return logger

    def _handle_sigterm(self, sig, frame):
        self.logger.warning('SIGTERM received stopping')
        sys.exit(0)

    def _break_fix(self, text: str, width: int, font: ImageFont, draw: ImageDraw):
        """
        Fix line breaks in text.
        """
        if not text:
            return
        if isinstance(text, str):
            text = text.split()  # this creates a list of words
        lo = 0
        hi = len(text)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            t = ' '.join(text[:mid])  # this makes a string again
            w = int(draw.textlength(text=t, font=font))
            if w <= width:
                lo = mid
            else:
                hi = mid - 1
        t = ' '.join(text[:lo])  # this makes a string again
        w = int(draw.textlength(text=t, font=font))
        yield t, w
        # yield from self._break_fix(text[lo:], width, font, draw)

    def _fit_text_top_down(self, img: Image, text: str, text_color: str, shadow_text_color: str, font: ImageFont,
                           y_offset: int, font_size: int, x_start_offset: int = 0, x_end_offset: int = 0,
                           offset_text_px_shadow: int = 0) -> int:
        """
        Fit text into container after applying line breaks. Returns the total
        height taken up by the text
        """
        width = img.width - x_start_offset - x_end_offset - offset_text_px_shadow
        draw = ImageDraw.Draw(img)
        pieces = list(self._break_fix(text, width, font, draw))
        y = y_offset
        h_taken_by_text = 0
        for t, _ in pieces:
            if offset_text_px_shadow > 0:
                draw.text((x_start_offset + offset_text_px_shadow, y + offset_text_px_shadow), t, font=font,
                          fill=shadow_text_color)
            draw.text((x_start_offset, y), t, font=font, fill=text_color)
            new_height = font_size
            y += font_size
            h_taken_by_text += new_height
        return h_taken_by_text

    def _fit_text_bottom_up(self, img: Image, text: str, text_color: str, shadow_text_color: str, font: ImageFont,
                            y_offset: int, font_size: int, x_start_offset: int = 0, x_end_offset: int = 0,
                            offset_text_px_shadow: int = 0) -> int:
        """
        Fit text into container after applying line breaks. Returns the total
        height taken up by the text
        """
        width = img.width - x_start_offset - x_end_offset - offset_text_px_shadow
        draw = ImageDraw.Draw(img)
        pieces = list(self._break_fix(text, width, font, draw))
        y = y_offset
        if len(pieces) > 1:
            y -= (len(pieces) - 1) * font_size
        h_taken_by_text = 0
        for t, _ in pieces:
            if offset_text_px_shadow > 0:
                draw.text((x_start_offset + offset_text_px_shadow, y + offset_text_px_shadow), t, font=font,
                          fill=shadow_text_color)
            draw.text((x_start_offset, y), t, font=font, fill=text_color)
            new_height = font_size
            y += font_size
            h_taken_by_text += new_height
        return h_taken_by_text

    def _display_clean(self):
        """cleans the display
        """
        try:
            if self.config.get('DEFAULT', 'model') == 'inky':
                inky = self.inky_auto()
                for _ in range(2):
                    for y in range(inky.height - 1):
                        for x in range(inky.width - 1):
                            inky.set_pixel(x, y, self.inky_clean)

                    inky.show()
                    time.sleep(1.0)
            if self.config.get('DEFAULT', 'model') == 'inky-phat':
                inky = self.inky_auto()
                for _ in range(2):
                    for y in range(inky.height - 1):
                        for x in range(inky.width - 1):
                            inky.set_pixel(x, y, self.inky_clean)
                    inky.show()
                    time.sleep(1.0)
            if self.config.get('DEFAULT', 'model') == 'waveshare4':
                epd = self.wave4.EPD()
                epd.init()
                epd.Clear()
            self.current_view = ViewState.CLEAN
        except Exception as e:
            self.logger.error(f'Display clean error: {e}')
            self.logger.error(traceback.format_exc())

    def _convert_image_wave(self, img: Image, saturation: int = 2) -> Image:
        # blow out the saturation
        converter = ImageEnhance.Color(img)
        img = converter.enhance(saturation)
        # dither to 7-color palette
        palette_data = [0x00, 0x00, 0x00,
                        0xff, 0xff, 0xff,
                        0x00, 0xff, 0x00,
                        0x00, 0x00, 0xff,
                        0xff, 0x00, 0x00,
                        0xff, 0xff, 0x00,
                        0xff, 0x80, 0x00]
        # Image size doesn't matter since it's just the palette we're using
        palette_image = Image.new('P', (1, 1))
        # Set our 7 color palette (+ clear) and zero out the other 247 colors
        palette_image.putpalette(palette_data + [0, 0, 0] * 248)
        # Force source image and palette data to be loaded for `.im` to work
        img.load()
        palette_image.load()
        im = img.im.convert('P', True, palette_image.im)
        # create the new 7 color image and return it
        return img._new(im)

    def _display_image(self, image: Image, saturation: float = 0.5):
        """displays a image on the inky display

        Args:
            image (Image): Image to display
            saturation (float, optional): saturation. Defaults to 0.5.
        """
        try:
            if self.config.get('DEFAULT', 'model') == 'inky':
                inky = self.inky_auto()
                inky.set_image(image, saturation=saturation)
                inky.show()
            if self.config.get('DEFAULT', 'model') == 'inky-phat':
                inky = self.inky_auto()
                inky.set_image(image)
                inky.show()
            if self.config.get('DEFAULT', 'model') == 'waveshare4':
                epd = self.wave4.EPD()
                epd.init()
                epd.display(epd.getbuffer(self._convert_image_wave(image)))
                epd.sleep()
        except Exception as e:
            self.logger.error(f'Display image error: {e}')
            self.logger.error(traceback.format_exc())

    def _gen_pic(self, image: Image, artist: str, title: str) -> Image:
        """Generates the Picture for the display

        Args:
            image (Image): album cover to be used
            artist (str): Artist text
            title (str): Song text

        Returns:
            Image: The finished image
        """
        album_cover_small_px = self.config.getint('DEFAULT', 'album_cover_small_px')
        offset_px_left = self.config.getint('DEFAULT', 'offset_px_left')
        offset_px_right = self.config.getint('DEFAULT', 'offset_px_right')
        offset_px_top = self.config.getint('DEFAULT', 'offset_px_top')
        offset_px_bottom = self.config.getint('DEFAULT', 'offset_px_bottom')
        offset_text_px_shadow = self.config.getint('DEFAULT', 'offset_text_px_shadow')
        text_direction = self.config.get('DEFAULT', 'text_direction')
        text_color = self.config.get('DEFAULT', 'text_color')
        text_shadow_color = self.config.get('DEFAULT', 'text_shadow_color')
        # The width and height of the background
        bg_w, bg_h = image.size
        if self.config.get('DEFAULT', 'background_mode') == 'fit':
            if bg_w < self.config.getint('DEFAULT', 'width') or bg_w > self.config.getint('DEFAULT', 'width'):
                image_new = ImageOps.fit(image=image, size=(
                    self.config.getint('DEFAULT', 'width'), self.config.getint('DEFAULT', 'height')), centering=(0, 0))
            else:
                # no need to expand just crop
                image_new = image.crop(
                    (0, 0, self.config.getint('DEFAULT', 'width'), self.config.getint('DEFAULT', 'height')))
        if self.config.get('DEFAULT', 'background_mode') == 'repeat':
            if bg_w < self.config.getint('DEFAULT', 'width') or bg_h < self.config.getint('DEFAULT', 'height'):
                # we need to repeat the background
                # Creates a new empty image, RGB mode, and size of the display
                image_new = Image.new('RGB',
                                      (self.config.getint('DEFAULT', 'width'), self.config.getint('DEFAULT', 'height')))
                # Iterate through a grid, to place the background tile
                for x in range(0, self.config.getint('DEFAULT', 'width'), bg_w):
                    for y in range(0, self.config.getint('DEFAULT', 'height'), bg_h):
                        # paste the image at location x, y:
                        image_new.paste(image, (x, y))
            else:
                # no need to repeat just crop
                image_new = image.crop(
                    (0, 0, self.config.getint('DEFAULT', 'width'), self.config.getint('DEFAULT', 'height')))
        if self.config.getboolean('DEFAULT', 'album_cover_small'):
            cover_smaller = image.resize([album_cover_small_px, album_cover_small_px], Image.LANCZOS)
            album_pos_x = (self.config.getint('DEFAULT', 'width') - album_cover_small_px) // 2
            image_new.paste(cover_smaller, [album_pos_x, offset_px_top])
        font_title = ImageFont.truetype(self.config.get('DEFAULT', 'font_path'),
                                        self.config.getint('DEFAULT', 'font_size_title'))
        font_artist = ImageFont.truetype(self.config.get('DEFAULT', 'font_path'),
                                         self.config.getint('DEFAULT', 'font_size_artist'))
        if text_direction == 'top-down':
            title_position_y = album_cover_small_px + offset_px_top + 10
            title_height = self._fit_text_top_down(img=image_new, text=title, text_color=text_color,
                                                   shadow_text_color=text_shadow_color, font=font_title,
                                                   font_size=self.config.getint('DEFAULT', 'font_size_title'),
                                                   y_offset=title_position_y, x_start_offset=offset_px_left,
                                                   x_end_offset=offset_px_right,
                                                   offset_text_px_shadow=offset_text_px_shadow)
            artist_position_y = album_cover_small_px + offset_px_top + 10 + title_height
            self._fit_text_top_down(img=image_new, text=artist, text_color=text_color, shadow_text_color=text_shadow_color,
                                    font=font_artist, font_size=self.config.getint('DEFAULT', 'font_size_artist'),
                                    y_offset=artist_position_y, x_start_offset=offset_px_left,
                                    x_end_offset=offset_px_right, offset_text_px_shadow=offset_text_px_shadow)
        if text_direction == 'bottom-up':
            artist_position_y = self.config.getint('DEFAULT', 'height') - (
                    offset_px_bottom + self.config.getint('DEFAULT', 'font_size_artist'))
            artist_height = self._fit_text_bottom_up(img=image_new, text=artist, text_color=text_color,
                                                     shadow_text_color=text_shadow_color, font=font_artist,
                                                     font_size=self.config.getint('DEFAULT', 'font_size_artist'),
                                                     y_offset=artist_position_y, x_start_offset=offset_px_left,
                                                     x_end_offset=offset_px_right,
                                                     offset_text_px_shadow=offset_text_px_shadow)
            title_position_y = self.config.getint('DEFAULT', 'height') - (
                    offset_px_bottom + self.config.getint('DEFAULT', 'font_size_title')) - artist_height
            self._fit_text_bottom_up(img=image_new, text=title, text_color=text_color, shadow_text_color=text_shadow_color,
                                     font=font_title, font_size=self.config.getint('DEFAULT', 'font_size_title'),
                                     y_offset=title_position_y, x_start_offset=offset_px_left,
                                     x_end_offset=offset_px_right, offset_text_px_shadow=offset_text_px_shadow)
        return image_new

    def _display_update_process(self, song_info: SongInfo = None, weather_info=None):
        """
        Args:
            song_info (SongInfo)
        Returns:
            int: updated picture refresh counter
        """
        if song_info:
            # download cover
            image = self._gen_pic(Image.open(requests.get(song_info.album_art, stream=True).raw), song_info.artist,
                                  song_info.title)
        elif weather_info:

            # not song playing use logo + weather info
            image = self._gen_pic(Image.open(self.config.get('DEFAULT', 'no_song_cover')),
                                  weather_info['weather_sub_description'],
                                  weather_info['temperature'])
        else:
            # not song playing use logo
            image = self._gen_pic(Image.open(self.config.get('DEFAULT', 'no_song_cover')), 'shazampi-eink',
                                  'No song playing')
        # clean screen every x pics
        if self.pic_counter > self.config.getint('DEFAULT', 'display_refresh_counter'):
            self._display_clean()
            self.pic_counter = 0
        # display picture on display
        self._display_image(image)
        self.pic_counter += 1

    def _get_song_info(self, raw_audio) -> SongInfo:
        """get the currently playing song

        Returns:
            SongInfo: with song name, album cover url, artist's name's
        """
        wav_audio = self.audio_service.convert_audio_to_wav_format(raw_audio)
        song_info_dict = self.shazam_service.identify_song(wav_audio)
        if song_info_dict:
            logging.debug("found song")
            return SongInfo(title=song_info_dict['title'],
                            artist=song_info_dict['artist'],
                            album_art=song_info_dict['album_art'],
                            song_duration=song_info_dict['song_duration'],
                            offset=song_info_dict['offset'])
        else:
            logging.debug("couldn't identify the music")

    def start(self):
        self.logger.info('Service started')
        # clean screen initially
        self._display_clean()
        prev_song_title = None
        weather_info = self.weather_service.get_weather_data()
        was_music_playing = False
        last_music_detection_time = datetime.datetime.now()
        song_end_duration_left = self.delay
        try:
            while True:
                try:
                    raw_audio = self.audio_service.record_raw_audio(self.recording_duration)
                    is_music_playing = self.music_detector.is_audio_music(raw_audio)
                    if is_music_playing:
                        # music is playing but check if we should re-trigger shazam
                        #   music was stopped in previous iteration i.e !was_music_playing
                        #   OR
                        #   song_info is outdated
                        if not was_music_playing or datetime.datetime.now() - last_music_detection_time >= datetime.timedelta(
                                seconds=song_end_duration_left):
                            self.logger.debug("music detected, identifying....")
                            # music detected, identify using shazam
                            song_info = self._get_song_info(raw_audio)

                            if song_info:
                                self.logger.debug("identified....")
                                # update remaining time to wait for next re-identify
                                if self.config.has_option('DEFAULT', 'delay_override'):
                                    song_end_duration_left = self.config.getint('DEFAULT', 'delay_override')
                                elif song_info.song_duration is None or song_info.offset is None:
                                    song_end_duration_left = self.delay
                                else:
                                    song_end_duration_left = max(self.delay,
                                                                 song_info.song_duration-song_info.offset-self.recording_duration)
                            else:
                                self.logger.debug("couldn't identify the song")
                                song_end_duration_left = 30  # couldn't identify song so retry in 30 sec

                            self.logger.debug(f"won't re-identify for {song_end_duration_left} seconds")

                            if song_info and song_info.title != prev_song_title:
                                self._display_update_process(song_info=song_info)
                                self.current_view = ViewState.PLAYING
                                prev_song_title = song_info.title
                            last_music_detection_time = datetime.datetime.now()
                        was_music_playing = True
                    else:
                        if was_music_playing:
                            self.logger.debug("music stopped...")
                        was_music_playing = False

                    if (not was_music_playing
                            and datetime.datetime.now() - last_music_detection_time >= datetime.timedelta(minutes=1)):
                        # nothing playing to set display to NO SONG view

                        # no need to reset everytime
                        if self.current_view != ViewState.NOTHING_PLAYING:
                            self._display_update_process(weather_info=weather_info)
                            prev_song_title = None

                        # weather data outdated after 30 min, update
                        elif datetime.datetime.now() - weather_info['fetched_at'] >= datetime.timedelta(minutes=30):
                            weather_info = self.weather_service.get_weather_data()
                            self._display_update_process(weather_info=weather_info)
                            self.current_view = ViewState.NOTHING_PLAYING

                        self.current_view = ViewState.NOTHING_PLAYING

                except Exception as e:
                    self.logger.error(f'Error: {e}')
                    self.logger.error(traceback.format_exc())
        except KeyboardInterrupt:
            self.logger.info('Service stopping')
            sys.exit(0)


if __name__ == "__main__":
    service = ShazampiEinkDisplay()
    service.start()
