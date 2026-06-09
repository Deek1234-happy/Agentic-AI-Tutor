"""
S5 — MCQValidator
Pipeline orchestrator that runs all 5 validation stages in order:

  1. format        → structural completeness (cheap, rule-based)
  2. relevance     → question ↔ chunk semantic similarity
  3. distractors   → plausible & distinguishable wrong answers
  4. deduplication → no near-duplicate questions
  5. llm_judge     → holistic quality score (expensive, runs last)

Design principles
-----------------
- Fail-fast: expensive checks only run if cheap checks pass.
- Checkpoint every stage: intermediate outputs saved to disk.
- Resume-safe: skips already-processed MCQs on restart.
- Provider-agnostic LLM judge: Anthropic / OpenAI / Ollama.
- GPU-aware: auto-detects CUDA > MPS > CPU.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.settings import ValidationConfig
from utils.embeddings import _get_device
from utils.logger import ValidationLogger
from validators.format_validator import FormatValidator
from validators.relevance_validator import RelevanceValidator
from validators.distractor_validator import DistractorValidator
from validators.dedup_validator import DeduplicationValidator
from validators.llm_judge_validator import LLMJudgeValidator


def _setup_logging(config: ValidationConfig):
    level = getattr(logging, config.pipeline.log_level.upper(), logging.INFO)
    handlers = [logging.StreamHandler(sys.stdout)]
    if config.pipeline.log_file:
        handlers.append(logging.FileHandler(config.pipeline.log_file))
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        handlers=handlers,
        force=True,
    )


class MCQValidator:
    """
    Orchestrates the full S5 validation pipeline for a single MCQ
    or a batch of MCQs.

    Quick start
    -----------
    validator = MCQValidator()
    result = validator.validate_pipeline(mcq_input)

    Batch
    -----
    results = validator.validate_batch(list_of_mcq_dicts)
    """

    def __init__(self, config: Optional[ValidationConfig] = None):
        self.config = config or ValidationConfig()
        _setup_logging(self.config)
        self.log = logging.getLogger("s5.orchestrator")

        # Auto-detect device
        self.device = _get_device(self.config.pipeline.device)
        self.log.info("Device: %s", self.device)

        # Shared logger / checkpoint system
        self.vlog = ValidationLogger(self.config.pipeline)

        # Instantiate all validators (models loaded lazily)
        self.format_v    = FormatValidator(self.config.format)
        self.relevance_v = RelevanceValidator(self.config.relevance, self.device)
        self.distractor_v = DistractorValidator(self.config.distractor, self.device)
        self.dedup_v     = DeduplicationValidator(self.config.deduplication, self.device)
        self.judge_v     = LLMJudgeValidator(self.config.llm_judge)

    # ── Single MCQ pipeline ───────────────────────────────────────────────

    def validate_pipeline(self, mcq_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run all 6 validation stages for a single MCQ.

        Returns a dict with:
          - all original MCQ fields
          - "validation" key containing per-stage results + final_passed flag
        """
        # Resume: skip if already processed
        if self.vlog.is_processed(mcq_input):
            self.log.info("SKIP (already processed): chunk_id=%s slot=%s",
                          mcq_input.get("chunk_id"), mcq_input.get("slot_index"))
            return {"skipped": True, "chunk_id": mcq_input.get("chunk_id")}

        self.log.info("-- Validating: chunk_id=%s slot=%s",
                      mcq_input.get("chunk_id"), mcq_input.get("slot_index"))

        validation: Dict[str, Any] = {}

        # ── Stage 1: Format ───────────────────────────────────────────────
        result = self._run_stage_with_resume(mcq_input, "format",
                                              lambda: self.validate_format(mcq_input))
        validation["format"] = result
        if not result["passed"]:
            return self._finalize_rejection(mcq_input, "format", result["reason"], validation)

        # ── Stage 2: Relevance ────────────────────────────────────────────
        result = self._run_stage_with_resume(mcq_input, "relevance",
                                              lambda: self.validate_relevance(mcq_input))
        validation["relevance"] = result
        if not result["passed"]:
            return self._finalize_rejection(mcq_input, "relevance", result["reason"], validation)

        # ── Stage 3: Distractors ──────────────────────────────────────────
        result = self._run_stage_with_resume(mcq_input, "distractors",
                                              lambda: self.validate_distractors(mcq_input))
        validation["distractors"] = result
        if not result["passed"]:
            return self._finalize_rejection(mcq_input, "distractors", result["reason"], validation)

        # ── Stage 4: Deduplication ────────────────────────────────────────
        result = self._run_stage_with_resume(mcq_input, "deduplication",
                                              lambda: self.validate_deduplication(mcq_input))
        validation["deduplication"] = result
        if not result["passed"]:
            return self._finalize_rejection(mcq_input, "deduplication", result["reason"], validation)

        # ── Stage 5: LLM Judge (expensive — only runs if all above pass) ──
        result = self._run_stage_with_resume(mcq_input, "llm_judge",
                                              lambda: self.validate_llm_judge(mcq_input))
        validation["llm_judge"] = result
        if not result["passed"]:
            return self._finalize_rejection(mcq_input, "llm_judge", result["reason"], validation)

        # ── All passed ────────────────────────────────────────────────────
        return self._finalize_success(mcq_input, validation)

    # ── Per-stage methods (can be called standalone) ──────────────────────

    def validate_format(self, mcq_input: Dict) -> Dict:
        return self.format_v.validate(mcq_input)

    def validate_relevance(self, mcq_input: Dict) -> Dict:
        result = self.relevance_v.validate(mcq_input)
        # Patch threshold into result for display consistency
        result["threshold"] = self.config.relevance.threshold
        return result

    def validate_distractors(self, mcq_input: Dict) -> Dict:
        return self.distractor_v.validate(mcq_input)

    def validate_deduplication(self, mcq_input: Dict) -> Dict:
        return self.dedup_v.validate(mcq_input)

    def validate_llm_judge(self, mcq_input: Dict) -> Dict:
        return self.judge_v.validate(mcq_input)

    # ── Checkpoint helpers ────────────────────────────────────────────────

    def save_checkpoint(self, mcq_input: Dict, stage: str, result: Dict):
        """
        Manually save a checkpoint for a given stage.
        Normally called automatically by _run_stage_with_resume.
        """
        self.vlog.save_stage_output(
            mcq_input=mcq_input,
            stage=stage,
            result=result,
            passed=result.get("passed", False),
            scores={k: v for k, v in result.items()
                    if isinstance(v, (int, float)) and k != "passed"},
            rejection_reason=result.get("reason") if not result.get("passed") else None,
        )

    def _run_stage_with_resume(self, mcq_input: Dict, stage: str, fn) -> Dict:
        """
        Try to load a cached stage result; if not found, run fn() and cache it.
        """
        cached = self.vlog.get_existing_stage_result(mcq_input, stage)
        if cached is not None:
            self.log.debug("Resume: using cached stage '%s'", stage)
            return cached.get("result", cached)

        result = fn()
        self.save_checkpoint(mcq_input, stage, result)
        return result

    # ── Finalisation helpers ──────────────────────────────────────────────

    def _finalize_rejection(
        self, mcq_input: Dict, stage: str, reason: str, validation: Dict
    ) -> Dict:
        validation["final_passed"] = False
        validation["failed_stage"] = stage

        self.vlog.save_rejection(mcq_input, stage, reason, full_result=validation)
        self.vlog.mark_processed(mcq_input)

        return {
            **mcq_input,
            "validation": {**validation, "final_passed": False, "failed_stage": stage},
        }

    def _finalize_success(self, mcq_input: Dict, validation: Dict) -> Dict:
        validation["final_passed"] = True

        validated_mcq = {**mcq_input, "validation": validation}
        self.vlog.save_final_output(validated_mcq)
        self.vlog.mark_processed(mcq_input)

        return validated_mcq

    # ── Batch processing ──────────────────────────────────────────────────

    def validate_batch(
        self, mcq_list: List[Dict[str, Any]], stop_on_error: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Validate a list of MCQs sequentially.
        Returns list of all results (passed + rejected).

        Parameters
        ----------
        mcq_list      : list of S4 MCQ dicts
        stop_on_error : if True, raise on unexpected exception
                        if False, log and continue
        """
        results = []
        total = len(mcq_list)
        passed_count = 0
        rejected_count = 0

        self.log.info("Starting batch validation: %d MCQs", total)

        for i, mcq in enumerate(mcq_list, start=1):
            self.log.info("Progress: %d/%d", i, total)
            try:
                result = self.validate_pipeline(mcq)
                results.append(result)
                if result.get("validation", {}).get("final_passed"):
                    passed_count += 1
                else:
                    rejected_count += 1
            except Exception as e:
                self.log.error("Unexpected error for MCQ %d: %s", i, e, exc_info=True)
                if stop_on_error:
                    raise
                rejected_count += 1

        self.log.info(
            "Batch complete: %d total | %d passed | %d rejected",
            total, passed_count, rejected_count,
        )
        return results

    # ── Stage-by-stage pipeline ───────────────────────────────────────────

    # Maps stage name → (validator attribute, validate method name)
    STAGE_REGISTRY = [
        ("format",        "format_v",     "validate_format"),
        ("relevance",     "relevance_v",  "validate_relevance"),
        ("distractors",   "distractor_v", "validate_distractors"),
        ("deduplication", "dedup_v",      "validate_deduplication"),
        ("llm_judge",     "judge_v",      "validate_llm_judge"),
    ]

    def run_stages(
        self, mcq_list: List[Dict[str, Any]], stop_on_error: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Run the validation pipeline **stage by stage**.

        Each stage processes all MCQs that passed the previous stage,
        writing ``passed.jsonl`` + ``failed.jsonl`` into its own numbered
        folder (``stage_1/``, ``stage_2/``, …).

        Parameters
        ----------
        mcq_list      : list of raw S4 MCQ dicts
        stop_on_error : if True, raise on unexpected exception

        Returns
        -------
        list of MCQ dicts that passed **all** stages
        """
        import json
        from datetime import datetime, timezone
        from pathlib import Path

        stage_root = Path(self.config.pipeline.stage_output_dir)
        stage_root.mkdir(parents=True, exist_ok=True)

        enabled = self.config.pipeline.enabled_stages
        # Filter registry to only enabled stages, preserving order
        stages = [
            (name, attr, method)
            for name, attr, method in self.STAGE_REGISTRY
            if name in enabled
        ]

        start = self.config.pipeline.start_stage
        end = self.config.pipeline.end_stage or len(stages)
        # Clamp to valid range
        start = max(1, min(start, len(stages)))
        end = max(start, min(end, len(stages)))

        current_input = list(mcq_list)
        all_failed: List[Dict[str, Any]] = []

        # ── If starting from a stage > 1, load input from previous stage ──
        if start > 1:
            prev_passed_path = stage_root / f"stage_{start - 1}" / "passed.jsonl"
            if not prev_passed_path.exists():
                self.log.error(
                    "Cannot start from stage %d: %s not found. "
                    "Run stages 1-%d first.",
                    start, prev_passed_path, start - 1,
                )
                return []

            loaded = []
            with open(prev_passed_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        loaded.append(json.loads(line))

            current_input = [r["mcq_data"] for r in loaded]
            self.log.info(
                "Loaded %d passed MCQs from stage %d as input for stage %d",
                len(current_input), start - 1, start,
            )

        self.log.info("=" * 60)
        self.log.info(
            "Stage-by-stage pipeline: %d MCQs, stages %d-%d (of %d total)",
            len(current_input), start, end, len(stages),
        )
        self.log.info("=" * 60)

        can_resume = self.config.pipeline.resume_from_checkpoint

        for stage_num, (stage_name, _attr, method_name) in enumerate(stages, start=1):
            # ── Skip stages outside the selected range ────────────────────
            if stage_num < start or stage_num > end:
                continue

            if not current_input:
                self.log.warning("No MCQs left to process — skipping stage %d (%s)", stage_num, stage_name)
                break

            stage_dir = stage_root / f"stage_{stage_num}"
            stage_dir.mkdir(parents=True, exist_ok=True)

            passed_path = stage_dir / "passed.jsonl"
            failed_path = stage_dir / "failed.jsonl"
            completed_marker = stage_dir / "_completed"

            # ── Resume: skip this stage if it was already completed ────────
            if can_resume and completed_marker.exists() and passed_path.exists():
                self.log.info(
                    "  Stage %d [%s]: SKIPPED (already completed, loading from disk)",
                    stage_num, stage_name,
                )
                # Load the passed MCQs from the previous run
                loaded_passed = []
                with open(passed_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            loaded_passed.append(json.loads(line))

                # Count failed for the log
                failed_count = 0
                if failed_path.exists():
                    with open(failed_path, "r", encoding="utf-8") as f:
                        failed_count = sum(1 for l in f if l.strip())

                self.log.info(
                    "  Stage %d [%s]: %d passed, %d failed (loaded from checkpoint)",
                    stage_num, stage_name, len(loaded_passed), failed_count,
                )
                # Feed the original MCQ data to the next stage
                current_input = [r["mcq_data"] for r in loaded_passed]
                continue

            # ── Partial resume: collect already-processed IDs ─────────────
            #    If passed/failed files exist from a previous interrupted run,
            #    we skip those (chunk_id, slot_index) pairs and append only
            #    the new results, so the run continues from where it stopped.
            already_processed_ids: set = set()
            if can_resume and (passed_path.exists() or failed_path.exists()):
                import json
                decoder = json.JSONDecoder()
                
                for _p in (passed_path, failed_path):
                    if not _p.exists():
                        continue
                    
                    # Robustly read and deduplicate the file to fix any corruption 
                    # from previous interrupted runs (e.g. missing newlines)
                    unique_records = []
                    seen_in_file = set()
                    
                    with open(_p, "r", encoding="utf-8") as _f:
                        for _line in _f:
                            text = _line.strip()
                            while text:
                                text = text.lstrip()
                                if not text:
                                    break
                                try:
                                    _r, idx = decoder.raw_decode(text)
                                    text = text[idx:]
                                    
                                    _cid = _r.get("chunk_id")
                                    _sid = _r.get("slot_index", 0)
                                    _key = (_cid, _sid)
                                    
                                    if _cid is not None:
                                        if _key not in seen_in_file:
                                            seen_in_file.add(_key)
                                            already_processed_ids.add(_key)
                                            unique_records.append(_r)
                                    else:
                                        unique_records.append(_r)
                                except json.JSONDecodeError:
                                    break
                                    
                    # Rewrite the file cleanly with deduplicated records
                    with open(_p, "w", encoding="utf-8") as _f:
                        for _r in unique_records:
                            _f.write(json.dumps(_r, ensure_ascii=False, default=str) + "\n")

                if already_processed_ids:
                    self.log.info(
                        "  Stage %d [%s]: partial resume — skipping %d already-saved MCQs",
                        stage_num, stage_name, len(already_processed_ids),
                    )
            elif not can_resume:
                # --no-resume: wipe everything and start fresh
                for p in (passed_path, failed_path, completed_marker):
                    if p.exists():
                        p.unlink()

            # Remove only the _completed marker so we re-run to finish the
            # stage; do NOT delete passed/failed — we will append to them.
            if completed_marker.exists():
                completed_marker.unlink()

            validate_fn = getattr(self, method_name)
            # LLM judge flushes every single item; other stages flush every 100
            flush_every = 1 if stage_name == "llm_judge" else 100
            passed_list, failed_list = self._run_single_stage(
                stage_num=stage_num,
                stage_name=stage_name,
                validate_fn=validate_fn,
                mcq_list=current_input,
                passed_path=passed_path,
                failed_path=failed_path,
                stop_on_error=stop_on_error,
                flush_every=flush_every,
                already_processed_ids=already_processed_ids,
            )

            # Mark this stage as fully completed (for resume on next run)
            completed_marker.write_text(
                f"completed_at={datetime.now(timezone.utc).isoformat()}\n"
                f"stage={stage_name}\n"
                f"passed={len(passed_list)}\n"
                f"failed={len(failed_list)}\n",
                encoding="utf-8",
            )

            self.log.info(
                "  Stage %d [%s]: %d passed, %d failed  ->  %s/",
                stage_num, stage_name, len(passed_list), len(failed_list),
                stage_dir,
            )

            all_failed.extend(failed_list)

            # Next stage receives only the *original MCQ data* from passed records
            # (strip the enrichment so validators get clean input)
            current_input = [r["mcq_data"] for r in passed_list]

        # ── Summary ───────────────────────────────────────────────────────
        final_passed = current_input
        total_failed = len(mcq_list) - len(final_passed)

        self.log.info("=" * 60)
        self.log.info(
            "Pipeline complete: %d passed | %d failed | %d total",
            len(final_passed), total_failed, len(mcq_list),
        )
        self.log.info("Stage outputs -> %s/", stage_root)
        self.log.info("=" * 60)

        return final_passed

    def _run_single_stage(
        self,
        stage_num: int,
        stage_name: str,
        validate_fn,
        mcq_list: List[Dict[str, Any]],
        passed_path: Any = None,
        failed_path: Any = None,
        stop_on_error: bool = False,
        flush_every: int = 100,
        already_processed_ids: Optional[set] = None,
    ) -> tuple:
        """
        Run one validation stage across all MCQs in the list.

        Parameters
        ----------
        flush_every           : write to disk every N *newly processed* items
                                (1 = every item, 100 = default batch)
        already_processed_ids : set of (chunk_id, slot_index) tuples that were
                                already saved in a previous interrupted run;
                                those items are skipped but pre-loaded into the
                                return lists so stage counts stay correct.

        Returns
        -------
        (passed_records, failed_records)
            Each record is enriched with stage metadata, timestamps, and scores.
        """
        import json
        from datetime import datetime, timezone

        already_processed_ids = already_processed_ids or set()
        skipped_count = len(already_processed_ids)
        total = len(mcq_list)

        # ── Pre-populate records from partial files so return value is complete
        passed_records: List[Dict[str, Any]] = []
        failed_records: List[Dict[str, Any]] = []
        if skipped_count and passed_path and passed_path.exists():
            with open(passed_path, "r", encoding="utf-8") as _f:
                for _line in _f:
                    _line = _line.strip()
                    if _line:
                        try:
                            passed_records.append(json.loads(_line))
                        except json.JSONDecodeError:
                            pass
        if skipped_count and failed_path and failed_path.exists():
            with open(failed_path, "r", encoding="utf-8") as _f:
                for _line in _f:
                    _line = _line.strip()
                    if _line:
                        try:
                            failed_records.append(json.loads(_line))
                        except json.JSONDecodeError:
                            pass

        batch_passed: List[Dict[str, Any]] = []
        batch_failed: List[Dict[str, Any]] = []
        processed_this_run = 0

        self.log.info(
            "-- Stage %d: %s (%d MCQs total%s) --",
            stage_num, stage_name, total,
            f", {skipped_count} already done" if skipped_count else "",
        )

        def _flush_batches():
            """Append current batches to disk and clear them."""
            if passed_path and batch_passed:
                with open(passed_path, "a", encoding="utf-8") as f:
                    for r in batch_passed:
                        f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
                batch_passed.clear()
            if failed_path and batch_failed:
                with open(failed_path, "a", encoding="utf-8") as f:
                    for r in batch_failed:
                        f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
                batch_failed.clear()

        for i, mcq in enumerate(mcq_list, start=1):
            # ── Partial resume: skip MCQs already written in a prior run ──
            _key = (mcq.get("chunk_id"), mcq.get("slot_index", 0))
            if _key in already_processed_ids:
                continue
                
            # Add to set immediately to prevent duplicates in the current run
            already_processed_ids.add(_key)

            processed_this_run += 1

            try:
                result = validate_fn(mcq)
                now = datetime.now(timezone.utc).isoformat()

                scores = {
                    k: v for k, v in result.items()
                    if isinstance(v, (int, float)) and k != "passed"
                }

                record = {
                    "mcq_data":         mcq,
                    "chunk_id":         mcq.get("chunk_id"),
                    "slot_index":       mcq.get("slot_index", 0),
                    "stage_name":       stage_name,
                    "stage_number":     stage_num,
                    "timestamp":        now,
                    "validation_result": result,
                    "scores":           scores,
                }

                if result.get("passed"):
                    passed_records.append(record)
                    batch_passed.append(record)
                else:
                    record["failure_reason"] = result.get("reason", "")
                    failed_records.append(record)
                    batch_failed.append(record)

                self.save_checkpoint(mcq, stage_name, result)

            except Exception as e:
                self.log.error(
                    "Stage %d [%s] — error on MCQ %d/%d: %s",
                    stage_num, stage_name, i, total, e, exc_info=True,
                )
                if stop_on_error:
                    raise
                err_record = {
                    "mcq_data":         mcq,
                    "chunk_id":         mcq.get("chunk_id"),
                    "slot_index":       mcq.get("slot_index", 0),
                    "stage_name":       stage_name,
                    "stage_number":     stage_num,
                    "timestamp":        datetime.now(timezone.utc).isoformat(),
                    "validation_result": {"passed": False, "reason": str(e)},
                    "scores":           {},
                    "failure_reason":   str(e),
                }
                failed_records.append(err_record)
                batch_failed.append(err_record)

            # ── Flush to disk every flush_every newly processed items ──────
            if processed_this_run % flush_every == 0:
                total_done = len(passed_records) + len(failed_records)
                self.log.info(
                    "    [%s] %d/%d done (%d passed, %d failed%s)",
                    stage_name, total_done, total,
                    len(passed_records), len(failed_records),
                    f"  [{skipped_count} resumed]" if skipped_count else "",
                )
                _flush_batches()

        # ── Final flush for any remainder not yet written ──────────────────
        _flush_batches()
        total_done = len(passed_records) + len(failed_records)
        self.log.info(
            "    [%s] %d/%d done (%d passed, %d failed%s) — stage complete",
            stage_name, total_done, total,
            len(passed_records), len(failed_records),
            f"  [{skipped_count} resumed]" if skipped_count else "",
        )

        return passed_records, failed_records