# app/kg.py

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import List, Dict, Optional

from .kg_pipeline import process_uploaded_file
from .kg_service import (
    KGValidationError,
    build_knowledge_graph,
    build_cross_document_relations,
    retrieve_subgraph_for_subject,
    focus_subgraph_for_query,
    subgraph_to_kg_context,
    generate_kg_answer,
    remove_document_graph,
    remove_subject_graph,
)
from .kg_store import (
    get_document_graph,
    get_subject_graph,
    get_cross_doc_relationships,
    get_document_cross_doc_links,
    list_kg_documents,
    list_kg_documents_for_subject,
)

router = APIRouter()

_MAX_UPLOAD_BYTES = 50 * 1024 * 1024   # 50 MB


# ════════════════════════════════════════════════════════════════
# Shared response models
# ════════════════════════════════════════════════════════════════

class EntityModel(BaseModel):
    name:        str
    type:        str
    document_id: Optional[str] = None


class RelationshipModel(BaseModel):
    source:     str
    relation:   str
    target:     str
    source_doc: Optional[str] = None
    target_doc: Optional[str] = None
    cross_doc:  Optional[bool] = False


class SubgraphResponse(BaseModel):
    entities:      List[EntityModel]
    relationships: List[RelationshipModel]


# ════════════════════════════════════════════════════════════════
# POST /kg/build
#
# Issue 1 fix:
#   Before writing anything to Neo4j, validate_build_ids() checks that
#   BOTH document_id and subject_id exist in PostgreSQL.
#   • Missing document_id → HTTP 404 with a clear message.
#   • Missing subject_id  → HTTP 404 with a clear message.
#   This prevents phantom nodes in Neo4j and gives the caller
#   actionable guidance ("process the document first").
# ════════════════════════════════════════════════════════════════

class BuildKGResponse(BaseModel):
    document_id:         str
    subject_id:          str
    filename:            str
    file_type:           str
    chunks_processed:    int
    entities_saved:      int
    relationships_saved: int


@router.post(
    "/build",
    response_model=BuildKGResponse,
    summary="Upload a document and index it into the KG",
)
async def build_kg(
    file: UploadFile = File(
        ...,
        description="Document to index (PDF, DOCX, DOC, PPTX, TXT, CSV)",
    ),
    document_id: str = Form(
        ...,
        description=(
            "UUID of the document — must already exist in content.documents. "
            "Upload and process it through the RAG /extract endpoint first."
        ),
    ),
    user_id: str = Form(..., description="UUID of the owning user"),
    subject_id: str = Form(
        ...,
        description=(
            "UUID of the subject — must already exist in content.subjects. "
            "Create it through the main API first."
        ),
    ),
    subject_name: str = Form(
        default="",
        description="Human-readable label, e.g. 'Data Structures'",
    ),
    doc_order: int = Form(
        default=0,
        description="Position within the subject (0-indexed). Used for cross-doc ordering.",
    ),
) -> BuildKGResponse:
    """
    **Full KG indexing pipeline in one Swagger call:**

    1. Validate `document_id` exists in `content.documents` → 404 if not  
    2. Validate `subject_id` exists in `content.subjects` → 404 if not  
    3. Receive the uploaded file and detect its type  
    4. Parse → clean → chunk the file (same parsers as RAG /extract)  
    5. Run Groq LLM extraction on every chunk — domain-specific entity and relationship types  
    6. Persist `User → Subject → Document → Entity` hierarchy in Neo4j  

    After indexing all documents in a subject, call  
    **POST /kg/build-cross-doc** to detect cross-lecture relationships.
    """

    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(file_bytes) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {_MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit.",
        )

    # ── Parse / chunk ─────────────────────────────────────────
    try:
        chunks, file_type = process_uploaded_file(
            file_bytes=file_bytes,
            filename=file.filename or "upload",
            content_type=file.content_type or "",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"File processing failed: {exc}")

    # ── Build KG (validates IDs first — Issue 1) ──────────────
    try:
        result = build_knowledge_graph(
            chunks=chunks,
            document_id=document_id,
            user_id=user_id,
            subject_id=subject_id,
            subject_name=subject_name or (file.filename or ""),
            filename=file.filename or "",
            doc_order=doc_order,
        )
    except KGValidationError as exc:
        # ID not found in PostgreSQL → 404 with precise message
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"KG construction failed: {exc}")

    return BuildKGResponse(
        document_id=result["document_id"],
        subject_id=result["subject_id"],
        filename=file.filename or "",
        file_type=file_type,
        chunks_processed=len(chunks),
        entities_saved=result["entities_saved"],
        relationships_saved=result["relationships_saved"],
    )


# ════════════════════════════════════════════════════════════════
# POST /kg/build-cross-doc
#
# What this does (Issue 3 answer):
#   1. Reads all non-deleted documents for the subject from PostgreSQL
#      (ordered by upload_time = lecture order).
#   2. For ≤ 10 docs: compares ALL unique ordered pairs.
#      For > 10 docs: consecutive pairs only (scalable).
#   3. For each pair: fetches entity name lists from Neo4j, then calls
#      the LLM cross-doc extraction prompt.
#   4. Stores results as semantic-label edges with cross_doc=true property
#      (visible in Neo4j UI as e.g. PREREQUISITE_TO, BUILDS_UPON).
#   5. Also creates coarser Document-level edges of the same type.
# ════════════════════════════════════════════════════════════════

class BuildCrossDocRequest(BaseModel):
    subject_id: str
    user_id:    str


class BuildCrossDocResponse(BaseModel):
    subject_id:                    str
    documents_processed:           int
    pairs_compared:                int
    cross_doc_relationships_saved: int


@router.post(
    "/build-cross-doc",
    response_model=BuildCrossDocResponse,
    summary="Build cross-document relationships for a subject",
)
def build_cross_doc(payload: BuildCrossDocRequest):
    """
    Detects and stores cross-lecture relationships across all documents
    in a subject (PREREQUISITE_TO, BUILDS_UPON, EXTENDS, etc.).

    Call once after all documents in a subject have been indexed.
    Safe to re-run — existing edges are merged, not duplicated.
    """
    try:
        return build_cross_document_relations(
            subject_id=payload.subject_id,
            user_id=payload.user_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ════════════════════════════════════════════════════════════════
# POST /kg/query/subject
# ════════════════════════════════════════════════════════════════

class SubjectQueryRequest(BaseModel):
    question:     str
    subject_id:   str
    user_id:      str
    document_ids: Optional[List[str]] = None
    hops:         int = 2


@router.post(
    "/query/subject",
    response_model=SubgraphResponse,
    summary="Query subgraph scoped to a subject",
)
def query_subgraph_subject(payload: SubjectQueryRequest):
    """
    Returns ONLY entities reachable within `hops` steps from the entities
    named in the question. The `hops` parameter is enforced strictly —
    unrelated entities from the same document are excluded.

    Set `hops=1` for immediate neighbours only.
    Set `hops=2` (default) for neighbours-of-neighbours.
    """
    try:
        return retrieve_subgraph_for_subject(
            question=payload.question,
            subject_id=payload.subject_id,
            user_id=payload.user_id,
            document_ids=payload.document_ids,
            hops=payload.hops,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ════════════════════════════════════════════════════════════════
# POST /kg/answer/subject
# ════════════════════════════════════════════════════════════════

class SubjectAnswerRequest(BaseModel):
    question:     str
    subject_id:   str
    user_id:      str
    document_ids: Optional[List[str]] = None
    hops:         int = 2


class KGAnswerContextEntity(BaseModel):
    id:    str
    label: str
    type:  str


class KGAnswerContextRelationship(BaseModel):
    source:   str
    relation: str
    target:   str


class KGAnswerContextPayload(BaseModel):
    entities:      List[KGAnswerContextEntity]
    relationships: List[KGAnswerContextRelationship]


class KGAnswerResponse(BaseModel):
    answer:         str
    kg_context:     KGAnswerContextPayload
    entities_used:  int
    relations_used: int


@router.post(
    "/answer/subject",
    response_model=KGAnswerResponse,
    summary="Generate KG-grounded answer for a subject",
)
def kg_answer_subject(payload: SubjectAnswerRequest):
    """
    Retrieves the hop-bounded subgraph for the question and generates
    a natural-language answer.

    The answer prompt uses entity types AND relationship semantics to
    answer descriptive questions ("what is X?") even without free text.
    Returns "I don't know." only when the entity has no graph context at all.

    `kg_context` is structured JSON (entity ids, labels, types; edges by id) for visualization.
    """
    try:
        subgraph = retrieve_subgraph_for_subject(
            question=payload.question,
            subject_id=payload.subject_id,
            user_id=payload.user_id,
            document_ids=payload.document_ids,
            hops=payload.hops,
        )
        focused = focus_subgraph_for_query(subgraph, payload.question)
        ctx = subgraph_to_kg_context(focused)
        return {
            "answer":         generate_kg_answer(payload.question, focused),
            "kg_context":     ctx,
            "entities_used":  len(ctx["entities"]),
            "relations_used": len(ctx["relationships"]),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ════════════════════════════════════════════════════════════════
# GET /kg/subject/{subject_id}
# ════════════════════════════════════════════════════════════════

@router.get(
    "/subject/{subject_id}",
    response_model=SubgraphResponse,
    summary="Get full subject graph",
)
def get_subject_kg(subject_id: str, user_id: str):
    """Every entity and relationship (intra + cross-doc) for a subject."""
    try:
        return get_subject_graph(subject_id=subject_id, user_id=user_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ════════════════════════════════════════════════════════════════
# GET /kg/document/{document_id}
# ════════════════════════════════════════════════════════════════

@router.get(
    "/document/{document_id}",
    response_model=SubgraphResponse,
    summary="Get full document graph",
)
def get_document_kg(document_id: str, user_id: str):
    """Every entity and intra-doc relationship for one document."""
    try:
        return get_document_graph(document_id=document_id, user_id=user_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ════════════════════════════════════════════════════════════════
# GET /kg/cross-doc/subject/{subject_id}
# ════════════════════════════════════════════════════════════════

class CrossDocRelModel(BaseModel):
    source:     str
    relation:   str
    target:     str
    source_doc: str
    target_doc: str


class CrossDocResponse(BaseModel):
    subject_id:    str
    relationships: List[CrossDocRelModel]


@router.get(
    "/cross-doc/subject/{subject_id}",
    response_model=CrossDocResponse,
    summary="Get all cross-document relationships for a subject",
)
def get_cross_doc_subject(subject_id: str, user_id: str):
    """All cross-lecture semantic edges within the subject."""
    try:
        rels = get_cross_doc_relationships(subject_id=subject_id, user_id=user_id)
        return {"subject_id": subject_id, "relationships": rels}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ════════════════════════════════════════════════════════════════
# GET /kg/cross-doc/document/{document_id}
# ════════════════════════════════════════════════════════════════

class DocumentCrossDocResponse(BaseModel):
    document_id:   str
    relationships: List[CrossDocRelModel]


@router.get(
    "/cross-doc/document/{document_id}",
    response_model=DocumentCrossDocResponse,
    summary="Get cross-document relationships for a document",
)
def get_cross_doc_document(document_id: str, user_id: str):
    """All cross-doc edges where this document is source or target."""
    try:
        rels = get_document_cross_doc_links(document_id=document_id, user_id=user_id)
        return {"document_id": document_id, "relationships": rels}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ════════════════════════════════════════════════════════════════
# GET /kg/documents
# ════════════════════════════════════════════════════════════════

class ListDocumentsResponse(BaseModel):
    user_id:      str
    document_ids: List[str]


@router.get(
    "/documents",
    response_model=ListDocumentsResponse,
    summary="List documents with a KG",
)
def list_documents(user_id: str):
    try:
        return {"user_id": user_id, "document_ids": list_kg_documents(user_id=user_id)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ════════════════════════════════════════════════════════════════
# GET /kg/documents/subject/{subject_id}
# ════════════════════════════════════════════════════════════════

class ListSubjectDocumentsResponse(BaseModel):
    subject_id:   str
    user_id:      str
    document_ids: List[str]


@router.get(
    "/documents/subject/{subject_id}",
    response_model=ListSubjectDocumentsResponse,
    summary="List documents with a KG for a subject",
)
def list_subject_documents(subject_id: str, user_id: str):
    try:
        doc_ids = list_kg_documents_for_subject(subject_id=subject_id, user_id=user_id)
        return {"subject_id": subject_id, "user_id": user_id, "document_ids": doc_ids}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ════════════════════════════════════════════════════════════════
# DELETE /kg/document/{document_id}
# ════════════════════════════════════════════════════════════════

class DeleteKGResponse(BaseModel):
    document_id:   str
    deleted_nodes: int


@router.delete(
    "/document/{document_id}",
    response_model=DeleteKGResponse,
    summary="Delete document KG",
)
def delete_document_kg(document_id: str, user_id: str):
    """
    Removes all Entity nodes (and their edges) for a single document.
    Also removes the orphaned Document node if no entities remain.
    PostgreSQL data is NOT affected.
    """
    try:
        deleted = remove_document_graph(document_id=document_id, user_id=user_id)
        return {"document_id": document_id, "deleted_nodes": deleted}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ════════════════════════════════════════════════════════════════
# DELETE /kg/subject/{subject_id}
#
# Issue 6 fix (cascading delete):
#   Deletes: Entity nodes → Document nodes → Subject node
#   DETACH DELETE on entities removes all their edges automatically.
#   PostgreSQL data is NOT affected.
# ════════════════════════════════════════════════════════════════

class DeleteSubjectKGResponse(BaseModel):
    subject_id:    str
    deleted_nodes: int


@router.delete(
    "/subject/{subject_id}",
    response_model=DeleteSubjectKGResponse,
    summary="Delete entire subject KG",
)
def delete_subject_kg(subject_id: str, user_id: str):
    """
    Cascading delete for an entire subject:
    Entities → Documents → Subject node are all removed from Neo4j.
    PostgreSQL data (content.subjects, content.documents) is NOT touched.
    """
    try:
        deleted = remove_subject_graph(subject_id=subject_id, user_id=user_id)
        return {"subject_id": subject_id, "deleted_nodes": deleted}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))