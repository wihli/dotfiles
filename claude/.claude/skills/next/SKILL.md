---
name: next
description: |
  Resume work on a project - discover state, verify health, clean up stale docs, suggest next tasks.
  Use when: (1) starting work at beginning of day, (2) after a long agent work loop completes,
  (3) user asks "what's next?", "what should we work on?", or similar,
  (4) user explicitly runs /next.
---

# Next: Project Resume Workflow

## 1. Gather Context

Read project planning files (if they exist):
- `README.md` - human-centric overview
- `PLAN.md` - agent-centric plan, status, future work
- `SPEC.md` - detailed specifications
- `TODO.md` - immediate tasks

Also check git status for uncommitted work or in-progress branches.

## 2. Discover & Run Verification

Find verification commands from (in priority order):
1. `README.md` - look for "Verification", "Development", "Quick Start" sections
2. `pyproject.toml` - scripts section, or infer from dependencies (pytest, mypy, ruff)
3. `Makefile` - check, test, lint targets
4. `package.json` - scripts section

Run discovered commands (typically: types, lint, tests). Note failures.

## 3. Clean Up Planning Docs

**Auto-fix** (no confirmation needed):
- Test counts that don't match actual (`N tests passing` → update N)
- Completed items still listed as in-progress
- Duplicate entries

**Ask user** about:
- Items marked "in progress" that appear stale
- Future work items that may now be done
- Sections that seem outdated but require judgment

## 4. Summarize & Present Options

Output a brief summary:
```
## Project State
- Health: [tests/types/lint status]
- Current: [what's in progress or recently completed]
- Cleaned: [what was auto-fixed in docs]

## Next Options
1. [Most impactful/logical next task]
2. [Alternative direction]
3. [Another option if applicable]
```

Wait for user to choose direction before proceeding.
