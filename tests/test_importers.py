"""Tests for importers.py — CSV import, dedup, and stable creator_id."""
import csv
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from creator_outreach_core.db import connect, init_schema, close
from creator_outreach_core.importers import import_targets_csv, _stable_id

# Real Instagram targets CSV used as import fixture
# tests/ is at project root/tests/, so parents[1] is the repo root,
# and the IG agent lives two levels up at /Users/expansioai/project/instagram-collab-agent
IG_CSV = Path("/Users/expansioai/project/instagram-collab-agent/data/targets.csv")


def _tmp_conn():
    """Return a fresh in-temp-file SQLite connection."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    conn = connect(tmp.name)
    init_schema(conn)
    return conn


class TestImportInstagramCSV(unittest.TestCase):

    def test_import_instagram_csv(self):
        conn = _tmp_conn()
        result = import_targets_csv(conn, IG_CSV, platform="instagram")
        self.assertEqual(result["inserted"], 12)
        self.assertEqual(result["skipped_dup"], 0)
        cur = conn.execute("SELECT COUNT(*) FROM creators WHERE platform='instagram'")
        self.assertEqual(cur.fetchone()[0], 12)
        close(conn)

    def test_import_dedup(self):
        conn = _tmp_conn()
        import_targets_csv(conn, IG_CSV, platform="instagram")
        result2 = import_targets_csv(conn, IG_CSV, platform="instagram")
        self.assertEqual(result2["inserted"], 0)
        self.assertEqual(result2["skipped_dup"], 12)
        close(conn)

    def test_import_partial_csv(self):
        """A minimal CSV with only handle + profile_url imports cleanly."""
        tmp_csv = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline=""
        )
        writer = csv.DictWriter(tmp_csv, fieldnames=["handle", "profile_url"])
        writer.writeheader()
        writer.writerow({"handle": "testcreator", "profile_url": "https://ig.com/testcreator"})
        tmp_csv.close()

        conn = _tmp_conn()
        result = import_targets_csv(conn, Path(tmp_csv.name), platform="tiktok")
        self.assertEqual(result["inserted"], 1)

        cur = conn.execute("SELECT * FROM creators WHERE handle='testcreator'")
        row = cur.fetchone()
        self.assertIsNotNone(row)
        self.assertIsNone(row["contact_email"])
        self.assertIsNone(row["category"])
        self.assertEqual(row["status"], "new")
        close(conn)

    def test_creator_id_stable_across_imports(self):
        """Same (platform, handle) always produces the same creator_id."""
        conn = _tmp_conn()
        import_targets_csv(conn, IG_CSV, platform="instagram")

        # Check a known handle
        expected_id = _stable_id("instagram", "droolingcapy")
        cur = conn.execute(
            "SELECT id FROM creators WHERE platform='instagram' AND handle='droolingcapy'"
        )
        row = cur.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["id"], expected_id)
        self.assertEqual(len(row["id"]), 16)
        close(conn)


if __name__ == "__main__":
    unittest.main()
