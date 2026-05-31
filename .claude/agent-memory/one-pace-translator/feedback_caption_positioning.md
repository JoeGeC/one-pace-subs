---
name: Top-positioned subtitle repositioning
description: All top-aligned styles (Title, Captions, Narrator, Note) must be pushed down via MarginV to clear hardcoded Japanese text — handled by merge_translation.py
type: feedback
---

All top-positioned subtitle styles must be pushed down to clear hardcoded Japanese text at the top of the screen. The `merge_translation.py` script handles this automatically — but ONLY if you use the pipeline (extract → translate TSV → merge).

**Affected styles:** Title, Captions, Narrator, Note (and their variants like Note-207-, Notes-207-, Note-207+, Narrator-207-, etc.)

**Why:** The video has burned-in Japanese text at the top that would overlap with default top-positioned subtitles. The merge script sets MarginV=100 for single-line and MarginV=200 for multi-line (containing \N) text. It also modifies Note/Narrator style definitions to have MarginV=100.

**How to apply:**
- ALWAYS use the extract/merge pipeline. NEVER write ASS files directly.
- The merge script automatically:
  - Adds `\an8` to Title/Captions lines and sets MarginV=100/200
  - Sets MarginV=100/200 on Narrator/Note dialogue lines
  - Changes Note/Narrator style definitions to MarginV=100
- If you bypass the merge script, none of this repositioning happens and subtitles appear in wrong positions on screen.

**What went wrong before:** Translation agents wrote ASS files directly instead of using the pipeline, resulting in Narrator/Note/Caption lines appearing at the top of screen overlapping burned-in Japanese text.
