# app/kg_service.py

import hashlib
import json
import re
from typing import List, Dict, Optional, Set

from .llm import generate_answer
from .kg_extractor import extract_from_chunks, extract_cross_document_relations
from .kg_store import (
    # PostgreSQL validation (Issue 1)
    document_exists_in_postgres,
    subject_exists_in_postgres,
    # structural nodes
    upsert_user_node,
    upsert_subject_node,
    upsert_document_node,
    # graph persistence
    save_graph,
    save_cross_document_relations,
    # reads
    get_document_graph,
    get_subject_graph,
    get_subgraph_for_query,
    get_cross_doc_relationships,
    get_document_cross_doc_links,
    list_kg_documents_for_subject,
    get_entity_names_for_document,
    get_documents_for_subject,
    get_subject_id_for_session,
    get_subject_for_document,
    normalize_query_entity_hint,
    # delete
    delete_document_graph,
    delete_subject_graph,
    set_document_status

)


IDK_MESSAGE = "I don't know."


# ════════════════════════════════════════════════════════════════
# Issue 1 — ID validation before build
# ════════════════════════════════════════════════════════════════

class KGValidationError(Exception):
    """Raised when a required ID does not exist in PostgreSQL."""


def validate_build_ids(document_id: str, subject_id: str) -> None:

    """
    Verify document_id and subject_id both exist in PostgreSQL before
    any Neo4j writes happen.  Raises KGValidationError (→ HTTP 404)
    with a precise message so the caller knows exactly what is missing.
    """
    if not document_exists_in_postgres(document_id):
        raise KGValidationError(
            f"document_id '{document_id}' not found in content.documents "
            "(or is marked deleted). Process the document through the RAG "
            "extraction pipeline first so it exists in the database."
        )

    if not subject_exists_in_postgres(subject_id):
        raise KGValidationError(
            f"subject_id '{subject_id}' not found in content.subjects. "
            "Create the subject through the main API first."
        )

# ════════════════════════════════════════════════════════════════
# Build KG for one document
# ════════════════════════════════════
def build_knowledge_graph(
    chunks:       List[Dict],
    document_id:  str,
    user_id:      str,
    subject_id:   str,
    subject_name: str = "",
    filename:     str = "",
    doc_order:    int = 0,
) -> Dict:
    """
    1. Validate document_id and subject_id exist in PostgreSQL.
    2. Upsert structural nodes (User, Subject, Document) in Neo4j.
    3. Extract entities + intra-doc relationships from all chunks via LLM.
    4. Persist everything in Neo4j.

    Raises KGValidationError (→ HTTP 404) if either ID is unknown.
    """
    # ── Validate ─────────────────────────────────────────────
    validate_build_ids(document_id, subject_id)
    set_document_status(document_id, "PROCESSING")

    try:

        # ── Structural nodes ─────────────────────────────────────
        upsert_user_node(user_id)
        upsert_subject_node(
            subject_id=subject_id,
            subject_name=subject_name or subject_id,
            user_id=user_id,
        )
        upsert_document_node(
            document_id=document_id,
            filename=filename or document_id,
            subject_id=subject_id,
            user_id=user_id,
            doc_order=doc_order,
        )

        # ── Extract ──────────────────────────────────────────────
        extracted = extract_from_chunks(
            chunks=chunks,
            document_id=document_id,
            subject_id=subject_id,
            user_id=user_id,
        )

        # ── Persist ──────────────────────────────────────────────
        save_graph(
            entities=extracted["entities"],
            relationships=extracted["relationships"],
        )
        set_document_status(document_id, "COMPLETED")

        print(
            f"[KG Service] Built: doc={document_id[:8]} subj={subject_id[:8]} "
            f"entities={len(extracted['entities'])} rels={len(extracted['relationships'])}"
        )

        return {
            "document_id":         document_id,
            "subject_id":          subject_id,
            "entities_saved":      len(extracted["entities"]),
            "relationships_saved": len(extracted["relationships"]),
            "kg_completed":        extracted.get("kg_completed", True),
            "kg_status":           extracted.get("kg_status", "COMPLETED"),
            "completed_at":        extracted.get("completed_at"),
        }
    except Exception:
        set_document_status(document_id, "FAILED")
        raise
    


# ════════════════════════════════════════════════════════════════
# Build cross-document relationships for an entire subject
#
# Issue 3 answer (documented here):
#   • Reads all non-deleted documents from PostgreSQL for the subject,
#     ordered by upload_time (= lecture order).
#   • For ≤ 10 documents: compares ALL unique ordered pairs (O(n²)).
#   • For > 10 documents: consecutive pairs only (scalable).
#   • For each pair: fetches entity name lists from Neo4j, then calls
#     the LLM cross-doc extraction prompt.
#   • Stores results as CROSS_DOC_RELATES edges (entity level) and
#     CROSS_DOC_REL edges (document level).
#   • Returns summary counts.
# ════════════════════════════════════════════════════════════════

def build_cross_document_relations(subject_id: str, user_id: str) -> Dict:
    """Link all documents within a subject via cross-document relationships."""

    documents = get_documents_for_subject(subject_id=subject_id, user_id=user_id)

    if len(documents) < 2:
        print(f"[KG Service] Subject {subject_id[:8]} has <2 indexed docs — skipping.")
        return {
            "subject_id":                    subject_id,
            "documents_processed":           len(documents),
            "pairs_compared":                0,
            "cross_doc_relationships_saved": 0,
        }

    pairs: List[tuple] = []
    if len(documents) <= 10:
        for i in range(len(documents)):
            for j in range(i + 1, len(documents)):
                pairs.append((documents[i], documents[j]))
    else:
        for i in range(len(documents) - 1):
            pairs.append((documents[i], documents[i + 1]))

    total_saved = 0
    for doc_a, doc_b in pairs:
        entities_a = get_entity_names_for_document(doc_a["id"], user_id)
        entities_b = get_entity_names_for_document(doc_b["id"], user_id)

        if not entities_a or not entities_b:
            continue

        cross_rels = extract_cross_document_relations(
            doc_a_id=doc_a["id"],       doc_a_title=doc_a["filename"],
            doc_a_entities=entities_a,
            doc_b_id=doc_b["id"],       doc_b_title=doc_b["filename"],
            doc_b_entities=entities_b,
        )
        if cross_rels:
            save_cross_document_relations(cross_rels)
            total_saved += len(cross_rels)

    print(
        f"[KG Service] Cross-doc subject={subject_id[:8]}: "
        f"{total_saved} rels across {len(pairs)} pairs."
    )
    return {
        "subject_id":                    subject_id,
        "documents_processed":           len(documents),
        "pairs_compared":                len(pairs),
        "cross_doc_relationships_saved": total_saved,
    }


# ════════════════════════════════════════════════════════════════
# Entity recognition from a query (LLM-based)
# ════════════════════════════════════════════════════════════════

ENTITY_RECOGNITION_PROMPT = """
You are a named entity recognizer.

Extract every meaningful entity (concept, algorithm, person, condition, process, etc.)
from the question below.

Return ONLY a JSON array of strings — no explanations, no markdown fences.

QUESTION:
{question}

JSON:
"""


def identify_query_entities(question: str) -> List[str]:
    prompt = ENTITY_RECOGNITION_PROMPT.format(question=question.strip())
    try:
        raw = generate_answer(prompt, temperature=0)
    except Exception as exc:
        print(f"[KG Service] Entity recognition failed: {exc}")
        return []

    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?", "", raw).strip()
    raw = re.sub(r"```$",          "", raw).strip()

    try:
        entities = json.loads(raw)
        if isinstance(entities, list):
            return [str(e).strip() for e in entities if e]
    except json.JSONDecodeError:
        m = re.search(r"\[.*\]", raw, re.DOTALL)
        if m:
            try:
                entities = json.loads(m.group(0))
                return [str(e).strip() for e in entities if e]
            except json.JSONDecodeError:
                pass

    print(f"[KG Service] Could not parse entity list: {raw[:200]}")
    return []


# def _fallback_hints_from_question(question: str) -> List[str]:
#     """Cheap hints when the LLM NER returns nothing or misses a short name."""
#     q = (question or "").strip()
#     if not q:
#         return []
#     q = re.sub(
#         r"^(?:who|what|when|where|why|how)\s+(?:is|are|was|were)\s+",
#         "",
#         q,
#         flags=re.I,
#     )
#     q = re.sub(r"^(?:tell\s+me\s+about|define|explain)\s+", "", q, flags=re.I)
#     q = q.strip().rstrip("?.!").strip()
#     if len(q) >= 2:
#         return [q]
#     return []
def _fallback_hints_from_question(question: str) -> List[str]:
    """
    Extract multiple candidate seed terms from the question,
    not just the whole stripped string.
    """
    q = (question or "").strip()
    if not q:
        return []

    # strip leading question words
    q = re.sub(
        r"^(?:who|what|when|where|why|how)\s+(?:is|are|was|were|did|does|do)\s+",
        "", q, flags=re.I,
    )
    q = re.sub(r"^(?:tell\s+me\s+about|define|explain)\s+", "", q, flags=re.I)
    q = q.strip().rstrip("?.!").strip()

    hints = []

    # add the full stripped phrase
    if len(q) >= 2:
        hints.append(q)

    # also add each capitalized word/phrase (likely proper nouns)
    # e.g. "sacrifice by elton john" → ["Sacrifice", "Elton John"]
    proper = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*', question)
    hints.extend(proper)

    # add individual words longer than 4 chars (catches lowercase titles)
    words = [w for w in re.split(r'\W+', q) if len(w) > 4]
    hints.extend(words)

    # deduplicate preserving order
    seen, out = set(), []
    for h in hints:
        k = h.lower().strip()
        if k and k not in seen:
            seen.add(k)
            out.append(h.strip())

    return out

# ════════════════════════════════════════════════════════════════
# Subject-scoped subgraph retrieval
# ════════════════════════════════════════════════════════════════

def retrieve_subgraph_for_subject(
    question:     str,
    subject_id:   str,
    user_id:      str,
    document_ids: Optional[List[str]] = None,
    hops:         int = 2,
    flexible_seed_match: bool = False,
    include_source_text: bool = False,
    use_llm_query_entities: bool = True,
) -> Dict:
    """Identify query entities then fetch the hop-bounded subgraph."""
    query_entities = identify_query_entities(question) if use_llm_query_entities else []
    if flexible_seed_match:
        merged: List[str] = []
        seen_m: Set[str] = set()
        for e in query_entities + _fallback_hints_from_question(question):
            if not e:
                continue
            s = str(e).strip()
            if not s:
                continue
            key = s.lower()
            if key not in seen_m:
                seen_m.add(key)
                merged.append(s)
        query_entities = merged
    print(f"\n[KG Service] Query entities: {query_entities}")

    subgraph = get_subgraph_for_query(
        query_entities=query_entities,
        subject_id=subject_id,
        user_id=user_id,
        document_ids=document_ids,
        hops=hops,
        flexible_seed_match=flexible_seed_match,
        include_source_text=include_source_text,
    )

    print(
        f"[KG Service] Subgraph: {len(subgraph['entities'])} nodes, "
        f"{len(subgraph['relationships'])} edges"
    )
    return subgraph


# ════════════════════════════════════════════════════════════════
# Session-aware subgraph retrieval (used internally by chat_service)
# ════════════════════════════════════════════════════════════════

def retrieve_subgraph_for_session(
    question:             str,
    session_id:           str,
    user_id:              str,
    allowed_document_ids: List[str],
    hops:                 int = 2,
) -> Dict:
    """Resolve subject from session then retrieve the subgraph."""
    subject_id = get_subject_id_for_session(session_id)
    if not subject_id:
        print(f"[KG Service] No subject for session={session_id}")
        return {"entities": [], "relationships": []}

    return retrieve_subgraph_for_subject(
        question=question,
        subject_id=subject_id,
        user_id=user_id,
        document_ids=[str(d) for d in allowed_document_ids],
        hops=hops,
        flexible_seed_match=True,
    )


# ════════════════════════════════════════════════════════════════
# Structured subgraph for API + LLM (JSON)
# ════════════════════════════════════════════════════════════════


def _entity_stable_id(name: str, document_id: Optional[str]) -> str:
    raw = f"{name or ''}\0{document_id or ''}"
    return "e_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def focus_subgraph_for_query(
    subgraph: Dict,
    question: str,
    max_entities: int = 28,
) -> Dict:
    """
    Returns a smaller subgraph: query-relevant seeds (NER + text match)
    plus their 1-hop neighbors, capped for visualization.
    """
    entities = list(subgraph.get("entities") or [])
    relationships = list(subgraph.get("relationships") or [])
    if not entities and not relationships:
        return {"entities": [], "relationships": []}

    q_terms = identify_query_entities(question)
    q_terms = list(dict.fromkeys(
        [str(t).strip() for t in q_terms if t and str(t).strip()]
        + _fallback_hints_from_question(question)
    ))
    q_lower = question.lower()

    def name_matches_query(name: str) -> bool:
        if not name:
            return False
        nl = normalize_query_entity_hint(name)
        for t in q_terms:
            if not t:
                continue
            tl = normalize_query_entity_hint(t)
            if tl and (tl == nl or tl in nl or nl in tl):
                return True
        return bool(nl and nl in normalize_query_entity_hint(question))

    seeds: Set[str] = {e["name"] for e in entities if name_matches_query(e.get("name", ""))}
    if not seeds:
        for e in entities:
            n = (e.get("name") or "").strip()
            if n and len(n) > 1 and n.lower() in q_lower:
                seeds.add(n)

    if not seeds:
        deg: Dict[str, int] = {}
        for r in relationships:
            for k in ("source", "target"):
                x = r.get(k)
                if x:
                    deg[x] = deg.get(x, 0) + 1
        if deg:
            seeds = {max(deg.keys(), key=lambda k: deg[k])}
        elif entities:
            seeds = {entities[0]["name"]}

    names: Set[str] = set(seeds)
    for r in relationships:
        s, t = r.get("source"), r.get("target")
        if not s or not t:
            continue
        if s in seeds or t in seeds:
            names.add(s)
            names.add(t)

    if len(names) > max_entities:
        deg = {}
        for r in relationships:
            for k in ("source", "target"):
                x = r.get(k)
                if x in names:
                    deg[x] = deg.get(x, 0) + 1
        non_seed = [n for n in names if n not in seeds]
        non_seed.sort(key=lambda n: -deg.get(n, 0))
        keep = set(seeds)
        for n in non_seed:
            if len(keep) >= max_entities:
                break
            keep.add(n)
        names = keep

    kept_entities = [e for e in entities if e.get("name") in names]
    kept_names = {e["name"] for e in kept_entities}
    kept_rels = [
        r
        for r in relationships
        if r.get("source") in kept_names and r.get("target") in kept_names
    ]
    return {"entities": kept_entities, "relationships": kept_rels}


def subgraph_to_kg_context(subgraph: Dict) -> Dict[str, List]:
    """
    Graph payload for /kg/answer/subject: entities with stable ids; edges by id.
    """
    entities = subgraph.get("entities") or []
    relationships = subgraph.get("relationships") or []

    name_to_id: Dict[str, str] = {}
    entities_out: List[Dict] = []
    for ent in entities:
        name = ent.get("name") or ""
        doc_id = ent.get("document_id")
        doc_str = str(doc_id) if doc_id is not None else None
        eid = _entity_stable_id(name, doc_str)
        name_to_id[name] = eid
        entities_out.append(
            {
                "id":    eid,
                "label": name,
                "type":  ent.get("type") or "Unknown",
            }
        )

    relationships_out: List[Dict] = []
    for rel in relationships:
        sname = rel.get("source") or ""
        tname = rel.get("target") or ""
        if not sname or not tname:
            continue
        sid = name_to_id.get(sname)
        tid = name_to_id.get(tname)
        if not sid or not tid:
            continue
        relationships_out.append(
            {
                "source":   sid,
                "relation": rel.get("relation") or "RELATED",
                "target":   tid,
            }
        )

    return {"entities": entities_out, "relationships": relationships_out}


# ════════════════════════════════════════════════════════════════
# Format subgraph as LLM-readable text
# ════════════════════════════════════════════════════════════════

def format_subgraph_as_text(subgraph: Dict) -> str:
    if not subgraph["entities"] and not subgraph["relationships"]:
        return ""

    lines: List[str] = []

    if subgraph["entities"]:
        lines.append("Entities:")
        for ent in subgraph["entities"]:
            doc_tag = f" [doc:{ent['document_id'][:8]}]" if ent.get("document_id") else ""
            lines.append(f"  - {ent['name']} (type: {ent['type']}){doc_tag}")

    if subgraph["relationships"]:
        lines.append("\nRelationships:")
        for rel in subgraph["relationships"]:
            source   = rel.get("source")   or ""
            relation = rel.get("relation") or "RELATED"
            target   = rel.get("target")   or ""
            if not source or not target:
                continue
            cross = " [cross-lecture]" if rel.get("cross_doc") else ""
            lines.append(f"  - {source} --[{relation}]--> {target}{cross}")

    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════
# KG-only answer generation
#
# Issue 5 fix:
#   The old prompt said "use ONLY the KG" but provided only entity
#   names + types — no textual description.  For "what is X?", the
#   LLM correctly returned IDK because there was nothing to say.
#
#   Fix: the new prompt teaches the LLM to reason from:
#     (a) entity type → "X is a <type>"
#     (b) outgoing relationships → "X calls Y", "X inherits from Z"
#     (c) incoming relationships → "X is called by A"
#   This allows descriptive answers even when there is no free text,
#   while still refusing when the entity genuinely has no connections.
# ════════════════════════════════════════════════════════════════

KG_ANSWER_PROMPT = """
You are an academic tutor with access to a structured knowledge graph.

The graph is JSON with:
- "entities": each has "id", "label" (name), and "type".
- "relationships": each has "source" and "target" as entity "id" strings, plus "relation".

Use only this JSON to answer the student's question.

ANSWERING RULES:
1. "What is X?" — X appears in the graph:
   - Start with: "X is a <type>."
   - Elaborate using outgoing relationships: describe what X does or connects to.
   - Elaborate using incoming relationships: describe what depends on or uses X.
   - Use relationship semantics to infer meaning:
       INHERITS_FROM  means specialisation / subclass
       CALLS          means invokes / depends on at runtime
       TREATS         means used therapeutically for
       CAUSES         means leads to / produces
       (apply the same logic to other relationship types)
2. Explain relationships in plain, educational language using full sentences.
3. If the graph contains no relevant information at all, reply exactly:
   "I don't know."
4. Do NOT add facts not present in the graph.
5. Answer in the same language as the question.

KNOWLEDGE GRAPH (JSON):
{kg_context_json}

QUESTION:
{question}

ANSWER:
"""


def generate_kg_answer(question: str, subgraph: Dict) -> str:
    payload = subgraph_to_kg_context(subgraph)
    if not payload["entities"] and not payload["relationships"]:
        return IDK_MESSAGE

    kg_context_json = json.dumps(payload, ensure_ascii=False, indent=2)
    prompt = KG_ANSWER_PROMPT.format(kg_context_json=kg_context_json, question=question)
    try:
        answer = generate_answer(prompt, temperature=0.1)
        return answer.strip() if answer else IDK_MESSAGE
    except Exception as exc:
        print(f"[KG Service] Answer generation failed: {exc}")
        return IDK_MESSAGE


# ════════════════════════════════════════════════════════════════
# Hybrid answer fusion (used by chat_service)
# ════════════════════════════════════════════════════════════════

HYBRID_FUSION_PROMPT = """
You are an academic tutor synthesizing two knowledge sources.

SOURCE 1 — Document Retrieval Answer:
{rag_answer}

SOURCE 2 — Knowledge Graph Answer:
{kg_answer}

RULES:
- Combine both into a single coherent, non-repetitive explanation.
- If one source says "I don't know", rely entirely on the other.
- If both say "I don't know", reply exactly: "I don't know."
- Answer in the same language as the question.
- Do NOT mention "Source 1" or "Source 2".

QUESTION:
{question}

COMBINED ANSWER:
"""


def fuse_answers(question: str, rag_answer: str, kg_answer: str) -> str:
    rag_idk = not rag_answer or IDK_MESSAGE.lower() in rag_answer.lower()
    kg_idk  = not kg_answer  or IDK_MESSAGE.lower() in kg_answer.lower()

    if rag_idk and kg_idk:
        return IDK_MESSAGE
    if rag_idk:
        return kg_answer
    if kg_idk:
        return rag_answer

    try:
        fused = generate_answer(
            HYBRID_FUSION_PROMPT.format(
                rag_answer=rag_answer,
                kg_answer=kg_answer,
                question=question,
            ),
            temperature=0.1,
        )
        return fused.strip() if fused else rag_answer
    except Exception as exc:
        print(f"[KG Service] Fusion failed: {exc}")
        return rag_answer


# ════════════════════════════════════════════════════════════════
# Convenience wrappers
# ════════════════════════════════════════════════════════════════

def remove_document_graph(document_id: str, user_id: str) -> int:
    return delete_document_graph(document_id, user_id)


def remove_subject_graph(subject_id: str, user_id: str) -> int:
    return delete_subject_graph(subject_id, user_id)
