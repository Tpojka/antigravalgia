"""User choices made at install time, read by the hook and the status line on every event."""
import json

from . import paths

DEFAULTS = {"notifications": False, "sound": True}


def load():
    try:
        return {**DEFAULTS, **json.loads(paths.config_file().read_text(encoding="utf-8"))}
    except (OSError, ValueError):
        return dict(DEFAULTS)


def save(config):
    path = paths.config_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
