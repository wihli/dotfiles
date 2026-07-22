---
name: research
description: |
  Research-first design for any implementation task.
  Spawns parallel research agents before proposing architecture.
  Usage: /research [topic] [agents=3]
---

# Research

Research before code. Spawns parallel agents to gather context, then synthesizes into a design spec.

## Process

### 1. Get Topic
If no topic provided, ask: "What are we designing/building?"

### 2. Parse Options
- `agents=N` sets agent count (default 3)
- Example: `/research auth system agents=4`

### 3. Spawn Parallel Research Agents

Launch N agents simultaneously using Task tool with `subagent_type=Explore`:

**Agent 1: External Research**
- Web search current best practices, papers, approaches
- Look for recent (2025-2026) implementations, tutorials
- Find authoritative sources

**Agent 2: Codebase Analysis**
- Search current codebase for existing patterns
- Find related code, similar implementations
- Identify reusable components

**Agent 3: Pitfalls & Edge Cases**
- Research common mistakes, failure modes
- Find edge cases, gotchas, "lessons learned" posts
- For data-heavy domains: data leakage, selection bias, overfitting

**Agent 4+ (if requested): Domain-Specific**
- Additional agents for specific research angles
- User can specify focus in topic description

### 4. Synthesize Findings

Wait for all agents. Combine findings into coherent summary.

### 5. Clarifying Questions

Based on research, ask 2-4 targeted questions:
- Choices research surfaced
- Tradeoffs to consider
- Scope decisions

### 6. Write Design Spec

Create `design-<topic-slug>.md` in CWD:

```markdown
# Design: <Topic>
Date: <timestamp>

## Goal
<1-2 sentence summary of what we're building>

## Research Findings

### Best Practices
- <key findings from external research>

### Existing Codebase
- <relevant patterns found>
- <reusable components>

### Pitfalls to Avoid
- <common mistakes>
- <edge cases to handle>

## Proposed Approach
<recommended architecture/strategy based on research>

## Risks
- <identified risks and mitigations>

## Requirements
- Data: <what data needed>
- APIs: <external services>
- Dependencies: <libraries, tools>

## Open Questions
- <unresolved decisions>
- <things to validate during implementation>

## Next Steps
1. <first concrete action>
2. <second action>
```

### 7. Confirm

Output: "Design spec written to `<filename>`. Review before implementing."

## Example

```
User: /research JWT auth system

Claude: [Spawns 3 parallel agents]
- Agent 1: Searching web for JWT auth best practices 2025-2026...
- Agent 2: Scanning codebase for existing auth patterns...
- Agent 3: Researching JWT pitfalls (token rotation, revocation, etc.)...

[Agents complete]

Based on research, a few questions:
1. Session length: short-lived access tokens + refresh, or long-lived?
2. Storage: httpOnly cookies or localStorage?
3. Do you need role-based access control?

[User answers]

[Writes design-jwt-auth-system.md]

Design spec written to `design-jwt-auth-system.md`. Review before implementing.
```
