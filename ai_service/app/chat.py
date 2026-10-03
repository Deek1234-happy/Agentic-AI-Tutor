# app/chat.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Literal
from uuid import UUID

from .chat_service import handle_chat

router = APIRouter()


class ChatRequest(BaseModel):
    session_id: UUID
    user_id: UUID
    question: str
    allowed_document_ids: List[UUID]
    top_k: int = 5
    language: Literal["en", "kn", "hi", "ml", "ta", "te"] = "en"


class Citation(BaseModel):
    document_id: str
    chunk_id: str
    page_start: int | None
    page_end: int | None


class KGContextEntity(BaseModel):
    id: str
    label: str
    type: str


class KGContextRelationship(BaseModel):
    source: str
    relation: str
    target: str


class KGContextPayload(BaseModel):
    entities: List[KGContextEntity]
    relationships: List[KGContextRelationship]


class ChatResponse(BaseModel):
    answer: str
    confidence_score: float
    citations: List[Citation]
    kg_context: KGContextPayload
    entities_used: int
    relations_used: int


@router.post("/", response_model=ChatResponse)
def chat(payload: ChatRequest):

    try:
        return handle_chat(payload)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))