"""
RAG Evaluation Pipeline — HotpotQA
=====================================
Hotpot-specific multi-hop RAG evaluation pipeline.

Uses the REAL live production RAG pipeline:
    retrieval → reranking → context building → generation

Changes from old version:
  - Better multi-hop prompting
  - Fixed contains_match bug
  - Fixed faithful_binary bug
  - Keeps REAL live retrieval pipeline
  - Uses production prompt from rag_service

Usage:
    python -m app.evaluation.hotpot_gen_eval --limit 100 --rpm 30
    python -m app.evaluation.hotpot_gen_eval --limit 500 --rpm 30 --resume
"""

import argparse
import json
import os
import re
import string
import sys
import time

from collections import Counter, deque
from typing import List, Dict, Any, Tuple, Optional

try:
    from tqdm import tqdm

except ImportError:

    def tqdm(iterable, **kwargs):

        total = kwargs.get("total", "?")
        desc  = kwargs.get("desc", "")

        for i, item in enumerate(iterable, 1):

            print(
                f"\r{desc}: {i}/{total}",
                end="",
                flush=True
            )

            yield item

        print()


try:
    from app.rag_service import (
        answer_question,
        IDK_MESSAGE
    )

except ModuleNotFoundError as e:

    sys.exit(
        f"\n[ERROR] Could not import your app: {e}\n"
        "Run this script from your project root directory, e.g.:\n"
        "    python -m app.evaluation.hotpot_gen_eval --limit 100\n"
    )


# ══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════════

INPUT_FILE = (
    "/home/aya/EvalFinalRAGWithDatasets/"
    "Agentic-AI-Tutor/ai_service/data/"
    "hotpot_retrieval_results.json"
)

EVAL_FILE = (
    "/home/aya/EvalFinalRAGWithDatasets/"
    "Agentic-AI-Tutor/ai_service/data/"
    "hotpot_eval.json"
)

OUTPUT_FILE = (
    "/home/aya/EvalFinalRAGWithDatasets/"
    "Agentic-AI-Tutor/ai_service/data/"
    "hotpot_rag_eval_output.json"
)

METRICS_FILE = (
    "/home/aya/EvalFinalRAGWithDatasets/"
    "Agentic-AI-Tutor/ai_service/data/"
    "hotpot_final_rag_metrics.json"
)


# ══════════════════════════════════════════════════════════════════════════════
# RATE LIMITER
# ══════════════════════════════════════════════════════════════════════════════

class RateLimiter:

    def __init__(self, rpm: int = 30):

        self.rpm         = rpm
        self.window      = 60.0
        self.calls       = deque()
        self._req_count  = 0
        self._wait_total = 0.0

    def wait(self) -> float:

        now = time.time()

        while self.calls and now - self.calls[0] >= self.window:
            self.calls.popleft()

        if len(self.calls) >= self.rpm:

            sleep_for = (
                self.window - (now - self.calls[0]) + 0.05
            )

            if sleep_for > 0:

                print(
                    f"\n  ⏳  Rate limit: "
                    f"{len(self.calls)}/{self.rpm} req/min — "
                    f"waiting {sleep_for:.1f}s …",
                    flush=True
                )

                time.sleep(sleep_for)

                self._wait_total += sleep_for

            return sleep_for

        return 0.0

    def record(self):

        self.calls.append(time.time())

        self._req_count += 1

    def report(self) -> Dict[str, Any]:

        return {

            "total_requests":
                self._req_count,

            "total_wait_sec":
                round(self._wait_total, 2),

            "avg_wait_per_req":
                round(
                    self._wait_total /
                    max(self._req_count, 1),
                    2
                ),

            "rpm_budget":
                self.rpm,
        }


# ══════════════════════════════════════════════════════════════════════════════
# NORMALIZATION
# ══════════════════════════════════════════════════════════════════════════════

def normalize(text: str) -> str:

    text = text.lower()

    text = re.sub(
        r"\b(a|an|the)\b",
        " ",
        text
    )

    text = text.translate(
        str.maketrans("", "", string.punctuation)
    )

    return " ".join(text.split())


def tokenize(text: str) -> List[str]:

    return normalize(text).split()


# ══════════════════════════════════════════════════════════════════════════════
# GENERATION QUALITY
# ══════════════════════════════════════════════════════════════════════════════

def token_prf(
    prediction: str,
    gold_answers: List[str]
) -> Dict[str, float]:

    pred_tokens = tokenize(prediction)

    best_p = best_r = best_f1 = 0.0

    for gold in gold_answers:

        gold_tokens = tokenize(gold)

        if not pred_tokens and not gold_tokens:

            p = r = f1 = 1.0

        elif not pred_tokens or not gold_tokens:

            p = r = f1 = 0.0

        else:

            common = (
                Counter(pred_tokens)
                &
                Counter(gold_tokens)
            )

            num_common = sum(common.values())

            p = num_common / len(pred_tokens)

            r = num_common / len(gold_tokens)

            f1 = (
                (2 * p * r / (p + r))
                if (p + r) > 0
                else 0.0
            )

        if f1 > best_f1:

            best_p = p
            best_r = r
            best_f1 = f1

    return {

        "precision":
            round(best_p * 100, 2),

        "recall":
            round(best_r * 100, 2),

        "f1":
            round(best_f1 * 100, 2),
    }


# ══════════════════════════════════════════════════════════════════════════════
# ANSWER CORRECTNESS
# ══════════════════════════════════════════════════════════════════════════════

def exact_match(
    prediction: str,
    gold_answers: List[str]
) -> int:

    pred_norm = normalize(prediction)

    return int(
        any(
            normalize(g) == pred_norm
            for g in gold_answers
        )
    )


def contains_match(
    prediction: str,
    gold_answers: List[str]
) -> int:

    pred_tokens = tokenize(prediction)

    for gold in gold_answers:

        gold_tokens = tokenize(gold)

        for i in range(
            len(pred_tokens) - len(gold_tokens) + 1
        ):

            if (
                pred_tokens[
                    i:i + len(gold_tokens)
                ] == gold_tokens
            ):
                return 1

    return 0


# ══════════════════════════════════════════════════════════════════════════════
# FAITHFULNESS
# ══════════════════════════════════════════════════════════════════════════════

def faithfulness_score(
    answer: str,
    context: str
) -> Tuple[str, float]:

    answer_lc = answer.lower()

    context_lc = context.lower()

    if (
        IDK_MESSAGE.lower() in answer_lc
        or "don't know" in answer_lc
    ):
        return "IDK/FAITHFUL", 1.0

    answer_words = [

        w for w in tokenize(answer)

        if len(w) > 4
    ]

    if not answer_words:
        return "NOT_FAITHFUL", 0.0

    matches = sum(

        1 for w in answer_words

        if w in context_lc
    )

    ratio = matches / len(answer_words)

    verdict = (

        "FAITHFUL"

        if ratio >= 0.3

        else "NOT_FAITHFUL"
    )

    return verdict, round(ratio, 3)


# ══════════════════════════════════════════════════════════════════════════════
# CHUNK HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def chunks_to_context(
    chunks: List[Tuple]
) -> str:

    return "\n\n".join(

        c[2].strip()

        for c in chunks

        if (
            len(c) > 2
            and c[2]
            and c[2].strip()
        )
    )


def avg_chunk_score(
    chunks: List[Tuple]
) -> Optional[float]:

    scores = [

        c[5]

        for c in chunks

        if len(c) > 5
    ]

    return (

        round(sum(scores) / len(scores), 4)

        if scores

        else None
    )


# ══════════════════════════════════════════════════════════════════════════════
# CHECKPOINT HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def load_checkpoint(
    output_path: str
) -> Tuple[List[Dict], set]:

    rows: List[Dict] = []

    done_ids: set = set()

    if not os.path.exists(output_path):
        return rows, done_ids

    try:

        with open(
            output_path,
            "r",
            encoding="utf-8"
        ) as f:

            rows = json.load(f)

        for row in rows:

            if row.get("question_id"):

                done_ids.add(
                    row["question_id"]
                )

        print(
            f"  ↩️  Resumed: found "
            f"{len(rows)} already-completed questions"
        )

    except Exception as e:

        print(
            f"  ⚠️  Could not read checkpoint file ({e}), "
            f"starting fresh."
        )

    return rows, done_ids


def save_checkpoint(
    output_path: str,
    rows: List[Dict],
    label: str = ""
) -> None:

    if not rows:
        return

    os.makedirs(
        os.path.dirname(output_path)
        if os.path.dirname(output_path)
        else ".",
        exist_ok=True
    )

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            rows,
            f,
            indent=2
        )

    tag = f" [{label}]" if label else ""

    print(
        f"  💾  Checkpoint saved{tag} "
        f"→ {output_path} ({len(rows)} rows)"
    )


# ══════════════════════════════════════════════════════════════════════════════
# LOAD GOLD ANSWERS
# ══════════════════════════════════════════════════════════════════════════════

def load_eval_map(
    eval_file: str
) -> Dict[str, Dict]:

    eval_map: Dict[str, Dict] = {}

    if not os.path.exists(eval_file):

        print(
            f"⚠️  Eval file not found: {eval_file}"
        )

        return eval_map

    with open(
        eval_file,
        encoding="utf-8"
    ) as f:

        records = json.load(f)

    for rec in records:

        qid = rec.get("id", "")

        if not qid:
            continue

        gold_answers = rec.get(
            "gold_answers",
            []
        )

        if isinstance(gold_answers, str):
            gold_answers = [gold_answers]

        gold_answer = rec.get(
            "gold_answer",
            ""
        )

        if (
            gold_answer
            and gold_answer not in gold_answers
        ):
            gold_answers = (
                [gold_answer] + gold_answers
            )

        gold_answers = [

            g for g in gold_answers

            if g and g.strip()
        ]

        eval_map[qid] = {

            "gold_answers":
                gold_answers,

            "hotpot_type":
                rec.get("hotpot_type", ""),
        }

    print(
        f"Loaded {len(eval_map)} gold answers"
    )

    return eval_map


# ══════════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

def run_pipeline(
    input_path: str,
    eval_path: str,
    output_path: str,
    top_k: int,
    limit: int,
    rpm: int,
    checkpoint_every: int,
    resume: bool,
) -> None:

    with open(
        input_path,
        "r",
        encoding="utf-8"
    ) as f:

        data: List[Dict[str, Any]] = json.load(f)

    if isinstance(data, dict):

        data = next(

            v for v in data.values()

            if isinstance(v, list)
        )

    data = data[:limit]

    eval_map = load_eval_map(eval_path)

    data = [

        d for d in data

        if d["question_id"] in eval_map
    ]

    if resume:
        rows, done_ids = load_checkpoint(output_path)

    else:
        rows, done_ids = [], set()

    limiter = RateLimiter(rpm=rpm)

    agg: Dict[str, list] = {

        "precision": [],
        "recall": [],
        "f1": [],
        "exact_match": [],
        "contains_match": [],
        "faithful": [],
        "overlap_ratio": [],
        "num_chunks": [],
        "avg_chunk_score": [],
        "generation_latency_ms": [],
        "wait_sec": [],
    }

    todo = [

        item for item in data

        if item.get("question_id", "")
        not in done_ids
    ]

    total_to_do = len(todo)

    eval_start = time.time()

    for idx, item in enumerate(

        tqdm(
            todo,
            desc="Evaluating",
            total=total_to_do
        ),

        1
    ):

        qid = item.get("question_id", "")

        question = item["question"]

        eval_info = eval_map[qid]

        golds = eval_info["gold_answers"]

        hotpot_type = eval_info["hotpot_type"]

        # ──────────────────────────────────────────────────────────────
        # REAL LIVE PIPELINE
        # ──────────────────────────────────────────────────────────────

        wait_sec = limiter.wait()

        t0 = time.time()

        answer, chunks = answer_question(
            question,
            top_k=top_k
        )

        if not chunks:
            answer = IDK_MESSAGE

        limiter.record()

        generation_latency = round(
            (time.time() - t0) * 1000,
            1
        )

        # ──────────────────────────────────────────────────────────────
        # METRICS
        # ──────────────────────────────────────────────────────────────

        context = chunks_to_context(chunks)

        prf = token_prf(answer, golds)

        em = exact_match(answer, golds)

        cm = contains_match(answer, golds)

        faith, overlap = faithfulness_score(
            answer,
            context
        )

        faithful_bin = int(
            faith in ("FAITHFUL", "IDK/FAITHFUL")
        )

        avg_score = avg_chunk_score(chunks)

        row = {

            "question_id":
                qid,

            "question":
                question,

            "gold_answers":
                golds,

            "hotpot_type":
                hotpot_type,

            "generated_answer":
                answer,

            "retrieved_chunks": [

                {
                    "document_id": str(c[1]),
                    "chunk_text": c[2],
                    "page_start": c[3],
                    "page_end": c[4],
                    "score": c[5],
                }

                for c in chunks
            ],

            "gen_precision":
                prf["precision"],

            "gen_recall":
                prf["recall"],

            "gen_f1":
                prf["f1"],

            "exact_match":
                em,

            "contains_match":
                cm,

            "faithful_verdict":
                faith,

            "faithful_binary":
                faithful_bin,

            "context_overlap_ratio":
                overlap,

            "num_chunks_retrieved":
                len(chunks),

            "avg_chunk_score":
                avg_score,

            "generation_latency_ms":
                generation_latency,

            "rate_wait_sec":
                round(wait_sec, 2),
        }

        rows.append(row)

        agg["precision"].append(prf["precision"])
        agg["recall"].append(prf["recall"])
        agg["f1"].append(prf["f1"])
        agg["exact_match"].append(em)
        agg["contains_match"].append(cm)
        agg["faithful"].append(faithful_bin)
        agg["overlap_ratio"].append(overlap)
        agg["num_chunks"].append(len(chunks))

        agg["generation_latency_ms"].append(
            generation_latency
        )

        agg["wait_sec"].append(wait_sec)

        if avg_score is not None:
            agg["avg_chunk_score"].append(avg_score)

        if idx % checkpoint_every == 0:

            save_checkpoint(
                output_path,
                rows,
                label=f"q{idx}/{total_to_do}"
            )

    save_checkpoint(
        output_path,
        rows,
        label="FINAL"
    )

    def avg(lst: list):

        return (
            round(sum(lst) / len(lst), 2)
            if lst
            else "n/a"
        )

    bridge = [

        r for r in rows

        if r.get("hotpot_type") == "bridge"
    ]

    comp = [

        r for r in rows

        if r.get("hotpot_type") == "comparison"
    ]

    def avg_t(subset, key):

        vals = [

            float(r[key])

            for r in subset

            if r.get(key) not in (
                None,
                "",
                "n/a"
            )
        ]

        return (
            round(sum(vals) / len(vals), 2)
            if vals
            else "n/a"
        )

    elapsed_min = round(
        (time.time() - eval_start) / 60,
        2
    )

    rate_report = limiter.report()

    n = len(rows)

    final_metrics = {

        "generation_quality": {

            "precision":
                avg(agg["precision"]),

            "recall":
                avg(agg["recall"]),

            "f1":
                avg(agg["f1"]),

            "by_type": {

                "bridge": {

                    "f1":
                        avg_t(bridge, "gen_f1"),

                    "count":
                        len(bridge),
                },

                "comparison": {

                    "f1":
                        avg_t(comp, "gen_f1"),

                    "count":
                        len(comp),
                },
            }
        },

        "answer_correctness": {

            "exact_match":
                avg(agg["exact_match"]),

            "contains_match":
                avg(agg["contains_match"]),
        },

        "faithfulness": {

            "faithful_rate":
                avg(agg["faithful"]),

            "avg_overlap":
                avg(agg["overlap_ratio"]),
        },

        "retrieval_live_system": {

            "avg_chunks_retrieved":
                avg(agg["num_chunks"]),

            "avg_chunk_score":
                avg(agg["avg_chunk_score"]),
        },

        "latency_and_rate_limit": {

            "avg_generation_latency_ms":
                avg(agg["generation_latency_ms"]),

            "total_elapsed_min":
                elapsed_min,

            "rpm_budget":
                rate_report["rpm_budget"],

            "total_requests":
                rate_report["total_requests"],

            "total_wait_sec":
                rate_report["total_wait_sec"],

            "avg_wait_per_request_sec":
                rate_report["avg_wait_per_req"],
        },

        "evaluation_info": {

            "num_questions":
                n,

            "top_k":
                top_k,
        }
    }

    os.makedirs(
        os.path.dirname(METRICS_FILE)
        if os.path.dirname(METRICS_FILE)
        else ".",
        exist_ok=True
    )

    with open(
        METRICS_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            final_metrics,
            f,
            indent=4,
            ensure_ascii=False
        )

    print(
        f"\n✅ Results saved → {output_path}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="HotpotQA RAG evaluation"
    )

    parser.add_argument(
        "--input",
        default=INPUT_FILE
    )

    parser.add_argument(
        "--eval",
        default=EVAL_FILE
    )

    parser.add_argument(
        "--output",
        default=OUTPUT_FILE
    )

    parser.add_argument(
        "--top_k",
        type=int,
        default=5
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=500
    )

    parser.add_argument(
        "--rpm",
        type=int,
        default=30
    )

    parser.add_argument(
        "--checkpoint",
        type=int,
        default=10
    )

    parser.add_argument(
        "--resume",
        action="store_true"
    )

    args = parser.parse_args()

    run_pipeline(
        input_path=args.input,
        eval_path=args.eval,
        output_path=args.output,
        top_k=args.top_k,
        limit=args.limit,
        rpm=args.rpm,
        checkpoint_every=args.checkpoint,
        resume=args.resume,
    )