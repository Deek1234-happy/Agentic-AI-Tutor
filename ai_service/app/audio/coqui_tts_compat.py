"""
Shims for Coqui TTS 0.22 with newer PyTorch / transformers.

- PyTorch 2.6+ defaults torch.load(..., weights_only=True). Coqui XTTS checkpoints
  pickle config classes (e.g. XttsConfig); load fails until weights_only=False.
  We only set the default when the caller omitted it (explicit True stays).

- transformers 4.5x+ often omits BeamSearchScorer from the package root; Coqui's
  stream_generator imports it from transformers. Aliases are added if missing.

Import this module before `from TTS.api import TTS` (see xtts_tts.py).
"""

from __future__ import annotations


def _apply_torch_load_weights_compat() -> None:
    import functools
    import inspect

    import torch

    if getattr(torch.load, "_coqui_tts_weights_compat", False):
        return

    _real = torch.load
    try:
        if "weights_only" not in inspect.signature(_real).parameters:
            return
    except (TypeError, ValueError):
        return

    @functools.wraps(_real)
    def _load(*args, **kwargs):
        kwargs.setdefault("weights_only", False)
        return _real(*args, **kwargs)

    _load._coqui_tts_weights_compat = True
    torch.load = _load


def _apply_transformers_beam_search_aliases() -> None:
    import transformers

    if hasattr(transformers, "BeamSearchScorer"):
        return
    try:
        from transformers.generation.beam_search import (
            BeamSearchScorer,
            ConstrainedBeamSearchScorer,
        )
    except Exception:
        return
    transformers.BeamSearchScorer = BeamSearchScorer
    transformers.ConstrainedBeamSearchScorer = ConstrainedBeamSearchScorer


_apply_torch_load_weights_compat()
_apply_transformers_beam_search_aliases()
