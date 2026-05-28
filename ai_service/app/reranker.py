from sentence_transformers import CrossEncoder

_reranker = None


def get_reranker():
    global _reranker
 # "cross-encoder/ms-marco-MiniLM-L-12-v2" first try
 #BAAI/bge-reranker-large second try
    if _reranker is None:
        _reranker = CrossEncoder(
            "BAAI/bge-reranker-base"
        )

    return _reranker


def rerank_chunks(question, chunks, top_k=5, verbose=False):

    if not chunks:
        return []

    model = get_reranker()

    pairs = []

    for chunk in chunks:

        chunk_text = chunk[2]
        document_title = chunk[6]

        combined_text = (
            f"Title: {document_title}\n"
            f"Passage: {chunk_text}"
        )

        pairs.append((question, combined_text))

    rerank_scores = model.predict(pairs)

    reranked = []

    for chunk, rerank_score in zip(chunks, rerank_scores):

        retrieval_score = float(chunk[5])
        final_score = float(rerank_score)

        reranked.append(
            (
                chunk,
                final_score,
                rerank_score,
                retrieval_score
            )
        )

    reranked.sort(
        key=lambda x: x[1],
        reverse=True
    )

    if verbose:
        print("\n=== RERANKED RESULTS ===")

        for i, (chunk, final_score, rerank_score, retrieval_score) in enumerate(reranked[:top_k]):

            print(f"\nRank #{i+1}")

            print(f"Document: {chunk[6]}")

            print(f"Retrieval Score: {retrieval_score:.4f}")

            print(f"Rerank Score: {rerank_score:.4f}")

            print(f"Final Score: {final_score:.4f}")

            print(chunk[2][:300])

    return [
        (
            chunk[0],
            chunk[1],
            chunk[2],
            chunk[3],
            chunk[4],
            retrieval_score,
            chunk[6],
            float(rerank_score),
            float(final_score),
        )
        for chunk, final_score, rerank_score, retrieval_score in reranked[:top_k]
    ]
