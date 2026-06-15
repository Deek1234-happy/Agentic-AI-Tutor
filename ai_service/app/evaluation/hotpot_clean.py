"""
امسح كل HotpotQA documents + chunks من الـ DB
بدون ما تنزّل حاجة من الإنترنت
"""
from app.db import SessionLocal
from sqlalchemy import text

USER_ID      = "97449496-0bdf-4169-8e82-73388cacafbd"
CONTEXT_FILE = "data/hotpot_contexts.json"

import json

def clean_hotpot():
    with open(CONTEXT_FILE) as f:
        contexts_list = json.load(f)

    titles = [c["title"] for c in contexts_list]

    db = SessionLocal()
    try:
        rows = db.execute(text("""
            SELECT id FROM content.documents
            WHERE user_id = :uid AND filename = ANY(:titles)
        """), {"uid": USER_ID, "titles": titles}).fetchall()

        if not rows:
            print("مفيش بيانات HotpotQA في الـ DB أصلاً ✅")
            return

        ids = [str(r[0]) for r in rows]

        db.execute(text("""
            DELETE FROM content.document_chunks
            WHERE document_id = ANY(CAST(:ids AS uuid[]))
        """), {"ids": ids})

        db.execute(text("""
            DELETE FROM content.documents
            WHERE id = ANY(CAST(:ids AS uuid[]))
        """), {"ids": ids})

        db.commit()
        print(f"✅ تم مسح {len(ids)} document و chunks بتاعتهم")

    finally:
        db.close()

if __name__ == "__main__":
    clean_hotpot()