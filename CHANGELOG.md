# Changelog

This file records agent assets (skills, subagents) that were removed, and why. Use it to tell a deliberate removal from a lost file before you re-create an asset.

To restore a removed asset, find the commit that deleted it with `git log --diff-filter=D --oneline -- <path>`. Then run `git checkout <commit>^ -- <path>` and `./install.sh`.

## 2026-11-09: Remove the Codex recap hook and the Claude formatter hook

Removed `bin/.local/bin/codex-recap`, its test, and the Codex `UserPromptSubmit` hook that ran it when the prompt was exactly `recap`. Codex 0.167 generates recaps itself (`/recap`, plus automatic recaps for an idle thread), and the prompt history shows eight uses between late August and late September, none since. `codex/.codex/hooks.json` stays as an empty hook set because `install.sh` merges the private hook groups into it.

Removed Claude's `PostToolUse` formatter hook from `claude/.claude/settings.json`. It ran `ruff`, `black` or `prettier` on edited files, and none of them is installed on this machine, so it had never formatted anything since it was added on 2026-04-16. Reinstall with `./install.sh`; it drops the stale `codex-recap` symlink and regenerates the merged hook files.

## 2026-11-09: Move the pre-push privacy review to the private overlay

`hooks/pre-push` now lives at `$SRC_DIR/wihli-dotfiles-private/hooks/pre-push`. It still guards pushes of this public repo: `install.sh` points this repo's `core.hooksPath` at the overlay's `hooks/` directory when the overlay is present. The review prompt describes what counts as private, which belongs with the other work-specific material in the overlay.

## 2026-11-06: Retire agent desktop notifications and delayed pane titles

Removed `agent-notify-ready`, its dedicated tests, its Claude and Codex Stop/UserPromptSubmit hooks, and Claude's desktop Notification hook. Routine ready/idle banners and sounds were not useful. Concurrent background workers also raced on shared pane state, making delayed title jobs fail and repeatedly open tmux's message viewer.

Agent status and permission requests remain in the terminal. Keep the existing permission guards and Codex recap hook. Reinstall with `./install.sh`; it removes the retired helper's stale symlink, so cached ready-hook commands in running sessions become harmless.

## 2026-11-03: Trial removal of generic completion and pickup skills

Removed `skills/.local/share/skills/finalize/` and `skills/.local/share/skills/next/` as a reversible trial. Both wrapped ordinary agent work. Finalize also prescribed staging every change, and next prescribed checks and planning-document edits for status questions. The audit found frequent loads, but did not establish that either skill improved outcomes.

Keep normal completion and resumption work in the agent's task and repository instructions. Git history preserves both skills for restoration if the trial exposes a useful missing behavior.

Narrowed `long-session` to explicitly requested Ralph-loop preparation, kept `north-star` explicitly selected, and changed `session-notes` to use existing project handoffs. Global instructions retain lasting preferences and constraints; task-specific writing and review procedures live in references.

## 2026-10-14: Retired deliberate-review

Removed the `deliberate-review` skill, its CLI adapter, and its dedicated tests. The skill opened and supervised persistent Deliberate PR reviews. Eric retired this workflow after the usage audit found no skill loads from September 14 through October 13. THABTO and the background PR review loop cover the active review workflows.

## 2026-10-07: Removed unused skills and subagents

A usage audit read the Claude Code transcripts (from 2026-08-13) and the Codex transcripts (from 2026-08-08). No session in that period loaded the assets below. Every installed skill and subagent puts its description into the context of each session, so an unused asset costs tokens and gives nothing back.

| Asset | Type | Purpose |
|---|---|---|
| `title` | skill | Set the terminal or Zellij pane title to a two-word summary |
| `mcp-builder` | skill | Guide for building MCP servers in Python or TypeScript |
| `debug` | subagent | Take a bug through reproduction, a test-first fix, and verification |
| `code-simplifier` | subagent | Reduce repetition in code that already works |
| `reviewer-contradiction` | subagent | Find two places in a codebase that disagree about the same fact |
| `reviewer-logging` | subagent | Review log levels, structure, and sensitive values |
| `verify-app` | subagent | Run the full lint, type, and test gate |

The subagent counts come from Claude Code sessions only, because Codex reads no subagent files. `code-reviewer` stays because one session used it.

To repeat the audit, run `$SRC_DIR/centcom/scripts/agent-skill-usage.py`.
