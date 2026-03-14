from fastapi import APIRouter, UploadFile, File
from fastapi.responses import FileResponse
import uuid
import os
import shutil

from app.audio.stt import transcribe_audio
from app.audio.normalize import normalize_text
from app.audio.tts import generate_speech
from app.rag_service import answer_question
from app.llm import generate_answer

router = APIRouter()

@router.post("/voice-chat")
async def voice_chat(audio: UploadFile = File(...)):

    temp_filename = f"temp_{uuid.uuid4().hex}.wav"
    temp_dir = "temp"
    os.makedirs(temp_dir, exist_ok=True)

    temp_path = os.path.join(temp_dir, temp_filename)

    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(audio.file, buffer)

    try:
        # 1️ Transcribe
        transcript, stt_confidence = transcribe_audio(temp_path)

        # 2️ Normalize
        clean_text = normalize_text(
            text=transcript,
            stt_confidence=stt_confidence,
            llm_callable=generate_answer,
            confidence_threshold=0.75
        )

        # 3️ RAG
        answer, retrieved_chunks = answer_question(clean_text)

        # 4️ TTS
        audio_output_path = generate_speech(answer)

        # 5️ Return audio file (stable)
        return FileResponse(
            audio_output_path,
            media_type="audio/wav"
        )

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)