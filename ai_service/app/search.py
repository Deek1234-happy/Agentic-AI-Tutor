# app/search.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

from .embedding import embed_texts
from .vector_store import search_similar_chunks

router = APIRouter()


class SearchPayload(BaseModel):
    query: str
    top_k: int = 5


class SearchResponse(BaseModel):
    chunk_id: str
    document_id: str
    text: str
    page_start: int | None
    page_end: int | None
    score: float


@router.post("/", response_model=List[SearchResponse])
def semantic_search(payload: SearchPayload):

    query_embedding = embed_texts([payload.query])[0]

    results = search_similar_chunks(
        query_embedding=query_embedding,
        top_k=payload.top_k
    )

    return [
        {
            "chunk_id": str(r[0]),
            "document_id": str(r[1]),
            "text": r[2],
            "page_start": r[3],
            "page_end": r[4],
            "score": float(r[5])
        }
        for r in results
    ]
