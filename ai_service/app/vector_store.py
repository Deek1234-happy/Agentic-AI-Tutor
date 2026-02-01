import faiss
import numpy as np
from typing import List, Dict

# Vector index wrapper (HNSW for fast ANN search)

class VectorStore:
    def __init__(self, embedding_dim: int, hnsw_m: int = 32):
        """
        embedding_dim: dimension of embedding vectors
        hnsw_m: number of neighbors in HNSW graph (higher = better recall, more memory)
        """
        self.embedding_dim = embedding_dim

        # HNSW index with inner product (cosine similarity for normalized vectors)
        self.index = faiss.IndexHNSWFlat(embedding_dim, hnsw_m)
        self.index.hnsw.efSearch = 50  # search accuracy vs speed
        self.index.hnsw.efConstruction = 200  # build quality

        self.metadata: List[Dict] = []

    def add(self, embeddings: List[List[float]], metadatas: List[Dict]):
        if not embeddings:
            return

        vectors = np.array(embeddings, dtype="float32")
        self.index.add(vectors)
        self.metadata.extend(metadatas)

    def search(self, query_embedding: List[float], top_k: int = 5):
        if not query_embedding:
            return []

        query_vector = np.array([query_embedding], dtype="float32")
        scores, indices = self.index.search(query_vector, top_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue

            results.append({
                "score": float(score),
                "metadata": self.metadata[idx]
            })

        return results
