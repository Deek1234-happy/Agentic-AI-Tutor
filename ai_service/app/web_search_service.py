import requests
import os
import re
from urllib.parse import urlparse
from .language_config import response_language_instruction
from .llm import generate_chat_answer

TAVILY_SEARCH_URL = "https://api.tavily.com/search"


def run_web_search(query: str, original_question: str | None = None, language: str = "en"):
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("Web search is not configured. Add TAVILY_API_KEY to ai_service/.env and restart the AI service.")

    payload = {
        "query": query,
        "search_depth": "ultra-fast",
        "max_results": 5,
        "include_answer": True,
    }

    try:
        response = requests.post(
            TAVILY_SEARCH_URL,
            json=payload,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        status = e.response.status_code if e.response is not None else "network error"
        raise RuntimeError(f"Tavily search failed ({status}): {e}") from e

    # --------- Generic extractors so we can handle many n8n shapes ----------

    def collect_sources(obj, acc):
        """Recursively collect source objects (with url + title/content) from any structure."""
        if isinstance(obj, dict):
            # A direct source-like dict?
            url = obj.get("url")
            title = obj.get("title")
            content = obj.get("content")
            if isinstance(url, str) and (isinstance(title, str) or isinstance(content, str)):
                acc.append(obj)
            # Recurse into values
            for v in obj.values():
                collect_sources(v, acc)
        elif isinstance(obj, list):
            for item in obj:
                collect_sources(item, acc)

    def find_answer(obj):
        """Recursively find the first reasonable answer string."""
        if isinstance(obj, dict):
            # Prefer these keys in this order
            for key in ("answer", "output", "summary", "text", "message", "content"):
                val = obj.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()
            # Recurse into nested dicts/lists
            for v in obj.values():
                found = find_answer(v)
                if found:
                    return found
        elif isinstance(obj, list):
            for item in obj:
                found = find_answer(item)
                if found:
                    return found
        return None

    # Collect sources from the entire payload
    raw_sources = []
    collect_sources(data, raw_sources)

    sources = []
    for r in raw_sources:
        url = r.get("url", "")
        title = r.get("title", "")
        domain = urlparse(url).netloc if isinstance(url, str) else ""

        sources.append({
            "title": title,
            "url": url,
            "domain": domain,
        })

    # Deduplicate sources by URL
    unique = {}
    for s in sources:
        key = s.get("url") or s.get("title")
        if key and key not in unique:
            unique[key] = s
    sources = list(unique.values())

    # Extract a single natural-language answer
    answer_text = find_answer(data)

    # If no structured sources were found, try to extract URLs from the answer text itself
    if isinstance(answer_text, str):
        url_pattern = re.compile(r"https?://\S+")
        urls = url_pattern.findall(answer_text)

        # Normalize URLs: trim trailing punctuation like ')', ']', ',' or '.'
        urls = [re.sub(r"[)\],.]+$", "", u) for u in urls]

        # If no structured sources were found, create source objects from URLs
        if urls and not sources:
            sources = []
            for u in urls:
                domain = ""
                domain = urlparse(u).netloc
                sources.append({"title": "", "url": u, "domain": domain})

        # Strip any trailing "sources" section in ANY language:
        # language-agnostic heuristic: if URLs appear (commonly in a sources block),
        # remove everything from the first URL onward.
        url_inline_match = re.search(r"https?://\S+", answer_text)
        md_link_match = re.search(r"\[[^\]]+\]\(\s*https?://[^)]+\)", answer_text)

        cut_at = None
        if url_inline_match:
            cut_at = url_inline_match.start()
        if md_link_match:
            cut_at = md_link_match.start() if cut_at is None else min(cut_at, md_link_match.start())

        if cut_at is not None:
            answer_text = answer_text[:cut_at].rstrip()
        else:
            # Fallback: if the model created a labeled section (any language), remove the last short block
            # that ends with ":" and is near the end (common for "Sources:" headings).
            m = re.search(r"(?m)^\s*[^:\n]{1,40}:\s*$", answer_text)
            if m and (len(answer_text) - m.start()) < 600:
                answer_text = answer_text[:m.start()].rstrip()

        # Clean up any leftover empty bullets or trailing formatting
        cleaned_lines = []
        for ln in answer_text.splitlines():
            if re.match(r"^\s*[-*]\s*$", ln):
                continue
            cleaned_lines.append(ln.rstrip())
        answer_text = "\n".join(cleaned_lines).rstrip()

    if not answer_text:
        if sources:
            # If sources is still a list of dicts here, this will be a generic fallback
            answer_text = f"I found {len(sources)} web sources."
        else:
            answer_text = "No web results found."

    if language != "en" and answer_text:
        source_context = "\n".join(
            f"{source.get('title', '')}: {source.get('content', '')} {source.get('url', '')}"
            for source in raw_sources
        )
        prompt = f"""
Use the web-search answer and source extracts below to answer the user's question.
Do not add unsupported claims. Keep URLs, filenames, technical terms, and source identifiers unchanged.
{response_language_instruction(language)}

Question:
{original_question or query}

Web-search answer:
{answer_text}

Source extracts:
{source_context}

Answer:
"""
        try:
            localized_answer = generate_chat_answer(prompt, temperature=0.1)
            answer_text = localized_answer.strip() if localized_answer else answer_text
        except Exception:
            pass

    return {
        "answer": answer_text,
        "sources": sources
    }