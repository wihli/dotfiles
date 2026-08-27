---
name: delarbitrate
description: Run bounded read-only Codex and Claude arbitration. Use when the user explicitly requests multi-model arbitration, an independent cross-model decision, or Delarbitrate.
---

# Delarbitrate

Use this skill for explicit requests such as “arbitrate this with Codex and Claude,” “get an independent cross-model decision,” or “use Delarbitrate.” Do not trigger for ordinary reviews, brainstorming, a second opinion from one unspecified model, or requests that do not ask for multi-model arbitration.

## Refuse recursion

Read `DELARBITRATE_CHILD` before any other action. If it equals `1`, refuse to invoke Delarbitrate because the current agent is already a provider child.

## Prepare the exact task

An explicit request to use Delarbitrate authorizes Codex and Claude to receive the relevant request, established context, and listed live source paths. Do not ask for a second transfer confirmation. This authorization does not grant write authority or permit unrelated data.

Prepare useful starting context before the run:

1. Identify each external evidence source and local directory that the request requires.
2. Use the owning read-only skill or supported CLI for Jira, Datadog, Slack, or another external source when it can add bounded findings and locators.
3. Treat those findings as starting context. The provider children can investigate the live workspace with the normal read-only agents, skills, and tools available inside their native read-only harness.
4. Never copy a secret, raw connector payload, or unrelated record into the task.
5. Use the referenced workspace as the primary workspace. Otherwise, use the current workspace.
6. Include each additional local directory as a source. Do not create a worktree, temporary checkout, or copied evidence directory. Choose specific paths instead of a broad source that contains Delarbitrate's XDG run state.

Create a temporary Markdown task file with these sections:

```text
# User request (verbatim)
<the referenced request without editing, summarizing, or correcting it>

# Established context
<only established facts, bounded findings, and exact locators>

## Source paths
- `/absolute/path`
```

List the primary workspace and each additional local source with the exact bullet form shown above. Add one `--source <absolute-path>` argument for each source outside the primary workspace. Do not add inferred preferences, external writes, provider instructions, or new authority.

Delarbitrate writes only its XDG run state. Its provider prompts and native harness restrictions require read-only investigation. The run must leave the workspace and external systems unchanged. A workspace change from another session is a provenance warning, not a reason to discard the result.

## Run the foreground pipeline

Use `delarbitrate-auth` when it is available. Otherwise, use `delarbitrate`. The command templates use `<delarbitrate-command>` for that selected executable. Do not log in, invoke a provider directly, enable a write permission, or add a connector to a provider child.

Run these commands with JSON output:

```text
<delarbitrate-command> doctor --json
<delarbitrate-command> run --task-file <task-file> --workspace <workspace> [--source <source-path>]... --json
```

A restricted command sandbox can block Keychain reads. When `delarbitrate-auth` reports this failure, retry the exact doctor command once through the harness's normal approval mechanism. The retry must run outside that sandbox. Do not create a setup command or recovery script for the first failure. Only recommend `delarbitrate-auth setup` when the approved retry also fails. If the harness cannot request approval, report the sandbox access blocker and ask the user to run the doctor command. Do not claim that the token is absent.

If `doctor` returns `blocked`, report its exact blocker. Do not attempt authentication or continue the pipeline.

## Report observed progress

For `run` and `continue`, read JSONL progress events from stderr while the foreground process runs. Relay concise observed stage changes, retries, and heartbeats. Do not infer progress from silence or elapsed time. Do not claim that a provider is collecting evidence unless an event says so.

Progress can include the run ID, stage, elapsed time, active launch count, and remaining timeout. Do not expose provider prompts, candidate claims, reasoning, raw provider output, or secrets. Treat stdout as the single terminal result object.

Handle the run result by its `status`:

- `complete`: Return `answer_markdown`, then a compact receipt with `run_id`, `selected_candidate_backbone`, `arbitration_path`, `evidence_coverage`, `warnings`, and `packet_path`.
- `needs_human`: Ask only `human_brief.question` when `authority_kind` is `preference` or `authoritative_fact` and the question is answer-only. An answer-only question asks for a choice or fact that the user already knows. A request for access, authorization to query, a source path, a command, investigation, or another tool action is a protocol blocker; report it and do not call `continue`. Preserve a valid answer verbatim in a temporary answer file. Then run `<delarbitrate-command> continue <run-id> --answer-file <answer-file> --json` and handle the successor result by the same rules.
- `blocked`: Report the exact `error` or doctor check, plus the retained `run_id` and `packet_path` when present. When `blocked_reason` is `insufficient_evidence`, also return `evidence_brief`, including every exact next read-only action. Do not replace arbitration with an informal model call.

`continue` adds only the answer to the emitted authority question and reads the predecessor's live workspace paths again. If the user supplies new evidence, a new source path, or new access, do not call `continue`. Rebuild the task and start a fresh `run`. Do not spend a second paid run after a blocked run unless the user explicitly requests it after seeing the blocker.

Use `<delarbitrate-command> show <run-id> --json` to recover a known run. Never select a run by recency or guess a run ID.

## Portability and discovery

The core workflow uses files, environment variables, and foreground commands. It does not depend on private tool syntax from Claude Code, Codex, OpenCode, or Pi.

The canonical source installs at `~/.local/share/skills/delarbitrate`. Claude Code discovers it through `~/.claude/skills/delarbitrate`. Codex, Pi, and OpenCode discover it through `~/.agents/skills/delarbitrate`; the installer also maintains `~/.codex/skills/delarbitrate` for Codex compatibility.
