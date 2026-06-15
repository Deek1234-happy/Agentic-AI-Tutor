"""
HotpotQA — Index (UPDATED for folder corpus)
============================================

✔ يقرأ من folder: data/hotpot_corpus
✔ كل file = document (paragraph)
✔ يستخرج title + text
✔ يعمل chunking + embedding
✔ يخزن في DB

Run:
  python -m app.evaluation.hotpot_index
"""

import os
import uuid
import time
import hashlib
import tempfile
import requests
from app.db import SessionLocal
from sqlalchemy import text

EXTRACT_URL  = "http://localhost:8000/extract/embed"
USER_ID      = "97449496-0bdf-4169-8e82-73388cacafbd"
SUBJECT_ID   = "7f12675d-82cf-4fa2-b64f-e9307880ae1f"

CORPUS_DIR   = "data/hotpot_corpus"
TEMP_DIR     = tempfile.gettempdir()


# ─────────────────────────────────────────────────────────────
# Helper: extract title + text from file
# ─────────────────────────────────────────────────────────────
def parse_document(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")

    title = ""
    text  = ""

    for line in lines:
        if line.startswith("Title:"):
            title = line.replace("Title:", "").strip()
        elif line.startswith("Text:"):
            text = line.replace("Text:", "").strip()

    return title, text


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
def index_hotpot_contexts():

    if not os.path.exists(CORPUS_DIR):
        print(f"❌ {CORPUS_DIR} not found")
        print("Run: prepare_hotpot.py first")
        return

    files = [f for f in os.listdir(CORPUS_DIR) if f.endswith(".txt")]

    print("=" * 60)
    print("HotpotQA — Indexing (UPDATED)")
    print(f"Documents: {len(files)}")
    print("=" * 60)

    success = 0
    failed  = []
    t_start = time.time()

    for i, filename in enumerate(files):

        file_path = os.path.join(CORPUS_DIR, filename)
        title, full_text = parse_document(file_path)

        if not full_text:
            failed.append(filename)
            continue

        tmp_path = os.path.join(TEMP_DIR, f"hotpot_tmp_{i}.txt")

        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(full_text)

        try:
            response = requests.post(
                EXTRACT_URL,
                json={"file_path": tmp_path, "file_type": "txt"},
                timeout=120,
            )

            if response.status_code == 200:
                chunks = response.json()

                if chunks:
                    content_hash = hashlib.md5(full_text.encode()).hexdigest()

                    db = SessionLocal()
                    try:
                        doc_id = str(uuid.uuid4())

                        # ✅ insert document
                        db.execute(text("""
                            INSERT INTO content.documents
                                (id, user_id, subject_id, filename, file_type,
                                 file_size, storage_path, processing_status, content_hash)
                            VALUES (:id, :uid, :sid, :filename, 'txt',
                                    0, '', 'completed', :chash)
                        """), {
                            "id": doc_id,
                            "uid": USER_ID,
                            "sid": SUBJECT_ID,
                            "filename": title,   # ✅ FIXED
                            "chash": content_hash  # ✅ FIXED
                        })

                        # ✅ insert chunks
                        for chunk in chunks:
                            emb_str = "[" + ",".join(map(str, chunk["embedding"])) + "]"

                            db.execute(text("""
                                INSERT INTO content.document_chunks
                                    (id, document_id, user_id, chunk_text,
                                     embedding, page_start, page_end)
                                VALUES (:id, :doc_id, :uid, :text,
                                        :emb, :ps, :pe)
                            """), {
                                "id": str(uuid.uuid4()),
                                "doc_id": doc_id,
                                "uid": USER_ID,
                                "text": chunk["text"],
                                "emb": emb_str,
                                "ps": chunk.get("page_start"),
                                "pe": chunk.get("page_end"),
                            })

                        db.commit()
                        success += 1

                    finally:
                        db.close()
                else:
                    failed.append(filename)

            else:
                failed.append(filename)
                print(f"❌ {filename}: HTTP {response.status_code}")

        except Exception as e:
            failed.append(filename)
            print(f"❌ {filename}: {e}")

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        # progress
        if (i + 1) % 100 == 0:
            elapsed = time.time() - t_start
            eta = (len(files) - i - 1) / ((i + 1) / elapsed)
            print(f"[{i+1}/{len(files)}] success={success} failed={len(failed)} ETA={eta:.0f}s")

    # ─────────────────────────────────────────────
    # FINAL STATS
    # ─────────────────────────────────────────────
    db = SessionLocal()
    try:
        total_docs = db.execute(text(
            "SELECT COUNT(*) FROM content.documents WHERE user_id = :uid"
        ), {"uid": USER_ID}).scalar()

        total_chunks = db.execute(text(
            "SELECT COUNT(*) FROM content.document_chunks WHERE user_id = :uid"
        ), {"uid": USER_ID}).scalar()

    finally:
        db.close()

    print("\n" + "=" * 60)
    print("Indexing complete")
    print(f"Success : {success}/{len(files)}")
    print(f"Failed  : {len(failed)}")
    print(f"DB      : {total_docs} docs, {total_chunks} chunks")

    if not failed:
        print("\n✅ Ready for evaluation")
    else:
        print(f"\n⚠️ Failed examples: {failed[:5]}")


# ─────────────────────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    index_hotpot_contexts()