"""Tests for db.py — schema creation, idempotency, and constraint enforcement."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from creator_outreach_core.db import connect, init_schema, close


class TestInitSchema(unittest.TestCase):

    def _tmp_conn(self) -> sqlite3.Connection:
        """Return a connection to a fresh in-memory (temp-file) DB."""
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        conn = connect(tmp.name)
        return conn

    def test_init_schema_creates_three_tables(self):
        conn = self._tmp_conn()
        init_schema(conn)
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row["name"] for row in cur.fetchall()}
        self.assertIn("creators", tables)
        self.assertIn("outreach_events", tables)
        self.assertIn("suppression_list", tables)
        close(conn)

    def test_init_schema_is_idempotent(self):
        conn = self._tmp_conn()
        init_schema(conn)
        # Second call must not raise
        init_schema(conn)
        close(conn)

    def test_creators_unique_platform_handle(self):
        conn = self._tmp_conn()
        init_schema(conn)
        conn.execute(
            "INSERT INTO creators (id, platform, handle, profile_url, status) "
            "VALUES ('abc1', 'instagram', 'testhandle', 'https://ig.com/t', 'new')"
        )
        conn.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO creators (id, platform, handle, profile_url, status) "
                "VALUES ('abc2', 'instagram', 'testhandle', 'https://ig.com/t2', 'new')"
            )
            conn.commit()
        close(conn)

    def test_outreach_events_fk_to_creators(self):
        conn = self._tmp_conn()
        init_schema(conn)
        # foreign_keys PRAGMA is set in connect(), but executescript() resets it
        conn.execute("PRAGMA foreign_keys = ON")
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO outreach_events (id, creator_id, event_type) "
                "VALUES ('ev1', 'nonexistent-creator-id', 'sent')"
            )
            conn.commit()
        close(conn)


if __name__ == "__main__":
    unittest.main()
