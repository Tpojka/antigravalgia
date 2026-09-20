import io
import json
import os
import shutil
import subprocess
import sys
from contextlib import redirect_stdout
from unittest import mock

from antigravalgia import config, install, paths
from antigravalgia.install import antigravity, system
from tests.support import IsolatedTestCase
from tests.test_host import read_message

PAYLOAD = json.dumps({"conversationId": "s1", "workspacePaths": ["/work/project"]}).encode()
STATUSLINE_PAYLOAD = json.dumps({"conversation_id": "s1", "agent_state": "working", "cwd": "/work/project"}).encode()


def shells(command):
    """How Antigravity runs a hook command: as a string, through a shell.

    Verified with agy 1.2.7 on macOS: the quoting, the argument and the `|| true` in the command all
    took effect, and the hook ran with the hooks file's folder as its working directory.
    """
    if sys.platform == "win32":
        return [["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", command]]
    return [[shell, "-c", command] for shell in ("/bin/sh", shutil.which("bash")) if shell]


class InstallTest(IsolatedTestCase):
    def run_installer(self, *args):
        with redirect_stdout(io.StringIO()) as out:
            install.main(list(args))
        return out.getvalue()

    def hook_commands(self):
        bundle = json.loads(antigravity.hooks_path().read_text(encoding="utf-8"))["antigravalgia"]
        commands = []
        for entries in bundle.values():
            for entry in entries:
                commands += [h["command"] for h in entry["hooks"]] if "hooks" in entry else [entry["command"]]
        return commands

    def test_exit_installs_nothing(self):
        self.assertIn("Nothing installed", self.run_installer("3"))
        self.assertFalse(os.path.exists(self.data))
        self.assertFalse(antigravity.hooks_path().exists())

    def test_install_is_self_contained_and_works(self):
        self.addCleanup(system.unregister_host)
        self.run_installer("2")

        self.assertTrue(paths.app_file().is_file())
        self.assertTrue((paths.extension_dir() / "manifest.json").is_file())
        self.assertTrue(paths.icon("back-ok").is_file())
        self.assertFalse(list(paths.extension_dir().rglob("*.svg")))
        self.assertTrue(config.load()["notifications"])
        # Two sub-commands, because the payload never says which event fired.
        self.assertEqual(len({c.split()[-3] for c in self.hook_commands()}), 2)

        # The installed app runs on its own: a hook event is recorded as session state.
        subprocess.run([sys.executable, str(paths.app_file()), "hook", "busy"], input=PAYLOAD, check=True, cwd=self.home)
        self.assertEqual((paths.sessions_dir() / "s1").read_text(), "busy")

    def test_hook_command_runs_in_the_shell_and_never_fails(self):
        self.addCleanup(system.unregister_host)
        self.run_installer("1")
        command = system.hook_command(paths.app_file())("busy")
        for argv in shells(command):
            with self.subTest(shell=argv[0]):
                (paths.sessions_dir() / "s1").unlink(missing_ok=True)
                result = subprocess.run(argv, input=PAYLOAD, cwd=self.home, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                # Antigravity reads a hook's stdout as a decision, so anything here could deny a tool call.
                self.assertEqual(result.stdout.strip(), b"")
                self.assertEqual((paths.sessions_dir() / "s1").read_text(), "busy")

        # Python exits 2 without the app, and a failing PreToolUse hook could gate every tool call.
        paths.app_file().unlink()
        for argv in shells(command):
            with self.subTest(shell=argv[0], app="missing"):
                result = subprocess.run(argv, input=PAYLOAD, cwd=self.home, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), b"")

    def test_statusline_command_prints_exactly_one_line(self):
        self.addCleanup(system.unregister_host)
        self.run_installer("1")
        command = system.statusline_command(paths.app_file())
        for argv in shells(command):
            with self.subTest(shell=argv[0]):
                result = subprocess.run(argv, input=STATUSLINE_PAYLOAD, cwd=self.home, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.decode().count("\n"), 1)
                self.assertIn(b"antigravalgia", result.stdout)

        # Its stdout is the status line, so garbage in must not become an error message on screen.
        for argv in shells(command):
            with self.subTest(shell=argv[0], input="garbage"):
                result = subprocess.run(argv, input=b"not json", cwd=self.home, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, b"\n")

    def test_menu_asks_about_sound_and_the_status_line(self):
        self.addCleanup(system.unregister_host)
        with mock.patch("builtins.input", side_effect=["2", "n", "y"]) as ask:
            out = self.run_installer()
        self.assertIn("2) Chrome extension + OS notifier", out)
        questions = " ".join(call.args[0] for call in ask.call_args_list)
        self.assertIn("Play a sound with notifications? [Y/n]", questions)
        self.assertIn('Also show "needs you" alerts?', questions)
        self.assertIn("[y/N]", questions)  # the status line is opt-in
        self.assertEqual(config.load(), {"notifications": True, "sound": False})
        self.assertEqual(antigravity.statusline_owner(), "antigravalgia")

        # Option 1 is the extension alone, so neither extra question is asked.
        with mock.patch("builtins.input", side_effect=["1"]) as ask:
            self.run_installer()
        self.assertEqual(ask.call_count, 1)

    def test_the_status_line_is_off_unless_asked_for(self):
        self.addCleanup(system.unregister_host)
        self.run_installer("2")
        self.assertIsNone(antigravity.statusline_owner())
        self.run_installer("2", "--statusline")
        self.assertEqual(antigravity.statusline_owner(), "antigravalgia")

    def test_an_existing_status_line_is_never_overwritten(self):
        self.addCleanup(system.unregister_host)
        mine = {"statusLine": {"type": "command", "command": "~/my-own-line.sh"}}
        antigravity.settings_path().parent.mkdir(parents=True, exist_ok=True)
        antigravity.settings_path().write_text(json.dumps(mine), encoding="utf-8")

        out = self.run_installer("2", "--statusline")
        self.assertIn("left it alone", out)
        self.assertIn("statusline", out)  # the command to set by hand
        self.assertEqual(json.loads(antigravity.settings_path().read_text()), mine)

        # And it isn't even offered in the menu.
        with mock.patch("builtins.input", side_effect=["2", "y"]) as ask:
            self.run_installer()
        self.assertEqual(ask.call_count, 2)

    def test_statusline_command_turns_it_on_and_off(self):
        self.addCleanup(system.unregister_host)
        self.run_installer("2")
        self.assertIn("Status line written", self.run_installer("statusline", "on"))
        self.assertEqual(antigravity.statusline_owner(), "antigravalgia")
        self.assertIn("Status line removed", self.run_installer("statusline", "off"))
        self.assertIsNone(antigravity.statusline_owner())
        with self.assertRaises(SystemExit):
            self.run_installer("statusline", "maybe")

    def test_sound_flag_without_prompting(self):
        self.addCleanup(system.unregister_host)
        self.run_installer("2", "--no-sound")
        self.assertFalse(config.load()["sound"])
        self.run_installer("2")
        self.assertTrue(config.load()["sound"])

    def test_set_changes_installed_setting(self):
        self.addCleanup(system.unregister_host)
        self.run_installer("2")
        self.assertIn("Sound off", self.run_installer("set", "sound", "off"))
        self.assertEqual(config.load(), {"notifications": True, "sound": False})
        self.run_installer("set", "notifications", "off")
        self.assertFalse(config.load()["notifications"])

    def test_set_rejects_bad_input_and_missing_install(self):
        with self.assertRaises(SystemExit):
            self.run_installer("set", "sound", "on")  # not installed yet
        self.run_installer("3")
        with self.assertRaises(SystemExit):
            self.run_installer("set", "volume", "on")

    def test_option_1_turns_notifier_off(self):
        self.addCleanup(system.unregister_host)
        self.run_installer("2")
        self.run_installer("1")
        self.assertFalse(config.load()["notifications"])

    def test_a_broken_hooks_file_stops_the_hooks_not_the_install(self):
        self.addCleanup(system.unregister_host)
        antigravity.hooks_path().parent.mkdir(parents=True, exist_ok=True)
        antigravity.hooks_path().write_text("{ not json", encoding="utf-8")
        out = self.run_installer("1")
        self.assertIn("not valid JSON", out)
        self.assertTrue(paths.app_file().is_file())  # the rest of the install still happened
        self.assertEqual(antigravity.hooks_path().read_text(), "{ not json")

    def test_uninstall_removes_everything(self):
        self.run_installer("1")
        self.run_installer("statusline", "on")
        self.run_installer("uninstall")
        self.assertFalse(os.path.exists(self.data))
        self.assertFalse(antigravity.hooks_path().exists() and "antigravalgia" in antigravity.hooks_path().read_text())
        self.assertIsNone(antigravity.statusline_owner())
        self.assertFalse(system.manifest_path().exists())

    def test_chrome_can_start_the_registered_host(self):
        self.addCleanup(system.unregister_host)
        self.run_installer("1")
        manifest = json.loads(system.manifest_path().read_text())
        self.assertEqual(manifest["name"], "com.tpojka.antigravalgia")
        self.assertEqual(manifest["allowed_origins"], ["chrome-extension://bpfhgifephcgodfaicmamfpgpcikhidd/"])

        # Chrome runs the manifest's path with the extension origin as the argument.
        proc = subprocess.Popen([manifest["path"], "chrome-extension://test/"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        try:
            self.assertEqual(read_message(proc.stdout)["state"], "ready")
            proc.stdin.close()
            self.assertEqual(proc.wait(timeout=10), 0)
        finally:
            proc.kill()
            proc.stdout.close()
