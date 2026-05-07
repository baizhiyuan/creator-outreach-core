"""Tests for scoring.py."""
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from creator_outreach_core.models import Creator
from creator_outreach_core.scoring import score_creator


def _make_creator(**kwargs) -> Creator:
    defaults = dict(
        id="test",
        platform="instagram",
        handle="testhandle",
        profile_url="https://ig.com/testhandle",
    )
    defaults.update(kwargs)
    return Creator(**defaults)


class TestScoringHighTier(unittest.TestCase):

    def test_high_tier_creator(self):
        """10k followers + email + en + US + collab in bio -> high tier (>= 75)."""
        c = _make_creator(
            contact_email="creator@example.com",
            followers_count=50_000,
            language="en",
            region="US",
            bio="Hey! I do collab and shop open",
        )
        result = score_creator(c)
        self.assertGreaterEqual(result["score"], 75)
        self.assertEqual(result["tier"], "high")
        self.assertIn("public_email", result["reasons"])
        self.assertIn("strong_size_fit", result["reasons"])

    def test_low_tier_creator(self):
        """No email, 1M followers, no bio signal -> <= 50."""
        c = _make_creator(
            contact_email=None,
            followers_count=1_500_000,
            language=None,
            region=None,
            bio="just vibes",
        )
        result = score_creator(c)
        self.assertLessEqual(result["score"], 50)
        self.assertIn(result["tier"], ("mid", "low"))

    def test_risk_flags_subtract_points(self):
        """Two risk flags subtract 20 points total."""
        c_no_risk = _make_creator(
            contact_email="x@x.com",
            followers_count=50_000,
            language="en",
            region="US",
            bio="collab",
        )
        c_with_risk = _make_creator(
            contact_email="x@x.com",
            followers_count=50_000,
            language="en",
            region="US",
            bio="collab",
            risk_flags=["avoid_crypto_or_coin_framing", "official_or_licensing_route"],
        )
        base = score_creator(c_no_risk)["score"]
        penalized = score_creator(c_with_risk)["score"]
        self.assertEqual(base - penalized, 20)
        self.assertIn("avoid_crypto_or_coin_framing", score_creator(c_with_risk)["risks"])
        self.assertIn("official_or_licensing_route", score_creator(c_with_risk)["risks"])

    def test_score_clamped_to_zero(self):
        """Score never goes below 0 even with many risk flags."""
        c = _make_creator(
            risk_flags=["f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11"],
        )
        result = score_creator(c)
        self.assertGreaterEqual(result["score"], 0)

    def test_no_followers_no_size_bonus(self):
        c = _make_creator(followers_count=None)
        result = score_creator(c)
        self.assertNotIn("strong_size_fit", result["reasons"])
        self.assertNotIn("mid_size_fit", result["reasons"])

    def test_small_followers_no_size_bonus(self):
        c = _make_creator(followers_count=3000)
        result = score_creator(c)
        self.assertNotIn("strong_size_fit", result["reasons"])


if __name__ == "__main__":
    unittest.main()
