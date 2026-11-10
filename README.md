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
| `agents` | Shared instructions for Claude Code, Codex, and Pi |
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

- Shared instructions: `agents/.config/AGENTS.md`, installed at `~/.config/AGENTS.md`
- Shared helper commands: `bin/.local/bin/`
- Claude-specific config: `claude/.claude/settings.json`
- Codex-specific hooks: `codex/.codex/hooks.json`
- Pi-specific user settings and global extensions: `$SRC_DIR/wihli-dotfiles-private/pi/.pi/agent/`
- Shared skills: `skills/.local/share/skills/`
- Shared subagents: `subagents/.local/share/subagents/`
- Private overlays: `$SRC_DIR/wihli-dotfiles-private/{claude,codex,pi,skills,subagents,...}`

Treat repo paths as the source of truth. Installed home paths such as
`~/.config/AGENTS.md`, `~/.local/share/skills/`, `~/.local/share/subagents/`,
`~/.claude/skills/`, `~/.claude/agents/`, `~/.agents/skills/`, and
`~/.codex/skills/` are generated targets managed by `install.sh` and Stow.
Pi reads the generated `~/.pi/agent/AGENTS.md` link.
Private Pi settings and extensions under `~/.pi/agent/` are managed the same way.
Do not edit these installed paths.

Agent status and permission requests stay in the terminal. The shared configuration
does not install desktop notification hooks or delayed tmux pane-title updates.

`install.sh` stows the public repo first, overlays the private repo second,
merges private Claude settings and Codex hook fragments into their public base
files, stows private Pi extensions, then links shared agent assets into the paths
Claude, Codex, and Pi expect.
With the overlay present, it also points this repo's `core.hooksPath` at the
overlay's `hooks/` directory, whose pre-push hook reviews each push of this
public repo for private information.
Pi and OpenCode discover those same shared skills through the shared Agent Skills
path at `~/.agents/skills/`.

Private Codex skill choices live in `codex/skill-preferences.toml`. The installer
uses Python 3.11 or newer to validate these choices and replace its marked section
in `~/.codex/config.toml`, preserving other settings. Set a skill entry to
`enabled = true` or remove it from the source to end an exclusion, then reinstall
and start a fresh Codex session. Synced skill files stay owned by their provider.

Skill directories and supporting files keep the Stow-managed overlay layout.
After both overlays are installed, `install.sh` replaces only dotfiles-owned
`SKILL.md` links with generated regular files so Codex can discover them. An
ownership marker lets later installs regenerate or remove those manifests
without touching skills installed by other tools.

If `stow` reports a conflict for a shared skill or subagent, that usually means
someone wrote a real file into one of those managed home paths. Move the change
back into the repo source under `skills/.local/share/...` or
`subagents/.local/share/...`, remove the unmanaged home-path file, then rerun
`./install.sh`.

The installer also removes broken `~/.local/bin` symlinks that still point into
this public repo, allowing a command to move cleanly into the private overlay.
It also prunes broken links and empty nested directories left by deleted shared
skills. Python `__pycache__` directories are ignored by Stow.

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
