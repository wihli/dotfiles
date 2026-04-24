# Auto-start tmux on interactive login shells.
# Skip when already inside tmux, inside an IDE terminal, or in a non-interactive context.
if status is-interactive
    and not set -q TMUX
    and not set -q VSCODE_RESOLVING_ENVIRONMENT
    and not set -q INTELLIJ_ENVIRONMENT_READER
    and command -q tmux
    exec tmux new-session -A -s main
end
