"""Tests for models.py — CANONICAL_STATUSES and dataclass instantiation."""
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from creator_outreach_core.models import (
    CANONICAL_STATUSES,
    Creator,
    OutreachEvent,
    SuppressionEntry,
)

_EXPECTED_STATUSES = (
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


class TestCanonicalStatuses(unittest.TestCase):

    def test_contains_all_13_expected_values(self):
        for status in _EXPECTED_STATUSES:
            self.assertIn(status, CANONICAL_STATUSES, f"Missing status: {status}")

    def test_length_is_13(self):
        self.assertEqual(len(CANONICAL_STATUSES), 13)

    def test_ordering_matches_spec(self):
        self.assertEqual(tuple(CANONICAL_STATUSES), _EXPECTED_STATUSES)


class TestCreatorDataclass(unittest.TestCase):

    def test_required_fields(self):
        c = Creator(id="x", platform="instagram", handle="foo", profile_url="https://ig.com/foo")
        self.assertEqual(c.platform, "instagram")
        self.assertEqual(c.status, "new")
        self.assertEqual(c.risk_flags, [])

    def test_optional_fields_default_none(self):
        c = Creator(id="x", platform="tiktok", handle="bar", profile_url="https://tt.com/bar")
        self.assertIsNone(c.contact_email)
        self.assertIsNone(c.followers_count)
        self.assertIsNone(c.score)


class TestOutreachEventDataclass(unittest.TestCase):

    def test_required_fields(self):
        ev = OutreachEvent(id="ev1", creator_id="c1", event_type="sent")
        self.assertEqual(ev.event_type, "sent")
        self.assertIsNone(ev.raw_metadata)


class TestSuppressionEntryDataclass(unittest.TestCase):

    def test_defaults(self):
        s = SuppressionEntry(id="s1")
        self.assertEqual(s.reason, "")
        self.assertEqual(s.created_at, "")
        self.assertIsNone(s.email)


if __name__ == "__main__":
    unittest.main()
