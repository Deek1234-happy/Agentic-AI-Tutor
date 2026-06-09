"""
S5 — Stage 1: Format Validation
Checks structural completeness and basic sanity of an MCQ dict.
No ML models needed; this is pure rule-based and very cheap.
"""

import logging
from typing import Any, Dict

from config.settings import FormatConfig

log = logging.getLogger("s5.format")


class FormatValidator:
    """
    Validates that an MCQ dict is structurally correct before
    any expensive model-based checks are run.

    Checks
    ------
    1. Top-level required fields present
    2. mcq sub-dict present with required keys
    3. Exactly 4 options labelled A/B/C/D
    4. Answer is one of A/B/C/D
    5. Question length within configured bounds
    6. Explanation is non-empty and long enough
    7. All option texts are non-empty strings
    """

    REQUIRED_TOP = {"chunk_id", "text", "mcq"}
    REQUIRED_MCQ = {"question", "options", "answer", "explanation"}

    def __init__(self, config: FormatConfig):
        self.cfg = config

    def validate(self, mcq_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Returns
        -------
        {
            "passed": bool,
            "reason": str,          # empty string when passed=True
            "checks": {             # per-check details for debugging
                "top_fields": ...,
                "mcq_fields": ...,
                "options": ...,
                "answer": ...,
                "question_length": ...,
                "explanation": ...,
                "option_texts": ...,
            }
        }
        """
        checks: Dict[str, Any] = {}

        # ── 1. Top-level fields ───────────────────────────────────────────
        missing_top = self.REQUIRED_TOP - set(mcq_input.keys())
        checks["top_fields"] = {
            "passed": not missing_top,
            "missing": sorted(missing_top),
        }
        if missing_top:
            return self._fail(f"Missing top-level fields: {sorted(missing_top)}", checks)

        mcq = mcq_input.get("mcq")
        if not isinstance(mcq, dict):
            checks["mcq_fields"] = {"passed": False, "reason": "mcq is not a dict"}
            return self._fail("Field 'mcq' must be a dict", checks)

        # ── 2. MCQ sub-fields ─────────────────────────────────────────────
        missing_mcq = self.REQUIRED_MCQ - set(mcq.keys())
        checks["mcq_fields"] = {
            "passed": not missing_mcq,
            "missing": sorted(missing_mcq),
        }
        if missing_mcq:
            return self._fail(f"Missing MCQ fields: {sorted(missing_mcq)}", checks)

        options = mcq.get("options", {})

        # ── 3. Options A/B/C/D ────────────────────────────────────────────
        required_opts = set(self.cfg.required_options)
        present_opts = set(options.keys()) if isinstance(options, dict) else set()
        options_ok = present_opts == required_opts
        checks["options"] = {
            "passed": options_ok,
            "found": sorted(present_opts),
            "required": sorted(required_opts),
        }
        if not options_ok:
            return self._fail(
                f"Options must be exactly A/B/C/D. Found: {sorted(present_opts)}", checks
            )

        # ── 4. Answer validity ────────────────────────────────────────────
        answer = str(mcq.get("answer", "")).strip().upper()
        answer_ok = answer in self.cfg.valid_answers
        checks["answer"] = {
            "passed": answer_ok,
            "value": answer,
            "valid_values": sorted(self.cfg.valid_answers),
        }
        if not answer_ok:
            return self._fail(f"Answer '{answer}' is not one of A/B/C/D", checks)

        # ── 5. Question length ────────────────────────────────────────────
        question = str(mcq.get("question", "")).strip()
        q_len = len(question)
        q_len_ok = self.cfg.min_question_length <= q_len <= self.cfg.max_question_length
        checks["question_length"] = {
            "passed": q_len_ok,
            "length": q_len,
            "min": self.cfg.min_question_length,
            "max": self.cfg.max_question_length,
        }
        if not q_len_ok:
            return self._fail(
                f"Question length {q_len} outside [{self.cfg.min_question_length},"
                f" {self.cfg.max_question_length}]",
                checks,
            )

        # ── 6. Explanation non-empty ──────────────────────────────────────
        explanation = str(mcq.get("explanation", "")).strip()
        exp_ok = len(explanation) >= self.cfg.min_explanation_length
        checks["explanation"] = {
            "passed": exp_ok,
            "length": len(explanation),
            "min": self.cfg.min_explanation_length,
        }
        if not exp_ok:
            return self._fail(
                f"Explanation too short ({len(explanation)} chars, "
                f"min={self.cfg.min_explanation_length})",
                checks,
            )

        # ── 7. Option texts non-empty ─────────────────────────────────────
        empty_opts = [k for k, v in options.items() if not str(v).strip()]
        opts_text_ok = len(empty_opts) == 0
        checks["option_texts"] = {
            "passed": opts_text_ok,
            "empty_options": empty_opts,
        }
        if not opts_text_ok:
            return self._fail(f"Option(s) have empty text: {empty_opts}", checks)

        # ── All passed ────────────────────────────────────────────────────
        log.debug("Format validation PASSED")
        return {"passed": True, "reason": "", "checks": checks}

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _fail(reason: str, checks: Dict) -> Dict:
        log.debug("Format validation FAILED: %s", reason)
        return {"passed": False, "reason": reason, "checks": checks}
