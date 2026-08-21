---
name: finalize
description: "Run the wrap-up checklist before handoff: git status, test/type/lint gates, critical review, then commit what remains. Use for finalize, wrap up, or did-you-commit requests."
---

# Finalize

Run this checklist before considering work complete.

## 1. Git Status Check

```bash
git status
git diff --stat
```

If uncommitted changes exist, proceed through remaining steps before committing.

## 2. Task Completion Check

- Review conversation for any unfinished TODOs or skipped items
- Check your agent's task list (if it has one) — are all items marked completed?
- If anything incomplete, finish it before proceeding

## 3. Run Quality Gates

Run project-appropriate checks. Detect from project structure:

| Files present | Commands to run |
|---------------|-----------------|
| `package.json` | `npm test`, `npm run lint`, `npm run typecheck` (or equivalents) |
| `pyproject.toml` / `setup.py` | `pytest`, `mypy .`, `ruff check .` (or project equivalents) |
| `Cargo.toml` | `cargo test`, `cargo clippy` |
| `go.mod` | `go test ./...`, `go vet ./...` |

Check `package.json` scripts or project config for actual command names. Fix any failures before proceeding.

## 4. Critical Self-Review

Review all changes with adversarial mindset:

- Security: injection, auth issues, exposed secrets?
- Edge cases: nil/null, empty collections, boundary conditions?
- Error handling: failures caught and handled appropriately?
- Breaking changes: backwards compatibility maintained?
- Tests: new code has test coverage?

If issues found, fix them. Re-run quality gates after fixes.

## 5. Commit

If all gates pass and changes look good:

```bash
git add -A
git commit -m "<descriptive message with why, not just what>"
```

Report final status to user.
