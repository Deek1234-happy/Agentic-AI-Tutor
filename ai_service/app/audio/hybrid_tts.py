import re
import numpy as np
import io
import soundfile as sf

from app.audio.xtts_tts import generate_speech as coqui_tts
from app.audio.tts import generate_speech as piper_tts


class HybridTTS:

    def detect_language(self, text: str) -> str:
        if re.search(r'[\u0600-\u06FF]', text):
            return "ar"
        return "en"

    def synthesize(self, text: str) -> bytes:
        lang = self.detect_language(text)

        if lang == "ar":
            print("🎙 Using Coqui (Arabic)")
            result = coqui_tts(text)
        else:
            print("⚡ Using Piper (English/Fast)")
            result = piper_tts(text)

        # ============================
        # Normalize output to bytes
        # ============================

        # Case 1: tuple (audio, sample_rate)
        if isinstance(result, tuple):
            audio = result[0]
            sample_rate = result[1] if len(result) > 1 else 22050
        else:
            audio = result
            sample_rate = 22050

        # Case 2: already bytes
        if isinstance(audio, bytes):
            return audio

        # Case 3: numpy array → convert to WAV bytes
        if isinstance(audio, np.ndarray):
            buffer = io.BytesIO()
            sf.write(buffer, audio, sample_rate, format='WAV')
            return buffer.getvalue()

        # Case 4: file path → read as bytes
        if isinstance(audio, str):
            with open(audio, "rb") as f:
                return f.read()

        # Unsupported format
        raise ValueError("Unsupported audio format returned from TTS")