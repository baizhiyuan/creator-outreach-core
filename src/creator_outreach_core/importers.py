"""CSV importer for creator BD agent target lists.

Imports ``data/targets.csv`` files from any of the three BD agent projects
(instagram-collab-agent, tiktok-collab-agent, x-collab-agent) into the
unified ``creators`` SQLite table.

Creator ID policy
-----------------
A stable 16-hex-character ID is derived from the SHA-256 hash of
``"{platform}:{handle}"``.  Re-importing the same CSV always maps to the
same row, enabling idempotent upserts.

Deduplication
-------------
``INSERT OR IGNORE`` skips rows whose ``(platform, handle)`` already exist.
The return value reports how many rows were inserted vs. skipped.
"""
from __future__ import annotations

import csv
import datetime
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any


# Columns that map 1-to-1 from CSV field → creators column (all optional)
_CSV_TO_COL: dict[str, str] = {
    "handle": "handle",
    "profile_url": "profile_url",
    "display_name": "display_name",
    "bio": "bio",
    "category": "category",
    "followers_count": "followers_count",
    "avg_views": "avg_views",
    "engagement_rate": "engagement_rate",
    "region": "region",
    "language": "language",
    "contact_email": "contact_email",
    "website": "website",
    "link_in_bio": "link_in_bio",
    "source": "source",
    "source_url": "source_url",
    "discovered_at": "discovered_at",
    "last_enriched_at": "last_enriched_at",
    "status": "status",
    "score": "score",
    "risk_level": "risk_level",
    "risk_flags": "risk_flags",
    "notes": "notes",
    "personalization": "personalization",
}

_INT_COLS = {"followers_count", "avg_views", "score"}
_FLOAT_COLS = {"engagement_rate"}


def _stable_id(platform: str, handle: str) -> str:
    """Return a stable 16-hex-char ID for (platform, handle)."""
    digest = hashlib.sha256(f"{platform}:{handle}".encode()).hexdigest()
    return digest[:16]


def _now_iso() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _coerce(col: str, value: str) -> Any:
    """Coerce a string CSV value to the appropriate Python type."""
    if value == "" or value is None:
        return None
    if col in _INT_COLS:
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    if col in _FLOAT_COLS:
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    return value


def import_targets_csv(
    conn: sqlite3.Connection,
    csv_path: Path,
    platform: str,
) -> dict[str, int]:
    """Import a BD agent ``targets.csv`` into the ``creators`` table.

    Parameters
    ----------
    conn:
        Open SQLite connection (foreign_keys + row_factory already set by
        ``db.connect()``).
    csv_path:
        Path to a ``targets.csv`` file.
    platform:
        Platform tag, e.g. ``"instagram"``, ``"tiktok"``, ``"x"``.

    Returns
    -------
    dict with keys ``"inserted"`` and ``"skipped_dup"``.
    """
    inserted = 0
    skipped_dup = 0
    now = _now_iso()

    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            handle = (row.get("handle") or "").strip()
            if not handle:
                continue

            profile_url = (row.get("profile_url") or "").strip()

            creator_id = _stable_id(platform, handle)

            # Build column→value dict; only include columns present in the CSV
            data: dict[str, Any] = {
                "id": creator_id,
                "platform": platform,
                "handle": handle,
                "profile_url": profile_url or f"https://www.{platform}.com/{handle}/",
            }

            for csv_col, db_col in _CSV_TO_COL.items():
                if csv_col in ("handle", "profile_url"):
                    continue  # already handled above
                if csv_col in row:
                    val = _coerce(db_col, row[csv_col])
                    # risk_flags: if present as a plain string, store as JSON array
                    if db_col == "risk_flags" and val is not None:
                        # might already be JSON; otherwise wrap in list
                        raw = str(val).strip()
                        if raw.startswith("["):
                            data[db_col] = raw  # already JSON
                        else:
                            data[db_col] = json.dumps([raw]) if raw else json.dumps([])
                    else:
                        data[db_col] = val

            # Default status to 'new' if not provided or empty
            if not data.get("status"):
                data["status"] = "new"

            # Set discovered_at to now if not present in CSV
            if not data.get("discovered_at"):
                data["discovered_at"] = now

            cols = list(data.keys())
            placeholders = ", ".join("?" for _ in cols)
            col_names = ", ".join(cols)
            values = [data[c] for c in cols]

            try:
                conn.execute(
                    f"INSERT OR IGNORE INTO creators ({col_names}) VALUES ({placeholders})",
                    values,
                )
                conn.commit()
                # Check if the row was actually inserted
                cur = conn.execute(
                    "SELECT changes()"
                )
                changes = cur.fetchone()[0]
                if changes:
                    inserted += 1
                else:
                    skipped_dup += 1
            except sqlite3.Error:
                skipped_dup += 1

    return {"inserted": inserted, "skipped_dup": skipped_dup}
