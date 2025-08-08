# ShazamPi E-Ink
![shazampi-eink Logo](/images/logo.png)

## Table of Contents
- [ShazamPi E-Ink](#shazampi-e-ink)
  - [Overview](#overview)
  - [Getting Started](#getting-started)
  - [Configuration](#configuration)
  - [Supported Hardware](#supported-hardware)
  - [Software](#software)
  - [3D Printing](#3d-printing)
    - [Free Cases](#free-cases)
    - [Non-Free Cases from Pimoroni](#non-free-cases-from-pimoroni)
  - [Showcase](#showcase)

## Overview
This project is a spinoff of the spotipi-eink project but does not use Spotify (or any streaming service) for showing what's playing.  
It relies on the [Shazamio](https://github.com/shazamio/ShazamIO) project to identify the music playing nearby.
Even though the reverse-engineered API is free (for now), it's undesirable to record audio and send it to Shazam continuously.  
To avoid this, we first process the audio recording with a locally running ML model ([YAMNet lite](https://www.tensorflow.org/hub/tutorials/yamnet)), which has "Music" as one of the classes. Once we have high confidence that there is music playing in the surrounding, we then send the audio recording to Shazam for identifying the song.

In my experiments, I've found that a 5-second audio clip was enough for the model to detect music; however, Shazam was more reliable with a 10-second audio recording.  
The model runs perfectly on the Pi Zero using the `tflite-runtime`.

Once the song is identified, its information is displayed on a 4", 5.7", or 7.3" e-ink display.  
Most of the work for displaying content is derived from [Spotipi-eink](https://github.com/Gabbajoe/spotipi-eink), including many of the instructions listed here.

This has been tried and tested on the Raspberry Pi Zero 2W, so it should work on any Raspberry Pi released after that.

## Getting Started

* This has been tested with `Raspberry Pi OS(64-bit) lite bookworm`
* Enable SPI and I2C under "Interface Options" with the command:
    ```bash
    sudo raspi-config
    ```
* Create an account at https://openweathermap.org/ and get api_key(free account)
* Locate your geo co-ordinates using Google Maps(right-click on the location)

* Download the setup script:
    ```bash
    wget https://raw.githubusercontent.com/ravi72munde/shazampi-eink/main/setup.sh
    chmod +x setup.sh
    ```

* Install the software: 
    ```bash
    bash setup.sh
    ```

After the shazampi-eink is installed, you have a systemd service:
* `shazampi-eink-display.service`

This service runs as the user who executed the setup.sh and should be enabled to autostart on boot.

You control the service via `systemctl` `start` | `stop` | `status` | `restart` | `enable` | `disable` `<service-name>`. For example, to get the status of `shazampi-eink-display.service`:
```bash
pi@shazampi:~/shazampi-eink $ sudo systemctl status shazampi-eink-display.service
  shazampi-eink-display.service - Shazampi eInk Display service
     Loaded: loaded (/etc/systemd/system/shazampi-eink-display.service; enabled; preset: enabled)
    Drop-In: /etc/systemd/system/shazampi-eink-display.service.d
             └─shazampi-eink-display_env.conf
     Active: active (running) since Wed 2024-08-28 21:46:29 EDT; 29min ago
   Main PID: 2084 (python3)
      Tasks: 15 (limit: 167)
        CPU: 1min 43.599s
     CGroup: /system.slice/shazampi-eink-display.service
             └─2084 /home/pi/shazampi-eink/shazampienv/bin/python3 /home/pi/shazampi-eink/python/shazam>

Aug 28 22:12:00 shazampi shazampi-eink-display[2084]: Shazampi eInk Display - music detected, identifying...
Aug 28 22:13:17 shazampi shazampi-eink-display[2084]: Shazampi eInk Display - will wake up after 30 sec

```

You can check the logs of the service by running:
```
# see all time logs
journalctl -u shazampi-eink-display.service
```
or
```
# see only today logs
journalctl -u shazampi-eink-display.service --since today
```
or

```
# see current boot logs
journalctl -u shazampi-eink-display.service -b
```


Shazampi-eink creates its own Python environment.

If you like to manual execute the Python script you have to load into the Virtual Python environment like the following commands shows. You will see then in front of you terminal a `(shazampienv)`:
```
source ~/shazampi-eink/shazampienv/bin/activate
```

If you like to leave the Virtual Python environment just type: `deactivate`


## Configuration
In the file `shazampi/config/eink_options.ini` you can modify:
* the displayed *title* and *artist* text size
* the direction of how the title or artist text line break will be done, **top-down** or **bottom-up**
* the offset from display borders
* disable the small album cover
* the size of the small album cover
* the font that will be used
* weather api key, location and units 
Example config:

```
[DEFAULT]
width = 640
height = 400
album_cover_small_px = 200
model = waveshare4
; disable smaller album cover set to False
; if disabled top offset is still calculated like as the following:
; offset_px_top + album_cover_small_px
album_cover_small = True
; cleans the display every 20 picture
; this takes ~60 seconds
display_refresh_counter = 20
shazampi_log = /home/pi/shazampi-eink/log/shazampi.log
no_song_cover = /home/pi/shazampi-eink/resources/default.jpg
font_path = /home/pi/shazampi-eink/resources/CircularStd-Bold.otf
font_size_title = 45
font_size_artist = 35
offset_px_left = 20
offset_px_right = 20
offset_px_top = 0
offset_px_bottom = 20
offset_text_px_shadow = 4
; text_direction possible values: top-down or bottom-up
text_direction = bottom-up
; possible modes are fit or repeat
background_mode = fit
openweathermap_api_key = random_id
geo_coordinates = 40.7484907432474, -73.98564504449533
units=imperial
```

## Supported Hardware
* [Raspberry Pi Zero 2](https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/)
* [Pimoroni Inky Impression 4"](https://shop.pimoroni.com/products/inky-impression-4?variant=39599238807635)
* [Waveshare 4.01inch ACeP 7-Color E-Paper E-Ink Display HAT](https://www.waveshare.com/product/displays/e-paper/epaper-2/4.01inch-e-paper-hat-f.htm)
* [Pimoroni Inky Impression 5.7"](https://shop.pimoroni.com/products/inky-impression-5-7?variant=32298701324371)
* [Pimoroni Inky Impression 7.3"](https://shop.pimoroni.com/products/inky-impression-7-3?variant=40512683376723)

Since raspberry pi doesn't have an in-built mic, I tried a couple of USB mics with great success. They are cheap as well as compact
* [Mini USB Microphone](https://www.amazon.com/dp/B071WH7FC6) (plug and play)
* [Mini USB Microphone(Adafruit link)](https://www.adafruit.com/product/3367) (plug and play)
* [Mini USB Microphone with gooseneck](https://www.amazon.com/dp/B08M37224H) (plug and play)
* [[Not Tested] MAX9814 Adafruit Amp](https://www.adafruit.com/product/1713)(if you want to go integrated route)

But I'm sure any mic should work as long as it records with least at 16kHz samplerate (which is minimal for the ML model to work)

## Software
* [Raspberry Pi Imager](https://www.raspberrypi.com/software/)

## 3D printing
### Free cases
* [Shazampi-eink Waveshare 4 inch case](https://www.printables.com/model/993754-shazampi-eink-waveshare-4-inch-case)
* [SpotiPi E-Ink - Inky Impression 5.7" Case](https://cults3d.com/en/3d-model/gadget/spotipi-e-ink-inky-impression-5-7-case)
* [Pimoroni Inky Impression Case - 5.7" I guess](https://www.printables.com/de/model/51765-pimoroni-inky-impression-case/files)
* [Inky Impression 5.7" Frame](https://www.printables.com/de/model/603008-inky-impression-57-frame)
* [Inky Impression 7.3 e-Paper frame/case](https://www.printables.com/de/model/585713-inky-impression-73-e-paper-framecase)
* [Pimoroni 7 color EInk display Frame](https://www.thingiverse.com/thing:4666925)
* [Spotipi-eink Waveshare 4 inch case](https://www.printables.com/model/634213-spotipi-eink-waveshare-4-inch-case)
### Non-free cases from Pimoroni
* [Desktop Case for pimoroni Inky Impression 4" (7 colour ePaper/eInk HAT) and Raspberry Pi Zero/3 A+](https://cults3d.com/en/3d-model/gadget/desktop-case-for-pimoroni-inky-impression-4-7-colour-epaper-eink-hat-and-raspberry-pi-zero-3-a)
* [Picture frame for pimoroni Inky Impression 5.7" (ePaper/eInk/EPD) and raspberry pi zero](https://cults3d.com/en/3d-model/gadget/picture-frame-for-pimoroni-inky-impression-epaper-eink-epd-and-raspberry-pi-zero)
* [Enclosure for pimoroni Inky Impression (ePaper/eInk/EPD) and raspberry pi zero](https://cults3d.com/en/3d-model/gadget/enclosure-for-pimoroni-inky-impression-epaper-eink-epd-and-raspberry-pi-zero)


## Show case

### Example picture of 4" display in custom case:
<img src="/images/example.png" height="350">

### Default view when no song playing on Waveshare 4.01 color display with weather info
<img src="/images/no_song.jpg" height="350">

## Notes: 
* Alternative to Shazam: https://audd.io/ (paid),  https://acoustid.org/webservice (open source but needs some work)
* If you want to port the app to a non-raspberry pi hardward refer to [Google's kaggle project](https://www.kaggle.com/models/google/yamnet/tensorFlow2/yamnet/) for samples as well as the model to run on tensorflow
* The model is able to identify most of the music but can (although rarely) have trouble identifying Raps songs with a lot more speech
