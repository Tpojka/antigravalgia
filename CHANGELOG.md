# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-09-20

The first release. It was checked against the Antigravity CLI hooks and status line documentation, and against `agy` 1.2.7 running on macOS, on 2026-09-20.

### Added

- **Chrome toolbar lower back** that hurts while Antigravity is working and relaxes when Antigravity is ready. The tooltip shows how many sessions are working.
- **Antigravity CLI hooks** in one bundle named `antigravalgia` in the shared `~/.gemini/config/hooks.json`, for `PreInvocation`, `PostInvocation`, `PreToolUse`, `PostToolUse` and `Stop`.
  *Why a bundle:* that file is keyed by bundle name and is shared with the `/hooks` command, the Antigravity 2.0 app and the IDE. The installer replaces only its own key, backs the file up first, and leaves a file it can't parse byte-identical.
  - Antigravity's payload carries **no event name**, so each event registers its own sub-command (`hook busy`, `hook stop`) instead of reading the event from the payload.
  - `Stop` marks a session ready only when `fullyIdle` is true, so intermediate stops don't end the turn early.
  - Sessions are keyed by `conversationId`, and the project name in a notification comes from `workspacePaths[0]` — never from the working directory, which is the hooks file's folder, not your project.
- **An optional status line**, which is the only source of the "needs you" signal. Antigravity has no notification, permission, session-start or session-end event, but its status line payload carries `agent_state` and `tool_confirmation_pending`.
  - Written to `~/.gemini/antigravity-cli/settings.json` with `stack_with_default: true`, so Antigravity's own line stays above it.
  - **Never overwrites an existing custom status line**: the installer says so and prints the command to set by hand.
  - Prints one short line — the session state, plus the cross-session count the built-in line can't know.
  - Turn it on or off later with `python3 -m antigravalgia.install statusline on|off`.
- **A third state, `waiting`,** for an open tool confirmation dialog. It counts as ready in the toolbar: Antigravity is blocked on you, not working.
- **Notifications are edge-triggered.** The status line script runs on *every* agent state change, so "Antigravity needs you" fires once per dialog, not once per redraw.
- **A hook command that can't break Antigravity.** It prints nothing and always exits 0 (`|| true` in a shell, `; exit 0` in PowerShell), even when Python or the installed app is missing.
  *Why:* Antigravity parses a hook's stdout as a decision (`allow`, `deny`, `force_ask`) and its exit codes are undocumented, so a misbehaving `PreToolUse` hook could gate every tool call. The status line likewise never prints an error, because its stdout is the status line.
- **Hook payload read as UTF-8 bytes**, so project names with non-ASCII letters work on Windows, where text stdin uses the ANSI code page.
- **Optional OS notifier** (macOS `osascript`, Linux `notify-send`, Windows PowerShell toast), with or without sound: "Antigravity is ready" and "Antigravity needs you".
- **Its own identifiers:** native host (`com.tpojka.antigravalgia`), extension ID (`bpfhgifephcgodfaicmamfpgpcikhidd`), data directory and `antigravalgia.pyz`, so it doesn't clash with Claudication, Codexalgia or Copilonidal.
- The `set` and `statusline` commands, `ANTIGRAVALGIA_HOME`, `ANTIGRAVALGIA_BUSY_STALE_SECONDS`, a 66-test unittest suite, and CI on macOS, Ubuntu and Windows. Tests run the generated hook command through `sh`, `bash` and PowerShell with a real payload on stdin, check that it exits 0 and prints nothing even with the app deleted, and check that the status line prints exactly one line on garbage input.
- Landing page for antigravalgia.tpojka.com in `site/`.

### Verified against agy 1.2.7

Recorded here because the documentation doesn't state them:

- A hook `command` runs **through a shell**: quoting, an argument and a trailing `|| true` all take effect.
- The hook process runs with the **hooks file's directory** as its working directory, not the workspace.
- `workspacePaths` is **empty in headless (`agy -p`) runs**, even when started inside a project.
- `timeout` is in seconds, and `/hooks` reports it as `timeout_seconds`.
- `agy -p "/hooks" --output-format json` answers without starting a turn.
- A full headless turn against the installed hooks ends with the session on `ready`, so `Stop` fires with `fullyIdle: true` when a turn completes normally.

[1.0.0]: https://github.com/Tpojka/antigravalgia/releases/tag/v1.0.0
