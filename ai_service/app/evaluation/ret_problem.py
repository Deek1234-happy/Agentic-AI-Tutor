# run_diagnosis.py
import json

with open("data/nq_retrieval_results.json") as f:
    results = json.load(f)

missed = [r for r in results if r["hit_at_k"] == 0]

print(f"Total missed: {len(missed)}/500")
print(f"\n── Sample of 5 missed questions ──")

for r in missed[:5]:
    print(f"\nQ: {r['question']}")
    print(f"Gold: {r['gold_answers']}")
    print(f"Titles returned: {list(set(r['retrieved_titles']))}")
    print(f"Gold chunk: {r['gold_chunks']}")
    # هل الـ title الصح اترجع بس الإجابة مش في الـ chunk؟
    gold_title_returned = any(
        r['gold_chunks'][0].lower().replace(' ','_') in t.lower()
        for t in r['retrieved_titles']
    )
    print(f"Gold article returned? {'✅' if gold_title_returned else '❌'}")