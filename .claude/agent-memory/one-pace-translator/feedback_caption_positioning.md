---
name: Top-positioned subtitle repositioning
description: All top-aligned styles (Title, Captions, Narrator, Note) must be pushed down to clear hardcoded Japanese text — MarginV=100 for single-line, 200 for multi-line
type: feedback
---

All top-positioned subtitle styles must be pushed down to clear hardcoded Japanese text at the top of the screen. For two-line subtitles (containing \N), MarginV should be 200 to push them down double the amount.

**Affected styles:** Title, Captions, Narrator, Note (and their variants like Note-207-, Notes-207-, Note-207+, Narrator-207-, etc.)

**Why:** The video has burned-in Japanese text at the top that would overlap with default top-positioned subtitles. Two-line text is taller, so it needs double the margin to clear the burned-in text.

**How to apply:**
- Caption-style lines that use \pos(): set the y coordinate to 100
- Narrator and Note style dialogue lines: MarginV=100 for single-line, MarginV=200 for two-line (containing \N)
- Title/Captions lines get \an8 added and MarginV=100/200 (handled by merge script)
- The merge script handles this automatically via the `TOP_POSITION_PREFIXES` and the MarginV logic for Narrator/Note styles
