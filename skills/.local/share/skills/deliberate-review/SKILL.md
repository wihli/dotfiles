---
name: deliberate-review
description: Open or supervise a local Deliberate pull-request review: status, findings, pause, cancel, resume, and guidance. Use for GitHub PR review requests with Deliberate or existing-review follow-ups.
---

# Deliberate Review

Use this skill for `deliberate review PR #123`, `review owner/repo#123 with deliberate`, a GitHub pull-request URL, and follow-ups about that review's status, findings, pause, cancel, resume, or focus.

The skill is shared by Claude Code and Codex. OpenCode can use the same tool-neutral core through its Agent Skills compatibility paths, but P027 validates discovery behavior only for Claude Code and Codex. Read state, run the bundled helper with Python, and use the returned local CLI operation without relying on either harness's private syntax.

## Safety boundary

- Results remain local. Do not post a pull-request comment or review, add labels, assign people, fetch a real pull request during a test, or make another external write.
- The helper only reads durable Deliberate state before it invokes a requested CLI command. It never chooses a globally newest run.
- `findings` uses Deliberate's `message --json` operation, which can start a fresh configured provider turn. Run it only for a direct request to interpret completed findings; never use it while testing this skill.
- A pause or cancel is a user-requested control. Guidance is future-only and may cancel an active attempt so it restarts cleanly.

## Resolve the review identity

1. Prefer an explicit `owner/repo#123` or `https://github.com/owner/repo/pull/123`.
2. For a bare PR number, have `scripts/deliberate_review.py` read the current repository's GitHub remotes. If it finds anything other than one repository, ask for `owner/repo` or the URL; never guess a default repository.
3. Retain an ID already established in the current conversation. On re-entry, use the helper's repository-and-PR lookup instead; it reads `draft.json`, `draft-state.json`, and `source/github-pr.json` below the XDG Deliberate state directory.
4. If lookup finds zero or multiple matching drafts/runs, ask the user to identify the intended run. Do not select by recency.

## Route the request

Ask the helper for a JSON operation plan, then execute that exact plan. It emits `deliberate-review-operation-v1`; do not reconstruct command arguments by hand.

| User intent | Helper action | Deliberate operation |
| --- | --- | --- |
| Open a review draft | `review` | `review --detach --json` |
| Status | `status` | `status --json` |
| Interpret completed findings | `findings` | `message --json` |
| Pause | `pause` | `pause` |
| Cancel | `cancel` | `cancel` |
| Resume a paused review | `resume` | `unpause` |
| Add focus or guidance | `guidance` | `steer` |

Use this form, resolving `<skill-directory>` relative to this file:

```text
python3 <skill-directory>/scripts/deliberate_review.py plan <action> ...
python3 <skill-directory>/scripts/deliberate_review.py execute <action> ...
```

Pass `--repo owner/repo --pr 123` for a known identity, `--url <pull-request-url>` for a URL, or `--pr 123 --cwd <repository>` only for a bare number. Pass `--message <text>` for `findings` and `guidance`. Use `--state-dir <path>` only when the caller has supplied a non-default state directory.

`execute` returns sanitized structured result data. For `review`, `status`, and `findings`, it requires valid JSON from the CLI. For controls, it records only the exit outcome and never relays terminal or provider output. If a review draft returns an open question, ask that exact question and answer it with `deliberate answer <draft-id> <question-id> <response>`; do not invent an answer or launch work first.

## Verify portability

Run `python3 <skill-directory>/scripts/deliberate_review.py validate` before handoff. The source directory is `skills/.local/share/skills/deliberate-review/`; installed copies under `~/.claude/skills`, `~/.agents/skills`, or `~/.codex/skills` are generated and must not be edited.
