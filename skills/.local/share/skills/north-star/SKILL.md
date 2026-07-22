---
name: north-star
description: |
  Create an immutable design contract for a new project.
  Collaborative process: research → discuss constraints → lock decisions → write doc.
  Usage: /north-star [project-name]
---

# North Star: Project Design Contract

Create NORTH_STAR.md — an immutable design contract whose primary audience is future LLM coding agents. Prevents agents from weakening assumptions, skipping validation, re-exploring dead ends, or mixing concerns.

## When to Use

- Starting a new project or major feature
- Pivoting an existing project to a new direction
- Multiple prior attempts have failed and you need to lock lessons learned

## Process

### 1. Get Project Context

If no project name given, ask: "What are we building?"

Gather:
- Existing code, prior attempts, lessons learned
- User's goals, constraints, budget, timeline
- What's been tried and failed (with evidence)

### 2. Research Phase

Spawn parallel research (use `/research` pattern or Task agents):
- **External**: best practices, published approaches, academic papers
- **Codebase**: existing patterns, reusable components, prior art
- **Pitfalls**: common mistakes, failure modes, "lessons learned"

### 3. Collaborative Discussion

This is where the value lives. Ask targeted questions to lock constraints:
- **Architecture**: what's the core abstraction? (e.g., "strategy is a pure function, execution owns async state")
- **Scope**: what's the proving ground vs end goal?
- **Ordering**: what must be true before the next layer?
- **Kill list**: what's been tried and should NOT be revisited? Why? (cite evidence)
- **Open questions**: what must be measured empirically before deciding?

Don't rush this. The NORTH_STAR is only as good as the discussion that produces it.

### 4. Write NORTH_STAR.md

Create `NORTH_STAR.md` in project root:

```markdown
# NORTH STAR — <Project Name>

Immutable design contract. Audience: LLM coding agents.
Append-only decision log at bottom. Do not weaken constraints.

## Goal
<1-2 sentence summary>

## Architecture — LOCKED
<Core abstraction, separation of concerns, what never mixes>

## Constraints

### LOCKED (do not change without decision log entry)
- <Constraint 1>: <rationale>
- <Constraint 2>: <rationale>

### OPEN (measure empirically)
- <Question 1>: <what we don't know, how to find out>
- <Question 2>: <default assumption + plan to validate>

## Layers
<Ordered implementation layers, each with gate criteria>

Layer-gate rule: each layer must pass its criteria before
the next layer is added. Do not skip. Do not build Layer N
to "fix" a broken Layer N-1.

## Anti-Patterns — DO NOT
1. <Thing an agent will try> — <why it fails, with evidence>
2. <Another thing> — <citation from prior work>

## Decision Log
| Date | Decision | Rationale |
|------|----------|-----------|
| <date> | Created NORTH_STAR | Initial constraints from research + discussion |
```

### 5. Companion Docs (Optional)

The three-doc hierarchy for larger projects:

| Doc | Scope | Mutability |
|-----|-------|------------|
| **NORTH_STAR.md** | Immutable constraints, kill list, gate rules | Append-only (decision log) |
| **ROADMAP.md** | Full vision, research findings, confidence ladder | Updated as we learn |
| **PROMPT.md** | Current phase spec, acceptance criteria, "done" definition | Replaced per phase |

Only create ROADMAP.md and PROMPT.md if the project warrants it.
Ask the user before creating companion docs.

### 6. Confirm

Output: "NORTH_STAR.md written. Review the LOCKED constraints — once we start building, these don't change without a decision log entry."

## Key Principles

- **Destination, not path.** NORTH_STAR defines *what* and *why* — constraints, invariants, kill list. It does NOT contain implementation plans, phases, timelines, or specs. Those belong in ROADMAP.md / PROMPT.md.
- **Primary audience is LLM agents**, not humans. Be explicit about what NOT to do.
- **Evidence over opinion**. Every killed approach needs a citation (which codebase, what result).
- **LOCKED means locked**. Changes require a decision log entry with rationale.
- **OPEN means measure**. Don't guess — design experiments to answer open questions.
- **Layer gates prevent complexity masking losses.** Each layer independently viable.
- **The discussion IS the deliverable.** A NORTH_STAR written without thorough discussion is just a template.
