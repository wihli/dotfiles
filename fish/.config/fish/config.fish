# Fish shell config - consolidated from bash/zsh

# === Git abbreviations ===
abbr gc "git commit"
abbr gcl "git clone"
abbr gp "git push"
abbr gpf "git push --force-with-lease"
abbr gl "git pull"
abbr gd "git diff"
abbr gds "git diff --staged"
abbr glg "git log --oneline"
abbr glp "git log -p"
abbr gco "git checkout"
abbr gpsup "git push --set-upstream origin (git rev-parse --abbrev-ref HEAD)"
abbr grhh "git reset --hard"
abbr gst "git status"
abbr ga "git add"
abbr gaa "git add --all"
abbr gcm "git commit -m"
abbr gsw "git switch"
abbr gswc "git switch -c"
abbr grb "git rebase"
abbr grbi "git rebase -i"

# === Cross-platform clipboard ===
switch (uname)
    case Darwin
        abbr xcp "pbcopy"
        abbr xpaste "pbpaste"
    case '*'
        abbr xcp "xclip -selection clipboard"
        abbr xpaste "xclip -selection clipboard -o"
end

# === Environment ===
set -gx XDG_STATE_HOME $HOME/.local/state
set -gx XDG_CONFIG_HOME $HOME/.config
set -gx XDG_DATA_HOME $HOME/.local/share
set -gx VIRTUALENV_DIR $XDG_STATE_HOME
set -gx EDITOR vim

# === PATH ===
fish_add_path $HOME/.local/bin
fish_add_path $HOME/bin
fish_add_path $HOME/.cargo/bin

# === mise (replaces pyenv/nvm/rbenv) ===
if type -q mise
    mise activate fish | source
end

# === Starship prompt ===
if type -q starship
    starship init fish | source
end

# === fzf ===
if type -q fzf
    # Use fd if available (faster than find, respects .gitignore)
    if type -q fd
        set -gx FZF_DEFAULT_COMMAND 'fd --type f --hidden --follow --exclude .git'
        set -gx FZF_CTRL_T_COMMAND "$FZF_DEFAULT_COMMAND"
        set -gx FZF_ALT_C_COMMAND 'fd --type d --hidden --follow --exclude .git'
    end
    set -gx FZF_DEFAULT_OPTS '--height 40% --layout=reverse --border'
    fzf --fish | source
end

# === SSH agent ===
if status is-interactive
    if not set -q SSH_AUTH_SOCK; and test -z "$SSH_CONNECTION"
        eval (ssh-agent -c) >/dev/null
    end
end

# === Functions ===

# Clone from GitHub via SSH: gshcl owner/repo [dirname]
function gshcl --description "Clone from GitHub via SSH"
    set -l repo $argv[1]
    set -l dir (string split '/' $repo)[-1]
    if test (count $argv) -gt 1
        set dir $argv[2]
    end
    git clone git@github.com:$repo.git $dir
end

# Clone from GitHub via HTTPS: ghhcl owner/repo [dirname]
function ghhcl --description "Clone from GitHub via HTTPS"
    set -l repo $argv[1]
    set -l dir (string split '/' $repo)[-1]
    if test (count $argv) -gt 1
        set dir $argv[2]
    end
    git clone https://github.com/$repo.git $dir
end

# Python virtualenv helpers
function penvn --description "Create new virtualenv"
    python3 -m venv ~/.virtualenvs/$argv[1]
end

function penva --description "Activate virtualenv"
    source ~/.virtualenvs/$argv[1]/bin/activate.fish
end
