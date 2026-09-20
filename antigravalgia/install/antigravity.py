"""Writes Antigravalgia's hooks into ~/.gemini/config/hooks.json, and its status line into
~/.gemini/antigravity-cli/settings.json.

Both files belong to Antigravity, not to us: the hooks file is shared with the `/hooks` command, the
Antigravity 2.0 app and the IDE, and the settings file is written sparsely by the CLI itself. So both are
merged key by key, backed up first, and never rewritten whole. A file that can't be parsed is left
untouched, because the CLI once lost every setting to exactly that.
"""
import json
import os
import shutil
from pathlib import Path

# hooks.json is keyed by bundle name, so Antigravalgia owns one key and never touches anyone else's.
BUNDLE = "antigravalgia"
TIMEOUT_SECONDS = 5
MATCHER = ".*"

# Event -> the `hook` sub-command registered for it. The payload has no event name, so each event has
# to name its own. PreToolUse and PostToolUse take matcher groups; the rest take a flat list.
FLAT_EVENTS = {"PreInvocation": "busy", "PostInvocation": "busy", "Stop": "stop"}
TOOL_EVENTS = {"PreToolUse": "busy", "PostToolUse": "busy"}


class ConfigError(Exception):
    """Antigravity's own file is unreadable, so we leave it alone and say so."""


def gemini_home():
    return Path.home() / ".gemini"


def hooks_path():
    return gemini_home() / "config" / "hooks.json"


def settings_path():
    return gemini_home() / "antigravity-cli" / "settings.json"


def bundle(command):
    """Our hooks.json entry. `command` turns a sub-command such as "busy" into a shell command line."""
    entry = lambda event: {"type": "command", "command": command(event), "timeout": TIMEOUT_SECONDS}
    hooks = {event: [entry(sub)] for event, sub in FLAT_EVENTS.items()}
    hooks.update({event: [{"matcher": MATCHER, "hooks": [entry(sub)]}] for event, sub in TOOL_EVENTS.items()})
    return hooks


def install(command):
    _update(hooks_path(), lambda data: data.update({BUNDLE: bundle(command)}))


def uninstall():
    _update(hooks_path(), lambda data: data.pop(BUNDLE, None), skip_if_missing=True)


def statusline_owner(settings=None):
    """Who owns the status line: None if free, "antigravalgia" if ours, "other" if someone else's."""
    if settings is None:
        try:
            settings = _read(settings_path())
        except ConfigError:
            return "other"  # unreadable, so treat it as taken and keep our hands off
    command = settings.get("statusLine", {}).get("command") if isinstance(settings.get("statusLine"), dict) else None
    if not command:
        return None
    return BUNDLE if BUNDLE in command else "other"


def install_statusline(command):
    """Add our statusLine block, keeping Antigravity's own line above ours."""

    def change(data):
        data["statusLine"] = {
            "type": "command",
            "command": command,
            "enabled": True,
            "stack_with_default": True,
        }

    _update(settings_path(), change)


def uninstall_statusline():
    def change(data):
        if statusline_owner(data) == BUNDLE:
            del data["statusLine"]

    _update(settings_path(), change, skip_if_missing=True)


def _read(path):
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    try:
        data = json.loads(text) if text.strip() else {}
    except ValueError as error:
        raise ConfigError(f"{path} is not valid JSON ({error}). Left it untouched.")
    if not isinstance(data, dict):
        raise ConfigError(f"{path} does not hold a JSON object. Left it untouched.")
    return data


def _update(path, change, skip_if_missing=False):
    if skip_if_missing and not path.exists():
        return
    data = _read(path)
    before = json.dumps(data, sort_keys=True)
    change(data)
    if json.dumps(data, sort_keys=True) == before:
        return
    if path.exists():
        shutil.copy2(path, str(path) + f".{BUNDLE}.bak")
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write beside the file and swap it in, so a crash can't leave Antigravity with half a config.
    tmp = path.with_name(path.name + f".{BUNDLE}.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)
