import json

FILE = "data/hotpot_retrieval_results.json"

def analyze():
    with open(FILE) as f:
        data = json.load(f)

    total = len(data)

    hits_top1 = 0
    hits_top5 = 0

    for item in data:
        answers = [a.lower() for a in item["answers"]]
        retrieved = [r["text"].lower() for r in item["retrieved"]]

        # top1
        if any(ans in retrieved[0] for ans in answers):
            hits_top1 += 1

        # top5
        if any(
            any(ans in r for ans in answers)
            for r in retrieved[:5]
        ):
            hits_top5 += 1

    print("Hit@1:", hits_top1 / total)
    print("Hit@5:", hits_top5 / total)


if __name__ == "__main__":
    analyze()