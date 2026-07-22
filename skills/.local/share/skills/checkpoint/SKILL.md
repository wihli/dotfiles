---
name: checkpoint
description: |
  Save/load session state for clean context recovery.
  Triggers: "/checkpoint save [name]", "/checkpoint load <query>", "/checkpoint list"
---

# Checkpoint

Capture and restore working state to prevent context pollution.

## Commands

### `/checkpoint save [name]`
Save current state. Name optional (auto-generates if omitted).
Suggest checkpointing when context is growing large or before risky changes.

1. Generate or use provided name (kebab-case, 2-3 words)
2. Ensure dir exists: `mkdir -p ~/.local/state/claude/checkpoints`
3. Create `~/.local/state/claude/checkpoints/<name>-<YYYYMMDD-HHMM>.md`
4. Write:
```
# Checkpoint: <name>
Date: <timestamp>
CWD: <pwd>

## Goal
<1-2 sentence summary>

## Current State
- <what's working/tested>
- <files changed>
- Diff stat: <output of `git diff --stat`>
- Last green commit: <SHA where tests last passed>

## Key Decisions
- <decisions and rationale>

## Gotchas
- <pitfalls discovered>

## Next Steps
- <what to do when resuming>
```
5. Confirm: "Saved: <filepath>"

### `/checkpoint load <query>`
Find and load checkpoint matching query.

1. Search `~/.local/state/claude/checkpoints/` for files matching query
2. If multiple matches, show list and ask which one
3. Read file contents
4. Summarize to user: "Loaded checkpoint from <date>. Goal was: <goal>. Next steps: <next>"

### `/checkpoint load` (no query)
Load most recent checkpoint.

### `/checkpoint list`
List recent checkpoints (last 10, newest first).

### `/checkpoint` (no args)
Default to `save` with auto-generated name.
