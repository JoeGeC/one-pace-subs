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

from extract_dialogue import extract, TRANSLATABLE_PREFIXES

# Styles whose translated text should be repositioned to the top of the screen.
# The originals use \pos() for precise placement over Japanese text on screen,
# but translations should sit at the top so they don't overlap the main dialogue.
TOP_POSITION_PREFIXES = ("Title", "Captions")

# Regex to strip \pos(...) tags from ASS override blocks
POS_TAG_RE = re.compile(r'\\pos\([^)]*\)')
# Regex to strip \an followed by a digit (existing alignment overrides)
AN_TAG_RE = re.compile(r'\\an\d')


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


def merge(original_path, translations, output_path):
    """Merge translations into the original ASS file.

    For each line number in the translations dict, replace the text field
    of the corresponding Dialogue line. All other lines are copied as-is.
    """
    translated_count = 0

    # Detect BOM in original file to preserve it in output
    with open(original_path, "rb") as fb:
        has_bom = fb.read(3) == b"\xef\xbb\xbf"

    out_encoding = "utf-8-sig" if has_bom else "utf-8"

    with open(original_path, "r", encoding="utf-8-sig") as fin, \
         open(output_path, "w", encoding=out_encoding) as fout:

        for line_num, line in enumerate(fin, 1):
            line = line.rstrip("\n").rstrip("\r")

            if line_num in translations and line.startswith("Dialogue:"):
                # Split into prefix (first 9 fields) + text
                parts = line.split(",", 9)
                if len(parts) >= 10:
                    style = parts[3]
                    text = translations[line_num]

                    # Reposition Title/Captions to top of screen
                    if style.startswith(TOP_POSITION_PREFIXES):
                        # For Captions, preserve original x and set y=100
                        # to avoid overlapping hardcoded Japanese text at the very top
                        orig_pos = POS_TAG_RE.search(text)
                        orig_x = float(orig_pos.group().split('(')[1].split(',')[0]) if orig_pos else 720

                        text = POS_TAG_RE.sub('', text)
                        text = AN_TAG_RE.sub('', text)

                        if style.startswith("Captions"):
                            x_str = f"{orig_x:.2f}".rstrip('0').rstrip('.')
                            pos_tag = f'\\an8\\pos({x_str},100)'
                        else:
                            pos_tag = '\\an8'

                        if text.startswith('{\\'):
                            text = '{' + pos_tag + text[1:]
                        else:
                            text = '{' + pos_tag + '}' + text

                    if '\\an8' in text or style.startswith("Narrator"):
                        parts[7] = '200' if '\\N' in text else '100'

                    prefix = ",".join(parts[:9]) + ","
                    fout.write(prefix + text + "\n")
                    translated_count += 1
                    continue

            # Adjust Narrator style MarginV to 100 so it clears hardcoded top text
            if line.startswith("Style: Narrator") and ",8," in line:
                line = re.sub(r',27,1$', ',100,1', line)

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

    # Validate: translated TSV must cover exactly the same lines as extraction
    expected = extract(original_path)
    expected_nums = {ln for ln, style, text in expected}
    translated_nums = set(translations.keys())

    missing = sorted(expected_nums - translated_nums)
    extra = sorted(translated_nums - expected_nums)

    if missing or extra:
        if missing:
            print(f"ERROR: {len(missing)} lines missing from translation: {missing[:20]}{'...' if len(missing) > 20 else ''}",
                  file=sys.stderr)
        if extra:
            print(f"ERROR: {len(extra)} extra lines in translation not in source: {extra[:20]}{'...' if len(extra) > 20 else ''}",
                  file=sys.stderr)
        print(f"Expected {len(expected_nums)} lines, got {len(translated_nums)}", file=sys.stderr)
        sys.exit(1)

    count = merge(original_path, translations, output_path)

    print(f"Merged {count} translated lines into {output_path}")


if __name__ == "__main__":
    main()
