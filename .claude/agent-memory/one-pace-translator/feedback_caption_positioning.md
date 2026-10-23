---
name: Top-positioned subtitle repositioning
description: Top-aligned styles (Title/Captions) and \an8 dialogue are moved to the top and STACKED to clear hardcoded English subs — handled by merge_translation.py
type: feedback
---

The episodes are watched with the release's **hardcoded English subtitles burned into the video**. Normal bottom dialogue is fine (the player renders the translated line above the English burn-in), but anything at the top or with a custom `\pos` would land on top of the burned-in English, so those lines are relocated. `merge_translation.py` handles this automatically — but ONLY if you use the pipeline (extract → translate TSV → merge). NEVER write ASS files directly.

**Affected:** Title, Captions (and lowercase variants), and any `\an8` dialogue line. Narrator/Note styles get MarginV=100 via their style definition.

**How merge repositions (as of 2026-10-23):**
- Every top line is pinned with `\an8\pos(x, y)`; x is the caption's original x if it had one, else screen-centre.
- y = first free vertical gap from STACK_TOP (100) down, sized to the line's REAL height (line count × font size × scale × POS_LINE_SPACING — the old fixed 55px rows were 720p-calibrated and overlapped at 1080p). It must clear the burned-in English of every line on screen at the time — including the line's OWN English (a two-line `\an8` English line at 1080p runs to y≈216, so pinning at 100 sat on it: Reverie 01 "pirate scum") — and any Chinese already placed.
- Animated captions (one line per frame) are chained into runs and get one y for the whole run; if no single y fits the run, frames are placed individually. Blocks that fit no gap take the least-overlapping spot.
- Montage = more than MAX_PINNED_CLUSTER captions at distinct positions on screen AT ONCE (only those captions keep their \pos). The old rule counted a time-chained cluster, so two name cards + three back-to-back `\an8` lines (Reverie 01 Ivankov/Dragon) were wrongly left unpinned on top of the English.
- `\clip`/`\iclip` move with the text (`_shift_clip`) — wipe/gradient captions are drawn as many 2px clipped strips (Wano 61 "Bariete"), which vanished when only `\pos` moved.
- Narrator/Note go through the same planner (their old flat MarginV=100×Chinese lines ignored the English narration's height — Reverie 03 "The World Government is a truly massive organization.").
- Montage placement key falls back to the `\move` start point, then the text — `\move`-animated map labels (Reverie 03 23:20 East/North/South/West Blue) otherwise all looked like one caption and got stacked down the centre.
- **Drawings are blanked**: `\p1` shape lines in translatable styles (map outlines, colour boxes behind signs) are already burned into the video under the English; redrawing them hid that English. merge keeps the line + tags (validator pairs lines 1:1) but drops the drawing commands. Removed 22k visible drawings across Reverie/Wano on 2026-10-23.
- Tunables at the top of merge_translation.py: STACK_TOP, POS_LINE_SPACING, POS_GAP, OVERLAP_EPS, FRAME_EPS.

**\pos-pinned dialogue (Main/Secondary/Thoughts/Flashbacks/Narrator/Note):** a source line with its own `\pos` (e.g. Reverie 01 "Think about it, Sanji!" at `\pos(392,1053)`) bypasses the player's lift and lands ON the burned-in English. `_plan_pos_offsets` in merge moves it just above the English block (offset = English line count × font size × POS_LINE_SPACING + POS_GAP), or just below if above would leave the frame; it keeps the source MarginV. Art-directed typeset (`\fn`, drawings, `\clip`, `\org`/`\fr`, `\t`, `\move`, `{=` motion tracking) is left in place. Applied to Reverie + Wano on 2026-10-23 by patching only the planned lines' position tags in place (a full re-merge would churn ~1300 unrelated lines from older merge versions). Collisions measured across Reverie+Wano: 2184 → 881 lines, the rest being in-place typeset (sound-effect fonts, motion-tracked frames) left deliberately, tall vertical location cards with no free gap, and crowd lines.

**Validator:** `validate_translation.py --fix` accepts `\an8` with OR without `\pos` as correctly repositioned. Do NOT revert it to the old "must not have \pos" rule — that strips the stacking. Its `detect_overlaps` warnings are position-unaware (time-only) and informational; they do not fail validation. See [[reference-fandom-name-verification]].

**Re-applying to already-translated files:** use `remerge_from_zhtw.py original.ass zhtw.ass` — it rebuilds the translation dict from the zh-TW text (translated words preserved) and re-runs merge so positioning is recomputed. Done for Dressrosa 01-05; **Punk Hazard and earlier arcs still have the old pile-at-one-position bug** and need the same re-merge when you're ready. Dressrosa through Zou/WCI were merged under the pre-2026-10-23 planner and may have the same top-overlap issues Reverie/Wano had. `build_translations` only feeds lines whose zh text differs from the source (as merge/validator do).

**What went wrong before:** merge forced every top line to the same y (Captions to `\pos(x,100)`, \an8 dialogue to MarginV=100), so a location card + its label, or a news caption + a shouted "King!", rendered on top of each other.
