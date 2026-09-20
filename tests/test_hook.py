import json
from unittest import mock

from antigravalgia import config, hook, state
from tests.support import IsolatedTestCase, stdin

# A real PreInvocation payload, captured from agy 1.2.7. Note what isn't here: no event name, no cwd,
# no session_id — none of the fields the sibling projects read.
PRE_INVOCATION = {
    "artifactDirectoryPath": "/home/u/.gemini/antigravity-cli/brain/054dbd28",
    "conversationId": "054dbd28-6757-4797-bfa3-742a0656f7c3",
    "initialNumSteps": 3,
    "invocationNum": 1,
    "modelName": "gemini-3.8-flash-high",
    "transcriptPath": "/home/u/.gemini/antigravity-cli/brain/054dbd28/transcript_full.jsonl",
    "workspacePaths": [],
}


class HookTest(IsolatedTestCase):
    def send(self, event, payload):
        with mock.patch("sys.stdin", stdin(json.dumps(payload))):
            hook.main([event])

    def busy(self, **payload):
        self.send("busy", {**PRE_INVOCATION, **payload})

    def stop(self, **payload):
        self.send("stop", {**PRE_INVOCATION, "executionNum": 1, "terminationReason": "done", **payload})

    def test_busy_events_make_the_session_busy(self):
        self.busy()
        self.assertEqual(state.summary(), {"state": "busy", "busy": 1, "total": 1})

    def test_stop_only_ends_the_turn_when_fully_idle(self):
        self.busy()
        self.stop(fullyIdle=False)  # an intermediate stop: the agent carries on
        self.assertEqual(state.summary()["state"], "busy")
        self.stop(fullyIdle=True)
        self.assertEqual(state.summary(), {"state": "ready", "busy": 0, "total": 1})

    def test_sessions_are_keyed_by_conversation_id(self):
        self.busy(conversationId="one")
        self.busy(conversationId="two")
        self.stop(conversationId="one", fullyIdle=True)
        self.assertEqual(state.summary(), {"state": "busy", "busy": 1, "total": 2})

    def test_payload_without_conversation_id_uses_default_session(self):
        self.send("busy", {})
        self.assertEqual(state.summary(), {"state": "busy", "busy": 1, "total": 1})

    def test_unknown_event_and_bad_input_are_ignored(self):
        self.send("SomethingNew", PRE_INVOCATION)
        with mock.patch("sys.stdin", stdin(json.dumps(PRE_INVOCATION))):
            hook.main([])
        with mock.patch("sys.stdin", stdin("not json")):
            hook.main(["busy"])
        self.assertEqual(state.summary()["total"], 0)

    @mock.patch("antigravalgia.notify.send")
    def test_no_notifications_unless_enabled(self, send):
        self.stop(fullyIdle=True)
        send.assert_not_called()

    @mock.patch("antigravalgia.notify.send")
    def test_only_the_end_of_a_turn_notifies(self, send):
        config.save({"notifications": True})
        self.busy()
        self.stop(fullyIdle=False)
        send.assert_not_called()
        self.stop(fullyIdle=True)
        self.assertEqual(send.call_args.args[:2], ("Antigravity is ready", "Task finished"))
        self.assertTrue(send.call_args.kwargs["sound"])

    @mock.patch("antigravalgia.notify.send")
    def test_the_title_names_the_workspace_when_there_is_one(self, send):
        config.save({"notifications": True})
        self.stop(fullyIdle=True, workspacePaths=["/work/project", "/work/other"])
        self.assertEqual(send.call_args.args[0], "Antigravity is ready · project")

    @mock.patch("antigravalgia.notify.send")
    def test_headless_runs_have_no_workspace_to_name(self, send):
        # Verified with agy 1.2.7: workspacePaths is [] in `agy -p` runs, even inside a project.
        config.save({"notifications": True})
        self.stop(fullyIdle=True, workspacePaths=[])
        self.assertEqual(send.call_args.args[0], "Antigravity is ready")

    @mock.patch("antigravalgia.notify.send")
    def test_non_ascii_payload_is_read_as_utf8(self, send):
        config.save({"notifications": True})
        self.stop(fullyIdle=True, workspacePaths=["/work/Đurđevac"])
        self.assertEqual(send.call_args.args[0], "Antigravity is ready · Đurđevac")

    @mock.patch("antigravalgia.notify.send")
    def test_sound_setting_is_passed_to_notifier(self, send):
        config.save({"notifications": True, "sound": False})
        self.stop(fullyIdle=True)
        self.assertFalse(send.call_args.kwargs["sound"])

    @mock.patch("antigravalgia.notify.send", side_effect=OSError("no notifier"))
    def test_notifier_failure_does_not_raise(self, send):
        config.save({"notifications": True})
        self.stop(fullyIdle=True)
        self.assertEqual(state.summary()["state"], "ready")
