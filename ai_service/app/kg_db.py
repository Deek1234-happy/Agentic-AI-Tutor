# app/kg_db.py

import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# Neo4j Configuration
# ============================================================

NEO4J_URI      = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
NEO4J_USER     = os.getenv("NEO4J_USER",     "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")


# ============================================================
# Driver — singleton, one connection for the process lifetime
# ============================================================

_driver = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD),
        )
    return _driver


def close_driver():
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


def get_session():
    return get_driver().session()


# ============================================================
# Schema — run once at startup
#
# Graph model:
#   (:User) -[:HAS_SUBJECT]-> (:Subject)
#            -[:HAS_DOCUMENT]-> (:Document)
#             -[:HAS_ENTITY]-> (:Entity)
#
#   (:Entity) -[:CALLS|INHERITS_FROM|TREATS|…]-> (:Entity)
#             (relationship label IS the semantic type — Issue 2 fix)
#
#   (:Entity) -[:CROSS_DOC_RELATES {type}]-> (:Entity)
#   (:Document) -[:CROSS_DOC_REL   {type}]-> (:Document)
#
# IMPORTANT — entity_unique must match the MERGE key in save_graph():
#   MERGE (e:Entity {name: $name, document_id: $document_id, user_id: $user_id})
# If you previously had the old (name, document_id) constraint, drop it first:
#   DROP CONSTRAINT entity_unique IF EXISTS
# ============================================================

def init_kg_schema():
    with get_session() as session:

        # ── User ─────────────────────────────────────────────
        session.run("""
            CREATE CONSTRAINT user_unique IF NOT EXISTS
            FOR (u:User) REQUIRE u.id IS UNIQUE
        """)

        # ── Subject ──────────────────────────────────────────
        session.run("""
            CREATE CONSTRAINT subject_unique IF NOT EXISTS
            FOR (s:Subject) REQUIRE s.id IS UNIQUE
        """)
        session.run("""
            CREATE INDEX subject_user_index IF NOT EXISTS
            FOR (s:Subject) ON (s.user_id)
        """)

        # ── Document ─────────────────────────────────────────
        session.run("""
            CREATE CONSTRAINT document_unique IF NOT EXISTS
            FOR (d:Document) REQUIRE d.id IS UNIQUE
        """)
        session.run("""
            CREATE INDEX document_subject_index IF NOT EXISTS
            FOR (d:Document) ON (d.subject_id)
        """)

        # ── Entity  (3-property key = name + document_id + user_id) ──
        session.run("""
            CREATE CONSTRAINT entity_unique IF NOT EXISTS
            FOR (e:Entity) REQUIRE (e.name, e.document_id, e.user_id) IS UNIQUE
        """)
        session.run("""
            CREATE INDEX entity_subject_index IF NOT EXISTS
            FOR (e:Entity) ON (e.subject_id)
        """)
        session.run("""
            CREATE INDEX entity_user_index IF NOT EXISTS
            FOR (e:Entity) ON (e.user_id)
        """)
        session.run("""
            CREATE INDEX entity_doc_index IF NOT EXISTS
            FOR (e:Entity) ON (e.document_id)
        """)

    print("[KG] Neo4j schema initialised.")