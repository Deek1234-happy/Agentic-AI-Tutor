# app/chunk_kg.py
#
# POST /chunk — use existing DB chunks and run incremental KG extraction.
# No file parsing/chunk generation and no chunk writes to PostgreSQL.

from typing import Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .kg_extractor import extract_entities_and_relations
from .kg_store import (
    get_existing_chunks_for_document,
    get_subject_title,
    get_subject_for_document,
    merge_cross_subject_edges,
    save_graph,
    upsert_document_node,
    upsert_subject_node,
    upsert_user_node,
)

router = APIRouter()


class ChunkFilePayload(BaseModel):
    file_id: str = Field(..., description="Document UUID in content.documents")


class StatusResponse(BaseModel):
    status: str


@router.post("/", response_model=StatusResponse)
def chunk_file_and_incremental_kg(payload: ChunkFilePayload):
    """
    Resolve metadata from `content.documents` using `file_id`, read existing chunks
    from `content.document_chunks`, extract KG triples per chunk,
    save to Neo4j (dedup via MERGE), and link to entities in other documents in
    the same subject when names match.
    """
    try:
        document_id = str(payload.file_id).strip()
        if not document_id:
            raise HTTPException(status_code=400, detail="file_id is required")

        doc = get_subject_for_document(document_id)
        if not doc or not doc.get("subject_id") or not doc.get("user_id"):
            raise HTTPException(
                status_code=404,
                detail="No document found for file_id in content.documents.",
            )

        subject_id = doc["subject_id"]
        user_id = doc["user_id"]
        filename = document_id

        chunks = get_existing_chunks_for_document(document_id)
        if not chunks:
            raise HTTPException(
                status_code=404,
                detail="No existing chunks found for file_id in content.document_chunks.",
            )

        subject_name = get_subject_title(subject_id)

        upsert_user_node(user_id)
        upsert_subject_node(
            subject_id=subject_id,
            subject_name=subject_name,
            user_id=user_id,
        )
        upsert_document_node(
            document_id=document_id,
            filename=filename,
            subject_id=subject_id,
            user_id=user_id,
            doc_order=0,
        )

        processed = 0
        prev_tail = ""

        for idx, ch in enumerate(chunks):
            text = (ch.get("text") or "").strip()
            if not text:
                continue

            chunk_id = str(ch.get("chunk_id") or "")
            if not chunk_id:
                continue

            extracted = extract_entities_and_relations(
                text=text,
                document_id=document_id,
                subject_id=subject_id,
                user_id=user_id,
                chunk_index=idx,
                previous_chunk_tail=prev_tail,
            )

            ents = extracted.get("entities") or []
            rels = extracted.get("relationships") or []

            save_graph(entities=ents, relationships=rels)
            merge_cross_subject_edges(
                user_id=user_id,
                subject_id=subject_id,
                current_document_id=document_id,
                relationships=rels,
            )

            prev_tail = text[-800:] if len(text) > 800 else text

            processed += 1

        if processed == 0:
            raise HTTPException(status_code=400, detail="All chunks were empty after processing")

        return StatusResponse(status="success")

    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        return StatusResponse(status="failed")