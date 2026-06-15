import wave
import os
import uuid
from pathlib import Path
from piper import PiperVoice

OUTPUT_DIR = "static/audio"
os.makedirs(OUTPUT_DIR, exist_ok=True)


class PiperTTS:

    def __init__(self):
        print("⚡ Loading Piper...")

        current_dir = os.path.dirname(os.path.abspath(__file__))
        base_path = os.path.join(current_dir, "models")

        Path(base_path).mkdir(parents=True, exist_ok=True)

        model_path = os.path.join(base_path, "en_US-amy-medium.onnx")
        config_path = os.path.join(base_path, "en_US-amy-medium.onnx.json")

        
        self.en_voice = PiperVoice.load(model_path, config_path)

    def synthesize(self, text: str, output_path: str):

        with wave.open(output_path, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.en_voice.config.sample_rate)

            for chunk in self.en_voice.synthesize(text):
                wav_file.writeframes(chunk.audio_int16_bytes)

        return output_path


# ============================================================
# LAZY LOAD
# ============================================================

_tts_instance = None

def get_tts():
    global _tts_instance
    if _tts_instance is None:
        _tts_instance = PiperTTS()
    return _tts_instance


# ============================================================
# GENERATE SPEECH
# ============================================================

def generate_speech(text: str):

    file_name = f"{uuid.uuid4().hex}.wav"
    output_path = os.path.join(OUTPUT_DIR, file_name)

    get_tts().synthesize(text, output_path)

    return output_path, "en"