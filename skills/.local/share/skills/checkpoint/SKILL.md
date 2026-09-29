---
name: checkpoint
description: |
  Save/load session state for clean context recovery.
  Triggers: "/checkpoint save [name]", "/checkpoint load [query]", "/checkpoint list"
---

# Checkpoint

Keep a short progress summary alongside the source material needed to resume accurately.

## Preserve useful source material

- Select task-specific constraints and decisions whose wording could affect the next action. Preserve their exact wording, source, and scope. Distinguish requirements from preferences and hypotheses.
- Keep decisive commands and short output excerpts, with enough context to interpret them and a path or link to the original record. Exclude secrets.
- Build updates from original messages, files, and tool output. Carry retained quotations forward unchanged instead of summarizing an earlier summary. If only a prior summary remains, label it as unverified rather than reconstructing a quotation.
- Use judgment to keep the checkpoint small. Include the details below when they help recovery; omit empty sections.

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
- Checkout: <branch, HEAD, and relevant uncommitted changes>

## Constraints and Scope
- <exact wording; original message or source; when it applies; later amendments>

## Decisive Evidence
- Check: <command, working directory, and environment>
- Tested state: <time, revision, and relevant uncommitted changes at execution>
- Result: <exit status and short verbatim output excerpt>
- Original record: <path or link; note if unavailable>

## Key Decisions
- <decisions and rationale>

## Gotchas
- <pitfalls discovered>

## Recheck on Resume
- <facts that depend on the checkout, environment, or live state>

## Next Steps
- <what to do when resuming>
```
5. Confirm: "Saved: <filepath>"

### `/checkpoint load <query>`
Find and load checkpoint matching query.

1. Search `~/.local/state/claude/checkpoints/` for files matching query
2. If multiple matches, show list and ask which one
3. Read the checkpoint and current project instructions. Follow its source pointers where needed.
4. Compare the checkout and environment with the recorded state. Refresh evidence affected by changes before relying on it.
5. Summarize to user: "Loaded checkpoint from <date>. Goal was: <goal>. Next steps: <next>"

### `/checkpoint load` (no query)
Load most recent checkpoint.

### `/checkpoint list`
List recent checkpoints (last 10, newest first).

### `/checkpoint` (no args)
Default to `save` with auto-generated name.
