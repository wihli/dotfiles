---
name: logalyzer
description: |
  Token-efficient analysis of large log files. Produces structured summaries for debugging.
  Use when: analyzing logs, debugging from logs, investigating errors/failures/performance issues,
  understanding what happened in a system, or when user provides log files to examine.
  Triggers: "analyze these logs", "what went wrong", "debug this", "look at the logs",
  file types: .log, server logs, application output, stderr captures.
---

# Logalyzer

Analyze large logs without exhausting context. Extract signal, summarize findings, enable next-step debugging.

## Quick Start

Run the analyzer script for a complete summary:

```bash
${CLAUDE_SKILL_DIR}/scripts/analyze.sh /path/to/logfile.log
```

Options:
- `--errors-only` - skip warnings, focus on errors
- `--max-samples N` - number of sample excerpts (default: 3)
- `--context N` - lines of context around samples (default: 5)

The script outputs: metadata, severity counts, normalized error patterns, temporal analysis, stack traces, samples, and common issue detection.

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
