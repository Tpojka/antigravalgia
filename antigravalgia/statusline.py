"""Antigravity CLI status line: the "needs you" signal the hooks don't provide.

The TUI runs this whenever the agent state changes, pipes the state JSON to stdin, and renders whatever
comes back on stdout. That payload carries `agent_state` and `tool_confirmation_pending`, which the hook
events cannot see, so this is where "Antigravity needs you" comes from.

It never fails and never prints an error: its stdout *is* the status line.
"""
import json
import os
import sys

from . import config, notify, paths, state

# agent_state -> recorded state. An open confirmation dialog outranks all of them.
AGENT_STATES = {
    "thinking": state.BUSY,
    "working": state.BUSY,
    "tool_use": state.BUSY,
    "idle": state.READY,
    "initializing": state.READY,
}

LABELS = {state.BUSY: "working", state.WAITING: "needs you", state.READY: "ready"}


def handle(payload):
    """Record this session's state, notify on the way into "waiting", and return the line to print."""
    session = str(payload.get("conversation_id") or payload.get("session_id") or "default")
    if payload.get("tool_confirmation_pending"):
        value = state.WAITING
    else:
        value = AGENT_STATES.get(payload.get("agent_state"), state.READY)

    previous = state.current(session)
    state.set_state(session, value)
    # This runs on every state change, so notify only on the edge into "waiting". "ready" belongs to the
    # Stop hook, which already notifies for it.
    if value == state.WAITING and previous != state.WAITING:
        try:
            settings = config.load()
            if settings["notifications"]:
                notify.send(title(payload), "Waiting for your confirmation", paths.icon("back-pain"), sound=settings["sound"])
        except Exception:
            pass  # a notifier that can't run is no reason to blank the status line
    return render(value, state.summary())


def title(payload):
    """"Antigravity needs you", with the project folder. Unlike the hooks, this payload always names one."""
    workspace = payload.get("workspace")
    current = workspace.get("current_dir") if isinstance(workspace, dict) else None
    project = os.path.basename(os.path.normpath(current or payload.get("cwd") or os.getcwd()))
    return f"Antigravity needs you · {project}" if project else "Antigravity needs you"


def render(value, summary):
    """One short line. With stack_with_default it sits under Antigravity's own line, so it adds only
    what that line can't know: how your other sessions are doing."""
    line = f"antigravalgia · {LABELS[value]}"
    if summary["total"] > 1:
        line += f" · {summary['busy']} of {summary['total']} sessions working"
    return line


def main():
    line = ""
    try:
        # Bytes, because the payload is UTF-8 and Windows would decode text stdin with the ANSI code page.
        line = handle(json.loads(sys.stdin.buffer.read()))
    except Exception:
        pass  # an error here would be rendered as the status line
    # Bytes again, for the two things print() gets wrong on Windows: it would encode the separator with
    # the ANSI code page, and turn the newline into CRLF. Antigravity renders this as the status line.
    sys.stdout.buffer.write(line.encode("utf-8") + b"\n")
    sys.stdout.buffer.flush()
