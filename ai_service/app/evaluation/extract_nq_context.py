import json
import os
import re

# ─────────────────────────────────────────
# Config
# ─────────────────────────────────────────
INPUT_PATH = "data/nq_eval.json"
OUTPUT_PATH = "data/nq_contexts_only.json"

os.makedirs("data", exist_ok=True)


# ─────────────────────────────────────────
# Clean text (optional but IMPORTANT)
# ─────────────────────────────────────────
def clean_text(text):
    # remove wikipedia navigation noise
    text = re.sub(r"Jump to.*?search", "", text)

    # remove extra spaces
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ─────────────────────────────────────────
# Load dataset
# ─────────────────────────────────────────
with open(INPUT_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)


# ─────────────────────────────────────────
# Extract contexts
# ─────────────────────────────────────────
contexts = []
seen_titles = set()

for item in data:
    context = item.get("context", {})
    
    text = context.get("text", "").strip()
    title = context.get("title", "").strip()

    # skip empty
    if not text:
        continue

    # remove duplicates (same Wikipedia page)
    if title in seen_titles:
        continue

    seen_titles.add(title)

    # clean text
    text = clean_text(text)

    # optional: truncate long docs (protect your system)
    text = text[:5000]

    contexts.append({
        "text": text,
        "metadata": {
            "title": title,
            "source": "NQ"
        }
    })


# ─────────────────────────────────────────
# Save
# ─────────────────────────────────────────
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(contexts, f, indent=2, ensure_ascii=False)


# ─────────────────────────────────────────
# Logs
# ─────────────────────────────────────────
print("=" * 50)
print(f"✅ Extracted {len(contexts)} unique contexts")
print(f"📁 Saved to: {OUTPUT_PATH}")
print("=" * 50)


# ─────────────────────────────────────────
# Preview
# ─────────────────────────────────────────
if contexts:
    print("\n===== SAMPLE =====")
    print("Title:", contexts[0]["metadata"]["title"])
    print("Text preview:", contexts[0]["text"][:300])
    print("==================")