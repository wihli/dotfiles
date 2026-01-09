# Work Dotfiles (Vanta)

Dotfiles for Codespaces and work machines. Uses [GNU Stow](https://www.gnu.org/software/stow/) for symlink management.

## Quick Install

```bash
git clone https://github.com/eihli/wihli-dotfiles ~/dotfiles
cd ~/dotfiles
./install.sh
```

## What's Included

| Package | Contents |
|---------|----------|
| `agents` | AGENTS.md - Claude Code instructions |
| `bash` | .bashrc |
| `claude` | Settings, skills, agents for Claude Code |
| `fish` | Fish shell config |
| `git` | .gitconfig (work email) |
| `starship` | Prompt config |
| `tmux` | Tmux config |
| `zellij` | Zellij terminal multiplexer |

## Codespaces Setup

Add to your Codespaces settings in GitHub:
- Repository: `eihli/wihli-dotfiles`
- Target: `~/dotfiles`

Or in devcontainer.json:
```json
{
  "dotfiles": {
    "repository": "eihli/wihli-dotfiles",
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
