import json

file_path = "/home/aya/EvalFinalRAGWithDatasets/Agentic-AI-Tutor/ai_service/data/nq_eval.json"  # change to your file

titles = set()
data = []

with open(file_path, "r", encoding="utf-8") as f:
    samples = json.load(f)  # Load the entire JSON array

for i, sample in enumerate(samples):
    if i >= 500:  # only first 500 questions
        break
    
    question = sample.get("question", "")
    title = sample.get("context", {}).get("title", "")
    
    if title:
        titles.add(title)
    
    data.append({
        "question": question,
        "title": title
    })
with open("wiki_titles.txt", "w", encoding="utf-8") as f:
    for t in titles:
        f.write(t + "\n")
print(f"Total questions: {len(data)}")
print(f"Unique titles: {len(titles)}")

