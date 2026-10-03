from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import io
import re
import base64
import os
from typing import Literal

from app.audio.hybrid_tts import HybridTTS
from app.llm import get_gemini_api_key

router = APIRouter()
tts_engine = None
gemini_client = None


class TTSRequest(BaseModel):
    text: str
    language: Literal["en", "kn", "hi", "ml", "ta", "te"] = "en"


def sanitize_for_tts(text: str) -> str:
    if text is None:
        return ""

    cleaned = text
    cleaned = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", cleaned)
    cleaned = re.sub(r"[*_`>#-]", " ", cleaned)
    cleaned = cleaned.replace("#", " ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def synthesize_with_gemini(text: str) -> bytes:
    global gemini_client

    api_key = get_gemini_api_key("GEMINI_TTS_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Gemini TTS is not configured. Set GEMINI_TTS_API_KEY in the AI service environment.",
        )

    if gemini_client is None:
        from google import genai
        gemini_client = genai.Client(api_key=api_key)

    model = os.getenv("GEMINI_TTS_MODEL", "gemini-3.8-flash-lite-tts")
    interaction = gemini_client.interactions.create(
        model=model,
        input=[{
            "type": "user_input",
            "content": [{"type": "text", "text": text}],
        }],
        response_format={"type": "audio"},
        generation_config={"speech_config": [{"voice": os.getenv("GEMINI_TTS_VOICE", "Kore")}]},
        timeout=120,
    )

    output_audio = getattr(interaction, "output_audio", None)
    encoded_audio = getattr(output_audio, "data", None)
    if isinstance(encoded_audio, bytes):
        return encoded_audio
    if not isinstance(encoded_audio, str) or not encoded_audio:
        raise RuntimeError("Gemini TTS returned no audio data.")
    return base64.b64decode(encoded_audio)


@router.post("/tts")
async def text_to_speech(request: TTSRequest):
    global tts_engine

    try:
        clean_text = sanitize_for_tts(request.text)
        if not clean_text:
            raise HTTPException(status_code=400, detail="Text cannot be empty")

        if request.language == "en":
            if tts_engine is None:
                print("🔥 Initializing HybridTTS...")
                tts_engine = HybridTTS()
            audio_bytes = tts_engine.synthesize(clean_text)
        else:
            audio_bytes = synthesize_with_gemini(clean_text)

        if not audio_bytes:
            raise HTTPException(status_code=500, detail="Failed to generate audio")

        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type="audio/wav"
        )

    except HTTPException:
        raise
    except Exception as exc:
        print(f"[TTS] Speech generation failed: {exc}")
        raise HTTPException(status_code=502, detail="Voice output could not be generated.") from exc