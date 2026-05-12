---
name: prompt-search
description: |
  Search prior prompts and sessions across BOTH Claude Code and Codex CLI history.
  Use when looking for an old conversation, resuming prior work, or finding where
  a term/topic was discussed before. Results are unified and tagged [claude]/[codex].
---

# Prompt Search Skill

Search across Claude Code + Codex CLI conversation history: $ARGUMENTS

Results are merged chronologically and tagged with their source tool.

## Storage layouts (reference)

**Claude** (`~/.claude/`):
- `history.jsonl` — flat user-prompt log: `{timestamp(ms), project, sessionId, display}` per line
- `projects/<slug>/<session-uuid>.jsonl` — full per-session transcripts. Each line is one event with `type` (`user`/`assistant`/...); user/assistant events carry `{sessionId, timestamp(ISO), cwd, message:{role,content}}`. The top-level `__store.db` / `store.db` files are empty stubs — ignore them.

**Codex** (`~/.codex/`):
- `history.jsonl` — flat user-prompt log: `{session_id, ts(sec), text}` per line
- `state_5.sqlite` — `threads(id, created_at, updated_at, cwd, title, first_user_message, rollout_path, ...)`
- `sessions/YYYY/MM/DD/rollout-*.jsonl` — full session transcripts

## Quick Search: User Prompts (both history files)

```bash
python3 -c "
import json, os
from datetime import datetime
term = '$ARGUMENTS'.lower()
rows = []
# Claude — ts in ms
p = os.path.expanduser('~/.claude/history.jsonl')
if os.path.exists(p):
    with open(p) as f:
        for l in f:
            if term in l.lower():
                d = json.loads(l)
                rows.append((
                    d.get('timestamp', 0) / 1000,
                    'claude',
                    d.get('sessionId', '')[:8],
                    d.get('project', '').split('/')[-1],
                    d.get('display', '')[:100].replace('\n', ' '),
                ))
# Codex — ts in sec
p = os.path.expanduser('~/.codex/history.jsonl')
if os.path.exists(p):
    with open(p) as f:
        for l in f:
            if term in l.lower():
                d = json.loads(l)
                rows.append((
                    d.get('ts', 0),
                    'codex',
                    d.get('session_id', '')[:8],
                    '',  # cwd not in codex history.jsonl; resolve via state_5.sqlite if needed
                    d.get('text', '')[:100].replace('\n', ' '),
                ))
rows.sort()
for ts, tool, sid, proj, disp in rows[-25:]:
    when = datetime.fromtimestamp(ts)
    print(f'{when:%Y-%m-%d %H:%M} | [{tool:6}] | {sid} | {proj:20} | {disp}')
"
```

## Recent Sessions (unified)

```bash
python3 -c "
import json, os, glob, sqlite3
from datetime import datetime
rows = []
# Claude — one JSONL per session under projects/<slug>/<uuid>.jsonl
for f in glob.glob(os.path.expanduser('~/.claude/projects/*/*.jsonl')):
    sid = os.path.splitext(os.path.basename(f))[0]
    cwd, first_user, msg_count, last_ts = '', '', 0, None
    try:
        with open(f) as fh:
            for line in fh:
                try: d = json.loads(line)
                except: continue
                if d.get('type') not in ('user','assistant'): continue
                msg_count += 1
                ts = d.get('timestamp')
                if ts: last_ts = ts
                if not cwd: cwd = d.get('cwd','')
                if not first_user and d.get('type') == 'user':
                    m = d.get('message',{}).get('content','')
                    if isinstance(m, list):
                        m = next((p.get('text','') for p in m if p.get('type')=='text'), '')
                    first_user = str(m)[:80].replace('\n',' ')
    except: continue
    if last_ts:
        # parse ISO → epoch for unified sort
        try: epoch = datetime.fromisoformat(last_ts.replace('Z','+00:00')).timestamp()
        except: epoch = 0
        rows.append((epoch, 'claude', sid[:8], msg_count, cwd or '', first_user))
# Codex — threads table
db = os.path.expanduser('~/.codex/state_5.sqlite')
if os.path.exists(db):
    c = sqlite3.connect(db).cursor()
    for tid, updated, cwd, first in c.execute('''
        SELECT id, updated_at, cwd, substr(first_user_message,1,80)
        FROM threads ORDER BY updated_at DESC LIMIT 30
    '''):
        rows.append((updated, 'codex', tid[:8], 0, cwd or '', (first or '').replace('\n',' ')))
rows.sort(reverse=True)
for ts, tool, sid, msgs, cwd, extra in rows[:20]:
    when = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M') if ts else '----------- ----'
    proj = cwd.split('/')[-1] if cwd else ''
    msg_col = f'{msgs:4} msgs' if msgs else '  n/a    '
    print(f'{when} | [{tool:6}] | {sid} | {msg_col} | {proj:20} | {extra[:60]}')
"
```

## Deep Search: full transcripts (assistant replies + tool output)

`history.jsonl` only contains user prompts. To search assistant text, code, errors, etc., grep the transcript JSONLs from both tools:

```bash
# Claude transcripts
echo "--- [claude] ---"
rg -l --no-messages -F "$ARGUMENTS" ~/.claude/projects/ 2>/dev/null | head -10 | while read f; do
    sid=$(basename "$f" .jsonl | cut -c1-8)
    proj=$(basename "$(dirname "$f")" | sed 's/^-//; s/-/\//g')
    when=$(date -r "$f" '+%Y-%m-%d %H:%M' 2>/dev/null)
    echo "$when | [claude] | $sid | $proj"
done

# Codex transcripts
echo "--- [codex] ---"
rg -l --no-messages -F "$ARGUMENTS" ~/.codex/sessions/ 2>/dev/null | head -10 | while read f; do
    sid=$(basename "$f" | sed 's/rollout-[0-9T-]*-//; s/\.jsonl$//' | cut -c1-8)
    when=$(basename "$f" | sed -nE 's/^rollout-([0-9-]+)T([0-9]{2})-([0-9]{2})-([0-9]{2}).*/\1 \2:\3/p')
    echo "$when | [codex ] | $sid | $f"
done
```

## Resume a Session

```bash
# Claude
claude --resume                       # interactive picker
claude --resume SESSION_ID            # specific
claude --resume SESSION_ID --fork-session

# Codex
codex resume                          # interactive picker
codex resume THREAD_ID                # specific
# Open Codex rollout file directly:
#   sqlite3 ~/.codex/state_5.sqlite "SELECT rollout_path FROM threads WHERE id LIKE 'PREFIX%';"
```
