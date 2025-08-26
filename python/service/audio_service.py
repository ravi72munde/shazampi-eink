import io
import logging

import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav

from scipy.signal import resample

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AudioService:
    def __init__(self):
        self.device_name_substring = 'USB'  # usb mics generally contain this in their name
        self.down_sampled_rate = 16000  # sample rate supported by ML model and Shazam API
        self.raw_recording_sample_rate = 44100  # only supported rate by raspberry pi zero
        self.gain = 3.0  # you can adjust this if needed
        device_index = self.find_device_idx_by_name()

        if device_index is not None:
            sd.default.device = (device_index, None)
        else:
            logger.warning(f"{self.device_name_substring} device not found. Using default audio device.")

    def find_device_idx_by_name(self):
        devices = sd.query_devices()
        for idx, device in enumerate(devices):
            if self.device_name_substring in device['name']:
                return idx
        return None

    def is_mic_connected(self):
        return self.find_device_idx_by_name() is not None

    def record_raw_audio(self, recording_duration):
        audio = sd.rec(int(recording_duration * self.raw_recording_sample_rate),
                       samplerate=self.raw_recording_sample_rate, channels=1, dtype=np.float32)
        sd.wait()
        num_samples = int(len(audio) * self.down_sampled_rate / self.raw_recording_sample_rate)
        resampled_audio = resample(audio, num_samples)
        max_val = np.max(np.abs(resampled_audio))
        if max_val > 0:
            resampled_audio = resampled_audio / max_val
        resampled_audio = np.clip(resampled_audio * self.gain, -1.0, 1.0)
        return np.squeeze(resampled_audio)

    def convert_audio_to_wav_format(self, raw_audio):
        audio_buffer = io.BytesIO()
        wav.write(audio_buffer, self.down_sampled_rate, raw_audio)
        audio_buffer.seek(0)
        return audio_buffer
