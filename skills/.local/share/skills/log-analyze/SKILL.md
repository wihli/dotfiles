---
name: log-analyze
description: Analyze local project logs under XDG state directories, summarize errors and warnings, inspect run metadata, and report timelines and key observations.
metadata:
  short-description: Analyze local logs
---

# Log Analyze

Analyze logs for: $ARGUMENTS

Follows convention in `~/.claude/conventions/logging.md`.

## 1. Resolve Project

If `$ARGUMENTS` names a project, use it. Otherwise derive from cwd:

```bash
basename "$(pwd)" | tr '[:upper:]_ ' '[:lower:]--'
```

## 2. Find Logs

Check convention path first, fall back to flat files:

```bash
PROJECT="<resolved>"
LOGDIR="${XDG_STATE_HOME:-$HOME/.local/state}/$PROJECT/runs/latest"
if [ ! -d "$LOGDIR" ]; then
  LOGDIR="${XDG_STATE_HOME:-$HOME/.local/state}/$PROJECT"
fi
ls -la "$LOGDIR"/*.log 2>/dev/null
```

Note the run dir name — it contains the git SHA and dirty flag.

## 3. Error Summary

Count errors by event type:

```bash
jq -r 'select(.level == "error") | .event' "$LOGDIR"/*.log 2>/dev/null | sort | uniq -c | sort -rn
```

For non-JSON logs, fall back:

```bash
grep -i 'error\|exception\|traceback' "$LOGDIR"/*.log 2>/dev/null | head -20
```

## 4. Warning Summary

```bash
jq -r 'select(.level == "warning") | .event' "$LOGDIR"/*.log 2>/dev/null | sort | uniq -c | sort -rn
```

## 5. Timeline (last 20 events)

```bash
jq -r '[.timestamp, .level, .event] | join(" | ")' "$LOGDIR"/*.log 2>/dev/null | sort | tail -20
```

## 6. Run Metadata

```bash
# Run directory name (has timestamp + git SHA)
readlink "${XDG_STATE_HOME:-$HOME/.local/state}/$PROJECT/runs/latest" 2>/dev/null || echo "no latest symlink"

# Log file sizes
du -sh "$LOGDIR"/*.log 2>/dev/null

# Time span
FIRST=$(jq -r '.timestamp' "$LOGDIR"/*.log 2>/dev/null | sort | head -1)
LAST=$(jq -r '.timestamp' "$LOGDIR"/*.log 2>/dev/null | sort | tail -1)
echo "Span: $FIRST → $LAST"
```

## 7. Output Format

Report as:

```
## Log Analysis: {project}
- **Run**: {dirname} (SHA: {sha}, {clean|dirty})
- **Span**: {first_ts} → {last_ts}
- **Files**: {list of log files with sizes}

### Errors ({count})
| Count | Event | First Occurrence |
|-------|-------|------------------|

### Warnings ({count})
| Count | Event |
|-------|-------|

### Recent Activity
{last 10-20 events as timeline}

### Key Observations
{patterns, anomalies, recommendations}
```
