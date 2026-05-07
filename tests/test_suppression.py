"""Tests for suppression.py."""
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from creator_outreach_core.db import connect, init_schema, close
from creator_outreach_core.suppression import add_suppression, is_suppressed, list_suppressions


def _tmp_conn():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    conn = connect(tmp.name)
    init_schema(conn)
    return conn


class TestSuppression(unittest.TestCase):

    def test_suppress_by_handle(self):
        conn = _tmp_conn()
        add_suppression(conn, platform="instagram", handle="badactor", email=None, reason="opt_out")
        self.assertTrue(is_suppressed(conn, platform="instagram", handle="badactor"))
        close(conn)

    def test_suppress_by_email(self):
        conn = _tmp_conn()
        add_suppression(conn, platform=None, handle=None, email="no@reply.com", reason="bounced")
        self.assertTrue(is_suppressed(conn, email="no@reply.com"))
        close(conn)

    def test_not_suppressed_different_handle(self):
        conn = _tmp_conn()
        add_suppression(conn, platform="instagram", handle="badactor", email=None, reason="opt_out")
        self.assertFalse(is_suppressed(conn, platform="instagram", handle="goodactor"))
        close(conn)

    def test_cross_platform_handle_uniqueness(self):
        """Same handle on different platforms are independent suppressions."""
        conn = _tmp_conn()
        add_suppression(conn, platform="instagram", handle="shared", email=None, reason="opt_out")
        # tiktok:shared should NOT be suppressed
        self.assertFalse(is_suppressed(conn, platform="tiktok", handle="shared"))
        # instagram:shared SHOULD be suppressed
        self.assertTrue(is_suppressed(conn, platform="instagram", handle="shared"))
        close(conn)

    def test_list_suppressions(self):
        conn = _tmp_conn()
        add_suppression(conn, platform="instagram", handle="a1", email=None, reason="r1")
        add_suppression(conn, platform=None, handle=None, email="x@x.com", reason="r2")
        entries = list_suppressions(conn)
        self.assertEqual(len(entries), 2)
        handles = [e.handle for e in entries]
        self.assertIn("a1", handles)
        close(conn)

    def test_idempotent_add(self):
        """Adding same suppression twice doesn't raise and doesn't duplicate."""
        conn = _tmp_conn()
        id1 = add_suppression(conn, platform="x", handle="dup", email=None, reason="r")
        id2 = add_suppression(conn, platform="x", handle="dup", email=None, reason="r")
        self.assertEqual(id1, id2)
        entries = list_suppressions(conn)
        self.assertEqual(len(entries), 1)
        close(conn)


if __name__ == "__main__":
    unittest.main()
