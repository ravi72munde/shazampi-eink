import configparser
import os
import threading
import json
from webhook_listener import Listener
from shazampi_display import ShazampiEinkDisplay, SongInfo
from service.weather_service import WeatherService

display = ShazampiEinkDisplay()

# --- Webhook handler ---
def handle_webhook(request, *args, **kwargs):
    body = request.body.read(int(request.headers.get('Content-Length', 0)))
    payload = json.loads(body.decode('utf-8'))

    song_data = payload.get('data')  # {"title": "...", "artist": "...", "album_art": "..."} or None
    if song_data:
        song = SongInfo(
            title=song_data['title'],
            artist=song_data['artist'],
            album_art=song_data['album_art'],
            offset=None,
            song_duration=None
        )
        display.display_update_process(song_info=song)
    else:
        # fallback to weather
        weather = display.weather_service.get_weather_data()
        display.display_update_process(weather_info=weather)

# --- Periodic weather updater ---
def weather_loop(interval_minutes=30):
    while True:
        weather = display.weather_service.get_weather_data()
        display.display_update_process(weather_info=weather)
        threading.Event().wait(interval_minutes * 60)

# --- Start webhook listener ---
handlers = {'POST': handle_webhook}
listener = Listener(handlers=handlers)

if __name__ == "__main__":
    # Load config and weather service
    config = configparser.ConfigParser()
    config.read(os.path.join(os.path.dirname(__file__), '..', 'config', 'eink_options.ini'))
    openweathermap_api_key = config.get('DEFAULT', 'openweathermap_api_key')
    geo_coordinates = config.get('DEFAULT', 'geo_coordinates')
    units = config.get('DEFAULT', 'units')
    display.weather_service = WeatherService(api_key=openweathermap_api_key,
                                             geo_coordinates=geo_coordinates,
                                             units=units)

    # Show initial weather immediately
    initial_weather = display.weather_service.get_weather_data()
    display.display_update_process(weather_info=initial_weather)

    # Start weather updater in a daemon thread
    weather_thread = threading.Thread(target=weather_loop, daemon=True)
    weather_thread.start()

    print("Webhook listener running...")

    # Start webhook listener
    listener.start()

    # Block main thread to keep daemon threads alive
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        print("Exiting service...")
