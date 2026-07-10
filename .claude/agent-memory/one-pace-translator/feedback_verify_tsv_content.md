---
name: verify-tsv-content-before-translating
description: Always confirm the extracted TSV content matches the episode being translated; a stale /tmp read once caused a full mistranslation
metadata:
  type: feedback
---

Before translating, confirm the TSV you read actually belongs to the episode named in the task — check that the first/last LINE_NUM range and the dialogue content match the file just extracted.

**Why:** During Zou 08 [816-817], an early Read of `/tmp/dialogue.tsv` returned content from a *different* episode (lines 841–1395, Zunesha/banquet scenes belonging to Zou 09). The real Zou 08 content was lines 837–1192 (Raizo reveal / Kozuki crest). I translated ~356 lines of the wrong episode, and merge_translation.py failed with "line numbers not in source" — that error is the tell-tale symptom. `/tmp` files also get clobbered/reset between runs and even mid-session in the scratchpad, so a stale read is a real hazard.

**How to apply:** (1) Immediately after running extract_dialogue.py, note the reported line count and the source file's LINE_NUM range. (2) When you Read the TSV, sanity-check that its LINE_NUM range and topic match. (3) If merge errors with "references line numbers not in the source" for a large contiguous block, STOP — you almost certainly translated stale/wrong content; re-extract fresh and re-read before redoing. (4) Prefer a unique scratchpad filename per episode (e.g. `zou08_translated.tsv`) over a generic `translated.tsv`, since the generic path gets overwritten and then Write refuses with "File has not been read yet."
