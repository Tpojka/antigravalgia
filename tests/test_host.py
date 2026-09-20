import json
import os
import struct
import subprocess
import sys

from antigravalgia import host, state
from tests.support import IsolatedTestCase

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_message(stream):
    (length,) = struct.unpack("@I", stream.read(4))
    return json.loads(stream.read(length))


class HostTest(IsolatedTestCase):
    def test_encode_frames_with_native_length_prefix(self):
        frame = host.encode({"state": "ready"})
        (length,) = struct.unpack("@I", frame[:4])
        self.assertEqual(json.loads(frame[4:]), {"state": "ready"})
        self.assertEqual(length, len(frame) - 4)

    def test_pushes_status_on_change_and_exits_when_stdin_closes(self):
        proc = subprocess.Popen(
            [sys.executable, "-m", "antigravalgia", "host"],
            cwd=REPO,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        try:
            self.assertEqual(read_message(proc.stdout), {"state": "ready", "busy": 0, "total": 0})
            state.set_state("s1", state.BUSY)
            self.assertEqual(read_message(proc.stdout), {"state": "busy", "busy": 1, "total": 1})
            proc.stdin.close()
            self.assertEqual(proc.wait(timeout=10), 0)
        finally:
            proc.kill()
            proc.stdout.close()
