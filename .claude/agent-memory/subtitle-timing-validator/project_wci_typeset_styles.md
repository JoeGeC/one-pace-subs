---
name: project_wci_typeset_styles
description: Whole Cake Island arc adds new translatable typeset styles (Musical, Munch Chomp, Dried Up, Special-Captions) not seen in earlier arcs
metadata:
  type: project
---

Whole Cake Island (this arc, "30 Whole Cake Island") introduces four new style
names that carry heavy \pos/\t/\fad override blocks and must be translated
(they're already listed in `extract_dialogue.py` TRANSLATABLE_PREFIXES):

- `Musical` — Big Mom Pirates / homies song lines (WCI 01+)
- `Munch Chomp` — Luffy eating typeset (WCI 01)
- `Dried Up` — Luffy's weakened mumbling typeset (WCI 02)
- `Special-Captions` — location cards not named `Captions` (WCI 05)

`validate_translation.py`'s tag check (`extract_format_tags`) already covers
these styles since they match TRANSLATABLE_PREFIXES. It normalizes out
\pos/\move/\an/legacy-\a/karaoke tags before comparing, so a clean "0
MISMATCHED" tag-check result on these styles is real confirmation that the
heavy \t/\fad/\c override blocks survived the merge intact — no need to
manually diff the override blocks by hand.

Files remerged 2026-07-18 to recover previously-missed lines in these four
styles: WCI 01 (823-824), 02 (825-826), 03 (827-828), 05 (831-832). All
passed validation (line counts, metadata, tags, repositioning all OK).

**How to apply:** When validating future WCI episodes (04, 06+), expect these
same four style names and don't be surprised they're translatable — they
aren't in the "standard" style set (Main/Secondary/Title/Captions/etc.) seen
in other arcs.
