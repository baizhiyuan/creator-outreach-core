"""End-to-end integration smoke test.

Chain: import IG CSV -> score all -> suppress 1 handle -> record sent event
       -> query latest event -> assert the full chain works.
"""
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from creator_outreach_core.db import connect, init_schema, close
from creator_outreach_core.importers import import_targets_csv, _stable_id
from creator_outreach_core.models import Creator, OutreachEvent
from creator_outreach_core.scoring import score_creator
from creator_outreach_core.suppression import add_suppression, is_suppressed
from creator_outreach_core.events import record_event, get_latest_event

IG_CSV = Path("/Users/expansioai/project/instagram-collab-agent/data/targets.csv")


def _tmp_conn():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    conn = connect(tmp.name)
    init_schema(conn)
    return conn


class TestIntegrationSmoke(unittest.TestCase):

    def test_full_chain(self):
        conn = _tmp_conn()

        # 1. Import IG CSV
        result = import_targets_csv(conn, IG_CSV, platform="instagram")
        self.assertEqual(result["inserted"], 12)
        self.assertEqual(result["skipped_dup"], 0)

        # 2. Fetch all creators and score them
        cur = conn.execute("SELECT * FROM creators WHERE platform='instagram'")
        rows = cur.fetchall()
        self.assertEqual(len(rows), 12)

        scores = []
        for row in rows:
            c = Creator(
                id=row["id"],
                platform=row["platform"],
                handle=row["handle"],
                profile_url=row["profile_url"],
                contact_email=row["contact_email"],
                followers_count=row["followers_count"],
                language=row["language"],
                region=row["region"],
                bio=row["bio"],
                link_in_bio=row["link_in_bio"],
                last_enriched_at=row["last_enriched_at"],
                risk_flags=[],  # risk_flags stored as JSON; skip parsing for smoke
            )
            scored = score_creator(c)
            scores.append(scored)

        # All 12 should produce a valid scored dict
        self.assertEqual(len(scores), 12)
        for s in scores:
            self.assertIn("score", s)
            self.assertIn("tier", s)
            self.assertIn(s["tier"], ("high", "mid", "low"))

        high_count = sum(1 for s in scores if s["tier"] == "high")
        print(f"\n[integration] imported 12, scored 12, top tier=high count={high_count}")

        # 3. Suppress one handle (droolingcapy — the one with a real email)
        add_suppression(
            conn,
            platform="instagram",
            handle="droolingcapy",
            email=None,
            reason="test_suppression",
        )
        self.assertTrue(is_suppressed(conn, platform="instagram", handle="droolingcapy"))
        # Other handles should not be suppressed
        self.assertFalse(is_suppressed(conn, platform="instagram", handle="miuustudio"))

        # 4. Record a sent event for another creator (lycheegelly.art)
        creator_id = _stable_id("instagram", "lycheegelly.art")
        ev = OutreachEvent(
            id="smoke_ev001",
            creator_id=creator_id,
            event_type="sent",
            channel="email",
            sent_at="2026-05-07T10:00:00Z",
            raw_metadata={"subject": "Collab inquiry", "thread": "t001"},
        )
        record_event(conn, ev)

        # 5. Query latest event
        latest = get_latest_event(conn, creator_id=creator_id)
        self.assertIsNotNone(latest)
        self.assertEqual(latest.event_type, "sent")
        self.assertEqual(latest.raw_metadata["thread"], "t001")

        print(f"[integration] suppressed droolingcapy, recorded sent event for "
              f"lycheegelly.art, latest event={latest.event_type}")

        close(conn)


if __name__ == "__main__":
    unittest.main()
