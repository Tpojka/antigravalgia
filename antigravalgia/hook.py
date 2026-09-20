"""Antigravity CLI hook: records session state and notifies when a turn ends.

Antigravity's payload carries no event name, so the event comes from the command line: the installer
registers `hook busy` for PreInvocation, PostInvocation, PreToolUse and PostToolUse, and `hook stop`
for Stop.

It prints nothing and always exits 0. Antigravity parses a hook's stdout as a decision, and a
PreToolUse hook that returns one can deny or auto-approve every tool call.
"""
import json
import os
import sys

from . import config, notify, paths, state

BUSY = "busy"
STOP = "stop"
EVENTS = (BUSY, STOP)


def handle(event, payload):
    session = str(payload.get("conversationId") or "default")
    if event == BUSY:
        state.set_state(session, state.BUSY)
        return
    # Stop fires whenever the execution loop terminates, including intermediate stops that carry on.
    # Only a fully idle agent means the turn is really over.
    if not payload.get("fullyIdle"):
        return
    state.set_state(session, state.READY)
    settings = config.load()
    if settings["notifications"]:
        notify.send(title(payload), "Task finished", paths.icon("back-ok"), sound=settings["sound"])


def title(payload):
    """"Antigravity is ready", with the project folder when the payload names one.

    The hook's own working directory is the hooks file's folder, not the project, so it is no help.
    `workspacePaths` is empty in headless runs, and then the title carries no project.
    """
    workspaces = payload.get("workspacePaths")
    first = workspaces[0] if isinstance(workspaces, list) and workspaces else None
    if not first:
        return "Antigravity is ready"
    return f"Antigravity is ready · {os.path.basename(os.path.normpath(first))}"


def main(argv=None):
    try:
        argv = sys.argv[2:] if argv is None else argv
        event = argv[0] if argv else ""
        if event in EVENTS:
            # Bytes, because the payload is UTF-8 and Windows would decode text stdin with the ANSI code page.
            handle(event, json.loads(sys.stdin.buffer.read()))
    except Exception:
        pass  # a failing hook must never block Antigravity
