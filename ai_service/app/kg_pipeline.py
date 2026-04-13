# app/kg_pipeline.py
"""
Internal pipeline used exclusively by the KG upload endpoint.

Responsibilities
────────────────
1. Save the uploaded bytes to a temp file
2. Parse raw text  (reuses RAG parsers — imported read-only, never modified)
3. Clean the text  (reuses RAG text_cleaner)
4. Chunk the text  (reuses RAG chunker)
5. Return the chunk list so kg_service.build_knowledge_graph() can consume it

Nothing in this file modifies any RAG module.
"""

import os
import tempfile
from typing import List, Dict, Tuple

# ── Reuse RAG modules read-only ───────────────────────────────────────────────
from .router       import route_file, validate_file_type   # dispatch to correct parser
from .text_cleaner import clean_text                        # normalise OCR/whitespace
from .chunker      import chunk_text                        # dynamic chunking
# ─────────────────────────────────────────────────────────────────────────────

# File types the KG upload endpoint will accept
KG_SUPPORTED_TYPES: Dict[str, str] = {
    "application/pdf":                                                      "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/msword":                                                   "docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "application/vnd.ms-powerpoint":                                        "pptx",
    "text/plain":                                                            "txt",
    "text/csv":                                                              "csv",
    "application/csv":                                                       "csv",
}

# Extension → file_type fallback (when content-type is generic)
KG_EXT_MAP: Dict[str, str] = {
    ".pdf":  "pdf",
    ".docx": "docx",
    ".doc":  "docx",
    ".pptx": "pptx",
    ".ppt":  "pptx",
    ".txt":  "txt",
    ".csv":  "csv",
}


def resolve_file_type(filename: str, content_type: str) -> str:
    """
    Determine the logical file type from MIME type first, then extension.
    Raises ValueError for unsupported types.
    """
    # 1. Try MIME type
    if content_type and content_type in KG_SUPPORTED_TYPES:
        return KG_SUPPORTED_TYPES[content_type]

    # 2. Fall back to extension
    _, ext = os.path.splitext(filename.lower())
    if ext in KG_EXT_MAP:
        return KG_EXT_MAP[ext]

    raise ValueError(
        f"Unsupported file type '{ext}'. "
        f"Supported: {', '.join(sorted(set(KG_EXT_MAP.keys())))}"
    )


def process_uploaded_file(
    file_bytes:   bytes,
    filename:     str,
    content_type: str,
) -> Tuple[List[Dict], str]:
    """
    Full parse → clean → chunk pipeline for an uploaded file.

    Returns
    -------
    chunks      : list of chunk dicts (same shape as the RAG chunker output)
    file_type   : resolved type string, e.g. "pdf"

    The caller is responsible for passing `chunks` to
    kg_service.build_knowledge_graph().
    """

    # ── 1. Resolve & validate type ────────────────────────────────────────────
    file_type = resolve_file_type(filename, content_type)

    # Double-check against RAG's own validation to stay consistent
    validate_file_type(file_type)

    # ── 2. Write bytes to a temp file ─────────────────────────────────────────
    suffix     = f".{file_type}"
    tmp_path   = None

    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
        ) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        # ── 3. Parse raw text ─────────────────────────────────────────────────
        raw_text = route_file(tmp_path, file_type)

        if not raw_text or not raw_text.strip():
            raise ValueError("No text could be extracted from the uploaded file.")

        # ── 4. Clean ──────────────────────────────────────────────────────────
        cleaned_text = clean_text(raw_text)

        # ── 5. Chunk ──────────────────────────────────────────────────────────
        chunks = chunk_text(
            text=cleaned_text,
            source_type=file_type,
        )

        if not chunks:
            raise ValueError("Document produced zero chunks after processing.")

        return chunks, file_type

    finally:
        # Always remove the temp file even if an exception was raised
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)