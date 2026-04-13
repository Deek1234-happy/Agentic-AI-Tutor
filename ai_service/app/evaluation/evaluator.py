import random

from .ragas_eval import evaluate_ragas
from .trulens_eval import evaluate_groundedness
from .judge import groq_judge
from .confidence import compute_confidence


def evaluate_answer(question, answer, contexts):

    # ------------------------------------------------
    # Convert retrieved_chunks → pure text contexts
    # ------------------------------------------------

    extracted_contexts = []

    for c in contexts:
        try:
            extracted_contexts.append(c[2])  # chunk text
        except:
            continue

    if not extracted_contexts:
        print("No contexts available for evaluation")
        return 0.5

    # ------------------------------------------------
    # RAGAS evaluation
    # ------------------------------------------------

    ragas_scores =  evaluate_ragas(
        question,
        answer,
        extracted_contexts
    )

    # ------------------------------------------------
    # TruLens groundedness
    # ------------------------------------------------

    groundedness = evaluate_groundedness(
        answer,
        extracted_contexts
    )

    # ------------------------------------------------
    # GROQ judge (run sometimes)
    # ------------------------------------------------

    judge_score = None

    if True:
        print("Running Groq judge...")

        try:
            judge_score = groq_judge(
                question,
                answer,
                extracted_contexts
            )

            print("Groq returned:", judge_score)

        except Exception as e:
            print("Groq judge ERROR:", e)

    # ------------------------------------------------
    # Final confidence
    # ------------------------------------------------

    confidence = compute_confidence(
        ragas_scores,
        groundedness,
        judge_score
    )

    # ------------------------------------------------
    # Logs
    # ------------------------------------------------

    print("\n----- AI Evaluation -----")
    print("Question:", question)
    print("Faithfulness:", ragas_scores["faithfulness"])
    print("Relevance:", ragas_scores["relevance"])
    print("Groundedness:", groundedness)
    print("Groq Judge:", judge_score)
    print("Final Confidence:", confidence)
    print("-------------------------\n")

    return confidence