from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
import ast
import json
import re
import uuid
import os
import shutil
from typing import List, Dict, Any, Optional

from app.audio.hybrid_tts import HybridTTS

tts_engine = HybridTTS()
from app.audio.stt import transcribe_audio
from app.audio.normalize import normalize_text

from app.chat_service import handle_chat

router = APIRouter()

# ============================================================
# Config
# ============================================================

TEMP_DIR = "temp"
AUDIO_STATIC_DIR = "static/audio"
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(AUDIO_STATIC_DIR, exist_ok=True)

_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def _parse_allowed_document_ids(raw: Optional[str]) -> List[str]:
    """
    Same logical list as JSON body `allowed_document_ids` on POST /chat/.
    Accepts JSON array, Python-style ['id'], comma-separated UUIDs, or one UUID.
    """
    if raw is None or not str(raw).strip():
        return []
    s = str(raw).strip().lstrip("\ufeff")
    s = s.translate(str.maketrans("\u201c\u201d\u2018\u2019", '""\'\''))

    def _coerce_list(data) -> Optional[List[str]]:
        if isinstance(data, list):
            out = [str(x).strip() for x in data if str(x).strip()]
            return out or None
        if isinstance(data, str) and data.strip():
            return [data.strip()]
        return None

    try:
        data = json.loads(s)
        got = _coerce_list(data)
        if got is not None:
            return got
        if isinstance(data, str):
            try:
                inner = json.loads(data.strip())
                got = _coerce_list(inner)
                if got is not None:
                    return got
            except json.JSONDecodeError:
                pass
    except json.JSONDecodeError:
        pass

    if s.startswith("[") and s.endswith("]"):
        try:
            data = ast.literal_eval(s)
            got = _coerce_list(data)
            if got is not None:
                return got
        except (ValueError, SyntaxError):
            pass
        inner = s[1:-1].strip()
        parts = re.split(r",\s*", inner)
        out: List[str] = []
        for p in parts:
            p = p.strip().strip('"').strip("'")
            if p and _UUID_RE.match(p):
                out.append(p)
        if out:
            return out

    if _UUID_RE.match(s):
        return [s]

    parts = [p.strip().strip('"').strip("'") for p in s.split(",")]
    parts = [p for p in parts if p]
    if parts and all(_UUID_RE.match(p) for p in parts):
        return parts

    return []


# ============================================================
# Response Model
# ============================================================

class AskAudioResponse(BaseModel):
    session_id: str
    transcription: str
    clean_text: str
    answer_text: str
    audio_url: str
    confidence: float
    citations: List[Dict]
    status: str


# ============================================================
# Payload — mirror ChatRequest (app/chat.py) for handle_chat()
# ============================================================

class Payload:
    def __init__(
        self,
        session_id: Any,
        user_id: Any,
        question: str,
        allowed_document_ids: List[Any],
        top_k: int = 5,
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.question = question
        self.allowed_document_ids = allowed_document_ids
        self.top_k = top_k


def clean_citations(citations):
    seen = set()
    unique = []

    for c in citations:
        key = (c["document_id"], c["page_start"], c["page_end"])

        if key not in seen:
            seen.add(key)
            unique.append(c)

    return unique


# ============================================================
# Voice chat — same RAG scope as POST /chat/ (allowed_document_ids)
# ============================================================

@router.post("/ask-audio", response_model=AskAudioResponse)
async def ask_audio(
    session_id: str = Form(...),
    user_id: str = Form(...),
    allowed_document_ids: str = Form(
        ...,
        description='Same as /chat/ body: list of document UUIDs. Examples: ["uuid"] or single uuid',
    ),
    top_k: int = Form(5),
    audio: UploadFile = File(...),
):
    temp_path = None

    try:
        file_ext = audio.filename.split(".")[-1]
        temp_filename = f"{uuid.uuid4().hex}.{file_ext}"
        temp_path = os.path.join(TEMP_DIR, temp_filename)

        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(audio.file, buffer)

        transcript, stt_confidence = transcribe_audio(temp_path)
        print("[STT]", transcript, "| confidence:", stt_confidence)

        if stt_confidence < 0.4:
            raise HTTPException(
                status_code=400,
                detail="Audio not clear, please try again",
            )

        clean_text = normalize_text(
            text=transcript,
            stt_confidence=stt_confidence,
            llm_callable=None,
            confidence_threshold=0.75,
        )

        print("[CLEAN TEXT]", clean_text)

        doc_ids = _parse_allowed_document_ids(allowed_document_ids)
        if not doc_ids:
            raise HTTPException(
                status_code=400,
                detail=(
                    "allowed_document_ids required (same as context-aware POST /chat/). "
                    'Examples: ["2d7a7ccd-677f-40fc-81cd-ab144624f954"] or '
                    "2d7a7ccd-677f-40fc-81cd-ab144624f954"
                ),
            )

        payload = Payload(
            session_id=session_id,
            user_id=user_id,
            question=clean_text,
            allowed_document_ids=doc_ids,
            top_k=top_k,
        )
        result = handle_chat(payload)

        answer = result.get("answer", "")
        confidence_score = result.get("confidence_score", 0.0)
        citations = result.get("citations", [])
        citations = clean_citations(citations)

        print("[ANSWER]", answer)

        if not answer:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate answer",
            )

        # HybridTTS returns raw WAV bytes; piper/xtts backends may return (path, lang).
        tts_result = tts_engine.synthesize(answer)
        if isinstance(tts_result, bytes):
            out_name = f"{uuid.uuid4().hex}.wav"
            output_path = os.path.join(AUDIO_STATIC_DIR, out_name)
            with open(output_path, "wb") as f:
                f.write(tts_result)
        elif isinstance(tts_result, (tuple, list)) and len(tts_result) >= 1:
            output_path = tts_result[0]
        else:
            output_path = str(tts_result)

        audio_url = f"http://localhost:8000/{output_path}"

        return AskAudioResponse(
            session_id=session_id,
            transcription=transcript,
            clean_text=clean_text,
            answer_text=answer,
            audio_url=audio_url,
            confidence=round(confidence_score, 3),
            citations=citations,
            status="success",
        )

    except HTTPException as e:
        raise e

    except Exception as e:
        print("❌ ERROR:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
