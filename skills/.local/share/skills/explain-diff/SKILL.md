---
name: explain-diff
description: Create persistent local literate diffs with background, intuition, narrative review order, Markdown, and HTML. Use for PRs, commit ranges, patches, or worktree changes.
---

# Explain Diff

Optimize for the best explanation, not the fastest summary. Catch the human up on the existing system, build intuition before details, and then walk through the change as a literate diff in causal review order.

## Establish the comparison

1. Resolve the repository, base, head, change source, intended audience, and requested focus. Ask only when different answers would materially change the explanation.
2. Read repository guidance and preserve the worktree. Treat this as read-only review unless the user separately asks for code changes.
3. Capture the exact raw diff in a temporary file. For worktree changes, include staged, unstaged, and relevant untracked files while respecting ignore rules.
4. Inspect the diff for credentials, `.env` contents, private keys, or other secrets before persisting it. Stop and identify the unsafe input rather than copying a suspected secret into an artifact.
5. Read enough pre-change code, current code, callers, tests, and nearby documentation to explain what existed before. Do not infer architecture from changed lines alone.

## Prepare the local artifact

Resolve `scripts/artifact_store.py` relative to this skill directory and run:

```text
python3 <skill-directory>/scripts/artifact_store.py prepare \
  --repo-root <repository> \
  --subject <stable-review-identity> \
  --snapshot-file <temporary-raw-diff> \
  --base <base-ref-or-sha> \
  --head <head-ref-sha-or-WORKTREE> \
  --source <local-diff-or-PR-URL> \
  --variant <audience-or-focus>
```

Use a stable subject such as a PR URL, `pr:<number>`, `range:<base>...<head>`, or `worktree:<branch>`. Use `general` as the default variant; name a different variant when the audience or review focus changes.

The helper stores durable artifacts under `$XDG_DATA_HOME/explain-diff` (default `~/.local/share/explain-diff`) and the mutable lookup index under `$XDG_STATE_HOME/explain-diff` (default `~/.local/state/explain-diff`). `$XDG_CACHE_HOME` is only appropriate for disposable rendering intermediates, never the explainer or its provenance.

The helper prints JSON containing `revision_dir`, `markdown_path`, `html_path`, `manifest_path`, and whether the exact subject, snapshot, and variant were reused. It creates a content-addressed revision for changed input and moves `latest` to that revision. Treat a revision as immutable after both outputs exist. If an exact revision already contains both outputs, return it instead of silently regenerating it.

## Build understanding

Write the canonical explanation to the returned Markdown path with this order:

1. **Goal** — State the user-visible or system-level outcome in plain language.
2. **What existed before** — Teach the minimum background needed to understand the change: architecture, data flow, vocabulary, and constraints.
3. **Intuition before details** — Give the mental model, analogy, diagram, or worked example that makes the implementation predictable before showing code.
4. **Literate diff** — Walk through changes in dependency and causal order, not filename order. For each step, explain its purpose, before/after behavior, concise code excerpts, source locations, and downstream effects.
5. **Verification and risk** — Explain what tests or runtime evidence establish, what could fail, and what still needs human attention.
6. **Review map** — List files in the recommended reading order and link the persisted raw diff.

Use evidence labels where certainty matters:

- **Observed** — Directly supported by code, tests, history, or runtime evidence inspected for this explanation.
- **Inferred** — A conclusion drawn from observed evidence; state the reasoning.
- **Unresolved** — Missing evidence or a decision the explanation cannot settle.

Keep excerpts small enough to teach the idea. The explainer complements the raw diff; it does not replace reviewing it.

## Derive self-contained HTML

Render the same narrative to the returned HTML path after the Markdown is complete.

- Embed CSS and JavaScript locally. Do not use CDNs, analytics, remote fonts, uploads, Notion, or other hosted dependencies.
- HTML-escape all repository content. Never interpolate code or diff text into executable JavaScript.
- Include readable typography, syntax styling, navigation, and print CSS so the document works on screen and paper.
- Add an interactive figure only when manipulating state materially improves the mental model. Keep it keyboard-accessible and ensure the prose still works without JavaScript.
- Do not launch a browser or server automatically. If the user asks to interact with an artifact that requires HTTP, use a loopback-only temporary server and report how it can be stopped.

## Verify and hand off

Before returning the artifact:

1. Re-read cited source locations and confirm every claim still matches them.
2. Open both outputs as text and verify their structure, code escaping, provenance, and links. Render or open the HTML when visual or interactive behavior is part of the request.
3. Confirm the manifest identifies the repository, comparison, snapshot hash, subject, variant, and output names without credentials.
4. Report the exact Markdown, HTML, manifest, and raw-diff paths; say whether the revision was created or reused.
5. Distinguish completed checks, unavailable runtime validation, and unresolved questions.
