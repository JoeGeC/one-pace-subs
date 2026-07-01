---
name: Top-positioned subtitle repositioning
description: Top-aligned styles (Title/Captions) and \an8 dialogue are moved to the top and STACKED to clear hardcoded English subs — handled by merge_translation.py
type: feedback
---

The episodes are watched with the release's **hardcoded English subtitles burned into the video**. Normal bottom dialogue is fine (the player renders the translated line above the English burn-in), but anything at the top or with a custom `\pos` would land on top of the burned-in English, so those lines are relocated. `merge_translation.py` handles this automatically — but ONLY if you use the pipeline (extract → translate TSV → merge). NEVER write ASS files directly.

**Affected:** Title, Captions (and lowercase variants), and any `\an8` dialogue line. Narrator/Note styles get MarginV=100 via their style definition.

**How merge repositions (as of the stacking fix):**
- Every top line is pinned to the top with `\an8\pos(x, y)`. x is the caption's original x if it had one, else screen-centre (PlayResX/2).
- Lines that are **on screen at the same time are STACKED into rows** (topmost at y=100, each row STACK_LINE_H·maxlines below) via interval-graph row colouring — rows are reused as lines end, and crossfades shorter than OVERLAP_EPS don't count. This prevents coincident captions/labels/shouts from overlapping each other (the old code forced them all to the same y).
- Tunables live at the top of merge_translation.py: STACK_TOP, STACK_LINE_H, OVERLAP_EPS.

**Validator:** `validate_translation.py --fix` accepts `\an8` with OR without `\pos` as correctly repositioned. Do NOT revert it to the old "must not have \pos" rule — that strips the stacking. Its `detect_overlaps` warnings are position-unaware (time-only) and informational; they do not fail validation. See [[reference-fandom-name-verification]].

**Re-applying to already-translated files:** use `remerge_from_zhtw.py original.ass zhtw.ass` — it rebuilds the translation dict from the zh-TW text (translated words preserved) and re-runs merge so positioning is recomputed. Done for Dressrosa 01-05; **Punk Hazard and earlier arcs still have the old pile-at-one-position bug** and need the same re-merge when you're ready.

**What went wrong before:** merge forced every top line to the same y (Captions to `\pos(x,100)`, \an8 dialogue to MarginV=100), so a location card + its label, or a news caption + a shouted "King!", rendered on top of each other.
