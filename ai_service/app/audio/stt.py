from faster_whisper import WhisperModel
from typing import Tuple
import os

# Load model once (important for performance)
MODEL_SIZE = "base"  # change to "small" if RAM allows
model = WhisperModel(MODEL_SIZE, compute_type="int8")  

def transcribe_audio(audio_path: str) -> Tuple[str, float]:
    """
    Transcribes audio file using Faster-Whisper.
    Returns:
        transcript (str)
        confidence (float 0-1)
    """

    if not os.path.exists(audio_path):
        raise FileNotFoundError("Audio file not found")

    segments, info = model.transcribe(audio_path)

    full_text = ""
    logprobs = []

    for segment in segments:
        full_text += segment.text.strip() + " "
        logprobs.append(segment.avg_logprob)

    full_text = full_text.strip()

    if not logprobs:
        return "", 0.0

    avg_logprob = sum(logprobs) / len(logprobs)

    # convert log probability to confidence (rough normalization)
    confidence = max(min(1 + avg_logprob, 1), 0)

    return full_text, round(confidence, 3)