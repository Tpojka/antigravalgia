import io
import json
from unittest import mock

from antigravalgia import config, state, statusline
from tests.support import IsolatedTestCase, stdin

# The shape of the payload Antigravity pipes to a status line script, trimmed to the fields we read.
PAYLOAD = {
    "cwd": "/work/project",
    "conversation_id": "054dbd28-6757-4797-bfa3-742a0656f7c3",
    "session_id": "054dbd28-6757-4797-bfa3-742a0656f7c3",
    "model": {"id": "gemini-3.8-flash-high", "display_name": "Gemini 3.8 Flash"},
    "workspace": {"current_dir": "/work/project", "project_dir": "/work/project"},
    "agent_state": "idle",
    "tool_confirmation_pending": False,
    "terminal_width": 120,
}


class StatusLineTest(IsolatedTestCase):
    def send(self, **payload):
        """Run the status line the way the TUI does, and return the single line it wrote."""
        written = self.run_with(json.dumps({**PAYLOAD, **payload}).encode("utf-8"))
        self.assertEqual(written.count(b"\n"), 1, f"expected one line, got {written!r}")
        self.assertTrue(written.endswith(b"\n"), "the status line must end in one newline")
        self.assertNotIn(b"\r", written)  # CRLF would reach Antigravity as part of the line
        return written[:-1].decode("utf-8")

    def run_with(self, payload):
        """Return the raw bytes the status line wrote to stdout."""
        out = io.BytesIO()
        stream = mock.Mock(buffer=out)
        with mock.patch("sys.stdin", stdin(payload.decode("utf-8", "replace"))):
            with mock.patch("sys.stdout", stream):
                statusline.main()
        return out.getvalue()

    def test_working_states_are_busy(self):
        for agent_state in ("thinking", "working", "tool_use"):
            with self.subTest(agent_state=agent_state):
                self.send(agent_state=agent_state)
                self.assertEqual(state.summary()["state"], "busy")

    def test_idle_and_initializing_are_ready(self):
        for agent_state in ("idle", "initializing"):
            with self.subTest(agent_state=agent_state):
                self.send(agent_state="working")
                self.send(agent_state=agent_state)
                self.assertEqual(state.summary()["state"], "ready")

    def test_a_confirmation_dialog_outranks_the_agent_state(self):
        self.send(agent_state="tool_use", tool_confirmation_pending=True)
        self.assertEqual(state.current(PAYLOAD["conversation_id"]), state.WAITING)
        self.assertEqual(state.summary()["state"], "ready")

    def test_an_unknown_agent_state_is_ready(self):
        self.send(agent_state="something-new")
        self.assertEqual(state.summary()["state"], "ready")

    def test_the_line_is_written_as_utf8(self):
        # Windows would otherwise encode the separator with the ANSI code page.
        self.assertEqual(self.run_with(json.dumps(PAYLOAD).encode()), "antigravalgia \u00b7 ready\n".encode("utf-8"))

    def test_line_names_the_state_and_other_sessions(self):
        self.assertEqual(self.send(agent_state="working"), "antigravalgia · working")
        self.assertEqual(self.send(tool_confirmation_pending=True), "antigravalgia · needs you")
        state.set_state("another", state.BUSY)
        self.assertEqual(self.send(agent_state="idle"), "antigravalgia · ready · 1 of 2 sessions working")

    def test_garbage_input_writes_one_empty_line_and_records_nothing(self):
        self.assertEqual(self.run_with(b"not json"), b"\n")
        self.assertEqual(state.summary()["total"], 0)

    @mock.patch("antigravalgia.notify.send")
    def test_no_notifications_unless_enabled(self, send):
        self.send(tool_confirmation_pending=True)
        send.assert_not_called()

    @mock.patch("antigravalgia.notify.send")
    def test_needs_you_notifies_once_per_dialog(self, send):
        config.save({"notifications": True})
        self.send(agent_state="tool_use", tool_confirmation_pending=True)
        self.assertEqual(send.call_args.args[:2], ("Antigravity needs you · project", "Waiting for your confirmation"))
        # The TUI runs the script on every state change; the dialog is still the same one.
        self.send(agent_state="working", tool_confirmation_pending=True)
        self.assertEqual(send.call_count, 1)
        # A new dialog, after the state moved on, notifies again.
        self.send(agent_state="tool_use")
        self.send(agent_state="tool_use", tool_confirmation_pending=True)
        self.assertEqual(send.call_count, 2)

    @mock.patch("antigravalgia.notify.send")
    def test_ready_is_left_to_the_stop_hook(self, send):
        config.save({"notifications": True})
        self.send(agent_state="working")
        self.send(agent_state="idle")
        send.assert_not_called()

    @mock.patch("antigravalgia.notify.send")
    def test_title_falls_back_to_cwd_without_a_workspace(self, send):
        config.save({"notifications": True})
        self.send(workspace=None, cwd="/work/Đurđevac", tool_confirmation_pending=True)
        self.assertEqual(send.call_args.args[0], "Antigravity needs you · Đurđevac")

    @mock.patch("antigravalgia.notify.send", side_effect=OSError("no notifier"))
    def test_a_failing_notifier_still_prints_the_line(self, send):
        config.save({"notifications": True})
        self.assertEqual(self.send(tool_confirmation_pending=True), "antigravalgia \u00b7 needs you")
        self.assertEqual(state.current(PAYLOAD["conversation_id"]), state.WAITING)
