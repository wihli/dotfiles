function grid-4x2 --description "Split current zellij tab into a 4x2 grid"
    # 4 equal columns: split in half, then split each half
    zellij action new-pane --direction right
    zellij action move-focus left
    zellij action new-pane --direction right
    zellij action move-focus right
    zellij action new-pane --direction right

    # Split each column top/bottom, moving right to left
    zellij action new-pane --direction down
    zellij action move-focus up
    zellij action move-focus left
    zellij action new-pane --direction down
    zellij action move-focus up
    zellij action move-focus left
    zellij action new-pane --direction down
    zellij action move-focus up
    zellij action move-focus left
    zellij action new-pane --direction down
end
