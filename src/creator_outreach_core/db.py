"""Database connection and schema helpers for creator-outreach-core.

Usage::

    from creator_outreach_core.db import connect, init_schema, close
    conn = connect("creator_outreach.db")
    init_schema(conn)
    # ... use conn ...
    close(conn)
"""
from __future__ import annotations

import sqlite3
from pathlib import Path


def connect(db_path: Path | str = "creator_outreach.db") -> sqlite3.Connection:
    """Open (or create) the SQLite database at *db_path*.

    Returns a connection with ``row_factory = sqlite3.Row`` so rows behave
    like dicts, and with foreign-key enforcement enabled.
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Run schema.sql against *conn*.

    Idempotent: all statements use ``CREATE TABLE IF NOT EXISTS``.
    """
    schema_path = Path(__file__).parent / "schema.sql"
    sql = schema_path.read_text(encoding="utf-8")
    conn.executescript(sql)
    conn.commit()


def close(conn: sqlite3.Connection) -> None:
    """Close *conn*."""
    conn.close()
