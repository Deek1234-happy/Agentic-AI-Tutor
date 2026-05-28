# """
# Diagnostic — Why does /search/ return empty results?
# =====================================================
# Run this BEFORE the evaluation to find the exact problem.
# Each check narrows down where the data is missing.
# """

# import json
# import requests
# from sqlalchemy import text
# from app.db import SessionLocal

# BASE_URL   = "http://localhost:8000"

# print("=" * 60)
# print("DIAGNOSTIC — Search returning empty results")
# print("=" * 60)


# # ─────────────────────────────────────────────────────────────────────────────
# # CHECK 1 — Does the DB have ANY chunks at all?
# # ─────────────────────────────────────────────────────────────────────────────
# print("\n── CHECK 1: Total chunks in DB ─────────────────────────────")
# db = SessionLocal()
# try:
#     total = db.execute(text("SELECT COUNT(*) FROM content.document_chunks")).scalar()
#     print(f"  Total chunks in content.document_chunks : {total}")
#     if total == 0:
#         print("  ❌ PROBLEM: No chunks exist at all — chunking did not write to DB")
#         print("     Fix: re-run your chunking endpoint on nq_contexts_only.json")
# finally:
#     db.close()


# # ─────────────────────────────────────────────────────────────────────────────
# # CHECK 2 — How many chunks have embeddings?
# # ─────────────────────────────────────────────────────────────────────────────
# print("\n── CHECK 2: Chunks with embeddings ─────────────────────────")
# db = SessionLocal()
# try:
#     with_emb = db.execute(text(
#         "SELECT COUNT(*) FROM content.document_chunks WHERE embedding IS NOT NULL"
#     )).scalar()
#     without_emb = db.execute(text(
#         "SELECT COUNT(*) FROM content.document_chunks WHERE embedding IS NULL"
#     )).scalar()
#     print(f"  With embedding    : {with_emb}")
#     print(f"  Without embedding : {without_emb}")
#     if with_emb == 0:
#         print("  ❌ PROBLEM: Chunks exist but have no embeddings")
#         print("     Fix: your chunking endpoint must also embed and store the vector")
# finally:
#     db.close()


# # ─────────────────────────────────────────────────────────────────────────────
# # CHECK 3 — What user_id do the chunks belong to?
# # ─────────────────────────────────────────────────────────────────────────────
# print("\n── CHECK 3: user_id values on chunks ───────────────────────")
# db = SessionLocal()
# try:
#     rows = db.execute(text(
#         "SELECT DISTINCT user_id, COUNT(*) as n FROM content.document_chunks GROUP BY user_id LIMIT 10"
#     )).fetchall()
#     if rows:
#         for r in rows:
#             print(f"  user_id={r[0]}  →  {r[1]} chunks")
#     else:
#         print("  No rows found")
# finally:
#     db.close()


# # ─────────────────────────────────────────────────────────────────────────────
# # CHECK 4 — What filenames are stored in documents table?
# # ─────────────────────────────────────────────────────────────────────────────
# print("\n── CHECK 4: Filenames in documents table ───────────────────")
# db = SessionLocal()
# try:
#     rows = db.execute(text("""
#         SELECT d.filename, d.user_id, COUNT(dc.id) as chunk_count
#         FROM content.documents d
#         LEFT JOIN content.document_chunks dc ON dc.document_id = d.id
#         GROUP BY d.filename, d.user_id
#         ORDER BY chunk_count DESC
#         LIMIT 10
#     """)).fetchall()
#     if rows:
#         for r in rows:
#             print(f"  filename={r[0]}  user_id={r[1]}  chunks={r[2]}")
#     else:
#         print("  No documents found in content.documents table")
# finally:
#     db.close()


# # ─────────────────────────────────────────────────────────────────────────────
# # CHECK 5 — What does the search endpoint actually filter by?
# # Try with user_id=None vs a real user_id
# # ─────────────────────────────────────────────────────────────────────────────
# print("\n── CHECK 5: Search endpoint test ───────────────────────────")

# # 5a — with user_id=None (evaluation mode — what the eval script sends)
# print("  Testing user_id=None ...")
# r = requests.post(f"{BASE_URL}/search/", json={
#     "query": "super bowl eagles patriots",
#     "top_k": 3,
#     "user_id": None,
#     "allowed_document_ids": None,
# })
# print(f"  Status: {r.status_code}")
# print(f"  Results: {len(r.json())} chunks returned")
# if r.json():
#     print(f"  First result source_title: {r.json()[0].get('source_title', 'MISSING')}")


# # 5b — get a real user_id from the DB and try with that
# db = SessionLocal()
# try:
#     real_user = db.execute(text(
#         "SELECT DISTINCT user_id FROM content.document_chunks LIMIT 1"
#     )).scalar()
#     if real_user:
#         print(f"\n  Testing with real user_id={real_user} ...")
#         r2 = requests.post(f"{BASE_URL}/search/", json={
#             "query": "super bowl eagles patriots",
#             "top_k": 3,
#             "user_id": str(real_user),
#             "allowed_document_ids": None,
#         })
#         print(f"  Status: {r2.status_code}")
#         print(f"  Results: {len(r2.json())} chunks returned")
#         if r2.json():
#             print(f"  First result source_title: {r2.json()[0].get('source_title', 'MISSING')}")
#             print(f"  First result text preview : {r2.json()[0]['text'][:100]}")
# finally:
#     db.close()


# # ─────────────────────────────────────────────────────────────────────────────
# # CHECK 6 — Raw vector search bypassing the endpoint
# # ─────────────────────────────────────────────────────────────────────────────
# print("\n── CHECK 6: Raw vector search (bypass endpoint) ────────────")
# db = SessionLocal()
# try:
#     from app.embedding import embed_texts
#     test_query     = "when did the eagles play in the superbowl"
#     query_embedding = embed_texts([test_query])[0]
#     embedding_str  = "[" + ",".join(map(str, query_embedding)) + "]"

#     rows = db.execute(text("""
#         SELECT
#             dc.id,
#             d.filename,
#             dc.chunk_text,
#             1 - (dc.embedding <=> :qe) AS score
#         FROM content.document_chunks dc
#         LEFT JOIN content.documents d ON d.id = dc.document_id
#         WHERE dc.embedding IS NOT NULL
#         ORDER BY dc.embedding <=> :qe
#         LIMIT 5
#     """), {"qe": embedding_str}).fetchall()

#     if rows:
#         print(f"  Raw search returned {len(rows)} results:")
#         for r in rows:
#             print(f"    score={r[3]:.3f}  filename={r[1]}  text={str(r[2])[:80]}")
#     else:
#         print("  ❌ Raw search also returns nothing — embeddings may be malformed")
# finally:
#     db.close()


# print("\n" + "=" * 60)
# print("DIAGNOSIS COMPLETE")
# print("=" * 60)
# print("Share the output above and the exact fix will be written.")

import time
from app.search import vector_search, bm25_search, reciprocal_rank_fusion
from app.reranker import get_reranker
reranker = get_reranker()
async def search_with_timing(query):
    t0 = time.time()
    dense_results = await vector_search(query, top_k=20)
    t1 = time.time()
    
    bm25_results = bm25_search(query, top_k=20)
    t2 = time.time()
    
    fused = reciprocal_rank_fusion(dense_results, bm25_results)
    reranked = reranker.predict(fused[:20])
    t3 = time.time()
    
    print(f"Dense: {t1-t0:.2f}s | BM25: {t2-t1:.2f}s | Rerank: {t3-t2:.2f}s")