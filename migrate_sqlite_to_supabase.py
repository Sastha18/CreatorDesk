"""One-time migration from local creatordesk.db to Supabase PostgreSQL.

Run locally with:
    streamlit run migrate_sqlite_to_supabase.py

Make a separate backup of creatordesk.db before running this script.
Existing cloud rows with conflicting keys are left unchanged.
"""
import sqlite3
from pathlib import Path

import streamlit as st
from database import initialize_database, connect_db

DB_PATH = Path(__file__).resolve().parent / "creatordesk.db"

TABLE_COLUMNS = {
    "clients": ["id", "name", "contact", "service", "created_at"],
    "projects": ["id", "client_id", "title", "fee", "due_date",
                 "status", "payment_status", "created_at"],
    "app_settings": ["setting_key", "setting_value"],
    "payments": ["id", "project_id", "amount", "payment_date",
                 "method", "note", "created_at"],
    "expenses": ["id", "title", "amount", "expense_date", "category",
                 "project_id", "note", "created_at"],
    "proposals": ["id", "client_name", "project_title", "proposal_text",
                  "created_at", "status"],
}


def table_exists(sqlite_conn, table):
    row = sqlite_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def migrate():
    if not DB_PATH.exists():
        st.error(f"Local database file not found: {DB_PATH}")
        st.stop()

    initialize_database()
    counts = {}

    with sqlite3.connect(str(DB_PATH)) as local:
        local.row_factory = sqlite3.Row
        with connect_db() as cloud:
            with cloud.cursor() as cur:
                # Parent tables first to preserve foreign-key relationships.
                for table, columns in TABLE_COLUMNS.items():
                    if not table_exists(local, table):
                        counts[table] = "not present locally"
                        continue

                    rows = local.execute(
                        f"SELECT {', '.join(columns)} FROM {table}"
                    ).fetchall()

                    if not rows:
                        counts[table] = 0
                        continue

                    placeholders = ", ".join(["%s"] * len(columns))
                    col_sql = ", ".join(columns)
                    insert_sql = (
                        f"INSERT INTO {table} ({col_sql}) "
                        f"VALUES ({placeholders}) ON CONFLICT DO NOTHING"
                    )
                    inserted = 0
                    for row in rows:
                        values = [row[column] for column in columns]
                        cur.execute(insert_sql, values)
                        inserted += cur.rowcount
                    counts[table] = f"{inserted} inserted; {len(rows) - inserted} skipped"

                # Ensure generated IDs continue above the largest migrated ID.
                for table in ("clients", "projects", "payments", "expenses", "proposals"):
                    cur.execute(
                        "SELECT setval(pg_get_serial_sequence(%s, 'id'), "
                        "COALESCE((SELECT MAX(id) FROM " + table + "), 1), "
                        "(SELECT MAX(id) IS NOT NULL FROM " + table + "))",
                        (f"public.{table}",),
                    )

    st.success("Migration completed. Review the counts below.")
    st.write("Rows inserted; rows skipped were already present or conflicted:")
    st.json(counts)
    st.warning(
        "Keep your SQLite backup. Verify clients, projects, proposals, "
        "payments and expenses in CreatorDesk before deleting or replacing anything."
    )


st.set_page_config(page_title="CreatorDesk database migration", page_icon="🗄️")
st.title("CreatorDesk — SQLite to Supabase migration")
st.caption("Run this locally once, after checking your Supabase connection.")
if st.button("Start migration", type="primary"):
    try:
        migrate()
    except Exception as exc:
        st.error(f"Migration failed: {type(exc).__name__}: {exc}")
        st.info(
            "Your local SQLite file was read but not changed. Fix the error "
            "and rerun only after checking what was already copied."
        )
