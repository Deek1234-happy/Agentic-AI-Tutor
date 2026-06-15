# app/embedding.py
from sentence_transformers import SentenceTransformer
from typing import List

# ============================================================
# Load model 
# ============================================================

#MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
# intfloat/e5-base-v2
#BAAI/bge-small-en-v1.5
MODEL_NAME = "intfloat/e5-base-v2" # for nq 
_model = SentenceTransformer(MODEL_NAME)


# ============================================================
# Public embedding function
# ============================================================

# def embed_texts(texts: List[str]) -> List[List[float]]:
#     """
#     Generate embeddings for a list of texts.
#     Returns a list of vectors (list of floats).
#     """
#     embeddings = _model.encode(
#         texts,
#         show_progress_bar=False,
#         normalize_embeddings=True
#     )

#     return embeddings.tolist()

def embed_texts(texts, is_query=True):  #false 
    if is_query:
        texts = [f"query: {t}" for t in texts]
    else:
        texts = [f"passage: {t}" for t in texts]

    embeddings = _model.encode(
        texts,
        normalize_embeddings=True
    )

    return embeddings.tolist()

