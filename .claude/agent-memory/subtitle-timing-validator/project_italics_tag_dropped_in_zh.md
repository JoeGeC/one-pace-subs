---
name: project_italics_tag_dropped_in_zh
description: validate_translation.py TAG MISMATCH warnings on zh-TW files have two distinct causes — dropped \i1\i0 italics (informational, leave alone) vs dropped \t() effect transforms (real bug, fix it)
metadata:
  type: project
---

`validate_translation.py`'s tag check (extract_format_tags) flags "TAG MISMATCH ... possible shifted translation" per-line whenever the tag set differs between orig/translated. Two distinct root causes have been observed — diagnose which one before deciding whether to fix:

**Cause 1 — dropped `{\i1}...{\i0}` italics (informational only, do not fix).** The one-pace-translator agent frequently omits italics/emphasis tags since Chinese text doesn't use italics for emphasis the way English does. Confirmed on Whole Cake Island 01 (2026-07-18): lines 183, 320 — text/timing lined up correctly, only the italics markup around a word/phrase was missing. Per "never modify dialogue text," report this to the user as informational; don't re-insert.

**Cause 2 — dropped `\t(...)` alpha/effect transform tag on a Title/Captions line (real bug, DO fix).** Confirmed on Whole Cake Island 07 (2026-07-18) line 437: original had two transforms, a fade-in `\t(380,425,\1a&H00&)` AND a fade-out `\t(3645,3690,\1a&HFF&)`; translated line was missing the second one entirely, meaning the caption would stay opaque instead of fading out. This is a positioning/effects tag, not dialogue text, so it's safe and correct to restore with Edit — copy the missing `\t()` clause back in, preserving any `\an8`/`\pos()` repositioning that was already correctly applied to the line.

**How to apply:** When TAG MISMATCH appears, look at *which* tags differ:
- If the diff is just `\i1`/`\i0` around text → Cause 1, informational, leave it, report to user.
- If the diff includes a missing/extra `\t(...)` transform clause (typically on Title/Captions lines with fade in/out effects) → Cause 2, this is a genuine dropped effect and should be fixed by restoring the missing tag exactly as in the original (adjusting only `\pos`/`\an` if repositioning applies).
- Only escalate as an actual *shifted line* (different issue) if the plain text content also looks mismatched with surrounding lines.
