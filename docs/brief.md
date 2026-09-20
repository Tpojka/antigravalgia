# Brief: a Claudication for Antigravity CLI

Written on 2026-09-20 in a Claude Code session in `~/GitHub/Tpojka/copilonidal`, to start a new, separate repository. It replaces an earlier draft aimed at Gemini CLI, which was deleted.

Everything below was checked on 2026-09-20 against primary sources: the `google-antigravity/antigravity-cli` repository at release **1.2.7** (published 2026-09-19) — its `README.md`, `CHANGELOG.md` and `examples/statusline/statusline.sh` — and the official documentation at `antigravity.google/docs`. Antigravity CLI ships roughly daily, so re-check every claim here before building on it.

> **Why Antigravity CLI and not Gemini CLI.** Google is migrating individual users off Gemini CLI and onto Antigravity. A personal Google login now fails with:
>
> ```
> reasonCode: UNSUPPORTED_CLIENT
> reasonMessage: This client is no longer supported for Gemini Code Assist for individuals.
>                To continue using Gemini, please migrate to the Antigravity suite of products
> ```
>
> Confirmed first-hand by the author on 2026-09-20 (login refused, redirected to Antigravity), and corroborated in `google-gemini/gemini-cli`: issue #28846 ("OAuth personal … UNSUPPORTED_CLIENT and Antigravity migration"), #28229 ("OAuth login fails for Google AI Pro users"), #29426 (a CPU check *before the Antigravity migration prompt*, merged 2026-09-20), and the CLI's own `packages/cli/src/ui/utils/antigravityUtils.ts`, which prints the Antigravity install command in a banner that — uniquely — is exempt from the five-showings cap.
>
> The repository itself is still active (v0.60.0, 2026-09-15), so hooks may keep working for API-key, Vertex or enterprise Code Assist paths; that is **unverified** and irrelevant here. What matters is that an individual user cannot log in, so **Gemini CLI is not a viable target** and Antigravity CLI is.
>
> Antigravity CLI is a different product, not a rename: a different binary (`agy`), a different agent engine and a different hook system. It only shares the `~/.gemini/` configuration root. Almost nothing from a Gemini CLI design transfers, which is why this brief was written from scratch.

## Name

**Antigravalgia** — *antigrav* + *-algia* (pain), in the pattern of Codexalgia.

The icon is the **lower back**. This is not arbitrary: physiology calls the postural muscles that hold you upright — the erector spinae above all — the **antigravity muscles**. They are also exactly the muscles that ache after a day at a desk. The name, the icon and the product line up.

| Project | Agent | Icon |
|---|---|---|
| Claudication | Claude Code | knee |
| Codexalgia | Codex CLI | hip |
| Copilonidal | GitHub Copilot CLI | tailbone |
| **Antigravalgia** | **Antigravity CLI** | **lower back** |

Identifiers, all of which must differ from the three siblings:

| | Native host | Extension ID |
|---|---|---|
| Claudication | `com.tpojka.claudication` | `hpoodlefheijkfkpebmooehgnjkibdnc` |
| Codexalgia | `com.tpojka.codexalgia` | `pdfldjccnohafaolkilhbnhjkeaineaa` |
| Copilonidal | `com.tpojka.copilonidal` | `bkmgmoledlbikdmpgoaciefdkdokdnnl` |
| **Antigravalgia** | **`com.tpojka.antigravalgia`** | generate a new key, commit the public `key` in `manifest.json`, keep the `.pem` local and gitignored |

Also new: Python package `antigravalgia`, app `antigravalgia.pyz`, launcher `antigravalgia-host`, data folder `~/Library/Application Support/Antigravalgia` / `~/.local/share/antigravalgia` / `%LOCALAPPDATA%\Antigravalgia`, env vars `ANTIGRAVALGIA_HOME` and `ANTIGRAVALGIA_BUSY_STALE_SECONDS`, icons `back-pain`, `back-ok`, `back-unknown`.

Alternatives if it reads too long: **Agyalgia** (after the `agy` command, shortest), **Antigravitis** (plainest). Check GitHub for the name before committing to it.

## What Antigravity CLI is

- Binary: **`agy`**. Installed with `curl -fsSL https://antigravity.google/cli/install.sh | bash` (macOS/Linux), `irm https://antigravity.google/cli/install.ps1 | iex` (Windows PowerShell), or an `install.cmd` on Windows CMD.
- Closed source. `google-antigravity/antigravity-cli` carries only the README, a detailed CHANGELOG, and `examples/`. Documentation lives at `antigravity.google/docs`.
- It shares its agent engine, settings and permissions bidirectionally with the **Antigravity 2.0 GUI**, and shares the `~/.gemini/` config root with it.
- Config layout (Windows: `%USERPROFILE%\.gemini\...`):

| Path | Holds |
|---|---|
| `~/.gemini/config/hooks.json` | **user-level hooks, shared between the TUI and the backend.** This is where the `/hooks` command writes |
| `~/.gemini/antigravity-cli/settings.json` | CLI settings, including the `statusLine` block. Sparse: only non-default values are written |
| `~/.gemini/antigravity-cli/keybindings.json` | key bindings |
| `~/.gemini/antigravity-cli/cache/` | caches |
| `<workspace>/.agents/hooks.json` | workspace-level hooks, loaded after the folder is trusted |
| plugins | may bundle their own `hooks.json` |

## Verified facts: hooks

- **Five events only:** `PreToolUse`, `PostToolUse`, `PreInvocation`, `PostInvocation`, `Stop`.

| Event | Fires |
|---|---|
| `PreInvocation` | before the model is called |
| `PostInvocation` | immediately after each model invocation completes |
| `PreToolUse` | before a tool is executed |
| `PostToolUse` | after a tool completes |
| `Stop` | when execution terminates |

- **There is no `SessionStart`, no `SessionEnd`, no user-prompt event and no notification or permission event.** This is the single biggest difference from all three siblings, and it drives the design below.
- **`hooks.json` is keyed by a hook-bundle name,** which is excellent news: Antigravalgia owns one top-level key and never touches anyone else's.
  ```json
  {
    "my-linter-hook": {
      "PostToolUse": [
        { "matcher": "run_command",
          "hooks": [ { "type": "command", "command": "./scripts/lint.sh", "timeout": 10 } ] }
      ]
    },
    "safety-gate": {
      "enabled": false,
      "PreToolUse": [
        { "matcher": "run_command", "hooks": [ { "command": "./scripts/safety-check.sh" } ] }
      ]
    },
    "reminder": {
      "PreInvocation": [ { "type": "command", "command": "./scripts/reminder.sh" } ]
    }
  }
  ```
  - `PreToolUse` / `PostToolUse` take matcher groups (`matcher` is a regex on the tool name, then a nested `hooks` array).
  - `PreInvocation` / `PostInvocation` / `Stop` take a flat list of handlers.
  - Handler fields: `type` (`"command"`), `command` (required), `timeout` (**seconds**, default 30).
  - `enabled: false` on a bundle disables it without deleting it. Default `true`.
- **I/O:** hooks receive JSON on **stdin** and return JSON on **stdout**.
- **Payload, every event:** `conversationId`, `workspacePaths` (an **array**), `transcriptPath`, `artifactDirectoryPath`, `modelName`. Note: no `hook_event_name`, no `cwd`, no `session_id` — none of the field names the sibling projects read.

| Event | Extra payload fields |
|---|---|
| `PreToolUse` | `toolCall` (name, args), `stepIdx` |
| `PostToolUse` | `toolCall`, `stepIdx`, `error` |
| `PreInvocation`, `PostInvocation` | `invocationNum`, `initialNumSteps` |
| `Stop` | `executionNum`, `terminationReason`, `error`, **`fullyIdle`** |

- **Control:** a `PreToolUse` hook can return `"deny"` (hard block), `"allow"` (auto-approve) or `"force_ask"` (always prompt). A `Stop` hook can return `"continue"` to stop the agent from stopping and re-enter the loop. **Antigravalgia must return neither** — it prints nothing.
- **`/hooks`** lists active hooks, including those bundled in plugins. In print mode it answers without starting a turn: `agy -p "/hooks"`, or `agy -p "/hooks" --output-format json`. Use this in the installer as the verification step.

## Verified facts: the status line (the better signal)

This is the discovery that shapes the project. A custom status line script gets far more than the hooks do.

- Configured under a `statusLine` block in `~/.gemini/antigravity-cli/settings.json`, with keys `type`, `command`, `padding`, `enabled` and **`stack_with_default`**.
- **"Whenever the agent state changes, the TUI executes your command script, pipes a detailed state JSON payload directly to the script's stdin, reads your formatted string from stdout, and renders the result in the prompt's status line."** So it is edge-triggered on state changes, not polled.
- Payload top-level fields: `cwd`, `session_id`, `conversation_id`, `transcript_path`, `model`, `workspace`, `version`, `context_window`, `exceeds_200k_tokens`, `product`, `quota`, **`agent_state`**, `vcs`, `sandbox`, `artifact_count`, `plan_tier`, `email`, `pending_input_count`, **`tool_confirmation_pending`**, `task_count`, `terminal_width`, `execution_mode`, `vim`. A `conversation_title` and a `cost` field were added in later releases and also go to the window title script.
- **`agent_state` values:** `idle`, `thinking`, `working`, `tool_use`, `initializing` (confirmed in the docs and in Google's own `examples/statusline/statusline.sh`).
- `tool_confirmation_pending` is the "needs you" signal that the hook system does not provide.
- `cwd` is here too, so notifications can name the project folder.

## Architecture decision

| Source | Gives | Misses |
|---|---|---|
| Hooks only | busy on `PreInvocation`/`PreToolUse`/`PostToolUse`, ready on `Stop` (`fullyIdle`). Works in headless `-p` runs | no "needs you", no session start/end, non-standard payload field names |
| Status line only | the CLI's own `agent_state`, `tool_confirmation_pending`, `session_id`, `cwd` — everything, edge-triggered | only runs while the TUI renders, so not in headless runs; occupies the `statusLine` setting |
| **Both (recommended)** | hooks as the always-on backbone, the status line as an opt-in "precision mode" that adds the waiting-for-you state | two writers to one state file — acceptable, they agree, and writes are atomic |

Make the status line a **third question in the installer**, alongside the notifier:

```
  1) Chrome extension
  2) Chrome extension + OS notifier
  3) Nothing (exit)
Choose 1, 2 or 3: 2
Play a sound with notifications? [Y/n]:
Also show "needs you" alerts? This sets Antigravity's status line command. [y/N]:
```

Only offer it when `statusLine.command` is unset. **Never overwrite an existing custom status line** — print the manual instructions instead. When it is set, write `stack_with_default: true` so the user keeps the default line, and have the script print an empty string (or one short marker).

## State mapping

From hooks:

| Event | Session becomes | Notification |
|---|---|---|
| `PreInvocation`, `PostInvocation` | busy | none |
| `PreToolUse`, `PostToolUse` (matcher `.*`) | busy | none |
| `Stop` with `fullyIdle: true` | ready | "Antigravity is ready" |
| `Stop` with `fullyIdle: false` | leave busy | none |

From the status line, when enabled:

| `agent_state` / flag | Session becomes | Notification |
|---|---|---|
| `tool_confirmation_pending: true` (any state) | waiting | "Antigravity needs you" |
| `thinking`, `working`, `tool_use` | busy | none |
| `idle` | ready | none (the `Stop` hook already notified) |
| `initializing` | ready | none |

Rules to carry over and to add:

- **Session key:** use `conversation_id` / `conversationId`, which both sources carry. Verify they are the same value before relying on it.
- **Edge-trigger the notifications.** The status line script runs on *every* state change; only notify when the previous stored state differs. The state file already holds the previous value — compare before writing.
- **No session end event exists.** Sessions are never removed explicitly; lean on the existing 24-hour staleness rule, and on the 15-minute busy-stale rule for interrupts (Ctrl+C cancels a turn; whether that fires `Stop` is unverified).
- **Project name for notifications** comes from `cwd` (status line) or `workspacePaths[0]` (hooks).
- Consider Codexalgia's third state, `waiting`, with its approval grace period; `tool_confirmation_pending` is exactly what it was designed for.

## Exactly what the installer writes

**1. `~/.gemini/config/hooks.json`** — read the file if it exists, replace only the `antigravalgia` key, write it back atomically, and keep a `.antigravalgia.bak` copy. Uninstall deletes just that key. The command must always exit 0 and print nothing:

```json
{
  "antigravalgia": {
    "PreInvocation":  [ { "type": "command", "command": "<CMD>", "timeout": 5 } ],
    "PostInvocation": [ { "type": "command", "command": "<CMD>", "timeout": 5 } ],
    "Stop":           [ { "type": "command", "command": "<CMD>", "timeout": 5 } ],
    "PreToolUse":  [ { "matcher": ".*", "hooks": [ { "type": "command", "command": "<CMD>", "timeout": 5 } ] } ],
    "PostToolUse": [ { "matcher": ".*", "hooks": [ { "type": "command", "command": "<CMD>", "timeout": 5 } ] } ]
  }
}
```

`<CMD>` is generated per OS, exactly as Copilonidal does it:

| OS | `<CMD>` |
|---|---|
| macOS / Linux | `python3 '<data>/antigravalgia.pyz' hook \|\| true` |
| Windows | `& '<python>' '<data>\antigravalgia.pyz' hook; exit 0` (shell unverified — see Hazards) |

**2. `~/.gemini/antigravity-cli/settings.json`**, only with consent and only when `statusLine.command` is unset. Merge into the existing file, never rewrite it whole — the CLI writes this file sparsely and a bad save is destructive (the CLI itself had a bug where an unparsable settings file was overwritten with defaults):

```json
{
  "statusLine": {
    "type": "command",
    "command": "python3 '<data>/antigravalgia.pyz' statusline",
    "enabled": true,
    "stack_with_default": true
  }
}
```

**3. Verification, printed by the installer:**

```sh
agy -p "/hooks" --output-format json      # antigravalgia should be listed
```

## Hazards

| Hazard | Why it matters |
|---|---|
| Exit codes are undocumented | The docs describe stdout JSON decisions but say nothing about exit codes, and `PreToolUse` hooks gate tool execution. Assume fail-closed: keep the `\|\| true` / `; exit 0` wrapper and the shell-level test from Copilonidal that deletes the app and asserts exit 0 |
| Stdout is parsed as a decision | Print **nothing**. A stray word could read as a hook decision. Older builds errored on empty decision strings from pre-tool hooks (fixed in 1.0.15-era releases), so state a minimum version in the README and test `{}` versus empty output |
| `Stop` can force continuation | Returning `continue` would put the agent in a loop. The CLI now caps consecutive continuations, but never emit it |
| The status line script must stay fast and must print | It runs on every agent state change and its stdout *is* the status line. Print one short line, never an error, always exit 0 |
| `~/.gemini/config/hooks.json` is shared | With the Antigravity 2.0 GUI and the `/hooks` command. Merge by key, back up, never rewrite wholesale. The upside: the same hooks may light the icon for GUI sessions too — worth testing |
| `timeout` is in **seconds** | Claude's is seconds, Gemini's is milliseconds, Copilot's is `timeoutSec`. Write `5` |
| Payload field names are new | `conversationId`, `workspacePaths[]`, no `cwd`, no event name field. `hook.py` cannot tell events apart from the payload — **register a different sub-command or argument per event**, e.g. `... hook stop`, `... hook tool`, since there is no `hook_event_name` |
| Sandbox | `agy --sandbox` exists and the status line reports it. Verify hooks still reach the host filesystem and the native host under it |

## Reuse from Copilonidal

| File | For Antigravity |
|---|---|
| `state.py`, `host.py`, `notify.py`, `config.py` | Unchanged apart from names and env vars |
| `paths.py`, `__init__.py`, `cli.py`, `install/system.py` | New app name, data folder, host name, extension ID; add a `statusline` sub-command to `cli.py` |
| `hook.py` | **Rewrite.** No `hook_event_name`, no `cwd`, no `session_id`; the event must come from the command line, and `Stop` must read `fullyIdle` |
| `install/copilot_hooks.py` | Replace with a writer for `~/.gemini/config/hooks.json` (merge by top-level key) plus an optional `settings.json` `statusLine` merge |
| new `statusline.py` | Read the payload, map `agent_state` and `tool_confirmation_pending`, write state, notify on transitions, print one line |
| `extension/` | New `key`, host name, texts, `back-*` icons |
| `tests/` | Keep the real-shell exit-0 test. Add: hooks.json merge keeps other bundles; uninstall removes only `antigravalgia`; settings.json merge preserves unknown keys; status line prints exactly one line and exits 0 on garbage input |

Keep the family rules: a failing hook never blocks the agent, state writes are atomic (`os.replace`), the installer copies everything into a per-user data folder, Python 3.9+ standard library only, macOS/Ubuntu/Windows.

## Not verified yet — test these first

1. Whether hooks run under `agy --sandbox`, and whether they can still write to the data folder. **Test before anything else**; a no here changes the design.
2. Whether `conversationId` (hooks) and `conversation_id` (status line) are the same value.
3. What a `Stop` payload looks like in practice: the values of `terminationReason`, and whether `fullyIdle` is `false` for intermediate stops.
4. Whether Ctrl+C (cancel) fires `Stop` at all.
5. Whether empty stdout is safe on `PreToolUse` in 1.2.7, and what an exit code other than 0 actually does.
6. Whether the status line script runs in headless `-p` mode (expected: no).
7. Whether `~/.gemini/config/hooks.json` is also read by the Antigravity 2.0 GUI and the IDE, which would extend coverage for free.
8. Which shell runs a `command` string on Windows, and whether stdin arrives as UTF-8.
9. What `pending_input_count` counts.
10. Whether `PostInvocation` fires often enough to keep long turns from going stale.

Record the answers in the README under "Not verified yet", the way Copilonidal does.

## Repository and release conventions

Follow what Copilonidal did on 2026-09-19:

- A **private** GitHub repository under `Tpojka`, default branch `main`. Public only when asked — the landing page's GitHub links 404 until then.
- Conventional commits, one per logical unit: `docs: add project brief`, `feat: …`, `test: add unittest suite and CI on macOS, Ubuntu and Windows`, `docs: add README, CHANGELOG and MIT license`, `docs(site): add landing page for antigravalgia.tpojka.com`.
- CI matrix: macOS, Ubuntu, Windows × Python 3.9 and latest. Six green jobs before tagging.
- Tag `v1.0.0`, MIT license, `CHANGELOG.md` in Keep a Changelog form.
- `site/index.html` + `site/index.md` for `antigravalgia.tpojka.com`, matching the sibling pages.

### Hosting the landing page

DigitalOcean droplet **138.68.154.134**, Apache 2.4.52 on Ubuntu, `tpojka.com` DNS on DigitalOcean nameservers, one Let's Encrypt certificate per subdomain (certbot, not wildcard).

1. Dashboard → Networking → Domains → `tpojka.com` → add an **A** record, hostname `antigravalgia`, pointing at the droplet, TTL 3600. No AAAA. Ports 80/443 are already open.
2. On the server: create `/var/www/antigravalgia.tpojka.com`, add a vhost mirroring the existing ones (`sudo apache2ctl -S` lists them) with `DocumentRoot`, `DirectoryIndex index.html`, `AddType text/markdown .md`, `AddCharset utf-8 .html .md`; then `sudo a2ensite antigravalgia.tpojka.com`, `sudo apache2ctl configtest && sudo systemctl reload apache2`.
3. When `dig +short antigravalgia.tpojka.com` returns the droplet IP: `sudo certbot --apache -d antigravalgia.tpojka.com --redirect`.
4. Deploy: `rsync -av --delete site/ <user>@138.68.154.134:/var/www/antigravalgia.tpojka.com/`, then verify with `curl -I` on `/` and `/index.md`.

## Author preferences

- Conventional commits (`feat:`, `fix:`, `docs:`, `docs(site):`, `test:`, `chore(release):` …).
- The user is the sole author. **Never** add a `Co-Authored-By: Claude` trailer to commits, and don't add Claude attribution to PRs.
- Verify claims against primary sources before building on them. This brief is a starting point, not evidence.

## Sources

- Antigravity CLI repository (README, CHANGELOG, examples): https://github.com/google-antigravity/antigravity-cli
- Lifecycle hooks: https://antigravity.google/docs/hooks/
- Status line customization (payload schema, `agent_state`): https://antigravity.google/docs/cli/statusline/
- `/statusline` command: https://antigravity.google/docs/cli/commands/statusline/
- Status line example script: https://github.com/google-antigravity/antigravity-cli/blob/main/examples/statusline/statusline.sh
- Settings: https://antigravity.google/docs/settings/
- CLI overview and reference: https://antigravity.google/docs/cli/overview/ , https://antigravity.google/docs/cli/reference/
- Plugins, skills, subagents, MCP: https://antigravity.google/docs/plugins/ , /docs/skills/ , /docs/subagents/ , /docs/mcp/
