# app/evaluation/diagnose_missing.py

import json
from app.kg_store import get_session
from app.db import SessionLocal
from sqlalchemy import text as sql_text

MISSING_QUESTIONS = [
    ("what caused breakup of democratic republican party", "disputed 1824 presidential election"),
    ("when was catch me if you can made", "2002"),
    ("what is final season of downton abbey", "six"),
    ("where do royalties for winnie pooh go", "slesinger"),
    ("who played stumpy in movie rio bravo", "walter brennan"),
    ("who warned europe to stay out of americas", "monroe doctrine"),
    ("where was uncle toms cabin first published", "national era"),
    ("who is richest club in championship", "aston villa"),
    ("who is guy who walked across twin towers", "philippe petit"),
    ("who sings song youll never find another love like mine", "lou rawls"),
    ("what is earths magnetic field responsible for", "solar wind"),
    ("where can you find dna in body", "nucleus"),
    ("who has scored more goals in premier league", "alan shearer"),
    ("when will next episode of my next guest needs no introduction", "may 31 2018"),
]

# map question id → context file from your eval dataset
with open("data/nq_questions_final_500.json") as f:
    all_q = json.load(f)

q_map = {q["question"]: q for q in all_q}

db = SessionLocal()
for question, key_answer in MISSING_QUESTIONS:
    q = q_map.get(question)
    if not q:
        print(f"NOT IN DATASET: {question}")
        continue

    context_file = q.get("context_file", "?")
    print(f"\nQ : {question}")
    print(f"CF: {context_file}")

    # check if doc exists in postgres
    from app.evaluation.nq_kg_retrieve import CONTEXT_TO_DOC_ID  # your mapping
    doc_id = CONTEXT_TO_DOC_ID.get(context_file)
    if not doc_id:
        print(f"  ✗ NO doc_id mapping for {context_file} — document never uploaded")
        continue

    result = db.execute(sql_text(
        "SELECT id, is_deleted FROM content.documents WHERE id = :did"
    ), {"did": doc_id}).fetchone()

    if not result:
        print(f"  ✗ doc_id {doc_id[:8]} NOT in PostgreSQL — never uploaded")
        continue
    if result[1]:
        print(f"  ✗ doc_id {doc_id[:8]} is DELETED in PostgreSQL")
        continue

    print(f"  ✓ doc_id {doc_id[:8]} exists in PostgreSQL")

    # check if entities exist in Neo4j for this doc
    with get_session() as s:
        count = s.run(
            "MATCH (e:Entity) WHERE e.document_id = $did RETURN count(e) AS n",
            did=doc_id
        ).single()["n"]
        print(f"  Neo4j entities: {count}")

        if count > 0:
            sample = s.run(
                "MATCH (e:Entity) WHERE e.document_id = $did RETURN e.name LIMIT 5",
                did=doc_id
            ).data()
            print(f"  Sample: {[r['e.name'] for r in sample]}")
        else:
            print(f"  ✗ ZERO entities in Neo4j — KG extraction never ran or failed")

db.close()