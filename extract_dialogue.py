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

# Prefixes of styles whose text content should be translated.
# Style names vary between files (e.g. Main-207-, Main-480p) so we match by prefix.
TRANSLATABLE_PREFIXES = (
    "Main",
    "Secondary",
    "Note",
    "Captions",
    "Title",
    "Thoughts",
    "Flashbacks",
    "RogerMonologue",
    "Narrator",
)

# Prefixes of styles that must NOT be translated, even if they match above.
SKIP_PREFIXES = (
    "Credits",
)

# Pattern to match editor comments (non-formatting curly brace blocks)
# These are {text} blocks where the content does NOT start with \
# and is NOT just "Z" (which is a keep-marker)
# Examples: {So this is... - OG}, {Rin: blah}, {-san}, {MOVING SUBS?}
EDITOR_COMMENT_RE = re.compile(
    r'\{(?!'           # opening brace, not followed by:
    r'\\|'             #   backslash (ASS formatting tag)
    r'Z\}'             #   just "Z}" (end-of-line marker)
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
            if style.startswith(SKIP_PREFIXES) or not style.startswith(TRANSLATABLE_PREFIXES):
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
