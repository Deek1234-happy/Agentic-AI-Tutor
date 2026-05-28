import json
import os

os.makedirs("contexts_split", exist_ok=True)

with open("data/nq_contexts_only.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for i, item in enumerate(data):
    title = item["metadata"]["title"]
    text  = item["text"]

    filename = f"context_{i}.txt"

    with open(f"contexts_split/{filename}", "w", encoding="utf-8") as f:
        f.write(title + "\n\n" + text)

print("✅ Done splitting contexts")