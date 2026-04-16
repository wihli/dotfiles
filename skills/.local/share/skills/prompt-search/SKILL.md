---
name: prompt-search
description: |
  Search Claude conversation history and local Claude session storage for prior prompts,
  sessions, and message snippets. Use when looking for an old conversation, resuming prior
  work, or finding where a term/topic was discussed before.
---

# Prompt Search Skill

Search across Claude Code conversation history: $ARGUMENTS

## Schema (DO NOT guess columns — use only these)

```
base_messages(uuid PK, parent_uuid, session_id, timestamp, message_type, cwd, user_type, version, isSidechain, original_cwd)
user_messages(uuid PK/FK→base_messages, message, tool_use_result, timestamp, is_at_mention_read, is_meta)
assistant_messages(uuid PK/FK→base_messages, cost_usd, duration_ms, message, is_api_error_message, timestamp, model)
conversation_summaries(leaf_uuid PK/FK→base_messages, summary, updated_at)
```

NOTE: `conversation_summaries` has NO `session_id`. Join via `base_messages`.

## Quick Search: User Prompts (history.jsonl)

```bash
python3 -c "
import json
from datetime import datetime
term = '$ARGUMENTS'.lower()
with open('$HOME/.claude/history.jsonl') as f:
    matches = [json.loads(l) for l in f if term in l.lower()]
for d in matches[-20:]:
    ts = datetime.fromtimestamp(d.get('timestamp', 0) / 1000)
    proj = d.get('project', '').split('/')[-1]
    sid = d.get('sessionId', '')[:8]
    disp = d.get('display', '')[:100].replace('\n', ' ')
    print(f'{ts:%Y-%m-%d %H:%M} | {sid} | {proj:20} | {disp}')
"
```

## Database Search: Messages

```bash
sqlite3 ~/.claude/__store.db "
SELECT
    b.session_id,
    datetime(b.timestamp, 'unixepoch', 'localtime') as date,
    b.cwd,
    CASE
        WHEN json_valid(u.message) AND json_type(json_extract(u.message, '\$.content')) = 'text'
        THEN substr(json_extract(u.message, '\$.content'), 1, 100)
        ELSE '[complex message]'
    END as preview
FROM user_messages u
JOIN base_messages b ON u.uuid = b.uuid
WHERE u.message LIKE '%$ARGUMENTS%'
  AND u.tool_use_result IS NULL
ORDER BY b.timestamp DESC
LIMIT 15;
"
```

## Recent Sessions

```bash
sqlite3 ~/.claude/__store.db "
SELECT
    b.session_id,
    datetime(MIN(b.timestamp), 'unixepoch', 'localtime') as started,
    datetime(MAX(b.timestamp), 'unixepoch', 'localtime') as ended,
    COUNT(*) as msgs,
    b.cwd
FROM base_messages b
GROUP BY b.session_id
ORDER BY MAX(b.timestamp) DESC
LIMIT 10;
"
```

## Resume a Session

```bash
claude --resume            # interactive search
claude --resume SESSION_ID # specific session
claude --resume SESSION_ID --fork-session  # fork instead of continue
```
