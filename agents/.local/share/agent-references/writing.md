# Writing PRs and comparison diagrams

Read the section for the artifact being written. Repository templates take precedence over these defaults.

## PR descriptions

Explain the current behavior and concrete problem, then connect the change to its intended result. Write for a reviewer who has not read the conversation. Preserve exploratory wording when the author supplied it, and settled wording when the decision is settled.

Include details and open questions that affect the review decision. Use connected prose, with one paragraph per line so the web UI can wrap it. Use headings only when they help or the repository template requires them.

Testing describes meaningful behavior or environment validation. Attribute each check to its actual actor. Report routine hooks, formatting, lint, and generic green CI to Eric separately. If only routine automation ran, omit an optional Testing section. State material limits of the evidence once, where they affect the review.

Link evidence that the diff cannot show: an unchanged caller, prior implementation, workflow result, decision, or dependency. Name whether a code link shows the PR head, its base, or another revision. Pin the revision when it matters to the claim.

Describe the current artifact. Discuss an absence when readers would expect the missing behavior, such as a migration's rollback path. Keep superseded implementation history in the relevant commit or review thread.

If a required screenshot or graph cannot be captured, leave a precise placeholder:

```html
<!-- TODO: paste screenshot of <dashboard/query> showing <metric> here -->
```

## Comparison diagrams

Keep matching nodes in the same order and positions across before/after views. Change only the relevant edge or state. In GitHub Mermaid flowcharts, an invisible `~~~` edge can reserve a rank in the before view; omit edge labels when they shift matching nodes.
