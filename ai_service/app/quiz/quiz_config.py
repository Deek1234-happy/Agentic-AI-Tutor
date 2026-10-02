# app/quiz/quiz_config.py
"""
Single source of truth for all quiz pipeline parameters.

To tune the pipeline, edit values HERE only.
These values flow into quiz_cleaner.py, quiz_chunker.py, and quiz_metadata.py.

Kept deliberately separate from the RAG ChunkingConfig in app/chunker.py so
that quiz and RAG pipelines can be tuned independently without risk of
accidentally affecting each other.
"""

import os
from dataclasses import dataclass


DEFAULT_QUIZ_GROQ_MODELS = (
    "qwen/qwen3.8-27b",
    "groq/compound",
    "groq/compound-mini",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
)


def _resolve_quiz_groq_models() -> tuple:
    """Prefer an explicit env override, otherwise use the safe default order."""
    env_value = os.getenv("GROQ_QUIZ_MODELS") or os.getenv("LLM_MODEL")
    if env_value:
        parsed = [item.strip() for item in env_value.split(",") if item.strip()]
        if parsed:
            return tuple(parsed)
    return DEFAULT_QUIZ_GROQ_MODELS


# ═══════════════════════════════════════════════════════════════
# CLEANING CONFIG
# ═══════════════════════════════════════════════════════════════

@dataclass
class QuizCleaningConfig:
    """
    Controls the quiz-specific text cleaner (quiz_cleaner.py).

    Identical fields to the RAG CleaningConfig.  The key behavioural
    difference is NOT here — it is in quiz_cleaner.py's _remove_page_markers()
    which strips __PGNUM_N__ completely instead of preserving them.
    """
    remove_headers_footers: bool = True
    remove_page_numbers: bool = True
    normalize_unicode: bool = True
    fix_hyphenation: bool = True
    normalize_whitespace: bool = True
    remove_boilerplate: bool = True
    min_line_length: int = 20
    preserve_tables: bool = True
    language: str = "english"


# ═══════════════════════════════════════════════════════════════
# CHUNKING CONFIG
# ═══════════════════════════════════════════════════════════════

@dataclass
class QuizChunkingConfig:
    """
    Controls the quiz-specific semantic chunker (quiz_chunker.py).

    Notable differences from RAG ChunkingConfig:
      - min_chunk_tokens  : 60  (RAG: 15)   — quiz needs richer chunks
      - target_chunk_tokens: 160 (RAG: 256)  — quiz prefers tighter focus
      - overlap_sentences : 0   (RAG: 2)    — context fringe is used instead
      - quality_score_threshold + min_semantic_score — quiz validates quality
      - min_words         : 35  (RAG: 8)    — quiz needs denser chunks
    """

    # ── Embedding model ────────────────────────────────────────────────────────
    # Used ONLY for cosine-similarity boundary detection during chunking.
    # Embeddings are NOT stored or returned.
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # ── Semantic similarity thresholds ─────────────────────────────────────────
    similarity_threshold: float = 0.68
    window_size: int = 3
    breakpoint_percentile: float = 75.0

    # ── Dynamic breakpoints (mean-std method) ──────────────────────────────────
    # True  = mean-std (recommended for slides/mixed docs)
    # False = percentile (recommended for long textbooks)
    dynamic_similarity: bool = True
    similarity_std_factor: float = 0.5

    # ── Size constraints (tokens ≈ chars / 4) ──────────────────────────────────
    min_chunk_tokens: int = 60
    max_chunk_tokens: int = 500      # increased from 300 — allows richer, denser quiz chunks
    target_chunk_tokens: int = 200   # mid-point raised proportionally

    # ── Sentence constraints ───────────────────────────────────────────────────
    min_sentence_length: int = 15
    max_sentences_per_chunk: int = 12

    # ── Overlap ────────────────────────────────────────────────────────────────
    # 0 overlap — context fringe (prev_sentence / next_sentence) is used instead
    overlap_sentences: int = 0

    # ── Merging ────────────────────────────────────────────────────────────────
    merge_orphans: bool = True

    # ── Quality gate ───────────────────────────────────────────────────────────
    # Chunks whose composite quality score is below this threshold are dropped.
    quality_score_threshold: float = 0.50

    # ── Semantic floor ─────────────────────────────────────────────────────────
    # Chunks with semantic_score below this value are dropped.
    min_semantic_score: float = 0.20

    # ── Post-processing size filter ────────────────────────────────────────────
    min_words: int = 35
    max_words: int = 450             # raised proportionally with max_chunk_tokens

    # ── Deduplication ──────────────────────────────────────────────────────────
    dedup_similarity_threshold: float = 0.92


# ═══════════════════════════════════════════════════════════════
# METADATA EXTRACTION CONFIG
# ═══════════════════════════════════════════════════════════════

@dataclass
class QuizMetadataConfig:
    """
    Controls the Groq-based metadata extractor (quiz_metadata.py).

    Model rotation order: when a model hits a rate limit the extractor
    automatically tries the next model in the list.
    """
    # Ordered list of Groq model IDs to try (first = preferred).
    # Prefer the model with the widest account compatibility; rotate away from
    # unavailable/404 model names instead of treating those as fatal.
    # A project-level env override can also be supplied via GROQ_QUIZ_MODELS or LLM_MODEL.
    models: tuple = ()

    def __post_init__(self):
        if not self.models:
            self.models = _resolve_quiz_groq_models()

    # Chunks sent per API call.
    # Groq request ceilings are lower than the older defaults, especially for
    # reasoning-oriented models. Keep this small to avoid 413 payload failures.
    batch_size: int = 2

    # Retry + backoff
    max_retries: int = 5
    base_backoff: float = 2.0        # seconds; doubles on each retry within a model

    # Truncation guard before sending (words) — raised to match max_words
    max_chunk_words: int = 450

    # Sleep between batches (seconds) to respect TPM limits
    inter_batch_sleep: float = 1.5
