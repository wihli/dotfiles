# Writing for human readers

Read "Reader attention" first, then the section for the artifact being written. Repository templates take precedence over these defaults.

## Reader attention

Readers scan before they read, and many stop after the first screen. Order,
paragraphing, headings, and emphasis decide what that scan finds.

Give visual prominence to what the reader needs to understand or decide. Use
emphasis sparingly enough that it remains meaningful, and keep essential
context and uncertainty visible.

- Put the request, conclusion, or decision first. Background follows for the
  reader who wants it.
- Get the ordinary paragraphs right before adding structure: one idea per
  paragraph, with a blank line between paragraphs.
- Emphasis works by contrast. Bold the few words the reader must not miss,
  usually the action, the decision, or a risk. A bold lead-in on every bullet,
  a bold whole paragraph, and bold combined with italic or capitals all spend
  that contrast. Headings, callouts, emoji, and color draw on the same
  attention.
- Add headings when the text is long enough that the reader will navigate it;
  two levels are usually enough. Name what the section says, so a reader who
  jumps there knows where they are.
- Use a numbered list for ordered steps, a bulleted list for parallel items,
  and a table when several items are compared on the same attributes. Keep
  reasoning in connected prose.
- Use code formatting for literal text the reader may type, search for, or
  match exactly: identifiers, commands, paths, and values. It is not a form of
  emphasis.
- Present the same kind of thing the same way throughout, such as one label
  per status.
- Keep risks, open questions, and limits on a recommendation in the visible
  text. Collapsed sections and trailing notes are for supporting detail.

## Slack messages

The first line appears in notifications, channel previews, and search results.
Put the request or conclusion there, and name who needs to act when someone
does.

Keep the message to a few short paragraphs separated by blank lines. Put longer
evidence, logs, or command output in a thread reply or a linked document.

Markdown headings and tables do not render in a posted message. Use a short
bold label on its own line in place of a heading, and a list or code block in
place of a table. Beyond those labels, bold at most the action or decision.

## Jira tickets and comments

Lead with why the work matters and what should change. Use short paragraphs to
connect the problem, intended outcome, and relevant constraint. Use lists for
acceptance criteria, parallel items, or ordered steps; add headings only when
they help readers navigate.

Include only technical detail that helps someone understand or act. Prefer
descriptive links to long URLs. Keep local worktree paths, agent-resume
instructions, and command/build inventories in the working handoff.

Descriptions hold the task and completion criteria. Put progress in comments:
start with the result or blocker, then what happens next. Use Jira's timestamps
instead of repeating dates. Before posting, read it as a teammate who has not
seen the chat.

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
The template's headings carry the structure; add no heading levels beneath
them. When one thing must stand out, make it the material risk or the action
the reviewer must take, with a short bold lead-in. Leave routine testing and
unchanged behavior at normal weight.

If a required screenshot or graph cannot be captured, leave a precise placeholder:

```html
<!-- TODO: paste screenshot of <dashboard/query> showing <metric> here -->
```

## PR review comments

A comment posted under Eric's name on someone else's PR is a short note to a
colleague. The structured finding (severity, source quote, counter-evidence)
is for the report to Eric and stays there.

Write one paragraph of plain prose: what happens today, what this change does
to it, and the consequence with how often it would occur. Use no headings,
lists, bold, or severity labels. Match the certainty to the evidence; "I
think" fits a consequence nobody has observed. Put each link on the words it
supports, pinned to a commit and line, and keep only the links the author
needs to see why. When the author's own testing would have missed it, say why.
Add one line for what is untested, and a suggestion block when the fix is a
line or two.

Example:

> Nightly deploys are started by `deploy-bot[bot]` ([example run](…)), and the
> action won't run for a bot unless it's listed in `allowed_bots` ([docs](…),
> [the check](…)). So I think every nightly deploy would show the fallback
> note instead of a summary. Manual runs still work, so local testing wouldn't
> show it.
>
> Not tested end to end. This is from the action's docs and source at the
> pinned commit.

## Documents and HTML pages

For substantial Google Docs, formatted documents, and reader-facing HTML
(explainers, review walkthroughs, or shareable reports), read
[Typography](typography.md): the shared principles and only the section for
that output medium. Read the theme options only when choosing a visual style.
Skip that reference for PR descriptions, Slack, plain Markdown, small text
corrections, and unrelated code changes; use the sections above instead.

## Comparison diagrams

Keep matching nodes in the same order and positions across before/after views. Change only the relevant edge or state. In GitHub Mermaid flowcharts, an invisible `~~~` edge can reserve a rank in the before view; omit edge labels when they shift matching nodes.
