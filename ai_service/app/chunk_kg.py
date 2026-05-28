# app/chunk_kg.py
#
# POST /chunk — use existing DB chunks and run incremental KG extraction.
# No file parsing/chunk generation and no chunk writes to PostgreSQL.

from typing import Dict, List
from .kg_chunking_strategy import chunk_document_for_kg
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .kg_extractor import extract_entities_and_relations
from .kg_checkpoint import (
    clear_checkpoint,
    load_checkpoint,
    mark_checkpoint_completed,
    mark_checkpoint_failed,
    mark_checkpoint_processing,
    save_checkpoint,
)
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
    kg_completed: bool = False
    document_id: str | None = None
    total_chunks: int | None = None
    last_completed_chunk_index: int | None = None


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
        # Re-chunk the document with KG-optimized config (larger, no overlap) > to fix kg
        raw_text = " ".join(
            (ch.get("text") or "").strip() for ch in chunks
        )
        kg_chunks = chunk_document_for_kg(raw_text)
        ########################################################
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
        cp = load_checkpoint(document_id)
        cp.total_chunks = len(kg_chunks)
        mark_checkpoint_processing(cp)
        # Default behavior:
        # - If last run stopped mid-way, resume from the next unprocessed chunk.
        # - Otherwise (no checkpoint / completed / chunk-count mismatch), start fresh.
        if (
            cp.total_chunks is not None
            and cp.total_chunks == len(kg_chunks)
            and int(cp.last_completed_chunk_index) < (len(kg_chunks) - 1)
        ):
            start_idx = max(-1, int(cp.last_completed_chunk_index)) + 1
        else:
            clear_checkpoint(document_id)
            cp = load_checkpoint(document_id)
            cp.total_chunks = len(kg_chunks)
            start_idx = 0
        prev_tail = cp.previous_chunk_tail or ""

        # Resume case: checkpoint says all chunks are already processed.
        if start_idx >= len(kg_chunks):
            mark_checkpoint_completed(cp)
            return StatusResponse(
                status="success",
                kg_completed=True,
                document_id=document_id,
                total_chunks=len(kg_chunks),
                last_completed_chunk_index=cp.last_completed_chunk_index,
            )

        # for idx, ch in enumerate(chunks):
        #     if idx < start_idx:
        #         continue
        #     text = (ch.get("text") or "").strip()
        #     if not text:
        #         continue

        #     chunk_id = str(ch.get("chunk_id") or "")
        #     if not chunk_id:
        #         continue
        for idx, chunk_text in enumerate(kg_chunks):
            if idx < start_idx:
                continue
            text = chunk_text.strip()
            if not text:
                continue
            chunk_id = f"kg_chunk_{document_id}_{idx}"

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
            cp.last_completed_chunk_index = idx
            cp.previous_chunk_tail = prev_tail
            save_checkpoint(cp)

        if processed == 0:
            # Either all remaining chunks were empty, or there was nothing to do.
            # Do not fail the request in resume mode.
            if start_idx > 0:
                mark_checkpoint_completed(cp)
                return StatusResponse(
                    status="success",
                    kg_completed=True,
                    document_id=document_id,
                    total_chunks=len(kg_chunks),
                    last_completed_chunk_index=cp.last_completed_chunk_index,
                )
            raise HTTPException(status_code=400, detail="All chunks were empty after processing")

        mark_checkpoint_completed(cp)
        return StatusResponse(
            status="success",
            kg_completed=True,
            document_id=document_id,
            total_chunks=len(kg_chunks),
            last_completed_chunk_index=cp.last_completed_chunk_index,
        )

    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        try:
            mark_checkpoint_failed(load_checkpoint(str(payload.file_id)))
        except Exception:
            pass
        return StatusResponse(status="failed", document_id=str(payload.file_id))
