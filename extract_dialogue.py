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
            results.append((line_num, style, cleaned))

    return results


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

    with open(output_path, "w", encoding="utf-8") as f:
        for line_num, style, text in results:
            f.write(f"{line_num}\t{style}\t{text}\n")

    print(f"Extracted {len(results)} translatable lines to {output_path}")


if __name__ == "__main__":
    main()
