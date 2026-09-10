---
name: explain-diff
description: Create persistent local literate diffs with review priorities and expandable explanations. Use for PRs, commit ranges, patches, or worktree changes.
---

# Explain Diff

Bring a technically capable reader up to speed without assuming familiarity with this system. Establish what the system does and how its parts relate before explaining the change or asking review questions. Then help the reader choose where to spend attention. The literate diff should reduce both missing context and the work of reconstructing the change across files.

## Establish the comparison

1. Resolve the repository, base, head, change source, intended audience, and requested focus. Ask only when different answers would materially change the explanation.
2. Read repository guidance and preserve the worktree. Treat this as read-only review unless the user separately asks for code changes.
3. Capture the exact raw diff in a temporary file. For worktree changes, include staged, unstaged, and relevant untracked files while respecting ignore rules.
4. Inspect the diff for credentials, `.env` contents, private keys, or other secrets before persisting it. Stop and identify the unsafe input rather than copying a suspected secret into an artifact.
5. Read enough pre-change code, current code, callers, tests, and nearby documentation to explain what existed before. Do not infer architecture from changed lines alone.

## Establish the reader's starting point

Assume practically zero context about the affected system unless the user demonstrates otherwise. Familiarity with a technology does not imply knowledge of this project's jobs, services, interfaces, or terminology.

- Start from what the reader says they know. Explain the connection and its limits: two tasks may use the same execution service while running different programs for different purposes.
- Trace the existing flow: who starts the work, where they start it, what runs, what information it uses, and what it changes. Follow callers and documentation until you can explain those relationships in ordinary language.
- Introduce each necessary component by its purpose before relying on its name. Locate interfaces concretely: a field in a named page or command, rather than an unexplained "dropdown" or "manual runner".
- Define terms through behavior and one concrete example when useful. A glossary of expanded acronyms does not explain how the system works. Do not use an identifier as its own explanation.

Use this context to select what the reader needs, not to write a general textbook. If a relationship cannot be verified, say what is unknown rather than inventing a familiar analogy.

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
- Explain the existing system and the concrete problem before the outcome. Name the actor, task, and place where the change takes effect. Connect these to the reader's known starting point. Give intuition before details; keep this essential background visible rather than behind an expansion.
- Separate existing behavior, code that moves, and behavior that changes. State the result of the analysis; omit narration about conducting the review.
- After that orientation, offer review priorities only when they help. Every question must use concepts already explained and state why the answer matters. A small change may need only a short conclusion. Do not make the reader answer architectural questions to discover what the PR is about.
- Keep material risks, uncertainty that affects a decision, and limits on an approval recommendation visible. Put exact revisions and artifact metadata in a final `## Provenance` section.

Aim for an opening the reader can absorb in about a minute, but do not remove prerequisite context to meet that target. Diff size does not determine how much orientation an unfamiliar system needs. Keep deeper implementation detail optional.

## Let the reader choose depth

Organize the walkthrough around questions about behavior or concrete conclusions. Keep each section heading and its takeaway visible. A reader who jumps directly to a section should understand the question, answer, and consequence without remembering earlier paragraphs.

Keep the context needed to understand the opening and review questions visible. Put optional background, small before/after code excerpts, source links, and verification details in native `<details>` blocks. Each `<summary>` should say what the reader will learn, such as a consequence or a specific reason to inspect the code. Avoid labels such as "Details" or "More information." Prefer one level of expansion.

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

Keep headings and internal link targets outside collapsed blocks so navigation always reaches visible context. Blocks start closed. Use a short causal reading order within each explanation; connect code from different files when it answers the same question. Explain unchanged code when it establishes the system model or a constraint the reviewer needs.

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
2. Read only the opening, headings, takeaways, and closed summaries from the user's stated starting point. Can the reader say what the system does, how it relates to what they know, where the change appears, and why it matters? Check every review question for an unexplained prerequisite. Add the missing explanation before the question, or omit the question. Jump into a middle section and check that it restores context after an interruption.
3. Open both outputs as text and verify their structure, code escaping, provenance, and links. Check that material risks remain visible with details closed. Render or open the HTML when visual or interactive behavior is part of the request; verify expansion, keyboard focus, and navigation to visible headings.
4. Confirm the manifest identifies the repository, comparison, snapshot hash, subject, variant, and output names without credentials.
5. Report the exact Markdown, HTML, manifest, and raw-diff paths; say whether the revision was created or reused.
6. Distinguish completed checks, unavailable runtime validation, and unresolved questions.
