# app/quiz/quiz_slot_selector.py
"""
Smart slot selector — picks the best N slots to maximise quiz diversity.

Sits between prepare_all_model_inputs() and generate_mcqs() in the pipeline:

    all_slots = prepare_all_model_inputs(chunks, mcqs_per_chunk=4)
    selected  = select_slots(all_slots, requested_count=10)
    mcqs      = generate_mcqs(selected)

Selection priorities (deterministic, no randomness):
  1. Chunk coverage   — spread slots across as many chunks as possible
  2. Bloom diversity  — avoid quizzes dominated by a single Bloom level
  3. Concept coverage — prefer distinct concepts over duplicates
  4. Slot quality     — prefer named > reuse > inferred slot types

Public API:
    from .quiz_slot_selector import select_slots
"""

import logging
from collections import Counter, defaultdict
from typing import Dict, List

log = logging.getLogger("quiz_slot_selector")


# Slot type priority — higher is better
_SLOT_TYPE_PRIORITY = {
    "named":    3,
    "reuse":    2,
    "inferred": 1,
}

# Bloom level ordering for diversity scoring
_BLOOM_ORDER = ["remember", "understand", "apply", "analyze", "evaluate", "create"]


def _slot_priority_key(slot: Dict) -> tuple:
    """
    Deterministic sort key for ranking slots within a chunk.

    Sorting order (descending preference):
      1. Slot type priority  (named=3 > reuse=2 > inferred=1)
      2. Bloom level index   (lower index first for deterministic ordering)
      3. Concept name        (alphabetical for deterministic tie-breaking)

    Returns a tuple suitable for sorted(..., key=..., reverse=True).
    """
    meta = slot.get("slot_metadata", {})
    type_score = _SLOT_TYPE_PRIORITY.get(meta.get("slot_type", "inferred"), 0)
    bloom = meta.get("bloom_level", "understand").lower()
    bloom_idx = _BLOOM_ORDER.index(bloom) if bloom in _BLOOM_ORDER else 2
    concept = meta.get("concept", "")
    return (type_score, -bloom_idx, concept)


def _least_represented_bloom(
    bloom_counts: Counter,
    candidate_blooms: List[str],
) -> str:
    """
    Among candidate Bloom levels, return the one with the lowest count
    in the current selection. Ties broken by Bloom ordering (lower index wins).
    """
    best = None
    best_count = float("inf")
    best_idx = float("inf")

    for bloom in candidate_blooms:
        count = bloom_counts.get(bloom, 0)
        idx = _BLOOM_ORDER.index(bloom) if bloom in _BLOOM_ORDER else 99
        if count < best_count or (count == best_count and idx < best_idx):
            best = bloom
            best_count = count
            best_idx = idx

    return best


def select_slots(
    model_inputs: List[Dict],
    requested_count: int,
) -> List[Dict]:
    """
    Select up to `requested_count` slots from the full pool, maximising
    diversity across chunks, Bloom levels, and concepts.

    Algorithm (deterministic, multi-pass):

      Pass 1 — Chunk coverage:
        Round-robin one slot from each unique chunk_id.
        Within each chunk, pick the highest-priority slot whose Bloom level
        is least represented in the selection so far.

      Pass 2 — Bloom diversity fill:
        From remaining un-selected slots, repeatedly pick the slot whose
        Bloom level is least represented. Break ties by:
          a) chunk with fewest slots already selected
          b) slot type priority (named > reuse > inferred)
          c) concept alphabetical order

      Pass 3 — Remaining fill:
        If still below requested_count, fill from remaining slots using
        the same composite ranking.

    Returns:
        List of selected model_input dicts (order matches selection priority).
        Length = min(requested_count, len(model_inputs)).
    """
    total_available = len(model_inputs)

    if requested_count <= 0:
        log.warning("[SlotSelector] requested_count=%d, returning empty list", requested_count)
        return []

    # If requested >= available, return all (no selection needed)
    if requested_count >= total_available:
        log.info(
            "[SlotSelector] Requested %d >= available %d -> returning all slots",
            requested_count, total_available,
        )
        _log_distribution(model_inputs, requested_count, total_available)
        return list(model_inputs)

    # ── Group slots by chunk_id ──────────────────────────────────
    chunk_slots: Dict[str, List[int]] = defaultdict(list)  # chunk_id → [indices]
    for idx, inp in enumerate(model_inputs):
        chunk_id = inp.get("slot_metadata", {}).get("chunk_id", f"unknown_{idx}")
        chunk_slots[chunk_id].append(idx)

    # Sort chunk_ids deterministically (alphabetical)
    chunk_ids = sorted(chunk_slots.keys())

    # Sort slots within each chunk by priority (best first)
    for cid in chunk_ids:
        chunk_slots[cid].sort(
            key=lambda i: _slot_priority_key(model_inputs[i]),
            reverse=True,
        )

    # ── Selection state ──────────────────────────────────────────
    selected_indices: List[int] = []
    selected_set: set = set()
    bloom_counts: Counter = Counter()
    chunk_counts: Counter = Counter()
    concept_set: set = set()

    def _add_slot(idx: int) -> None:
        """Add a slot index to the selection and update tracking counters."""
        selected_indices.append(idx)
        selected_set.add(idx)
        meta = model_inputs[idx].get("slot_metadata", {})
        bloom_counts[meta.get("bloom_level", "understand").lower()] += 1
        chunk_counts[meta.get("chunk_id", "")] += 1
        concept_set.add(meta.get("concept", "").lower())

    # ── Pass 1: One slot per chunk (round-robin) ─────────────────
    for cid in chunk_ids:
        if len(selected_indices) >= requested_count:
            break

        candidates = [i for i in chunk_slots[cid] if i not in selected_set]
        if not candidates:
            continue

        # Pick the candidate whose Bloom level is least represented
        candidate_blooms = [
            model_inputs[i].get("slot_metadata", {}).get("bloom_level", "understand").lower()
            for i in candidates
        ]
        target_bloom = _least_represented_bloom(bloom_counts, candidate_blooms)

        # Find the first candidate matching the target Bloom
        best = None
        for i in candidates:
            bloom = model_inputs[i].get("slot_metadata", {}).get("bloom_level", "understand").lower()
            if bloom == target_bloom:
                best = i
                break
        if best is None:
            best = candidates[0]

        _add_slot(best)

    # ── Pass 2 & 3: Fill remaining slots ─────────────────────────
    remaining = [i for i in range(total_available) if i not in selected_set]

    while len(selected_indices) < requested_count and remaining:
        # Score each remaining slot
        best_idx = None
        best_score = None

        for i in remaining:
            meta = model_inputs[i].get("slot_metadata", {})
            bloom = meta.get("bloom_level", "understand").lower()
            cid = meta.get("chunk_id", "")
            concept = meta.get("concept", "").lower()
            slot_type = meta.get("slot_type", "inferred")

            # Lower bloom count = higher priority (invert for sorting)
            bloom_score = -(bloom_counts.get(bloom, 0))

            # Lower chunk count = higher priority (spread across chunks)
            chunk_score = -(chunk_counts.get(cid, 0))

            # Unseen concept = bonus
            concept_score = 0 if concept in concept_set else 1

            # Slot type priority
            type_score = _SLOT_TYPE_PRIORITY.get(slot_type, 0)

            # Bloom index for deterministic tie-breaking
            bloom_idx = _BLOOM_ORDER.index(bloom) if bloom in _BLOOM_ORDER else 99

            # Composite score tuple — Python sorts tuples element-by-element
            # Higher is better for all components
            score = (bloom_score, chunk_score, concept_score, type_score, -bloom_idx, concept)

            if best_score is None or score > best_score:
                best_score = score
                best_idx = i

        if best_idx is None:
            break

        _add_slot(best_idx)
        remaining.remove(best_idx)

    selected = [model_inputs[i] for i in selected_indices]
    _log_distribution(selected, requested_count, total_available)
    return selected


def _log_distribution(
    selected: List[Dict],
    requested_count: int,
    total_available: int,
) -> None:
    """
    Print a summary of the slot selection to the terminal and log file.
    Shows requested vs available vs selected, chunk distribution, and
    Bloom level distribution.
    """
    # ANSI color codes
    RESET = "\033[0m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"

    chunk_dist: Counter = Counter()
    bloom_dist: Counter = Counter()

    for inp in selected:
        meta = inp.get("slot_metadata", {})
        chunk_dist[meta.get("chunk_id", "?")] += 1
        bloom_dist[meta.get("bloom_level", "?").lower()] += 1

    n_selected = len(selected)

    print(f"\n{CYAN}{'-'*60}{RESET}", flush=True)
    print(f"{BOLD}[SlotSelector]{RESET} Slot Selection Summary", flush=True)
    print(f"{CYAN}{'-'*60}{RESET}", flush=True)
    print(f"  Requested:  {BOLD}{requested_count}{RESET}", flush=True)
    print(f"  Available:  {BOLD}{total_available}{RESET}", flush=True)
    print(f"  Selected:   {BOLD}{n_selected}{RESET}", flush=True)

    if requested_count > total_available:
        print(
            f"  {BOLD}NOTE:{RESET} Requested exceeds available. "
            f"Returning all {total_available} slots.",
            flush=True,
        )

    # Chunk distribution
    print(f"\n  {BOLD}Chunk Distribution:{RESET}", flush=True)
    for cid in sorted(chunk_dist.keys()):
        label = cid[:16] if len(cid) > 16 else cid
        print(f"    {label:<18} -> {chunk_dist[cid]} slot(s)", flush=True)

    # Bloom distribution
    print(f"\n  {BOLD}Bloom Distribution:{RESET}", flush=True)
    for bloom in _BLOOM_ORDER:
        count = bloom_dist.get(bloom, 0)
        if count > 0:
            print(f"    {bloom:<12} -> {count}", flush=True)

    print(f"{CYAN}{'-'*60}{RESET}\n", flush=True)

    log.info(
        "[SlotSelector] Selected %d/%d slots (requested=%d). "
        "Chunks=%s, Blooms=%s",
        n_selected, total_available, requested_count,
        dict(chunk_dist), dict(bloom_dist),
    )
