"""Entry point of the installed antigravalgia.pyz.

`hook busy|stop` is called by Antigravity CLI, `statusline` by its TUI, `host` by Chrome.
"""
import sys


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    command = argv[0] if argv else ""
    if command == "hook":
        from . import hook

        hook.main(argv[1:])
    elif command == "statusline":
        from . import statusline

        statusline.main()
    elif command == "host":
        from . import host

        host.main()
    else:
        sys.exit("usage: antigravalgia.pyz hook busy|stop | statusline | host")
