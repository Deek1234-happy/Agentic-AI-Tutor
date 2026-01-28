from sentence_transformers import SentenceTransformer
from typing import List

# ============================================================
# Load model 
# ============================================================

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

_model = SentenceTransformer(MODEL_NAME)


# ============================================================
# Public embedding function
# ============================================================

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

