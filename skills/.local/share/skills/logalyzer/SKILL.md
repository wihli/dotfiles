---
name: logalyzer
description: Summarize large log files token-efficiently for debugging. Use for log analysis, .log or stderr captures, and what-went-wrong questions.
---

# Logalyzer

Analyze large logs without exhausting context. Extract signal, summarize findings, enable next-step debugging.

## Quick Start

Run the analyzer script from this skill directory for a complete summary:

```bash
scripts/analyze.sh /path/to/logfile.log
```

Options:
- `--errors-only` - skip warnings, focus on errors
- `--max-samples N` - number of sample excerpts (default: 3)
- `--context N` - lines of context around samples (default: 5)

The script outputs: metadata, severity counts, normalized error patterns, temporal analysis, stack traces, samples, and common issue detection.

For project-scoped logs under `${XDG_STATE_HOME:-$HOME/.local/state}`, read `references/xdg-project-logs.md` and use its run metadata and structured JSON workflow.

## Input modes

| Input | Mode |
|-------|------|
| `/path/to/file.log` | Analyze that file |
| `path1.log path2.log` | Diff the two (before and after) |
| `xdg` | Recent logs under `${XDG_STATE_HOME:-$HOME/.local/state}` |
| `journalctl` | systemd journal |
| `docker` | Docker or compose logs |
| `project` | `.log` files under the working directory |
| `system` | `/var/log` |
| nothing, or a vague ask | Discover, in the order below |

Discovery order, stopping at the first hit. Pick the most recently modified candidate;
ask which to analyze when several look relevant.

```bash
find . -name "*.log" -type f -mtime -1 -exec ls -lt {} + 2>/dev/null | head -5   # project logs
rg -l -i "log_file|LOG_DIR|FileHandler" --type py --type js --type toml 2>/dev/null | head -3   # where the code writes
ls -lt ~/.local/state/**/*.log 2>/dev/null | head -5   # XDG state
ls -lt /var/log/*.log 2>/dev/null | head -5            # system
```

### journalctl

```bash
journalctl --priority=err --since "1 hour ago" --no-pager | head -50
journalctl -u SERVICE_NAME --since "1 hour ago" --no-pager | tail -100
```

### Docker

```bash
if [[ -f docker-compose.yml ]] || [[ -f compose.yml ]]; then
    docker compose logs --tail 100 2>&1
else
    docker ps --format '{{.Names}}' | head -1 | xargs -I {} docker logs {} --tail 100
fi
```

## Manual Commands

Use these for targeted follow-up or when the script output needs refinement.

### Metadata

```bash
wc -l "$LOG" && ls -lh "$LOG"
head -1 "$LOG" && tail -1 "$LOG"
```

### Severity Counts

```bash
rg -c -i "error|exception|fail" "$LOG"
rg -c -i "warn" "$LOG"
```

### Unique Error Patterns (normalized)

```bash
rg -i "error|exception|fail" "$LOG" | \
  sed -E 's/[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9:.Z-]*//g' | \
  sed -E 's/[0-9a-f]{8}-[0-9a-f-]{27,}/UUID/gi' | \
  sort | uniq -c | sort -rn | head -20
```

### Targeted Sampling

```bash
rg -C5 -m3 "PATTERN" "$LOG"     # 5 lines context, max 3 matches
rg -B10 "fatal|panic" "$LOG"    # 10 lines before fatal errors
```

### Request/Trace ID Following

```bash
rg "request_id.*error" "$LOG" | head -1
rg "REQUEST_ID_HERE" "$LOG"
```

### Diff Analysis (Two Files)

```bash
diff <(rg -o 'pattern' good.log | sort -u) \
     <(rg -o 'pattern' bad.log | sort -u)
```

## Token Efficiency Rules

1. **Run script first** - get structured overview before diving deeper
2. **Counts before content** - know frequency before reading examples
3. **Limit context** - use `-m` (max count) and `-C` (context lines)
4. **Deduplicate aggressively** - unique patterns with counts
5. **Never dump** - no `cat`, no unlimited `grep`; a raw log in the transcript defeats the point

## Output Format

After analysis, produce a summary for the user:

```markdown
## Log Analysis: [filename]

### Metadata
Lines: X | Size: Y | Time range: START to END

### Error Summary
| Type | Count |
|------|-------|

### Key Patterns
1. [Pattern + count]

### Hypotheses
1. [Likely root cause based on patterns]

### Suggested Investigation
- Compare [function/file] to [error pattern]
```

## Common Issue Patterns

```bash
rg -i "out.of.memory|oom|heap" "$LOG"           # OOM
rg -i "timeout|timed.out|deadline" "$LOG"       # Timeouts
rg -i "connection.refused|econnreset" "$LOG"    # Connection
rg -i "unauthorized|forbidden|401|403" "$LOG"   # Auth
```
