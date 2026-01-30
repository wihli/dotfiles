---
name: code-context
description: |
  Trace organizational/business context behind code decisions - "code archaeology."
  Use when user asks "why" about code patterns, config values, IaC decisions, or historical choices.
  Triggers: "why is this...", "what's the context for...", "who decided...", "when was this added...",
  "explain the history of...", understanding business/organizational reasoning (not technical correctness).
---

# Code Context

Investigate the organizational context behind code decisions by tracing through version control history, PRs, tickets, and documentation.

## Workflow

1. **Git archaeology** - Find when/who/why the pattern was introduced
2. **Follow breadcrumbs** - PRs, Jira tickets, linked docs
3. **Expand search** - Guru for broader organizational context
4. **Company Knowledge fallback** - Provide prompt for Slack/GDrive/Gmail search

## Tools Hierarchy

```
git log/blame → GitHub PRs → Jira tickets → Guru → Slack/GDrive/Gmail (prompt fallback)
```

## Git Spelunking

Find when pattern was introduced:
```bash
git log -S "pattern" --oneline --all
git log -p --all -S "pattern" -- "*.tf"  # with diff, file type filter
```

Find who and why:
```bash
git blame -L 10,20 path/to/file
git log --follow -p -- path/to/file  # full history with renames
```

Search commit messages:
```bash
git log --all --grep="CIDR\|subnet" --oneline
```

## GitHub CLI (`gh`)

Find PRs that touched a file:
```bash
gh pr list --state all --search "path/to/file" --limit 20
```

Get PR details including description and comments:
```bash
gh pr view 12345 --comments
```

Search PRs by keyword:
```bash
gh pr list --state all --search "CIDR subnet" --limit 10
```

Get commits in a PR:
```bash
gh pr view 12345 --json commits
```

## Jira CLI (`acli`)

Search for tickets by keyword:
```bash
acli jira --action getIssueList --search "text ~ 'CIDR' OR text ~ 'subnet'" --outputFormat 2
```

Get ticket details:
```bash
acli jira --action getIssue --issue INFRA-1234
```

Search by date range:
```bash
acli jira --action getIssueList --search "created >= 2024-01-01 AND text ~ 'github actions ip'"
```

## Guru MCP

Use Guru to search organizational knowledge base:
- `mcp__guru__search_cards` - Search for relevant documentation
- `mcp__guru__get_card` - Get full card content by ID

Search patterns:
- Technical decisions: "CIDR", "subnet", "IP allocation"
- Process docs: "github actions", "runner setup"
- Team knowledge: team names, project codenames

## Output Format

Always provide:
1. **Summary** - The "why" in 2-3 sentences
2. **Timeline** - Key commits/PRs/tickets with dates
3. **References** - Links for user verification
4. **Methodology** - Commands used (teach the user)
5. **Related terms** - Concepts user might not know to search for

## Company Knowledge Fallback (Slack/GDrive/Gmail)

When context likely exists in company communications but is unavailable here, provide a prompt for ChatGPT Company Knowledge search:

```
I'm investigating why [specific pattern/decision]. Git history shows it was
introduced in [commit/PR] by [author] on [date]. The commit message says
"[message]" but doesn't explain the business reasoning.

Search Slack, Google Drive, and Gmail around [date range] for context about [topic].
Slack channels: #[channel1], #[channel2]
Search terms: [term1], [term2], [term3]
```

## Tips

- Commit messages often reference PR numbers (`#1234`) or Jira tickets (`INFRA-1234`)
- PR descriptions usually have more context than commit messages
- Authors may have moved teams - check git blame for current maintainers
- Related search terms: if searching "CIDR", also try "subnet", "IP range", "network mask", "/29"
