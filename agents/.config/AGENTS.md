# AGENTS.md

Eric Ihli owns this. Start: say hi + 1 motivating line. Work style: concise dense thorough; min tokens;

## This file

- ~/.config/AGENTS.md (symlinked to ~/.claude/CLAUDE.md)
- "Make a note" or "Remember to" => edit this file
- Minimize tokens; optimize for AI agent

## Core Philosophy

- **Start simple, always** - smallest testable version first
- **Ask before assuming** - gather context/specificity before implementing
- **Fail fast explicitly** - raise exceptions, not silent failures
- **Fix root cause** - no band-aids

## Before Implementing

Check:
- Have context? (existing code, patterns, constraints)
- User specific enough? If vague, ask.
- Can start with simple testable version?
- Response >50 lines or >3 files? Simplify or break down.

## Coding

- Write tests before implementation
- Tests document context: what was the situation/expectation when added?
- Type checks pass before "done"
- Tests pass before "done"
- No shortcuts to pass types/tests
- Use appropriate lint tools
- Keep files small (optimize for tokens)

### Docstrings

Non-trivial functions get detailed "why" docstrings:
- **Purpose**: Why does this exist? What problem does it solve?
- **Context**: Who uses this? When/why created?
- **Behavior**: What decisions and why?
- **Exceptions**: What error conditions cause failure?

Comments should add value beyond what code says:
- X `# Calculate EPS surprise` (obvious)
- OK `# Use abs() to handle negative estimates (expected loss)`

### Error Handling

- Invalid inputs raise exceptions (don't silently omit)
- Error messages: include invalid value + suggest fix
- Let callers handle edge cases (they have context)
- Batch processors catch exceptions at batch level

### Secrets

- .env.enc encrypted age/sops (decrypted to .gitignored .env)
- Only *secrets* in .env; config in config files (.toml, .py, .json, .yaml, whatever...)!

### Logging

- Output useful to AI agents: clean, structured, min tokens, max info
- Use log levels appropriately
- Use logs to debug

### XDG Directories

Follow XDG Base Directory spec:
- `$XDG_CONFIG_HOME` (~/.config) - config files
- `$XDG_DATA_HOME` (~/.local/share) - persistent data
- `$XDG_CACHE_HOME` (~/.cache) - non-essential cached data
- `$XDG_STATE_HOME` (~/.local/state) - logs, history, recent files

Never pollute $HOME with dotfiles/dotdirs.

## Testing

- Testing pyramid: mostly unit, some integration, few e2e
- E2e to verify; if blocked, say what's missing
- **External APIs: integration test early** - verify real connectivity before extensive mocks

## Planning

- Web search early
- Read external docs early

## Documentation

- Keep notes short; update when behavior/API changes
- Add `read_when` hints on cross-cutting docs
- Follow links until domain makes sense
- **Proactively fix stale docs** after significant work
- **README.md maintenance**: update verification commands, document new modules

## Build / Test

- Before handoff: run full gate (lint, types, tests, docs)
- Use `/review` skill for critical review before complete
- **Handoff summary**: findings, choices made, results (what changed and why)

## Git

- Destructive ops forbidden unless explicit
- No repo-wide search & replace; keep edits small
- Avoid manual `git stash`
- Check `git status` and `git diff`; keep commits small

### Commit messages

- No "Co-authored by ..." AI tagline
- Add context: "what" + "why" (+ "why not X" where appropriate)

## Context Window Management

- Never paste long repetitive tool output - summarize patterns
- Fix auto-fixable issues before asking for help (`--fix` flags)
- Group related errors: "12 type annotation errors" not 12 lines
- Show solutions with problems
- Use incremental checking (changes, not entire codebase)

## Process Management

Use shell job control:
```bash
npm start &          # background
jobs                 # list
kill %1              # kill job 1
jobs -p | xargs kill # cleanup all
```

## Red Flags - Stop and Reassess

- Same error type 3+ times
- Response >50 lines new code
- Changing >3 files at once
- User keeps asking "why isn't this working?"
- Debugging helpers more complex than target code

When triggered: step back, ask what's the smallest useful piece, simplify ruthlessly.

## Critical Thinking

- Fix root cause (not band-aid)
- Unsure: read more code; if still stuck, ask w/ short options
- Conflicts: call out; pick safer path
- Leave breadcrumb notes in thread
