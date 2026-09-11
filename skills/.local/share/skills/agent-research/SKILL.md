---
name: agent-research
description: Run or inspect a personalized weekly scan of evidence-backed coding-agent research. Use for agent research scans or the weekly research brief; not ordinary PR reviews or general news.
---

# Agent research

Use the installed `agent-research` command. Its worker and assets live under this skill's `scripts/` directory.

- `agent-research --status` reads the latest local report and run status without a model call.
- `agent-research` runs only when the weekly scan is due.
- `agent-research --run` starts a paid scan now. Use when the user requests a fresh scan.

Read configuration from `$XDG_CONFIG_HOME/agent-research/config.json` and the workflow profile it names. Missing configuration must produce an explicit error. Keep public source queries generic; customize the report locally. Save reports, source identities, raw provider output, and token estimates under `$XDG_STATE_HOME/agent-research/`.

Return at most three new useful findings, grounded in sources that were actually read. Include limitations and a practical suggestion the user can try anecdotally during normal work. Do not add experiment planning, benchmark requirements, or automatic skill/instruction changes.

The command's current automated provider is Codex with web search. Calling the command from Claude Code, Codex, Pi, or OpenCode does not change that provider. Report missing runtime or authentication explicitly. A failed or partial scan is not a successful no-news week. The report's API-equivalent estimate excludes search fees and can be incomplete.

To change schedule or scan depth, edit the source-owned configuration and reinstall it. `weekday` uses Monday=0 through Sunday=6. The default is Friday at 09:00 in America/Los_Angeles. The weekly due check catches up once after downtime. `enabled: false` pauses paid scans. Preserve existing approved schedules unless asked to change them.

Automatic retries are limited to two attempts in any seven-day window. Partial scans retain the last complete timestamp and become eligible for a retry after 24 hours. `max_web_calls` is an observed-call cutoff; in-flight calls can exceed it. Each run has a hard process timeout.
