---
name: delarbitrate
description: Run bounded read-only Codex and Claude arbitration. Use when the user explicitly requests multi-model arbitration, an independent cross-model decision, or Delarbitrate.
---

# Delarbitrate

Use this skill for explicit requests such as “arbitrate this with Codex and Claude,” “get an independent cross-model decision,” or “use Delarbitrate.” Do not trigger for ordinary reviews, brainstorming, a second opinion from one unspecified model, or requests that do not ask for multi-model arbitration.

## Refuse recursion

Read `DELARBITRATE_CHILD` before any other action. If it equals `1`, refuse to invoke Delarbitrate because the current agent is already a provider child.

## Freeze the task

1. Create a temporary Markdown task file.
2. Copy the referenced user request into a `User request (verbatim)` section without editing, summarizing, or correcting it.
3. Add only facts already established in the conversation under `Established context`.
4. Add only explicit local source paths under `Source paths`.
5. Do not add inferred preferences, external writes, provider instructions, or new authority.

Use the referenced workspace when the user supplies one. Otherwise, use the current workspace. Before human escalation, the task file is the only skill-created input. Delarbitrate can write only its XDG run state and must leave the workspace and external systems unchanged.

## Run the foreground pipeline

Use `delarbitrate-auth` when it is available. Otherwise, use `delarbitrate`. The command templates use `<delarbitrate-command>` for that selected executable. Do not invoke `delarbitrate-auth setup`; only the user can add a token to Keychain.

Run these commands with JSON output. Do not log in, invoke a provider directly, enable a write permission, or add a connector.

```text
<delarbitrate-command> doctor --json
<delarbitrate-command> run --task-file <task-file> --workspace <workspace> --json
```

A restricted command sandbox can block Keychain reads. When `delarbitrate-auth` reports this failure, retry the exact doctor command once through the harness's normal approval mechanism. The retry must run outside that sandbox. Do not create a setup command or recovery script for the first failure. Only recommend `delarbitrate-auth setup` when the approved retry also fails. If the harness cannot request approval, report the sandbox access blocker and ask the user to run the doctor command. Do not claim that the token is absent.

If `doctor` returns `blocked`, report its exact blocker. Do not attempt authentication or continue the pipeline.

Handle the run result by its `status`:

- `complete`: Return `answer_markdown`, then a compact receipt with `run_id`, `selected_candidate_backbone`, `arbitration_path`, `evidence_coverage`, and `packet_path`.
- `needs_human`: Ask only `human_brief.question`. Preserve the answer verbatim in a temporary answer file. Then run `<delarbitrate-command> continue <run-id> --answer-file <answer-file> --json` and handle the successor result by the same rules.
- `blocked`: Report the exact `error` or doctor check. Do not replace arbitration with an informal model call.

Use `<delarbitrate-command> show <run-id> --json` to recover a known run. Never select a run by recency or guess a run ID.

## Portability and discovery

The core workflow uses files, environment variables, and foreground commands. It does not depend on private tool syntax from Claude Code, Codex, OpenCode, or Pi.

The canonical source installs at `~/.local/share/skills/delarbitrate`. Claude Code discovers it through `~/.claude/skills/delarbitrate`. Codex, Pi, and OpenCode discover it through `~/.agents/skills/delarbitrate`; the installer also maintains `~/.codex/skills/delarbitrate` for Codex compatibility.
