"""
S5 Validation Pipeline — Configuration
All thresholds, model names, and runtime settings in one place.
Change these without touching any validator logic.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class FormatConfig:
    min_question_length: int = 15       # characters
    max_question_length: int = 500
    required_options: list = field(default_factory=lambda: ["A", "B", "C", "D"])
    min_explanation_length: int = 20
    valid_answers: set = field(default_factory=lambda: {"A", "B", "C", "D"})


@dataclass
class RelevanceConfig:
    model_name: str = "models/bge-large-en-v1.5"
    threshold: float = 0.5             # cosine similarity — lower = more permissive
    batch_size: int = 32
    cache_embeddings: bool = True


@dataclass
class DistractorConfig:
    model_name: str = "models/bge-large-en-v1.5"
    min_relevance_to_question: float = 0.12
    max_similarity_to_answer: float = 0.90

    # Local NLI model used only to detect paraphrase / equivalence when a distractor
    # is very similar to the correct answer.
    nli_model_name: str = "models/nli-deberta-v3-large"
    nli_duplicate_entailment_threshold: float = 0.78

    batch_size: int = 32



@dataclass
class DeduplicationConfig:
    model_name: str = "models/bge-large-en-v1.5"
    similarity_threshold: float = 0.92  # above this = near-duplicate
    scope: str = "global"               # "global" | "document"
    persistent_store: str = "dedup_store.json"


GROQ_MODELS = {
    "llama-3.3-70b":           "llama-3.3-70b-versatile",
    "oss-120b":                "gpt-oss-120b",
    "llama-3.3-70b-versatile": "llama-3.3-70b-versatile",
    "openai/gpt-oss-120b":     "openai/gpt-oss-120b",
}

@dataclass
class LLMJudgeConfig:
    # Provider: "groq" | "anthropic" | "openai" | "ollama"
    provider: str = "groq"

    # Model — for Groq use short alias ("llama-3.3-70b" or "oss-120b")
    # or the full API string. Other providers use the string as-is.
    model: str = "llama-3.3-70b"
    base_url: Optional[str] = None
    
    # Fallback configuration for automatic provider switching on Rate Limits (429)
    use_fallback_chain: bool = False
    fallback_chain_index: int = 0
    api_key_env: Optional[str] = None
    fallback_chain: List[Dict[str, str]] = field(default_factory=lambda: [
        # Model 1: GPT-OSS 120B
        {"provider": "groq", "model": "openai/gpt-oss-120b"},
        {"provider": "openai", "model": "openai/gpt-oss-120b", "base_url": "https://openrouter.ai/api/v1", "api_key_env": "OPENROUTER_API_KEY"},
        
        # Model 2: Llama 3.3 70B
        {"provider": "groq", "model": "llama-3.3-70b-versatile"},
        {"provider": "groq", "model": "llama-3.3-70b-specdec"},
        {"provider": "openai", "model": "meta-llama/llama-3.3-70b-instruct:free", "base_url": "https://openrouter.ai/api/v1", "api_key_env": "OPENROUTER_API_KEY"},
        
        # Model 3: Llama 3.2 3B
        # {"provider": "groq", "model": "llama-3.2-3b-preview"},
        # {"provider": "openai", "model": "meta-llama/llama-3.2-3b-instruct:free", "base_url": "https://openrouter.ai/api/v1", "api_key_env": "OPENROUTER_API_KEY"},
    ])
    # Groq settings
    groq_api_key: Optional[str] = None  # None → reads GROQ_API_KEY env var

    # Ollama settings (used when provider == "ollama")
    ollama_base_url: str = "http://localhost:11434"

    # Retry / reliability
    max_retries: int = 3
    retry_delay: float = 2.0            # base seconds; actual = retry_delay * 2^attempt

    # Quality threshold
    min_overall_score: float = 3.5      # out of 5 — below this → reject

    # Chunk grounding threshold (replaces Stage 4 NLI entailment).
    # chunk_grounding is scored 1-5 by the judge:
    #   5 = answer explicitly stated in chunk
    #   3 = answer clearly implied but not verbatim
    #   1 = answer not derivable from chunk, or chunk contradicts it
    # MCQs scoring below this value are rejected regardless of overall score.
    min_chunk_grounding_score: float = 3.0

    # Request settings
    timeout: int = 60
    temperature: float = 0.0            # must stay 0 for scoring consistency



@dataclass
class PipelineConfig:
    debug_mode: bool = True
    debug_dir: str = "debug_outputs"
    compress_debug: bool = False        # gzip debug files on large runs
    validated_output: str = "validated_mcqs.jsonl"
    rejected_output: str = "rejected_mcqs.jsonl"
    checkpoint_dir: str = "checkpoints"
    resume_from_checkpoint: bool = True
    log_level: str = "INFO"
    log_file: str = "s5_validation.log"
    device: Optional[str] = None        # None = auto-detect (cuda > mps > cpu)
    # ── Stage-by-stage pipeline settings ────────────────────────────────
    stage_output_dir: str = "stage_outputs"   # root dir for stage_1/, stage_2/, ...
    run_stage_by_stage: bool = True           # True = new stage flow, False = old per-MCQ flow
    enabled_stages: list = field(default_factory=lambda: [
        "format", "relevance", "distractors", "deduplication", "llm_judge",
    ])
    start_stage: int = 1                      # first stage to run (1-indexed)
    end_stage: Optional[int] = None           # last stage to run (None = run all)


@dataclass
class ValidationConfig:
    format: FormatConfig = field(default_factory=FormatConfig)
    relevance: RelevanceConfig = field(default_factory=RelevanceConfig)
    distractor: DistractorConfig = field(default_factory=DistractorConfig)
    deduplication: DeduplicationConfig = field(default_factory=DeduplicationConfig)
    llm_judge: LLMJudgeConfig = field(default_factory=LLMJudgeConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)


# ── Singleton default config ────────────────────────────────────────────────
DEFAULT_CONFIG = ValidationConfig()