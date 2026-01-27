from typing import List, Dict, Optional, Union
import re

# ============================================================
# Chunking configuration (soft limits)
# ============================================================

TARGET_CHUNK_TOKENS = 600
MAX_CHUNK_TOKENS = 900
MIN_CHUNK_TOKENS = 250

OVERLAP_RATIO = 0.15  # 15% overlap


# ============================================================
# Token estimation (LLM-agnostic heuristic)
# ============================================================

def estimate_tokens(text: str) -> int:
    """
    Rough token estimation.
    Works reasonably across Gemini, Grok, GPT-like models.
    """
    words = text.split()
    return max(1, int(len(words) / 0.75))


# ============================================================
# Structural marker detection
# ============================================================

def is_page_or_slide_marker(line: str) -> bool:
    return bool(re.match(r"---\s+(Page|Slide)\s+\d+\s+---", line))


def looks_like_section_header(line: str) -> bool:
    """
    Conservative heuristic for section headers.
    Prefer false negatives over false positives.
    """
    if not line:
        return False

    if len(line) > 80:
        return False

    if line.endswith((".", ",", ";", ":", "?", "!")):
        return False

    if re.match(r"^\d+(\.\d+)*\s+[A-Z]", line):
        return True

    if line.isupper() and len(line.split()) <= 6:
        return True

    return False


# ============================================================
# Split text into structural blocks
# ============================================================

def split_into_blocks(text: str) -> List[Dict]:
    blocks = []
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    current_block = {
        "page": None,
        "section": None,
        "lines": []
    }

    i = 0
    while i < len(lines):
        line = lines[i]

        if is_page_or_slide_marker(line):
            if current_block["lines"]:
                blocks.append(current_block)

            current_block = {
                "page": line,
                "section": None,
                "lines": []
            }
            i += 1
            continue

        if looks_like_section_header(line):
            if i + 1 < len(lines) and len(lines[i + 1]) > 30:
                if current_block["lines"]:
                    blocks.append(current_block)

                current_block = {
                    "page": current_block["page"],
                    "section": line,
                    "lines": []
                }
                i += 1
                continue

        current_block["lines"].append(line)
        i += 1

    if current_block["lines"]:
        blocks.append(current_block)

    return blocks


# ============================================================
# Chunk builder (FIXED METADATA LOGIC)
# ============================================================

def build_chunks(
    blocks: List[Dict],
    file_id: str,
    source_type: str
) -> List[Dict]:

    chunks = []

    current_text_parts: List[str] = []
    current_tokens = 0

    current_pages: List[str] = []
    seen_pages = set()

    current_sections: List[str] = []
    seen_sections = set()

    chunk_index = 1

    def flush_chunk():
        nonlocal chunk_index
        nonlocal current_text_parts, current_tokens
        nonlocal current_pages, seen_pages
        nonlocal current_sections, seen_sections

        if not current_text_parts:
            return

        chunks.append({
            "file_id": file_id,
            "chunk_id": f"{file_id}_chunk_{chunk_index}",
            "source_type": source_type,
            "page_or_slide": (
                current_pages if len(current_pages) > 1
                else current_pages[0] if current_pages
                else None
            ),
            "section": (
                current_sections if len(current_sections) > 1
                else current_sections[0] if current_sections
                else None
            ),
            "text": " ".join(current_text_parts).strip()
        })

        chunk_index += 1
        current_text_parts = []
        current_tokens = 0

        current_pages = []
        seen_pages = set()

        current_sections = []
        seen_sections = set()

    for block in blocks:
        block_text = " ".join(block["lines"])
        block_tokens = estimate_tokens(block_text)

        block_page = block.get("page")
        block_section = block.get("section")

        # Oversized block → sentence-level split
        if block_tokens > MAX_CHUNK_TOKENS:
            sentences = re.split(r"(?<=[.!?])\s+", block_text)

            for sentence in sentences:
                sentence_tokens = estimate_tokens(sentence)

                if current_tokens + sentence_tokens > MAX_CHUNK_TOKENS:
                    flush_chunk()

                current_text_parts.append(sentence)
                current_tokens += sentence_tokens

                if block_page and block_page not in seen_pages:
                    current_pages.append(block_page)
                    seen_pages.add(block_page)

                if block_section and block_section not in seen_sections:
                    current_sections.append(block_section)
                    seen_sections.add(block_section)

            continue

        # Normal accumulation
        if current_tokens + block_tokens > MAX_CHUNK_TOKENS:
            flush_chunk()

        current_text_parts.append(block_text)
        current_tokens += block_tokens

        if block_page and block_page not in seen_pages:
            current_pages.append(block_page)
            seen_pages.add(block_page)

        if block_section and block_section not in seen_sections:
            current_sections.append(block_section)
            seen_sections.add(block_section)

    flush_chunk()

    return apply_overlap(chunks)

# ============================================================
# Overlap handling (text only, metadata untouched)
# ============================================================

def apply_overlap(chunks: List[Dict]) -> List[Dict]:
    if len(chunks) < 2:
        return chunks

    result = [chunks[0]]

    for i in range(1, len(chunks)):
        prev_words = chunks[i - 1]["text"].split()
        overlap_size = int(len(prev_words) * OVERLAP_RATIO)

        overlap_text = " ".join(prev_words[-overlap_size:])

        chunk = chunks[i].copy()
        chunk["text"] = overlap_text + " " + chunk["text"]

        result.append(chunk)

    return result


# ============================================================
# Public API
# ============================================================

def chunk_text(
    text: str,
    file_id: str,
    source_type: str
) -> List[Dict]:
    """
    Main entry point for dynamic chunking (US-35).
    """
    blocks = split_into_blocks(text)
    return build_chunks(blocks, file_id, source_type)
