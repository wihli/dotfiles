---
name: explain-diff
description: Create persistent local literate diffs with review priorities and expandable explanations. Use for PRs, commit ranges, patches, or worktree changes.
---

# Explain Diff

Help the reader choose where to spend attention. Lead with what changed, why it matters, and where to start reviewing. Let the reader request background, code, and evidence as needed. The literate diff should reduce the work of reconstructing the change across files.

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

Use a stable subject such as a PR URL, `pr:<number>`, `range:<base>...<head>`, or `worktree:<branch>`. Use `progressive` as the default variant to identify this reading format. Name a different variant when the audience, review focus, or requested rewrite changes.

The helper stores durable artifacts under `$XDG_DATA_HOME/explain-diff` (default `~/.local/share/explain-diff`) and the mutable lookup index under `$XDG_STATE_HOME/explain-diff` (default `~/.local/state/explain-diff`). `$XDG_CACHE_HOME` is only appropriate for disposable rendering intermediates, never the explainer or its provenance.

The helper prints JSON containing `revision_dir`, `markdown_path`, `html_path`, `manifest_path`, and whether the exact subject, snapshot, and variant were reused. It creates a content-addressed revision for changed input and moves `latest` to that revision. Treat a revision as immutable after both outputs exist. If an exact revision already contains both outputs, return it instead of silently regenerating it.

## Write the first screen

Write the canonical explanation to the returned Markdown path. Make the opening useful without expansion:

- Title the actual change. For an extraction, name the code being shared; do not present existing behavior as a new fix.
- Explain the outcome and motivation in a few sentences. Use one concrete input, event, or before/after example when it makes the change easier to grasp. Give intuition before details without requiring a background chapter.
- Separate existing behavior, code that moves, and behavior that changes. State the result of the analysis; omit narration about conducting the review.
- Offer a few prioritized review questions with a short answer or consequence and a link to the relevant section. Order them by what deserves attention. Do not invent findings to fill a quota.
- Keep material risks, uncertainty that affects a decision, and limits on an approval recommendation visible. Put exact revisions and artifact metadata in a final `## Provenance` section.

Aim for an opening the reader can absorb in about a minute. Adapt to the change and requested depth; a small change may need no expandable detail.

## Let the reader choose depth

Organize the walkthrough around questions about behavior or concrete conclusions. Keep each section heading and its takeaway visible. A reader who jumps directly to a section should understand the question, answer, and consequence without remembering earlier paragraphs.

Put supporting background, small before/after code excerpts, source links, and verification details in native `<details>` blocks. Each `<summary>` should say what the reader will learn, such as a consequence or a specific reason to inspect the code. Avoid labels such as "Details" or "More information." Prefer one level of expansion.

Use this Markdown pattern. Keep blank lines around the block content so code and links render correctly:

````markdown
## Which IDs can reach the scheduler?

**Changed behavior:** Any string now passes the ID filter. Check how the scheduler handles malformed IDs.

<details>
<summary>The replacement removes the ID-format check</summary>

```diff
- .filter(isRecordId)
+ .filter(id => typeof id === "string")
```

[Inspect the changed predicate](raw.diff)

</details>
````

Keep headings and internal link targets outside collapsed blocks so navigation always reaches visible context. Blocks start closed. Use a short causal reading order within each explanation; connect code from different files when it answers the same question. Explain unchanged code only when it establishes a constraint the reviewer needs.

Keep evidence beside the claim it supports. **Observed** means directly supported by inspected evidence; **Inferred** means a reasoned conclusion; **Unresolved** means missing evidence or an open decision. Use these labels when certainty affects interpretation, not on every paragraph. Distinguish an existing reviewer's question from an established defect. Keep detailed review discussion separate from background teaching.

State what verification establishes and what remains unknown in a short visible takeaway. Expand into test behavior, runtime evidence, and source references only as needed. The explainer complements the raw diff; it does not replace reviewing it.

## Render deterministic HTML

Markdown is canonical; render it after it is complete. Resolve `scripts/render_explainer.py` relative to this skill directory and run:

```text
python3 <skill-directory>/scripts/render_explainer.py \
  --markdown <markdown_path> \
  --html <html_path> \
  --manifest <manifest_path>
```

Use only the native disclosure markup shown above; do not author ad hoc page HTML, CSS, scripts, or direct Pandoc commands. The renderer owns the local template, styling, semantic TOC, compact provenance, responsive/print treatment, content escaping, and no-network-asset policy. It consumes the Markdown H1 as the one document title, renders verdict/evidence labels semantically, and refuses to overwrite a completed HTML revision with different bytes. Prepare a new variant if the canonical content changes.

For PR-backed explainers, use the PR URL as `--source`: the renderer exposes **Open PR**, **Changed files**, and **Raw diff** near the title. Link review-level claims, checks, or changed-file navigation to the PR surface; use SHA-pinned blob links only for exact source evidence. Keep all links meaningful rather than turning every mention into a link.

When visual quality is material, inspect the rendered HTML at wide desktop, normal laptop, and mobile widths before handoff. Do not launch a browser or server automatically unless the user asks to interact with it; a local file remains complete without JavaScript.

## Verify and hand off

Before returning the artifact:

1. Re-read cited source locations and confirm every claim still matches them.
2. Read only the opening, headings, takeaways, and closed summaries. Can the reader explain the change and choose where to review next? Jump into a middle section and check that it restores context after an interruption.
3. Open both outputs as text and verify their structure, code escaping, provenance, and links. Check that material risks remain visible with details closed. Render or open the HTML when visual or interactive behavior is part of the request; verify expansion, keyboard focus, and navigation to visible headings.
4. Confirm the manifest identifies the repository, comparison, snapshot hash, subject, variant, and output names without credentials.
5. Report the exact Markdown, HTML, manifest, and raw-diff paths; say whether the revision was created or reused.
6. Distinguish completed checks, unavailable runtime validation, and unresolved questions.
