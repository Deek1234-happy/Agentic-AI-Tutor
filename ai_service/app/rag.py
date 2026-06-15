# app/rag.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

from .rag_service import answer_question, IDK_MESSAGE

router = APIRouter()


class RAGPayload(BaseModel):
    question: str
    top_k: int = 5


class Citation(BaseModel):
    document_id: str
    page_start: int
    page_end: int


class RAGResponse(BaseModel):
    answer: str
    citations: List[Citation]


@router.post("/", response_model=RAGResponse)
def rag_answer(payload: RAGPayload):

    try:
        answer, retrieved = answer_question(
            payload.question,
            payload.top_k
        )

        citations = [
            {
                "document_id": str(r[1]),
                "page_start": r[3],
                "page_end": r[4]
            }
            for r in retrieved
        ]

        return {
            "answer": answer,
            "citations": citations
        }

    except Exception:
        return {
            "answer": IDK_MESSAGE,
            "citations": []
        }