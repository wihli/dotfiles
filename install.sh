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

# Clean up ~/.bashrc.d so stow can create its symlink cleanly
if [ -L ~/.bashrc.d ] && [ ! -e ~/.bashrc.d ]; then
    echo "Removing broken .bashrc.d symlink..."
    rm ~/.bashrc.d
elif [ -d ~/.bashrc.d ] && [ ! -L ~/.bashrc.d ]; then
    echo "Removing existing .bashrc.d directory..."
    rm -rf ~/.bashrc.d
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

# Ensure ~/.bashrc sources ~/.bashrc.d/ (works with devcontainer-managed .bashrc)
BASHRC_HOOK='# Source drop-in configs from ~/.bashrc.d/
if [ -d "$HOME/.bashrc.d" ]; then
    for f in "$HOME/.bashrc.d"/*.bash; do
        [ -r "$f" ] && . "$f"
    done
    unset f
fi'
if [ ! -f ~/.bashrc ]; then
    echo "Creating minimal ~/.bashrc..."
    printf '# Minimal bash initialization\n[[ $- != *i* ]] && return\n' > ~/.bashrc
fi
if ! grep -qF '# Source drop-in configs from ~/.bashrc.d/' ~/.bashrc; then
    echo "Adding .bashrc.d sourcing to ~/.bashrc..."
    printf '\n%s\n' "$BASHRC_HOOK" >> ~/.bashrc
fi

# Symlink AGENTS.md to CLAUDE.md for Claude Code
if [ -f ~/.config/AGENTS.md ] && [ ! -e ~/.claude/CLAUDE.md ]; then
    mkdir -p ~/.claude
    ln -sf ~/.config/AGENTS.md ~/.claude/CLAUDE.md
    echo "Symlinked AGENTS.md to ~/.claude/CLAUDE.md"
fi

echo "Done! Symlinks created."
