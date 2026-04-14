# app/chunk_kg.py
#
# POST /chunk — parse file, chunk, run KG extraction + Neo4j upsert per chunk
# (no batch wait). Document must already exist in content.documents; chunks
# are NOT written to PostgreSQL.

import os
import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .router import validate_file, validate_file_type, route_file
from .text_cleaner import clean_text
from .chunker import chunk_text
from .file_loader import download_if_url
from .kg_extractor import extract_entities_and_relations
from .kg_store import (
    get_subject_title,
    merge_cross_subject_edges,
    resolve_document_by_file_path,
    save_graph,
    upsert_document_node,
    upsert_subject_node,
    upsert_user_node,
)

router = APIRouter()


class ChunkFilePayload(BaseModel):
    file_path: str = Field(..., description="Local path, URL, or document UUID")
    file_type: str


class KGUpdatePayload(BaseModel):
    entities: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]


class ChunkStepResponse(BaseModel):
    document_id: str
    subject_id: str
    chunk_id: str
    kg_update: KGUpdatePayload
    status: str


def _public_kg_update(entities: List[Dict], relationships: List[Dict]) -> Dict:
    ent_out = [
        {
            "name": e.get("name", ""),
            "type": e.get("type", "Unknown"),
        }
        for e in entities
    ]
    rel_out = [
        {
            "source":   r.get("source", ""),
            "relation": r.get("relation", ""),
            "target":   r.get("target", ""),
        }
        for r in relationships
    ]
    return {"entities": ent_out, "relationships": rel_out}


@router.post("/", response_model=List[ChunkStepResponse])
def chunk_file_and_incremental_kg(payload: ChunkFilePayload):
    """
    Resolve `document_id` / `subject_id` from `content.documents` using `file_path`
    (document must already exist — same as RAG registration). For each text chunk:
    assign an ephemeral `chunk_id` (not stored in Postgres), extract KG triples,
    save to Neo4j (dedup via MERGE), and link to entities in other documents in
    the same subject when names match.
    """
    local_file = None
    downloaded = False

    try:
        doc = resolve_document_by_file_path(payload.file_path)
        if not doc:
            raise HTTPException(
                status_code=404,
                detail=(
                    "No document found for file_path. Use document UUID, storage_path, "
                    "or filename registered in content.documents."
                ),
            )

        document_id = doc["document_id"]
        subject_id = doc["subject_id"]
        user_id = doc["user_id"]
        filename = doc.get("filename") or os.path.basename(payload.file_path)

        local_file = download_if_url(payload.file_path)
        downloaded = local_file != payload.file_path.strip()

        validate_file(local_file)
        validate_file_type(payload.file_type)

        raw_text = route_file(local_file, payload.file_type)
        if not raw_text.strip():
            raise HTTPException(status_code=400, detail="Extracted text is empty")

        cleaned = clean_text(raw_text)
        chunks = chunk_text(text=cleaned, source_type=payload.file_type)
        if not chunks:
            raise HTTPException(status_code=400, detail="Chunking produced zero chunks")

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

        results: List[ChunkStepResponse] = []
        prev_tail = ""

        for idx, ch in enumerate(chunks):
            text = (ch.get("text") or "").strip()
            if not text:
                continue

            chunk_id = str(uuid.uuid4())

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

            pub = _public_kg_update(ents, rels)
            results.append(
                ChunkStepResponse(
                    document_id=document_id,
                    subject_id=subject_id,
                    chunk_id=chunk_id,
                    kg_update=KGUpdatePayload(
                        entities=pub["entities"],
                        relationships=pub["relationships"],
                    ),
                    status="indexed",
                )
            )

        if not results:
            raise HTTPException(status_code=400, detail="All chunks were empty after processing")

        return results

    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chunk KG pipeline failed: {e}")

    finally:
        if downloaded and local_file and os.path.exists(local_file):
            try:
                os.remove(local_file)
            except OSError:
                pass