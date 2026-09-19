# Claude session kit

A small kit for long Claude Code sessions. It has two parts:

- **A Claude Code plugin, `kit`**, with the handoff skill and two hooks. The skill moves the work of a long session to a fresh one through a short note. One hook records the token, cache and cost figures of each session. The other says, on each prompt above a line, that it is time for the handoff.
- **A VS Code extension, the Claude usage bar**, that shows those figures for every live session on the machine in the status bar, with a details pane.

Install both once on a machine, and they work in every project there.

## Why

Every step of a Claude Code session re-reads the whole session, so a long session costs more for each step. At 500,000 tokens of context the kit says the same three steps in four places: run `/kit:handoff`, then `/clear`, then say "continue from handoff <topic>".

- The status bar item turns to the warning color, and its hover adds the three steps.
- The extension shows one notification for the session, with a button that opens the pane. The notification comes once at the warning line and once more at the alert line, 750,000 by default.
- The pane's context meter says the three steps under the bar.
- On the next prompt, the nudge hook shows the user the size with the three steps, and tells Claude to suggest them when the request starts a new task.

The skill writes a note of at most 40 lines to `.claude/handoffs/<topic>.md` in the project. The fresh session reads that note in place of the old conversation.

## Install

The plugin, in a Claude Code session:

```
/plugin marketplace add nandyalu/claude-session-kit
/plugin install kit@nandyalu
```

Or from the terminal:

```sh
claude plugin marketplace add nandyalu/claude-session-kit
claude plugin install kit@nandyalu
```

The extension, from the latest release:

```sh
gh release download --repo nandyalu/claude-session-kit --pattern claude-usage-bar.vsix -D /tmp
code --install-extension /tmp/claude-usage-bar.vsix
```

Then run **Developer: Reload Window** in VS Code, and start a new Claude Code session. Over Remote-SSH, run all of this on the remote host: the extension host, the hooks and Claude Code all run there. The hooks need `python3` on the machine.

To update the plugin, run `claude plugin update kit@nandyalu`, or turn on auto-update for the marketplace under `/plugin`. To update the extension, repeat the two extension commands for the new release.

## What is in it

| Path | What it is |
|---|---|
| `.claude-plugin/plugin.json` | The plugin manifest |
| `.claude-plugin/marketplace.json` | The marketplace list, with this one plugin |
| `skills/handoff/SKILL.md` | The handoff skill, `/kit:handoff` in a session |
| `hooks/hooks.json` | Registers the two hooks |
| `hooks/session-usage.py` | Writes the figures of each session to `~/.claude/usage/` |
| `hooks/context-nudge.py` | Reports a large session on each prompt |
| `vscode/` | The Claude usage bar extension |
| `.github/workflows/release.yml` | Builds the `.vsix` on a `v*` tag and puts it on the release |

## How it works

1. `session-usage.py` runs after each tool call, at the end of each turn, and when a session ends. It reads the new lines of the session transcript and writes the totals to `~/.claude/usage/<session_id>.json`, with the project directory of the session. When `CLAUDE_CONFIG_DIR` is set, the folder is `usage/` under that directory instead. Main-thread requests and subagent requests are counted apart. A `SessionEnd` event marks the file ended.
2. [graft](https://github.com/nandyalu/graft), when a project uses it, writes its own figures, the tokens it saved and its estimate of the input cost, to `graft/.cache/session/<session_id>.json` inside the project. A project without graft shows no graft figures and no cost.
3. The extension reads the usage folder, and for each session graft's file in that session's project. It shows every session that is not ended and was written in the last 24 hours. It refreshes when a usage file changes, when a graft file in this window changes, and every 30 seconds.
4. `context-nudge.py` runs on each prompt. It reads the last context size from the transcript. Above `CONTEXT_NUDGE_TOKENS`, 500,000 by default, it prints one line for the user and one instruction for Claude.
5. The plugin's `hooks/hooks.json` registers both hooks, so they merge with the hooks in `~/.claude/settings.json` and nothing there needs to change.

## Settings

| Setting | Default | What it does |
|---|---|---|
| `claudeUsageBar.warnTokens` | 500000 | The context size at which the status bar item turns to the warning color |
| `claudeUsageBar.alertTokens` | 750000 | The context size at which it turns to the error color |
| `CONTEXT_NUDGE_TOKENS` | 500000 | The line above which the nudge hook speaks. Set it in the `env` block of `~/.claude/settings.json`, and keep it equal to `warnTokens` so the bar and the prompt agree. |

## Release

1. Set the same version in `.claude-plugin/plugin.json` and `vscode/package.json`.
2. Commit, then tag and push the tag: `git tag v1.0.1 && git push origin main --tags`.
3. The workflow builds `claude-usage-bar.vsix` and creates the release. The plugin needs no build. A machine gets the new plugin version at its next `claude plugin update`.

## Develop

Run Claude Code with the checkout as the plugin, without an install: `claude --plugin-dir /path/to/claude-session-kit`. To try the extension, run `npx --yes @vscode/vsce package -o /tmp/claude-usage-bar.vsix` in `vscode/`, then `code --install-extension /tmp/claude-usage-bar.vsix`.

## Limits

- The usage hook cannot see the `prompt_cache` object of Claude Code's status line, so the pane does not show cache misses or their causes. Run `/usage` in the panel to see those.
- The input cost is graft's estimate, not a bill.
- A session that ends without a `SessionEnd` event, such as a killed process, stays in the list for up to 24 hours. The hook deletes a usage file that is older than seven days.
- Every window sees every session on the machine. The order and the bold folder names say which ones belong to this window.
- The notification names the session and its folder, not the panel it runs in. With two panels in one window, open the pane to see which session is large.
