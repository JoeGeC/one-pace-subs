---
name: Caption positioning
description: Captions use pos y=100 and Narrator lines use MarginV=100 to clear hardcoded Japanese text at top of screen
type: feedback
---

Captions should be positioned at y=100, and Narrator lines should have MarginV=100 to clear hardcoded Japanese text at the top of the screen. For two-line subtitles (containing \N), MarginV should be 200 to push them down double the amount.

**Why:** The video has burned-in Japanese text at the top that would overlap with default top-positioned subtitles. Two-line text is taller, so it needs double the margin to clear the burned-in text.

**How to apply:** When translating Caption-style lines that use \pos(), set the y coordinate to 100. For Narrator style lines, ensure MarginV=100 for single-line text, or MarginV=200 for two-line text (containing \N).
