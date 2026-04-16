#!/usr/bin/env bash
# Log analyzer - token-efficient summary for LLM debugging
# Usage: analyze.sh <logfile> [--errors-only] [--max-samples N] [--context N]

set -euo pipefail

# Defaults
MAX_SAMPLES=3
CONTEXT_LINES=5
ERRORS_ONLY=false

# Parse args
LOGFILE=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --errors-only) ERRORS_ONLY=true; shift ;;
        --max-samples) MAX_SAMPLES="$2"; shift 2 ;;
        --context) CONTEXT_LINES="$2"; shift 2 ;;
        -*) echo "Unknown option: $1" >&2; exit 1 ;;
        *) LOGFILE="$1"; shift ;;
    esac
done

if [[ -z "$LOGFILE" ]] || [[ ! -f "$LOGFILE" ]]; then
    echo "Usage: analyze.sh <logfile> [--errors-only] [--max-samples N] [--context N]" >&2
    exit 1
fi

# Normalize function: strip timestamps, UUIDs, hex strings, numbers for dedup
normalize() {
    sed -E \
        -e 's/[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2}:[0-9]{2}[.0-9]*[Z]?//g' \
        -e 's/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/UUID/gi' \
        -e 's/0x[0-9a-f]+/HEX/gi' \
        -e 's/[0-9]{10,}/BIGNUM/g' \
        -e 's/:[0-9]+/:N/g' \
        -e 's/\[[0-9]+\]/[N]/g'
}

# === METADATA ===
echo "=== LOG ANALYSIS: $(basename "$LOGFILE") ==="
echo ""
echo "METADATA"
LINES=$(wc -l < "$LOGFILE")
SIZE=$(ls -lh "$LOGFILE" | awk '{print $5}')
FIRST=$(head -1 "$LOGFILE" | cut -c1-80)
LAST=$(tail -1 "$LOGFILE" | cut -c1-80)
echo "Lines: $LINES | Size: $SIZE"
echo "First: $FIRST"
echo "Last:  $LAST"
echo ""

# === FORMAT DETECTION ===
SAMPLE=$(head -5 "$LOGFILE")
FORMAT="plain"
if echo "$SAMPLE" | head -1 | grep -qE '^\s*\{.*\}\s*$'; then
    FORMAT="json"
elif echo "$SAMPLE" | grep -qE '^[A-Z][a-z]{2} +[0-9]+ [0-9:]+'; then
    FORMAT="syslog"
fi
echo "FORMAT: $FORMAT"
echo ""

# === SEVERITY COUNTS ===
echo "SEVERITY"
ERR_COUNT=$(rg -c -i 'error|exception|fail|fatal|panic|crash' "$LOGFILE" 2>/dev/null || echo "0")
WARN_COUNT=$(rg -c -i 'warn' "$LOGFILE" 2>/dev/null || echo "0")
if [[ "$FORMAT" == "json" ]]; then
    # Try to extract level field for JSON
    rg -o '"level"\s*:\s*"[^"]+"' "$LOGFILE" 2>/dev/null | sort | uniq -c | sort -rn | head -5 || true
else
    echo "ERROR/FAIL/FATAL: $ERR_COUNT | WARN: $WARN_COUNT"
fi
echo ""

# === TOP ERROR PATTERNS ===
echo "TOP ERROR PATTERNS (count | normalized pattern)"
if [[ "$ERRORS_ONLY" == "true" ]]; then
    PATTERN='error|exception|fail|fatal|panic|crash'
else
    PATTERN='error|exception|fail|fatal|panic|crash|warn'
fi
rg -i "$PATTERN" "$LOGFILE" 2>/dev/null | normalize | sort | uniq -c | sort -rn | head -15 || echo "(none found)"
echo ""

# === TEMPORAL ANALYSIS ===
echo "TEMPORAL"
# Find line numbers of errors to detect bursts
ERROR_LINES=$(rg -n -i 'error|exception|fail|fatal' "$LOGFILE" 2>/dev/null | cut -d: -f1 | head -100)
if [[ -n "$ERROR_LINES" ]]; then
    FIRST_ERR=$(echo "$ERROR_LINES" | head -1)
    LAST_ERR=$(echo "$ERROR_LINES" | tail -1)
    ERR_SPAN=$((LAST_ERR - FIRST_ERR + 1))
    echo "First error: line $FIRST_ERR | Last error: line $LAST_ERR | Span: $ERR_SPAN lines"

    # Detect bursts (many errors in small line range)
    echo "$ERROR_LINES" | awk '
        NR==1 { prev=$1; start=$1; count=1; next }
        $1 - prev <= 10 { count++; prev=$1; next }
        count >= 5 { print "  Burst: lines " start "-" prev " (" count " errors)" }
        { start=$1; prev=$1; count=1 }
        END { if (count >= 5) print "  Burst: lines " start "-" prev " (" count " errors)" }
    '
else
    echo "(no errors found)"
fi
echo ""

# === UNIQUE STACK TRACES ===
echo "STACK TRACES (count | first line)"
rg -A1 'Traceback|Exception:|^\s+at .*\(.*:[0-9]+\)' "$LOGFILE" 2>/dev/null | \
    grep -v '^--$' | \
    normalize | \
    sort | uniq -c | sort -rn | head -10 || echo "(none found)"
echo ""

# === SAMPLE EXCERPTS ===
echo "SAMPLES (first $MAX_SAMPLES distinct errors with $CONTEXT_LINES lines context)"
echo ""

# Get line numbers of first few distinct error types
# Use awk to deduplicate by normalized form while preserving line numbers
SAMPLE_LINES=$(rg -n -i 'error|exception|fail|fatal|panic' "$LOGFILE" 2>/dev/null | \
    awk -F: '
    {
        line = $1
        msg = $0
        sub(/^[0-9]+:/, "", msg)
        # Normalize for dedup
        gsub(/[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2}:[0-9]{2}[.0-9]*[Z]?/, "", msg)
        gsub(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/, "UUID", msg)
        if (!seen[msg]++) print line
    }' | head -"$MAX_SAMPLES")

SAMPLE_NUM=0
for LINE_NUM in $SAMPLE_LINES; do
    SAMPLE_NUM=$((SAMPLE_NUM + 1))
    START=$((LINE_NUM - CONTEXT_LINES))
    [[ $START -lt 1 ]] && START=1
    END=$((LINE_NUM + CONTEXT_LINES))
    echo "--- Sample $SAMPLE_NUM (line $LINE_NUM) ---"
    sed -n "${START},${END}p" "$LOGFILE" 2>/dev/null
    echo ""
done

if [[ $SAMPLE_NUM -eq 0 ]]; then
    echo "(no error samples found)"
    echo ""
fi

# === COMMON ISSUE DETECTION ===
echo "COMMON ISSUES CHECK"
declare -A CHECKS=(
    ["OOM/Memory"]='out.of.memory|oom|heap|cannot allocate|memory'
    ["Timeout"]='timeout|timed.out|deadline|exceeded'
    ["Connection"]='connection.refused|econnreset|broken.pipe|econnaborted'
    ["Auth"]='unauthorized|forbidden|401|403|auth.*fail|permission.denied'
    ["Disk"]='no.space|disk.full|enospc|readonly.file'
    ["DNS"]='could.not.resolve|dns|nxdomain|getaddrinfo'
)

for name in "${!CHECKS[@]}"; do
    COUNT=$(rg -c -i "${CHECKS[$name]}" "$LOGFILE" 2>/dev/null || echo "0")
    if [[ "$COUNT" -gt 0 ]]; then
        echo "  $name: $COUNT occurrences"
    fi
done
echo ""

echo "=== END ANALYSIS ==="
