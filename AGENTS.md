# AGENTS.md

Shared repo instructions for coding agents working on this dotfiles repo.

## Purpose

This repo is the public/base layer of a two-repo dotfiles setup:

- `$SRC_DIR/wihli-dotfiles` is the public base
- `$SRC_DIR/wihli-dotfiles-private` is the private overlay

The install flow stows the public repo first, then overlays private packages when present.

## Multi-Agent Layout

- Shared installed agent instructions live at `agents/.config/AGENTS.md`
- Shared helper commands live under `bin/.local/bin/`
- Claude-specific runtime config lives under `claude/.claude/`
- Codex-specific runtime hooks live under `codex/.codex/`
- Shared skills live under `skills/.local/share/skills/`
- Shared subagents live under `subagents/.local/share/subagents/`
- Private-only Claude config, skills, and subagents live in the private repo
- Installed home paths under `~/.config/`, `~/.local/share/`, `~/.claude/`, and `~/.codex/` are generated targets, not source-of-truth edit locations

Keep shared behavior in the shared XDG-style locations above. Keep tool-specific behavior in the tool-specific package only.

## Editing Rules

- Prefer changing the public repo when guidance or assets are safe to share
- Put secrets, work-only permissions, and company-specific operational knowledge in the private repo
- Do not duplicate shared instructions between `AGENTS.md` and `CLAUDE.md`
- Keep stow package layouts aligned with their final target paths under `$HOME`
- For shared skills and subagents, edit the repo source under `skills/.local/share/...` or `subagents/.local/share/...`, never the installed targets under `~/.local/share/`, `~/.claude/`, or `~/.codex/`
- Do not edit generated install outputs directly: `~/.config/AGENTS.md`, `~/.config/AGENTS.private.md`, `~/.claude/CLAUDE.md`, `~/.claude/settings.json`, `~/.claude/skills/`, `~/.claude/agents/`, `~/.codex/AGENTS.md`, `~/.codex/skills/`
- After changing shared agent assets, rerun `cd $SRC_DIR/wihli-dotfiles && ./install.sh`
- If `stow` reports a conflict in a managed target, treat it as an unmanaged file in `$HOME`; move the source back into the repo package instead of editing the home-path copy
- If you change install behavior, update `README.md` and any repo-local agent docs in the same change

## Validation

When changing agent-related layout, verify:

1. `install.sh` still reflects the documented source-of-truth layout
2. Public/private overlay order is still correct
3. Shared docs describe Codex and Claude accurately
4. New skills/subagents include valid front matter
