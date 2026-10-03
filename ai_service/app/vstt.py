from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import uuid
import os
from app.audio.stt import transcribe_audio
from app.language_config import normalize_language

router = APIRouter()

TEMP_DIR = "temp_audio"
os.makedirs(TEMP_DIR, exist_ok=True)

MAX_SIZE = 10 * 1024 * 1024  # 10MB


@router.post("/stt")
async def speech_to_text(audio_file: UploadFile = File(...), language: str | None = Form(None)):
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

        # ✅ STT
        try:
            selected_language = normalize_language(language) if language else None
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        text, confidence = transcribe_audio(temp_path, selected_language)

        print(f"[STT] text={text}, confidence={confidence}")

        # 🎯 return text only
        return {"text": text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)