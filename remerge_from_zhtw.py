#!/usr/bin/env python3
"""Re-run merge_translation on an already-translated zh-TW file.

Rebuilds the translation dict from the current zh-TW file (translated text is
kept; positioning is re-derived from the original by merge) and re-merges with
the current merge_translation.py logic. Used to re-apply positioning fixes to
files that were merged by an older version of the script.

Usage: python remerge_from_zhtw.py original.ass zhtw.ass [output.ass]
"""
import sys
from pathlib import Path
from extract_dialogue import extract
from merge_translation import merge


def build_translations(original_path, zhtw_path):
    nums = {ln for ln, _s, _t in extract(original_path)}
    with open(zhtw_path, "r", encoding="utf-8-sig") as f:
        zh = [l.rstrip("\n").rstrip("\r") for l in f]
    translations = {}
    for ln in nums:
        if ln - 1 < len(zh):
            line = zh[ln - 1]
            if line.startswith("Dialogue:"):
                parts = line.split(",", 9)
                if len(parts) >= 10:
                    translations[ln] = parts[9]
    return translations


def main():
    original, zhtw = Path(sys.argv[1]), Path(sys.argv[2])
    out = Path(sys.argv[3]) if len(sys.argv) >= 4 else zhtw
    translations = build_translations(original, zhtw)
    n = merge(original, translations, out)
    print(f"Re-merged {n} lines -> {out}")


if __name__ == "__main__":
    main()
