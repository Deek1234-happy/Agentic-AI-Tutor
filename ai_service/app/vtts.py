from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import io

from app.audio.hybrid_tts import HybridTTS

router = APIRouter()
tts_engine = None


class TTSRequest(BaseModel):
    text: str
    session_id: str


@router.post("/tts")
async def text_to_speech(request: TTSRequest):
    global tts_engine

    try:
        if tts_engine is None:
            print("🔥 Initializing HybridTTS...")
            tts_engine = HybridTTS()

        if not request.text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")

        # detect language
        language = tts_engine.detect_language(request.text)

        # engine selection
        engine = "coqui" if language == "ar" else "piper"

        # generate audio
        audio_bytes = tts_engine.synthesize(request.text)

        if not audio_bytes:
            raise HTTPException(status_code=500, detail="Failed to generate audio")

        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type="audio/wav",
            headers={
                "X-Session-ID": request.session_id,
                "X-Language": language,
                "X-TTS-Engine": engine,
                "X-Audio-Available": "true"
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))