"""OS-specific install steps: how hooks start Python, and how Chrome finds the native host."""
import json
import os
import shlex
import sys
from pathlib import Path

from .. import EXTENSION_ID, HOST_NAME, paths

LABELS = {"darwin": "macOS", "linux": "Ubuntu/Linux", "win32": "Windows"}


def label():
    return LABELS.get(sys.platform, sys.platform)


def hook_command(app):
    """Return a function turning a sub-command ("busy", "stop") into one hooks.json `command` string.

    Antigravity runs the string through a shell (verified with agy 1.2.7: quoting, arguments and `||`
    all work), so the command can end in `|| true`. It always exits 0 and prints nothing: Antigravity
    reads a hook's stdout as a decision and its exit code is undocumented, so a PreToolUse hook that
    fails could deny every tool call. Python itself exits 2 when the app is missing.
    """
    if sys.platform == "win32":
        # Use this interpreter's path, because `python` may be the Microsoft Store stub.
        return lambda sub: f"& {_powershell_quote(sys.executable)} {_powershell_quote(str(app))} hook {sub}; exit 0"
    return lambda sub: f"python3 {shlex.quote(str(app))} hook {sub} || true"


def statusline_command(app):
    """The `statusLine.command` string. The same shell runs it, but its stdout *is* the status line, so
    there is no `|| true`: the script prints one line and swallows its own errors."""
    if sys.platform == "win32":
        return f"& {_powershell_quote(sys.executable)} {_powershell_quote(str(app))} statusline"
    return f"python3 {shlex.quote(str(app))} statusline"


def _powershell_quote(text):
    return "'" + text.replace("'", "''") + "'"


def write_host_launcher(app):
    """Chrome starts native hosts as executables, so wrap `python antigravalgia.pyz host` in a script."""
    if sys.platform == "win32":
        launcher = paths.data_dir() / "antigravalgia-host.bat"
        with open(launcher, "w", newline="\r\n") as f:
            f.write(f'@echo off\n"{sys.executable}" "{app}" host %*\n')
    else:
        launcher = paths.data_dir() / "antigravalgia-host"
        launcher.write_text(f'#!/bin/sh\nexec python3 {shlex.quote(str(app))} host "$@"\n')
        launcher.chmod(0o755)
    return launcher


def register_host(launcher):
    """Tell Chrome where the native host is. Returns the manifest paths written."""
    manifest = json.dumps(
        {
            "name": HOST_NAME,
            "description": "Antigravalgia: Antigravity CLI status for Chrome",
            "path": str(launcher),
            "type": "stdio",
            "allowed_origins": [f"chrome-extension://{EXTENSION_ID}/"],
        },
        indent=2,
    ) + "\n"

    if sys.platform == "win32":
        import winreg

        target = manifest_path()
        target.write_text(manifest)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _windows_key()) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, str(target))
        return [target]

    written = []
    for directory in _manifest_dirs():
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / f"{HOST_NAME}.json"
        target.write_text(manifest)
        written.append(target)
    return written


def manifest_path():
    """The native host manifest Chrome reads (the Chrome one, on Linux)."""
    if sys.platform == "win32":
        return paths.data_dir() / f"{HOST_NAME}.json"
    return _manifest_dirs()[0] / f"{HOST_NAME}.json"


def unregister_host():
    if sys.platform == "win32":
        import winreg

        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, _windows_key())
        except FileNotFoundError:
            pass
        return
    for directory in _manifest_dirs(all_browsers=True):
        (directory / f"{HOST_NAME}.json").unlink(missing_ok=True)


def _windows_key():
    return rf"Software\Google\Chrome\NativeMessagingHosts\{HOST_NAME}"


def _manifest_dirs(all_browsers=False):
    if sys.platform == "darwin":
        return [Path.home() / "Library" / "Application Support" / "Google" / "Chrome" / "NativeMessagingHosts"]
    config = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    # Chrome always; Chromium only when it has a profile (Snap/Flatpak browsers can't start native hosts).
    browsers = ["google-chrome", "chromium"]
    return [
        config / b / "NativeMessagingHosts"
        for b in browsers
        if all_browsers or b == "google-chrome" or (config / b).is_dir()
    ]
