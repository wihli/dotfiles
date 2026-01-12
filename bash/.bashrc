# Minimal bash config - fallback when fish unavailable
# Mirror of fish config for consistency across machines

# Exit if non-interactive
[[ $- != *i* ]] && return

# === History ===
HISTCONTROL=ignoreboth
HISTSIZE=50000
HISTFILESIZE=100000
shopt -s histappend

# === XDG ===
export XDG_CONFIG_HOME="$HOME/.config"
export XDG_DATA_HOME="$HOME/.local/share"
export XDG_STATE_HOME="$HOME/.local/state"
export XDG_CACHE_HOME="$HOME/.cache"

# === Environment ===
export EDITOR=vim

# === PATH (platform-aware) ===
export PATH="$HOME/.local/bin:$HOME/bin:$HOME/.cargo/bin:$PATH"
case "$(uname)" in
    Darwin)
        # Homebrew (Apple Silicon then Intel) + MacPorts
        [ -d /opt/homebrew/bin ] && export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:$PATH"
        [ -d /usr/local/bin ] && export PATH="/usr/local/bin:/usr/local/sbin:$PATH"
        [ -d /opt/local/bin ] && export PATH="/opt/local/bin:/opt/local/sbin:$PATH"
        ;;
esac

# === Git aliases ===
alias gc='git commit'
alias gp='git push'
alias gpf='git push --force-with-lease'
alias gl='git pull'
alias gd='git diff'
alias gds='git diff --staged'
alias glg='git log --oneline'
alias gco='git checkout'
alias gst='git status'
alias ga='git add'
alias gaa='git add --all'
alias gcm='git commit -m'
alias gsw='git switch'
alias gswc='git switch -c'
alias grb='git rebase'

# === Prompt (colored, with git branch) ===
parse_git_branch() {
    git branch 2>/dev/null | sed -e '/^[^*]/d' -e 's/* \(.*\)/ (\1)/'
}
PS1='\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[33m\]$(parse_git_branch)\[\033[00m\]\$ '

# === ls aliases ===
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'
alias ls='ls --color=auto'
alias ll='ls -alF --color=auto'
alias la='ls -A --color=auto'
alias l='ls -CF --color=auto'

# === grep colors ===
alias grep='grep --color=auto'
alias fgrep='fgrep --color=auto'
alias egrep='egrep --color=auto'

# === Cross-platform clipboard ===
case "$(uname)" in
    Darwin) alias xcp='pbcopy'; alias xpaste='pbpaste' ;;
    *)      alias xcp='xclip -selection clipboard'; alias xpaste='xclip -selection clipboard -o' ;;
esac

# === Tools (if available) ===
command -v mise &>/dev/null && eval "$(mise activate bash)"
command -v starship &>/dev/null && eval "$(starship init bash)"
# fzf: use --bash for 0.48+, otherwise source scripts directly
if command -v fzf &>/dev/null; then
    fzf_version=$(fzf --version | cut -d' ' -f1)
    if [[ "$(printf '%s\n' "0.48" "$fzf_version" | sort -V | head -n1)" == "0.48" ]]; then
        eval "$(fzf --bash)"
    else
        [ -f /usr/share/doc/fzf/examples/key-bindings.bash ] && source /usr/share/doc/fzf/examples/key-bindings.bash
        [ -f /usr/share/doc/fzf/examples/completion.bash ] && source /usr/share/doc/fzf/examples/completion.bash
    fi
fi

# === fzf with fd ===
if command -v fd &>/dev/null; then
    export FZF_DEFAULT_COMMAND='fd --type f --hidden --follow --exclude .git'
    export FZF_CTRL_T_COMMAND="$FZF_DEFAULT_COMMAND"
    export FZF_ALT_C_COMMAND='fd --type d --hidden --follow --exclude .git'
fi
export FZF_DEFAULT_OPTS='--height 40% --layout=reverse --border'

# === zoxide (smart cd) ===
command -v zoxide &>/dev/null && eval "$(zoxide init bash)"

# === bat (better cat) ===
command -v bat &>/dev/null && alias cat='bat'

# === Bash completion ===
if ! shopt -oq posix; then
    if [ -f /usr/share/bash-completion/bash_completion ]; then
        . /usr/share/bash-completion/bash_completion
    elif [ -f /etc/bash_completion ]; then
        . /etc/bash_completion
    fi
fi

# === Nix (for codespaces) ===
if [ "${PATH#*$HOME/.nix-profile/bin}" = "${PATH}" ]; then
    [ -z "$USER" ] && USER=$(whoami)
    [ -f "$HOME/.nix-profile/etc/profile.d/nix.sh" ] && . "$HOME/.nix-profile/etc/profile.d/nix.sh"
fi
