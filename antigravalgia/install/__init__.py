"""Installer: copies the app and extension into the per-user data directory, then wires up Chrome and
Antigravity CLI.

Usage: python3 -m antigravalgia.install                      interactive menu
       python3 -m antigravalgia.install 1|2|3 [--no-sound] [--statusline]
       python3 -m antigravalgia.install set sound on|off     change a setting of the installed app
       python3 -m antigravalgia.install set notifications on|off
       python3 -m antigravalgia.install statusline on|off    add or remove Antigravity's status line
       python3 -m antigravalgia.install uninstall            remove everything
"""
import shutil
import sys
import tempfile
import zipapp
from pathlib import Path

from .. import __version__, config, notify, paths
from . import antigravity, system

REPO = Path(__file__).resolve().parents[2]

MENU = """
Antigravalgia {version} installer ({os})

  1) Chrome extension
  2) Chrome extension + OS notifier
  3) Nothing (exit)
"""

STATUSLINE_QUESTION = 'Also show "needs you" alerts? This sets Antigravity\'s status line command.'


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    arg = argv[0] if argv else None
    if arg == "uninstall":
        uninstall()
        return
    if arg == "set":
        set_option(*argv[1:3])
        return
    if arg == "statusline":
        set_statusline(*argv[1:2])
        return
    if arg in ("1", "2", "3"):
        choice, sound, statusline = arg, "--no-sound" not in argv, "--statusline" in argv
    else:
        choice = ask()
        sound = choice == "2" and ask_yes_no("Play a sound with notifications?")
        statusline = choice == "2" and _statusline_free() and ask_yes_no(STATUSLINE_QUESTION, default=False)
    if choice == "3":
        print("Nothing installed.")
        return
    install(notifications=choice == "2", sound=sound, statusline=statusline)


def ask():
    print(MENU.format(version=__version__, os=system.label()))
    while True:
        try:
            choice = input("Choose 1, 2 or 3: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return "3"
        if choice in ("1", "2", "3"):
            return choice


def ask_yes_no(question, default=True):
    prompt = "[Y/n]" if default else "[y/N]"
    while True:
        try:
            answer = input(f"{question} {prompt}: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return default
        if not answer:
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False


def set_option(name=None, value=None):
    """Change one setting in the installed config.json; the hook picks it up on its next event."""
    if name not in config.DEFAULTS or value not in ("on", "off"):
        sys.exit("usage: python3 -m antigravalgia.install set sound|notifications on|off")
    if not paths.config_file().exists():
        sys.exit("Antigravalgia isn't installed. Run the installer first.")
    settings = config.load()
    settings[name] = value == "on"
    config.save(settings)
    print(f"✓ {name.capitalize()} {value}")


def set_statusline(value=None):
    """Add or remove Antigravalgia's status line in Antigravity's own settings.json."""
    if value not in ("on", "off"):
        sys.exit("usage: python3 -m antigravalgia.install statusline on|off")
    if not paths.app_file().exists():
        sys.exit("Antigravalgia isn't installed. Run the installer first.")
    try:
        if value == "off":
            antigravity.uninstall_statusline()
            print("✓ Status line removed")
        elif _install_statusline():
            print(f"✓ Status line written to {antigravity.settings_path()}")
    except antigravity.ConfigError as error:
        sys.exit(f"! {error}")


def install(notifications, sound=True, statusline=False):
    data = paths.data_dir()
    data.mkdir(parents=True, exist_ok=True)
    _copy_extension()
    app = _build_app()
    print(f"✓ Installed to {data}")

    for manifest in system.register_host(system.write_host_launcher(app)):
        print(f"✓ Native host registered: {manifest}")

    try:
        antigravity.install(system.hook_command(app))
        print(f"✓ Antigravity CLI hooks written to {antigravity.hooks_path()}")
    except antigravity.ConfigError as error:
        print(f"! {error}")
        print("  Fix that file by hand, then run the installer again.")

    config.save({"notifications": notifications, "sound": sound})
    if notifications:
        print(f"✓ OS notifier on, {'with' if sound else 'without'} sound: a notification appears when Antigravity finishes")
        hint = notify.setup_hint()
        if hint:
            print(f"  ! {hint}")
    else:
        print("✓ OS notifier off")

    if statusline:
        try:
            if _install_statusline():
                print(f'✓ Status line on: "Antigravity needs you" alerts, stacked under Antigravity\'s own line')
        except antigravity.ConfigError as error:
            print(f"! {error}")

    print(
        f"""
Next, if the extension isn't loaded yet: open chrome://extensions, turn on Developer mode,
click "Load unpacked" and pick: {paths.extension_dir()}
Then pin the lower back to the toolbar. Restart running Antigravity CLI sessions to load the hooks.
Check them with: agy -p "/hooks" --output-format json"""
    )


def uninstall():
    system.unregister_host()
    for step in (antigravity.uninstall, antigravity.uninstall_statusline):
        try:
            step()
        except antigravity.ConfigError as error:
            print(f"! {error}")
    shutil.rmtree(paths.data_dir(), ignore_errors=True)
    print("✓ Antigravalgia removed. Remove the extension itself from chrome://extensions.")


def _statusline_free():
    """True when no one owns Antigravity's status line, or we already do."""
    return antigravity.statusline_owner() in (None, antigravity.BUNDLE)


def _install_statusline():
    """Write our status line unless someone else's is already there. Returns True when it was written."""
    if not _statusline_free():
        print(f"! You already have a custom status line in {antigravity.settings_path()}; left it alone.")
        print(f'  To use Antigravalgia\'s instead, set statusLine.command to:')
        print(f"    {system.statusline_command(paths.app_file())}")
        return False
    antigravity.install_statusline(system.statusline_command(paths.app_file()))
    return True


def _copy_extension():
    # Chrome loads the unpacked extension from here, so the repository can be moved or deleted.
    target = paths.extension_dir()
    shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(REPO / "extension", target, ignore=shutil.ignore_patterns("*.svg", ".DS_Store"))


def _build_app():
    # Pack the runtime modules into one file that hooks, the status line and the native host run directly.
    target = paths.app_file()
    with tempfile.TemporaryDirectory() as staging:
        shutil.copytree(
            REPO / "antigravalgia",
            Path(staging) / "antigravalgia",
            ignore=shutil.ignore_patterns("__pycache__", "install"),
        )
        zipapp.create_archive(staging, target, main="antigravalgia.cli:main")
    return target
