import json
from sentence_transformers import CrossEncoder

MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-12-v2"

print("Loading CrossEncoder...")
reranker = CrossEncoder(MODEL_NAME)
print("Model loaded.\n")


def answer_in_text(text, answers):
    text = text.lower()

    for ans in answers:
        if ans.lower() in text:
            return True

    return False


def rerank(question, texts, titles, retrieval_scores):

    pairs = []

    for title, text in zip(titles, texts):

        combined = f"Title: {title}\nPassage: {text}"

        pairs.append((question, combined))

    rerank_scores = reranker.predict(pairs)

    combined_results = []

    for text, title, retrieval_score, rerank_score in zip(
        texts,
        titles,
        retrieval_scores,
        rerank_scores
    ):

        final_score = (
            0.7 * float(rerank_score)
            +
            0.3 * float(retrieval_score)
        )

        combined_results.append({
            "text": text,
            "title": title,
            "retrieval_score": retrieval_score,
            "rerank_score": float(rerank_score),
            "final_score": final_score
        })

    combined_results.sort(
        key=lambda x: x["final_score"],
        reverse=True
    )

    return combined_results


def evaluate(data):

    hit1_before = 0
    hit1_after = 0

    mrr_before = 0
    mrr_after = 0

    total = len(data)

    for item in data:

        question = item["question"]
        answers = item["answers"]

        texts = item["retrieved_texts"][:20]
        titles = item["retrieved_titles"][:20]
        scores = item["retrieval_scores"][:20]

        # =========================
        # BEFORE
        # =========================

        before_rank = None

        for i, text in enumerate(texts):

            if answer_in_text(text, answers):
                before_rank = i + 1
                break

        # =========================
        # RERANK
        # =========================

        reranked = rerank(
            question,
            texts,
            titles,
            scores
        )

        # =========================
        # AFTER
        # =========================

        after_rank = None

        for i, chunk in enumerate(reranked):

            if answer_in_text(chunk["text"], answers):
                after_rank = i + 1
                break

        # =========================
        # METRICS
        # =========================

        if before_rank == 1:
            hit1_before += 1

        if after_rank == 1:
            hit1_after += 1

        if before_rank:
            mrr_before += 1 / before_rank

        if after_rank:
            mrr_after += 1 / after_rank

        # =========================
        # LOGGING
        # =========================

        print("=" * 80)
        print("QUESTION:")
        print(question)

        print()

        print(f"Before Rank: {before_rank}")
        print(f"After Rank : {after_rank}")

        if before_rank and after_rank:

            diff = before_rank - after_rank

            if diff > 0:
                print(f"IMPROVED ↑ by {diff}")

            elif diff < 0:
                print(f"WORSE ↓ by {-diff}")

            else:
                print("NO CHANGE")

        print()

        if reranked:

            top = reranked[0]

            print("TOP RESULT AFTER RERANK:")
            print(top["title"])

            print()

            print("Retrieval Score:",
                  round(top["retrieval_score"], 4))

            print("Rerank Score:",
                  round(top["rerank_score"], 4))

            print("Final Score:",
                  round(top["final_score"], 4))

            print()

            print(top["text"][:500])

            print()

    # =========================
    # FINAL METRICS
    # =========================

    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)

    print(f"Hit@1 BEFORE: {(hit1_before / total) * 100:.2f}%")
    print(f"Hit@1 AFTER : {(hit1_after / total) * 100:.2f}%")

    print()

    print(f"MRR BEFORE: {(mrr_before / total) * 100:.2f}%")
    print(f"MRR AFTER : {(mrr_after / total) * 100:.2f}%")


if __name__ == "__main__":

    with open("/home/aya/EvalFinalRAGWithDatasets/Agentic-AI-Tutor/ai_service/data/nq_retrieval_results.json", "r") as f:
        data = json.load(f)

    evaluate(data)