from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")


def evaluate_ragas(question, answer, contexts):

    context_text = " ".join(contexts)

    # embeddings
    q_emb = model.encode(question, convert_to_tensor=True)
    a_emb = model.encode(answer, convert_to_tensor=True)
    c_emb = model.encode(context_text, convert_to_tensor=True)

    # similarity scores
    relevance = util.cos_sim(q_emb, a_emb).item()
    faithfulness = util.cos_sim(a_emb, c_emb).item()

    return {
        "faithfulness": max(0, min(faithfulness, 1)),
        "relevance": max(0, min(relevance, 1))
    }