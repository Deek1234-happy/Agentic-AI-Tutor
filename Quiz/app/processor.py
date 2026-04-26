# app/processor.py
"""
Document processing pipeline:
  1. Parse        (parsers.py via router)
  2. Clean        (quiz_engine.TextCleaner)
  3. Chunk        (quiz_engine.chunk_text)
  4. Post-process (quiz_engine.postprocess)
  5. Save to JSONL
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from .router import route_file, SUPPORTED_TYPES
from .quiz_engine import TextCleaner, chunk_text, postprocess

logger = logging.getLogger(__name__)

CHUNK_DIR = "data/chunks"
os.makedirs(CHUNK_DIR, exist_ok=True)
GLOBAL_CHUNK_DIR = "data/global_chunks"
GLOBAL_CHUNK_PREFIX = "all_chunks"
GLOBAL_CHUNK_BACKUP_SUFFIX = ".backup"
GLOBAL_CHUNK_LIMIT = 1000
os.makedirs(GLOBAL_CHUNK_DIR, exist_ok=True)

_cleaner = TextCleaner()


def _progress(message: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] QUIZ | {message}", flush=True)


def _compact_chunk_record(chunk: Dict) -> Dict:
    return {
        "file_id": chunk.get("file_id"),
        "chunk_id": chunk.get("chunk_id"),
        "text": chunk.get("text"),
        "context_fringe": chunk.get("context_fringe", {}),
    }


def _global_chunk_file_paths(index: int) -> Tuple[str, str]:
    base_name = f"{GLOBAL_CHUNK_PREFIX}_{index}.jsonl"
    primary = os.path.join(GLOBAL_CHUNK_DIR, base_name)
    backup = os.path.join(
        GLOBAL_CHUNK_DIR,
        f"{GLOBAL_CHUNK_PREFIX}_{index}{GLOBAL_CHUNK_BACKUP_SUFFIX}.jsonl",
    )
    return primary, backup


def _count_jsonl_rows(path: str) -> int:
    if not os.path.exists(path):
        return 0
    with open(path, "r", encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def _extract_index_from_name(name: str) -> Optional[int]:
    if not name.startswith(f"{GLOBAL_CHUNK_PREFIX}_") or not name.endswith(".jsonl"):
        return None

    middle = name[len(GLOBAL_CHUNK_PREFIX) + 1 : -len(".jsonl")]
    if middle.endswith(GLOBAL_CHUNK_BACKUP_SUFFIX):
        middle = middle[: -len(GLOBAL_CHUNK_BACKUP_SUFFIX)]
    return int(middle) if middle.isdigit() else None


def _latest_global_index() -> int:
    max_index = 1
    for filename in os.listdir(GLOBAL_CHUNK_DIR):
        idx = _extract_index_from_name(filename)
        if idx is not None:
            max_index = max(max_index, idx)
    return max_index


def _append_to_global_archives(chunks: List[Dict]) -> None:
    if not chunks:
        return

    compact_rows = [_compact_chunk_record(chunk) for chunk in chunks]
    row_pointer = 0
    current_index = _latest_global_index()

    while row_pointer < len(compact_rows):
        primary_path, backup_path = _global_chunk_file_paths(current_index)
        current_count = _count_jsonl_rows(primary_path)

        if current_count >= GLOBAL_CHUNK_LIMIT:
            current_index += 1
            continue

        room_left = GLOBAL_CHUNK_LIMIT - current_count
        to_write = compact_rows[row_pointer : row_pointer + room_left]

        with open(primary_path, "a", encoding="utf-8") as primary_f, open(
            backup_path, "a", encoding="utf-8"
        ) as backup_f:
            for row in to_write:
                line = json.dumps(row, ensure_ascii=False)
                primary_f.write(line + "\n")
                backup_f.write(line + "\n")

        row_pointer += len(to_write)


def process_document(
    file_path: str,
    file_type: str,
    use_ocr: bool = True,
    use_bart: bool = False,
    force_reprocess: bool = True,
):
    if file_type.lower() not in SUPPORTED_TYPES:
        logger.warning(f"Unsupported file type '{file_type}' for {file_path}")
        _progress(f"SKIP  {os.path.basename(file_path)} | unsupported type '{file_type}'")
        return None, 0

    display_name = os.path.basename(file_path)

    # STEP 1: Parse
    try:
        _progress(f"START {display_name} | parse")
        raw_text = route_file(file_path, file_type, use_ocr=use_ocr)
        _progress(f"DONE  {display_name} | parse")
    except Exception as e:
        logger.error(f"Parsing failed for {file_path}: {e}")
        _progress(f"FAIL  {display_name} | parse | {e}")
        return None, 0

    if not raw_text or not raw_text.strip():
        _progress(f"FAIL  {display_name} | no text extracted")
        return None, 0

    # STEP 2: Clean
    _progress(f"START {display_name} | clean")
    cleaned = _cleaner.clean(raw_text)
    if not cleaned or not cleaned.strip():
        _progress(f"FAIL  {display_name} | clean produced empty text")
        return None, 0
    _progress(f"DONE  {display_name} | clean")

    file_id = (
        os.path.basename(file_path)
        .rsplit(".", 1)[0]
        .lower()
        .replace(" ", "_")
    )

    output_file = os.path.join(CHUNK_DIR, f"{file_id}.jsonl")

    if os.path.exists(output_file) and not force_reprocess:
        _progress(f"CACHE {display_name} | {os.path.basename(output_file)}")
        with open(output_file, "r", encoding="utf-8") as f:
            existing = sum(1 for line in f if line.strip())
        return output_file, existing

    # STEP 3: Chunk
    _progress(f"START {display_name} | chunk")
    chunks = chunk_text(cleaned, file_id=file_id)
    if not chunks:
        _progress(f"FAIL  {display_name} | chunk produced 0 results")
        return output_file, 0
    _progress(f"DONE  {display_name} | chunk | {len(chunks)} kept")

    # STEP 4: Post-process
    _progress(f"START {display_name} | post-process")
    doc_title = (
        os.path.basename(file_path)
        .rsplit(".", 1)[0]
        .replace("_", " ")
        .replace("-", " ")
        .title()
    )
    chunks = postprocess(
        chunks,
        document_title=doc_title,
        dedup_threshold=0.92,
        min_words=50,
        max_words=300,
        use_bart=use_bart,
    )
    _progress(f"DONE  {display_name} | post-process | {len(chunks)} kept")

    # STEP 5: Save
    _progress(f"START {display_name} | save")
    with open(output_file, "w", encoding="utf-8") as f:
        for chunk in chunks:
            json.dump(chunk, f, ensure_ascii=False)
            f.write("\n")

    _append_to_global_archives(chunks)

    _progress(f"DONE  {display_name} | save | {len(chunks)} chunks written")

    return output_file, len(chunks)