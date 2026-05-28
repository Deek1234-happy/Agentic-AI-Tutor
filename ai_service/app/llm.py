# app/llm.py

import os
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence, Tuple

import requests
from dotenv import load_dotenv

# Load .env file
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# ===============================
# LLM Provider Configuration
# ===============================

LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_URL = os.getenv("LLM_URL", "https://api.groq.com/openai/v1/chat/completions")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")


# ===============================
# Generic LLM Completion
# ===============================

@dataclass(frozen=True)
class LLMFailure(Exception):
    kind: str  # "rate_limit" | "token_limit" | "auth" | "timeout" | "http" | "network" | "unknown"
    message: str
    status_code: Optional[int] = None
    model: Optional[str] = None

    def __str__(self) -> str:
        s = f"{self.kind}: {self.message}"
        if self.status_code is not None:
            s += f" (status={self.status_code})"
        if self.model:
            s += f" (model={self.model})"
        return s


def _parse_failure(resp: requests.Response, model: str) -> LLMFailure:
    status = resp.status_code
    text = (resp.text or "").strip()

    retry_after = resp.headers.get("retry-after")
    # keep retry-after parsing in the caller; here we only classify

    # Best-effort parse OpenAI-style error object
    err_msg = ""
    err_type = ""
    try:
        j = resp.json()
        if isinstance(j, dict) and isinstance(j.get("error"), dict):
            err_msg = str(j["error"].get("message") or "").strip()
            err_type = str(j["error"].get("type") or "").strip()
    except Exception:
        pass

    msg = err_msg or text or f"HTTP {status}"
    msg_l = msg.lower()
    err_type_l = err_type.lower()

    if status == 429 or "rate limit" in msg_l or "too many requests" in msg_l or "rate_limit" in err_type_l:
        return LLMFailure(kind="rate_limit", message=msg, status_code=status, model=model)

    # Token / context errors vary by provider; treat as token_limit when message hints at it.
    if (
        "context length" in msg_l
        or "maximum context" in msg_l
        or "max context" in msg_l
        or "too many tokens" in msg_l
        or "token limit" in msg_l
        or "request too large" in msg_l
        or "prompt is too long" in msg_l
        or "context_window_exceeded" in err_type_l
    ):
        return LLMFailure(kind="token_limit", message=msg, status_code=status, model=model)

    if status in (401, 403) or "invalid api key" in msg_l or "unauthorized" in msg_l:
        return LLMFailure(kind="auth", message=msg, status_code=status, model=model)

    if status >= 500:
        return LLMFailure(kind="http", message=msg, status_code=status, model=model)

    return LLMFailure(kind="unknown", message=msg, status_code=status, model=model)


def _sleep_with_jitter(seconds: float) -> None:
    seconds = max(0.0, float(seconds))
    jitter = random.uniform(0.0, min(1.0, seconds * 0.1))
    time.sleep(seconds + jitter)


def _compute_backoff(attempt: int, base: float = 1.5, cap: float = 60.0) -> float:
    # attempt is 1-based: attempt=1 => ~base, attempt=2 => ~base^2, ...
    return min(cap, base ** max(1, attempt))


def _default_fallback_models(primary: str) -> Tuple[str, ...]:
    """
    Hardcoded fallback list. These do NOT need to exist in .env.
    The provider may not support all of them; failures will be handled and skipped.

    Ordering matters: earlier = preferred fallback.
    """
    candidates = [
        # Frequently available "small-ish" chat models on OpenAI-compatible gateways.
        "llama-3.1-8b-instant",
        "llama-3.2-3b-preview",
        "gemma2-9b-it",
        "mixtral-8x7b-32768",
    ]
    primary = (primary or "").strip()
    return tuple([m for m in candidates if m and m != primary])


def generate_answer(
    prompt: str,
    temperature: float = 0.1,
    *,
    model: Optional[str] = None,
    fallback_models: Optional[Sequence[str]] = None,
    max_retries_per_model: int = 5,
) -> str:
    """
    Generic LLM completion function.
    Works with Groq (OpenAI-compatible API).
    You can switch providers without changing function name.
    """

    # Re-read in case env vars were loaded after module import.
    api_key = os.getenv("LLM_API_KEY") or LLM_API_KEY
    if not api_key:
        raise RuntimeError("LLM_API_KEY is not set in environment variables")

    primary_model = (model or os.getenv("LLM_MODEL") or LLM_MODEL).strip()
    fallbacks = list(fallback_models) if fallback_models is not None else list(_default_fallback_models(primary_model))
    model_chain = [primary_model] + [m for m in fallbacks if m and str(m).strip()]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    last_failure: Optional[LLMFailure] = None

    for m in model_chain:
        m = str(m).strip()
        if not m:
            continue

        payload = {
            "model": m,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }

        for attempt in range(1, max(1, int(max_retries_per_model)) + 1):
            try:
                response = requests.post(
                    LLM_URL,
                    headers=headers,
                    json=payload,
                    timeout=90,
                )
            except requests.Timeout as exc:
                last_failure = LLMFailure(kind="timeout", message=str(exc), model=m)
                _sleep_with_jitter(_compute_backoff(attempt))
                continue
            except requests.RequestException as exc:
                last_failure = LLMFailure(kind="network", message=str(exc), model=m)
                _sleep_with_jitter(_compute_backoff(attempt))
                continue

            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()

            failure = _parse_failure(response, model=m)
            last_failure = failure

            # Auth failures won't succeed with retry or model switching.
            if failure.kind == "auth":
                raise failure

            # If token limit, immediately try a smaller model (no pointless retries).
            if failure.kind == "token_limit":
                break

            # Rate limiting: honor Retry-After when present, else backoff.
            if failure.kind == "rate_limit":
                ra = response.headers.get("retry-after")
                if ra:
                    try:
                        _sleep_with_jitter(float(ra))
                        continue
                    except ValueError:
                        pass

            _sleep_with_jitter(_compute_backoff(attempt))

        # next model in chain

    raise last_failure or LLMFailure(kind="unknown", message="LLM request failed with no response")