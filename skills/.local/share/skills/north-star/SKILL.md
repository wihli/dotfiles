---
name: north-star
description: Create or update a project's NORTH_STAR.md design contract only when the user names north-star or explicitly requests that contract.
---

# North Star: Project Design Contract

Capture the user's agreed design constraints for a specific project. A new project or difficult feature alone does not select this workflow.

Read the project's instructions, existing design documents, relevant code, and prior decisions. Reuse constraints the user already supplied. Research unresolved choices when evidence can change the decision; ask targeted questions for decisions the user must make.

Write to the project's established contract path, or `NORTH_STAR.md` in its root when no path exists. Keep implementation steps in the project's planning documents.

## Contract contents

- **Goal:** the result the project should achieve.
- **Locked decisions:** user-agreed invariants, boundaries, and rationale. Identify their source and scope.
- **Open questions:** unresolved choices, available evidence, and what would settle them. Keep proposals separate from agreed constraints.
- **Rejected approaches:** the conditions under which an approach failed, supported by source or observed results.
- **Layer requirements:** dependencies or acceptance conditions that the agreed architecture actually needs.
- **Decision log:** dated decisions and their rationale, preserving earlier entries.

Mark a decision locked only when the user has agreed to it. Changing a locked decision requires the user's authorization and a decision-log entry explaining the change. Preserve the original constraint and its history.

Use existing companion documents for plans and current work. Create additional documents only within the requested scope. Report the contract path and any decisions that remain open.
