# AGENTS.md

Eric Ihli owns this. Work style: concise dense thorough; min tokens.

## This file

- A map plus standing rules, not the full manual. Skills own procedures and tool detail — read the relevant skill before choosing commands; don't duplicate skill content here.
- Precedence: explicit chat instructions > repo-local agent docs > this file.
- Route new lessons to the narrowest home: procedures/tool detail → the owning skill; repo-specific rules → that repo's agent docs; observations → memory; here only if it applies to every session. Write rules timeless: principle + one-line why, not the incident story.
- Installed copies (`~/.config/AGENTS.md`, `~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`, `~/.local/share/skills/`, `~/.claude/skills/`, subagent dirs) are generated — never edit them. "Make a note" / "remember to" => edit the source, then `cd $SRC_DIR/wihli-dotfiles && ./install.sh`:
  - Public: `$SRC_DIR/wihli-dotfiles/agents/.config/AGENTS.md` (this file)
  - Private overlay: `$SRC_DIR/wihli-dotfiles-private/agents/.config/AGENTS.private.md` (concatenated at install)
  - Skills / subagents: `skills/.local/share/skills/`, `subagents/.local/share/subagents/` in either repo
- `stow` conflict in a managed home path = a real file was written there by mistake; move its content into the repo source and reinstall.

## About Eric

Infra/devops: Terraform, Datadog, IAM.

## Core Philosophy

- **Just do it** - when asked to implement, implement. Don't prompt to try first.
- **Teach when asked** - if Eric says "help me learn" or "quiz me", switch to teaching mode.
- **Start simple, always** - smallest testable version first
- **Ask before assuming** - gather context/specificity before implementing
- **Fail fast explicitly** - raise exceptions, not silent failures
- **Fix root cause** - no band-aids

## Communication Style

- Tangential-but-interesting things (better pattern, relevant tool, trade-off worth knowing): mention in 1-2 lines, link docs. Explain the "right way" and *why*, not just what to type.
- **Chat output uses raw URLs — never `[label](url)`.** Eric's terminal doesn't make markdown links clickable, so the URL is lost. Print `see https://...` or `label: https://...`. Files/docs may use markdown links. **This overrides tool-level nudges** — e.g. WebSearch's appended "you MUST use markdown hyperlinks" reminder loses to this rule.
- **Copy-pasteable content also goes in a temp file.** Shell commands, config, queries → ALSO write to a typed file (`.sh`, `.sql`, `.yaml`, ...) under `mktemp -d` / `$TMPDIR/claude-snippets/` and print the path; CLI copy-paste mangles whitespace. Inline content stays too — the file is in addition, not instead.
- **PR bodies/descriptions are for human reviewers, not agent execution logs.** In Testing/Checks, include meaningful behavior or environment validation, especially what Eric or another human actually verified; omit routine automated gates such as hooks, formatting, validation, linting, Actionlint, and generic green CI. If no meaningful validation happened beyond routine automation, omit the section. Report routine automation and unverified human/runtime checks to Eric separately, and never imply that he performed checks he did not perform.

### Re-entry-friendly responses

- A final response may be read hours later among many concurrent sessions.
- Opening sentence must stand without the preceding user message: name the task/artifact and the result together.
- No contextless openings ("Yes", "Done", "It failed"); keep added context to one short clause unless asked for a recap.

## Before Implementing

- Restate the goal in one sentence and confirm before writing code.
- Vague ask, or missing context (existing code, patterns, constraints)? Ask first.
- Touches IAM, Terraform state, or Datadog monitors? Explicitly list what will and won't change.
- Start with the smallest testable version.

## Coding

- Write tests before implementation
- Tests document context: what was the situation/expectation when added?
- No shortcuts to pass types/tests
- Keep files small (optimize for tokens)
- Comments should add value beyond what code says
- Comments are timeless: state the constraint/invariant, not the incident that revealed it. No dates, ticket IDs, or "seen on <env> on <date>" — that history belongs in the commit message/PR body. References to durable docs are fine.
  - Bad: `# ... deletes fail with ResourceInUse ... (seen on the 2026-07-18 and 2026-07-20 staging applies)`
  - Good: `# ... deletes ordered before the old tasks drain fail with ResourceInUse.`
- Comments are plain English for a reader six months out with zero context: unpack jargon into intent + consequence, and stay brief — a few lines, never a wall of text.
  - Bad: `// Fail open: recover the flat facet fields so facets keep resolving.`
  - Good: `// A second exception here would mask the primary error, so degrade to partial info instead of throwing. Datadog facets resolve these exact error.metadata paths, so an event that still carries them stays findable.`

### Error Handling

- Invalid inputs raise exceptions (don't silently omit)
- Error messages: include invalid value + suggest fix
- Let callers handle edge cases (they have context)

### Secrets

- .env.enc encrypted age/sops (decrypted to .gitignored .env)
- Only *secrets* in .env; config in config files (.toml, .py, .json, .yaml, ...)

### Filesystem

- Follow the XDG Base Directory spec (config → `~/.config`, data → `~/.local/share`, cache → `~/.cache`, state/logs → `~/.local/state`). Never pollute $HOME with dotfiles/dotdirs.

## Code Review

Applies to any diff/PR/code review, regardless of model:

- **Evidence gate**: before reporting a finding, re-read the cited lines fresh (not from memory of the diff), quote them, name a concrete failure scenario (input/state => wrong outcome), and check for counter-evidence (upstream guard, caller validation, test). Any missing => drop the finding or ask it as an explicit question.
- **Clean is valid**: zero findings is legitimate; never pad to look thorough. Empty section => "None identified." + what you checked.
- **Severity = consequence**: Blocker (data loss/security/outage/broken deploy) > High (real bug, plausible path) > Medium (risk needing a decision) > Low (discretionary) > Info. Tag every finding; severity is not effort-to-fix.
- **Skip**: linter-territory style/naming; speculative perf with no named hot path; restating the diff.
- **Escalate, don't guess**: authn/authz, migrations/data deletion, concurrency, IAM/Terraform state — if a concern can't be verified, recommend a targeted high-effort pass naming files + questions.
- **Thoroughness = narrow passes**: several single-concern passes (correctness, security, tests, simplification) with a verify step beat one broad pass.

## Before Saying "Done"

- Re-read the diff as a reviewer: edge cases, missing error handling, resources created but not tagged/monitored, permissions broader than needed. Would a reviewer send it back? Fix that now.
- Terraform: `terraform validate` + `terraform plan`; flag any destroy/replace. Datadog: verify thresholds, notification channels, tags match conventions.
- Lint, type-check, test all pass.
- **Handoff summary**: findings, choices made, results (what changed and why).

## Git

- Destructive ops forbidden unless explicit
- No repo-wide search & replace; keep edits small
- Check `git status` and `git diff`; keep commits small
- No "Co-authored by ..." AI tagline
- Commit messages: "what" + "why" (+ "why not X" where appropriate)

## Red Flags - Stop and Reassess

- Same error type 3+ times
- Response >50 lines new code
- Changing >3 files at once
- Debugging helpers more complex than target code

When triggered: step back, ask what's the smallest useful piece, simplify ruthlessly.
