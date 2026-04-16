# Work Dotfiles

Public/base dotfiles for Codespaces and work machines. Uses [GNU Stow](https://www.gnu.org/software/stow/) for symlink management and is designed to layer with `~/src/wihli-dotfiles-private`.

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
| `claude` | Claude-specific runtime settings |
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
- Claude-specific config: `claude/.claude/settings.json`
- Shared skills: `skills/.local/share/skills/`
- Shared subagents: `subagents/.local/share/subagents/`
- Private overlays: `~/src/wihli-dotfiles-private/{claude,skills,subagents,...}`

`install.sh` stows the public repo first, overlays the private repo second, then links shared agent assets into the paths Claude and Codex expect.

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
