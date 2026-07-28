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

from extract_dialogue import extract, style_matches

# Styles whose translated text should be repositioned to the top of the screen.
# The originals use \pos() for precise placement over Japanese text on screen,
# but translations should sit at the top so they don't overlap the main dialogue.
# Matched case-insensitively via style_matches (source files use both `Title`
# and `title`, `Captions` and `captions`).
TOP_POSITION_PREFIXES = ("Title", "Captions")

# Regex to strip \pos(...) tags from ASS override blocks
POS_TAG_RE = re.compile(r'\\pos\(([^,]+),([^)]+)\)')
# Regex to strip \an followed by a digit (new-style alignment overrides)
AN_TAG_RE = re.compile(r'\\an\d')
# Regex to strip legacy \a<N> alignment overrides (VSFilter numbering: 1-3
# bottom, 5-7 top, 9-11 middle). Must not match \an — the (?!\d) guard plus
# requiring a digit immediately after \a keeps it independent of AN_TAG_RE.
LEGACY_A_TAG_RE = re.compile(r'\\a(?:1[01]|[1-9])(?!\d)')
# Regex to find an explicit \an<N> or legacy \a<N> tag, to resolve which of
# the 9 (or 11) alignment zones a line's OWN override claims — used by
# _resolve_zone_and_margin below, which falls back to the style's default
# Alignment field when neither tag is present.
AN_TAG_SEARCH_RE = re.compile(r'\\an([1-9])(?!\d)')
LEGACY_A_TAG_SEARCH_RE = re.compile(r'\\a(1[01]|[1-9])(?!\d)')
STYLE_LINE_RE = re.compile(r'^style:\s*(.*)$', re.IGNORECASE)
# Regex to strip \move(...) — a caption pinned to the top must be static;
# leaving \move alongside the injected \pos is renderer-ambiguous.
MOVE_TAG_RE = re.compile(r'\\move\([^)]*\)')
# Regex to match a fade tag (\fad(t1,t2) or the complex \fade(...)). Unlike
# \pos/\move/\an, a fade is part of the caption's typesetting (fade-in/out)
# and must SURVIVE repositioning — see _apply_top_pos, which recovers it from
# the source line rather than trusting the translated text to have kept it.
FAD_TAG_RE = re.compile(r'\\fade?\([^)]*\)')

# A line renders "flush against the top" if its resolved on-screen anchor
# lands within this many pixels of the top edge — regardless of whether that
# came from an explicit top-alignment tag or from a plain bottom-anchored
# line whose MarginV was cranked up to push it near the top (a pattern found
# in Main/Secondary dialogue with no alignment tag at all, e.g. Dressrosa 38
# "Leo, can you hear me?" at MarginV=660 on a 720-tall frame). Calibrated
# against a corpus-wide scan: genuine top-flush lines cluster at 60-145px;
# the next cluster (deliberate mid-frame "epitaph" captions like the Lao G/
# Baby 5 name cards) starts at 213px+, so 150 sits cleanly in the gap.
TOP_MARGIN_THRESHOLD = 150

# Repositioning geometry. Top-positioned lines (Title/Captions, and \an8 dialogue)
# are moved off the hardcoded English subs to the top of the screen. When several
# such lines are on screen at once they must be STACKED, not piled onto the same
# y — otherwise they overlap each other. STACK_TOP is the y of the topmost line in
# a group; each subsequent line drops by STACK_LINE_H per text line it contains.
STACK_TOP = 100
STACK_LINE_H = 55
OVERLAP_EPS = 0.3         # seconds; ignore briefer overlaps (crossfades) when stacking
DEFAULT_RES_X = 1280      # fallback PlayResX for centering \an8 lines when stacking
DEFAULT_RES_Y = 720       # fallback PlayResY for keeping stacked rows on-screen

# Montage screens (character-introduction recaps etc.) label many characters
# at once, each \pos'd beside its character across the whole frame. Pinning
# such a screen stacks rows far past the bottom of the frame — most labels
# would land off-screen. Clusters of more than this many simultaneous caption
# groups therefore KEEP their original \pos instead of being pinned.
MAX_PINNED_CLUSTER = 3

# Sidecar file of manual per-line position overrides. The stacking planner only
# knows about caption-vs-caption collisions in TIME; it cannot see burned-in
# content in the video frame (a hardcoded English caption or an in-frame sign
# already occupying the top of the screen). Lines listed here are pinned to the
# given (x, y) instead of the planner's choice. Format, tab-separated:
#     <original .ass filename>	<line_num>	<x>	<y>
# Lines starting with # are comments.
OVERRIDES_PATH = Path(__file__).parent / "position_overrides.tsv"

# Sidecar file of manual per-line MarginV overrides. The automatic Narrator/Note
# margin (100 per text line, see below) only accounts for OUR translated line
# count — it can't know how many lines the hardcoded English narration burned
# into the video occupies, so a short Chinese line can still collide with a
# taller English one above it. Lines listed here get their MarginV pinned to
# the given value instead of the formula's choice. Format, tab-separated:
#     <original .ass filename>	<line_num>	<marginV>
# Lines starting with # are comments.
MARGIN_OVERRIDES_PATH = Path(__file__).parent / "margin_overrides.tsv"


def _load_position_overrides(original_name):
    """Return {line_num: (x, y)} overrides for this original file, if any."""
    overrides = {}
    if not OVERRIDES_PATH.exists():
        return overrides
    with open(OVERRIDES_PATH, "r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw or raw.startswith("#"):
                continue
            parts = raw.split("\t")
            if len(parts) != 4 or parts[0] != original_name:
                continue
            overrides[int(parts[1])] = (float(parts[2]), float(parts[3]))
    return overrides


def _load_margin_overrides(original_name):
    """Return {line_num: marginV} overrides for this original file, if any."""
    overrides = {}
    if not MARGIN_OVERRIDES_PATH.exists():
        return overrides
    with open(MARGIN_OVERRIDES_PATH, "r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw or raw.startswith("#"):
                continue
            parts = raw.split("\t")
            if len(parts) != 3 or parts[0] != original_name:
                continue
            overrides[int(parts[1])] = parts[2]
    return overrides


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


def _parse_styles(raw_lines):
    """Return {style_name_lower: (alignment, marginV)} parsed from the [V4+ Styles] header."""
    styles = {}
    for line in raw_lines:
        m = STYLE_LINE_RE.match(line.strip())
        if not m:
            continue
        parts = m.group(1).split(",")
        if len(parts) < 22:
            continue
        name = parts[0].strip().lower()
        try:
            alignment = int(parts[18])
            marginv = float(parts[21])
        except ValueError:
            continue
        styles[name] = (alignment, marginv)
    return styles


def _zone(alignment):
    """Map a 1-9 numpad-style alignment (new \\an tag OR the style's own
    Alignment field, which uses the same numbering) to top/middle/bottom."""
    if alignment in (7, 8, 9):
        return "top"
    if alignment in (4, 5, 6):
        return "middle"
    return "bottom"


def _legacy_zone(alignment):
    """Map a 1-11 legacy \\a alignment (VSFilter numbering) to top/middle/bottom."""
    if alignment in (5, 6, 7):
        return "top"
    if alignment in (9, 10, 11):
        return "middle"
    return "bottom"


def _is_flush_top(text, style, dialogue_marginv, style_map, res_y):
    """Return True if this line's resolved vertical anchor lands within
    TOP_MARGIN_THRESHOLD of the top of the frame — whatever mechanism put it
    there. Covers three cases uniformly:
      1. Explicit top alignment (\\an7/8/9 or legacy \\a5/6/7) with a small
         MarginV (the classic "burned-in top text" collision).
      2. A plain bottom-anchored line (no alignment tag, or \\an1-3/\\a1-3)
         whose MarginV was pushed up so far that its anchor sits near the
         top anyway — no alignment tag involved at all.
      3. Middle-anchored lines are never flagged; a moderate MarginV there
         doesn't put text at the very top edge.
    Lines that already carry an explicit \\pos(...) are skipped — their
    position is art-directed (per-frame typesetting, animated calligraphy)
    and MarginV is meaningless for them. Narrator/Note lines are also
    skipped — those styles are top-aligned (Alignment=8) by design and
    already get their own top-clearance treatment (a flat MarginV bump
    elsewhere in merge()), not \\an8/\\pos pinning; sweeping them in here
    would flag the entire Narrator/Note track as "needs repositioning"
    even though they're already handled by a different, working mechanism.
    """
    if POS_TAG_RE.search(text):
        return False
    if style_matches(style, ("Narrator", "Note")):
        return False

    m = AN_TAG_SEARCH_RE.search(text)
    if m:
        zone = _zone(int(m.group(1)))
    else:
        m = LEGACY_A_TAG_SEARCH_RE.search(text)
        if m:
            zone = _legacy_zone(int(m.group(1)))
        else:
            alignment, style_marginv = style_map.get(style.strip().lower(), (2, 18.0))
            zone = _zone(alignment)

    if zone == "middle":
        return False

    if dialogue_marginv > 0:
        marginv = dialogue_marginv
    else:
        _, marginv = style_map.get(style.strip().lower(), (2, 18.0))

    y_from_top = marginv if zone == "top" else (res_y - marginv)
    return y_from_top < TOP_MARGIN_THRESHOLD


def _apply_top_pos(text, x, y, orig_text=""):
    """Strip any existing \\pos/\\move/\\an/\\a from text and pin it to \\an8\\pos(x,y).

    A fade (\\fad/\\fade) is part of the caption's typesetting, not its
    placement, and must survive the reposition. If the translated text still
    carries its fade we leave it exactly where it is — reordering it would
    itself trip the validator's tag-order check on complex multi-tag captions
    (\\blur\\bord\\fad\\fscx...). Only when the translation DROPPED the fade do
    we recover it from the source line, so a repositioned caption never
    silently loses its fade-in/out (the bug seen on fade-only Titles and on
    simple {\\fad\\pos} captions whose whole tag block the translator omitted).
    """
    text = POS_TAG_RE.sub("", text)
    text = MOVE_TAG_RE.sub("", text)
    text = AN_TAG_RE.sub("", text)
    text = LEGACY_A_TAG_RE.sub("", text)
    if FAD_TAG_RE.search(text):
        fad = ""  # translation kept a fade — don't move it or add a second
    else:
        fad_match = FAD_TAG_RE.search(orig_text)
        fad = fad_match.group(0) if fad_match else ""
    pos_tag = f"\\an8\\pos({_num(x)},{_num(y)}){fad}"
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


def _plan_top_positions(raw_lines, translations, res_x, res_y, style_map):
    """Decide the final (x, y) for every top-positioned translated line.

    Top-positioned = Title/Captions (always relocated to the top of screen to
    clear the hardcoded English subs) or any line whose RESOLVED on-screen
    position lands near the top edge (see _is_flush_top) — whether that's
    from an explicit top alignment tag or just a bottom-anchored line with
    an oversized MarginV pushing it up there. Without this, those lines
    render flush against the top edge and collide with whatever's burned
    into the top of the frame.
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
        try:
            dialogue_marginv = float(parts[7])
        except ValueError:
            dialogue_marginv = 0.0
        is_caption = style_matches(style, TOP_POSITION_PREFIXES)
        is_top_aligned = (_is_flush_top(trans_text, style, dialogue_marginv, style_map, res_y)
                           or _is_flush_top(parts[9], style, dialogue_marginv, style_map, res_y))
        if not (is_caption or is_top_aligned):
            continue
        # Motion-tracked frames (Aegisub-Motion {=NN...} marker) are positioned
        # per-frame to follow the camera — never pin them to the top.
        if re.search(r'\{=\d', parts[9]):
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

    # Cluster time-overlapping groups; clusters larger than MAX_PINNED_CLUSTER
    # (montage screens) keep their original \pos — exclude them from pinning.
    clusters = []
    cur, cur_end = [], None
    for g in sorted(groups.values(), key=lambda g: g["start"]):
        if cur and g["start"] < cur_end - OVERLAP_EPS:
            cur.append(g)
            cur_end = max(cur_end, g["end"])
        else:
            if cur:
                clusters.append(cur)
            cur, cur_end = [g], g["end"]
    if cur:
        clusters.append(cur)
    pinned = [g for c in clusters if len(c) <= MAX_PINNED_CLUSTER for g in c]
    if not pinned:
        return {}

    # Uniform row height sized to the tallest caption so no two rows can touch.
    # Some captions pad themselves with many blank \N lines purely to offset a
    # second piece of text lower within their OWN box (a single-anchor
    # two-tier name-card trick) — that isn't real stacked content, but it
    # still inflates nlines, so row_h can be huge. Combined with several rows
    # (multiple groups overlapping in time) that pushes far past the bottom
    # of the frame. Rather than trying to detect the padding trick, just
    # refuse to place anything past the frame — see max_y below.
    row_h = max(g["nlines"] for g in pinned) * STACK_LINE_H
    max_y = res_y - STACK_LINE_H  # leave room for at least one line at the bottom

    slot_end = []  # slot_end[i] = end time of the group currently holding row i
    assignment = {}
    for g in sorted(pinned, key=lambda g: g["start"]):
        slot = None
        for i, end in enumerate(slot_end):
            if end - OVERLAP_EPS <= g["start"]:  # row is free by the time g starts
                slot = i
                slot_end[i] = g["end"]
                break
        if slot is None:
            slot_end.append(g["end"])
            slot = len(slot_end) - 1
        y = STACK_TOP + slot * row_h
        if y > max_y:
            # Stacking this row would push the group off-screen. Leave its
            # original position untouched rather than making it invisible.
            continue
        x = g["ox"] if g["ox"] is not None else res_x / 2
        for n in g["members"]:
            assignment[n] = (x, y)

    return assignment


def merge(original_path, translations, output_path):
    """Merge translations into the original ASS file.

    For each line number in the translations dict, replace the text field
    of the corresponding Dialogue line. All other lines are copied as-is.
    Top-positioned lines (Title/Captions and top-aligned dialogue, old- or
    new-style) are relocated to the top of the screen and stacked when
    several coincide in time.
    """
    translated_count = 0

    # Detect BOM in original file to preserve it in output
    with open(original_path, "rb") as fb:
        has_bom = fb.read(3) == b"\xef\xbb\xbf"

    out_encoding = "utf-8-sig" if has_bom else "utf-8"

    with open(original_path, "r", encoding="utf-8-sig") as fin:
        raw_lines = [line.rstrip("\n").rstrip("\r") for line in fin]

    res_x = DEFAULT_RES_X
    res_y = DEFAULT_RES_Y
    for line in raw_lines:
        if line.lower().startswith("playresx:"):
            try:
                res_x = float(line.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif line.lower().startswith("playresy:"):
            try:
                res_y = float(line.split(":", 1)[1].strip())
            except ValueError:
                pass

    style_map = _parse_styles(raw_lines)
    top_pos = _plan_top_positions(raw_lines, translations, res_x, res_y, style_map)
    top_pos.update(_load_position_overrides(Path(original_path).name))
    margin_overrides = _load_margin_overrides(Path(original_path).name)

    with open(output_path, "w", encoding=out_encoding) as fout:
        for line_num, line in enumerate(raw_lines, 1):
            if line_num in translations and line.startswith("Dialogue:"):
                parts = line.split(",", 9)
                if len(parts) >= 10:
                    style = parts[3]
                    text = translations[line_num]

                    if line_num in top_pos:
                        x, y = top_pos[line_num]
                        text = _apply_top_pos(text, x, y, orig_text=parts[9])

                    if "\\an8" in text or style_matches(style, ("Narrator", "Note")):
                        parts[7] = str(100 * (1 + text.count("\\N")))

                    if line_num in margin_overrides:
                        parts[7] = margin_overrides[line_num]

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
