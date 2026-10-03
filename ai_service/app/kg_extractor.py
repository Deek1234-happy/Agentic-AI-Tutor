# app/kg_extractor.py

import json
import os
import re
from typing import List, Dict

from .llm import generate_answer, get_gemini_api_key
from .kg_checkpoint import (
    load_checkpoint,
    mark_checkpoint_completed,
    mark_checkpoint_failed,
    mark_checkpoint_processing,
    save_checkpoint,
    KGCheckpoint,
)


# ============================================================
# Intra-document extraction prompt
#
# Issue 1 / 2 fix:
#   • Domain detection forces domain-specific relationship types.
#   • The extracted "relation" value IS the Neo4j relationship label
#     (e.g. "INHERITS_FROM"), NOT a generic wrapper.
#   • FORBIDDEN types are named explicitly.
#   • NQ-style fact questions often ask for attributes, not just entity links.
#     The prompt therefore includes common_fact_attributes such as dates,
#     genres, albums, seasons, locations, and record holders.
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
Use ONLY types from:
1. the matching domain list below, OR
2. common_fact_attributes when the text states an answer-bearing attribute
   such as a date, genre, album, season, location, role, winner, record holder,
   release, publication, or official country.

FORBIDDEN (never use): RELATES_TO, HAS_ENTITY, CONNECTED_TO,
                        ASSOCIATED_WITH, IS_RELATED_TO, HAS, IS, WAS

common_fact_attributes:
  DATE, YEAR, RELEASE_DATE, RELEASED_ON, RELEASED_IN,
  PUBLISHED_ON, PUBLISHED_IN, ESTABLISHED_IN, FOUNDED_IN, MADE_IN,
  GENRE, HAS_GENRE, ALBUM, ON_ALBUM, SEASON, FINAL_SEASON,
  LOCATION, LOCATED_IN, PUBLISHED_IN_LOCATION, FILMED_IN, SET_IN,
  COUNTRY, OFFICIAL_IN, RECORD_HOLDER, MOST_BY, TRAINED_BY,
  WON_BY, WON_IN, AWARDED_TO, PLAYED_BY, STARRING, CHARACTER_BASED_ON,
  AGE, ROLE, POSITION, NAMED_AS, ALSO_CALLED, INSTANCE_OF, RENAMED_TO

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
- Also extract answer-bearing attribute values as entities when they are
  explicit in the text: dates ("March 8 2018"), years ("2002"), seasons
  ("Sixth Season", "Eighth Season"), genres ("Graphic Novel"), albums
  ("Sleeping With The Past"), locations ("Nashville Tennessee"), countries
  ("Nepal"), ages ("Age 44"), and record-holder names.

Relationship rules:
- Source and target must both be entities you extracted in this response.
- Each relationship must be directional: source → target.
- Do NOT invent information absent from the text.
- Prefer specific attribute relations over generic relations:
  * film/show/song/book release date → RELEASED_ON or RELEASED_IN
  * publication date/place → PUBLISHED_ON / PUBLISHED_IN / PUBLISHED_IN_LOCATION
  * genre → HAS_GENRE
  * song appears on album → ON_ALBUM
  * final season / season number → FINAL_SEASON or SEASON
  * location / country / official use → LOCATED_IN or OFFICIAL_IN
  * "most", "record", "trained most", "richest", "winner" → RECORD_HOLDER,
    MOST_BY, TRAINED_BY, WON_BY, or WON_IN as appropriate
  * actor/character questions → PLAYED_BY, STARRING, CHARACTER_BASED_ON
  - When extracting FINAL_SEASON or SEASON, use the LAST value stated in
  the text as definitive. If the text says "Season 7 ended... Season 8
  will be the final season", extract FINAL_SEASON → Eighth Season only.
- When a text contains both an old and new value for the same attribute
  (renamed city, corrected date, updated record), extract only the
  current/final value.
- If CONTEXT FROM PREVIOUS CHUNK is included, you may add relationships between
  an entity in that context and an entity in the CURRENT CHUNK only when both
  are named in your entities list (cross-chunk links).
- For question-answering facts, ALWAYS prefer answer-bearing attribute
  relations over generic event relations.

BAD:
  Game Of Thrones --PARTICIPATED_IN--> Season 8

GOOD:
  Game Of Thrones --FINAL_SEASON--> Eighth Season
Examples:
- "Catch Me If You Can was released in 2002"
  → Catch Me If You Can --RELEASED_IN--> 2002
- "Sacrifice is from the album Sleeping With The Past"
  → Sacrifice --ON_ALBUM--> Sleeping With The Past
- "The final season of Game of Thrones is the eighth season"
  → Game Of Thrones --FINAL_SEASON--> Eighth Season
- "Vikram Samvat is official in Nepal"
  → Vikram Samvat --OFFICIAL_IN--> Nepal
- "Country Music Hall of Fame is located in Nashville, Tennessee"
  → Country Music Hall Of Fame --LOCATED_IN--> Nashville Tennessee
- "Bart Cummings has trained the most Melbourne Cup winners"
  → Bart Cummings --MOST_BY--> Melbourne Cup

- "Diary of a Wimpy Kid: The Getaway is a graphic novel"
  → Diary Of A Wimpy Kid: The Getaway --HAS_GENRE--> Graphic Novel

- "Rocky won the Academy Award for Best Picture in 1976"
  → Rocky --WON_BY--> Academy Award Best Picture 1976

- "Jessica Jones Season 2 was released on March 8 2018"
  → Jessica Jones Season 2 --RELEASED_ON--> March 8 2018

- "The Little Couple season premiered on September 19 2017"
  → The Little Couple --RELEASED_ON--> September 19 2017

- "The Tampa Bay Buccaneers have the most losses in NFL history"
  → Tampa Bay Buccaneers --RECORD_HOLDER--> NFL Losses
- "Bombay was renamed to Mumbai in 1995"
  → Bombay --RENAMED_TO--> Mumbai
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
        provider = os.getenv("KG_LLM_PROVIDER", "groq").strip().lower()
        if provider == "gemini":
          api_key_override = get_gemini_api_key("GEMINI_KG_API_KEY")
          if not api_key_override:
            raise RuntimeError("GEMINI_KG_API_KEY is required when KG_LLM_PROVIDER=gemini")
          api_url_override = os.getenv(
            "KG_LLM_API_URL",
            "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
          )
          default_model = "gemini-3.5-flash-lite"
          default_fallback_models = ""
        elif provider == "groq":
          api_key_override = None
          api_url_override = None
          default_model = "openai/gpt-oss-20b"
          default_fallback_models = "openai/gpt-oss-120b"
        else:
          raise RuntimeError(f"Unsupported KG_LLM_PROVIDER: {provider}")

        fallback_models = [
          model.strip()
          for model in os.getenv("KG_LLM_FALLBACK_MODELS", default_fallback_models).split(",")
          if model.strip()
        ]
        raw = generate_answer(
          prompt,
          temperature=0,
          model=os.getenv("KG_LLM_MODEL", default_model),
          fallback_models=fallback_models,
          max_retries_per_model=max(1, int(os.getenv("KG_LLM_MAX_RETRIES_PER_MODEL", "1"))),
          api_key_override=api_key_override,
          api_url_override=api_url_override,
          timeout=max(5.0, float(os.getenv("KG_LLM_TIMEOUT_SECONDS", "45"))),
        )
    except Exception as exc:
        # Let callers decide whether to resume; do not silently "succeed" with {}.
        raise RuntimeError(f"[KG Extractor] LLM failed ({label}): {exc}") from exc

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

    # ============================================================
    # EDIT:
    # Build combined extraction context:
    # previous chunk tail + current chunk.
    #
    # This improves:
    # - cross-chunk entity linking
    # - temporal relation continuity
    # - multi-sentence fact extraction
    # ============================================================

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

    # ============================================================
    # EDIT:
    # Filter generic useless relations.
    #
    # This significantly improves:
    # - retrieval precision
    # - answer-bearing graph quality
    # - triples-only evaluation
    # ============================================================

    valid_rels = [
        r for r in relationships
        if _is_valid_relation(r.get("relation", ""))
    ]

    dropped = len(relationships) - len(valid_rels)

    if dropped:
        print(
            f"[KG Extractor] chunk-{chunk_index}: "
            f"dropped {dropped} generic rel(s). domain={domain}"
        )

    # ============================================================
    # EDIT:
    # Store FULL extraction context instead of current chunk only.
    #
    # OLD:
    #   source_text = text.strip()
    #
    # NEW:
    #   source_text = combined.strip()
    #
    # Why:
    # The LLM extracted relations using BOTH:
    #   - previous chunk context
    #   - current chunk
    #
    # So debugging must store the SAME exact text the LLM saw.
    # ============================================================

    source_text = combined.strip()

    for rel in valid_rels:
        rel["document_id"] = document_id
        rel["subject_id"] = subject_id
        rel["user_id"] = user_id
        rel["chunk_index"] = chunk_index
        rel["source_text"] = source_text

    return {
        "entities": entities,
        "relationships": valid_rels,
    }

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

    # ============================================================
# EDIT:
# Preserve previous chunk count BEFORE overwriting.
#
# Why:
# We need to distinguish:
# - real resume
# - fresh extraction run
#
# The old code overwrote total_chunks before comparison,
# making resume detection unreliable.
# ============================================================

    cp = load_checkpoint(document_id)

    old_total_chunks = cp.total_chunks

    cp.total_chunks = len(chunks)

    mark_checkpoint_processing(cp)
    # Default behavior:
    # - Start fresh on every run
    # - Only resume when we have evidence the last run stopped mid-way
    #   (checkpoint exists, chunk count matches, and not all chunks completed).
    # ============================================================
# EDIT:
# Resume ONLY if:
# - previous chunk count matches current run
# - extraction was incomplete
# ============================================================

    if (
        old_total_chunks is not None
        and old_total_chunks == len(chunks)
        and int(cp.last_completed_chunk_index) < (len(chunks) - 1)
    ):
        start_idx = max(-1, int(cp.last_completed_chunk_index)) + 1
        prev_tail = cp.previous_chunk_tail or ""
    else:
        cp.last_completed_chunk_index = -1
        cp.previous_chunk_tail = ""
        save_checkpoint(cp)
        start_idx = 0
        prev_tail = ""

    try:
        for idx, chunk in enumerate(chunks):
            if idx < start_idx:
                continue
            text = chunk.get("text", "").strip()
            if not text:
                continue

            result = extract_entities_and_relations(
                text=text,
                document_id=document_id,
                subject_id=subject_id,
                user_id=user_id,
                chunk_index=idx,
                previous_chunk_tail=prev_tail,
            )

            for ent in result["entities"]:
                key = (ent["name"].lower(), document_id)
                if key not in seen:
                    seen.add(key)
                    all_entities.append(ent)

            all_relationships.extend(result["relationships"])
            prev_tail = text[-800:] if len(text) > 800 else text

            # checkpoint after each successful chunk extraction
            cp.last_completed_chunk_index = idx
            cp.previous_chunk_tail = prev_tail
            save_checkpoint(cp)
    except Exception:
        mark_checkpoint_failed(cp)
        raise

    mark_checkpoint_completed(cp)
    print(f"[KG Extractor] doc={document_id[:8]} → {len(all_entities)} entities, {len(all_relationships)} rels")
    return {
        "entities": all_entities,
        "relationships": all_relationships,
        "kg_completed": cp.kg_completed,
        "kg_status": cp.status,
        "completed_at": cp.completed_at,
    }


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
