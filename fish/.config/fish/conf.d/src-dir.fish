# Default source directory for all repos.
# Override per-machine with: set -Ux SRC_DIR ~/whatever
if not set -q SRC_DIR
    set -gx SRC_DIR $HOME/src
end
