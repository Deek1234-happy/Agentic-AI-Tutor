"""
Reprocess Failed Metadata
=========================
Scans existing metadata output files in data/metadata/ (both usable/ and
not_usable/) and identifies chunks that need reprocessing:

  1. Chunks whose concepts == ["general concept"]  (LLM extraction failed)
  2. The first 100 chunks from all_chunks_1 (trial run, need a redo)

For each chunk that needs reprocessing, the script:
  - Looks up the original chunk data from data/global_chunks/
  - Calls the Groq LLM again to extract proper metadata
  - Writes a NEW combined output file that contains:
      • Corrected metadata for the reprocessed chunks
      • Unchanged metadata for chunks that were already correct

The new output is written to data/metadata_fixed/ (usable/ and not_usable/).

Usage:
    python app/reprocess_failed_metadata.py
    python app/reprocess_failed_metadata.py --api-key YOUR_KEY
    python app/reprocess_failed_metadata.py --dry-run        # preview without calling LLM
"""

import os
import json
import time
import logging
import argparse
import re
from pathlib import Path
from typing import Optional

# ── reuse functions from metadata_extraction.py ──────────────────────────────
from metadata_extraction import (
    load_dotenv_file,
    load_jsonl,
    call_groq,
    SYSTEM_PROMPT,
    BATCH_SIZE,
    _merge,
    _fallback_metadata,
    _validate_metadata,
)

from groq import Groq

# ── logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("reprocess_metadata")

# ── paths ────────────────────────────────────────────────────────────────────
METADATA_DIR   = Path("data/metadata")
CHUNKS_DIR     = Path("data/global_chunks")
OUTPUT_DIR     = Path("data/metadata_fixed")
CACHE_FILENAME = "_reprocessed_cache.jsonl"   # incremental save file

# ── criteria for reprocessing ────────────────────────────────────────────────
TRIAL_FILE_STEM     = "all_chunks_1"          # file containing trial chunks
TRIAL_CHUNK_COUNT   = 0                     # first 100 chunks are trial


def _extract_chunk_index(chunk_id: str) -> Optional[int]:
    """
    Extract the numeric index from a chunk_id like 'hands-on-machine-learning_42'.
    Returns the integer index or None if the format is unexpected.
    """
    parts = chunk_id.rsplit("_", 1)
    if len(parts) == 2 and parts[1].isdigit():
        return int(parts[1])
    return None


def needs_reprocessing(record: dict, source_file_stem: str) -> bool:
    """
    Return True if a metadata record should be reprocessed.

    Conditions (OR):
      1. concepts == ["general concept"]  → LLM failed
      2. chunk belongs to the first TRIAL_CHUNK_COUNT chunks of TRIAL_FILE_STEM
    """
    meta = record.get("metadata", {})
    concepts = meta.get("concepts", [])

    # Condition 1: failed extraction
    if concepts == ["general concept"]:
        return True

    # Condition 2: trial chunks (first 100 in all_chunks_1)
    if source_file_stem == TRIAL_FILE_STEM:
        idx = _extract_chunk_index(record.get("chunk_id", ""))
        if idx is not None and 1 <= idx <= TRIAL_CHUNK_COUNT:
            return True

    return False


def load_source_chunks(chunks_dir: Path) -> dict[str, dict]:
    """
    Load all source chunks from global_chunks/ into a dict keyed by chunk_id.
    """
    chunk_map = {}
    for jf in sorted(chunks_dir.glob("*.jsonl")):
        if "backup" in jf.stem.lower():
            continue
        for line in jf.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                chunk = json.loads(line)
                chunk_map[chunk["chunk_id"]] = chunk
            except (json.JSONDecodeError, KeyError):
                pass
    log.info(f"Loaded {len(chunk_map)} source chunks from {chunks_dir}")
    return chunk_map


def load_all_metadata(metadata_dir: Path) -> dict[str, dict[str, list[dict]]]:
    """
    Load all metadata records from usable/ and not_usable/ sub-folders.

    Returns a nested dict:
        {
            file_stem: {           # e.g. "all_chunks_1_meta"
                "usable": [...],
                "not_usable": [...]
            }
        }
    """
    result = {}

    for subfolder in ("usable", "not_usable"):
        folder = metadata_dir / subfolder
        if not folder.exists():
            continue
        for jf in sorted(folder.glob("*.jsonl")):
            stem = jf.stem  # e.g. "all_chunks_1_meta"
            if stem not in result:
                result[stem] = {"usable": [], "not_usable": []}
            records = load_jsonl(str(jf))
            result[stem][subfolder] = records
            log.info(f"  Loaded {len(records)} records from {subfolder}/{jf.name}")

    return result


def determine_source_file_stem(meta_file_stem: str) -> str:
    """
    Convert a metadata file stem like 'all_chunks_1_meta' back to the
    source file stem 'all_chunks_1'.
    """
    if meta_file_stem.endswith("_meta"):
        return meta_file_stem[:-5]
    return meta_file_stem


def load_cache(cache_path: Path) -> dict[str, dict]:
    """
    Load already-reprocessed records from the cache file.
    Returns a dict: chunk_id → record.
    """
    cache = {}
    if not cache_path.exists():
        return cache
    for line in cache_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
            cid = record.get("chunk_id")
            if cid:
                cache[cid] = record
        except json.JSONDecodeError:
            pass
    log.info(f"Loaded {len(cache)} records from cache: {cache_path.name}")
    return cache


def append_to_cache(cache_path: Path, records: list[dict]) -> None:
    """
    Append one or more records to the cache file (immediate save).
    """
    with open(cache_path, "a", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def reprocess_chunks(
    client: Groq,
    chunks_to_reprocess: list[dict],
    cache_path: Path,
    dry_run: bool = False,
) -> dict[str, dict]:
    """
    Call the LLM to reprocess a list of source chunks.
    Each batch is saved immediately to ``cache_path`` so the run can be
    resumed later if the API hits rate limits.
    Returns a dict: chunk_id → new metadata record (merged chunk + metadata).
    """
    # Load any previously-cached results (from an interrupted run)
    results = load_cache(cache_path)
    already_done = len(results)

    # Filter out chunks that were already reprocessed in a previous run
    pending = [c for c in chunks_to_reprocess if c["chunk_id"] not in results]
    total = len(chunks_to_reprocess)

    if already_done:
        log.info(
            f"Resuming: {already_done} already cached, "
            f"{len(pending)} remaining out of {total}"
        )

    if not pending:
        log.info("All chunks already reprocessed (found in cache). Nothing to do.")
        return results

    log.info(f"Reprocessing {len(pending)} chunks...")

    processed = 0
    errors = 0

    for batch_start in range(0, len(pending), BATCH_SIZE):
        batch = pending[batch_start : batch_start + BATCH_SIZE]

        if dry_run:
            for chunk in batch:
                log.info(f"  [DRY RUN] Would reprocess: {chunk['chunk_id']}")
                results[chunk["chunk_id"]] = None
            continue

        metadata_list = call_groq(client, batch)

        batch_records = []  # collect for immediate cache save

        if metadata_list is None:
            log.error(
                f"Failed batch at position {batch_start}. "
                f"Using fallback for {len(batch)} chunks."
            )
            for chunk in batch:
                record = _merge(chunk, _fallback_metadata(chunk["chunk_id"]))
                results[chunk["chunk_id"]] = record
                batch_records.append(record)
                errors += 1
        else:
            for chunk, meta in zip(batch, metadata_list):
                record = _merge(chunk, meta)
                results[chunk["chunk_id"]] = record
                batch_records.append(record)
                processed += 1

        # ── autosave: append this batch to the cache file immediately ──
        if batch_records:
            append_to_cache(cache_path, batch_records)

        # Respect rate limits
        time.sleep(1.5)

        batch_num = batch_start // BATCH_SIZE + 1
        if batch_num % 20 == 0:
            done_now = already_done + processed + errors
            log.info(
                f"  Progress: {done_now}/{total} chunks done "
                f"({processed} new, {errors} fallback)"
            )

    log.info(
        f"Reprocessing done: {processed} succeeded, {errors} fallback, "
        f"{already_done} from cache, {total} total"
    )
    return results


def build_fixed_output(
    all_metadata: dict[str, dict[str, list[dict]]],
    source_chunks: dict[str, dict],
    reprocessed: dict[str, dict],
    output_dir: Path,
    dry_run: bool = False,
):
    """
    Build the final merged output files in output_dir/usable/ and output_dir/not_usable/.

    For each metadata file:
      - If a chunk was reprocessed, use the new record
      - Otherwise, keep the original record unchanged
    """
    usable_dir = output_dir / "usable"
    not_usable_dir = output_dir / "not_usable"
    usable_dir.mkdir(parents=True, exist_ok=True)
    not_usable_dir.mkdir(parents=True, exist_ok=True)

    stats = {"kept": 0, "replaced": 0, "usable": 0, "not_usable": 0}

    for meta_stem, categories in all_metadata.items():
        usable_out = usable_dir / f"{meta_stem}.jsonl"
        not_usable_out = not_usable_dir / f"{meta_stem}.jsonl"

        usable_records = []
        not_usable_records = []

        # Combine all records from both usable and not_usable for this file
        all_records = []
        for record in categories.get("usable", []):
            all_records.append(record)
        for record in categories.get("not_usable", []):
            all_records.append(record)

        # De-duplicate by chunk_id (keep last occurrence)
        seen = {}
        for record in all_records:
            cid = record.get("chunk_id")
            if cid:
                seen[cid] = record

        # Process each unique chunk
        for cid, original_record in seen.items():
            if cid in reprocessed and reprocessed[cid] is not None:
                record = reprocessed[cid]
                stats["replaced"] += 1
            else:
                record = original_record
                stats["kept"] += 1

            # Route to usable or not_usable
            is_usable = record.get("metadata", {}).get("usable", True)
            if is_usable:
                usable_records.append(record)
                stats["usable"] += 1
            else:
                not_usable_records.append(record)
                stats["not_usable"] += 1

        if dry_run:
            log.info(
                f"  [DRY RUN] {meta_stem}: "
                f"{len(usable_records)} usable, {len(not_usable_records)} not_usable"
            )
            continue

        # Sort records by chunk index for deterministic output
        def _sort_key(r):
            idx = _extract_chunk_index(r.get("chunk_id", ""))
            return idx if idx is not None else 999999

        usable_records.sort(key=_sort_key)
        not_usable_records.sort(key=_sort_key)

        # Write output files
        with open(usable_out, "w", encoding="utf-8") as f:
            for record in usable_records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        with open(not_usable_out, "w", encoding="utf-8") as f:
            for record in not_usable_records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        log.info(
            f"  {meta_stem}: wrote {len(usable_records)} usable, "
            f"{len(not_usable_records)} not_usable"
        )

    log.info(f"\n{'='*55}")
    log.info(f"Merge Summary:")
    log.info(f"  Replaced (reprocessed): {stats['replaced']}")
    log.info(f"  Kept (unchanged):       {stats['kept']}")
    log.info(f"  Total usable:           {stats['usable']}")
    log.info(f"  Total not_usable:       {stats['not_usable']}")
    log.info(f"  Output directory:       {output_dir}")
    log.info(f"{'='*55}")


# ── CLI ──────────────────────────────────────────────────────────────────────
def parse_args():
    p = argparse.ArgumentParser(
        description="Reprocess failed metadata chunks and merge with correct ones"
    )
    p.add_argument(
        "--metadata-dir",
        default=str(METADATA_DIR),
        help=f"Path to existing metadata directory (default: {METADATA_DIR})",
    )
    p.add_argument(
        "--chunks-dir",
        default=str(CHUNKS_DIR),
        help=f"Path to source chunks directory (default: {CHUNKS_DIR})",
    )
    p.add_argument(
        "--output",
        default=str(OUTPUT_DIR),
        help=f"Path to write fixed metadata (default: {OUTPUT_DIR})",
    )
    p.add_argument(
        "--api-key",
        default=None,
        help="Groq API key (defaults to GROQ_API_KEY env variable)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview which chunks would be reprocessed without calling the LLM",
    )
    return p.parse_args()


def main():
    # Auto-load variables from app/.env
    load_dotenv_file(Path(__file__).with_name(".env"))

    args = parse_args()

    metadata_dir = Path(args.metadata_dir)
    chunks_dir = Path(args.chunks_dir)
    output_dir = Path(args.output)
    cache_path = output_dir / CACHE_FILENAME

    # Ensure output dir exists (cache file lives here)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Step 1: Load everything ──────────────────────────────────────────
    log.info("=" * 55)
    log.info("Step 1: Loading existing metadata and source chunks")
    log.info("=" * 55)

    all_metadata = load_all_metadata(metadata_dir)
    source_chunks = load_source_chunks(chunks_dir)

    # ── Step 2: Identify chunks to reprocess ─────────────────────────────
    log.info("\n" + "=" * 55)
    log.info("Step 2: Identifying chunks that need reprocessing")
    log.info("=" * 55)

    to_reprocess_ids = set()
    reason_counts = {"general_concept": 0, "trial_chunk": 0}

    for meta_stem, categories in all_metadata.items():
        source_stem = determine_source_file_stem(meta_stem)
        for subfolder in ("usable", "not_usable"):
            for record in categories.get(subfolder, []):
                if needs_reprocessing(record, source_stem):
                    cid = record.get("chunk_id")
                    if cid:
                        # Determine which reason(s) triggered it
                        meta = record.get("metadata", {})
                        if meta.get("concepts") == ["general concept"]:
                            reason_counts["general_concept"] += 1
                        idx = _extract_chunk_index(cid)
                        if (
                            source_stem == TRIAL_FILE_STEM
                            and idx is not None
                            and 1 <= idx <= TRIAL_CHUNK_COUNT
                        ):
                            reason_counts["trial_chunk"] += 1
                        to_reprocess_ids.add(cid)

    log.info(f"Chunks to reprocess: {len(to_reprocess_ids)}")
    log.info(f"  - Failed (general concept): {reason_counts['general_concept']}")
    log.info(f"  - Trial chunks (first {TRIAL_CHUNK_COUNT}): {reason_counts['trial_chunk']}")

    # Resolve source data for chunks to reprocess
    chunks_to_reprocess = []
    missing = []
    for cid in sorted(to_reprocess_ids):
        if cid in source_chunks:
            chunks_to_reprocess.append(source_chunks[cid])
        else:
            missing.append(cid)
            log.warning(f"Source chunk not found for {cid} — will keep original metadata")

    if missing:
        log.warning(f"{len(missing)} chunks have no source data — they will be kept as-is")

    if not chunks_to_reprocess:
        log.info("Nothing to reprocess!")
        # Still build merged output if cache has data from previous runs
        cached = load_cache(cache_path)
        if cached:
            log.info(f"Building merged output from {len(cached)} cached records...")
            build_fixed_output(all_metadata, source_chunks, cached, output_dir)
            log.info("Done! Fixed metadata written to: " + str(output_dir))
        return

    # ── Step 3: Reprocess (with autosave) ────────────────────────────────
    log.info("\n" + "=" * 55)
    log.info("Step 3: Reprocessing chunks via LLM (autosave enabled)")
    log.info(f"  Cache file: {cache_path}")
    log.info("=" * 55)

    if args.dry_run:
        log.info("[DRY RUN MODE — no LLM calls will be made]")
        reprocessed = {}
        for chunk in chunks_to_reprocess:
            log.info(f"  Would reprocess: {chunk['chunk_id']}")
            reprocessed[chunk["chunk_id"]] = None
    else:
        api_key = args.api_key or os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("Set GROQ_API_KEY environment variable or pass --api-key")
        client = Groq(api_key=api_key)
        reprocessed = reprocess_chunks(
            client, chunks_to_reprocess, cache_path=cache_path
        )

    # ── Step 4: Build merged output ──────────────────────────────────────
    log.info("\n" + "=" * 55)
    log.info("Step 4: Building merged output files")
    log.info("=" * 55)

    build_fixed_output(
        all_metadata,
        source_chunks,
        reprocessed,
        output_dir,
        dry_run=args.dry_run,
    )

    log.info("\nDone! Fixed metadata written to: " + str(output_dir))


if __name__ == "__main__":
    main()
