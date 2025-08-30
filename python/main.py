import threading
import json
from webhook_listener import Listener  # your webhook listener module
from shazampi_display import ShazampiEinkDisplay, SongInfo  # adjust import paths

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
        display._display_update_process(song_info=song)
    else:
        # fallback to weather
        weather = display.weather_service.get_weather_data()
        display._display_update_process(weather_info=weather)

# --- Periodic weather updater ---
def weather_loop(interval_minutes=30):
    while True:
        weather = display.weather_service.get_weather_data()
        display._display_update_process(weather_info=weather)
        threading.Event().wait(interval_minutes * 60)

# --- Start webhook listener ---
handlers = {'POST': handle_webhook}
listener = Listener(handlers=handlers)

if __name__ == "__main__":
    # show initial weather immediately
    initial_weather = display.weather_service.get_weather_data()
    display._display_update_process(weather_info=initial_weather)

    threading.Thread(target=weather_loop, daemon=True).start()
    print("Webhook listener running...")
    listener.start()

