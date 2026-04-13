def compute_confidence(ragas_scores, groundedness, judge_score=None):

    faithfulness = ragas_scores["faithfulness"]
    relevance = ragas_scores["relevance"]

    confidence = (
        0.35 * faithfulness +
        0.30 * relevance +
        0.35 * groundedness
    )

    if judge_score:
        confidence = (confidence + judge_score) / 2

    return round(confidence, 3)