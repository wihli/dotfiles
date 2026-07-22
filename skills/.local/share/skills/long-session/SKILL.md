---
name: long-session
description: |
  Prep workflow before autonomous ralph-wiggum loops.
  Use when: (1) starting overnight/long autonomous runs,
  (2) user says "long session", "overnight", "autonomous",
  (3) work will span multiple sessions without user interaction.
---

# Long Session: Ralph Loop Prep

Structured prep before entering autonomous loop. Each phase requires user confirmation.

## Phase 1: Explore

Understand the codebase before planning.

```
- Read README, CLAUDE.md, project structure
- Identify tech stack, patterns, conventions
- Find existing tests and how they run
- Summarize findings to user (keep brief)
```

## Phase 2: Goals

Ask user what they want built.

```
Questions to ask:
- What feature(s) should this session produce?
- Any constraints or requirements?
- What does "done" look like?
- How long can this run unattended? (set --max-iterations)
```

Create/update `features.json`:
```json
{
  "features": [
    {"id": 1, "name": "feature name", "done_when": "criteria", "tests": []}
  ],
  "max_iterations": 50
}
```

## Phase 3: Plan

Design implementation approach.

```
For each feature:
- Files to create/modify
- Dependencies or prerequisites
- Risks or unknowns
- Order of implementation
```

Present plan to user. Do NOT proceed without explicit approval.

## Phase 4: Write Tests

TDD: tests define "done" for the ralph loop.

```
- Write failing tests that capture each feature's acceptance criteria
- Tests should be runnable (pytest, jest, etc.)
- Verify tests fail for the right reasons
- Update features.json with test file paths
```

Show user the test names/descriptions. Confirm they capture intent.

## Phase 5: Confirm & Launch

Final checklist before autonomous loop:

```
1. User approved plan? [y/n]
2. Tests written and failing? [y/n]
3. Tests capture all features? [y/n]
4. max_iterations set? [value]
5. Completion criteria clear? [y/n]
```

If all confirmed, create ralph prompt:

```
Implement features to make all tests pass.

Features: [list from features.json]
Tests: [test commands]
Constraints: [from CLAUDE.md + user input]

After each iteration:
- Run tests
- If all pass + lint clean + types pass → output <promise>COMPLETE</promise>
- If stuck after 5 iterations on same issue → document blocker, continue

Output <promise>COMPLETE</promise> only when:
- All tests green
- No type errors
- Lint clean
- features.json updated with done_when satisfied
```

Then launch:
```bash
/ralph-loop "<prompt>" --max-iterations <n> --completion-promise "COMPLETE"
```

## Artifacts Created

| File | Purpose |
|------|---------|
| features.json | Feature list with completion criteria |
| claude-progress.txt | Session handoff notes (updated by ralph) |

## Constraints

- **User confirms each phase** - no skipping ahead
- **Tests before loop** - ralph needs pass/fail signal
- **One feature at a time** in implementation (ralph handles this)
- **max_iterations always set** - safety net
