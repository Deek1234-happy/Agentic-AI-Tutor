# app/kg_chunking_strategy.py

import re
from .chunker import SemanticChunker, ChunkingConfig
from .kg_chunker_config import (
    KG_SINGLE_CHUNK_THRESHOLD_SENTENCES,
    KG_MAX_CHUNKS_PER_DOCUMENT,
)

# Separate instance from the RAG singleton — does NOT touch _chunker_singleton
_kg_chunker = SemanticChunker(ChunkingConfig(
    similarity_threshold=0.82,
    similarity_std_factor=1.5,
    max_sentences_per_chunk=25,
    overlap_sentences=0,       # critical — zero overlap for KG
    min_chunk_tokens=25,
    max_chunk_tokens=2000,
    min_words=10,
    max_words=1200,
    dynamic_similarity=True,
    merge_orphans=True,
    dedup_similarity_threshold=0.98,
))


def chunk_document_for_kg(raw_text: str) -> list[str]:
    """
    Returns plain text strings — one per KG chunk.
    Uses larger chunks, no overlap, less aggressive splitting.
    """
    # count sentences to decide if splitting is even needed
    sentences = [
        s.strip()
        for s in re.split(r'(?<=[.!?])\s+', raw_text.strip())
        if s.strip()
    ]

    if len(sentences) <= KG_SINGLE_CHUNK_THRESHOLD_SENTENCES:
        # tiny document — treat as single chunk, skip all splitting
        return [raw_text.strip()]

    chunks = _kg_chunker.chunk(raw_text)
    texts = [c.text for c in chunks if c.text.strip()]

    if len(texts) > KG_MAX_CHUNKS_PER_DOCUMENT:
        texts = _force_merge(texts, KG_MAX_CHUNKS_PER_DOCUMENT)

    return texts


def _force_merge(chunks: list[str], max_chunks: int) -> list[str]:
    while len(chunks) > max_chunks:
        min_idx = min(
            range(len(chunks) - 1),
            key=lambda i: len(chunks[i]) + len(chunks[i + 1])
        )
        merged = chunks[min_idx] + " " + chunks[min_idx + 1]
        chunks = chunks[:min_idx] + [merged] + chunks[min_idx + 2:]
    return chunks