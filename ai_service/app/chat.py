# app/chat.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from uuid import UUID

from .chat_service import handle_chat

router = APIRouter()


class ChatRequest(BaseModel):
    session_id: UUID
    question: str
    top_k: int = 5


class Citation(BaseModel):
    document_id: str
    page_start: int | None
    page_end: int | None


class ChatResponse(BaseModel):
    answer: str
    citations: List[Citation]


@router.post("/", response_model=ChatResponse)
def chat(payload: ChatRequest):
    try:
        return handle_chat(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))