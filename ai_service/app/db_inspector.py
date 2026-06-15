#!/usr/bin/env python3
"""
db_inspector.py
===============
Prints a complete map of your PostgreSQL database:
  - All schemas
  - All tables per schema (with row counts)
  - All columns per table (name, type, nullable, default, constraints)
  - All foreign keys
  - All indexes
  - Sample data rows (configurable)
  - Vector embedding status (pgvector)
  - Neo4j graph summary

Usage
-----
    cd D:/Graduation_Project/Agentic-AI-Tutor/ai_service
    python db_inspector.py

    # Show more sample rows:
    python db_inspector.py --rows 5

    # Inspect one specific schema only:
    python db_inspector.py --schema rag

    # Skip sample data (faster):
    python db_inspector.py --no-data

    # Also inspect Neo4j:
    python db_inspector.py --neo4j
"""

import os
import sys
import argparse
from dotenv import load_dotenv

load_dotenv()

# ── allow running from any directory ──────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

try:
    from sqlalchemy import create_engine, text
    from urllib.parse import quote_plus
except ImportError:
    print("Missing sqlalchemy. Run:  pip install sqlalchemy psycopg2-binary")
    sys.exit(1)


# ===========================================================================
# Config
# ===========================================================================

SKIP_SCHEMAS = {"pg_catalog", "information_schema", "pg_toast"}

# Schemas we care about (shown first, in this order)
PRIORITY_SCHEMAS = ["auth", "content", "rag", "public"]


# ===========================================================================
# DB connection
# ===========================================================================

def get_engine():
    host     = os.getenv("DB_HOST",     "localhost")
    port     = os.getenv("DB_PORT",     "5432")
    name     = os.getenv("DB_NAME",     "postgres")
    user     = os.getenv("DB_USER",     "postgres")
    password = os.getenv("DB_PASSWORD", "")

    if password:
        password = quote_plus(password)

    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}?sslmode=require"
    return create_engine(url, connect_args={"options": "-csearch_path=public"})


# ===========================================================================
# Formatters
# ===========================================================================

SEP  = "─" * 70
SEP2 = "═" * 70

def h1(text):  print(f"\n{SEP2}\n  {text}\n{SEP2}")
def h2(text):  print(f"\n{SEP}\n  {text}")
def h3(text):  print(f"\n    ── {text}")


# ===========================================================================
# Schema inspector
# ===========================================================================

def get_schemas(conn):
    rows = conn.execute(text("""
        SELECT schema_name
        FROM information_schema.schemata
        ORDER BY schema_name
    """)).fetchall()
    all_schemas = [r[0] for r in rows if r[0] not in SKIP_SCHEMAS]
    # Sort: priority schemas first, then alphabetical
    priority = [s for s in PRIORITY_SCHEMAS if s in all_schemas]
    rest     = sorted([s for s in all_schemas if s not in PRIORITY_SCHEMAS])
    return priority + rest


def get_tables(conn, schema):
    rows = conn.execute(text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = :schema
          AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """), {"schema": schema}).fetchall()
    return [r[0] for r in rows]


def get_row_count(conn, schema, table):
    try:
        row = conn.execute(
            text(f'SELECT COUNT(*) FROM "{schema}"."{table}"')
        ).fetchone()
        return row[0] if row else 0
    except Exception:
        return "?"


def get_columns(conn, schema, table):
    rows = conn.execute(text("""
        SELECT
            c.column_name,
            c.data_type,
            c.udt_name,
            c.is_nullable,
            c.column_default,
            c.character_maximum_length,
            c.numeric_precision,
            c.numeric_scale
        FROM information_schema.columns c
        WHERE c.table_schema = :schema
          AND c.table_name   = :table
        ORDER BY c.ordinal_position
    """), {"schema": schema, "table": table}).fetchall()
    return rows


def get_primary_keys(conn, schema, table):
    rows = conn.execute(text("""
        SELECT kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
           AND tc.table_schema    = kcu.table_schema
        WHERE tc.constraint_type = 'PRIMARY KEY'
          AND tc.table_schema    = :schema
          AND tc.table_name      = :table
        ORDER BY kcu.ordinal_position
    """), {"schema": schema, "table": table}).fetchall()
    return {r[0] for r in rows}


def get_foreign_keys(conn, schema, table):
    rows = conn.execute(text("""
        SELECT
            kcu.column_name,
            ccu.table_schema AS ref_schema,
            ccu.table_name   AS ref_table,
            ccu.column_name  AS ref_column
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
           AND tc.table_schema    = kcu.table_schema
        JOIN information_schema.constraint_column_usage ccu
            ON ccu.constraint_name = tc.constraint_name
           AND ccu.table_schema    = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_schema    = :schema
          AND tc.table_name      = :table
    """), {"schema": schema, "table": table}).fetchall()
    return rows


def get_indexes(conn, schema, table):
    rows = conn.execute(text("""
        SELECT
            i.relname       AS index_name,
            ix.indisunique  AS is_unique,
            array_to_string(array_agg(a.attname ORDER BY k.n), ', ') AS columns
        FROM pg_class t
        JOIN pg_index ix      ON t.oid = ix.indrelid
        JOIN pg_class i       ON i.oid = ix.indexrelid
        JOIN pg_namespace n   ON n.oid = t.relnamespace
        CROSS JOIN LATERAL unnest(ix.indkey) WITH ORDINALITY AS k(attnum, n)
        JOIN pg_attribute a   ON a.attrelid = t.oid AND a.attnum = k.attnum
        WHERE t.relname  = :table
          AND n.nspname  = :schema
          AND NOT ix.indisprimary
        GROUP BY i.relname, ix.indisunique
        ORDER BY i.relname
    """), {"schema": schema, "table": table}).fetchall()
    return rows


def get_sample_rows(conn, schema, table, n=2):
    try:
        rows = conn.execute(
            text(f'SELECT * FROM "{schema}"."{table}" LIMIT {n}')
        ).fetchall()
        cols = conn.execute(
            text(f'SELECT * FROM "{schema}"."{table}" LIMIT 0')
        ).keys()
        return list(cols), rows
    except Exception as e:
        return [], []


# ===========================================================================
# Print helpers
# ===========================================================================

def format_type(col):
    """Return a human-readable type string for a column row."""
    dtype  = col[1]   # data_type
    udt    = col[2]   # udt_name
    maxlen = col[5]   # character_maximum_length
    prec   = col[6]   # numeric_precision
    scale  = col[7]   # numeric_scale

    if dtype == "USER-DEFINED":
        return udt           # e.g. "vector", "citext"
    if dtype in ("character varying", "character"):
        return f"varchar({maxlen})" if maxlen else "text"
    if dtype == "numeric" and prec:
        return f"numeric({prec},{scale or 0})"
    if dtype == "ARRAY":
        return f"{udt.lstrip('_')}[]"
    return dtype


def truncate(val, max_len=60):
    s = str(val)
    if len(s) > max_len:
        return s[:max_len] + "…"
    return s


def print_table_info(conn, schema, table, show_data, sample_rows, show_fk, show_idx):
    row_count = get_row_count(conn, schema, table)
    pks       = get_primary_keys(conn, schema, table)
    columns   = get_columns(conn, schema, table)
    fks       = get_foreign_keys(conn, schema, table)
    idxs      = get_indexes(conn, schema, table)

    print(f"\n    📋  {schema}.{table}  ({row_count} rows)")
    print(f"    {'Column':<28} {'Type':<22} {'Null':<6} {'Default / Notes'}")
    print(f"    {'─'*28} {'─'*22} {'─'*6} {'─'*30}")

    for col in columns:
        name     = col[0]
        typ      = format_type(col)
        nullable = "YES" if col[3] == "YES" else "NO"
        default  = col[4] or ""
        flags    = []
        if name in pks:
            flags.append("PK")
        if any(fk[0] == name for fk in fks):
            ref = next(f"{fk[1]}.{fk[2]}.{fk[3]}" for fk in fks if fk[0] == name)
            flags.append(f"FK→{ref}")
        notes = " | ".join(flags) + ("  " if flags else "") + truncate(default, 30)
        print(f"    {name:<28} {typ:<22} {nullable:<6} {notes}")

    if show_idx and idxs:
        print(f"\n    Indexes:")
        for idx in idxs:
            uniq = " UNIQUE" if idx[1] else ""
            print(f"      {idx[0]}{uniq}  ({idx[2]})")

    if show_fk and fks:
        print(f"\n    Foreign keys:")
        for fk in fks:
            print(f"      {fk[0]}  →  {fk[1]}.{fk[2]}.{fk[3]}")

    if show_data and row_count and row_count != "?":
        col_names, rows = get_sample_rows(conn, schema, table, sample_rows)
        if rows and col_names:
            print(f"\n    Sample data ({min(sample_rows, row_count)} of {row_count} rows):")
            # Print header
            headers = [truncate(c, 18) for c in col_names]
            print("      " + "  ".join(f"{h:<20}" for h in headers))
            print("      " + "  ".join("─"*20 for _ in headers))
            for row in rows:
                vals = [truncate(v, 18) if v is not None else "NULL" for v in row]
                print("      " + "  ".join(f"{v:<20}" for v in vals))


# ===========================================================================
# Vector / embedding stats
# ===========================================================================

def print_embedding_stats(conn):
    h2("pgvector embedding status")
    try:
        # Check extension exists
        row = conn.execute(text("""
            SELECT extname, extversion
            FROM pg_extension WHERE extname = 'vector'
        """)).fetchone()
        if not row:
            print("  ⚠️  pgvector extension not installed")
            return
        print(f"  pgvector version: {row[1]}")

        # Find all vector columns
        rows = conn.execute(text("""
            SELECT table_schema, table_name, column_name
            FROM information_schema.columns
            WHERE udt_name = 'vector'
            ORDER BY table_schema, table_name
        """)).fetchall()

        if not rows:
            print("  No vector columns found")
            return

        for r in rows:
            s, t, c = r
            total = conn.execute(
                text(f'SELECT COUNT(*) FROM "{s}"."{t}"')
            ).scalar()
            with_emb = conn.execute(
                text(f'SELECT COUNT(*) FROM "{s}"."{t}" WHERE "{c}" IS NOT NULL')
            ).scalar()
            null_emb  = total - with_emb
            print(f"  {s}.{t}.{c}")
            print(f"    Total rows  : {total}")
            print(f"    With vector : {with_emb}")
            print(f"    NULL vector : {null_emb}")
            if with_emb > 0:
                # Get vector dimension from first non-null row
                try:
                    dim_row = conn.execute(
                        text(f'SELECT vector_dims("{c}") FROM "{s}"."{t}" WHERE "{c}" IS NOT NULL LIMIT 1')
                    ).fetchone()
                    if dim_row:
                        print(f"    Dimensions  : {dim_row[0]}")
                except Exception:
                    pass
    except Exception as e:
        print(f"  Error checking embeddings: {e}")


# ===========================================================================
# Neo4j inspector
# ===========================================================================

def print_neo4j_stats():
    h2("Neo4j graph summary")
    try:
        from neo4j import GraphDatabase
        uri      = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
        user     = os.getenv("NEO4J_USERNAME", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password123")

        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as s:
            # Totals
            nodes = s.run("MATCH (n) RETURN count(n) AS c").single()["c"]
            rels  = s.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]
            print(f"  Total nodes        : {nodes}")
            print(f"  Total relationships: {rels}")

            # By subject_id
            rows = s.run("""
                MATCH (e:Entity)
                RETURN
                    COALESCE(e.subject_id, 'NULL') AS subject_id,
                    COALESCE(e.user_id,    'NULL') AS user_id,
                    count(e) AS n
                ORDER BY n DESC
                LIMIT 20
            """).data()
            if rows:
                print(f"\n  Breakdown by subject_id:")
                print(f"  {'subject_id':<30} {'user_id':<20} {'entities':>10}")
                print(f"  {'─'*30} {'─'*20} {'─'*10}")
                for r in rows:
                    sid = (r["subject_id"] or "NULL")[:30]
                    uid = (r["user_id"]    or "NULL")[:20]
                    print(f"  {sid:<30} {uid:<20} {r['n']:>10}")

            # Relationship types
            rel_rows = s.run("""
                MATCH ()-[r]->()
                RETURN type(r) AS rel_type, count(r) AS n
                ORDER BY n DESC LIMIT 15
            """).data()
            if rel_rows:
                print(f"\n  Top relationship types:")
                for r in rel_rows:
                    print(f"    {r['rel_type']:<40} {r['n']:>6}")

        driver.close()
    except ImportError:
        print("  neo4j driver not installed. Run:  pip install neo4j")
    except Exception as e:
        print(f"  Could not connect to Neo4j: {e}")


# ===========================================================================
# Summary table
# ===========================================================================

def print_summary(conn, schemas):
    h2("Database summary")
    print(f"  {'Schema':<20} {'Table':<35} {'Rows':>10}")
    print(f"  {'─'*20} {'─'*35} {'─'*10}")
    for schema in schemas:
        tables = get_tables(conn, schema)
        if not tables:
            print(f"  {schema:<20} (no tables)")
            continue
        for table in tables:
            count = get_row_count(conn, schema, table)
            print(f"  {schema:<20} {table:<35} {str(count):>10}")


# ===========================================================================
# Main
# ===========================================================================

def main():
    parser = argparse.ArgumentParser(description="Inspect your PostgreSQL database")
    parser.add_argument("--rows",     type=int, default=2,    help="Sample rows per table (default: 2)")
    parser.add_argument("--schema",   type=str, default=None, help="Inspect one schema only")
    parser.add_argument("--no-data",  action="store_true",    help="Skip sample data")
    parser.add_argument("--no-fk",    action="store_true",    help="Skip foreign key details")
    parser.add_argument("--no-idx",   action="store_true",    help="Skip index details")
    parser.add_argument("--neo4j",    action="store_true",    help="Also inspect Neo4j")
    parser.add_argument("--summary",  action="store_true",    help="Show only the summary table")
    args = parser.parse_args()

    engine = get_engine()

    try:
        with engine.connect() as conn:
            db_name = conn.execute(text("SELECT current_database()")).scalar()
            db_user = conn.execute(text("SELECT current_user")).scalar()
            pg_ver  = conn.execute(text("SELECT version()")).scalar()

            h1(f"Database Inspector — {db_name}")
            print(f"  User    : {db_user}")
            print(f"  Version : {pg_ver[:60]}")

            schemas = get_schemas(conn)
            if args.schema:
                schemas = [args.schema] if args.schema in schemas else []
                if not schemas:
                    print(f"Schema '{args.schema}' not found.")
                    return

            # Always show summary
            print_summary(conn, schemas)

            if args.summary:
                print_embedding_stats(conn)
                if args.neo4j:
                    print_neo4j_stats()
                return

            # Full inspection
            for schema in schemas:
                tables = get_tables(conn, schema)
                if not tables:
                    continue

                h1(f"Schema: {schema}  ({len(tables)} tables)")

                for table in tables:
                    print_table_info(
                        conn, schema, table,
                        show_data=not args.no_data,
                        sample_rows=args.rows,
                        show_fk=not args.no_fk,
                        show_idx=not args.no_idx,
                    )

            print_embedding_stats(conn)

    except Exception as e:
        print(f"\n❌  Connection failed: {e}")
        import traceback; traceback.print_exc()
        return

    if args.neo4j:
        print_neo4j_stats()

    print(f"\n{SEP2}")
    print(f"  Inspection complete")
    print(SEP2)


if __name__ == "__main__":
    main()