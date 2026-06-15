import json

with open("data/kg_retrieval_results.json") as f:
    results = json.load(f)

still_missing = [
    r for r in results
    if r.get("seed_miss") and "error" not in r
]

print(f"Still missing: {len(still_missing)}")
for r in still_missing:
    print(f"  Q: {r['question']}")
    print(f"  A: {r['answers']}")
    print()