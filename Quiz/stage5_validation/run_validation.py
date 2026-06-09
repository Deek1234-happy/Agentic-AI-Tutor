"""
S5 Validation Pipeline — CLI Entry Point
Usage:
    python run_validation.py --input mcqs.jsonl
    python run_validation.py --input mcqs.jsonl --provider ollama --debug
    python run_validation.py --input mcqs.jsonl --provider anthropic --no-resume
    python run_validation.py --input mcqs.jsonl --no-stage-by-stage   # old per-MCQ flow
    python run_validation.py --input mcqs.jsonl --stage-output-dir my_stages
"""

import argparse
import json
import logging
import sys
from pathlib import Path

log = logging.getLogger("s5.cli")


def load_jsonl(path: str):
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def main():
    # Silence sentence-transformers progress bars and model loading logs
    import logging
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("transformers").setLevel(logging.WARNING)

    parser = argparse.ArgumentParser(description="S5 MCQ Validation Pipeline")
    parser.add_argument("--input", required=True, help="Input JSONL file with S4 MCQs")
    parser.add_argument("--output", default="validated_mcqs.jsonl", help="Validated output JSONL")
    parser.add_argument("--rejected", default="rejected_mcqs.jsonl", help="Rejected output JSONL")
    parser.add_argument("--debug-dir", default="debug_outputs", help="Debug checkpoint directory")
    parser.add_argument("--provider", default="groq",
                        choices=["groq", "anthropic", "openai", "ollama"],
                        help="LLM judge provider (default: groq)")
    parser.add_argument("--groq-model", default="llama-3.3-70b",
                        help="Groq model alias: llama-3.3-70b (default) or oss-120b")
    parser.add_argument("--groq-api-key", default=None,
                        help="Groq API key (overrides GROQ_API_KEY env var)")
    parser.add_argument("--ollama-model", default="llama3", help="Ollama model name")
    parser.add_argument("--relevance-threshold", type=float, default=None,
                        help="Override relevance similarity threshold (default: from settings.py)")
    parser.add_argument("--dedup-threshold", type=float, default=None,
                        help="Override dedup similarity threshold (default: from settings.py)")
    parser.add_argument("--no-debug", action="store_true", help="Disable debug checkpoints")
    parser.add_argument("--no-resume", action="store_true", help="Ignore existing checkpoints")
    parser.add_argument("--compress", action="store_true", help="Gzip debug output files")
    parser.add_argument("--device", default=None, help="cuda|mps|cpu (auto-detect if not set)")
    # ── Stage-by-stage flags ──────────────────────────────────────────────
    parser.add_argument("--stage-output-dir", default="stage_outputs",
                        help="Root directory for stage_1/, stage_2/, ... output folders")
    parser.add_argument("--no-stage-by-stage", action="store_true",
                        help="Disable stage-by-stage mode; use old per-MCQ flow instead")
    parser.add_argument("--start-stage", type=int, default=1,
                        help="First stage to run (1-indexed). Loads input from previous stage's passed.jsonl")
    parser.add_argument("--end-stage", type=int, default=None,
                        help="Last stage to run (1-indexed). Default = run all remaining stages")
    
    # Fallback configuration
    parser.add_argument("--use-fallback-chain", action="store_true",
                        help="Enable the automatic provider and model switching chain on rate limits.")
    args = parser.parse_args()

    # Build config from CLI args
    from config.settings import (
        ValidationConfig, RelevanceConfig, DeduplicationConfig,
        LLMJudgeConfig,
        PipelineConfig
    )

    # Only override thresholds if explicitly passed on the CLI
    relevance_kwargs = {}
    if args.relevance_threshold is not None:
        relevance_kwargs["threshold"] = args.relevance_threshold

    dedup_kwargs = {}
    if args.dedup_threshold is not None:
        dedup_kwargs["similarity_threshold"] = args.dedup_threshold

    config = ValidationConfig(
        relevance=RelevanceConfig(**relevance_kwargs),
        deduplication=DeduplicationConfig(**dedup_kwargs),
        llm_judge=LLMJudgeConfig(
            provider=args.provider,
            model=args.groq_model if args.provider == "groq" else (
                args.ollama_model if args.provider == "ollama" else "claude-sonnet-4-20250514"
            ),
            groq_api_key=args.groq_api_key,  # None → reads GROQ_API_KEY env var
            use_fallback_chain=args.use_fallback_chain,
            # We don't populate fallback_chain here, it will be populated in __post_init__ or defined statically in settings.py
        ),
        pipeline=PipelineConfig(
            debug_mode=not args.no_debug,
            debug_dir=args.debug_dir,
            compress_debug=args.compress,
            validated_output=args.output,
            rejected_output=args.rejected,
            resume_from_checkpoint=not args.no_resume,
            device=args.device,
            stage_output_dir=args.stage_output_dir,
            run_stage_by_stage=not args.no_stage_by_stage,
            start_stage=args.start_stage,
            end_stage=args.end_stage,
        ),
    )

    # Load input
    if not Path(args.input).exists():
        print(f"ERROR: Input file not found: {args.input}")
        sys.exit(1)

    mcq_list = load_jsonl(args.input)
    print(f"Loaded {len(mcq_list)} MCQs from {args.input}")

    # Run pipeline
    from mcq_validator import MCQValidator
    validator = MCQValidator(config=config)

    if config.pipeline.run_stage_by_stage:
        # ── New: stage-by-stage flow ──────────────────────────────────────
        final_passed = validator.run_stages(mcq_list)
        total_failed = len(mcq_list) - len(final_passed)

        print(f"\n✓ Done (stage-by-stage) — Passed: {len(final_passed)} | "
              f"Failed: {total_failed} | Total: {len(mcq_list)}")
        print(f"  Stage outputs → {args.stage_output_dir}/")
        if not args.no_debug:
            print(f"  Debug         → {args.debug_dir}/")
    else:
        # ── Old: per-MCQ fail-fast flow ───────────────────────────────────
        results = validator.validate_batch(mcq_list)

        passed = sum(1 for r in results if r.get("validation", {}).get("final_passed"))
        rejected = len(results) - passed
        print(f"\n✓ Done — Passed: {passed} | Rejected: {rejected} | Total: {len(results)}")
        print(f"  Validated → {args.output}")
        print(f"  Rejected  → {args.rejected}")
        if not args.no_debug:
            print(f"  Debug     → {args.debug_dir}/")


if __name__ == "__main__":
    main()