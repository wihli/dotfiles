# Code review

This reference owns the procedure and finding requirements for ordinary and delegated code reviews. Scope the work to the requested change and the questions that can affect its assessment.

## Establish scope and expectations

Identify the checkout, base, and head or uncommitted diff being reviewed. If the request leaves scope unclear, inspect the available changes and state the scope chosen. Recheck the current patch before delivering findings.

Read the enclosing code and relevant callers or consumers, especially when a signature, schema, default, or shared lifecycle changes. Establish the intended outcome and relevant organizational constraints before judging consequential behavior or test coverage. Use an applicable context skill, such as `code-context`, when available; otherwise follow the relevant decisions, tickets, and callers directly. Separate accepted requirements from proposals and inference.

Derive review scenarios from those expectations. If a missing decision changes the assessment, state it and continue the supported checks.

## Focus the review

Choose passes that match the changed behavior:

- Error and boundary paths, including partial failure and retries.
- Resource ownership, concurrency, cleanup, and idempotency.
- Authorization, secret exposure, and untrusted inputs.
- Compatibility across callers, schemas, migrations, and rollout order.
- Tests that exercise the actual trigger and observable outcome.
- Simpler existing mechanisms, when a concrete alternative improves the result.

For infra changes, read the matching sections of `~/.local/share/agent-references/review-checklists.md` when available. Its repository-specific accepted patterns and failure classes apply only in their stated scope.

## Verify each finding

Before reporting a finding:

1. Re-read the cited lines on the current patch, including the enclosing code. Quote the relevant source.
2. Name a concrete input or state and the incorrect outcome it causes.
3. Check for counter-evidence in guards, callers, tests, and dependency behavior. State what was checked.

Drop a candidate that does not meet these requirements. If an important concern remains unresolved, label it as a question and name the evidence needed. Agreement between reviewers helps prioritize investigation; it does not establish correctness.

Settle conditions that the current session can check before delivering them to Eric. A delegated review's access gap does not establish that the coordinator lacks access.

## Report the result

Lead with the change's effect and assessment. For consequential reviews, explain the expectations that guided the checks and cite their sources. Order findings by consequence:

| Severity | Consequence |
| --- | --- |
| Blocker | Data loss, security failure, outage, or broken deployment |
| High | A real defect on a plausible path |
| Medium | A material risk that needs a decision |
| Low | A discretionary improvement with a concrete benefit |
| Info | Context that helps the reviewer |

Each finding includes severity, path and line, source quote, failure scenario, counter-evidence checked, and a concise proposed correction. Zero findings is valid; say what was checked. Omit linter-owned style issues, speculative performance claims without a named path, and diff narration.

Distinguish source inspection, tests, plans, deployed behavior, and unverified assumptions. For consequential concerns that remain unresolved, recommend a targeted additional check or review with exact files and questions. Keep approval, publication, and production actions within the user's existing authorization.
