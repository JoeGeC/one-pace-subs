---
name: Glossary storage preference
description: Glossary lives in agent-memory directory as glossary.md, not in a separate prompt file
type: feedback
---

The translation glossary is stored at `.claude/agent-memory/one-pace-translator/glossary.md`.

**Why:** Keeps glossary within the agent memory system so it persists across conversations and is version-controlled with the project.

**How to apply:** Always read glossary from agent-memory at session start; update it there after each translation file.
