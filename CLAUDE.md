# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a dotfiles repository using GNU Stow for symlink management. It contains configuration files for various development tools that are deployed to user's home directory via symlinks.

## Key Commands

### Installation
```bash
./install.sh  # Auto-installs stow, removes existing .bashrc, installs delta, stows all packages
```

### Manual Stow Operations
```bash
stow -t ~ <package>        # Install single package
stow -D -t ~ <package>     # Uninstall package
```

## Repository Structure

Packages managed via Stow:
- `agents/` - Contains AGENTS.md with Claude Code instructions (symlinked to ~/.claude/CLAUDE.md)
- `bash/` - Bash configuration (.bashrc)
- `claude/` - Claude Code settings (settings.local.json)
- `fish/` - Fish shell configuration
- `git/` - Git configuration (.gitconfig)
- `starship/` - Prompt configuration (starship.toml)
- `tmux/` - Tmux configuration
- `zellij/` - Zellij terminal multiplexer config

## Important Notes

1. **AGENTS.md Integration**: The `agents/.config/AGENTS.md` file contains detailed coding guidelines and is automatically symlinked to `~/.claude/CLAUDE.md` by the install script.

2. **Codespaces Support**: This repository is designed to work with GitHub Codespaces. The install script handles removing existing .bashrc to prevent conflicts.

3. **Delta Installation**: On Linux systems, the install script automatically installs git-delta for enhanced diff viewing.

4. **Stow Target**: All packages are stowed to the home directory (`~`) as the target.

## Development Workflow

When modifying dotfiles:
1. Edit files within their package directories (e.g., `bash/.bashrc`)
2. Changes take effect immediately due to symlinks
3. Test changes before committing
4. Keep each package self-contained