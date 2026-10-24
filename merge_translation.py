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

from extract_dialogue import (
    extract,
    is_translatable,
    is_drawing_only,
    style_matches,
    group_translatable,
    leading_tags,
    strip_leading_tags,
)

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
# \clip/\iclip mask a caption to a screen region — rectangle or vector drawing.
# Wipe/gradient typeset draws a caption as many copies each clipped to a thin
# strip (Wano 61 "Bariete": 252 two-pixel strips); moving \pos without moving
# the clip leaves every strip masking empty screen and the caption vanishes.
CLIP_TAG_RE = re.compile(r'\\(i?clip)\(([^)]*)\)')

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
# y — otherwise they overlap each other. STACK_TOP is the highest y a pinned line
# may take; lines are pushed further down past any burned-in English or other
# pinned Chinese on screen at the same time (see _plan_top_positions).
STACK_TOP = 100
OVERLAP_EPS = 0.3         # seconds; ignore briefer overlaps (crossfades) when stacking
FRAME_EPS = 0.05          # seconds; max gap between frames of one animated caption
DEFAULT_RES_X = 1280      # fallback PlayResX for centering \an8 lines when stacking
DEFAULT_RES_Y = 720       # fallback PlayResY for keeping stacked rows on-screen

# Montage screens (character-introduction recaps etc.) label many characters
# at once, each \pos'd beside its character across the whole frame. Pinning
# such a screen stacks rows far past the bottom of the frame — most labels
# would land off-screen. When more than this many caption groups are on screen
# at once, those captions KEEP their original \pos instead of being pinned.
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


# Dialogue-style lines that the source pins with an explicit \pos (two speakers
# placed left/right of frame, a line parked beside its speaker, ...) sit exactly
# where the hardcoded English copy of that line is burned into the video. The
# player only lifts ordinary bottom-anchored dialogue above the burn-in; a \pos
# line bypasses that and lands on top of the English. Such lines are moved just
# ABOVE the English block — or just BELOW it when above would leave the frame —
# offset by the English block's height (its own line count x line height), the
# same way stacked top lines are offset by their line count.
POS_DIALOGUE_PREFIXES = ("Main", "Secondary", "Thoughts", "Flashbacks", "Narrator", "Note")
# Art-directed typesetting (custom fonts, drawings, clips, rotation, animation,
# motion tracking) is not plain positioned dialogue; moving it would tear it off
# the scene element it's drawn onto, so those lines keep their source position.
POS_TYPESET_RE = re.compile(r'\\(?:fn|p[1-9]|i?clip|org|fr[xyz]?-?\d|t\(|move)|\{=\d')
FS_TAG_RE = re.compile(r'\\fs(\d+(?:\.\d+)?)')
FSCY_TAG_RE = re.compile(r'\\fscy(\d+(?:\.\d+)?)')
POS_LINE_SPACING = 1.15   # rendered line height as a multiple of the font size
POS_GAP = 10              # px of clearance between the English and Chinese blocks


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
    and MarginV is meaningless for them. Narrator/Note lines (top-aligned
    by style) are included: their old flat MarginV bump (100 per CHINESE
    line) ignored how tall the burned-in English narration is, so a
    two-line English narration (y 27-216 at 1080p) sat under a Chinese line
    at y=100 (Reverie 03 "The World Government is a truly massive
    organization.").
    """
    if POS_TAG_RE.search(text):
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


def _apply_top_pos(text, x, y, orig_text="", clip_dy=0):
    """Strip any existing \\pos/\\move/\\an/\\a from text and pin it to \\an8\\pos(x,y).

    Clips move with the text: each \\clip/\\iclip is rebuilt from the SOURCE
    line's clip shifted by clip_dy (see _clip_dy), so re-pinning an
    already-pinned line never shifts its clip twice.

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
    if clip_dy and orig_text:
        shifted = iter([_shift_clip(m, clip_dy) for m in CLIP_TAG_RE.finditer(orig_text)])
        text = CLIP_TAG_RE.sub(lambda m: next(shifted, m.group(0)), text)
    pos_tag = f"\\an8\\pos({_num(x)},{_num(y)}){fad}"
    # Keep a leading Aegisub-Motion {=NN} marker block intact and in front —
    # writing tags into it ({\an8\pos(..)=59}) corrupts the marker.
    marker = re.match(r'(?:\{=[^}\\]*\})*', text).group(0)
    text = text[len(marker):]
    # Insert into the existing leading override block (which may now be empty
    # after stripping \pos/\an), otherwise open a new one.
    if text.startswith("{"):
        return marker + "{" + pos_tag + text[1:]
    return marker + "{" + pos_tag + "}" + text


def _shift_clip(match, dy):
    """A CLIP_TAG_RE match rebuilt with every y coordinate moved by dy."""
    kind, args = match.group(1), [a.strip() for a in match.group(2).split(",")]
    if len(args) == 4:  # rectangle: x1,y1,x2,y2
        x1, y1, x2, y2 = args
        return f"\\{kind}({x1},{_num(_float(y1) + dy)},{x2},{_num(_float(y2) + dy)})"
    # Vector: [scale,] drawing. Coordinates come in x y pairs; a scale of n
    # means the drawing is in units of 1/2^(n-1) px.
    scale = int(_float(args[0])) if len(args) > 1 else 1
    dy_units = dy * 2 ** (max(scale, 1) - 1)
    out, is_y = [], False
    for tok in args[-1].split():
        try:
            v = float(tok)
        except ValueError:
            out.append(tok)
            continue
        out.append(_num(v + dy_units) if is_y else tok)
        is_y = not is_y
    return f"\\{kind}(" + ",".join(args[:-1] + [" ".join(out)]) + ")"


def _clip_dy(orig_text, text, style, dialogue_marginv, new_top, res_y, style_map, style_fonts):
    """How far a pinned line's text block moves vertically: from the top of the
    translated block at the source's own anchor to its new \\an8 top."""
    if not CLIP_TAG_RE.search(orig_text):
        return 0
    old = _text_extent(orig_text, style, dialogue_marginv, res_y, style_map, style_fonts,
                       nlines=_visible_line_count(text))
    return new_top - old[0] if old else 0


def _blank_drawing(text):
    """A drawing line's override blocks without its drawing commands."""
    return "".join(re.findall(r'\{[^}]*\}', text))


def _float(v):
    try:
        return float(v)
    except ValueError:
        return 0.0


def _parse_style_fonts(raw_lines):
    """Return {style_name_lower: (Fontsize, ScaleY)} from the [V4+ Styles] header."""
    fonts = {}
    for line in raw_lines:
        m = STYLE_LINE_RE.match(line.strip())
        if not m:
            continue
        parts = m.group(1).split(",")
        if len(parts) < 22:
            continue
        try:
            fonts[parts[0].strip().lower()] = (float(parts[2]), float(parts[12]))
        except ValueError:
            continue
    return fonts


def _strip_comments(text):
    """Drop {editor comments}, keeping {\\override} blocks — comments quote
    the old line, \\N and all, and must not count as rendered text."""
    return re.sub(r'\{(?!\\)[^}]*\}', '', text)


def _visible_line_count(text):
    """Number of rendered text lines, ignoring \\N inside {editor comments}."""
    return 1 + re.sub(r'\{[^}]*\}', '', text).count("\\N")


def _line_height(text, style, style_fonts):
    """Rendered height of one text line: font size x vertical scale, with
    \\fs / \\fscy overrides taking precedence over the style's values."""
    size, scale_y = style_fonts.get(style.strip().lower(), (0.0, 100.0))
    tags = _strip_comments(text)
    fs = FS_TAG_RE.search(tags)
    fscy = FSCY_TAG_RE.search(tags)
    if fs:
        size = float(fs.group(1))
    if fscy:
        scale_y = float(fscy.group(1))
    return size * scale_y / 100 * POS_LINE_SPACING


def _alignment(text, style, style_map):
    """Resolved 1-9 numpad alignment: \\an tag, legacy \\a tag, else the style's."""
    tags = _strip_comments(text)
    m = AN_TAG_SEARCH_RE.search(tags)
    if m:
        return int(m.group(1))
    m = LEGACY_A_TAG_SEARCH_RE.search(tags)
    if m:
        legacy = int(m.group(1))
        return {5: 7, 6: 8, 7: 9, 9: 4, 10: 5, 11: 6}.get(legacy, legacy)
    return style_map.get(style.strip().lower(), (2, 0))[0]


def _text_extent(text, style, dialogue_marginv, res_y, style_map, style_fonts, nlines=None):
    """(top, bottom) y of a line's rendered text block, or None if it has no
    visible text. Anchored at its \\pos (or \\move start) if it has one, else
    at the MarginV its alignment zone implies. `nlines` overrides the text's
    own line count (to size a translation at its source line's anchor)."""
    if not re.sub(r'\{[^}]*\}', '', text).replace("\\N", "").strip():
        return None
    tags = _strip_comments(text)
    zone = _zone(_alignment(tags, style, style_map))
    h = (nlines or _visible_line_count(text)) * _line_height(tags, style, style_fonts)
    _x, y = _orig_pos(tags)
    if y is None:
        m = re.search(r'\\move\(\s*[^,]+,\s*([^,]+)', tags)
        y = _float(m.group(1)) if m else None
    if y is None:
        marginv = dialogue_marginv or style_map.get(style.strip().lower(), (2, 18.0))[1]
        y = {"top": marginv, "bottom": res_y - marginv, "middle": res_y / 2}[zone]
    if zone == "top":
        return (y, y + h)
    if zone == "bottom":
        return (y - h, y)
    return (y - h / 2, y + h / 2)


def _plan_pos_offsets(raw_lines, translations, res_y, style_map, style_fonts, skip):
    """Decide where each \\pos-pinned dialogue line goes to clear its burned-in
    English copy (see POS_DIALOGUE_PREFIXES).

    The English block's vertical extent is derived from the source line's
    anchor (\\pos y + alignment zone) and its height — source line count x line
    height. The Chinese block is placed POS_GAP above that extent, bottom-
    anchored; if its own height (translated line count x line height) would
    push it past the top of the frame, it's placed POS_GAP below instead,
    top-anchored. If neither fits, whichever side has more room wins.

    Returns {line_num: (x, y, an)} — `an` keeps the source's horizontal
    alignment (left/centre/right) with the new vertical anchor.
    """
    plan = {}
    for line_num, line in enumerate(raw_lines, 1):
        if line_num in skip or line_num not in translations or not line.startswith("Dialogue:"):
            continue
        parts = line.split(",", 9)
        if len(parts) < 10:
            continue
        style, orig = parts[3], parts[9]
        if not style_matches(style, POS_DIALOGUE_PREFIXES):
            continue
        x, y = _orig_pos(orig)
        if y is None or POS_TYPESET_RE.search(orig):
            continue
        line_h = _line_height(orig, style, style_fonts)
        if line_h <= 0:
            continue
        h_col = (_alignment(orig, style, style_map) - 1) % 3  # 0 left, 1 centre, 2 right
        extent = _text_extent(orig, style, _float(parts[7]), res_y, style_map, style_fonts)
        if extent is None:
            continue
        en_top, en_bottom = extent

        zh_h = _visible_line_count(translations[line_num]) * line_h
        room_above = en_top - POS_GAP
        room_below = res_y - (en_bottom + POS_GAP)
        if room_above >= zh_h or room_above >= room_below:
            plan[line_num] = (x, room_above, 1 + h_col)       # \an1-3: bottom edge
        else:
            plan[line_num] = (x, en_bottom + POS_GAP, 7 + h_col)  # \an7-9: top edge
    return plan


def _apply_pos_offset(text, x, y, an):
    """Re-pin text to \\an<an>\\pos(x,y), keeping every other override tag."""
    text = POS_TAG_RE.sub("", text)
    text = AN_TAG_RE.sub("", text)
    text = LEGACY_A_TAG_RE.sub("", text)
    pos_tag = f"\\an{an}\\pos({_num(x)},{_num(y)})"
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
    label and a shouted line, say — on top of the burned-in English, which is
    itself often at the top (an \\an8 English line at 1080p is ~94px per line).
    Sweeping lines in start-time order, each takes the first vertical gap from
    STACK_TOP down that's tall enough for it (translated line count x real line
    height) and clear of every burned-in English block and already-pinned line
    sharing the screen with it. Space frees up as lines end, so a long chain of
    non-simultaneous captions does NOT keep stacking downward. A brief
    crossfade overlap (< OVERLAP_EPS) doesn't count as sharing the screen.

    Typeset captions are often LAYERED: the same text drawn twice or more with
    identical timing on different layers (a border pass and a fill pass with
    different override tags). Those duplicates must land on the SAME (x, y) —
    stacking them apart tears the caption into ghost copies. We therefore group
    lines by (start, end, tag-stripped text) and place each group once.

    Returns {line_num: (x, y)} for every line to be pinned with \\an8\\pos.
    """
    style_fonts = _parse_style_fonts(raw_lines)
    groups = {}  # (start_str, end_str, plain_text) -> info incl. member line numbers
    for line_num, line in enumerate(raw_lines, 1):
        if line_num not in translations or not line.startswith("Dialogue:"):
            continue
        parts = line.split(",", 9)
        if len(parts) < 10:
            continue
        style = parts[3]
        trans_text = translations[line_num]
        dialogue_marginv = _float(parts[7])
        is_caption = style_matches(style, TOP_POSITION_PREFIXES)
        is_top_aligned = (_is_flush_top(trans_text, style, dialogue_marginv, style_map, res_y)
                           or _is_flush_top(parts[9], style, dialogue_marginv, style_map, res_y))
        if not (is_caption or is_top_aligned):
            continue
        # Motion-tracked frames (Aegisub-Motion {=NN...} marker) are positioned
        # per-frame to follow the camera. Captions/Title frames still go to the
        # top: they track the burned-in English name card / sign, so leaving them
        # in place covers it (Wano 35 Raizo card after the Oct 2026 upstream
        # retime marked it {=59}). The run chaining below gives the whole track
        # one y, and the montage rule keeps word-by-word boards (Dressrosa 39)
        # in place. Other tracked lines (\an8 dialogue) keep their positions.
        if re.search(r'\{=\d', parts[9]) and not is_caption:
            continue
        # Perspective/3D-rotated typeset (an \org() rotation origin paired with
        # \frx/\fry/\frz) is locked to scene geometry: the glyphs rotate about
        # \org, so moving only \pos to the top while leaving \org where it was
        # shears the caption off its intended spot (a ~14deg \frz about a pivot
        # ~240px away swings the text sideways and out of frame). These stylized
        # cards — e.g. Wano's "Vile Criminal" wanted-poster title — sit mid-frame
        # over a scene element, not over the bottom dialogue, so they need no
        # top-clearing. Keep their original placement; the translated words are
        # swapped in by expand_grouped_translations while the frame's own
        # \pos/\org/rotation block is preserved.
        if "\\org(" in parts[9] and re.search(r'\\fr[xyz]', parts[9]):
            continue
        plain = re.sub(r'\{[^}]*\}', '', trans_text)
        ox, oy = _orig_pos(parts[9])  # x geometry from the ORIGINAL line
        # Where the caption sits, for montage detection: its \\pos, else its
        # \\move start, else (unpositioned) its text.
        mv = re.search(r'\\move\(\s*([^,]+),\s*([^,]+)', parts[9])
        place = (ox, oy) if ox is not None else (
            (_float(mv.group(1)), _float(mv.group(2))) if mv else plain)
        key = (parts[1], parts[2], plain)
        g = groups.setdefault(key, {
            "start": _parse_time(parts[1]),
            "end": _parse_time(parts[2]),
            "ox": ox,
            "place": place,
            "is_caption": is_caption,
            "plain": plain,
            "nlines": 1 + trans_text.count("\\N"),
            "line_h": _line_height(trans_text, style, style_fonts),
            "members": [],
        })
        g["members"].append(line_num)
        if g["ox"] is None:
            g["ox"] = ox

    if not groups:
        return {}

    # Cluster time-overlapping groups. A cluster that ever shows more than
    # MAX_PINNED_CLUSTER captions AT ONCE is a montage screen: its captions keep
    # their original \pos. Only simultaneous captions count — a run of
    # back-to-back top dialogue chained between two name cards is not a montage
    # (Reverie 01's Ivankov/Dragon cards: two cards + three \an8 lines formed a
    # 5-group chain, and the whole chain was left unpinned on top of the
    # English). Dialogue in a montage cluster is still pinned.
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
    pinned = [g for c in clusters for g in c
              if not g["is_caption"] or _max_concurrent(
                  [x for x in c if x["is_caption"]]) <= MAX_PINNED_CLUSTER]
    if not pinned:
        return {}

    # Each group takes the first free vertical gap from STACK_TOP down, sized
    # to its real rendered height (line count x line height — 720p-calibrated
    # fixed rows overlapped at 1080p, where one line is ~94px). "Busy" bands
    # are everything already on screen while the group is: the burned-in
    # English of every source line — INCLUDING the group's own English, which
    # for a two-line \an8 line at 1080p runs well past STACK_TOP (Reverie 01
    # "pirate scum") — plus Chinese lines already placed.
    #
    # Animated captions are authored one line per frame. Placing frames
    # independently let consecutive frames land in different gaps (the caption
    # visibly jumps), so back-to-back frames of the same text form a RUN that
    # is placed once, over the run's whole time span; each frame keeps its own
    # animated x. A long run has to dodge every line that comes and goes while
    # it's up; if no single y clears all of them, its frames are placed one by
    # one instead — a caption that steps between rows beats one parked on top
    # of dialogue.
    runs, open_runs = [], {}  # open_runs: plain text -> (run, run's end time)
    for g in sorted(pinned, key=lambda g: g["start"]):
        run, run_end = open_runs.get(g["plain"], (None, None))
        if run and g["start"] <= run_end + FRAME_EPS:
            run.append(g)
            open_runs[g["plain"]] = (run, max(run_end, g["end"]))
        else:
            open_runs[g["plain"]] = ([g], g["end"])
            runs.append(open_runs[g["plain"]][0])

    burned = sorted(_burned_extents(raw_lines, res_y, style_map, style_fonts))
    on_screen = []  # burned/placed extents that may still overlap upcoming runs
    next_burned = 0
    assignment = {}
    for run in runs:
        start = run[0]["start"]
        end = max(g["end"] for g in run)
        # Sweep in start order: admit lines that start before the run ends,
        # retire lines that ended before it starts (later runs start later).
        while next_burned < len(burned) and burned[next_burned][0] < end - OVERLAP_EPS:
            on_screen.append(burned[next_burned])
            next_burned += 1
        on_screen = [ext for ext in on_screen if ext[1] > start + OVERLAP_EPS]

        def busy_during(s0, e0):
            return sorted((t, b) for s, e, t, b in on_screen
                          if s < e0 - OVERLAP_EPS and e > s0 + OVERLAP_EPS)

        h = max(g["nlines"] * g["line_h"] for g in run)
        y = _free_gap(busy_during(start, end), h, res_y)
        if len(run) == 1 or y is not None:
            placements = [(run, start, end, h, y)]
        else:
            placements = [([g], g["start"], g["end"], g["nlines"] * g["line_h"], None)
                          for g in run]
        for groups, s0, e0, gh, gy in placements:
            if gy is None:
                gy = _least_overlap(busy_during(s0, e0), gh, res_y)
            on_screen.append((s0, e0, gy, gy + gh))
            for g in groups:
                x = g["ox"] if g["ox"] is not None else res_x / 2
                for n in g["members"]:
                    assignment[n] = (x, gy)

    return assignment


def _free_gap(busy, h, res_y):
    """Top y of the first gap from STACK_TOP down that fits a block of height h
    between the (top, bottom) bands in `busy` (sorted by top), POS_GAP clear of
    each, or None if no gap is tall enough."""
    y = STACK_TOP
    for top, bottom in busy:
        if top < y + h + POS_GAP and bottom + POS_GAP > y:
            y = max(y, bottom + POS_GAP)
    return y if y + h <= res_y else None


def _least_overlap(busy, h, res_y):
    """For a block that fits no free gap — a big title card, a caption padded
    with blank \\N lines to space out a two-tier name card — the first-fit
    gap if there is one, else the on-screen spot covering the least of the
    busy bands."""
    y = _free_gap(busy, h, res_y)
    if y is not None:
        return y
    lowest = max(0, res_y - h)
    candidates = {min(c, lowest) for c in [STACK_TOP] + [b + POS_GAP for _t, b in busy]}
    return min(sorted(candidates), key=lambda c: sum(
        max(0, min(bottom, c + h) - max(top, c)) for top, bottom in busy))


def _max_concurrent(groups):
    """Most distinct caption placements on screen at the same instant (brief
    crossfades ignored). Counted by source position, not by text: the
    validator re-runs the planner with the ENGLISH text, and pieces of one
    caption ("Flying" / "Squirrel" masked by separate clips) can merge or split
    differently once translated — counting text groups made the two runs
    disagree about which screens are montages."""
    spans = {(g["start"], g["end"], g["place"]) for g in groups}
    events = sorted([(start + OVERLAP_EPS, 1) for start, _e, _p in spans]
                    + [(end, -1) for _s, end, _p in spans])
    best = cur = 0
    for _t, delta in events:
        cur += delta
        best = max(best, cur)
    return best


def _burned_extents(raw_lines, res_y, style_map, style_fonts):
    """(start, end, top, bottom) of every source line's English text, which the
    release burns into the video at its authored position."""
    extents = []
    for line in raw_lines:
        if not line.startswith("Dialogue:"):
            continue
        parts = line.split(",", 9)
        if len(parts) < 10 or not is_translatable(parts[3]) or is_drawing_only(parts[9]):
            continue
        ext = _text_extent(parts[9], parts[3], _float(parts[7]), res_y, style_map, style_fonts)
        if ext:
            extents.append((_parse_time(parts[1]), _parse_time(parts[2])) + ext)
    return extents


def expand_grouped_translations(members, translations):
    """Fan each translated representative out across its group's repeated frames.

    `extract` collapses runs of identical typeset frames (105 `Wano Arc` sign
    frames, ...) to one representative in the TSV, so the translator only
    renders the words once. Here we reconstruct the dropped frames: each member
    of a group keeps its OWN leading typeset block (its unique \\pos/\\fscx) and
    receives the representative's translated words. Taking the placement from
    the source frame — not from the representative's translation — means every
    frame lands where it was authored regardless of what tags the translation
    kept. Singleton groups (ordinary, non-repeated lines) are left untouched, so
    dialogue behaves exactly as before. Mutates and returns `translations`.
    """
    for rep_ln, group in members.items():
        if len(group) < 2 or rep_ln not in translations:
            continue
        translated_body = strip_leading_tags(translations[rep_ln])
        for member_ln, member_text in group:
            translations[member_ln] = leading_tags(member_text) + translated_body
    return translations


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
    style_fonts = _parse_style_fonts(raw_lines)
    top_pos = _plan_top_positions(raw_lines, translations, res_x, res_y, style_map)
    top_pos.update(_load_position_overrides(Path(original_path).name))
    margin_overrides = _load_margin_overrides(Path(original_path).name)
    pos_offsets = _plan_pos_offsets(raw_lines, translations, res_y, style_map,
                                    style_fonts, skip=top_pos)

    with open(output_path, "w", encoding=out_encoding) as fout:
        for line_num, line in enumerate(raw_lines, 1):
            if line_num in translations and line.startswith("Dialogue:"):
                parts = line.split(",", 9)
                if len(parts) >= 10:
                    style = parts[3]
                    text = translations[line_num]

                    if line_num in top_pos:
                        x, y = top_pos[line_num]
                        dy = _clip_dy(parts[9], text, style, _float(parts[7]), y,
                                      res_y, style_map, style_fonts)
                        text = _apply_top_pos(text, x, y, orig_text=parts[9], clip_dy=dy)
                    elif line_num in pos_offsets:
                        text = _apply_pos_offset(text, *pos_offsets[line_num])

                    # A \pos-pinned line ignores MarginV, so it keeps the source's.
                    if line_num not in pos_offsets and (
                            "\\an8" in text or style_matches(style, ("Narrator", "Note"))):
                        parts[7] = str(100 * (1 + text.count("\\N")))

                    if line_num in margin_overrides:
                        parts[7] = margin_overrides[line_num]

                    prefix = ",".join(parts[:9]) + ","
                    fout.write(prefix + text + "\n")
                    translated_count += 1
                    continue

            # Typeset drawings (\\p1 shapes: map outlines, colour boxes behind
            # signs) are already burned into the video UNDER the English text.
            # Drawing them again on top of the video hides that English, while
            # the Chinese that replaced it has moved elsewhere (Reverie 03
            # 23:20 map) — so blank them: keep the line and its tags (the
            # validator pairs lines one-to-one) but drop the shape itself.
            if line.startswith("Dialogue:"):
                parts = line.split(",", 9)
                if len(parts) >= 10 and is_translatable(parts[3]) and is_drawing_only(parts[9]):
                    line = ",".join(parts[:9]) + "," + _blank_drawing(parts[9])

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

    # Validate against the set of extractable lines. extract() collapses repeated
    # typeset frames to one representative per group, so the TSV the translator
    # worked from holds representatives only — validate LINE_NUMs against those.
    all_rows = extract(original_path)
    representatives, members = group_translatable(all_rows)
    all_nums = {ln for ln, style, text in all_rows}
    rep_nums = {ln for ln, style, text in representatives}
    translated_nums = set(translations.keys())

    # `extra` is still a hard error: a translated line whose LINE_NUM isn't a
    # translatable source line at all means a typo in the LINE_NUM column (or a
    # line number off-by-one from a chunked write). Checked against every
    # translatable line (not just representatives) so hand-picking a specific
    # frame's number isn't punished — only genuinely-bogus numbers are.
    extra = sorted(translated_nums - all_nums)
    if extra:
        print(f"ERROR: {len(extra)} translated lines reference line numbers not in the source: "
              f"{extra[:20]}{'...' if len(extra) > 20 else ''}", file=sys.stderr)
        print("These are likely typos in the LINE_NUM column. Fix them and re-run.", file=sys.stderr)
        sys.exit(1)

    # Fan translated representatives back out over their repeated frames before
    # merging, so every collapsed frame is restored with its own placement.
    expand_grouped_translations(members, translations)

    # `untranslated` is allowed: the agent may intentionally omit representatives
    # kept in the source language (decorative English signs, pure punctuation,
    # onomatopoeia, etc.). merge() leaves the original text in place for any line
    # not present in the TSV. Report the omitted REPRESENTATIVES so nothing is
    # dropped silently — scan this list to confirm every omission was deliberate.
    untranslated = sorted(rep_nums - translated_nums)
    count = merge(original_path, translations, output_path)

    print(f"Merged {count} translated lines into {output_path}")
    if untranslated:
        print(f"Kept {len(untranslated)} source representatives untranslated (originals preserved): "
              f"{untranslated[:20]}{'...' if len(untranslated) > 20 else ''}")


if __name__ == "__main__":
    main()
