from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

from .embedding import embed_texts
from .vector_store import search_similar_chunks, get_all_chunks
from .reranker import rerank_chunks
from rank_bm25 import BM25Okapi
import re


# ─────────────────────────────
# Tokenizer
# ─────────────────────────────
def tokenize(text):
    return re.findall(r"\w+", text.lower())


# ─────────────────────────────
# BM25 Globals
# ─────────────────────────────
ALL_CHUNKS = []
bm25 = None
bm25_user_id = None

def init_bm25(user_id):
    global ALL_CHUNKS, bm25, bm25_user_id

    ALL_CHUNKS = get_all_chunks(user_id)

    corpus = [
        f"{c['source_title']} {c['text']}"
        for c in ALL_CHUNKS
    ]
    tokenized = [tokenize(t) for t in corpus]

    bm25 = BM25Okapi(tokenized)
    bm25_user_id = user_id


def bm25_search(query, k=50, allowed_document_ids=None):
    if bm25 is None:
        return []

    allowed = set(allowed_document_ids or [])
    tokenized_query = tokenize(query)
    scores = bm25.get_scores(tokenized_query)

    candidate_indices = range(len(scores))
    if allowed:
        candidate_indices = [
            i for i, chunk in enumerate(ALL_CHUNKS)
            if str(chunk["document_id"]) in allowed
        ]

    top_indices = sorted(candidate_indices, key=lambda i: scores[i], reverse=True)[:k]

    results = []
    for rank, i in enumerate(top_indices, start=1):
        chunk = ALL_CHUNKS[i]
        results.append((
            chunk["chunk_id"],
            chunk["document_id"],
            chunk["text"],
            chunk["page_start"],
            chunk["page_end"],
            float(scores[i]),
            chunk["source_title"],
            rank,
        ))

    return results


def dense_search(query, user_id, allowed_document_ids, k=50):
    query_embedding = embed_texts([query], is_query=True)[0]

    results = search_similar_chunks(
        query_embedding=query_embedding,
        allowed_document_ids=allowed_document_ids,
        user_id=user_id,
        top_k=k,
    )

    return [
        (*chunk, rank)
        for rank, chunk in enumerate(results, start=1)
    ]


def reciprocal_rank_fusion(dense_results, bm25_results, k=60):
    combined = {}

    def add_results(results, source):
        for item in results:
            chunk = item[:7]
            rank = item[7]
            chunk_id = str(chunk[0])

            if chunk_id not in combined:
                combined[chunk_id] = {
                    "chunk": chunk,
                    "score": 0.0,
                    "dense_rank": None,
                    "bm25_rank": None,
                }

            combined[chunk_id]["score"] += 1.0 / (k + rank)
            combined[chunk_id][f"{source}_rank"] = rank

    add_results(dense_results, "dense")
    add_results(bm25_results, "bm25")

    fused = sorted(
        combined.values(),
        key=lambda x: x["score"],
        reverse=True,
    )

    return [
        (
            item["chunk"][0],
            item["chunk"][1],
            item["chunk"][2],
            item["chunk"][3],
            item["chunk"][4],
            item["score"],
            item["chunk"][6],
        )
        for item in fused
    ]




# ─────────────────────────────
# API
# ─────────────────────────────
router = APIRouter()


class SearchPayload(BaseModel):
    query: str
    top_k: int = 5
    user_id: Optional[str] = None
    allowed_document_ids: Optional[List[str]] = None


class SearchResponse(BaseModel):
    chunk_id: str
    document_id: str
    text: str
    page_start: int | None
    page_end: int | None
    score: float
    rerank_score: float | None = None
    final_score: float | None = None
    source_title: str


@router.post("/", response_model=List[SearchResponse])
def semantic_search(payload: SearchPayload):

    user_id = payload.user_id or "00000000-0000-0000-0000-000000000000"
    allowed_document_ids = payload.allowed_document_ids or []
    retrieval_k = max(50, payload.top_k * 5)
    rerank_k = max(20, payload.top_k * 2)

    if bm25 is None or bm25_user_id != user_id:
        init_bm25(user_id)

    dense_results = dense_search(
        query=payload.query,
        user_id=user_id,
        allowed_document_ids=allowed_document_ids,
        k=retrieval_k,
    )

    bm25_results = bm25_search(
        query=payload.query,
        allowed_document_ids=allowed_document_ids,
        k=retrieval_k,
    )

    results = reciprocal_rank_fusion(
        dense_results=dense_results,
        bm25_results=bm25_results,
    )[:rerank_k]

    # Re-rank fused dense + BM25 candidates.
    results = rerank_chunks(
        question=payload.query,
        chunks=results,
        top_k=payload.top_k
    )

    return [
        {
            "chunk_id": str(r[0]),
            "document_id": str(r[1]),
            "text": r[2],
            "page_start": r[3],
            "page_end": r[4],
            "score": float(r[5]),
            "rerank_score": float(r[7]) if len(r) > 7 else None,
            "final_score": float(r[8]) if len(r) > 8 else None,
            "source_title": r[6],
        }
        for r in results
    ]
