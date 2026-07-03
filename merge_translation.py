#!/usr/bin/env python3
"""
Merge translated dialogue back into an ASS subtitle file.

Takes the original ASS file and a translated TSV file (from extract_dialogue.py),
and produces a new ASS file with the translated text in place of the original.

Usage:
    python merge_translation.py original.ass translated.tsv [output.ass]

If output is omitted, it writes to <original_stem> zh-TW.ass in the same directory.

TSV format expected:
    LINE_NUM<tab>STYLE<tab>TRANSLATED_TEXT
"""

import re
import sys
from pathlib import Path

from extract_dialogue import extract, TRANSLATABLE_PREFIXES, style_matches

# Styles whose translated text should be repositioned to the top of the screen.
# The originals use \pos() for precise placement over Japanese text on screen,
# but translations should sit at the top so they don't overlap the main dialogue.
# Matched case-insensitively via style_matches (source files use both `Title`
# and `title`, `Captions` and `captions`).
TOP_POSITION_PREFIXES = ("Title", "Captions")

# Regex to strip \pos(...) tags from ASS override blocks
POS_TAG_RE = re.compile(r'\\pos\(([^,]+),([^)]+)\)')
# Regex to strip \an followed by a digit (existing alignment overrides)
AN_TAG_RE = re.compile(r'\\an\d')
# Regex to strip \move(...) — a caption pinned to the top must be static;
# leaving \move alongside the injected \pos is renderer-ambiguous.
MOVE_TAG_RE = re.compile(r'\\move\([^)]*\)')

# Repositioning geometry. Top-positioned lines (Title/Captions, and \an8 dialogue)
# are moved off the hardcoded English subs to the top of the screen. When several
# such lines are on screen at once they must be STACKED, not piled onto the same
# y — otherwise they overlap each other. STACK_TOP is the y of the topmost line in
# a group; each subsequent line drops by STACK_LINE_H per text line it contains.
STACK_TOP = 100
STACK_LINE_H = 55
OVERLAP_EPS = 0.3         # seconds; ignore briefer overlaps (crossfades) when stacking
DEFAULT_RES_X = 1280      # fallback PlayResX for centering \an8 lines when stacking


def _parse_time(t):
    h, m, s = t.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def _orig_pos(text):
    """Return (x, y) floats from the first \\pos() in text, or (None, None)."""
    m = POS_TAG_RE.search(text)
    if not m:
        return (None, None)
    try:
        return (float(m.group(1)), float(m.group(2)))
    except ValueError:
        return (None, None)


def _num(v):
    """Format a float without a trailing .0 (ASS positions are plain numbers)."""
    return f"{v:.2f}".rstrip("0").rstrip(".")


def _apply_top_pos(text, x, y):
    """Strip any existing \\pos/\\move/\\an from text and pin it to \\an8\\pos(x,y)."""
    text = POS_TAG_RE.sub("", text)
    text = MOVE_TAG_RE.sub("", text)
    text = AN_TAG_RE.sub("", text)
    pos_tag = f"\\an8\\pos({_num(x)},{_num(y)})"
    # Insert into the existing leading override block (which may now be empty
    # after stripping \pos/\an), otherwise open a new one.
    if text.startswith("{"):
        return "{" + pos_tag + text[1:]
    return "{" + pos_tag + "}" + text


def load_translations(tsv_path):
    """Load translated lines from TSV into a dict keyed by line number."""
    translations = {}
    with open(tsv_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n").rstrip("\r")
            if not line:
                continue
            parts = line.split("\t", 2)
            if len(parts) < 3:
                continue
            line_num = int(parts[0])
            translations[line_num] = parts[2]
    return translations


def _plan_top_positions(raw_lines, translations, res_x):
    """Decide the final (x, y) for every top-positioned translated line.

    Top-positioned = Title/Captions (always relocated to the top of screen to
    clear the hardcoded English subs) or any line whose text carries \\an8.
    Several of these can be on screen at once — a location caption, a character
    label and a shouted line, say. If they all pin to the same y they overlap,
    so we assign each to a horizontal ROW and stack the rows downward.

    Rows are assigned by interval-graph colouring: sweeping lines in start-time
    order, each takes the lowest row not currently occupied by another line it
    shares the screen with. Rows free up as lines end and are reused, so the
    number of rows only ever grows to the maximum simultaneously-on-screen count
    (a long chain of non-simultaneous captions does NOT keep stacking downward).
    A brief crossfade overlap (< OVERLAP_EPS) doesn't count as sharing a row.

    Typeset captions are often LAYERED: the same text drawn twice or more with
    identical timing on different layers (a border pass and a fill pass with
    different override tags). Those duplicates must land on the SAME (x, y) —
    stacking them apart tears the caption into ghost copies. We therefore group
    lines by (start, end, tag-stripped text) and assign one row per group.

    Returns {line_num: (x, y)} for every line to be pinned with \\an8\\pos.
    """
    groups = {}  # (start_str, end_str, plain_text) -> info incl. member line numbers
    for line_num, line in enumerate(raw_lines, 1):
        if line_num not in translations or not line.startswith("Dialogue:"):
            continue
        parts = line.split(",", 9)
        if len(parts) < 10:
            continue
        style = parts[3]
        trans_text = translations[line_num]
        is_caption = style_matches(style, TOP_POSITION_PREFIXES)
        is_an8 = "\\an8" in trans_text or "\\an8" in parts[9]
        if not (is_caption or is_an8):
            continue
        ox, _oy = _orig_pos(parts[9])  # x geometry from the ORIGINAL line
        key = (parts[1], parts[2], re.sub(r'\{[^}]*\}', '', trans_text))
        g = groups.setdefault(key, {
            "start": _parse_time(parts[1]),
            "end": _parse_time(parts[2]),
            "ox": ox,
            "nlines": 1 + trans_text.count("\\N"),
            "members": [],
        })
        g["members"].append(line_num)
        if g["ox"] is None:
            g["ox"] = ox

    if not groups:
        return {}

    # Uniform row height sized to the tallest caption so no two rows can touch.
    row_h = max(g["nlines"] for g in groups.values()) * STACK_LINE_H

    slot_end = []  # slot_end[i] = end time of the group currently holding row i
    assignment = {}
    for g in sorted(groups.values(), key=lambda g: g["start"]):
        slot = None
        for i, end in enumerate(slot_end):
            if end - OVERLAP_EPS <= g["start"]:  # row is free by the time g starts
                slot = i
                slot_end[i] = g["end"]
                break
        if slot is None:
            slot_end.append(g["end"])
            slot = len(slot_end) - 1
        x = g["ox"] if g["ox"] is not None else res_x / 2
        for n in g["members"]:
            assignment[n] = (x, STACK_TOP + slot * row_h)

    return assignment


def merge(original_path, translations, output_path):
    """Merge translations into the original ASS file.

    For each line number in the translations dict, replace the text field
    of the corresponding Dialogue line. All other lines are copied as-is.
    Top-positioned lines (Title/Captions and \\an8 dialogue) are relocated to
    the top of the screen and stacked when several coincide in time.
    """
    translated_count = 0

    # Detect BOM in original file to preserve it in output
    with open(original_path, "rb") as fb:
        has_bom = fb.read(3) == b"\xef\xbb\xbf"

    out_encoding = "utf-8-sig" if has_bom else "utf-8"

    with open(original_path, "r", encoding="utf-8-sig") as fin:
        raw_lines = [line.rstrip("\n").rstrip("\r") for line in fin]

    res_x = DEFAULT_RES_X
    for line in raw_lines:
        if line.lower().startswith("playresx:"):
            try:
                res_x = float(line.split(":", 1)[1].strip())
            except ValueError:
                pass
            break

    top_pos = _plan_top_positions(raw_lines, translations, res_x)

    with open(output_path, "w", encoding=out_encoding) as fout:
        for line_num, line in enumerate(raw_lines, 1):
            if line_num in translations and line.startswith("Dialogue:"):
                parts = line.split(",", 9)
                if len(parts) >= 10:
                    style = parts[3]
                    text = translations[line_num]

                    if line_num in top_pos:
                        x, y = top_pos[line_num]
                        text = _apply_top_pos(text, x, y)

                    if "\\an8" in text or style_matches(style, ("Narrator", "Note")):
                        parts[7] = "200" if "\\N" in text else "100"

                    prefix = ",".join(parts[:9]) + ","
                    fout.write(prefix + text + "\n")
                    translated_count += 1
                    continue

            # Adjust Narrator/Note style MarginV to 100 so it clears hardcoded top text
            line_lower = line.lower()
            if (line_lower.startswith("style: narrator") or line_lower.startswith("style: note")) and ",8," in line:
                line = re.sub(r',\d+,1$', ',100,1', line)

            fout.write(line + "\n")

    return translated_count


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} original.ass translated.tsv [output.ass]",
              file=sys.stderr)
        sys.exit(1)

    original_path = Path(sys.argv[1])
    tsv_path = Path(sys.argv[2])

    if not original_path.exists():
        print(f"Error: {original_path} not found", file=sys.stderr)
        sys.exit(1)
    if not tsv_path.exists():
        print(f"Error: {tsv_path} not found", file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) >= 4:
        output_path = Path(sys.argv[3])
    else:
        # Default: replace final part of name with zh-TW
        stem = original_path.stem
        output_path = original_path.with_name(stem + " zh-TW.ass")

    translations = load_translations(tsv_path)

    # Validate against the set of extractable lines.
    expected = extract(original_path)
    expected_nums = {ln for ln, style, text in expected}
    translated_nums = set(translations.keys())

    untranslated = sorted(expected_nums - translated_nums)
    extra = sorted(translated_nums - expected_nums)

    # `extra` is still a hard error: a translated line whose LINE_NUM isn't in the
    # source means a typo in the LINE_NUM column (or a line number off-by-one from
    # a chunked write). These would silently land on the wrong dialogue line.
    if extra:
        print(f"ERROR: {len(extra)} translated lines reference line numbers not in the source: "
              f"{extra[:20]}{'...' if len(extra) > 20 else ''}", file=sys.stderr)
        print("These are likely typos in the LINE_NUM column. Fix them and re-run.", file=sys.stderr)
        sys.exit(1)

    # `untranslated` is allowed: the agent may intentionally omit lines that are
    # kept in the source language (signs already in the target language, pure
    # punctuation, onomatopoeia, etc.). merge() leaves the original text in place
    # for any line not present in the TSV. We report them so nothing is dropped
    # silently — scan this list to confirm every omission was deliberate.
    count = merge(original_path, translations, output_path)

    print(f"Merged {count} translated lines into {output_path}")
    if untranslated:
        print(f"Kept {len(untranslated)} source lines untranslated (originals preserved): "
              f"{untranslated[:20]}{'...' if len(untranslated) > 20 else ''}")


if __name__ == "__main__":
    main()
