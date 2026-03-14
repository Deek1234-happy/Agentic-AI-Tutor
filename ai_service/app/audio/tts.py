from piper import PiperVoice
import wave
import re
import os
from pathlib import Path

class PiperTTS:

    def __init__(self):
        # Get current file directory
        current_dir = os.path.dirname(os.path.abspath(__file__))

        # models folder inside app/audio
        base_path = os.path.join(current_dir, "models")
        
        # Create models directory if it doesn't exist
        Path(base_path).mkdir(parents=True, exist_ok=True)

        # Load voices with automatic download support
        # Piper will download models to the specified directory if they don't exist
        self.en_voice = PiperVoice.load(
            "en_US-amy-medium",
            model_path=base_path,
            download=True
        )

        self.ar_voice = PiperVoice.load(
            "ar_JO-kareem-medium",
            model_path=base_path,
            download=True
        )

    def detect_language(self, text: str) -> str:
        # Detect Arabic characters
        if re.search(r'[\u0600-\u06FF]', text):
            return "ar"
        return "en"

    def synthesize(self, text: str, output_path="response.wav") -> str:

        lang = self.detect_language(text)
        voice = self.ar_voice if lang == "ar" else self.en_voice

        with wave.open(output_path, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(voice.config.sample_rate)

            for chunk in voice.synthesize(text):
                wav_file.writeframes(chunk.audio_int16_bytes)

        return output_path
    
    # create a stream version
_tts_instance = None

def _initialize_tts():
    """Lazy initialization of TTS instance"""
    global _tts_instance
    if _tts_instance is None:
        try:
            _tts_instance = PiperTTS()
        except FileNotFoundError as e:
            raise RuntimeError(
                f"Piper TTS models not found. Please download the models to the app/audio/models directory. Error: {e}"
            )
    return _tts_instance

def generate_speech(text: str, output_path: str = None) -> str:
    if output_path is None:
        import uuid
        output_path = f"temp/response_{uuid.uuid4().hex}.wav"

    tts = _initialize_tts()
    return tts.synthesize(text, output_path)