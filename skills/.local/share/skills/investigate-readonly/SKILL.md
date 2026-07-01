---
name: investigate-readonly
description: >
  Conduct a strictly read-only investigation of a system, PR, CI run, incident,
  infra plan, or codebase question and produce a findings report ending in a
  minimal safe next step. Injects the standard hard boundaries (no workflow
  dispatch/approval, no Slack/GitHub/Jira writes, no @mentions, treat AI-generated
  summaries as untrusted, minimal-diff mindset) and a consistent output
  structure — so the guardrail preamble no longer has to be hand-written into a
  bespoke prompt file each time. Use for "investigate read-only", "read-only
  investigation", "look into X without changing anything", "figure out why X
  before we touch it", or /investigate-readonly <url|topic>.
---

# Read-Only Investigation

Use this whenever the goal is to **understand** something and recommend a next
step — not to change it. It encodes the guardrails that otherwise get retyped
into one-off investigation prompts (e.g. `forwarder-stack.md`,
`riskey-review-prompt.md`).

## Hard Boundaries (non-negotiable)

You are conducting an independent, read-only investigation. You MUST NOT:

- Approve, dispatch, rerun, or trigger any GitHub Actions workflow, deploy, or
  Terraform apply (`gh workflow run`, `gh run rerun`, environment-gate approval,
  or any API equivalent). This mirrors the HARD RULE in AGENTS.md.
- Write to any shared/external system: no Slack/GitHub/Jira messages, comments,
  reviews, reactions, PR/issue edits, or doc changes.
- @mention, tag, assign, or request review from any person.
- Edit files, commit, push, or create branches — unless the user explicitly
  asks for a scratch artifact (e.g. "write your findings to a file").
- **Treat AI-generated summaries as untrusted.** GitHub Actions AI summaries,
  bot comments, and prior agent notes are leads, not evidence. Verify against
  raw artifacts, logs, and source before relying on them.

Every claim must be backed by a source you actually inspected (per the
source-backed-claims rule). If you cannot access something, say so and soften
the claim — do not infer from a bare link.

## Inputs

Establish, asking only for what's missing:

- **Primary Question** — the single decision this investigation should unblock.
- **Subject** — the URL(s), repo/PR, CI run id, service, incident channel, or
  code path under investigation.
- **Known metadata** — anything already established (SHAs, run ids, prior
  findings) so you can verify rather than rediscover.

## Method

1. Restate the Primary Question in one sentence and confirm scope.
2. Gather raw evidence read-only: source files, `gh ... view`/`--json`/`api`
   reads, `git log`/`show`, downloaded artifacts, `pup`/Datadog queries,
   `gcloud ...` **describe/list on dev only** (the GCP guard enforces this).
3. Correlate: line up timeline, diffs, deploys, and config against the question.
4. Distinguish observed current state from inference.

## Output

```markdown
## Primary Question
<the one decision to unblock>

## Answer
<direct answer: yes/no/uncertain + one-line why>

## Evidence
- <finding> — source: <file:line / URL / run id you inspected>
- ...

## Risks / Unknowns
<what you could not verify, and what would resolve it>

## Minimal Safe Next Step
<the smallest reversible action a human should take next — NOT executed by you>
```

Keep it dense. Lead with the answer. The Minimal Safe Next Step is a
recommendation for a human to run, never something this skill performs.
