# import requests

# SEARCH_URL = "http://localhost:8000/search/"

# def inspect(question):
#     resp = requests.post(
#         SEARCH_URL,
#         json={
#             "query": question,
#             "top_k": 5,
#             "user_id": "97449496-0bdf-4169-8e82-73388cacafbd",
#         }
#     )

#     results = resp.json()

#     print("\nQUESTION:", question)
#     print("="*50)

#     for i, r in enumerate(results):
#         print(f"\n--- Chunk {i+1} ---")
#         print(r["text"][:300])


# if __name__ == "__main__":
#     inspect("What was Iqbal F. Qadir on when he participated in an attack on a radar station located on western shore of the Okhamandal Peninsula")

# run_chunk_debug.py
import json

with open("data/nq_retrieval_results.json") as f:
    results = json.load(f)

# سؤال kansas city
r = results[1]
print(f"Q: {r['question']}")
print(f"Gold answers: {r['gold_answers']}")
print(f"\n── All retrieved chunks from gold article ──")

for i, (text, title) in enumerate(zip(r['retrieved_texts'], r['retrieved_titles'])):
    if 'Kansas_City' in title or 'Kansas City' in title:
        print(f"\nChunk {i+1} [{title}]:")
        print(text)
        print("---")