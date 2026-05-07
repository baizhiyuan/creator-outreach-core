# creator-outreach-core

Shared SQLite CRM data layer for the three multi-platform creator BD agent projects:
`instagram-collab-agent`, `tiktok-collab-agent`, and `x-collab-agent`.

Each platform agent maintains its own `data/targets.csv`; this library provides a
unified SQLite backend that imports those CSVs, deduplicates by `(platform, handle)`,
scores creators, manages a suppression list, and records outreach events. It implements
spec §3 P1 of the multi-platform creator BD agent upgrade plan.

Runtime dependencies: stdlib only (`sqlite3`, `dataclasses`, `pathlib`, `json`, `hashlib`).
Future migration path to Postgres is straightforward — only `db.py` and `schema.sql` need changing.

## Quick start

```python
from pathlib import Path
from creator_outreach_core.db import connect, init_schema
from creator_outreach_core.importers import import_targets_csv

conn = connect("creator_outreach.db")
init_schema(conn)
result = import_targets_csv(conn, Path("instagram-collab-agent/data/targets.csv"), platform="instagram")
print(result)  # {"inserted": 12, "skipped_dup": 0}
```

## Status flow (13 states)

```
new -> enriched -> ranked -> drafted -> approved -> sent
-> followup_1_due -> followup_1_sent
-> followup_2_due -> followup_2_sent
-> replied -> closed -> suppressed
```

## Relation to Phase 2 Track A/B/C agents

- **Track A** (`instagram-collab-agent`): provides `data/targets.csv` with 12 real IG targets
- **Track B** (`tiktok-collab-agent`): provides `data/targets.csv` (empty, schema-compatible)
- **Track C** (`x-collab-agent`): provides `data/targets.csv` (empty, schema-compatible)

All three CSVs share the same column schema and can be imported via `import_targets_csv`.

## Notes

This is a single-developer SQLite v1. For multi-user or production use, migrate to
Postgres by replacing `db.py`'s `connect()` with a `psycopg2` connection and adapting
`schema.sql` for Postgres syntax (remove `IF NOT EXISTS` on indexes, use `SERIAL` for
auto-increment if needed). The rest of the codebase is SQL-dialect agnostic.
