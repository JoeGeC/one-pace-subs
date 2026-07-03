#!/usr/bin/env python3
"""
Validate a translated ASS subtitle file against its original source.

Compares every Dialogue line's metadata (timing, style, layer, margins) between
original and translated files. Checks Title/Captions repositioning. Optionally
applies fixes for repositioning issues.

Usage:
    python validate_translation.py original.ass translated.ass [--fix]

Without --fix, reports issues only. With --fix, applies repositioning fixes
and rewrites the translated file.

Exit codes:
    0 = all checks pass (or all issues fixed with --fix)
    1 = issues found (without --fix) or unfixable issues found
"""

import re
import sys
from pathlib import Path

from extract_dialogue import (
    parse_ass_line, TRANSLATABLE_PREFIXES, SKIP_PREFIXES,
    EDITOR_COMMENT_RE, is_drawing_only, style_matches
)

# Matched case-insensitively via style_matches — source files ship the same
# styles under different capitalisation (`Title`/`title`, `Captions`/`captions`).
TOP_POSITION_PREFIXES = ("Title", "Captions")
BOTTOM_POSITION_PREFIXES = ("Main", "Secondary", "Note", "Thoughts", "Flashback", "RogerMonologue", "Gold")
POS_TAG_RE = re.compile(r'\\pos\([^)]*\)')
AN_TAG_RE = re.compile(r'\\an\d')
# \move is stripped by merge when pinning a caption to the top of the screen,
# so it must not count as a tag difference (mirrors merge_translation.py).
MOVE_TAG_RE = re.compile(r'\\move\([^)]*\)')

# Extract ASS formatting tag blocks: {\...} where content starts with backslash
ASS_TAG_RE = re.compile(r'\{\\[^}]*\}')


def parse_ass_time(timestr):
    """Parse ASS timestamp H:MM:SS.CC to centiseconds."""
    timestr = timestr.strip()
    h, m, rest = timestr.split(":")
    s, cs = rest.split(".")
    return int(h) * 360000 + int(m) * 6000 + int(s) * 100 + int(cs)


def detect_overlaps(dialogue_lines):
    """Detect timing overlaps between subtitles sharing the same screen position.

    Groups styles into bottom-positioned and top-positioned, then checks for
    temporal overlaps within each group. Returns list of overlap descriptions.

    Skips pairs with identical start+end times (visual effect layers like
    stacked Captions at layers 0/1/2).
    """
    overlaps = []

    bottom_lines = []
    top_lines = []

    for ln, layer, start, end, style, name, ml, mr, mv, effect, text in dialogue_lines:
        if style_matches(style, BOTTOM_POSITION_PREFIXES) and not style_matches(style, SKIP_PREFIXES):
            bottom_lines.append((ln, layer, start, end, style))
        elif style_matches(style, TOP_POSITION_PREFIXES) and not style_matches(style, SKIP_PREFIXES):
            top_lines.append((ln, layer, start, end, style))

    for group_name, lines in [("bottom", bottom_lines), ("top", top_lines)]:
        sorted_lines = sorted(lines, key=lambda x: parse_ass_time(x[2]))

        for i in range(len(sorted_lines)):
            ln_a, layer_a, start_a, end_a, style_a = sorted_lines[i]
            end_a_cs = parse_ass_time(end_a)

            for j in range(i + 1, len(sorted_lines)):
                ln_b, layer_b, start_b, end_b, style_b = sorted_lines[j]
                start_b_cs = parse_ass_time(start_b)

                if start_b_cs >= end_a_cs:
                    break

                # Skip effect layers with identical timing
                if start_a == start_b and end_a == end_b:
                    continue

                overlaps.append(
                    f"OVERLAP ({group_name}): lines {ln_a} ({style_a} {start_a}-{end_a}) "
                    f"and {ln_b} ({style_b} {start_b}-{end_b})"
                )

    return overlaps


def extract_format_tags(text):
    """Extract list of ASS formatting tag blocks from text.

    Returns only {\\...} blocks (real formatting), not editor comments or {Z}.
    Normalizes tags so equivalent forms compare equal:
      - Strips \\pos() and \\an (changed by repositioning)
      - Normalizes \\i -> \\i0, \\b -> \\b0 (shorthand equivalents)
    """
    tags = ASS_TAG_RE.findall(text)
    normalized = []
    for tag in tags:
        t = POS_TAG_RE.sub('', tag)
        t = MOVE_TAG_RE.sub('', t)
        t = AN_TAG_RE.sub('', t)
        # Normalize shorthand toggle tags: \i} -> \i0}, \b} -> \b0}
        t = re.sub(r'\\([ib])([\\}])', r'\\\g<1>0\2', t)
        # Remove empty tag blocks left after stripping
        if t != '{}' and t != '{\\}':
            normalized.append(t)
    return normalized


def parse_all_dialogue(path):
    """Parse all Dialogue lines from an ASS file.

    Returns list of (line_num, layer, start, end, style, name, ml, mr, mv, effect, text).
    """
    results = []
    with open(path, "r", encoding="utf-8-sig") as f:
        for line_num, line in enumerate(f, 1):
            line = line.rstrip("\n").rstrip("\r")
            if not line.startswith("Dialogue:"):
                continue
            parts = line.split(",", 9)
            if len(parts) < 10:
                continue
            # parts[0] = "Dialogue: <layer>"
            layer = parts[0].split(":", 1)[1].strip()
            start, end, style = parts[1], parts[2], parts[3]
            name, ml, mr, mv, effect = parts[4], parts[5], parts[6], parts[7], parts[8]
            text = parts[9]
            results.append((line_num, layer, start, end, style, name, ml, mr, mv, effect, text))
    return results


def reposition_text(text):
    """Apply \an8 repositioning to a Title/Captions text field."""
    text = POS_TAG_RE.sub('', text)
    text = MOVE_TAG_RE.sub('', text)
    text = AN_TAG_RE.sub('', text)
    if text.startswith('{\\'):
        text = '{\\an8' + text[1:]
    else:
        text = '{\\an8}' + text
    return text


def validate(original_path, translated_path, fix=False):
    """Validate translated ASS against original. Returns (report, issues_found, fixes_applied)."""
    orig_lines = parse_all_dialogue(original_path)
    trans_lines = parse_all_dialogue(translated_path)

    report = []
    issues = []
    fixes = []  # (line_num, fixed_full_line) for rewriting

    # Check line count
    if len(orig_lines) != len(trans_lines):
        issues.append(f"LINE COUNT MISMATCH: original has {len(orig_lines)} dialogue lines, translated has {len(trans_lines)}")

    # Compare line by line
    metadata_ok = 0
    metadata_fail = 0
    tag_ok = 0
    tag_mismatch = 0
    reposition_ok = 0
    reposition_needed = 0
    reposition_fixed = 0

    for i, (orig, trans) in enumerate(zip(orig_lines, trans_lines)):
        o_ln, o_layer, o_start, o_end, o_style, o_name, o_ml, o_mr, o_mv, o_effect, o_text = orig
        t_ln, t_layer, t_start, t_end, t_style, t_name, t_ml, t_mr, t_mv, t_effect, t_text = trans

        # Check metadata match
        meta_issues = []
        if o_ln != t_ln:
            meta_issues.append(f"line number: orig={o_ln} trans={t_ln}")
        if o_start != t_start:
            meta_issues.append(f"start: {o_start} vs {t_start}")
        if o_end != t_end:
            meta_issues.append(f"end: {o_end} vs {t_end}")
        if o_style != t_style:
            meta_issues.append(f"style: {o_style} vs {t_style}")
        if o_layer != t_layer:
            meta_issues.append(f"layer: {o_layer} vs {t_layer}")
        has_an8_margin = ('\\an8' in t_text or style_matches(t_style, ("Narrator", "Note"))) and t_mv in ('100', '200')
        if o_ml != t_ml or o_mr != t_mr or (o_mv != t_mv and not has_an8_margin):
            meta_issues.append(f"margins: {o_ml},{o_mr},{o_mv} vs {t_ml},{t_mr},{t_mv}")

        if meta_issues:
            metadata_fail += 1
            issues.append(f"Line {t_ln} (orig {o_ln}): {'; '.join(meta_issues)}")
        else:
            metadata_ok += 1

        # Check formatting tag consistency (detects shifted translations)
        # Only check translatable lines — non-translatable lines are copied verbatim
        is_translatable = style_matches(t_style, TRANSLATABLE_PREFIXES) and not style_matches(t_style, SKIP_PREFIXES)
        if is_translatable and not is_drawing_only(o_text):
            o_tags = extract_format_tags(o_text)
            t_tags = extract_format_tags(t_text)
            if o_tags != t_tags:
                tag_mismatch += 1
                # Show first differing tag for context
                orig_preview = o_text[:60].replace('\n', '\\n')
                trans_preview = t_text[:60].replace('\n', '\\n')
                issues.append(
                    f"TAG MISMATCH line {t_ln} ({t_style}): "
                    f"formatting tags differ — possible shifted translation\n"
                    f"    orig:  {orig_preview}\n"
                    f"    trans: {trans_preview}"
                )
            else:
                tag_ok += 1

        # Check Title/Captions repositioning (only on translatable lines)
        if is_translatable and style_matches(t_style, TOP_POSITION_PREFIXES):
            has_an8 = bool(re.search(r'\\an8', t_text))
            has_pos = bool(POS_TAG_RE.search(t_text))

            # A repositioned caption is one that has been pulled to the top with
            # \an8. It may ALSO carry \pos(x,y): merge_translation.py pins
            # coincident top lines to explicit stacked positions so they don't
            # overlap each other. \an8\pos is therefore valid — do NOT strip it.
            o_pos_m = POS_TAG_RE.search(o_text)
            t_pos_m = POS_TAG_RE.search(t_text)
            kept_in_place = (not has_an8 and o_pos_m and t_pos_m
                             and o_pos_m.group(0) == t_pos_m.group(0))
            if has_an8:
                reposition_ok += 1
            elif kept_in_place:
                # Deliberately unpinned: merge keeps original \pos for montage
                # clusters (> MAX_PINNED_CLUSTER simultaneous captions).
                reposition_ok += 1
            else:
                reposition_needed += 1
                if fix:
                    fixed_text = reposition_text(t_text)
                    fixed_mv = '200' if '\\N' in fixed_text else '100'
                    prefix = f"Dialogue: {t_layer},{t_start},{t_end},{t_style},{t_name},{t_ml},{t_mr},{fixed_mv},{t_effect},"
                    fixes.append((t_ln, prefix + fixed_text))
                    reposition_fixed += 1
                else:
                    issues.append(f"Line {t_ln} ({t_style}): needs \\an8 repositioning (has_an8={has_an8}, has_pos={has_pos})")

    # Check for timing overlaps within same screen position
    overlap_warnings = detect_overlaps(trans_lines)

    # Build report
    total = min(len(orig_lines), len(trans_lines))
    report.append(f"VALIDATION REPORT")
    report.append(f"Original:   {original_path}")
    report.append(f"Translated: {translated_path}")
    report.append(f"")
    report.append(f"Dialogue lines: original={len(orig_lines)} translated={len(trans_lines)}")
    report.append(f"Metadata check: {metadata_ok} OK, {metadata_fail} FAILED")
    report.append(f"Tag check:      {tag_ok} OK, {tag_mismatch} MISMATCHED")
    report.append(f"Repositioning:  {reposition_ok} OK, {reposition_needed} need fixing")
    report.append(f"Overlaps:       {len(overlap_warnings)} warnings")

    if fix and reposition_fixed:
        report.append(f"Repositioning fixes applied: {reposition_fixed}")

    if issues:
        report.append(f"")
        report.append(f"ISSUES ({len(issues)}):")
        for issue in issues[:50]:
            report.append(f"  - {issue}")
        if len(issues) > 50:
            report.append(f"  ... and {len(issues) - 50} more")

    if overlap_warnings:
        report.append(f"")
        report.append(f"OVERLAP WARNINGS ({len(overlap_warnings)}):")
        for warning in overlap_warnings[:20]:
            report.append(f"  - {warning}")
        if len(overlap_warnings) > 20:
            report.append(f"  ... and {len(overlap_warnings) - 20} more")

    if not issues or (fix and metadata_fail == 0):
        report.append(f"")
        report.append(f"RESULT: PASS")
    else:
        report.append(f"")
        report.append(f"RESULT: FAIL")

    return report, issues, fixes


def apply_fixes(translated_path, fixes):
    """Rewrite specific lines in the translated file."""
    fix_map = {ln: line for ln, line in fixes}

    with open(translated_path, "rb") as fb:
        has_bom = fb.read(3) == b"\xef\xbb\xbf"

    out_encoding = "utf-8-sig" if has_bom else "utf-8"

    lines = []
    with open(translated_path, "r", encoding="utf-8-sig") as f:
        for line_num, line in enumerate(f, 1):
            line = line.rstrip("\n").rstrip("\r")
            if line_num in fix_map:
                lines.append(fix_map[line_num])
            else:
                lines.append(line)

    with open(translated_path, "w", encoding=out_encoding) as f:
        for line in lines:
            f.write(line + "\n")


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} original.ass translated.ass [--fix]", file=sys.stderr)
        sys.exit(1)

    original_path = Path(sys.argv[1])
    translated_path = Path(sys.argv[2])
    fix = "--fix" in sys.argv

    if not original_path.exists():
        print(f"Error: {original_path} not found", file=sys.stderr)
        sys.exit(1)
    if not translated_path.exists():
        print(f"Error: {translated_path} not found", file=sys.stderr)
        sys.exit(1)

    report, issues, fixes = validate(original_path, translated_path, fix=fix)

    for line in report:
        print(line)

    if fix and fixes:
        apply_fixes(translated_path, fixes)
        print(f"\nApplied {len(fixes)} fixes to {translated_path}")

    # Exit 1 if unfixable issues remain
    has_unfixable = any(not issue.startswith("Line") or "repositioning" not in issue for issue in issues)
    if issues and (not fix or has_unfixable):
        sys.exit(1)


if __name__ == "__main__":
    main()
