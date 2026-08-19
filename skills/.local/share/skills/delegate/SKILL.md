---
name: delegate
description: Spawn a sub-agent from a saved role definition instead of an ad-hoc prompt. Use when delegating a scoped task in a harness that does not load agent files natively, such as Codex.
---

# Delegate to a saved role

Role definitions live in `~/.local/share/subagents/<name>.md`. Each file is a complete
system prompt for one role — reviewer, simplifier, debugger, log analyst, PR reviewer —
written for an agent that starts with no conversation history.

Claude Code and OpenCode load these files themselves, so this skill is for harnesses that
do not. Codex is the case that needs it: it spawns sub-agents as thread forks and reads no
agent definition files, and it will not delegate at all unless a skill or `AGENTS.md` asks
it to.

## Choose the role

Never guess from the filename. List the directory, then read just the frontmatter of the
plausible candidates and match on the `description`:

```bash
ls ~/.local/share/subagents/
awk '/^---$/ { fence++; next } fence == 1' ~/.local/share/subagents/<name>.md
```

If nothing fits the task, stop and write your own prompt. A role that half-matches steers
the sub-agent worse than no role at all.

## Spawn it

Every agent shares this filesystem and working directory, so the child reads its own role
file. Do not paste the body into the prompt; pass the path.

Call `spawn_agent` with:

- `fork_turns="none"`. Required. These definitions assume a clean context, and a
  full-history fork also refuses the overrides below.
- `task_name` set to the role name, so the transcript shows which role is running.
- A brief with three parts: read and follow `~/.local/share/subagents/<name>.md`; the task
  itself; and every path, diff range, log file, ticket, or PR number the work needs. The
  child cannot see this conversation, so anything you leave out is simply gone.

Two fields in the role file are for Claude and do not translate:

- `model:` holds a Claude alias (`sonnet`, `opus`). It names no model in another harness.
  Let the child inherit the session model unless the user asks otherwise.
- `tools:` is a Claude allow-list. Read it as a statement of what the role needs, then give
  the child the local equivalent — `pup` for Datadog, `glean_default__search` for internal
  docs, `gh` for GitHub. Tool names differ per harness: Claude prefixes MCP tools with
  `mcp__`, Codex does not.

## Come back with the answer, not the transcript

Relay what the user needs from the child's final answer. The point of delegating is that
the intermediate reading stayed out of this context; quoting it back defeats that.
