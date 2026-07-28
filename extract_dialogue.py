#!/usr/bin/env python3
"""
Extract translatable dialogue from an ASS subtitle file.

Parses the ASS file, extracts only the text content of translatable lines,
strips editor comments and honorific blocks, and outputs a compact TSV file
that can be translated efficiently.

Usage:
    python extract_dialogue.py input.ass [output.tsv]

If output is omitted, it writes to <input_stem>_dialogue.tsv in the same directory.

Output format (TSV):
    LINE_NUM<tab>STYLE<tab>TEXT

The TEXT column contains only the translatable text with:
- Editor comments stripped ({... - OG}, {Rin: ...}, {Zenef: ...}, {-gab...}, etc.)
- Honorific blocks stripped ({-san}, {-chan}, {-kun}, {-sama})
- ASS formatting tags preserved ({\\i1}, {\\fad(...)}, etc.)
- {Z} markers preserved
"""

import re
import sys
from pathlib import Path

# Everything is translated EXCEPT opening/ending karaoke, credits, and pure
# typesetting FX — a BLACKLIST, not a whitelist. The old whitelist of known
# dialogue styles silently dropped every one-off style a new arc introduced
# (WCI alone shipped `Musical`, `Munch Chomp`, `Dried Up`, `Special-Captions`
# untranslated); defaulting to "translate" makes a miss visible instead.
#
# OP/ED style names change with nearly every opening across the series
# (`Karaoke-OP5`, `OP13-Kanji`, `English - OP18`, `We-Go-Karaoke`,
# `Wake up! lyrics`, ...), so they're matched as regex families against the
# lowercased style name. Case-insensitive for the same reason style_matches is.
NON_TRANSLATABLE_RES = tuple(re.compile(p) for p in (
    r"^credits",        # Team One Pace staff credits — kept in English
    r"^karaoke",        # frame-baked karaoke FX tracks (all OP/ED)
    r"^kanji",          # OP/ED karaoke stack: original script (+ -furigana)
    r"^romaji",         # OP/ED karaoke stack: romanisation
    r"^translation",    # OP/ED karaoke stack: English lyric translation
    r"^lyrics",         # Lyrics / Lyrics Main / Lyrics-OP5 / `lyrics english`
    r"lyrics$",         # per-song OP/ED tracks: `Jungle P lyrics`, `Wake up! lyrics`, ...
    r"^op\d{1,2}\b",    # OP11/OP13/OP20-* opening styles. 3+ digits is an anime
                        # EPISODE number (`OP_664_Signs` = in-episode signs): translatable.
    r"^english - op",   # `English - OP18` (Dressrosa/Zou opening)
    r"^we-go-",         # We-Go-Karaoke / We-Go-Translation (OP15)
    r"^we go roger",    # Roger monologue baked into the We Go! opening
    r"^sign-op$",       # Wano `One Piece` logo typeset in the opening
))

# Exact style names (lowercased) that match a family above but are diegetic
# in-episode content, not OP/ED — these MUST be translated.
TRANSLATABLE_EXCEPTIONS = {
    "binks' sake lyrics",  # Brook/crew singing in-episode (Thriller Bark)
    "karaokefade",         # one Dressrosa dialogue line with a fade FX name
}

# Letter/syllable-reveal typeset FX (exact lowercased names): each Dialogue
# line is a FRAGMENT of an attack name ("F", "Flame", "Ar", "mor", "ed"...)
# revealed per frame over the burned-in Japanese calligraphy. Substituting
# text fragment-by-fragment can't produce readable Chinese — recreating these
# needs per-character re-typesetting, and the spoken attack name is already
# translated in the accompanying Main dialogue line. Left in English.
TYPESET_FX_STYLES = {
    # Marineford attack-name reveals
    "ace", "moria", "borsalino", "hancock", "kuma", "kuzan", "sakazuki",
    "luffy", "luffy gear third",
    # Return to Sabaody "Armored Me!" reveal
    "armored me main",
}


def is_translatable(style):
    """True if this style's text content should be translated."""
    style_lower = style.strip().lower()
    if style_lower in TRANSLATABLE_EXCEPTIONS:
        return True
    if style_lower in TYPESET_FX_STYLES:
        return False
    return not any(p.search(style_lower) for p in NON_TRANSLATABLE_RES)


def style_matches(style, prefixes):
    """Case-insensitive prefix match for ASS style names.

    Source files are inconsistent about capitalisation (e.g. `Title` vs `title`,
    `Captions` vs `captions`), so we always compare lowercased. Matching by case
    silently dropped episode titles from translation/repositioning from Fishman
    Island ep 07 onward — keep this case-insensitive.
    """
    style_lower = style.lower()
    return any(style_lower.startswith(p.lower()) for p in prefixes)

# Pattern to match editor comments (non-formatting curly brace blocks)
# These are {text} blocks where the content does NOT start with \
# and is NOT just "Z" (which is a keep-marker)
# Examples: {So this is... - OG}, {Rin: blah}, {-san}, {MOVING SUBS?}
EDITOR_COMMENT_RE = re.compile(
    r'\{(?!'           # opening brace, not followed by:
    r'\\|'             #   backslash (ASS formatting tag)
    r'Z\}|'            #   just "Z}" (end-of-line marker)
    r'=\d'             #   "=NN" Aegisub-Motion frame marker (carries \pos etc.)
    r')[^}]*\}'        # any content until closing brace
)

# Pattern to detect lines that are pure vector drawings (no translatable text)
# These contain \p1 or \p4 drawing mode tags and consist mostly of coordinates
DRAWING_RE = re.compile(r'\\p[1-9]')

# Per-letter typeset-reveal animation tags. A caption/sign/title drawn as a
# per-letter reveal interleaves one of these override blocks with (almost)
# every character — \alpha / numbered alpha (\1a..\4a) for fade-in reveals,
# \fax/\fay shear-kerning, \frz/\frx/\fry rotation arcs. Emphasis tags (\i, \b)
# are deliberately excluded so ordinary dialogue with a little italic/bold, or
# stammered lines split by \i, are never mistaken for typeset.
PER_LETTER_TAG_RE = re.compile(r'\\(?:alpha|[1-4]a(?=[&\\}])|fa[xy]|fr[xyz])')
ANY_TAG_BLOCK_RE = re.compile(r'\{[^}]*\}')


def is_drawing_only(text):
    """Check if a line is a pure vector drawing with no translatable text.

    Drawing lines contain \\p1 (or similar) and their visible content is just
    coordinate data (m, l, b commands with numbers). We detect these by checking
    if there's any readable text outside of ASS tags.
    """
    if not DRAWING_RE.search(text):
        return False
    # Strip all {...} blocks, then check if remaining content is just drawing commands
    stripped = re.sub(r'\{[^}]*\}', '', text)
    # Drawing commands are: m/l/b/s/c followed by numbers and spaces
    stripped = re.sub(r'[mlbsc]\s+[\d.\s-]+', '', stripped).strip()
    return len(stripped) == 0


def is_per_letter_reveal(text):
    """True if the line is a per-letter/per-fragment typeset reveal animation.

    Location name-cards and decorative signs are often drawn as a reveal where
    each character carries its own animation override
    (`T{\\fax}r{\\fax}e...`, `P{\\alpha}r{\\alpha}i...`, curved `\\frz` arcs).
    These can't be recreated char-for-char in Chinese: collapsing them to a
    block drops the interior tags (TAG MISMATCH) and, for \\alpha reveals, pins
    the whole caption at the first fragment's alpha — usually fully transparent,
    so it renders invisible. Like OP/ED karaoke and Sign-Treasure kerning, they
    are left as the source animation (the concept is conveyed by dialogue/other
    captions).

    Detected by counting interior override blocks (those after the single
    leading placement block) that carry a per-letter animation tag; three or
    more means a reveal. Emphasis-only interior tags (\\i/\\b) don't count, so
    ordinary dialogue — including stammers split by italics — is never flagged.
    """
    m = re.match(r'^(?:\{[^}]*\})+', text)
    body = text[m.end():] if m else text
    n = sum(1 for b in ANY_TAG_BLOCK_RE.findall(body) if PER_LETTER_TAG_RE.search(b))
    return n >= 3


def parse_ass_line(line):
    """Parse an ASS Dialogue line into its components.

    Returns (prefix, style, text) where prefix is everything before the text field,
    or None if the line is not a Dialogue line.
    """
    if not line.startswith("Dialogue:"):
        return None

    # ASS format: Dialogue: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
    # Split on comma, but only the first 9 commas — the rest is the Text field
    parts = line.split(",", 9)
    if len(parts) < 10:
        return None

    style = parts[3]
    text = parts[9]
    prefix = ",".join(parts[:9]) + ","
    return prefix, style, text


def strip_editor_comments(text):
    """Remove editor comments and honorific blocks from dialogue text,
    preserving ASS formatting tags and {Z} markers."""
    return EDITOR_COMMENT_RE.sub("", text)


def extract(input_path):
    """Extract translatable dialogue from an ASS file.

    Returns a list of (line_number, style, cleaned_text) tuples.
    Line numbers are 1-based to match the source file.
    """
    results = []
    with open(input_path, "r", encoding="utf-8-sig") as f:
        for line_num, line in enumerate(f, 1):
            line = line.rstrip("\n").rstrip("\r")
            parsed = parse_ass_line(line)
            if parsed is None:
                continue

            prefix, style, text = parsed
            if not is_translatable(style):
                continue

            # Skip pure vector drawing lines (no translatable text)
            if is_drawing_only(text):
                continue

            cleaned = strip_editor_comments(text)

            # Skip per-letter typeset reveals — kept as the source animation
            # (see is_per_letter_reveal). Checked on the comment-stripped text
            # so editor notes can't inflate the interior-tag count.
            if is_per_letter_reveal(cleaned):
                continue

            results.append((line_num, style, cleaned))

    return results


# A line's "visible text" is its translatable surface with every {...} override
# and comment block removed — used to detect typeset animation frames that
# repeat the same words. Leading-tag helpers isolate the per-frame typesetting
# block (\pos/\fscx/...) so a single translation can be fanned back out over
# every frame while each keeps its own placement.
TAG_BLOCK_RE = re.compile(r'\{[^}]*\}')
LEADING_TAGS_RE = re.compile(r'^(?:\{[^}]*\})+')


def visible_text(text):
    """Translatable surface of a line: all {...} blocks removed, ends trimmed."""
    return TAG_BLOCK_RE.sub("", text).strip()


def leading_tags(text):
    """The contiguous run of {...} override blocks at the very start of text
    (the per-frame typesetting), or '' if the text doesn't start with one."""
    m = LEADING_TAGS_RE.match(text)
    return m.group(0) if m else ""


def strip_leading_tags(text):
    """text with its single leading run of {...} blocks removed."""
    return LEADING_TAGS_RE.sub("", text, count=1)


def group_translatable(rows):
    """Collapse extract() rows that repeat the same words in the same style.

    Typeset sign/caption animation tracks emit the SAME text once per frame
    (e.g. 105 `Wano Arc` frames, 188 per-letter `Treasure` frames), each frame
    differing only in per-frame \\pos/\\fscx typesetting. Translating every
    frame is wasted work, so we group by (style, visible_text) and expose one
    representative per group — the lowest-line-num member.

    Returns (representatives, members):
      representatives: [(line_num, style, text)] — one per group, in line order.
      members:         {rep_line_num: [(line_num, text), ...]} — every member of
                       the group (including the representative), in line order,
                       carrying the cleaned text so a caller can read each
                       frame's own leading typeset block.

    Frames are grouped only when they are byte-identical AFTER their leading
    typeset block is removed — i.e. they repeat the same words AND the same
    interior tags, differing solely in per-frame placement. A frame that also
    varies mid-text (e.g. an animated \\bord on a second line of a caption)
    therefore stays in its own group, so its per-frame animation is never
    flattened. This is what makes the fan-out exact: every member shares the
    identical post-leading content the representative's translation replaces.

    Lines with unique content form singleton groups, so a caller that
    translates the representatives and fans results back over `members`
    reproduces exactly today's behaviour for non-repeated content. Lines whose
    visible text is empty (tags only) are never grouped — each stays its own
    singleton so an empty surface can't sweep unrelated lines together.
    """
    rep_for_key = {}
    members = {}
    representatives = []
    for ln, style, text in rows:
        # Discriminate on the text minus its leading placement block, so only
        # per-frame \pos/\fscx differences are collapsed — not interior tag
        # animation. Guard on visible_text so tag-only lines never group.
        key = (style.strip().lower(), strip_leading_tags(text)) if visible_text(text) else ("", ln)
        rep = rep_for_key.get(key)
        if rep is None:
            rep_for_key[key] = ln
            members[ln] = []
            representatives.append((ln, style, text))
            rep = ln
        members[rep].append((ln, text))
    return representatives, members


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} input.ass [output.tsv]", file=sys.stderr)
        sys.exit(1)

    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f"Error: {input_path} not found", file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) >= 3:
        output_path = Path(sys.argv[2])
    else:
        output_path = input_path.with_name(input_path.stem + "_dialogue.tsv")

    results = extract(input_path)
    representatives, members = group_translatable(results)

    with open(output_path, "w", encoding="utf-8") as f:
        for line_num, style, text in representatives:
            f.write(f"{line_num}\t{style}\t{text}\n")

    collapsed = len(results) - len(representatives)
    msg = f"Extracted {len(representatives)} translatable lines to {output_path}"
    if collapsed:
        msg += f" (collapsed {collapsed} repeated typeset frames into their representatives)"
    print(msg)


if __name__ == "__main__":
    main()
