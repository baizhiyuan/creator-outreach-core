"""Suppression list helpers.

A creator/email is permanently suppressed once added. The list is checked
before any outreach action. Removal requires a direct DELETE query (not
exposed in v1 API).

Match logic: suppressed if ANY of:
  - (platform, handle) matches a row where both platform and handle are set
  - email matches a row where email is set
"""
from __future__ import annotations

import datetime
import hashlib
import sqlite3
from typing import Optional

from creator_outreach_core.models import SuppressionEntry


def _gen_id(platform: Optional[str], handle: Optional[str], email: Optional[str]) -> str:
    """Stable ID for a suppression entry."""
    key = f"{platform or ''}:{handle or ''}:{email or ''}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _now_iso() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def add_suppression(
    conn: sqlite3.Connection,
    *,
    platform: Optional[str],
    handle: Optional[str],
    email: Optional[str],
    reason: str,
) -> str:
    """Add a suppression entry. Returns the entry id."""
    entry_id = _gen_id(platform, handle, email)
    now = _now_iso()
    conn.execute(
        "INSERT OR IGNORE INTO suppression_list (id, platform, handle, email, reason, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (entry_id, platform, handle, email, reason, now),
    )
    conn.commit()
    return entry_id


def is_suppressed(
    conn: sqlite3.Connection,
    *,
    platform: Optional[str] = None,
    handle: Optional[str] = None,
    email: Optional[str] = None,
) -> bool:
    """Return True if the given (platform+handle) or email is suppressed."""
    if platform and handle:
        cur = conn.execute(
            "SELECT 1 FROM suppression_list WHERE platform=? AND handle=? LIMIT 1",
            (platform, handle),
        )
        if cur.fetchone():
            return True
    if email:
        cur = conn.execute(
            "SELECT 1 FROM suppression_list WHERE email=? LIMIT 1",
            (email,),
        )
        if cur.fetchone():
            return True
    return False


def list_suppressions(conn: sqlite3.Connection) -> list[SuppressionEntry]:
    """Return all suppression entries."""
    cur = conn.execute(
        "SELECT id, platform, handle, email, reason, created_at "
        "FROM suppression_list ORDER BY created_at"
    )
    return [
        SuppressionEntry(
            id=row["id"],
            platform=row["platform"],
            handle=row["handle"],
            email=row["email"],
            reason=row["reason"],
            created_at=row["created_at"],
        )
        for row in cur.fetchall()
    ]
