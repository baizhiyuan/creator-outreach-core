"""Typed dataclasses matching the creator-outreach-core SQLite schema.

All fields mirror the column names in schema.sql verbatim.
``risk_flags`` and ``raw_metadata`` are stored as JSON TEXT in the DB;
serialization/deserialization is handled in importers.py / events.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Status constant
# ---------------------------------------------------------------------------

CANONICAL_STATUSES = (
    "new",
    "enriched",
    "ranked",
    "drafted",
    "approved",
    "sent",
    "followup_1_due",
    "followup_1_sent",
    "followup_2_due",
    "followup_2_sent",
    "replied",
    "closed",
    "suppressed",
)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Creator:
    id: str
    platform: str
    handle: str
    profile_url: str
    display_name: str | None = None
    bio: str | None = None
    category: str | None = None
    followers_count: int | None = None
    avg_views: int | None = None
    engagement_rate: float | None = None
    region: str | None = None
    language: str | None = None
    contact_email: str | None = None
    website: str | None = None
    link_in_bio: str | None = None
    source: str | None = None
    source_url: str | None = None
    discovered_at: str | None = None
    last_enriched_at: str | None = None
    status: str = "new"
    score: int | None = None
    risk_level: str | None = None
    risk_flags: list[str] = field(default_factory=list)  # stored as JSON TEXT in DB
    notes: str | None = None
    personalization: str | None = None


@dataclass
class OutreachEvent:
    id: str
    creator_id: str
    event_type: str
    channel: str | None = None
    subject: str | None = None
    body_path: str | None = None
    message_id: str | None = None
    thread_id: str | None = None
    sent_at: str | None = None
    replied_at: str | None = None
    next_followup_at: str | None = None
    status: str | None = None
    raw_metadata: dict | None = None  # stored as JSON TEXT in DB


@dataclass
class SuppressionEntry:
    id: str
    platform: str | None = None
    handle: str | None = None
    email: str | None = None
    reason: str = ""
    created_at: str = ""
