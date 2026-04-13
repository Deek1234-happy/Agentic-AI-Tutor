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


def search_similar_chunks(query_embedding, allowed_document_ids, user_id, top_k=5):
    db = SessionLocal()

    try:
        embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

        result = db.execute(text("""
            SELECT
                id,
                document_id,
                chunk_text,
                page_start,
                page_end,
                1 - (embedding <=> :query_embedding) AS score
            FROM content.document_chunks
            WHERE
                document_id = ANY(CAST(:allowed_docs AS uuid[]))
                AND user_id = :user_id
                AND embedding IS NOT NULL
            ORDER BY embedding <=> :query_embedding
            LIMIT :top_k
        """), {
            "query_embedding": embedding_str,
            "allowed_docs": allowed_document_ids,
            "user_id": str(user_id),
            "top_k": top_k
        })

        rows = result.fetchall()

        return [
            (
                r[0],  # chunk_id
                r[1],  # document_id
                r[2],  # chunk_text
                r[3],  # page_start
                r[4],  # page_end
                float(r[5]) if r[5] is not None else 0.0  # score
            )
            for r in rows
        ]

    finally:
        db.close()