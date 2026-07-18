---
name: project_italics_tag_dropped_in_zh
description: validate_translation.py TAG MISMATCH warnings on zh-TW files are usually just dropped \i1\i0 italics, not shifted translations
metadata:
  type: project
---

The one-pace-translator agent frequently omits `{\i1}...{\i0}` italics/emphasis tags when producing zh-TW (Traditional Chinese) translations, since Chinese text doesn't use italics for emphasis the way English does. `validate_translation.py`'s tag check (extract_format_tags) flags this as "TAG MISMATCH ... possible shifted translation" per-line, but it does NOT fail the overall RESULT — it's informational only (no --fix exists for it).

**Why:** Confirmed on Whole Cake Island 01 (2026-07-18): two TAG MISMATCH lines (183, 320) were checked by comparing timings/context against the original — text and timing lined up correctly, the only difference was the missing italics markup around a single word/phrase. Not an actual shift.

**How to apply:** When TAG MISMATCH appears, spot-check by comparing the original line's plain text (stripping tags) against the translated line's text at the same line number/timing — if they correspond correctly, this is very likely just the translator dropping italics, not a real shift. Report it to the user as informational (per the "never modify dialogue text" rule, don't try to re-insert the tags yourself unless asked). Only escalate as an actual shift if the *content* also looks mismatched with surrounding lines (i.e. the translated text seems to belong to a different original line).
