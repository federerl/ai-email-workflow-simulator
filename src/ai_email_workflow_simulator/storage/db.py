"""SQLite-backed mutable queue/review state.

This is the "current state" store for the review UI. The immutable audit
trail of every pipeline decision and human review action lives separately
in audit_log.py (JSONL) -- see that module for why they're kept apart.
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from .. import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_path TEXT NOT NULL,
    subject TEXT NOT NULL,
    sender TEXT NOT NULL,
    sent_at TEXT NOT NULL,
    body_text TEXT NOT NULL,
    category TEXT NOT NULL,
    decision TEXT NOT NULL,
    rationale TEXT NOT NULL,
    draft_text TEXT,
    final_draft_text TEXT,
    edited INTEGER NOT NULL DEFAULT 0,
    review_status TEXT NOT NULL,
    model_id TEXT,
    prompt_version TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _connect():
    config.ensure_dirs()
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _connect() as conn:
        conn.execute(SCHEMA)


def _initial_review_status(decision: str) -> str:
    return {
        "Pursue": "pending_review",
        "Decline": "closed",
        "Needs-Human-Review": "needs_review",
    }[decision]


def insert_item(
    *,
    source_path: str,
    subject: str,
    sender: str,
    sent_at: str,
    body_text: str,
    category: str,
    decision: str,
    rationale: str,
    draft_text: str | None,
    model_id: str | None,
    prompt_version: str | None,
) -> int:
    init_db()
    now = _now()
    with _connect() as conn:
        cur = conn.execute(
            """INSERT INTO items
               (source_path, subject, sender, sent_at, body_text, category,
                decision, rationale, draft_text, final_draft_text, edited,
                review_status, model_id, prompt_version, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?)""",
            (
                source_path,
                subject,
                sender,
                sent_at,
                body_text,
                category,
                decision,
                rationale,
                draft_text,
                draft_text,
                _initial_review_status(decision),
                model_id,
                prompt_version,
                now,
                now,
            ),
        )
        return cur.lastrowid


def get_item(item_id: int) -> sqlite3.Row | None:
    init_db()
    with _connect() as conn:
        return conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()


def list_items() -> list[sqlite3.Row]:
    init_db()
    with _connect() as conn:
        return conn.execute("SELECT * FROM items ORDER BY id DESC").fetchall()


def update_item(item_id: int, **fields) -> None:
    if not fields:
        return
    fields["updated_at"] = _now()
    columns = ", ".join(f"{key} = ?" for key in fields)
    with _connect() as conn:
        conn.execute(
            f"UPDATE items SET {columns} WHERE id = ?",
            (*fields.values(), item_id),
        )
