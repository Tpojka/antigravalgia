# Antigravalgia

A Chrome toolbar button that shows whether Antigravity CLI is working, with optional desktop notifications. It works on macOS, Ubuntu/Linux and Windows.

| Icon | Meaning |
| --- | --- |
| <img src="extension/icons/back-pain-48.png" width="24"> | Lower back in pain: Antigravity is working on a task |
| <img src="extension/icons/back-ok-48.png" width="24"> | Relaxed back: Antigravity is ready (finished, or waiting for your confirmation) |
| <img src="extension/icons/back-unknown-48.png" width="24"> | Grey: the native host isn't connected (run the installer) |

Hover over the icon to see how many sessions are working.

Physiology calls the muscles that hold you upright — the erector spinae above all — the **antigravity muscles**. They are also exactly the muscles that ache after a day at a desk. Antigravalgia is the sibling of [Claudication](https://github.com/Tpojka/claudication) (Claude Code), [Codexalgia](https://github.com/Tpojka/codexalgia) (Codex CLI) and [Copilonidal](https://github.com/Tpojka/copilonidal) (GitHub Copilot CLI). All four can be installed side by side.

## Install

Requires Python 3.9 or newer, Google Chrome and Antigravity CLI **1.1.10 or newer** (see [Minimum version](#minimum-version)). macOS ships Python as `/usr/bin/python3`. On Windows, install it from python.org or with `winget install Python.Python.3.12`.

```sh
./install.sh        # macOS / Ubuntu
install.cmd         # Windows
```

The installer detects your OS and asks what to install:

```
  1) Chrome extension
  2) Chrome extension + OS notifier
  3) Nothing (exit)
Choose 1, 2 or 3: 2
Play a sound with notifications? [Y/n]:
Also show "needs you" alerts? This sets Antigravity's status line command. [y/N]:
```

The third question is the [status line](#the-status-line-needs-you-alerts). It is only asked when you don't already have a custom status line, and answering no leaves Antigravity's settings untouched.

To skip the prompts, pass the choice directly: `python3 -m antigravalgia.install 2` (with sound), `2 --no-sound`, or `2 --statusline`.

Everything is copied into a per-user data directory, so you can move or delete the repository afterwards:

| OS | Data directory |
| --- | --- |
| macOS | `~/Library/Application Support/Antigravalgia` |
| Ubuntu/Linux | `~/.local/share/antigravalgia` (or `$XDG_DATA_HOME/antigravalgia`) |
| Windows | `%LOCALAPPDATA%\Antigravalgia` |

Then load the extension from that directory (only needed once):

1. Open `chrome://extensions` and turn on **Developer mode**.
2. Click **Load unpacked** and select the `extension` folder inside the data directory. The installer prints the exact path.
3. Pin **Antigravalgia** to the toolbar.
4. Restart any running Antigravity CLI sessions so they load the hooks.

Check that Antigravity picked the hooks up. This answers without starting a turn or spending quota:

```sh
agy -p "/hooks" --output-format json      # antigravalgia should be listed
```

Running the installer again is safe. It updates the installed copy and rewrites its own hook bundle.

### What it writes

Both files belong to Antigravity and are shared with other tools, so Antigravalgia merges into them key by key, keeps a `.antigravalgia.bak` copy, and **never rewrites either one whole**. A file it cannot parse is left byte-identical and reported, because the CLI itself once lost every setting to exactly that (fixed in 1.1.16).

| File | What goes in |
| --- | --- |
| `~/.gemini/config/hooks.json` | one top-level bundle named `antigravalgia`. Your other bundles are untouched, and uninstalling deletes only that key |
| `~/.gemini/antigravity-cli/settings.json` | only with consent: a `statusLine` block, with `stack_with_default` so Antigravity's own line stays |

On Windows both live under `%USERPROFILE%\.gemini\`.

## OS notifier

When the OS notifier is on, you get a notification when Antigravity finishes a turn. With the status line on as well, you also get one when it needs you.

| When | Title | Text | Needs |
| --- | --- | --- | --- |
| Antigravity finishes a turn | Antigravity is ready · *project* | Task finished | hooks |
| A tool confirmation dialog opens | Antigravity needs you · *project* | Waiting for your confirmation | the status line |

How each OS shows them:

- **macOS:** built-in `osascript`, with the Glass sound. The first time, allow notifications for **Script Editor** in System Settings → Notifications.
- **Ubuntu/Linux:** `notify-send` (`sudo apt install libnotify-bin`), with the freedesktop "complete" sound through `paplay` when available.
- **Windows:** a toast through built-in PowerShell, with the default notification sound. No modules are needed.

### The status line: "needs you" alerts

Antigravity's hooks never report that the agent is waiting for you — there is no notification or permission event. Its **status line** does. Whenever the agent state changes, the TUI runs a script of your choosing, pipes it a detailed state payload and renders what it prints. That payload carries `agent_state` and `tool_confirmation_pending`, which is the "needs you" signal.

So the status line is an optional precision mode on top of the hooks:

```sh
python3 -m antigravalgia.install statusline on
python3 -m antigravalgia.install statusline off
```

It adds one short line under Antigravity's own, telling you only what that line can't know — how your other sessions are doing:

```
antigravalgia · ready · 1 of 2 sessions working
```

**It never overwrites a status line you already have.** If `statusLine.command` is already set to something else, the installer says so and prints the command to set by hand instead.

The status line only runs while the TUI is drawing, so it does nothing in headless `agy -p` runs. The hooks cover those.

### Notifier settings

Change the settings from the terminal, run from the repository. They take effect with the next notification, with no reinstall or restart:

```sh
python3 -m antigravalgia.install set sound off           # silent notifications
python3 -m antigravalgia.install set sound on
python3 -m antigravalgia.install set notifications off   # no notifications at all
python3 -m antigravalgia.install set notifications on
```

On Windows, use `py -3` instead of `python3`.

The settings are stored in `config.json` in the [data directory](#install), which you can also edit by hand:

```json
{ "notifications": true, "sound": false }
```

You can also mute or turn off the notifications in your OS settings, without touching Antigravalgia:

| OS | Where |
| --- | --- |
| macOS | System Settings → Notifications → **Script Editor**: turn off "Play sound for notification", or turn notifications off |
| Ubuntu (GNOME) | Settings → Sound → **System Sounds** volume, or Settings → Notifications → Do Not Disturb |
| Windows | Settings → System → Notifications → **Windows PowerShell**: turn off "Play a sound when a notification arrives", or turn notifications off |

The notifications come from Script Editor on macOS and Windows PowerShell on Windows, because those are the built-in tools that show them. Changing these OS settings also affects other scripts that use the same tools.

## How it works

```
Antigravity CLI ──hook──────► antigravalgia.pyz hook busy|stop ──► <data>/sessions/<conversationId>
                                          └──────────────────────► desktop notification (if enabled)
                └──status line──► antigravalgia.pyz statusline ──► the same file, plus "needs you"

Chrome ──starts──► antigravalgia-host ──► antigravalgia.pyz host
                      watches <data>/sessions, pushes status on change
                                  │  native messaging
                                  ▼
                   extension/background.js swaps the icon
```

Antigravity's hook payload has **no event name field**, so each event registers its own sub-command:

| Antigravity event | Sub-command | Session becomes | Notification |
| --- | --- | --- | --- |
| `PreInvocation`, `PostInvocation` | `hook busy` | busy | none |
| `PreToolUse`, `PostToolUse` (matcher `.*`) | `hook busy` | busy | none |
| `Stop` with `fullyIdle: true` | `hook stop` | ready | "Antigravity is ready" |
| `Stop` with `fullyIdle: false` | `hook stop` | stays busy | none |

And from the status line, when it's on:

| Payload | Session becomes | Notification |
| --- | --- | --- |
| `tool_confirmation_pending: true` | waiting | "Antigravity needs you" |
| `agent_state` `thinking`, `working`, `tool_use` | busy | none |
| `agent_state` `idle`, `initializing` | ready | none — the `Stop` hook already notified |

- **Never in the way:** the hook prints nothing and always exits 0, even when Python or the installed app is missing. Antigravity parses a hook's stdout as a *decision* (`allow`, `deny`, `force_ask`), and its exit codes are undocumented, so a `PreToolUse` hook that misbehaves could gate every tool call. The status line likewise never prints an error, because its stdout *is* the status line.
- **`waiting` relaxes the back.** When Antigravity is blocked on your confirmation, it isn't working — it's your turn — so the icon goes green and the notification tells you.
- **Session key:** `conversationId` from the hooks, `conversation_id` from the status line. They are the same conversation UUID.
- **Multiple sessions:** the back hurts while *any* session is busy.
- **No session end, no interrupt event:** Antigravity has neither, so a session busy with no activity for 15 minutes counts as ready (`ANTIGRAVALGIA_BUSY_STALE_SECONDS`), and a session untouched for 24 hours is forgotten.
- **Stable extension ID:** the `key` in `extension/manifest.json` fixes the ID to `bpfhgifephcgodfaicmamfpgpcikhidd`, which is the only extension the native host accepts.

### Minimum version

Antigravity CLI ships roughly daily. These are the releases the design depends on:

| Version | What it fixed |
| --- | --- |
| 1.0.6 | added `stack_with_default`, so the status line can sit under Antigravity's own |
| 1.0.8 | `/hooks` writes to the shared `~/.gemini/config/hooks.json` |
| 1.0.16 | empty decision strings from pre-tool hooks stopped erroring |
| 1.1.9 | `PostToolUse` stopped firing on non-tool steps and started honouring matchers |
| **1.1.10** | **hooks run before the built-in termination checks, so `Stop` hooks run at all** |

Below 1.1.10 the `Stop` hook may never fire, and the back would only relax on the 15-minute staleness rule.

### Scope

| Where Antigravity runs | Covered? |
| --- | --- |
| Antigravity CLI (`agy`) in the terminal | Yes |
| Antigravity CLI headless (`agy -p`) | Hooks yes, status line no |
| Antigravity 2.0 app and the Antigravity IDE | Probably: they read the same `~/.gemini/config/hooks.json`. Not tested |
| Gemini CLI | No. It's a different product, and personal accounts are being migrated off it |

### Not verified yet

These were checked against agy 1.2.7 on macOS and **are** confirmed: the hook `command` string runs through a shell (quoting, arguments and `|| true` all take effect); `timeout` is in seconds; `/hooks` lists the bundle; `PreInvocation`, `PreToolUse`, `PostToolUse` and `PostInvocation` all fire in headless runs; `error` is `""` after a successful tool call; and the hook's own working directory is the *hooks file's* folder, not your project — which is why the project name comes from the payload.

Still open:

- **`workspacePaths` is empty in headless runs**, even when `agy -p` is started inside a project, so the "ready" notification then carries no project name. Whether the TUI fills it in is untested.
- Whether `Stop` fires when a turn ends by permission denial. It did not in the headless runs observed here.
- What `terminationReason` values occur, and whether `fullyIdle` is ever `false` in practice.
- Whether Ctrl+C (cancel) fires `Stop` at all. If it doesn't, the session counts as busy until the 15-minute rule applies.
- Whether hooks run under `agy --sandbox`, and whether they can still write to the data folder.
- Whether the same hooks light the icon for Antigravity 2.0 and IDE sessions.
- Which shell runs a `command` string on Windows. CI runs the generated command through PowerShell, but not through Antigravity CLI itself.

## Project layout

```
antigravalgia/         Python package (standard library only)
  hook.py              Antigravity CLI hook handler
  statusline.py        status line script: "needs you" and the session summary
  host.py              Chrome native messaging host
  state.py             per-session busy/ready/waiting files
  notify.py            desktop notifications per OS
  config.py, paths.py  installed settings and locations
  cli.py               entry point of the installed antigravalgia.pyz
  install/             installer: copies files, registers the host, merges Antigravity's config
extension/             Chrome extension (Manifest V3)
site/                  landing page for antigravalgia.tpojka.com
tests/                 unittest suite
```

## Development

```sh
python3 -m unittest -v
```

The tests are self-contained. Every test uses a temporary home and data directory, so your real install and your real `~/.gemini` aren't touched. CI runs them on macOS, Ubuntu and Windows with Python 3.9 and the latest Python 3.

To use a data directory other than the default, set `ANTIGRAVALGIA_HOME`.

## Uninstall

```sh
./uninstall.sh      # macOS / Ubuntu
uninstall.cmd       # Windows
```

This removes the `antigravalgia` hook bundle, its status line (only if it's still ours), the native host registration and the data directory. Your other hooks and settings stay. Then remove the extension from `chrome://extensions`.

See [CHANGELOG.md](CHANGELOG.md) for release history.

## License

[MIT](LICENSE) © 2026 Goran Grbic. An independent project, not affiliated with Google.
