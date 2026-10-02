from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import io
import re

from app.audio.hybrid_tts import HybridTTS

router = APIRouter()
tts_engine = None


class TTSRequest(BaseModel):
    text: str


def sanitize_for_tts(text: str) -> str:
    if text is None:
        return ""

    cleaned = text
    cleaned = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", cleaned)
    cleaned = re.sub(r"[*_`>#-]", " ", cleaned)
    cleaned = cleaned.replace("#", " ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


@router.post("/tts")
async def text_to_speech(request: TTSRequest):
    global tts_engine

    try:
        if tts_engine is None:
            print("🔥 Initializing HybridTTS...")
            tts_engine = HybridTTS()

        clean_text = sanitize_for_tts(request.text)
        if not clean_text:
            raise HTTPException(status_code=400, detail="Text cannot be empty")

        # generate audio
        audio_bytes = tts_engine.synthesize(clean_text)

        if not audio_bytes:
            raise HTTPException(status_code=500, detail="Failed to generate audio")

        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type="audio/wav"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))