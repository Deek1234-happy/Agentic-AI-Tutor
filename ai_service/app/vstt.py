from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import uuid
import os
from app.audio.stt import transcribe_audio
from pydantic import BaseModel


router = APIRouter()

TEMP_DIR = "temp_audio"
os.makedirs(TEMP_DIR, exist_ok=True)

MAX_SIZE = 10 * 1024 * 1024  # 10MB

class STTResponse(BaseModel):
    session_id: str
    user_id: str
    text: str
    confidence: float

@router.post("/stt",response_model=STTResponse)
async def speech_to_text(
    session_id: str = Form(...),
    user_id: str = Form(...),
    audio_file: UploadFile = File(...)
):
    temp_path = None

    try:
        # ✅ validation
        if not audio_file.content_type.startswith("audio"):
            raise HTTPException(status_code=400, detail="Invalid file type")

        content = await audio_file.read()

        if len(content) > MAX_SIZE:
            raise HTTPException(status_code=400, detail="File too large")

        # ✅ save temp file
        file_ext = audio_file.filename.split(".")[-1]
        temp_filename = f"{uuid.uuid4()}.{file_ext}"
        temp_path = os.path.join(TEMP_DIR, temp_filename)

        with open(temp_path, "wb") as f:
            f.write(content)

        # ✅ call your STT
        text, confidence = transcribe_audio(temp_path)

        #  logging 
        print(f"[STT] text={text}, confidence={confidence}")

        return STTResponse(
            session_id=session_id,
            user_id=user_id,
            text=text,
            confidence=confidence
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # ✅ cleanup
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)