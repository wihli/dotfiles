# Writing PRs and comparison diagrams

Read the section for the artifact being written. Repository templates take precedence over these defaults.

## PR descriptions

Write for the human deciding how to review the change. The opening should make
the purpose and resulting behavior clear without reading the diff or chat.
Preserve the author's intent and certainty, including exploratory wording.

For an ordinary PR, aim for roughly 100–250 words across the required sections.
This is a default, not a quota: use fewer for a small change and add detail only
for a design choice, risk, dependency, or rollout decision the reviewer needs.
Preserve the repository's required headings and fields. A heading usually needs
one short paragraph, often one or two sentences.

Explain what changes and why. Include a concrete example when it makes the
behavior easier to understand. Include implementation detail only when it helps
the reviewer assess the design. Use a table only when the comparison itself is
needed for that decision; keep full inventories in the task's existing handoff
or linked record.

Testing should summarize the behavior verified and any material gap, with one
or two useful evidence links. Attribute checks to their actual actor. Keep
command lists, routine hooks, test counts, intermediate SHAs/builds, and the
agent's review process in the verification record unless a specific item changes
the review decision. Required AI disclosure should briefly name the models and
primary task, without narrating the agent workflow.

Deployment should retain material permission changes, automatic apply triggers,
unrelated plan actions, blockers, and rollback constraints when they affect the
merge decision. State each once. Brevity must not hide a risk or missing proof.

Link evidence the diff cannot show, such as a live result, decision, unchanged
caller, or dependency. Name and pin the source revision when the claim depends
on it. Prefer durable sources reviewers can access. Do not move
a wall of text into a collapsed section or a new document just to meet a word
target. Keep detailed working records where the task already maintains them.

Before publishing or updating, reread from a new reviewer's perspective: can
they quickly tell what changes, why, and what needs attention? Cut repeated
context and details available in the diff or CI UI. On updates, replace stale
testing or rollout text; do not append a chronological progress log.

Use connected prose, with one paragraph per line so the web UI can wrap it.
If a required screenshot or graph cannot be captured, leave a precise placeholder:

```html
<!-- TODO: paste screenshot of <dashboard/query> showing <metric> here -->
```

## Comparison diagrams

Keep matching nodes in the same order and positions across before/after views. Change only the relevant edge or state. In GitHub Mermaid flowcharts, an invisible `~~~` edge can reserve a rank in the before view; omit edge labels when they shift matching nodes.
