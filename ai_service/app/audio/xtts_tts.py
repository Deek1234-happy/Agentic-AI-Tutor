import os
import uuid
import re

from app.audio import coqui_tts_compat  # noqa: F401 — PyTorch 2.6+ load + transformers aliases
from TTS.api import TTS
from pydub import AudioSegment

# ============================================================
# CONFIG
# ============================================================

OUTPUT_DIR = "static/audio"
TEMP_DIR = "temp"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)


# ============================================================
# XTTS SERVICE (Arabic Only)
# ============================================================

class XTTSService:

    def __init__(self):
        print("🔵 Loading Coqui XTTS...")
        self.tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")

    def synthesize(self, text: str, output_path: str) -> str:

        # 🔥 forced Arabic
        self.tts.tts_to_file(
            text=text,
            file_path=output_path,
            speaker="Ana Florence",
            language="ar"
        )

        return output_path


# ============================================================
# LAZY LOAD
# ============================================================

_tts_instance = None

def get_tts():
    global _tts_instance
    if _tts_instance is None:
        _tts_instance = XTTSService()
    return _tts_instance


# ============================================================
# SMART SPLIT
# ============================================================

def split_text(text, max_length=120):
    chunks = []

    while len(text) > max_length:
        split_at = text.rfind(" ", 0, max_length)
        if split_at == -1:
            split_at = max_length

        chunks.append(text[:split_at].strip())
        text = text[split_at:].strip()

    if text:
        chunks.append(text)

    return chunks


# ============================================================
# GENERATE SPEECH (Arabic Only)
# ============================================================

def generate_speech(text: str):

    chunks = split_text(text)

    audio_segments = []
    chunk_paths = []

    for i, chunk in enumerate(chunks):

        if not chunk.strip():
            continue

        chunk_path = os.path.join(
            TEMP_DIR,
            f"chunk_{i}_{uuid.uuid4().hex}.wav"
        )

        get_tts().synthesize(chunk, chunk_path)

        segment = AudioSegment.from_wav(chunk_path)

        audio_segments.append(segment)
        chunk_paths.append(chunk_path)

    if not audio_segments:
        raise ValueError("No audio generated")

    final_audio = AudioSegment.empty()
    pause = AudioSegment.silent(duration=200)

    for seg in audio_segments:
        final_audio += seg + pause

    file_name = f"{uuid.uuid4().hex}.wav"
    output_path = os.path.join(OUTPUT_DIR, file_name)

    final_audio.export(output_path, format="wav")

    # cleanup
    for path in chunk_paths:
        if os.path.exists(path):
            os.remove(path)

    return output_path, "ar"