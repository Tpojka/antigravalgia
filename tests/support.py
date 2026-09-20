"""Test isolation: every test gets its own home and data directory, so no real install is touched.

Antigravity CLI has no way to relocate ~/.gemini, so the tests move HOME instead, which is also what
Path.home() follows on every platform.
"""
import io
import os
import tempfile
import unittest
from unittest import mock


def stdin(text):
    """A stand-in for sys.stdin that, like the real one, has a binary buffer."""
    return io.TextIOWrapper(io.BytesIO(text.encode("utf-8")), encoding="utf-8")


class IsolatedTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = tmp.name
        # A space and a quote, like "Application Support" on macOS, so hook commands must quote the path.
        self.data = os.path.join(self.home, "data dir's")
        env = {"HOME": self.home, "USERPROFILE": self.home, "ANTIGRAVALGIA_HOME": self.data}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
