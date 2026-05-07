# creator-outreach-core

Shared SQLite CRM data layer for the three multi-platform creator BD agent projects:
`instagram-collab-agent`, `tiktok-collab-agent`, and `x-collab-agent`.

Each platform agent maintains its own `data/targets.csv`; this library provides a
unified SQLite backend that imports those CSVs, deduplicates by `(platform, handle)`,
scores creators, manages a suppression list, and records outreach events. It implements
spec §3 P1 of the multi-platform creator BD agent upgrade plan.

Runtime dependencies: **stdlib only** (`sqlite3`, `dataclasses`, `pathlib`, `json`, `hashlib`).
Python >= 3.11 required.

## Quick start

```python
from pathlib import Path
from creator_outreach_core.db import connect, init_schema
from creator_outreach_core.importers import import_targets_csv
from creator_outreach_core.scoring import score_creator
from creator_outreach_core.suppression import add_suppression, is_suppressed
from creator_outreach_core.events import record_event, get_latest_event
from creator_outreach_core.models import OutreachEvent
import uuid

conn = connect("creator_outreach.db")
init_schema(conn)

# Import all 12 Instagram targets
result = import_targets_csv(
    conn,
    Path("../instagram-collab-agent/data/targets.csv"),
    platform="instagram",
)
print(result)  # {"inserted": 12, "skipped_dup": 0}

# Score a creator fetched from the DB
from creator_outreach_core.models import Creator
c = Creator(id="abc", platform="instagram", handle="droolingcapy",
            profile_url="https://ig.com/droolingcapy",
            contact_email="droolingcapy99@gmail.com", followers_count=265_000,
            language="en", region="US", bio="capybara collab")
print(score_creator(c))  # {"score": 95, "tier": "high", ...}

# Suppress a handle
add_suppression(conn, platform="instagram", handle="badactor", email=None, reason="opt_out")
print(is_suppressed(conn, platform="instagram", handle="badactor"))  # True

# Record an outreach event
ev = OutreachEvent(id=str(uuid.uuid4())[:16], creator_id="abc", event_type="sent",
                   channel="email", sent_at="2026-05-07T10:00:00Z")
record_event(conn, ev)
latest = get_latest_event(conn, creator_id="abc")
print(latest.event_type)  # "sent"
```

## Status flow (13 states)

```
new
 └─> enriched
      └─> ranked
           └─> drafted
                └─> approved
                     └─> sent
                          └─> followup_1_due
                               └─> followup_1_sent
                                    └─> followup_2_due
                                         └─> followup_2_sent
                                              └─> replied
                                                   └─> closed
                                                        └─> suppressed
```

## Module overview

| Module | Purpose |
|--------|---------|
| `db.py` | `connect()`, `init_schema()`, `close()` |
| `schema.sql` | SQLite DDL — 3 tables: `creators`, `outreach_events`, `suppression_list` |
| `models.py` | `Creator`, `OutreachEvent`, `SuppressionEntry` dataclasses + `CANONICAL_STATUSES` |
| `importers.py` | `import_targets_csv()` — BD agent CSV → SQLite with stable hash IDs + dedup |
| `scoring.py` | `score_creator()` — heuristic 0-100 scorer with tunable `WEIGHTS` dict |
| `suppression.py` | `add_suppression()`, `is_suppressed()`, `list_suppressions()` |
| `events.py` | `record_event()`, `list_events()`, `get_latest_event()` |

## Relation to Phase 2 Track A/B/C agents

- **Track A** (`instagram-collab-agent`): provides `data/targets.csv` with 12 real IG targets.
  Import with `import_targets_csv(conn, path, platform="instagram")`.
- **Track B** (`tiktok-collab-agent`): provides `data/targets.csv` (currently empty, schema-compatible).
  Import with `platform="tiktok"`.
- **Track C** (`x-collab-agent`): provides `data/targets.csv` (currently empty, schema-compatible).
  Import with `platform="x"`.

All three CSVs share the same 10-column schema
(`handle`, `profile_url`, `category`, `status`, `contact_email`, `website`,
`personalization`, `notes`, `last_contacted`, `next_followup`)
and can be imported via the same `import_targets_csv` call.

## Scoring dimensions (v1 heuristics)

Tune by editing `WEIGHTS` in `scoring.py` — no logic changes needed.

| Dimension | Max pts | Signal |
|-----------|---------|--------|
| contactability | 25+5 | `contact_email` (+25), `link_in_bio` (+5) |
| commercial_signal | 15 | bio contains shop/store/collab/partnership/business |
| size_fit | 15 | 10k-300k followers (+15), 300k-1M (+10), 1M+ (+5) |
| audience_fit | 30 | language=en (+10), region in US/EU (+20) |
| freshness | 10 | `last_enriched_at` within 30 days |
| risk_penalty | -10/flag | each `risk_flags` entry |

Tiers: **high** >= 75, **mid** 50-74, **low** < 50.

## Notes — v1 limitations and future migration

- **SQLite v1**: single-developer, single-process. No connection pooling.
- **Postgres migration**: replace `db.connect()` with `psycopg2.connect()`, adapt
  `schema.sql` for Postgres syntax (`TEXT` → `VARCHAR`, drop `IF NOT EXISTS` on indexes,
  use `gen_random_uuid()` if switching to UUID PKs). All other modules are SQL-dialect agnostic.
- **No ORM**: intentional — keeps runtime deps at zero and the schema explicit.
