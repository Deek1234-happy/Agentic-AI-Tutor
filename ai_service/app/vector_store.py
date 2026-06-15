# # app/vector_store.py

# # app/vector_store.py

# from sqlalchemy import text
# from .db import SessionLocal


# def search_similar_chunks(query_embedding, top_k=5):
#     db = SessionLocal()

#     try:
#         embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

#         result = db.execute(text("""
#             SELECT
#                 id,
#                 document_id,
#                 chunk_text,
#                 page_start,
#                 page_end,
#                 1 - (embedding <=> :query_embedding) AS score
#             FROM content.document_chunks
#             ORDER BY embedding <=> :query_embedding
#             LIMIT :top_k
#         """), {
#             "query_embedding": embedding_str,
#             "top_k": top_k
#         })

#         rows = result.fetchall()

#         return [
#             (
#                 r[0],  # id
#                 r[1],  # document_id
#                 r[2],  # chunk_text
#                 r[3],  # page_start
#                 r[4],  # page_end
#                 float(r[5])  # score
#             )
#             for r in rows
#         ]

#     finally:
#         db.close()

# # app/vector_store.py

# from sqlalchemy import text
# from .db import SessionLocal


# def search_similar_chunks(query_embedding, allowed_document_ids, user_id, top_k=5):
#     db = SessionLocal()

#     try:
#         embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

#         result = db.execute(text("""
#             SELECT
#                 id,
#                 document_id,
#                 chunk_text,
#                 page_start,
#                 page_end,
#                 1 - (embedding <=> :query_embedding) AS score
#             FROM content.document_chunks
#             WHERE
#                 document_id = ANY(:allowed_docs)
#                 AND user_id = :user_id
#             ORDER BY embedding <=> :query_embedding
#             LIMIT :top_k
#         """), {
#             "query_embedding": embedding_str,
#             "allowed_docs": allowed_document_ids,
#             "user_id": str(user_id),
#             "top_k": top_k
#         })

#         rows = result.fetchall()

#         return [
#             (
#                 r[0],  # chunk_id
#                 r[1],  # document_id
#                 r[2],  # chunk_text
#                 r[3],  # page_start
#                 r[4],  # page_end
#                 float(r[5])  # score
#             )
#             for r in rows
#         ]

#     finally:
#         db.close()

# from sqlalchemy import text
# from .db import SessionLocal


# def search_similar_chunks(query_embedding, allowed_document_ids, user_id, top_k=5):
#     db = SessionLocal()

#     try:
#         query_embedding = list(query_embedding)

#         result = db.execute(text("""
#             SELECT
#                 id,
#                 document_id,
#                 chunk_text,
#                 page_start,
#                 page_end,
#                 1 - (embedding <=> (:query_embedding)::vector) AS score
#             FROM content.document_chunks
#             WHERE
#                 document_id = ANY(:allowed_docs)
#                 AND user_id = :user_id
#             ORDER BY embedding <=> (:query_embedding)::vector
#             LIMIT :top_k
#         """), {
#             "query_embedding": query_embedding,
#             "allowed_docs": allowed_document_ids,
#             "user_id": str(user_id),
#             "top_k": top_k
#         })

#         rows = result.fetchall()

#         return [
#             (r[0], r[1], r[2], r[3], r[4], float(r[5]))
#             for r in rows
#         ]

#     finally:
#         db.close()



# # app/vector_store.py

# from sqlalchemy import text
# from .db import SessionLocal


# def search_similar_chunks(query_embedding, allowed_document_ids, user_id, top_k=5):
#     db = SessionLocal()

#     try:
#         query_embedding = list(query_embedding)

#         result = db.execute(text("""
#             SELECT
#                 id,
#                 document_id,
#                 chunk_text,
#                 page_start,
#                 page_end,
#                 1 - (embedding <=> (:query_embedding)::vector) AS score
#             FROM content.document_chunks
#             WHERE
#                 document_id = ANY(:allowed_docs)
#                 AND user_id = :user_id
#             ORDER BY embedding <=> (:query_embedding)::vector
#             LIMIT :top_k
#         """), {
#             "query_embedding": query_embedding,
#             "allowed_docs": allowed_document_ids,
#             "user_id": str(user_id),
#             "top_k": top_k
#         })

#         rows = result.fetchall()

#         return [
#             (
#                 r[0],  # chunk_id
#                 r[1],  # document_id
#                 r[2],  # chunk_text
#                 r[3],  # page_start
#                 r[4],  # page_end
#                 float(r[5]) if r[5] is not None else 0.0  # score
#             )
#             for r in rows
#         ]

#     finally:
#         db.close()




# app/vector_store.py

from sqlalchemy import text
from .db import SessionLocal


# def search_similar_chunks(query_embedding, allowed_document_ids, user_id, top_k=5):
#     db = SessionLocal()

#     try:
#         embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

#         result = db.execute(text("""
#             SELECT
#                 id,
#                 document_id,
#                 chunk_text,
#                 page_start,
#                 page_end,
#                 1 - (embedding <=> :query_embedding) AS score
#             FROM content.document_chunks
#             WHERE
#                 document_id = ANY(CAST(:allowed_docs AS uuid[]))
#                 AND user_id = :user_id
#                 AND embedding IS NOT NULL
#             ORDER BY embedding <=> :query_embedding
#             LIMIT :top_k
#         """), {
#             "query_embedding": embedding_str,
#             "allowed_docs": allowed_document_ids,
#             "user_id": str(user_id),
#             "top_k": top_k
#         })

#         rows = result.fetchall()

#         return [
#             (
#                 r[0],  # chunk_id
#                 r[1],  # document_id
#                 r[2],  # chunk_text
#                 r[3],  # page_start
#                 r[4],  # page_end
#                 float(r[5]) if r[5] is not None else 0.0  # score
#             )
#             for r in rows
#         ]

#     finally:
#         db.close()
# app/vector_store.py


# app/vector_store.py

from sqlalchemy import text
from .db import SessionLocal


def search_similar_chunks(
    query_embedding,
    allowed_document_ids=None,
    user_id=None,
    top_k=5
):
    db = SessionLocal()

    try:
        embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

        # ── Optional filtering ─────────────────────────────
        where_clauses = ["dc.embedding IS NOT NULL"]

        if user_id is not None:
            where_clauses.append("dc.user_id = :user_id")

        if allowed_document_ids:
            where_clauses.append("dc.document_id = ANY(CAST(:allowed_docs AS uuid[]))")

        where_sql = " AND ".join(where_clauses)

        # ── Query ──────────────────────────────────────────
        result = db.execute(text(f"""
            SELECT
                dc.id,
                dc.document_id,
                dc.chunk_text,
                dc.page_start,
                dc.page_end,
                1 - (dc.embedding <=> :query_embedding) AS score,
                d.filename AS source_title
            FROM content.document_chunks dc
            LEFT JOIN content.documents d ON d.id = dc.document_id
            WHERE {where_sql}
            ORDER BY dc.embedding <=> :query_embedding
            LIMIT :top_k
        """), {
            "query_embedding": embedding_str,
            "allowed_docs": allowed_document_ids if allowed_document_ids else [],
            "user_id": str(user_id) if user_id else None,
            "top_k": top_k,
        })

        rows = result.fetchall()

        return [
            (
                r[0],  # chunk_id
                r[1],  # document_id
                r[2],  # chunk_text
                r[3],  # page_start
                r[4],  # page_end
                float(r[5]) if r[5] is not None else 0.0,  # score
                r[6] if r[6] is not None else "",          # source_title
            )
            for r in rows
        ]

    finally:
        db.close()


# ── Helper (اختياري للتقييم) ─────────────────────────────
def get_all_chunks(user_id=None):
    db = SessionLocal()

    try:
        if user_id:
            result = db.execute(text("""
                SELECT
                    dc.id,
                    dc.document_id,
                    dc.chunk_text,
                    dc.page_start,
                    dc.page_end,
                    d.filename
                FROM content.document_chunks dc
                LEFT JOIN content.documents d ON d.id = dc.document_id
                WHERE
                    dc.user_id = :user_id
                    AND dc.chunk_text IS NOT NULL
            """), {"user_id": str(user_id)})
        else:
            result = db.execute(text("""
                SELECT
                    dc.id,
                    dc.document_id,
                    dc.chunk_text,
                    dc.page_start,
                    dc.page_end,
                    d.filename
                FROM content.document_chunks dc
                LEFT JOIN content.documents d ON d.id = dc.document_id
                WHERE
                    dc.chunk_text IS NOT NULL
            """))

        rows = result.fetchall()

        return [
            {
                "chunk_id": r[0],
                "document_id": r[1],
                "text": r[2],
                "page_start": r[3],
                "page_end": r[4],
                "source_title": r[5] if r[5] else ""
            }
            for r in rows
        ]

    finally:
        db.close()

