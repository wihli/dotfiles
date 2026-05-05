---
name: sheets
description: Legacy Google Sheets compatibility skill. Use only when the user explicitly asks for the old `gsheet` CLI. For normal Google Sheets, Google Docs, docs.google.com URLs, spreadsheet updates, formatting, or recurring Workspace workflows, prefer the private `google-workspace-workflows` skill and the `gws` CLI instead.
---

# Sheets

This legacy skill used to route spreadsheet work to the bespoke `gsheet` CLI. Prefer `gws` through the `google-workspace-workflows` skill for new work.

If the user explicitly asks for `gsheet`, use it carefully:

1. Read the sheet structure before writing.
2. Target cells by headers and stable row keys.
3. Avoid broad writes, clears, whole-tab rewrites, and formatting changes without an explicit preview.
4. Re-read the edited range after writing.

For all other spreadsheet work, load `google-workspace-workflows` and follow its safety rules.
