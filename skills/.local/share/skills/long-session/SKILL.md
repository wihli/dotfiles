---
name: long-session
description: Prepare a bounded Ralph loop when the user names long-session or explicitly requests Ralph-loop preparation. Ordinary long or overnight tasks do not select this workflow.
---

# Ralph Loop Preparation

Prepare the user's requested loop using the project's existing acceptance criteria and handoff conventions. Reuse decisions and authorization already supplied; ask only for missing choices that affect scope, permitted actions, or the execution bound.

## Prepare the run

- Establish the target checkout, objective, permitted actions, completion evidence, and an explicit iteration or time bound. Do not invent an unattended runtime budget.
- Read the repository's instructions and identify checks that can distinguish completion from partial progress. Add tests when the changed behavior needs them; passing tests alone must not stand in for other acceptance criteria.
- Use the existing project plan, issue list, or checkpoint as the task record. Record exact constraints and unresolved dependencies where the project already keeps handoffs.
- Check the installed Ralph-loop runner's documentation and command syntax. If the runner is unavailable, deliver the prepared task and report that limitation.

## Prepare the loop prompt

Include the objective, checkout, allowed changes, completion criteria, check commands, execution bound, and handoff destination. Require the loop to preserve unrelated work, report failed checks, and stop when the bound or an authorization boundary is reached. It may claim completion only when the requested outcome and its acceptance criteria are satisfied.

Start the verified command when the user's request authorizes launch. Otherwise provide the prepared prompt and command. Record the observed run state and results; distinguish preparation from a started or completed loop.
