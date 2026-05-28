import json
import os

INPUT = "data/wiki_clean"
OUTPUT = "data/wiki_txt"

os.makedirs(OUTPUT, exist_ok=True)

for file in os.listdir(INPUT):
    if not file.endswith(".json"):
        continue

    with open(f"{INPUT}/{file}", "r", encoding="utf-8") as f:
        chunks = json.load(f)

    # 🟢 جمع chunks كنص
    text = "\n\n".join([c["text"] for c in chunks])

    out_path = f"{OUTPUT}/{file.replace('.json', '.txt')}"

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"Saved: {out_path}")