# Antigravalgia

**Your back hurts while Antigravity works. It relaxes when Antigravity is ready.**

A Chrome toolbar button that shows whether Antigravity CLI is working, with optional desktop notifications. It works on macOS, Ubuntu and Windows.

> *antigravalgia* (n.): antigrav + *-algia* (pain). Physiology calls the muscles that hold you upright — the erector spinae above all — the antigravity muscles. They are also the ones that ache after a day at a desk.

- Website: <https://antigravalgia.tpojka.com>
- Source: <https://github.com/Tpojka/antigravalgia>

---

## Three states, one glance

| Icon | State | Meaning |
| :-: | --- | --- |
| 🔴 | **Working** | Antigravity CLI is working on a task in at least one session |
| 🟢 | **Ready** | Antigravity has finished, or is waiting for you to confirm a tool |
| ⚪ | **Not connected** | The local helper isn't running. Run the installer |

Hover over the icon to see how many sessions are working.

## What you get

- **Live toolbar status:** the icon changes the moment Antigravity starts or finishes a turn, with no polling delay.
- **Every session:** the back hurts while *any* Antigravity CLI session is working.
- **"Needs you" alerts:** Antigravity's hooks can't tell you it's waiting. Its status line can, and Antigravalgia uses it — optionally, and never over a status line you already have.
- **Three platforms:** macOS, Ubuntu/Linux and Windows. The installer detects which one you're on.
- **Stays out of the way:** it owns one bundle in your shared `~/.gemini/config/hooks.json`, backs it up, and leaves a file it can't parse untouched.
- **Fully local:** nothing leaves your machine. The status goes from Antigravity's hooks to Chrome over native messaging.

## Install

Requires Python 3.9 or newer, Google Chrome and Antigravity CLI 1.1.10 or newer.

**macOS**

```sh
git clone https://github.com/Tpojka/antigravalgia.git
cd antigravalgia
./install.sh
```

**Ubuntu**

```sh
sudo apt install python3 libnotify-bin   # notify-send, for the notifier
git clone https://github.com/Tpojka/antigravalgia.git
cd antigravalgia
./install.sh
```

**Windows**

```bat
winget install Python.Python.3.12
git clone https://github.com/Tpojka/antigravalgia.git
cd antigravalgia
install.cmd
```

The installer asks:

```
  1) Chrome extension
  2) Chrome extension + OS notifier
  3) Nothing (exit)
Choose 1, 2 or 3: 2
Play a sound with notifications? [Y/n]:
Also show "needs you" alerts? This sets Antigravity's status line command. [y/N]:
```

Then load the extension (once):

1. Open `chrome://extensions` and turn on **Developer mode**.
2. Click **Load unpacked** and pick the `extension` folder the installer printed.
3. Pin **Antigravalgia** to the toolbar.
4. Restart any running Antigravity sessions, then check the hooks loaded with `agy -p "/hooks" --output-format json`.

Antigravalgia writes one bundle named `antigravalgia` into the shared `~/.gemini/config/hooks.json`, and nothing else. Your other bundles stay, the file is backed up first, and a file it can't parse is left exactly as it is.

## OS notifier

You get a notification when Antigravity finishes a turn, and — with the status line on — when it needs you. The title includes the project name.

| When | Title | Text | Needs |
| --- | --- | --- | --- |
| Antigravity finishes a turn | Antigravity is ready · *project* | Task finished | hooks |
| A tool confirmation dialog opens | Antigravity needs you · *project* | Waiting for your confirmation | the status line |

### The status line: where "needs you" comes from

Antigravity's hooks have no notification, permission, session-start or session-end event — five events, and none of them says the agent is waiting for you. Its **status line** does: whenever the agent state changes, the TUI runs a script of your choosing and pipes it a payload carrying `agent_state` and `tool_confirmation_pending`.

So Antigravalgia offers the status line as an optional precision mode on top of the hooks. It adds one short line under Antigravity's own:

```
antigravalgia · ready · 1 of 2 sessions working
```

It **never overwrites a status line you already have**. Turn it on or off later:

```sh
python3 -m antigravalgia.install statusline on
python3 -m antigravalgia.install statusline off
```

### Change settings any time

Run these from the repository. They take effect with the next notification, with no restart:

```sh
python3 -m antigravalgia.install set sound off           # silent notifications
python3 -m antigravalgia.install set sound on
python3 -m antigravalgia.install set notifications off   # no notifications at all
python3 -m antigravalgia.install set notifications on
```

On Windows, use `py -3` instead of `python3`.

Or use your OS settings:

| OS | Where |
| --- | --- |
| macOS | System Settings → Notifications → **Script Editor** |
| Ubuntu (GNOME) | Settings → Sound → **System Sounds**, or Notifications → Do Not Disturb |
| Windows | Settings → System → Notifications → **Windows PowerShell** |

## How it works

```
Antigravity CLI ──hook────────► antigravalgia.pyz hook busy|stop ──► sessions/<conversationId>
                                            └──────────────────────► desktop notification (optional)
                └──status line──► antigravalgia.pyz statusline ────► the same file, plus "needs you"

Chrome ──starts──► antigravalgia.pyz host
                      watches sessions/, pushes status on change
                                  │  native messaging
                                  ▼
                   extension swaps the icon
```

Antigravity's hook payload carries **no event name**, so each event registers its own sub-command.

| Antigravity event | Back | Notification |
| --- | --- | --- |
| `PreInvocation`, `PostInvocation` | hurts | none |
| `PreToolUse`, `PostToolUse` | hurts | none |
| `Stop` with `fullyIdle: true` | relaxes | Antigravity is ready |
| `Stop` with `fullyIdle: false` | stays hurting | none |

And from the status line, when it's on:

| Status line payload | Back | Notification |
| --- | --- | --- |
| `tool_confirmation_pending: true` | relaxes — it's your turn | Antigravity needs you |
| `agent_state` `thinking`, `working`, `tool_use` | hurts | none |
| `agent_state` `idle`, `initializing` | relaxes | none — the `Stop` hook already did |

The hook prints nothing and always exits 0. Antigravity reads a hook's stdout as a *decision* (`allow`, `deny`, `force_ask`) and its exit codes are undocumented, so a `PreToolUse` hook that misbehaves could gate every tool call. The status line never prints an error either, because its stdout *is* the status line.

It covers **Antigravity CLI** (`agy`). Headless `agy -p` runs are covered by the hooks, but not by the status line, which only runs while the TUI draws. The Antigravity 2.0 app and the IDE read the same hooks file and should work too, but they aren't tested yet. It doesn't cover Gemini CLI, which is a different product.

---

Antigravalgia 1.0.0 · [MIT](https://github.com/Tpojka/antigravalgia/blob/main/LICENSE) © 2026 Goran Grbic · An independent project, not affiliated with Google.

Using another agent? [Claudication](https://claudication.tpojka.com) for Claude Code, [Codexalgia](https://codexalgia.tpojka.com) for Codex CLI, [Copilonidal](https://copilonidal.tpojka.com) for GitHub Copilot CLI.
