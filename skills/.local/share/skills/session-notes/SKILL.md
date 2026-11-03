---
name: session-notes
description: Summarize verified session changes, decisions, blockers, and next actions for signoff or handoff, using the project's existing notes or checkpoint destination.
---

# Session Notes

Summarize the requested session from its conversation, source changes, and observed check results. Identify the relevant commits and uncommitted work; do not attribute unrelated recent work to this session.

Include the material facts needed to resume:

- Changes and their purpose, grouped by topic.
- Decisions and constraints, with their source and scope.
- Checks performed and their results, including remaining gaps.
- Uncommitted work, unresolved questions, blockers, and concrete next actions.
- Any personal notes the user already supplied.

Follow the repository's existing log or handoff format and destination. If the user requests a checkpoint, use the checkpoint workflow. Preserve existing history and update only the requested handoff material.

When no destination is established, provide the summary in chat; save a file when requested. Finish the signoff using the available facts, and identify any missing information that affects the next session. Report the saved path when a file was written.
