# Changelog

This file records agent assets (skills, subagents) that were removed, and why. Use it to tell a deliberate removal from a lost file before you re-create an asset.

To restore a removed asset, find the commit that deleted it with `git log --diff-filter=D --oneline -- <path>`. Then run `git checkout <commit>^ -- <path>` and `./install.sh`.

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
