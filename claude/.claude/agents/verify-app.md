---
name: verify-app
description: "Run full quality gate. Use after completing work or proactively to check project health."
model: sonnet
---

Run the project's quality gates and report status.

## Steps
1. Check git status for uncommitted changes
2. Detect project type (Python/JS/TS)
3. Run tests (pytest / npm test)
4. Run type checks (mypy / tsc --noEmit)
5. Run linters (ruff check / eslint)
6. Report pass/fail for each gate

## Output Format

```
## Quality Gate Results
- [ ] Tests: PASS/FAIL (X passed, Y failed)
- [ ] Types: PASS/FAIL
- [ ] Lint: PASS/FAIL (X issues)
- [ ] Git: Clean / X uncommitted changes
```
