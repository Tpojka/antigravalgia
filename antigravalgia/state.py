"""Per-session state: the hook and the status line write one file per session, the host sums them up."""
import os
import time

from . import paths

BUSY = "busy"
READY = "ready"
WAITING = "waiting"  # a tool confirmation dialog is open, so Antigravity is blocked on you

# Antigravity has no session end event and no interrupt event, so a session busy with no activity for
# this long counts as ready.
BUSY_STALE_SECONDS = int(os.environ.get("ANTIGRAVALGIA_BUSY_STALE_SECONDS", 15 * 60))
# Sessions that ended without a trace (the CLI never signals an end) are ignored after this long.
SESSION_STALE_SECONDS = 24 * 60 * 60


def _path(session_id):
    safe = "".join(c for c in session_id if c.isalnum() or c in "-_") or "default"
    return paths.sessions_dir() / safe


def set_state(session_id, value):
    path = _path(session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(value, encoding="utf-8")
    os.replace(tmp, path)  # atomic, so the host never reads a half-written file


def current(session_id):
    """The session's recorded state, or None. Lets a writer notify only when the state actually changes."""
    try:
        return _path(session_id).read_text(encoding="utf-8").strip()
    except OSError:
        return None


def clear(session_id):
    try:
        _path(session_id).unlink()
    except FileNotFoundError:
        pass


def summary(now=None):
    """Return {"state": "busy"|"ready", "busy": n, "total": n} across all live sessions.

    `waiting` counts as ready: Antigravity is blocked on you, so the back relaxes and you can go back to it.
    """
    now = time.time() if now is None else now
    busy = total = 0
    try:
        entries = list(paths.sessions_dir().iterdir())
    except FileNotFoundError:
        entries = []
    for path in entries:
        if path.name.endswith(".tmp"):
            continue
        try:
            age = now - path.stat().st_mtime
            value = path.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if age > SESSION_STALE_SECONDS:
            continue
        total += 1
        if value == BUSY and age <= BUSY_STALE_SECONDS:
            busy += 1
    return {"state": BUSY if busy else READY, "busy": busy, "total": total}
