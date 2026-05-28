"""
Step 1 — Run this first to see the ACTUAL structure of NQ in your version.
This prints the raw record so we know exactly what fields exist.
"""
from datasets import load_dataset

nq_stream = load_dataset(
    "natural_questions",
    "default",
    split="validation",
    streaming=True,
)

# Just grab the first record and print everything
for record in nq_stream:
    print("=== KEYS AT TOP LEVEL ===")
    print(list(record.keys()))

    print("\n=== FULL RECORD (raw) ===")
    import json
    print(json.dumps(record, indent=2, default=str))
    break  # only need one record