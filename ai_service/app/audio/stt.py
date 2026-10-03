from faster_whisper import WhisperModel
from typing import Tuple
import os
from app.language_config import LANGUAGES, normalize_language

# Load model once for better performance
MODEL_SIZE = "medium"  # change to "small" if RAM is limited

# Default CPU: avoids "cublas64_12.dll is not found" on Windows when a GPU is
# present but the CUDA 12 toolkit / cuBLAS runtime is not installed.
# Set WHISPER_DEVICE=cuda only with a matching CUDA+cuDNN stack for GPU inference.
_whisper_dev = os.environ.get("WHISPER_DEVICE", "cpu").strip().lower()
_use_cuda = _whisper_dev in ("gpu", "cuda")
if _use_cuda:
    _compute = os.environ.get("WHISPER_COMPUTE_TYPE", "float16")
    model = WhisperModel(MODEL_SIZE, device="cuda", compute_type=_compute)
else:
    _compute = os.environ.get("WHISPER_COMPUTE_TYPE", "int8")
    model = WhisperModel(MODEL_SIZE, device="cpu", compute_type=_compute)


def transcribe_audio(audio_path: str, language: str | None = None) -> Tuple[str, float]:
    """
    Transcribes an audio file using Faster-Whisper.

    Args:
        audio_path (str): Path to the audio file.

    Returns:
        Tuple[str, float]:
            - transcript (str): Transcribed text
            - confidence (float): Confidence score (0 to 1)
    """

    # Validate file existence
    if not os.path.exists(audio_path):
        raise FileNotFoundError("Audio file not found")

    # Perform transcription
    language_code = normalize_language(language) if language else None
    whisper_language = (
        LANGUAGES[language_code]["whisper"]
        if language_code and language_code != "en"
        else None
    )
    segments, info = model.transcribe(
        audio_path,
        beam_size=5,
        language=whisper_language,
        condition_on_previous_text=False,
        task="transcribe",
        initial_prompt = "The following audio may contain multiple languages. Transcribe exactly as spoken. Do not translate.",
        vad_filter=True
    )

    # Log detected language information
    print(f"[STT] Detected language: {info.language}")
    print(f"[STT] Language probability: {info.language_probability}")

    full_text = ""
    logprobs = []

    # Collect text and log probabilities from segments
    for segment in segments:
        if segment.text:
            full_text += segment.text.strip() + " "
        if segment.avg_logprob is not None:
            logprobs.append(segment.avg_logprob)

    full_text = full_text.strip()

    # Handle case where no speech was detected
    if not full_text:
        return "", 0.0

    # Handle case where log probabilities are missing
    if not logprobs:
        return full_text, 0.0

    # Compute average log probability
    avg_logprob = sum(logprobs) / len(logprobs)

    # Convert log probability to confidence score (normalized)
    confidence = max(min(1 + avg_logprob, 1), 0)

    # Slight boost if language detection is highly confident
    if hasattr(info, "language_probability") and info.language_probability > 0.8:
        confidence = min(confidence + 0.05, 1)

    confidence = round(confidence, 3)

    # Log final outputs (useful for debugging and evaluation)
    print(f"[STT] Final text: {full_text}")
    print(f"[STT] Confidence: {confidence}")

    return full_text, confidence