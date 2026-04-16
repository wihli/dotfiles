# AGENTS.md

Shared repo instructions for coding agents working on this dotfiles repo.

## Purpose

This repo is the public/base layer of a two-repo dotfiles setup:

- `~/src/wihli-dotfiles` is the public base
- `~/src/wihli-dotfiles-private` is the private overlay

The install flow stows the public repo first, then overlays private packages when present.

## Multi-Agent Layout

- Shared installed agent instructions live at `agents/.config/AGENTS.md`
- Claude-specific runtime config lives under `claude/.claude/`
- Shared skills live under `skills/.local/share/skills/`
- Shared subagents live under `subagents/.local/share/subagents/`
- Private-only Claude config, skills, and subagents live in the private repo

Keep shared behavior in the shared XDG-style locations above. Keep tool-specific behavior in the tool-specific package only.

## Editing Rules

- Prefer changing the public repo when guidance or assets are safe to share
- Put secrets, work-only permissions, and company-specific operational knowledge in the private repo
- Do not duplicate shared instructions between `AGENTS.md` and `CLAUDE.md`
- Keep stow package layouts aligned with their final target paths under `$HOME`
- If you change install behavior, update `README.md` and any repo-local agent docs in the same change

## Validation

When changing agent-related layout, verify:

1. `install.sh` still reflects the documented source-of-truth layout
2. Public/private overlay order is still correct
3. Shared docs describe Codex and Claude accurately
4. New skills/subagents include valid front matter
