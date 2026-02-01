from sentence_transformers import SentenceTransformer
from typing import List
import logging


# Load model 

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_VERSION = "v1.0.0"  # version tracking
_model = SentenceTransformer(MODEL_NAME)


# Public embedding function

def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a list of texts.
    Returns a list of vectors (list of floats).
    """
    embeddings = _model.encode(
        texts,
        show_progress_bar=False,
        normalize_embeddings=True
    )

    return embeddings.tolist()



# Internal helper

def _safe_encode(texts: List[str]) -> List[List[float]]:
    try:
        embeddings = _model.encode(
            texts,
            show_progress_bar=False,
            normalize_embeddings=True  # cosine-ready
        )
        return embeddings.tolist()

    except Exception as e:
        logging.error(f"Embedding generation failed: {e}")
        return []


# Public API

def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for document chunks.
    """
    return _safe_encode(texts)


def embed_query(query: str) -> List[float]:
    """
    Generate embedding for a user query.
    Must use SAME model & normalization.
    """
    vectors = _safe_encode([query])
    return vectors[0] if vectors else []
