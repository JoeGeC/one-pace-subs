#!/usr/bin/env python3
"""
Resolve English One Piece character/term names to their zh-TW Fandom wiki
titles in one deterministic pass, instead of an agent guessing candidate
Chinese transliterations turn-by-turn against the zh wiki's opensearch API.

Strategy per name:
1. Full-text search the ENGLISH wiki (onepiece.fandom.com) for the name —
   the English wiki is comprehensive even for one-episode characters, so
   this almost always finds the right page on the first try.
2. Read that page's interlanguage link to the zh wiki (prop=langlinks,
   lllang=zh) — this is the wiki's own authoritative English->zh mapping,
   no guessing required.
3. Only if no English page or no zh langlink exists, fall back to a single
   full-text search directly on the zh wiki (list=search, not opensearch,
   since opensearch is prefix-only and useless for an English query string).

Usage:
    python3 verify_names.py "Mother Carmel" "Giberson" "Peclo" ...
    python3 verify_names.py < names.txt   (one name per line)

Output (TSV to stdout): ENGLISH_NAME<TAB>ZH_TITLE_OR_NOT_FOUND<TAB>SOURCE_EN_PAGE_OR_BLANK
"""

import json
import subprocess
import sys
import time
import urllib.parse

EN_API = "https://onepiece.fandom.com/api.php"
ZH_API = "https://onepiece.fandom.com/zh/api.php"


def _get(api, params):
    # Shell out to curl rather than urllib — this machine's Python lacks a
    # configured cert bundle for urllib.request, but curl uses the system
    # store and works fine (confirmed against this same API elsewhere).
    url = f"{api}?{urllib.parse.urlencode(params)}"
    out = subprocess.run(
        ["curl", "-s", "--max-time", "15", url],
        capture_output=True, text=True, check=True,
    ).stdout
    return json.loads(out)


def search_en_title(name):
    data = _get(EN_API, {
        "action": "query", "list": "search", "srsearch": name,
        "srlimit": 1, "format": "json",
    })
    hits = data.get("query", {}).get("search", [])
    return hits[0]["title"] if hits else None


def zh_langlink(en_title):
    data = _get(EN_API, {
        "action": "query", "titles": en_title, "prop": "langlinks",
        "lllang": "zh", "format": "json",
    })
    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        for link in page.get("langlinks", []):
            return link.get("*")
    return None


def zh_fulltext_fallback(name):
    data = _get(ZH_API, {
        "action": "query", "list": "search", "srsearch": name,
        "srlimit": 1, "format": "json",
    })
    hits = data.get("query", {}).get("search", [])
    return hits[0]["title"] if hits else None


def resolve(name):
    try:
        en_title = search_en_title(name)
        if en_title:
            zh_title = zh_langlink(en_title)
            if zh_title:
                return name, zh_title, en_title
        zh_title = zh_fulltext_fallback(name)
        if zh_title:
            return name, zh_title, en_title or ""
        return name, "NOT_FOUND", en_title or ""
    except Exception as e:
        return name, f"ERROR: {e}", ""


def main():
    names = sys.argv[1:] or [line.strip() for line in sys.stdin if line.strip()]
    if not names:
        print(__doc__)
        sys.exit(1)
    for name in names:
        row = resolve(name)
        print("\t".join(row))
        time.sleep(0.2)  # be polite to the API


if __name__ == "__main__":
    main()
