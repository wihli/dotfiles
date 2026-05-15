# Work Dotfiles

Public/base dotfiles for Codespaces and work machines. Uses [GNU Stow](https://www.gnu.org/software/stow/) for symlink management and is designed to layer with `$SRC_DIR/wihli-dotfiles-private`.

## Quick Install

```bash
git clone git@github.com:wihli/dotfiles.git ~/dotfiles
cd ~/dotfiles
./install.sh
```

## What's Included

| Package | Contents |
|---------|----------|
| `agents` | Shared installed agent instructions (`~/.config/AGENTS.md`) |
| `bash` | .bashrc |
| `bin` | Shared helper commands in `~/.local/bin` |
| `claude` | Claude-specific runtime settings |
| `codex` | Codex-specific runtime hooks |
| `fish` | Fish shell config |
| `git` | .gitconfig |
| `skills` | Shared agent skills in XDG layout |
| `starship` | Prompt config |
| `subagents` | Shared subagents in XDG layout |
| `tmux` | Tmux config |
| `vim` | Vim config |
| `zellij` | Zellij terminal multiplexer |

## Agent Structure

The intended split is:

- Shared instructions: `agents/.config/AGENTS.md`
- Shared helper commands: `bin/.local/bin/`
- Claude-specific config: `claude/.claude/settings.json`
- Codex-specific hooks: `codex/.codex/hooks.json`
- Shared skills: `skills/.local/share/skills/`
- Shared subagents: `subagents/.local/share/subagents/`
- Private overlays: `$SRC_DIR/wihli-dotfiles-private/{claude,skills,subagents,...}`

Treat repo paths as the source of truth. Installed home paths such as
`~/.config/AGENTS.md`, `~/.local/share/skills/`, `~/.local/share/subagents/`,
`~/.claude/skills/`, `~/.claude/agents/`, and `~/.codex/skills/` are generated
targets managed by `install.sh` and Stow, not places to edit shared assets.

`install.sh` stows the public repo first, overlays the private repo second, then links shared agent assets into the paths Claude and Codex expect.

If `stow` reports a conflict for a shared skill or subagent, that usually means
someone wrote a real file into one of those managed home paths. Move the change
back into the repo source under `skills/.local/share/...` or
`subagents/.local/share/...`, remove the unmanaged home-path file, then rerun
`./install.sh`.

## Codespaces Setup

Add to your Codespaces settings in GitHub:
- Repository: `wihli/dotfiles`
- Target: `~/dotfiles`

Or in devcontainer.json:
```json
{
  "dotfiles": {
    "repository": "wihli/dotfiles",
    "installCommand": "./install.sh"
  }
}
```

## Manual Stow

```bash
# Install single package
stow -t ~ bash

# Uninstall
stow -D -t ~ bash
```
