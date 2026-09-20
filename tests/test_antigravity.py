import json

from antigravalgia.install import antigravity
from tests.support import IsolatedTestCase

COMMAND = lambda sub: f"python3 '/data/antigravalgia.pyz' hook {sub} || true"
STATUSLINE = "python3 '/data/antigravalgia.pyz' statusline"

# Another bundle in the same file, and settings the CLI wrote itself. Neither may be disturbed.
FOREIGN_BUNDLE = {"my-linter-hook": {"PostToolUse": [{"matcher": "run_command", "hooks": [{"command": "./lint.sh"}]}]}}
FOREIGN_SETTINGS = {"permissions": {"allow": ["command(agy)"]}, "trustedWorkspaces": ["/home/u"]}


class HooksFileTest(IsolatedTestCase):
    def write(self, data):
        path = antigravity.hooks_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")

    def read(self):
        return json.loads(antigravity.hooks_path().read_text(encoding="utf-8"))

    def test_location_is_the_shared_hooks_file(self):
        self.assertEqual(antigravity.hooks_path(), antigravity.gemini_home() / "config" / "hooks.json")

    def test_registers_every_event_under_one_bundle(self):
        antigravity.install(COMMAND)
        bundle = self.read()["antigravalgia"]
        self.assertEqual(set(bundle), {"PreInvocation", "PostInvocation", "Stop", "PreToolUse", "PostToolUse"})
        # PreToolUse and PostToolUse take matcher groups; the rest take a flat list of handlers.
        for event in ("PreToolUse", "PostToolUse"):
            (group,) = bundle[event]
            self.assertEqual(group["matcher"], ".*")
            (handler,) = group["hooks"]
            self.assertEqual(handler, {"type": "command", "command": COMMAND("busy"), "timeout": 5})
        for event in ("PreInvocation", "PostInvocation"):
            self.assertEqual(bundle[event], [{"type": "command", "command": COMMAND("busy"), "timeout": 5}])
        # The payload carries no event name, so Stop has to be told which event it is.
        self.assertEqual(bundle["Stop"], [{"type": "command", "command": COMMAND("stop"), "timeout": 5}])

    def test_keeps_other_bundles_and_backs_the_file_up(self):
        self.write(FOREIGN_BUNDLE)
        antigravity.install(COMMAND)
        self.assertEqual(self.read()["my-linter-hook"], FOREIGN_BUNDLE["my-linter-hook"])
        backup = antigravity.hooks_path().with_name("hooks.json.antigravalgia.bak")
        self.assertEqual(json.loads(backup.read_text()), FOREIGN_BUNDLE)

    def test_reinstall_replaces_only_our_bundle(self):
        antigravity.install(lambda sub: "old")
        antigravity.install(COMMAND)
        self.assertEqual(self.read()["antigravalgia"]["Stop"][0]["command"], COMMAND("stop"))

    def test_uninstall_removes_only_our_bundle(self):
        self.write(FOREIGN_BUNDLE)
        antigravity.install(COMMAND)
        antigravity.uninstall()
        antigravity.uninstall()  # twice is harmless
        self.assertEqual(self.read(), FOREIGN_BUNDLE)

    def test_uninstall_without_the_file_does_nothing(self):
        antigravity.uninstall()
        self.assertFalse(antigravity.hooks_path().exists())

    def test_an_unreadable_file_is_left_untouched(self):
        # The CLI once overwrote a settings file it couldn't parse and lost every setting. Don't repeat it.
        self.write("nonsense")
        antigravity.hooks_path().write_text("{ not json", encoding="utf-8")
        with self.assertRaises(antigravity.ConfigError):
            antigravity.install(COMMAND)
        self.assertEqual(antigravity.hooks_path().read_text(), "{ not json")


class StatusLineSettingsTest(IsolatedTestCase):
    def write(self, data):
        path = antigravity.settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")

    def read(self):
        return json.loads(antigravity.settings_path().read_text(encoding="utf-8"))

    def test_location_is_the_cli_settings_file(self):
        self.assertEqual(antigravity.settings_path(), antigravity.gemini_home() / "antigravity-cli" / "settings.json")

    def test_owner_is_free_then_ours(self):
        self.assertIsNone(antigravity.statusline_owner())
        antigravity.install_statusline(STATUSLINE)
        self.assertEqual(antigravity.statusline_owner(), "antigravalgia")

    def test_someone_elses_status_line_is_recognised(self):
        self.write({"statusLine": {"type": "command", "command": "~/my-own-line.sh"}})
        self.assertEqual(antigravity.statusline_owner(), "other")

    def test_an_unreadable_settings_file_counts_as_taken(self):
        antigravity.settings_path().parent.mkdir(parents=True, exist_ok=True)
        antigravity.settings_path().write_text("{ not json", encoding="utf-8")
        self.assertEqual(antigravity.statusline_owner(), "other")

    def test_keeps_the_settings_the_cli_wrote(self):
        self.write(FOREIGN_SETTINGS)
        antigravity.install_statusline(STATUSLINE)
        settings = self.read()
        self.assertEqual(settings["permissions"], FOREIGN_SETTINGS["permissions"])
        self.assertEqual(settings["trustedWorkspaces"], FOREIGN_SETTINGS["trustedWorkspaces"])
        self.assertEqual(
            settings["statusLine"],
            {"type": "command", "command": STATUSLINE, "enabled": True, "stack_with_default": True},
        )

    def test_uninstall_removes_only_our_status_line(self):
        self.write(FOREIGN_SETTINGS)
        antigravity.install_statusline(STATUSLINE)
        antigravity.uninstall_statusline()
        self.assertEqual(self.read(), FOREIGN_SETTINGS)

    def test_uninstall_leaves_someone_elses_status_line(self):
        mine = {"statusLine": {"type": "command", "command": "~/my-own-line.sh"}}
        self.write(mine)
        antigravity.uninstall_statusline()
        self.assertEqual(self.read(), mine)
