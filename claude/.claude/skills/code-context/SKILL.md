---
name: code-context
description: |
  Trace organizational/business context behind code decisions - "code archaeology."
  Use when user asks "why" about code patterns, config values, IaC decisions, or historical choices.
  Triggers: "why is this...", "what's the context for...", "who decided...", "when was this added...",
  "explain the history of...", understanding business/organizational reasoning (not technical correctness).
  Also triggers on bare terms/identifiers the user wants explored (e.g. "warm-caches", "staging-snapshots").
---

# Code Context

Investigate the organizational context behind code decisions by tracing through version control history, PRs, tickets, and documentation.

## Workflow

1. **Git archaeology** - Find when/who/why the pattern was introduced
2. **Follow breadcrumbs** - PRs, Jira tickets, linked docs
3. **Expand search** - Guru for broader organizational context
4. **Company Knowledge** - Glean MCP for Slack/GDrive/Gmail/Confluence search

## Tools Hierarchy

```
git log/blame → GitHub PRs → Jira tickets → Guru → Glean (Slack/GDrive/Gmail/Confluence)
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

Use Guru to search organizational knowledge base.

**IMPORTANT**: Guru cards can be 10-20k tokens. Always use a haiku subagent to fetch and summarize:

```
Task(
  subagent_type="general-purpose",
  model="haiku",
  description="Summarize Guru card",
  prompt="""
  Fetch Guru card ID '<card_id>' using mcp__guru__get_card.

  Summarize for context: "<your investigation question>"

  Return:
  - Key facts relevant to the question (bullet points)
  - Important dates, people, or decisions mentioned
  - Links to related resources
  - Card URL for reference

  Keep summary under 500 words.
  """
)
```

**Search first** (cheap): `mcp__guru__search_cards(query="mongodb migrations")`
**Then summarize** (via subagent): Use card IDs from search results

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

## Understanding Frames

After gathering facts, apply these 6 lenses to build real understanding. Don't wait for follow-ups — anticipate the deeper questions.

### 1. Parts → Whole
Map how this connects to adjacent systems. What's upstream? Downstream? Trace the full chain from trigger to outcome. A single resource is meaningless in isolation — show how it fits into the pipeline.

### 2. Compare & Contrast
What else solves a similar problem differently in this codebase? Why the divergence? The contrast between approaches often reveals the real constraints better than either approach alone.

### 3. Consequences & Implications
What breaks if this changes? What becomes possible if a constraint lifts? Think both directions — fragility (what could go wrong today) and opportunity (what could be simplified if conditions change).

### 4. Boundaries & Scope
Where does this apply and where does it *not*? What environments, regions, contexts? Knowing the edges prevents false generalizations and scopes the blast radius of changes.

### 5. Assumptions & Prerequisites
What must be true for this to work? Surface the hidden load-bearing walls — config values, installed tools, network access, secrets that must exist. These are invisible until they break.

### 6. Alternatives Not Taken
Why this approach and not something else? Search PR comments, Slack threads, and linked tickets for rejected alternatives. The *absence* of alternatives considered is itself a signal — was this a thoughtful decision or a quick fix?

## Glean MCP (Slack/GDrive/Gmail/Confluence)

Use Glean to search company communications and documents.

> **Note**: If Glean tools aren't available, run `/toggle-glean-mcp enable` first.

**Search** (returns snippets, cheap):
```
mcp__glean_default__search(query="CIDR subnet github actions", app="slack")
mcp__glean_default__search(query="IP allocation", updated="past_month")
```

**Chat** (AI synthesis, moderate cost):
```
mcp__glean_default__chat(message="Why did we choose /29 CIDR for GitHub Actions runners?")
```

**Read document** (can be large - use haiku subagent):
```
Task(
  subagent_type="general-purpose",
  model="haiku",
  description="Summarize Glean doc",
  prompt="""
  Fetch document using mcp__glean_default__read_document(urls=["<url>"]).

  Summarize for context: "<your investigation question>"

  Return key facts, decisions, dates. Keep under 500 words.
  """
)
```

Filter options:
- `app`: slack, gdrive, gmail, confluence, jira, github, notion
- `updated`: today, yesterday, past_week, past_month
- `from`/`owner`: person name
- `after`/`before`: "YYYY-MM-DD"

## Related Term Exploration

When the user provides a bare term or identifier (not a full question), treat it as a request to explore that term in the codebase. Run the standard archaeology workflow:
1. `git log -S "term"` to find introduction
2. `grep` for current usage across file types
3. Read the relevant files for context
4. Follow the same output format (summary, timeline, references, methodology, related terms)

This makes the "Related terms" output from a previous investigation directly actionable — the user can just type one and get the full story.

## Tips

- Commit messages often reference PR numbers (`#1234`) or Jira tickets (`INFRA-1234`)
- PR descriptions usually have more context than commit messages
- Authors may have moved teams - check git blame for current maintainers
- Related search terms: if searching "CIDR", also try "subnet", "IP range", "network mask", "/29"
- **Token efficiency**: Search tools return small results; fetch/read tools return large docs. Always use haiku subagents for full document fetches to avoid context bloat.
