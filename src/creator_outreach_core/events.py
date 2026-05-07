"""Outreach event recording and retrieval.

Events log every meaningful action in the outreach lifecycle: sent, replied,
bounced, followup_due, etc.  ``raw_metadata`` is stored as JSON TEXT and
round-trips as a Python dict.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Optional

from creator_outreach_core.models import OutreachEvent


def record_event(conn: sqlite3.Connection, event: OutreachEvent) -> str:
    """Insert *event* into ``outreach_events``. Returns the event id."""
    raw_meta_json: Optional[str] = None
    if event.raw_metadata is not None:
        raw_meta_json = json.dumps(event.raw_metadata, ensure_ascii=False)

    conn.execute(
        """
        INSERT INTO outreach_events
          (id, creator_id, event_type, channel, subject, body_path,
           message_id, thread_id, sent_at, replied_at, next_followup_at,
           status, raw_metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event.id,
            event.creator_id,
            event.event_type,
            event.channel,
            event.subject,
            event.body_path,
            event.message_id,
            event.thread_id,
            event.sent_at,
            event.replied_at,
            event.next_followup_at,
            event.status,
            raw_meta_json,
        ),
    )
    conn.commit()
    return event.id


def list_events(
    conn: sqlite3.Connection,
    *,
    creator_id: Optional[str] = None,
    limit: int = 50,
) -> list[OutreachEvent]:
    """Return up to *limit* events, optionally filtered by *creator_id*."""
    if creator_id is not None:
        cur = conn.execute(
            "SELECT * FROM outreach_events WHERE creator_id=? "
            "ORDER BY sent_at DESC LIMIT ?",
            (creator_id, limit),
        )
    else:
        cur = conn.execute(
            "SELECT * FROM outreach_events ORDER BY sent_at DESC LIMIT ?",
            (limit,),
        )
    return [_row_to_event(row) for row in cur.fetchall()]


def get_latest_event(
    conn: sqlite3.Connection,
    *,
    creator_id: str,
    event_type: Optional[str] = None,
) -> Optional[OutreachEvent]:
    """Return the most recent event for *creator_id*, optionally filtered by type."""
    if event_type is not None:
        cur = conn.execute(
            "SELECT * FROM outreach_events WHERE creator_id=? AND event_type=? "
            "ORDER BY sent_at DESC LIMIT 1",
            (creator_id, event_type),
        )
    else:
        cur = conn.execute(
            "SELECT * FROM outreach_events WHERE creator_id=? "
            "ORDER BY sent_at DESC LIMIT 1",
            (creator_id,),
        )
    row = cur.fetchone()
    if row is None:
        return None
    return _row_to_event(row)


def _row_to_event(row: sqlite3.Row) -> OutreachEvent:
    raw_meta = None
    if row["raw_metadata"] is not None:
        try:
            raw_meta = json.loads(row["raw_metadata"])
        except (json.JSONDecodeError, TypeError):
            raw_meta = None
    return OutreachEvent(
        id=row["id"],
        creator_id=row["creator_id"],
        event_type=row["event_type"],
        channel=row["channel"],
        subject=row["subject"],
        body_path=row["body_path"],
        message_id=row["message_id"],
        thread_id=row["thread_id"],
        sent_at=row["sent_at"],
        replied_at=row["replied_at"],
        next_followup_at=row["next_followup_at"],
        status=row["status"],
        raw_metadata=raw_meta,
    )
