---
name: project_wci19_katakuri_namecard_styles
description: WCI 19's ~600+ repeat animated name-card sequence uses per-character style names (Katakuri 2/3, God of Fortune, Du Feld, Stussy, etc.), not Title/Captions — repositioning logic correctly leaves them alone since they're geometrically positioned mid-frame, not top-of-frame.
metadata:
  type: project
---

Whole Cake Island 19 has a long guest-name-card overlay sequence during the tea
party arrivals (bounty/name cards like "Charlotte / Katakuri", "Bounty:
1,057,000,000 Belly"). It uses dozens of distinct style names — `Katakuri 2`
(360 lines), `Katakuri 3` (255 lines), plus ~12-14 lines each for `God of
Fortune`, `Du Feld`, `Stussy`, `Drug Peclo`, `Big News`, `Morgans`, `Giberson`,
`The Concealer`, `Deep-Sea Currents` — one style per named guest, each with its
own `\pos()` shifting frame-by-frame (e.g. `\pos(637,715)` -> `\pos(584,715)` ->
`\pos(583.5,715)` at ~4-centisecond layered triples for border/fill/shadow).

None of these are `Title`/`Captions` style names, but `validate_translation.py`'s
repositioning check doesn't gate on style name — it calls
`merge_translation._plan_top_positions`, which does geometric detection (actual
resolved margin/alignment/position), so it correctly determined these name-card
lines are NOT top-of-frame content (they sit mid-frame, y≈715 or y≈220) and left
them unpinned/untouched. Confirmed by spot-checking occurrences 1, 300, 600+ of
the sequence — `\pos()` coordinates were bit-for-bit identical between orig and
trans, translated text was consistent for repeated values (e.g. the bounty
figure "10億5700萬貝里" for "1,057,000,000 Belly" stayed the same across all
occurrences). Only 30 lines file-wide actually needed the `\an8` top-pin fix,
and the script reported "0 need fixing" both times — the katakuri block is not
where those 30 live.

Takeaway: when a description mentions a large repeating animated sequence, don't
assume it needs special-case repositioning handling — check whether
`_plan_top_positions` treats it as top-of-frame at all before worrying about
per-frame position drift. See [[project_off_by_one_shift_bug]] for the actual bug
this episode had (unrelated to the name-card sequence).
