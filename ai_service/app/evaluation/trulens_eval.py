from trulens_eval import Tru
from trulens_eval.feedback import Feedback
from trulens_eval.feedback.provider import OpenAI

# simple groundedness approximation using semantic overlap

from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

def evaluate_groundedness(answer, contexts):

    context_text = " ".join(contexts)

    a_emb = model.encode(answer, convert_to_tensor=True)
    c_emb = model.encode(context_text, convert_to_tensor=True)

    score = util.cos_sim(a_emb, c_emb).item()

    return max(0, min(score, 1))