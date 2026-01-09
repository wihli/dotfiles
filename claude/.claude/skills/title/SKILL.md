---
name: title
description: |
  Set terminal/Zellij pane title to 2-word summary of current conversation.
  Triggers: "/title", "update title", "set title"
---

# Title

Set terminal title via escape sequence.

## Process

1. Reflect on conversation: What's the main topic or current task?
2. Generate exactly 2 words (Title Case) summarizing it
3. Run: `zellij action rename-tab "Two Words"`

## Examples

- Debugging auth flow → "Auth Debugging"
- Setting up CI pipeline → "CI Setup"
- Refactoring database queries → "Query Refactor"
- General chat, no clear focus → "Claude Chat"
