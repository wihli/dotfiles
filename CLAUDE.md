# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a dotfiles repository using GNU Stow for symlink management. It contains configuration files for various development tools that are deployed to user's home directory via symlinks.

## Key Commands

### Installation
```bash
./install.sh  # Auto-installs stow, installs delta, stows all packages, hooks bash into .bashrc
```

### Manual Stow Operations
```bash
stow -t ~ <package>        # Install single package
stow -D -t ~ <package>     # Uninstall package
```

## Repository Structure

Packages managed via Stow:
- `agents/` - Contains AGENTS.md with Claude Code instructions (symlinked to ~/.claude/CLAUDE.md)
- `bash/` - Bash configuration (drop-in via `~/.bashrc.d/dotfiles.bash`)
- `claude/` - Claude Code settings (settings.local.json)
- `fish/` - Fish shell configuration
- `git/` - Git configuration (.gitconfig)
- `starship/` - Prompt configuration (starship.toml)
- `tmux/` - Tmux configuration
- `zellij/` - Zellij terminal multiplexer config

## Important Notes

1. **AGENTS.md Integration**: The `agents/.config/AGENTS.md` file contains detailed coding guidelines and is automatically symlinked to `~/.claude/CLAUDE.md` by the install script.

2. **Devcontainer/Codespaces Support**: Bash config uses a `.bashrc.d/` drop-in pattern so it coexists with container-managed `~/.bashrc`. The install script appends a sourcing hook to `~/.bashrc` rather than replacing it.

3. **Delta Installation**: On Linux systems, the install script automatically installs git-delta for enhanced diff viewing.

4. **Stow Target**: All packages are stowed to the home directory (`~`) as the target.

## Development Workflow

When modifying dotfiles:
1. Edit files within their package directories (e.g., `bash/.bashrc.d/dotfiles.bash`)
2. Changes take effect immediately due to symlinks
3. Test changes before committing
4. Keep each package self-contained