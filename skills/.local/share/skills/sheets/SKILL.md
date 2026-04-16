---
name: sheets
description: |
  Work with Google Sheets via the `gsheet` CLI: inspect tabs, read ranges, write cells,
  append rows, and format cells. Use when the user mentions spreadsheets, sheet URLs,
  gsheet, updating a sheet, formatting rows/cells, or highlighting cells.
---

# Skill: Google Sheets via `gsheet` CLI

## CRITICAL: Variable Scoping with Pipes

**When piping data to `gsheet write`/`gsheet append`, pass the spreadsheet ID as a literal value, NOT a shell variable.**

In zsh (the default shell in this environment), non-exported variables can silently expand to empty strings in pipeline contexts. gsheet will catch this and show a helpful error, but avoid it entirely:

```bash
# CORRECT — inline the ID directly
printf 'data' | gsheet write 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms 'Sheet Name!A1:C1'

# CORRECT — use a heredoc (avoids pipe entirely)
gsheet write 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms 'Sheet Name!A1:C1' <<< 'data'

# RISKY — $ID may silently be empty in zsh pipe context
ID="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms"
printf 'data' | gsheet write "$ID" 'Sheet Name!A1:C1'
```

Commands without pipes (`gsheet read`, `gsheet info`, `gsheet clear`, `gsheet format`) work fine with variables.

---

## 1. gsheet CLI Reference

`gsheet` is a bash/curl/jq wrapper around Google Sheets API v4 with OAuth PKCE auth. It lives on `$PATH`.

### Commands

| Command | Usage | Description |
|---------|-------|-------------|
| `auth` | `gsheet auth` | OAuth browser flow, stores tokens |
| `info` | `gsheet info <ID>` | List sheet names, indices, grid sizes |
| `read` | `gsheet read <ID> <range>` | Output cell data as TSV |
| `write` | `gsheet write <ID> <range>` | Read TSV from stdin, PUT values |
| `append` | `gsheet append <ID> <range>` | Read TSV from stdin, append rows after data |
| `clear` | `gsheet clear <ID> <range>` | Clear a range |
| `format` | `gsheet format <ID> <range> --bg <hex>` | Set background color of cells |

### Examples

```bash
# Get spreadsheet structure
gsheet info 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms

# Read data from a sheet tab (spaces in name are fine, no extra quoting needed)
gsheet read 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms 'My Sheet!A1:Z'

# Write a single cell
printf 'done' | gsheet write 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms 'Sheet1!B3'

# Write a row (TSV)
printf 'alice\t42\tactive' | gsheet write 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms 'Sheet1!A5:C5'

# Write multiple rows from stdin
printf 'row1a\trow1b\nrow2a\trow2b' | gsheet write 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms 'Sheet1!A1:B2'

# Append rows
printf 'new\trow' | gsheet append 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms 'Sheet1!A:B'

# Format: set background color
gsheet format 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms 'My Sheet!A2:D2' --bg '#fffde7'
```

---

## 2. URL → Spreadsheet ID

Google Sheets URLs contain the spreadsheet ID between `/d/` and the next `/`:

```
https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms/edit#gid=0
                                       ^--- spreadsheet_id ---^
```

Extract with:
```bash
url="https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms/edit#gid=0"
id=$(echo "$url" | sed 's|.*/d/\([^/]*\).*|\1|')
```

Always extract the ID from URLs before passing to `gsheet` commands.

---

## 3. Reading Structure — Always Read First

**Before writing or formatting, understand the sheet's structure.**

### Step 1: Get sheet tabs

```bash
gsheet info "$ID"
# Output:
# Spreadsheet: My Tracker
#
# Index  Sheet                          Size
# 0      Dashboard                      100x10
# 1      Repos                   50x8
```

This tells you the tab names and grid dimensions.

### Step 2: Read headers + data

```bash
# Read first few rows to understand column layout
gsheet read "$ID" 'Repos!A1:Z5'
# Output (TSV):
# Repo	Status	Last Deploy	Owner	Notes
# my-api	active	2025-01-15	eric	main service
# my-web	active	2025-01-14	eric	frontend
```

Now you know column A = Repo, column B = Status, etc.

### Step 3: Read all data when you need row numbers

```bash
# Pipe through cat -n or nl to get line numbers for targeting specific rows
gsheet read "$ID" 'Repos!A:A' | cat -n
#      1  Repo
#      2  my-api
#      3  my-web
#      4  my-infra
```

Row 1 in output = row 1 in the sheet (A1). Use this to find the right row for writes/formats.

---

## 4. Writing Patterns

### Single cell
```bash
printf 'value' | gsheet write "$ID" 'Sheet1!B3'
```

### Single row
```bash
printf 'col1\tcol2\tcol3' | gsheet write "$ID" 'Sheet1!A5:C5'
```

### Multiple rows
```bash
printf 'a1\tb1\na2\tb2\na3\tb3' | gsheet write "$ID" 'Sheet1!A1:B3'
```

### From a pipeline (dynamic TSV)
```bash
# Write output of another command
some_command | gsheet write "$ID" 'Sheet1!A2:C100'
```

### Append (auto-detect next empty row)
```bash
printf 'new\tdata\there' | gsheet append "$ID" 'Sheet1!A:C'
```

**Key:** `write` overwrites the target range. `append` finds the last row with data and adds below it.

---

## 5. Formatting

### Background color

```bash
gsheet format "$ID" 'Sheet Name!A2:D2' --bg '#rrggbb'
```

The `--bg` flag accepts a 6-digit hex color (with or without `#` prefix).

### Semantic color palette

Use these colors for consistent meaning:

| Purpose | Hex | Description |
|---------|-----|-------------|
| Success / green | `#c8e6c9` | Light green — done, passing, deployed |
| Warning / yellow | `#fffde7` | Light yellow — needs attention, in progress |
| Error / red | `#ffcdd2` | Light red — failing, blocked, critical |
| Info / blue | `#bbdefb` | Light blue — informational, neutral highlight |
| Neutral / gray | `#f5f5f5` | Light gray — disabled, archived, inactive |
| Header | `#e8eaf6` | Light indigo — column/row headers |

### Be precise with ranges

Format only the specific column/cells needed — not entire rows. If the user says "color the repo name red", format column A only, not A:E.

```bash
# Highlight just column A for row 5
gsheet format "$ID" 'Sheet1!A5' --bg '#ffcdd2'

# Highlight a full row only if explicitly asked
gsheet format "$ID" 'Sheet1!A5:F5' --bg '#c8e6c9'
```

### Resetting formatting

There is no "undo". To reset, apply white:

```bash
gsheet format "$ID" 'Sheet1!A5' --bg '#ffffff'
```

---

## 6. Workflow Guidance

### Standard workflow for sheet tasks

1. **Extract ID** from URL
2. **`gsheet info`** — learn tab names and sizes
3. **`gsheet read`** — understand column layout and current data
4. **Find target rows** — read column A (or key column) with line numbers
5. **Write/format** — target specific cells/ranges

### Dynamic row finding

Don't hardcode row numbers. Find them:

```bash
# Find which row contains "my-api" in column A
gsheet read "$ID" 'My Sheet!A:A' | grep -n 'my-api'
# 3:my-api  →  row 3 in the sheet
```

### Batch operations

For multiple writes, pipe TSV. For multiple formats on different ranges, run sequential `gsheet format` commands.

### Error handling

- **API error (403)**: Token expired or no access. Run `gsheet auth`.
- **API error (404)**: Wrong spreadsheet ID or sheet name. Check with `gsheet info`.
- **"spreadsheet_id is empty"**: Variable wasn't expanded. Use inline ID (see CRITICAL section).
- **"Sheet 'X' not found"**: Check exact name with `gsheet info`. Names are case-sensitive.

---

## 7. Quoting Rules

### Sheet names with spaces

Use single quotes around the entire range argument. **No inner quoting needed** — gsheet handles URL encoding internally:

```bash
# Correct — single quotes, sheet name with spaces works directly
gsheet read "$ID" 'Repos!A1:Z'
gsheet format "$ID" 'Repos!A2:D2' --bg '#c8e6c9'

# Also correct — double quotes work too (but beware of ! in zsh)
gsheet read "$ID" "Sheet1!A1:Z"

# Wrong — do NOT add inner single quotes around the sheet name
gsheet read "$ID" "'Repos'!A1:Z"  # will fail with "Unable to parse range"
```

### The `!` character

gsheet sanitizes `\!` → `!` internally, so ranges work even if the calling shell escapes `!`. No special handling needed by the caller.

### Simple sheet names (no spaces)

```bash
gsheet read "$ID" 'Sheet1!A1:Z'
```

---

## 8. Tips

- **TSV is the interchange format.** `gsheet read` outputs TSV, `gsheet write` reads TSV. Pipe between them or with `cut`, `awk`, `paste`.
- **Ranges are inclusive.** `A1:C3` includes all cells in that rectangle.
- **Open-ended ranges** like `A:A` or `A1:Z` read entire columns/rows up to data extent.
- **`USER_ENTERED` input.** Values written are parsed like manual entry — formulas (`=SUM(A:A)`), dates, numbers all work.
- **One format option at a time.** Currently `--bg` is the only format flag. Multiple format changes need multiple calls.
- **Inline IDs for writes.** When piping data, always inline the spreadsheet ID to avoid zsh variable scoping issues.
