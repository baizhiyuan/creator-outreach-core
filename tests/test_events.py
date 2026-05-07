"""Tests for events.py."""
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from creator_outreach_core.db import connect, init_schema, close
from creator_outreach_core.models import OutreachEvent
from creator_outreach_core.events import record_event, list_events, get_latest_event


def _tmp_conn():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    conn = connect(tmp.name)
    init_schema(conn)
    # Insert a creator so FK constraint is satisfied
    conn.execute(
        "INSERT INTO creators (id, platform, handle, profile_url, status) "
        "VALUES ('c1', 'instagram', 'testhandle', 'https://ig.com/t', 'new')"
    )
    conn.commit()
    return conn


class TestRecordAndRetrieve(unittest.TestCase):

    def test_record_and_list_roundtrip(self):
        conn = _tmp_conn()
        ev = OutreachEvent(
            id="ev001",
            creator_id="c1",
            event_type="sent",
            channel="email",
            sent_at="2026-05-07T10:00:00Z",
        )
        record_event(conn, ev)
        events = list_events(conn, creator_id="c1")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].id, "ev001")
        self.assertEqual(events[0].event_type, "sent")
        close(conn)

    def test_raw_metadata_json_roundtrip(self):
        conn = _tmp_conn()
        meta = {"thread_id": "thread123", "labels": ["inbox", "bd"]}
        ev = OutreachEvent(
            id="ev002",
            creator_id="c1",
            event_type="replied",
            raw_metadata=meta,
            sent_at="2026-05-07T11:00:00Z",
        )
        record_event(conn, ev)
        retrieved = list_events(conn, creator_id="c1")[0]
        self.assertEqual(retrieved.raw_metadata, meta)
        close(conn)

    def test_latest_event_filter_by_type(self):
        conn = _tmp_conn()
        ev1 = OutreachEvent(id="ev003", creator_id="c1", event_type="sent",
                            sent_at="2026-05-01T00:00:00Z")
        ev2 = OutreachEvent(id="ev004", creator_id="c1", event_type="followup_1_sent",
                            sent_at="2026-05-06T00:00:00Z")
        record_event(conn, ev1)
        record_event(conn, ev2)

        latest_sent = get_latest_event(conn, creator_id="c1", event_type="sent")
        self.assertIsNotNone(latest_sent)
        self.assertEqual(latest_sent.id, "ev003")

        latest_followup = get_latest_event(conn, creator_id="c1", event_type="followup_1_sent")
        self.assertIsNotNone(latest_followup)
        self.assertEqual(latest_followup.id, "ev004")
        close(conn)

    def test_get_latest_event_none_when_no_events(self):
        conn = _tmp_conn()
        result = get_latest_event(conn, creator_id="c1")
        self.assertIsNone(result)
        close(conn)

    def test_list_events_limit(self):
        conn = _tmp_conn()
        for i in range(5):
            record_event(conn, OutreachEvent(
                id=f"ev{i:03d}", creator_id="c1", event_type="sent",
                sent_at=f"2026-05-0{i+1}T00:00:00Z",
            ))
        events = list_events(conn, creator_id="c1", limit=3)
        self.assertEqual(len(events), 3)
        close(conn)


if __name__ == "__main__":
    unittest.main()
