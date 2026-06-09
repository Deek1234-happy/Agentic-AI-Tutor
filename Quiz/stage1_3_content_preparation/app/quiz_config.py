# app/quiz_config.py
"""
Single source of truth for all chunking parameters.
To tune the pipeline, edit values HERE only.
These values flow to quiz_engine.py (cleaner, chunker, validator, postprocessor).
"""

from dataclasses import dataclass


@dataclass
class ChunkingConfig:

    # ── Embedding model ───────────────────────────────────────────────────────
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # ── Semantic similarity thresholds ────────────────────────────────────────
    similarity_threshold: float = 0.68
    window_size: int = 3
    breakpoint_percentile: float = 75.0

    # ── Dynamic similarity (adaptive breakpoints) ─────────────────────────────
    # True  = mean-std method (recommended for slides)
    # False = percentile method (recommended for books)
    dynamic_similarity: bool = True
    similarity_std_factor: float = 0.5

    # ── Size constraints (tokens ≈ chars/4) ───────────────────────────────────
    min_chunk_tokens: int = 60
    max_chunk_tokens: int = 300
    target_chunk_tokens: int = 160

    # ── Sentence constraints ──────────────────────────────────────────────────
    min_sentence_length: int = 15
    max_sentence_length: int = 1000
    min_sentences_per_chunk: int = 2
    max_sentences_per_chunk: int = 12

    # ── Overlap ───────────────────────────────────────────────────────────────
    overlap_sentences: int = 0

    # ── Merging ───────────────────────────────────────────────────────────────
    merge_orphans: bool = True
    prevent_large_merge: bool = True
    max_merge_tokens: int = 280

    # ── Structural ────────────────────────────────────────────────────────────
    respect_headings: bool = True

    # ── Quality gate ──────────────────────────────────────────────────────────
    quality_score_threshold: float = 0.50

    # ── Semantic floor ────────────────────────────────────────────────────────
    min_semantic_score: float = 0.20

    # ── Output ────────────────────────────────────────────────────────────────
    output_dir: str = "chunks_output"
    pretty_json: bool = True


@dataclass
class CleaningConfig:
    remove_headers_footers: bool = True
    remove_page_numbers: bool = True
    normalize_unicode: bool = True
    fix_hyphenation: bool = True
    normalize_whitespace: bool = True
    remove_boilerplate: bool = True
    min_line_length: int = 20
    preserve_tables: bool = True
    language: str = "english"