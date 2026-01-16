#!/bin/bash
# Install dotfiles via stow
# Run from the dotfiles directory

set -e
cd "$(dirname "$0")"

# Install stow if missing
if ! command -v stow &> /dev/null; then
    echo "Installing stow..."
    if command -v apt &> /dev/null; then
        sudo apt install -y stow
    elif command -v brew &> /dev/null; then
        brew install stow
    else
        echo "Please install stow manually"
        exit 1
    fi
fi

# Remove existing .bashrc to allow stow overwrite (common in codespaces)
if [ -f ~/.bashrc ] && [ ! -L ~/.bashrc ]; then
    echo "Removing existing .bashrc..."
    rm ~/.bashrc
fi

# Install git-delta on Linux
if [[ "$(uname)" == "Linux" ]] && ! command -v delta &> /dev/null; then
    echo "Installing git-delta..."
    DELTA_VERSION="0.18.2"
    curl -sLO "https://github.com/dandavison/delta/releases/download/${DELTA_VERSION}/git-delta_${DELTA_VERSION}_amd64.deb"
    sudo dpkg -i "git-delta_${DELTA_VERSION}_amd64.deb"
    rm "git-delta_${DELTA_VERSION}_amd64.deb"
fi

# Stow all packages
for pkg in claude agents bash fish git starship tmux vim zellij; do
    echo "Stowing $pkg..."
    stow -t ~ "$pkg"
done

# Symlink AGENTS.md to CLAUDE.md for Claude Code
if [ -f ~/.config/AGENTS.md ] && [ ! -e ~/.claude/CLAUDE.md ]; then
    mkdir -p ~/.claude
    ln -sf ~/.config/AGENTS.md ~/.claude/CLAUDE.md
    echo "Symlinked AGENTS.md to ~/.claude/CLAUDE.md"
fi

echo "Done! Symlinks created."
