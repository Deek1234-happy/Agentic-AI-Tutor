# app/kg_extractor.py

import json
import re
from typing import List, Dict

from .llm import generate_answer


# ============================================================
# Intra-document extraction prompt
#
# Issue 1 / 2 fix:
#   • Domain detection forces domain-specific relationship types.
#   • The extracted "relation" value IS the Neo4j relationship label
#     (e.g. "INHERITS_FROM"), NOT a generic wrapper.
#   • FORBIDDEN types are named explicitly.
# ============================================================

EXTRACTION_PROMPT = """
You are a knowledge graph extraction expert.

Read the TEXT, detect its academic domain, then extract entities and
DOMAIN-SPECIFIC relationships.

════════════════════════════
STEP 1 — DETECT DOMAIN
════════════════════════════
Choose one: programming_cs | medical_healthcare | physics_science |
            mathematics | business_economics | history_social | other

════════════════════════════
STEP 2 — DOMAIN RELATIONSHIP TYPES
════════════════════════════
Use ONLY types from the matching domain list below.
FORBIDDEN (never use): RELATES_TO, HAS_ENTITY, CONNECTED_TO,
                        ASSOCIATED_WITH, IS_RELATED_TO, HAS, IS, WAS

programming_cs:
  INHERITS_FROM, IMPLEMENTS, THROWS, CALLS, PASSES_TO, RETURNS,
  TAKES_PARAMETER, OVERLOADS, EXTENDS, IMPORTS, INSTANTIATES,
  STORED_IN, USES, DEFINES, CONTAINS, PART_OF, DEPENDS_ON,
  COMPILES_TO, EXECUTES, ALLOCATES, ACCESSES, OVERRIDES

medical_healthcare:
  TREATS, CAUSES, DIAGNOSES, PREVENTS, INTERACTS_WITH,
  PRESCRIBES_FOR, CONTRAINDICATES, SYMPTOM_OF, ADMINISTERED_VIA,
  METABOLIZED_BY, INHIBITS, ACTIVATES, DETECTED_BY, RISK_FACTOR_FOR,
  PART_OF_ANATOMY

physics_science:
  EQUALS, CONVERTS_TO, PRODUCES, REQUIRES, DEPENDS_ON,
  MEASURES, CALCULATES, DERIVED_FROM, GOVERNED_BY, APPLIED_TO,
  REACTS_WITH, EMITS, ABSORBS, ACCELERATES, DECAYS_INTO

mathematics:
  EQUALS, PROVES, DERIVED_FROM, SPECIAL_CASE_OF, GENERALIZES,
  APPLIES_TO, DEFINED_BY, COMPOSED_OF, EQUIVALENT_TO,
  BOUNDED_BY, TRANSFORMS_TO, CONVERGES_TO

business_economics:
  MANAGES, REPORTS_TO, OWNS, EMPLOYS, SUPPLIES,
  PURCHASES_FROM, COMPETES_WITH, INVESTS_IN, REGULATES,
  PARTNERS_WITH, PRODUCES, DISTRIBUTES, ACQUIRES

history_social:
  LED_BY, CAUSED_BY, RESULTED_IN, PARTICIPATED_IN,
  INFLUENCED_BY, PRECEDED_BY, FOLLOWED_BY, ALLIED_WITH,
  OPPOSED_BY, ESTABLISHED_BY, ABOLISHED_BY

other:
  IS_A, PART_OF, USES, DEFINES, REQUIRES, PRODUCES,
  CAUSES, PREVENTS, LEADS_TO, CONSISTS_OF

════════════════════════════
STEP 3 — EXTRACT
════════════════════════════
Entity rules:
- Extract meaningful named entities: classes, algorithms, diseases,
  laws, processes, organisations, people — NOT vague nouns.
- Normalise to Title Case (e.g. "Binary Search Tree").

Relationship rules:
- Source and target must both be entities you extracted in this response.
- Each relationship must be directional: source → target.
- Do NOT invent information absent from the text.
- If CONTEXT FROM PREVIOUS CHUNK is included, you may add relationships between
  an entity in that context and an entity in the CURRENT CHUNK only when both
  are named in your entities list (cross-chunk links).

════════════════════════════
OUTPUT — ONLY this JSON, no markdown, no extra text:
{{
  "domain": "<detected_domain>",
  "entities": [
    {{"name": "EntityName", "type": "EntityType"}},
    ...
  ],
  "relationships": [
    {{"source": "EntityName", "relation": "RELATION_TYPE", "target": "EntityName"}},
    ...
  ]
}}

TEXT:
{text}

JSON:
"""


def _build_extraction_text(main_text: str, previous_chunk_tail: str = "") -> str:
    main_text = main_text.strip()
    if not previous_chunk_tail or not previous_chunk_tail.strip():
        return main_text
    tail = previous_chunk_tail.strip()
    if len(tail) > 1500:
        tail = tail[-1500:]
    return (
        "=== CONTEXT (end of previous chunk; use only to link entities to the current chunk) ===\n"
        f"{tail}\n\n"
        "=== CURRENT CHUNK (primary extraction target) ===\n"
        f"{main_text}"
    )


# ============================================================
# Cross-document extraction prompt
# ============================================================

CROSS_DOC_PROMPT = """
You are an academic knowledge graph expert.

Two documents from the SAME SUBJECT are summarised below.
Identify relationships that cross FROM Document A TO Document B.

ALLOWED CROSS-DOCUMENT RELATIONSHIP TYPES:
  PREREQUISITE_TO, BUILDS_UPON, FOLLOWED_BY, CONTRASTS_WITH,
  EXTENDS, USED_IN, DEFINED_IN_CONTEXT_OF, GENERALIZES, SPECIALIZES

RULES:
- Output a relationship ONLY when BOTH entity names appear in the entity lists.
- Do NOT invent entities or relationships.
- Return ONLY valid JSON, no markdown.

OUTPUT FORMAT:
{{
  "cross_document_relationships": [
    {{
      "source_entity":  "EntityName",
      "source_doc_id":  "document_id_string",
      "relation":       "RELATION_TYPE",
      "target_entity":  "EntityName",
      "target_doc_id":  "document_id_string"
    }}
  ]
}}

DOCUMENT A (id: {doc_a_id}, title: {doc_a_title}):
Entities: {doc_a_entities}

DOCUMENT B (id: {doc_b_id}, title: {doc_b_title}):
Entities: {doc_b_entities}

JSON:
"""


# ============================================================
# Forbidden relationship types (post-extraction filter)
# ============================================================

_FORBIDDEN = {
    "RELATES_TO", "HAS_ENTITY", "CONNECTED_TO", "ASSOCIATED_WITH",
    "IS_RELATED_TO", "RELATED_TO", "HAS", "IS", "WAS", "ARE",
}


def _is_valid_relation(rel_type: str) -> bool:
    return rel_type.strip().upper() not in _FORBIDDEN and len(rel_type.strip()) >= 3


# ============================================================
# LLM JSON helper
# ============================================================

def _call_llm_for_json(prompt: str, label: str) -> dict:
    try:
        raw = generate_answer(prompt, temperature=0)
    except Exception as exc:
        print(f"[KG Extractor] LLM failed ({label}): {exc}")
        return {}

    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?", "", raw).strip()
    raw = re.sub(r"```$",          "", raw).strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass

    print(f"[KG Extractor] JSON parse failed ({label}). Snippet: {raw[:300]}")
    return {}


# ============================================================
# Single-chunk extraction
# ============================================================

def extract_entities_and_relations(
    text:                 str,
    document_id:          str,
    subject_id:           str,
    user_id:              str,
    chunk_index:          int = 0,
    previous_chunk_tail:  str = "",
) -> Dict:
    combined = _build_extraction_text(text, previous_chunk_tail)
    data = _call_llm_for_json(
        EXTRACTION_PROMPT.format(text=combined),
        f"chunk-{chunk_index}",
    )
    entities      = data.get("entities", [])
    relationships = data.get("relationships", [])
    domain        = data.get("domain", "unknown")

    for ent in entities:
        ent["document_id"] = document_id
        ent["subject_id"]  = subject_id
        ent["user_id"]     = user_id

    valid_rels = [r for r in relationships if _is_valid_relation(r.get("relation", ""))]
    dropped    = len(relationships) - len(valid_rels)
    if dropped:
        print(f"[KG Extractor] chunk-{chunk_index}: dropped {dropped} generic rel(s). domain={domain}")

    return {"entities": entities, "relationships": valid_rels}


# ============================================================
# Batch: all chunks of one document
# ============================================================

def extract_from_chunks(
    chunks:      List[Dict],
    document_id: str,
    subject_id:  str,
    user_id:     str,
) -> Dict:
    all_entities:      List[Dict] = []
    all_relationships: List[Dict] = []
    seen = set()

    for idx, chunk in enumerate(chunks):
        text = chunk.get("text", "").strip()
        if not text:
            continue

        result = extract_entities_and_relations(
            text=text,
            document_id=document_id,
            subject_id=subject_id,
            user_id=user_id,
            chunk_index=idx,
        )

        for ent in result["entities"]:
            key = (ent["name"].lower(), document_id)
            if key not in seen:
                seen.add(key)
                all_entities.append(ent)

        all_relationships.extend(result["relationships"])

    print(f"[KG Extractor] doc={document_id[:8]} → {len(all_entities)} entities, {len(all_relationships)} rels")
    return {"entities": all_entities, "relationships": all_relationships}


# ============================================================
# Cross-document extraction
# ============================================================

def extract_cross_document_relations(
    doc_a_id:       str,
    doc_a_title:    str,
    doc_a_entities: List[str],
    doc_b_id:       str,
    doc_b_title:    str,
    doc_b_entities: List[str],
) -> List[Dict]:
    if not doc_a_entities or not doc_b_entities:
        return []

    prompt = CROSS_DOC_PROMPT.format(
        doc_a_id=doc_a_id,
        doc_a_title=doc_a_title,
        doc_a_entities=", ".join(doc_a_entities[:60]),
        doc_b_id=doc_b_id,
        doc_b_title=doc_b_title,
        doc_b_entities=", ".join(doc_b_entities[:60]),
    )

    data = _call_llm_for_json(prompt, f"cross-{doc_a_id[:8]}-{doc_b_id[:8]}")
    rels = data.get("cross_document_relationships", [])
    print(f"[KG Extractor] cross-doc ({doc_a_id[:8]}↔{doc_b_id[:8]}): {len(rels)} rels")
    return rels