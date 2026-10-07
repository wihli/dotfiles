---
name: thabto
description: Run independent Claude and Codex attempts, mutual review, and revision, then synthesize. Use only when the user names THABTO. Read-only tasks only.
---

# THABTO — Two Heads Are Better Than One

Use for explicit requests such as "use thabto to investigate X", "use thabto to review X", or "use thabto to design X". Do not trigger for ordinary investigations or an unspecified second opinion.

## Scope

This first version is read-only. If asked to "use thabto to implement X", explain that isolated implementation worktrees are not available yet. Ask whether to investigate or design the change with THABTO. Do not silently substitute a design for implementation.

Read `THABTO_CHILD` before running anything. If it equals `1`, refuse recursion. An explicit THABTO request authorizes both providers to receive the relevant task and context. Preserve the user's existing authority boundaries.

## Prepare

1. Resolve this skill's directory and its bundled `scripts/thabto.py`. Use Python 3.10+ on macOS or Linux. Both provider CLIs must already be installed and authenticated.
2. Save a UTF-8 task file containing the user's request verbatim, established context, relevant source paths, constraints, and the desired deliverable. Exclude the coordinator's preferred answer so the first attempts remain independent.
3. Use the requested workspace, or the current workspace if none was named. Name additional local source paths in the task. Providers read live files; concurrent edits can affect results.
4. These providers inspect local files. Claude Code has Read, Glob, and Grep; Codex has its native read-only sandbox; OpenCode runs the bundled `thabto-child` agent from `harness/opencode.json` (read, glob, grep, list only); Pi runs with `--tools read,grep,find,ls`. MCP connections, plugins, and extensions are disabled. OpenCode and Pi accept OpenAI models only (`openai/…`, `openai-codex/…`): Anthropic limits Claude subscription sign-in to Claude Code, so Claude participates through Claude Code alone, and the driver refuses other combinations. For external evidence, use the owning read-only skill first and include relevant excerpts and source locators in the task. Never copy secrets or unrelated data. State any source that remains inaccessible.
5. Default to `--claude-model claude-opus-5-5 --codex-model gpt-6-sol` at `high` effort. They cost a fraction of the frontier tier and still produce concrete, cited cross-review corrections. Escalate to the frontier tier (`fable`, `gpt-6-astra`) only for an unusually hard task: open architecture judgment, conflicting evidence, or a rerun after these defaults missed something. Say which tier you chose and why. An explicit user model preference overrides both. Confirm the IDs against the installed CLIs. Set each provider's effort if its supported values differ from `high`. Keep the same model through that provider's three stages.

## Run

Run in the foreground with an argument list. Resolve the placeholders below; preserve quoting for paths with spaces:

```sh
python3 "<skill-directory>/scripts/thabto.py" \
  --task-file "<task-file>" \
  --workspace "<workspace>" \
  --claude-model "<claude-model>" \
  --codex-model "<codex-model>"
```

Optional arguments: `--claude-effort`, `--codex-effort`, `--timeout` (seconds per invocation, default 600), `--seed` (ring order; random and recorded by default), and `--<harness>-executable` overrides. Executable overrides receive the same arguments as native CLIs; they are not a different test protocol.

For more than two participants, or a harness other than the default pair, replace the model flags with repeated `--participant HARNESS:MODEL[:EFFORT]` (for example `--participant claude-code:claude-opus-5-5 --participant codex:gpt-6-sol --participant codex:gpt-6-astra`). Known harnesses are listed in the driver's `--help`. Participants are named by harness (`claude`, `codex`, `codex-2`, …); those names appear in the run directory and in `run.json`. The two forms cannot be mixed.

Relay the driver's observed stage messages while it runs. Every participant attempts the task; then each reviews the next participant in a shuffled ring (`review_targets` in `run.json`); then each participant that received a review revises. With two participants the ring is the familiar mutual review. Fresh processes, no retries. Ctrl-C or termination cancels the active process groups.

A participant that fails at any stage drops out of the later stages; the run continues if at least two attempts succeeded, and `run.json` records `failed_at` for the dropped participant. A participant whose reviewer failed keeps its attempt as its final answer. If a provider fails, report the exact failure and retained run path. Read its `error.txt` and relevant diagnostics before suggesting recovery. Do not claim that a partial exchange is a completed THABTO answer. Follow the harness's normal approval mechanism for a sandbox-blocked launch; do not switch credential mechanisms or bypass provider permissions. If interactive authentication is required, stop and explain the required provider login.

## Synthesize

On success, the driver prints the exact run directory. Read its `synthesis-prompt.md`, which lists the original `task.md`, each participant's final answer (`revision/<name>/answer.md`, or the attempt when no review reached it), and any participant that failed. Read the original attempts and reviews where needed to resolve a claim.

Write one answer to the user's question. Prefer supported claims; agreement alone proves nothing. State unresolved disagreement and verification limits.

Then record the outcome so runs can be compared later. Save the exact answer to a temporary file and write a verdict JSON file with this shape:

```json
{
  "schema": 1,
  "coordinator": {"harness": "claude-code", "model": "<your model id>"},
  "material_disagreement": true,
  "selected_backbone": "codex",
  "claims": [
    {"id": "c1", "text": "<one decisive claim from the exchange>",
     "positions": {"claude": "asserts", "codex": "disputes"},
     "disposition": "supported", "basis": "evidence"}
  ],
  "ground_truth": null
}
```

- `positions`: one entry per participant `name` in the run's `run.json`; each is `asserts`, `disputes`, or `silent`.
- `disposition`: your ruling on the claim after checking evidence: `supported`, `rejected`, or `unresolved`. `basis`: `evidence`, `preference`, or `unverified`.
- Agreement is not evidence: a claim every participant asserts that you did not check against a source is `unresolved` with `basis: unverified`. Use agreement only to decide which claims to check first.
- `material_disagreement`: `true` exactly when some claim has both an `asserts` and a `disputes` position.
- `selected_backbone`: the participant whose revision your answer follows most closely, `merged`, or `none`.
- `ground_truth`: leave `null`; label it later when reality settles the question.

Run `python3 "<skill-directory>/scripts/thabto_finish.py" --run "<run>" --synthesis "<answer-file>" --verdict "<verdict-file>"`. It validates the verdict, stores `synthesis.md` and `verdict.json` in the run, and sets the status to `synthesized`. Fix the named field and rerun if it rejects the verdict. Then return the answer and run path. The coordinator performs this step; the driver stops at `awaiting_synthesis`.

When the real outcome becomes known — a merged fix, a confirmed root cause — record it: `python3 "<skill-directory>/scripts/thabto_finish.py" --run "<run>" --label <participant|both|neither|unknown> --note "<what settled it>"`. `--pending` lists the runs still waiting for a label with the claims that divided the participants. If a later conversation reveals how a question THABTO investigated turned out, label that run before moving on; a verdict without a label only says which answer the coordinator preferred.

## Saved exchange

Runs live under `$XDG_STATE_HOME/thabto/<run-id>/`, defaulting to `~/.local/state/thabto/<run-id>/`. Each run directory is private to the user. Each stage/provider directory contains `prompt.md`, `command.json`, `stdout.log`, `stderr.log`, and, after success, `answer.md`. Codex also writes `final-message.md`. Failures retain `error.txt`. `run.json` records status (`running`, `awaiting_synthesis`, `synthesized`, `failed`, `cancelled`), the participants with their harness, model, and effort, and per-stage timing and exit codes; raw provider output retains any provider-reported usage and model details. After synthesis the run also holds `synthesis.md` and `verdict.json`. The driver does not record the child environment.

## Stats

`python3 "<skill-directory>/scripts/thabto_stats.py"` summarizes every retained THABTO run under `$XDG_STATE_HOME`: status, synthesis presence, resolved models, per-stage minutes, Claude cost, and verdict-derived scores per participant. It only reads. Add `--json` for machine-readable output, or `--thabto-state` to point at another directory. Fields a run never recorded print as `-` or `null`; they are not errors.

## Installation and discovery

Canonical source: `wihli-dotfiles/skills/.local/share/skills/thabto/`. Install through the repository's `install.sh`; never edit installed copies. The shared installation is `~/.local/share/skills/thabto`. Claude Code uses `~/.claude/skills/thabto`; Codex, Pi, and OpenCode use the shared `~/.agents/skills/thabto` discovery path. The installer also maintains `~/.codex/skills/thabto`.

The core skill uses files and foreground commands. Record discovery and behavior separately for each harness; link existence alone does not prove invocation works.
