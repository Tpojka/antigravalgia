"""Chrome native-messaging host: pushes the combined session status to the extension whenever it changes."""
import json
import os
import struct
import sys
import threading
import time

from . import state

POLL_SECONDS = 0.5


def encode(message):
    """Native messaging frame: 4-byte native-endian length, then UTF-8 JSON."""
    data = json.dumps(message).encode("utf-8")
    return struct.pack("@I", len(data)) + data


def _exit_when_chrome_disconnects():
    # Chrome closes our stdin when the extension disconnects.
    while sys.stdin.buffer.read(4096):
        pass
    os._exit(0)


def main():
    if sys.platform == "win32":
        import msvcrt

        # Text mode would turn \n into \r\n inside the binary frames.
        msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

    threading.Thread(target=_exit_when_chrome_disconnects, daemon=True).start()
    last = None
    while True:
        status = state.summary()
        if status != last:
            sys.stdout.buffer.write(encode(status))
            sys.stdout.buffer.flush()
            last = status
        time.sleep(POLL_SECONDS)
