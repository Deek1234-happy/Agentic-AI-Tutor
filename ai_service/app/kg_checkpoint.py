import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class KGCheckpoint:
    document_id: str
    last_completed_chunk_index: int = -1
    previous_chunk_tail: str = ""
    total_chunks: Optional[int] = None
    # Flags used by evaluation/upload scripts to know whether KG extraction
    # finished for this document without inspecting logs.
    kg_completed: bool = False
    status: str = "PENDING"
    completed_at: Optional[str] = None


def _checkpoint_dir() -> str:
    # Store alongside the service code (no DB writes, no .env requirements).
    base = os.path.dirname(os.path.abspath(__file__))
    d = os.path.join(base, ".kg_checkpoints")
    os.makedirs(d, exist_ok=True)
    return d


def _checkpoint_path(document_id: str) -> str:
    safe = "".join([c for c in (document_id or "unknown") if c.isalnum() or c in ("-", "_")])
    if not safe:
        safe = "unknown"
    return os.path.join(_checkpoint_dir(), f"{safe}.json")


def load_checkpoint(document_id: str) -> KGCheckpoint:
    path = _checkpoint_path(document_id)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        return KGCheckpoint(
            document_id=str(data.get("document_id") or document_id),
            last_completed_chunk_index=int(data.get("last_completed_chunk_index", -1)),
            previous_chunk_tail=str(data.get("previous_chunk_tail") or ""),
            total_chunks=(int(data["total_chunks"]) if data.get("total_chunks") is not None else None),
            kg_completed=bool(data.get("kg_completed", False)),
            status=str(data.get("status") or "PENDING"),
            completed_at=(str(data["completed_at"]) if data.get("completed_at") else None),
        )
    except FileNotFoundError:
        return KGCheckpoint(document_id=document_id)
    except Exception:
        # Corrupt checkpoint should not block processing; start fresh but don't crash.
        return KGCheckpoint(document_id=document_id)


def save_checkpoint(cp: KGCheckpoint) -> None:
    path = _checkpoint_path(cp.document_id)
    payload = {
        "document_id": cp.document_id,
        "last_completed_chunk_index": int(cp.last_completed_chunk_index),
        "previous_chunk_tail": cp.previous_chunk_tail or "",
        "total_chunks": cp.total_chunks,
        "kg_completed": bool(cp.kg_completed),
        "status": cp.status or "PENDING",
        "completed_at": cp.completed_at,
    }

    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)

    # Atomic-ish write on Windows: write temp then replace.
    fd, tmp = tempfile.mkstemp(prefix="kgcp_", suffix=".json", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        os.replace(tmp, path)
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass


def clear_checkpoint(document_id: str) -> None:
    path = _checkpoint_path(document_id)
    try:
        os.remove(path)
    except FileNotFoundError:
        return


def mark_checkpoint_processing(cp: KGCheckpoint) -> KGCheckpoint:
    cp.status = "PROCESSING"
    cp.kg_completed = False
    cp.completed_at = None
    save_checkpoint(cp)
    return cp


def mark_checkpoint_completed(cp: KGCheckpoint) -> KGCheckpoint:
    cp.status = "COMPLETED"
    cp.kg_completed = True
    cp.completed_at = datetime.now(timezone.utc).isoformat()
    save_checkpoint(cp)
    return cp


def mark_checkpoint_failed(cp: KGCheckpoint) -> KGCheckpoint:
    cp.status = "FAILED"
    cp.kg_completed = False
    save_checkpoint(cp)
    return cp
