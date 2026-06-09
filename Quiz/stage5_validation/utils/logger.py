"""
S5 Validation Pipeline — ValidationLogger
Handles all debug checkpoint saving, rejection logging, and final output persistence.

Each MCQ gets its own debug folder:
    debug_outputs/
        <chunk_id>_<slot_index>/
            01_format.json
            02_relevance.json
            ...
            final_result.json
"""

import gzip
import json
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from config.settings import PipelineConfig


# ── Stage name → filename prefix mapping ────────────────────────────────────
STAGE_FILES = {
    "format":        "01_format.json",
    "relevance":     "02_relevance.json",
    "distractors":   "03_distractors.json",
    "entailment":    "04_entailment.json",
    "deduplication": "05_deduplication.json",
    "judge":         "06_judge.json",
    "final":         "final_result.json",
}


def _now() -> str:
    """ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def _mcq_key(mcq_input: Dict) -> str:
    """Build a filesystem-safe identifier for one MCQ."""
    chunk_id = mcq_input.get("chunk_id", "unknown")
    slot = mcq_input.get("slot_index", 0)
    # sanitise: replace characters that are invalid in directory names
    safe = str(chunk_id).replace("/", "_").replace("\\", "_").replace(" ", "_")
    return f"{safe}__slot{slot}"


class ValidationLogger:
    """
    Centralised logging + debug-checkpoint system for the S5 pipeline.

    Usage
    -----
    logger = ValidationLogger(config)
    logger.save_stage_output(mcq_input, stage="format", result={...}, passed=True)
    logger.save_rejection(mcq_input, stage="format", reason="Missing field: answer")
    logger.save_final_output(validated_mcq)
    """

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.debug_root = Path(config.debug_dir)
        self.checkpoint_dir = Path(config.checkpoint_dir)

        # Output files (append-mode JSONL)
        self.validated_path = Path(config.validated_output)
        self.rejected_path = Path(config.rejected_output)

        # Python logger
        self.log = logging.getLogger("s5.logger")

        # Create base directories
        self.debug_root.mkdir(parents=True, exist_ok=True)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _mcq_debug_dir(self, mcq_input: Dict) -> Path:
        key = _mcq_key(mcq_input)
        d = self.debug_root / key
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _write_json(self, path: Path, data: Dict, compress: bool = False):
        """Write a JSON file, optionally gzip-compressed."""
        if compress:
            gz_path = path.with_suffix(path.suffix + ".gz")
            with gzip.open(gz_path, "wt", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        else:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    def _append_jsonl(self, path: Path, record: Dict):
        """Append one record to a JSONL file."""
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

    # ── Public API ───────────────────────────────────────────────────────────

    def save_stage_output(
        self,
        mcq_input: Dict,
        stage: str,
        result: Dict[str, Any],
        passed: bool,
        scores: Optional[Dict] = None,
        rejection_reason: Optional[str] = None,
    ):
        """
        Persist the debug checkpoint after a single validation stage.

        Parameters
        ----------
        mcq_input        : original MCQ dict from S4
        stage            : one of format / relevance / distractors /
                           entailment / deduplication / judge
        result           : raw output from the validator
        passed           : True if the MCQ passed this stage
        scores           : optional dict of numeric scores
        rejection_reason : filled when passed=False
        """
        if not self.config.debug_mode:
            return

        filename = STAGE_FILES.get(stage, f"{stage}.json")
        debug_dir = self._mcq_debug_dir(mcq_input)
        out_path = debug_dir / filename

        payload = {
            "stage": stage,
            "timestamp": _now(),
            "mcq_key": _mcq_key(mcq_input),
            "input": mcq_input,
            "result": result,
            "scores": scores or {},
            "passed": passed,
            "rejection_reason": rejection_reason,
        }

        self._write_json(out_path, payload, compress=self.config.compress_debug)
        self.log.debug("Checkpoint saved: %s", out_path)

    def save_final_output(self, validated_mcq: Dict):
        """
        Append a fully validated MCQ to the validated output JSONL
        and save final_result.json in the debug folder.
        """
        mcq_input = {
            "chunk_id": validated_mcq.get("chunk_id"),
            "slot_index": validated_mcq.get("slot_index", 0),
        }

        # Debug final snapshot
        if self.config.debug_mode:
            debug_dir = self._mcq_debug_dir(mcq_input)
            out_path = debug_dir / STAGE_FILES["final"]
            payload = {
                "stage": "final",
                "timestamp": _now(),
                "status": "PASSED",
                "validated_mcq": validated_mcq,
            }
            self._write_json(out_path, payload, compress=self.config.compress_debug)

        # Append to validated JSONL
        self._append_jsonl(self.validated_path, validated_mcq)
        self.log.info("Validated MCQ saved: chunk_id=%s slot=%s",
                      validated_mcq.get("chunk_id"), validated_mcq.get("slot_index"))

    def save_rejection(
        self,
        mcq_input: Dict,
        stage: str,
        reason: str,
        full_result: Optional[Dict] = None,
    ):
        """
        Append a rejected MCQ (with reason) to the rejected output JSONL
        and save final_result.json in the debug folder.
        """
        record = {
            "chunk_id": mcq_input.get("chunk_id"),
            "slot_index": mcq_input.get("slot_index", 0),
            "failed_stage": stage,
            "rejection_reason": reason,
            "timestamp": _now(),
            "mcq": mcq_input.get("mcq"),
            "text_preview": (mcq_input.get("text") or "")[:200],
            "validation_detail": full_result or {},
        }

        # Debug final snapshot
        if self.config.debug_mode:
            debug_dir = self._mcq_debug_dir(mcq_input)
            out_path = debug_dir / STAGE_FILES["final"]
            payload = {
                "stage": "final",
                "timestamp": _now(),
                "status": "REJECTED",
                "failed_at": stage,
                "rejection_reason": reason,
                "mcq_input": mcq_input,
            }
            self._write_json(out_path, payload, compress=self.config.compress_debug)

        # Append to rejected JSONL
        self._append_jsonl(self.rejected_path, record)
        self.log.warning("Rejected MCQ [%s]: chunk_id=%s slot=%s — %s",
                         stage, mcq_input.get("chunk_id"),
                         mcq_input.get("slot_index"), reason)

    # ── Checkpoint (resume support) ──────────────────────────────────────────

    def mark_processed(self, mcq_input: Dict):
        """Record that this MCQ has been fully processed (for resume support)."""
        key = _mcq_key(mcq_input)
        cp_path = self.checkpoint_dir / "processed.json"

        processed: set = set()
        if cp_path.exists():
            with open(cp_path) as f:
                processed = set(json.load(f))

        processed.add(key)
        with open(cp_path, "w") as f:
            json.dump(sorted(processed), f)

    def is_processed(self, mcq_input: Dict) -> bool:
        """Return True if this MCQ was already fully processed in a prior run."""
        if not self.config.resume_from_checkpoint:
            return False
        key = _mcq_key(mcq_input)
        cp_path = self.checkpoint_dir / "processed.json"
        if not cp_path.exists():
            return False
        with open(cp_path) as f:
            return key in set(json.load(f))

    def get_existing_stage_result(self, mcq_input: Dict, stage: str) -> Optional[Dict]:
        """
        If debug mode is on and a stage checkpoint already exists,
        return it so we can skip re-running that stage (fast resume).
        """
        if not self.config.debug_mode:
            return None
        filename = STAGE_FILES.get(stage)
        if not filename:
            return None
        out_path = self._mcq_debug_dir(mcq_input) / filename
        if out_path.exists():
            with open(out_path) as f:
                return json.load(f)
        return None
