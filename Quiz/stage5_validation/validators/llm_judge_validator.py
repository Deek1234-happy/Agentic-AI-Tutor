"""
S5 — Stage 6: LLM-as-Judge
Final high-level quality evaluation using a language model.

This runs LAST and ONLY when all prior checks have passed,
since LLM calls are the most expensive operation in the pipeline.

Supports multiple providers:
  - "groq"      → Groq API (llama-3.3-70b-versatile or gpt-oss-120b, free tier)
  - "anthropic"  → Anthropic API (claude-sonnet-4-20250514)
  - "openai"     → OpenAI API (gpt-4o-mini by default)
  - "ollama"     → local Ollama server (offline-friendly)

The judge evaluates:
  1. correctness          (1-5)
  2. clarity              (1-5)
  3. distractor quality   (1-5)
  4. educational value    (1-5)
  5. chunk_grounding      (1-5)  ← replaces the NLI Stage 4 entailment check
  6. overall score        (weighted average, recomputed and validated locally)
  7. ambiguity flag       (bool)
  8. reject flag + reason

chunk_grounding checks three things the old NLI stage could not reliably do:
  - Is the correct answer directly stated or clearly implied by the chunk?
  - Does the question's topic match the chunk's primary subject (not just a
    tangential sentence)?
  - Could a reader derive the answer from the chunk alone, without outside
    knowledge?

Retry logic with exponential back-off handles transient errors and
Groq 429 rate-limit responses without killing the pipeline.
"""

import json
import logging
import re
import time
from typing import Any, Dict, Optional

# from config_llm_judge import LLMJudgeConfig, GROQ_MODELS

from config.settings import LLMJudgeConfig, GROQ_MODELS


log = logging.getLogger("s5.judge")

# ── Prompt templates ──────────────────────────────────────────────────────────

JUDGE_SYSTEM = (
    "You are a strict MCQ quality auditor for AI/ML educational content. "
    "Your job is to find flaws — assume every MCQ has at least one problem "
    "until proven otherwise. A score of 5 requires exceptional quality; "
    "most MCQs score 2–4. "
    "Pay special attention to chunk_grounding: many MCQs fail because their "
    "question or answer draws on information not actually present in the source "
    "chunk, or because the question is about a tangential sentence rather than "
    "the chunk's primary topic. "
    "Return ONLY a valid JSON object with no text outside it."
)

JUDGE_PROMPT = """
Evaluate the following MCQ critically.

SOURCE CHUNK:
{chunk_text}

QUESTION:
{question}

OPTIONS:
A) {opt_a}
B) {opt_b}
C) {opt_c}
D) {opt_d}

CORRECT ANSWER: {answer}

EXPLANATION:
{explanation}

---

Rate each criterion from 1–5:

- correctness:
  Is the answer fully supported by the chunk and unambiguously correct?

- clarity:
  Is the question clear, precise, and free from ambiguity?

- distractors:
  Are incorrect options plausible, distinct, and not obviously wrong?

- educational_value:
  Does the MCQ test meaningful understanding instead of trivia?

- chunk_grounding:
  Can the answer be derived from this chunk alone, and is the question aligned with the chunk’s main topic rather than a tangential detail?

Return ONLY this JSON structure (no extra text):
{{
  "correctness": <int 1-5>,
  "clarity": <int 1-5>,
  "distractors": <int 1-5>,
  "educational_value": <int 1-5>,
  "chunk_grounding": <int 1-5>,
  "ambiguous": <bool>,
  "overall": <float, weighted average>,
  "reject": <bool>,
  "reason": "<empty string if not rejected, otherwise brief reason>"
}}

Rules:
- overall = correctness*0.30 + clarity*0.20 + distractors*0.15 + educational_value*0.15 + chunk_grounding*0.20
- reject  = true if any criterion ≤ 2  OR  chunk_grounding < 3  OR  ambiguous is true  OR  overall < 3.5
- reason  = non-empty string explaining rejection (empty string if not rejected)
"""


class _RateLimitError(Exception):
    """Raised internally when a provider returns a rate-limit (429) response."""


class LLMJudgeValidator:
    """
    Calls an LLM to perform holistic quality evaluation of an MCQ.
    Provider-agnostic via the _call_llm() abstraction method.
    """

    def __init__(self, config: LLMJudgeConfig):
        self.cfg = config
        
        if getattr(self.cfg, "use_fallback_chain", False) and self.cfg.fallback_chain:
            self.cfg.fallback_chain_index = 0
            first_cfg = self.cfg.fallback_chain[0]
            self.cfg.provider = first_cfg.get("provider", "openai")
            self.cfg.model = first_cfg.get("model", self.cfg.model)
            self.cfg.base_url = first_cfg.get("base_url")
            self.cfg.api_key_env = first_cfg.get("api_key_env")
            
        self._resolved_model = self._resolve_model_name()
        log.info(
            "LLMJudgeValidator ready | provider=%s | model=%s",
            self.cfg.provider,
            self._resolved_model,
        )

    def validate(self, mcq_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Returns
        -------
        {
            "passed": bool,
            "reason": str,
            "scores": {
                "correctness":       float,
                "clarity":           float,
                "distractors":       float,
                "educational_value": float,
                "chunk_grounding":   float,
                "overall":           float,
                "ambiguous":         bool,
            },
            "raw_response": str,
        }
        """
        prompt = self._build_prompt(mcq_input)
        raw_response: str = ""
        parsed: Optional[Dict] = None

        attempt = 1
        while attempt <= self.cfg.max_retries:
            try:
                raw_response = self._call_llm(prompt)
                parsed = self._parse_json(raw_response)
                break
            except _RateLimitError as e:
                if attempt < self.cfg.max_retries:
                    wait = self.cfg.retry_delay * (2 ** (attempt - 1))
                    log.warning(
                        "Rate-limit hit (attempt %d/%d). Waiting %.1fs: %s",
                        attempt, self.cfg.max_retries, wait, e,
                    )
                    time.sleep(wait)
                    attempt += 1
                else:
                    # Max rate-limit attempts exhausted for this provider, try fallback
                    if getattr(self.cfg, "use_fallback_chain", False) and self.cfg.fallback_chain:
                        self.cfg.fallback_chain_index += 1
                        if self.cfg.fallback_chain_index < len(self.cfg.fallback_chain):
                            next_cfg = self.cfg.fallback_chain[self.cfg.fallback_chain_index]
                            log.warning(
                                "Max rate-limit attempts exhausted on %s. Switching permanently to fallback config: %s",
                                self.cfg.provider, next_cfg
                            )
                            self.cfg.provider = next_cfg.get("provider", "openai")
                            self.cfg.model = next_cfg.get("model", self.cfg.model)
                            self.cfg.base_url = next_cfg.get("base_url")
                            self.cfg.api_key_env = next_cfg.get("api_key_env")
                            self._resolved_model = self._resolve_model_name()
                            # Reset attempt counter for the new provider
                            attempt = 1
                            continue
                        else:
                            log.warning("Rate-limit hit, and all fallback chain configurations are exhausted!")
                            break
                    else:
                        break  # No fallback available, break the loop and fail the MCQ
            except Exception as e:
                log.warning(
                    "LLM judge attempt %d/%d failed: %s",
                    attempt, self.cfg.max_retries, e,
                )
                if attempt < self.cfg.max_retries:
                    time.sleep(self.cfg.retry_delay * attempt)
                attempt += 1

        if parsed is None:
            return {
                "passed": False,
                "reason": "LLM judge failed to return valid JSON after all retries",
                "scores": {},
                "raw_response": raw_response[:800],
            }

        scores = self._extract_scores(parsed)
        overall = scores.get("overall", 0.0)
        chunk_grounding = scores.get("chunk_grounding", 1.0)
        reject_flag = bool(parsed.get("reject", False))
        ambiguous = bool(parsed.get("ambiguous", False))
        llm_reason = str(parsed.get("reason", "")).strip()

        passed = (
            not reject_flag
            and not ambiguous
            and overall >= self.cfg.min_overall_score
            and chunk_grounding >= self.cfg.min_chunk_grounding_score
        )

        if not passed and not llm_reason:
            parts = []
            if reject_flag:
                parts.append("LLM judge marked as reject")
            if ambiguous:
                parts.append("question is ambiguous")
            if overall < self.cfg.min_overall_score:
                parts.append(
                    f"overall score {overall:.2f} < threshold {self.cfg.min_overall_score}"
                )
            if chunk_grounding < self.cfg.min_chunk_grounding_score:
                parts.append(
                    f"chunk grounding score {chunk_grounding:.0f} < "
                    f"threshold {self.cfg.min_chunk_grounding_score:.0f} "
                    f"(answer not sufficiently supported by source chunk)"
                )
            llm_reason = "; ".join(parts)

        return {
            "passed": passed,
            "reason": llm_reason if not passed else "",
            "scores": scores,
            "raw_response": raw_response[:800],
        }

    # ── Prompt building ───────────────────────────────────────────────────

    def _build_prompt(self, mcq_input: Dict) -> str:
        text = str(mcq_input.get("text", ""))[:1200]
        mcq = mcq_input.get("mcq", {})
        options = mcq.get("options", {})
        return JUDGE_PROMPT.format(
            chunk_text=text,
            question=mcq.get("question", ""),
            opt_a=options.get("A", ""),
            opt_b=options.get("B", ""),
            opt_c=options.get("C", ""),
            opt_d=options.get("D", ""),
            answer=mcq.get("answer", ""),
            explanation=mcq.get("explanation", ""),
        )

    # ── JSON parsing ──────────────────────────────────────────────────────

    def _parse_json(self, text: str) -> Dict:
        """
        Robustly parse JSON from LLM output.
        Handles markdown fences, leading/trailing whitespace, etc.
        """
        cleaned = re.sub(r"```(?:json)?", "", text).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        raise ValueError(f"No valid JSON found in: {cleaned[:200]}")

    def _extract_scores(self, parsed: Dict) -> Dict:
        def clamp(v, lo=1, hi=5):
            try:
                return max(lo, min(hi, float(v)))
            except (TypeError, ValueError):
                return float(lo)

        correctness     = clamp(parsed.get("correctness",       1))
        clarity         = clamp(parsed.get("clarity",           1))
        distractors     = clamp(parsed.get("distractors",       1))
        edu_value       = clamp(parsed.get("educational_value", 1))
        chunk_grounding = clamp(parsed.get("chunk_grounding",   1))

        # Always recompute from the fixed formula; accept LLM value only
        # if it is within ±0.3 of the computed result (guards against
        # hallucinated out-of-range values such as 9.5).
        computed = round(
            correctness     * 0.30
            + clarity       * 0.20
            + distractors   * 0.15
            + edu_value     * 0.15
            + chunk_grounding * 0.20,
            3,
        )
        overall = computed
        llm_overall_raw = parsed.get("overall")
        if llm_overall_raw is not None:
            try:
                llm_overall = round(float(llm_overall_raw), 3)
                if abs(llm_overall - computed) <= 0.3:
                    overall = llm_overall
                else:
                    log.warning(
                        "LLM overall (%.3f) deviates from computed (%.3f) — using computed.",
                        llm_overall, computed,
                    )
            except (TypeError, ValueError):
                pass

        return {
            "correctness":       correctness,
            "clarity":           clarity,
            "distractors":       distractors,
            "educational_value": edu_value,
            "chunk_grounding":   chunk_grounding,
            "overall":           overall,
            "ambiguous":         bool(parsed.get("ambiguous", False)),
        }

    # ── Model name resolution ─────────────────────────────────────────────

    def _resolve_model_name(self) -> str:
        """Map short aliases to full API model strings for the active provider."""
        if self.cfg.provider == "groq":
            return GROQ_MODELS.get(self.cfg.model.lower(), self.cfg.model)
        return self.cfg.model

    # ── LLM provider abstraction ──────────────────────────────────────────

    def _call_llm(self, prompt: str) -> str:
        provider = self.cfg.provider.lower()
        if provider == "groq":
            return self._call_groq(prompt)
        elif provider == "anthropic":
            return self._call_anthropic(prompt)
        elif provider == "openai":
            return self._call_openai(prompt)
        elif provider == "ollama":
            return self._call_ollama(prompt)
        else:
            raise ValueError(f"Unknown LLM provider: {provider!r}")

    def _call_groq(self, prompt: str) -> str:
        try:
            from groq import Groq, RateLimitError as GroqRateLimitError
        except ImportError as exc:
            raise ImportError(
                "groq package not installed. Run: pip install groq"
            ) from exc

        client = Groq(api_key=self.cfg.groq_api_key)
        try:
            response = client.chat.completions.create(
                model=self._resolved_model,
                messages=[
                    {"role": "system", "content": JUDGE_SYSTEM},
                    {"role": "user",   "content": prompt},
                ],
                max_tokens=1024,
                temperature=self.cfg.temperature,
                response_format={"type": "json_object"},
            )
        except GroqRateLimitError as e:
            raise _RateLimitError(str(e)) from e
        except Exception as e:
            # Groq's underlying exceptions usually inherit from APIStatusError
            # Check if it's a 402 or if it mentions credits
            if hasattr(e, "status_code") and getattr(e, "status_code") == 402:
                raise _RateLimitError(str(e)) from e
            if "credit" in str(e).lower() or "rate limit" in str(e).lower():
                raise _RateLimitError(str(e)) from e
            raise

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Groq returned an empty response.")
        return content

    def _call_anthropic(self, prompt: str) -> str:
        import anthropic
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=self.cfg.model,
            max_tokens=512,
            system=JUDGE_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    def _call_openai(self, prompt: str) -> str:
        import openai
        
        # If a custom base_url is set, pass it to the client
        client_kwargs = {}
        if self.cfg.base_url:
            client_kwargs["base_url"] = self.cfg.base_url
            
        if getattr(self.cfg, "api_key_env", None):
            import os
            key = os.environ.get(self.cfg.api_key_env)
            if key:
                client_kwargs["api_key"] = key
                
        client = openai.OpenAI(**client_kwargs)
        try:
            response = client.chat.completions.create(
                model=self.cfg.model or "gpt-4o-mini",
                messages=[
                    {"role": "system", "content": JUDGE_SYSTEM},
                    {"role": "user",   "content": prompt},
                ],
                max_tokens=1024,
                temperature=self.cfg.temperature,
                response_format={"type": "json_object"},
            )
        except openai.RateLimitError as e:
            raise _RateLimitError(str(e)) from e
        except openai.APIStatusError as e:
            # 402 Payment Required (e.g. out of credits on OpenRouter/Together)
            if e.status_code == 402 or "credit" in str(e).lower() or "rate limit" in str(e).lower():
                raise _RateLimitError(str(e)) from e
            raise
        return response.choices[0].message.content

    def _call_ollama(self, prompt: str) -> str:
        import requests
        payload = {
            "model":   self.cfg.model,
            "prompt":  JUDGE_SYSTEM + "\n\n" + prompt,
            "stream":  False,
            "options": {"temperature": self.cfg.temperature},
        }
        r = requests.post(
            f"{self.cfg.ollama_base_url}/api/generate",
            json=payload,
            timeout=self.cfg.timeout,
        )
        r.raise_for_status()
        return r.json().get("response", "")