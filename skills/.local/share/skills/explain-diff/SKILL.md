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

## Render deterministic HTML

Markdown is canonical; render it after it is complete. Resolve `scripts/render_explainer.py` relative to this skill directory and run:

```text
python3 <skill-directory>/scripts/render_explainer.py \
  --markdown <markdown_path> \
  --html <html_path> \
  --manifest <manifest_path>
```

Do not author ad hoc HTML, CSS, or direct Pandoc commands. The renderer owns the local template, styling, semantic TOC, compact provenance, responsive/print treatment, content escaping, and no-network-asset policy. It consumes the Markdown H1 as the one document title, renders verdict/evidence labels semantically, and refuses to overwrite a completed HTML revision with different bytes. Prepare a new variant if the canonical content changes.

For PR-backed explainers, use the PR URL as `--source`: the renderer exposes **Open PR**, **Changed files**, and **Raw diff** near the title. Link review-level claims, checks, or changed-file navigation to the PR surface; use SHA-pinned blob links only for exact source evidence. Keep all links meaningful rather than turning every mention into a link.

When visual quality is material, inspect the rendered HTML at wide desktop, normal laptop, and mobile widths before handoff. Do not launch a browser or server automatically unless the user asks to interact with it; a local file remains complete without JavaScript.

## Verify and hand off

Before returning the artifact:

1. Re-read cited source locations and confirm every claim still matches them.
2. Open both outputs as text and verify their structure, code escaping, provenance, and links. Render or open the HTML when visual or interactive behavior is part of the request.
3. Confirm the manifest identifies the repository, comparison, snapshot hash, subject, variant, and output names without credentials.
4. Report the exact Markdown, HTML, manifest, and raw-diff paths; say whether the revision was created or reused.
5. Distinguish completed checks, unavailable runtime validation, and unresolved questions.
