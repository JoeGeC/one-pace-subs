---
name: project_off_by_one_shift_bug
description: A block of TAG MISMATCH lines with alternating styles (e.g. Musical/Main) is a symptom of a translation-content off-by-one shift — diagnose and fix by physical-line-number shifting, not by re-translating everything.
metadata:
  type: project
---

Found in Whole Cake Island 19 zh-TW: the validator's TAG MISMATCH list only flags
lines where a *formatting tag* actually differs between orig and trans (e.g. a
`{\fad(150,150)}` on a Musical lyric line landing on a plain Main-207+ line, or
vice versa). It does NOT flag a shift across two adjacent lines that both lack
special tags — so a reported cluster of ~10 TAG MISMATCH lines can be just the
visible tip of a much longer contiguous shift (in this episode: 83 lines, physical
lines 368-451, only ~10 of which happened to involve a tag-bearing Musical line
and so got caught).

**Root cause pattern**: one original line's translation was silently skipped
during the original translation/merge pass. Everything after it then got written
one slot early (`trans[L] = translation of orig[L+1]`) until the array was
patched back to the correct total count by duplicating one line's translation
into two adjacent slots (the duplicate happened to be *correct* content, it just
also got left in the wrong-shifted slot next to it) — resync happens right after
the duplicate.

**How to find the exact range**: dump orig vs trans text keyed by *physical file
line number* (not 0-based dialogue array index — the two are offset by wherever
`[Events]`/`Format:` lines end, e.g. first Dialogue line was at physical line 43
in this file) for the region around the first reported TAG MISMATCH, and read
forward. The shift is trans[L] == translation-of(orig[L+1]) — keep going until
trans[L] == translation-of(orig[L]) again (the resync point, often marked by an
exact duplicate string in two consecutive trans lines).

**How to fix**: this is a text-only bug — timing/style/margins for every line in
the range are still correct (metadata check passes 100%), only the Text field
content is offset. Fix by: for L from resync-end down to shift-start+1, set
text[L] = text[L-1] (shift back into place); then the one line at shift-start
needs a genuinely new translation (the one that was originally skipped) — write
one matching the surrounding style/tone (e.g. song lyric formatting with
`{\fad(...)}` and `♪...♪` wrapper if adjacent lines are Musical style).

**Why this matters**: re-running validate_translation.py --fix does nothing for
this — it's not a metadata or repositioning issue, so RESULT can still say PASS
with only a handful of TAG MISMATCH issues listed, masking the true blast radius.
Always manually trace the full extent of any TAG MISMATCH cluster with alternating
styles before concluding it's just a couple of isolated dropped-tag cases (see
[[project_italics_tag_dropped_in_zh]] for the other, benign cause of TAG MISMATCH).
