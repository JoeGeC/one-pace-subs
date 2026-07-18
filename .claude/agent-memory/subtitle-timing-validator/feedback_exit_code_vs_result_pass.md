---
name: feedback_exit_code_vs_result_pass
description: validate_translation.py can exit 1 while still printing "RESULT: PASS" — don't treat nonzero exit as a real failure on its own
metadata:
  type: feedback
---

`validate_translation.py` exits 1 whenever any *unfixable* issue string
exists — including TAG MISMATCH lines (dropped/added \i, \b, etc. formatting
inside dialogue text) — even when metadata_fail is 0 and the report body
prints "RESULT: PASS". Root cause is in `main()`: it exits 1 if
`issues and (not fix or has_unfixable)`, and `has_unfixable` is true for any
issue string that isn't a "Line N ... repositioning" fix note. TAG MISMATCH
issues fall into that bucket.

Example: WCI 01 zh-TW validation (2026-07-18) exited 1 but the report itself
said "RESULT: PASS" with "Metadata check: 559 OK, 0 FAILED" — the only
issues were 2 cosmetic TAG MISMATCH lines where the translator dropped
`{\i1}...{\i0}` emphasis italics around a single emphasized word/phrase
(e.g. "wonder...{\i1}land{\i0}" -> plain Chinese with no italics). Chinese
has no real typographic convention for mid-sentence italic emphasis, so
translators often drop it; this is a stylistic/translation call, not a
timing or positioning defect, and is out of scope to "fix" (fixing would
mean picking which Chinese substring to wrap in \i1\i0 — a text-content
judgment call, not layout).

**Why:** Misreading exit code 1 as FAIL when the printed report says PASS
would cause unnecessary rework or incorrect reporting to the user.

**How to apply:** Always read the printed "RESULT:" line and the
`metadata_fail` count, not just the shell exit code, to decide pass/fail.
Report TAG MISMATCH-only issues (no metadata failures) as informational
notes, same tier as OVERLAP WARNINGS — not as validation failures requiring
a fix.
