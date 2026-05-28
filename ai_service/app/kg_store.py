# app/kg_store.py

import difflib
import os
import re as _re
import uuid
from typing import List, Dict, Optional, Tuple
from urllib.parse import unquote

from sqlalchemy import text as sql_text

from .kg_db import get_session
from .db import SessionLocal


# ════════════════════════════════════════════════════════════════
# Relationship type sanitiser
# ════════════════════════════════════════════════════════════════

_SAFE_REL = _re.compile(r'^[A-Z][A-Z0-9_]*$')

# Labels that are structural (hierarchy edges) — never treated as semantic rels
_STRUCTURAL_LABELS = {'HAS_ENTITY', 'HAS_SUBJECT', 'HAS_DOCUMENT', 'HAS_USER'}


def _sanitize_rel_type(rel_type: str, fallback: str = "RELATED") -> str:
    """Ensure the value is safe to interpolate as a Neo4j relationship label."""
    cleaned = rel_type.strip().upper()
    return cleaned if _SAFE_REL.match(cleaned) else fallback


# ════════════════════════════════════════════════════════════════
# PostgreSQL helpers  (read-only — never modifies RAG data)
# ════════════════════════════════════════════════════════════════

def document_exists_in_postgres(document_id: str) -> bool:
    db = SessionLocal()
    try:
        result = db.execute(sql_text("""
            SELECT 1 FROM content.documents
            WHERE id = :did AND is_deleted = false
        """), {"did": str(document_id)})
        return result.fetchone() is not None
    finally:
        db.close()


def subject_exists_in_postgres(subject_id: str) -> bool:
    db = SessionLocal()
    try:
        result = db.execute(sql_text("""
            SELECT 1 FROM content.subjects WHERE id = :sid
        """), {"sid": str(subject_id)})
        return result.fetchone() is not None
    finally:
        db.close()


def get_subject_id_for_session(session_id: str) -> Optional[str]:
    """Majority subject_id among a session's documents. Used by chat_service."""
    db = SessionLocal()
    try:
        result = db.execute(sql_text("""
            SELECT d.subject_id, COUNT(*) AS cnt
            FROM   rag.chat_documents cd
            JOIN   content.documents  d ON d.id = cd.document_id
            WHERE  cd.session_id = :sid AND d.subject_id IS NOT NULL
            GROUP  BY d.subject_id
            ORDER  BY cnt DESC
            LIMIT  1
        """), {"sid": str(session_id)})
        row = result.fetchone()
        return str(row[0]) if row else None
    finally:
        db.close()


def get_documents_for_subject(subject_id: str, user_id: str) -> List[Dict]:
    """Non-deleted documents in a subject, ordered by upload_time."""
    db = SessionLocal()
    try:
        result = db.execute(sql_text("""
            SELECT id, filename, subject_id, user_id
            FROM   content.documents
            WHERE  subject_id = :sid AND user_id = :uid AND is_deleted = false
            ORDER  BY upload_time ASC
        """), {"sid": str(subject_id), "uid": str(user_id)})
        return [
            {"id": str(r[0]), "filename": r[1],
             "subject_id": str(r[2]), "user_id": str(r[3])}
            for r in result.fetchall()
        ]
    finally:
        db.close()


def get_subject_for_document(document_id: str) -> Optional[Dict]:
    db = SessionLocal()
    try:
        result = db.execute(sql_text("""
            SELECT subject_id, user_id FROM content.documents WHERE id = :did
        """), {"did": str(document_id)})
        row = result.fetchone()
        return (
            {"subject_id": str(row[0]) if row[0] else None, "user_id": str(row[1])}
            if row else None
        )
    finally:
        db.close()


def get_subject_title(subject_id: str) -> str:
    db = SessionLocal()
    try:
        result = db.execute(sql_text("""
            SELECT name FROM content.subjects WHERE id = :sid
        """), {"sid": str(subject_id)})
        row = result.fetchone()
        return str(row[0]) if row and row[0] else str(subject_id)
    finally:
        db.close()


def resolve_document_by_file_path(file_path: str) -> Optional[Dict]:
    """
    Resolve content.documents row from a client-provided path: document UUID,
    storage_path, or filename basename match.
    """
    raw = unquote((file_path or "").strip())
    if not raw:
        return None

    norm = os.path.normpath(raw).replace("\\", "/")
    basename = os.path.basename(norm)

    db = SessionLocal()
    try:
        try:
            uuid.UUID(norm)
            r = db.execute(
                sql_text("""
                    SELECT id, subject_id, user_id, filename
                    FROM content.documents
                    WHERE id = :did AND is_deleted = false
                """),
                {"did": norm},
            ).fetchone()
            if r:
                return {
                    "document_id": str(r[0]),
                    "subject_id":  str(r[1]),
                    "user_id":     str(r[2]),
                    "filename":    str(r[3]) if r[3] else basename,
                }
        except ValueError:
            pass

        r = db.execute(
            sql_text("""
                SELECT id, subject_id, user_id, filename
                FROM content.documents
                WHERE is_deleted = false
                  AND (
                        storage_path = :p_exact
                     OR storage_path = :norm
                     OR filename = :basename
                     OR filename = :norm
                  )
                ORDER BY upload_time DESC
                LIMIT 1
            """),
            {"p_exact": raw, "norm": norm, "basename": basename},
        ).fetchone()
        if r:
            return {
                "document_id": str(r[0]),
                "subject_id":  str(r[1]),
                "user_id":     str(r[2]),
                "filename":    str(r[3]) if r[3] else basename,
            }
        return None
    finally:
        db.close()


def get_existing_chunks_for_document(document_id: str) -> List[Dict]:
    """
    Read pre-existing chunks for a document from PostgreSQL.
    This is read-only and never writes or generates chunks.
    """
    db = SessionLocal()
    try:
        result = db.execute(
            sql_text(
                """
                SELECT id, chunk_text, page_start, page_end
                FROM content.document_chunks
                WHERE document_id = :did
                ORDER BY page_start NULLS FIRST, page_end NULLS FIRST, id ASC
                """
            ),
            {"did": str(document_id)},
        )
        rows = result.fetchall()
        return [
            {
                "chunk_id": str(r[0]),
                "text": str(r[1]) if r[1] is not None else "",
                "page_start": r[2],
                "page_end": r[3],
            }
            for r in rows
        ]
    finally:
        db.close()


# ════════════════════════════════════════════════════════════════
# Neo4j — structural node upserts
# ════════════════════════════════════════════════════════════════

def upsert_user_node(user_id: str) -> None:
    with get_session() as s:
        s.run("MERGE (u:User {id: $id})", id=user_id)


def upsert_subject_node(subject_id: str, subject_name: str, user_id: str) -> None:
    with get_session() as s:
        s.run(
            """
            MERGE (sub:Subject {id: $id})
            SET   sub.name    = $name,
                  sub.user_id = $uid
            """,
            id=subject_id, name=subject_name, uid=user_id,
        )
        s.run(
            """
            MATCH  (u:User    {id: $uid})
            MATCH  (sub:Subject {id: $sid})
            MERGE  (u)-[:HAS_SUBJECT]->(sub)
            """,
            uid=user_id, sid=subject_id,
        )


def upsert_document_node(
    document_id: str,
    filename:    str,
    subject_id:  str,
    user_id:     str,
    doc_order:   int = 0,
) -> None:
    with get_session() as s:
        s.run(
            """
            MERGE (d:Document {id: $id})
            SET   d.filename   = $filename,
                  d.subject_id = $sid,
                  d.user_id    = $uid,
                  d.doc_order  = $doc_order
            """,
            id=document_id, filename=filename,
            sid=subject_id, uid=user_id, doc_order=doc_order,
        )
        s.run(
            """
            MATCH  (sub:Subject  {id: $sid})
            MATCH  (d:Document   {id: $did})
            MERGE  (sub)-[:HAS_DOCUMENT]->(d)
            """,
            sid=subject_id, did=document_id,
        )


# ════════════════════════════════════════════════════════════════
# for debugging
#
def set_document_status(document_id: str, status: str) -> None:
    with get_session() as s:
        s.run(
            """
            MATCH (d:Document {id: $did})
            SET d.kg_status = $status
            """,
            did=document_id,
            status=status,
        )


# ════════════════════════════════════════════════════════════════
# Neo4j — entity + intra-document relationship persistence
#
# Relationship label = the semantic type (e.g. :CALLS, :TREATS).
# _sanitize_rel_type() guarantees safe interpolation.
# ════════════════════════════════════════════════════════════════

def save_graph(entities: List[Dict], relationships: List[Dict]) -> None:
    """
    Upsert intra-document entities and relationships.

    Entity MERGE key: (name, document_id, user_id)
    Relationship label: the semantic type extracted by the LLM
    """
    if not entities and not relationships:
        return

    # name.lower() → document_id — for relationship resolution
    entity_doc_map: Dict[str, str] = {}
    batch_user_id = entities[0].get("user_id", "") if entities else ""

    with get_session() as s:

        # 1. Upsert entity nodes ──────────────────────────────
        for ent in entities:
            name        = ent.get("name", "").strip()
            document_id = ent.get("document_id", "")
            subject_id  = ent.get("subject_id",  "")
            user_id     = ent.get("user_id",     "")
            ent_type    = ent.get("type", "Unknown")

            if not name or not document_id:
                continue

            entity_doc_map[name.lower()] = document_id

            s.run(
                """
                MERGE (e:Entity {name: $name, document_id: $did, user_id: $uid})
                SET   e.type       = $type,
                      e.subject_id = $sid
                """,
                name=name, did=document_id, uid=user_id,
                type=ent_type, sid=subject_id,
            )

            # Structural link: Document → Entity
            s.run(
                """
                MATCH  (d:Document {id: $did})
                MATCH  (e:Entity   {name: $name, document_id: $did, user_id: $uid})
                MERGE  (d)-[:HAS_ENTITY]->(e)
                """,
                did=document_id, name=name, uid=user_id,
            )

        # 2. Upsert intra-doc semantic relationships ──────────
        for rel in relationships:
            source   = rel.get("source", "").strip()
            target   = rel.get("target", "").strip()
            rel_type = _sanitize_rel_type(rel.get("relation", ""))

            if not source or not target:
                continue

            doc_id = (
                entity_doc_map.get(source.lower())
                or entity_doc_map.get(target.lower())
                or (entities[0]["document_id"] if entities else "")
            )
            if not doc_id:
                continue

            # Safe: rel_type matches ^[A-Z][A-Z0-9_]*$ after sanitisation
            s.run(
                f"""
                MATCH  (src:Entity {{name: $source, document_id: $did, user_id: $uid}})
                MATCH  (tgt:Entity {{name: $target, document_id: $did, user_id: $uid}})
                MERGE  (src)-[r:{rel_type}]->(tgt)
                SET    r.document_id = $did,
                       r.subject_id = $sid,
                       r.user_id = $uid,
                       r.chunk_index = $chunk_index,
                       r.source_text = $source_text
                """,
                source=source, target=target,
                did=doc_id,
                sid=rel.get("subject_id", entities[0].get("subject_id", "") if entities else ""),
                uid=rel.get("user_id", batch_user_id),
                chunk_index=rel.get("chunk_index"),
                source_text=rel.get("source_text", ""),
            )

    print(
        f"[KG Store] Saved {len(entities)} entities "
        f"and {len(relationships)} intra-doc relationships."
    )


def merge_cross_subject_edges(
    user_id: str,
    subject_id: str,
    current_document_id: str,
    relationships: List[Dict],
) -> None:
    """
    For each extracted relationship, if the counterpart entity already exists in
    another document (same subject, same user), add a semantic edge with
    cross_doc=true. Complements save_graph (same-document edges).
    """
    if not relationships:
        return

    cd = str(current_document_id)
    uid = str(user_id)
    sid = str(subject_id)
    n = 0

    with get_session() as s:
        for rel in relationships:
            src = rel.get("source", "").strip()
            tgt = rel.get("target", "").strip()
            rel_type = _sanitize_rel_type(rel.get("relation", ""))
            if not src or not tgt:
                continue

            # Source anchored in current doc → target may exist in another doc
            s.run(
                f"""
                MATCH (src:Entity {{name: $sn, document_id: $cd, user_id: $uid}})
                MATCH (tgt:Entity {{name: $tn, user_id: $uid}})
                WHERE tgt.subject_id = $sid AND tgt.document_id <> $cd
                MERGE (src)-[r:{rel_type} {{cross_doc: true}}]->(tgt)
                """,
                sn=src, tn=tgt, cd=cd, uid=uid, sid=sid,
            )
            # Target anchored in current doc → source may exist in another doc
            s.run(
                f"""
                MATCH (tgt:Entity {{name: $tn, document_id: $cd, user_id: $uid}})
                MATCH (src:Entity {{name: $sn, user_id: $uid}})
                WHERE src.subject_id = $sid AND src.document_id <> $cd
                MERGE (src)-[r:{rel_type} {{cross_doc: true}}]->(tgt)
                """,
                sn=src, tn=tgt, cd=cd, uid=uid, sid=sid,
            )
            n += 1

    if n:
        print(f"[KG Store] Cross-subject edge attempts for {n} extracted relationship(s).")


# ════════════════════════════════════════════════════════════════
# Neo4j — cross-document relationship persistence
# ════════════════════════════════════════════════════════════════

def save_cross_document_relations(cross_rels: List[Dict]) -> None:
    if not cross_rels:
        return

    saved = 0
    with get_session() as s:
        for rel in cross_rels:
            src_name = rel.get("source_entity", "").strip()
            src_doc  = rel.get("source_doc_id", "").strip()
            tgt_name = rel.get("target_entity", "").strip()
            tgt_doc  = rel.get("target_doc_id", "").strip()
            rel_type = _sanitize_rel_type(
                rel.get("relation", "RELATED_TO"), fallback="RELATED_TO"
            )

            if not src_name or not tgt_name or not src_doc or not tgt_doc:
                continue

            s.run(
                f"""
                MATCH  (src:Entity {{name: $src_name, document_id: $src_doc}})
                MATCH  (tgt:Entity {{name: $tgt_name, document_id: $tgt_doc}})
                MERGE  (src)-[r:{rel_type} {{cross_doc: true}}]->(tgt)
                """,
                src_name=src_name, src_doc=src_doc,
                tgt_name=tgt_name, tgt_doc=tgt_doc,
            )

            s.run(
                f"""
                MATCH  (da:Document {{id: $src_doc}})
                MATCH  (db:Document {{id: $tgt_doc}})
                MERGE  (da)-[:{rel_type}]->(db)
                """,
                src_doc=src_doc, tgt_doc=tgt_doc,
            )

            saved += 1

    print(f"[KG Store] Saved {saved} cross-document relationships.")


# ════════════════════════════════════════════════════════════════
# Neo4j — read: full document graph
# ════════════════════════════════════════════════════════════════

def get_document_graph(document_id: str, user_id: str) -> Dict:
    """All entities + semantic (non-structural) relationships for one document."""
    with get_session() as s:

        ent_res = s.run(
            """
            MATCH (e:Entity)
            WHERE e.document_id = $did
              AND e.user_id     = $uid
            RETURN e.name AS name, e.type AS type
            """,
            did=document_id, uid=user_id,
        )
        entities = [{"name": r["name"], "type": r["type"]} for r in ent_res]

        rel_res = s.run(
            """
            MATCH (src:Entity)-[r]->(tgt:Entity)
            WHERE src.document_id = $did
              AND src.user_id     = $uid
              AND tgt.document_id = $did
              AND tgt.user_id     = $uid
              AND NOT type(r) IN ['HAS_ENTITY', 'HAS_SUBJECT', 'HAS_DOCUMENT']
            RETURN src.name AS source,
                   type(r)  AS relation,
                   tgt.name AS target
            """,
            did=document_id, uid=user_id,
        )
        relationships = [
            {"source": r["source"], "relation": r["relation"], "target": r["target"]}
            for r in rel_res
        ]

    return {"entities": entities, "relationships": relationships}


# ════════════════════════════════════════════════════════════════
# Neo4j — read: subject-scoped full graph
# ════════════════════════════════════════════════════════════════

def get_subject_graph(subject_id: str, user_id: str) -> Dict:
    """Every entity + all semantic relationships for a subject."""
    with get_session() as s:

        ent_res = s.run(
            """
            MATCH (e:Entity)
            WHERE e.subject_id = $sid
              AND e.user_id    = $uid
            RETURN e.name        AS name,
                   e.type        AS type,
                   e.document_id AS document_id
            """,
            sid=subject_id, uid=user_id,
        )
        entities = [
            {"name": r["name"], "type": r["type"], "document_id": r["document_id"]}
            for r in ent_res
        ]

        rel_res = s.run(
            """
            MATCH (src:Entity)-[r]->(tgt:Entity)
            WHERE src.subject_id = $sid
              AND src.user_id    = $uid
              AND tgt.subject_id = $sid
              AND tgt.user_id    = $uid
              AND NOT type(r) IN ['HAS_ENTITY', 'HAS_SUBJECT', 'HAS_DOCUMENT']
            RETURN src.name        AS source,
                   type(r)         AS relation,
                   tgt.name        AS target,
                   src.document_id AS source_doc,
                   tgt.document_id AS target_doc,
                   r.cross_doc     AS cross_doc
            """,
            sid=subject_id, uid=user_id,
        )
        relationships = [
            {
                "source":     r["source"],
                "relation":   r["relation"],
                "target":     r["target"],
                "source_doc": r["source_doc"],
                "target_doc": r["target_doc"],
                "cross_doc":  bool(r["cross_doc"]),
            }
            for r in rel_res
        ]

    return {"entities": entities, "relationships": relationships}


# ════════════════════════════════════════════════════════════════
# Neo4j — seed matching helpers
# ════════════════════════════════════════════════════════════════

_TITLE_PREFIX_RE = _re.compile(
    r"^(?:dr\.?|doctor|prof\.?|professor|mr\.?|mrs\.?|ms\.?|miss|sir|madam)\s+",
    _re.IGNORECASE,
)
_TITLE_ANYWHERE_RE = _re.compile(
    r"\b(?:dr|doctor|prof|professor|mr|mrs|ms|miss|sir|madam)\.?\s+",
    _re.IGNORECASE,
)


def _normalize_label_for_match(s: str) -> str:
    s = (s or "").strip().lower()
    s = _TITLE_PREFIX_RE.sub("", s)
    s = _TITLE_ANYWHERE_RE.sub("", s)
    s = _re.sub(r"[^\w\s]", " ", s)
    s = _re.sub(r"\s+", " ", s).strip()
    return s


def normalize_query_entity_hint(s: str) -> str:
    """Normalize a user or graph entity label for comparison (titles, punctuation)."""
    return _normalize_label_for_match(s)


def _token_set(norm: str) -> set:
    return {t for t in norm.split() if len(t) > 1}


def _score_entity_name_match(query_norm: str, candidate_norm: str) -> float:
    if not query_norm or not candidate_norm:
        return 0.0
    if query_norm == candidate_norm:
        return 1.0
    if query_norm in candidate_norm or candidate_norm in query_norm:
        return 0.92
    qt = _token_set(query_norm)
    ct = _token_set(candidate_norm)
    if not qt:
        return 0.0
    if qt <= ct:
        return 0.88
    inter = qt & ct
    ratio = len(inter) / len(qt) if qt else 0.0
    if ratio >= 0.66:
        return 0.55 + 0.3 * ratio
    return difflib.SequenceMatcher(None, query_norm, candidate_norm).ratio()


def list_entities_in_scope_for_matching(
    subject_id:   str,
    user_id:      str,
    document_ids: Optional[List[str]] = None,
    limit:        int = 2500,
) -> List[Dict]:
    """Distinct Entity rows in subject (optionally restricted to documents) for fuzzy seed resolution."""
    doc_clause = ""
    params: Dict = {"sid": subject_id, "uid": user_id, "limit": limit}
    if document_ids:
        doc_clause = "AND e.document_id IN $doc_ids"
        params["doc_ids"] = document_ids

    cypher = f"""
        MATCH (e:Entity)
        WHERE e.subject_id = $sid
          AND e.user_id    = $uid
          AND e.name IS NOT NULL
          AND trim(e.name) <> ''
          {doc_clause}
        RETURN DISTINCT e.name AS name, e.type AS type, e.document_id AS document_id
        LIMIT $limit
    """
    with get_session() as s:
        rows = s.run(cypher, **params).data()
    return [dict(r) for r in rows]


def resolve_flexible_entity_seeds(
    query_hints:  List[str],
    subject_id:   str,
    user_id:      str,
    document_ids: Optional[List[str]] = None,
    min_score:    float = 0.45,  # lowered from 0.55 — catches more partial matches
) -> List[str]:
    """
    Map short / partial query strings to canonical Entity.name values in Neo4j.
    Used when exact toLower(name) IN $hints and CONTAINS both find no seeds.
    """
    hints = [str(h).strip() for h in (query_hints or []) if h and str(h).strip()]
    if not hints:
        return []

    candidates = list_entities_in_scope_for_matching(
        subject_id=subject_id,
        user_id=user_id,
        document_ids=document_ids,
    )
    if not candidates:
        return []

    cand_norms: List[Tuple[str, str]] = []
    for c in candidates:
        name = c.get("name")
        if not name:
            continue
        cand_norms.append((name, _normalize_label_for_match(name)))

    resolved: List[str] = []
    seen_lower: set = set()

    for hint in hints:
        qn = _normalize_label_for_match(hint)
        if not qn:
            continue
        best_name: Optional[str] = None
        best_score = 0.0
        for orig, cn in cand_norms:
            sc = _score_entity_name_match(qn, cn)
            if sc > best_score:
                best_score = sc
                best_name = orig
        if best_name and best_score >= min_score:
            bl = best_name.lower()
            if bl not in seen_lower:
                seen_lower.add(bl)
                resolved.append(best_name)

    return resolved


# ════════════════════════════════════════════════════════════════
# Neo4j — read: query-specific subgraph (subject-scoped)
# ════════════════════════════════════════════════════════════════

def get_subgraph_for_query(
    query_entities: List[str],
    subject_id:     str,
    user_id:        str,
    document_ids:   Optional[List[str]] = None,
    hops:           int = 2,
    limit:          int = 60,
    flexible_seed_match: bool = False,
    include_source_text: bool = False,
) -> Dict:
    """
    Return the hop-bounded neighbourhood around the query entities.

    Seed resolution order:
      1. Exact toLower(name) IN $names          — always runs
      2. CONTAINS match in Neo4j               — fast substring fallback
      3. Python fuzzy scorer (min_score=0.45)  — catches typos / partials
    """
    if not query_entities:
        return {"entities": [], "relationships": []}

    # Clamp hops: 1–4 (safe for interpolation)
    hops_int    = max(1, min(int(hops), 4))
    lower_names = [n.lower() for n in query_entities]

    doc_filter_seed = ""
    doc_filter_nbr  = ""
    params: Dict = {
        "sid":   subject_id,
        "uid":   user_id,
        "names": lower_names,
        "limit": limit,
    }
    if document_ids:
        doc_filter_seed = "AND seed.document_id IN $doc_ids"
        doc_filter_nbr  = "AND neighbor.document_id IN $doc_ids"
        params["doc_ids"] = document_ids

    # ── Step 1: exact toLower match ──────────────────────────────────────
    seed_cypher = f"""
        MATCH (seed:Entity)
        WHERE seed.subject_id    = $sid
          AND seed.user_id       = $uid
          AND toLower(seed.name) IN $names
          {doc_filter_seed}
        RETURN seed.name        AS name,
               seed.type        AS type,
               seed.document_id AS document_id
    """

    with get_session() as s:
        seed_res  = s.run(seed_cypher, **params)
        seed_rows = seed_res.data()

    # ── Step 2: CONTAINS match in Neo4j (fast, before Python fuzzy) ─────
    if not seed_rows and flexible_seed_match:
        contains_rows = []
        with get_session() as s:
            for hint in lower_names:
                if len(hint) < 3:
                    continue
                res = s.run(
                    f"""
                    MATCH (seed:Entity)
                    WHERE seed.subject_id = $sid
                      AND seed.user_id    = $uid
                      AND (toLower(seed.name) CONTAINS $hint
                           OR $hint CONTAINS toLower(seed.name))
                      {doc_filter_seed}
                    RETURN seed.name        AS name,
                           seed.type        AS type,
                           seed.document_id AS document_id
                    LIMIT 5
                    """,
                    sid=subject_id,
                    uid=user_id,
                    hint=hint,
                    **({'doc_ids': document_ids} if document_ids else {}),
                )
                contains_rows.extend(res.data())

        if contains_rows:
            # deduplicate by name
            seen_c, deduped_c = set(), []
            for row in contains_rows:
                if row["name"] not in seen_c:
                    seen_c.add(row["name"])
                    deduped_c.append(row)
            seed_rows = deduped_c
            # update params so expand_cypher below uses matched names
            params["names"] = [r["name"].lower() for r in seed_rows]
            print(
                f"[KG Store] CONTAINS fallback: hints={lower_names!r} "
                f"→ matched {len(seed_rows)} seed(s)"
            )

    # ── Step 3: Python fuzzy resolver ────────────────────────────────────
    if not seed_rows and flexible_seed_match:
        # Expand hints: add individual tokens and adjacent pairs
        # so "little couples new season" also tries "little", "couple", etc.
        expanded_hints = list(query_entities)
        for hint in query_entities:
            tokens = [t for t in hint.split() if len(t) > 3]
            expanded_hints.extend(tokens)
            words = hint.split()
            for i in range(len(words) - 1):
                pair = f"{words[i]} {words[i+1]}"
                if len(pair) > 4:
                    expanded_hints.append(pair)
        # deduplicate
        seen_h, deduped = set(), []
        for h in expanded_hints:
            k = h.lower().strip()
            if k and k not in seen_h:
                seen_h.add(k)
                deduped.append(h)

        resolved_names = resolve_flexible_entity_seeds(
            deduped,
            subject_id=subject_id,
            user_id=user_id,
            document_ids=document_ids,
        )
        if resolved_names:
            print(
                f"[KG Store] Fuzzy seed match: hints={query_entities!r} "
                f"→ resolved={resolved_names!r}"
            )
            lower_names = [n.lower() for n in resolved_names]
            params["names"] = lower_names
            with get_session() as s:
                seed_res  = s.run(seed_cypher, **params)
                seed_rows = seed_res.data()

    if not seed_rows:
        return {"entities": [], "relationships": []}

    # ── Expand *1..N* from each seed — only :Entity neighbours ──────────
    expand_cypher = f"""
        MATCH (seed:Entity)
        WHERE seed.subject_id    = $sid
          AND seed.user_id       = $uid
          AND toLower(seed.name) IN $names
          {doc_filter_seed}

        MATCH path = (seed)-[*1..{hops_int}]-(neighbor:Entity)
        WHERE neighbor.subject_id = $sid
          AND neighbor.user_id    = $uid
          {doc_filter_nbr}

        UNWIND nodes(path) AS n
        WITH DISTINCT n
        WHERE n:Entity
          AND n.name        IS NOT NULL
          AND n.subject_id  = $sid
          AND n.user_id     = $uid

        RETURN
            collect(DISTINCT {{
                name:        n.name,
                type:        n.type,
                document_id: n.document_id
            }}) AS neighbours
        LIMIT $limit
    """

    with get_session() as s:
        expand_res = s.run(expand_cypher, **params)
        expand_row = expand_res.single()

    neighbours: List[Dict] = (expand_row["neighbours"] if expand_row else None) or []

    # Merge seeds + neighbours, deduplicated by name
    seen_names: set        = set()
    entities:   List[Dict] = []

    for row in seed_rows:
        key = row["name"]
        if key and key not in seen_names:
            seen_names.add(key)
            entities.append({
                "name":        row["name"],
                "type":        row["type"] or "Unknown",
                "document_id": row["document_id"],
            })

    for n in neighbours:
        key = n.get("name")
        if key and key not in seen_names:
            seen_names.add(key)
            entities.append({
                "name":        n["name"],
                "type":        n.get("type") or "Unknown",
                "document_id": n.get("document_id"),
            })

    if not entities:
        return {"entities": [], "relationships": []}

    # ── All relationships between the found entities ──────────────────────
    entity_names = [e["name"] for e in entities]

    rel_params: Dict = {
        "sid":          subject_id,
        "uid":          user_id,
        "entity_names": entity_names,
    }

    rel_cypher = """
        MATCH (src:Entity)-[r]->(tgt:Entity)
        WHERE src.subject_id = $sid
          AND src.user_id    = $uid
          AND tgt.subject_id = $sid
          AND tgt.user_id    = $uid
          AND src.name IN $entity_names
          AND tgt.name IN $entity_names
          AND NOT type(r) IN ['HAS_ENTITY', 'HAS_SUBJECT', 'HAS_DOCUMENT']
        RETURN src.name        AS source,
               type(r)         AS relation,
               tgt.name        AS target,
               src.document_id AS source_doc,
               tgt.document_id AS target_doc,
               r.cross_doc     AS cross_doc,
               r.chunk_index   AS chunk_index,
               r.source_text   AS source_text
    """

    with get_session() as s:
        rel_res = s.run(rel_cypher, **rel_params)
        seen_rels:     set        = set()
        relationships: List[Dict] = []
        for r in rel_res:
            key = (r["source"], r["relation"], r["target"])
            if key not in seen_rels:
                seen_rels.add(key)
                relationships.append({
                    "source":     r["source"],
                    "relation":   r["relation"],
                    "target":     r["target"],
                    "source_doc": r["source_doc"],
                    "target_doc": r["target_doc"],
                    "cross_doc":  bool(r["cross_doc"]),
                    **(
                        {
                            "chunk_index": r["chunk_index"],
                            "source_text": r["source_text"] or "",
                        }
                        if include_source_text
                        else {}
                    ),
                })

    return {"entities": entities, "relationships": relationships}


# ════════════════════════════════════════════════════════════════
# Neo4j — read: cross-document relationships
# ════════════════════════════════════════════════════════════════

def get_cross_doc_relationships(subject_id: str, user_id: str) -> List[Dict]:
    """All cross-doc semantic edges within a subject."""
    with get_session() as s:
        result = s.run(
            """
            MATCH (src:Entity)-[r]->(tgt:Entity)
            WHERE src.subject_id = $sid
              AND src.user_id    = $uid
              AND tgt.subject_id = $sid
              AND tgt.user_id    = $uid
              AND r.cross_doc    = true
            RETURN src.name        AS source,
                   type(r)         AS relation,
                   tgt.name        AS target,
                   src.document_id AS source_doc,
                   tgt.document_id AS target_doc
            """,
            sid=subject_id, uid=user_id,
        )
        return [
            {
                "source":     r["source"],
                "relation":   r["relation"],
                "target":     r["target"],
                "source_doc": r["source_doc"],
                "target_doc": r["target_doc"],
            }
            for r in result
        ]


def get_document_cross_doc_links(document_id: str, user_id: str) -> List[Dict]:
    """All cross-doc edges where this document is source or target."""
    with get_session() as s:
        result = s.run(
            """
            MATCH (src:Entity)-[r]->(tgt:Entity)
            WHERE (src.document_id = $did OR tgt.document_id = $did)
              AND src.user_id = $uid
              AND r.cross_doc = true
            RETURN src.name        AS source,
                   type(r)         AS relation,
                   tgt.name        AS target,
                   src.document_id AS source_doc,
                   tgt.document_id AS target_doc
            """,
            did=document_id, uid=user_id,
        )
        return [
            {
                "source":     r["source"],
                "relation":   r["relation"],
                "target":     r["target"],
                "source_doc": r["source_doc"],
                "target_doc": r["target_doc"],
            }
            for r in result
        ]


# ════════════════════════════════════════════════════════════════
# Neo4j — list helpers
# ════════════════════════════════════════════════════════════════

def list_kg_documents(user_id: str) -> List[str]:
    with get_session() as s:
        result = s.run(
            """
            MATCH (e:Entity)
            WHERE e.user_id = $uid
            RETURN DISTINCT e.document_id AS doc_id
            """,
            uid=user_id,
        )
        return [r["doc_id"] for r in result]


def list_kg_documents_for_subject(subject_id: str, user_id: str) -> List[str]:
    with get_session() as s:
        result = s.run(
            """
            MATCH (e:Entity)
            WHERE e.subject_id = $sid
              AND e.user_id    = $uid
            RETURN DISTINCT e.document_id AS doc_id
            """,
            sid=subject_id, uid=user_id,
        )
        return [r["doc_id"] for r in result]


def get_entity_names_for_document(document_id: str, user_id: str) -> List[str]:
    with get_session() as s:
        result = s.run(
            """
            MATCH (e:Entity)
            WHERE e.document_id = $did
              AND e.user_id     = $uid
            RETURN e.name AS name
            """,
            did=document_id, uid=user_id,
        )
        return [r["name"] for r in result]


# ════════════════════════════════════════════════════════════════
# Neo4j — delete
# ════════════════════════════════════════════════════════════════

def delete_document_graph(document_id: str, user_id: str) -> int:
    """
    Delete all Entity nodes for a document.
    Returns count of entities deleted.
    Does NOT touch PostgreSQL.
    """
    with get_session() as s:
        cnt_res = s.run(
            """
            MATCH (e:Entity)
            WHERE e.document_id = $did
              AND e.user_id     = $uid
            RETURN count(e) AS cnt
            """,
            did=document_id, uid=user_id,
        )
        count = int((cnt_res.single() or {"cnt": 0})["cnt"])

        s.run(
            """
            MATCH (e:Entity)
            WHERE e.document_id = $did
              AND e.user_id     = $uid
            DETACH DELETE e
            """,
            did=document_id, uid=user_id,
        )

        s.run(
            """
            MATCH (d:Document)
            WHERE d.id = $did
              AND NOT (d)-[:HAS_ENTITY]->()
            DETACH DELETE d
            """,
            did=document_id,
        )

    print(f"[KG Store] Deleted {count} entities for document={document_id[:8]}.")
    return count


def delete_subject_graph(subject_id: str, user_id: str) -> int:
    """
    Cascading delete for an entire subject from Neo4j.
    Returns count of entity nodes deleted.
    Does NOT touch PostgreSQL.
    """
    with get_session() as s:
        cnt_res = s.run(
            """
            MATCH (e:Entity)
            WHERE e.subject_id = $sid
              AND e.user_id    = $uid
            RETURN count(e) AS cnt
            """,
            sid=subject_id, uid=user_id,
        )
        count = int((cnt_res.single() or {"cnt": 0})["cnt"])

        s.run(
            """
            MATCH (e:Entity)
            WHERE e.subject_id = $sid
              AND e.user_id    = $uid
            DETACH DELETE e
            """,
            sid=subject_id, uid=user_id,
        )

        s.run(
            """
            MATCH (d:Document)
            WHERE d.subject_id = $sid
            DETACH DELETE d
            """,
            sid=subject_id,
        )

        s.run(
            """
            MATCH (sub:Subject)
            WHERE sub.id = $sid
            DETACH DELETE sub
            """,
            sid=subject_id,
        )

    print(
        f"[KG Store] Cascading delete subject={subject_id[:8]}: "
        f"{count} entities + document nodes + subject node removed."
    )
    return count