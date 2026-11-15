#!/usr/bin/env python3
"""Build an English .ass source from a video with hardcoded (burned-in) subtitles.

    python3 ocr_hardsubs.py VIDEO.mp4 OUTPUT.ass [--template SRC.ass] [--scan-json X.jsonl] [--review-dir DIR]

Pipeline:
  1. hardsub_scan (Swift/Vision, compiled on demand into ~/Library/Caches/one-pace-subs)
     decodes every frame once, detects bottom-subtitle changes frame-exactly and
     OCRs only a couple of frames per subtitle, plus a 0.5s caption scan of the
     rest of the frame.
  2. The opening is found from its karaoke romaji (a long, dense run of text at
     the top of the frame) and everything inside it is dropped — song lyrics and
     the anime's own Japanese staff credits are not translated.
  3. Segments are cleaned (fade/flicker merges, junk filter, known OCR typo fixes),
     spell-checked against the system dictionary + every English source already in
     the repo, and written as Main-207+ lines; mid/top text becomes Captions-207+.
  4. Anything uncertain is listed in REVIEW.txt with a numbered contact sheet
     (review_*.png) showing the actual frame crop beside the OCR text.

After reviewing/fixing the flagged lines, continue with the normal
extract_dialogue.py -> translate -> merge_translation.py -> validate_translation.py flow.
Limitations: italics are not detected (all dialogue is Main-207+); caption timing
is only accurate to ~0.5s.
"""
import argparse
import collections
import difflib
import glob
import json
import math
import os
import re
import subprocess
import sys
import unicodedata

ROOT = os.path.dirname(os.path.abspath(__file__))
SWIFT_SRC = os.path.join(ROOT, "hardsub_scan.swift")
BIN = os.path.expanduser("~/Library/Caches/one-pace-subs/hardsub_scan")
DEFAULT_TEMPLATE = os.path.join(ROOT, "32 Wano", "[One Pace][1012-1013] Wano 62 [1080p] Extended.ass")

# Known Vision misreads of this subtitle font (applied word-wise / to whole lines).
TYPO_FIXES = [
    (r"\bl'm\b", "I'm"), (r"\bl'll\b", "I'll"), (r"\bl've\b", "I've"), (r"\bl'd\b", "I'd"),
    (r"\bfll\b", "I'll"), (r"\bIl\b", "I'll"), (r"^lam\b", "I am"), (r"(?<=[.!?] )lam\b", "I am"),
    (r"\b(T|t)heyre\b", r"\1hey're"), (r"\b(Y|y)oure\b", r"\1ou're"), (r"\b(Y|y)oull\b", r"\1ou'll"),
    (r"\b(W|w)ere gonna\b", r"\1e're gonna"), (r"\b(I|i)ts a\b", r"\1t's a"),
    (r"\b(I|i)f's\b", r"\1t's"), (r"\b(W|w)elve\b", r"\1e've"),
    (r"[®©•·]", ""),                                           # stray symbols
    (r"\.+o\.*$", "..."), (r"\.{2,}o\b", "..."),                  # "…" read as ".o" / "..o"
    (r"^[o•·]?\.{2,}(?=\w)", "..."), (r"^o\.\.(?=\w)", "..."),     # leading "o..our" -> "...our"
    (r"(?<!\.)\.\.(?!\.)", "..."),                                # two dots -> ellipsis
    (r"\.{4,}", "..."),
    (r"^L, ", "I, "), (r"'S\b", "'s"), (r"^\\(?=\w)", ""),
    (r"^(co|bo|oo|o)\.\s+(?=[a-z])", "..."),                     # "co. would" -> "...would"
    (r"^(poo|ooo|oo|co)\s+(?=[a-z]{3})", "..."), (r"^oo (?=[A-Z])", "..."),  # "poo work", "oo Suplex"
    (r"^[B-HJ-Z] (?=[a-z])", ""),                               # stray capital before a lowercase line
    (r"^1 (?=[a-z])", "I "), (r"(?<=[\s,.!?])[l1] (?=(am|have|was|had|can|will|think|guess|know|pity)\b)", "I "),
    (r"(?<= )i(?= )", "I"), (r"^i(?= )", "I"), (r"\bMl\b", "I'll"), (r"\b([a-z]{2,})W\b", lambda m: m.group(1) + "w"),
    (r"^'(?=[A-Z][a-z])", ""),                                  # stray leading apostrophe
    (r"(?:(?<=^)|(?<=[\s\"]))l(?=(ain't|'m|'ll|'ve|'d)\b)", "I "),  # "lain't" -> "I ain't"
    (r"\b([a-z]{3,})([A-Z])\b", lambda m: m.group(1) + m.group(2).lower()),   # "monsterS" -> "monsters"
    (r"\b([A-Z][a-z']+) (sama|san|chan|kun|dono)\b", r"\1-\2"),  # lost honorific hyphen
    (r"(\w)!!$", r"\1!"),
    (r"(\w)l$", r"\1!"),                                       # trailing "!" read as "l" (only if word unknown; see below)
    (r"[‹›«»|]+$", ""), (r"^[‹›«»|]+", ""),
]
LETTER_L_FIX = re.compile(r"(\w)l$")


def log(*a):
    print(*a, file=sys.stderr)


def ensure_binary():
    if not os.path.exists(BIN) or os.path.getmtime(BIN) < os.path.getmtime(SWIFT_SRC):
        os.makedirs(os.path.dirname(BIN), exist_ok=True)
        log("Compiling hardsub_scan…")
        subprocess.run(["swiftc", "-O", SWIFT_SRC, "-o", BIN], check=True)


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def sim(a, b):
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def obs_to_text(obs, min_conf=0.5):
    """Join OCR boxes into lines (top to bottom), '\\N' between lines."""
    obs = [o for o in obs if o["c"] >= min_conf and o["t"].strip()]
    obs.sort(key=lambda o: (-(o["y"] + o["h"] / 2), o["x"]))
    lines = []
    for o in obs:
        cy = o["y"] + o["h"] / 2
        if lines and abs(lines[-1][0] - cy) < o["h"] * 0.6:
            lines[-1][1].append(o)
        else:
            lines.append([cy, [o]])
    out = []
    for _, os_ in lines:
        os_.sort(key=lambda o: o["x"])
        out.append(" ".join(o["t"].strip() for o in os_))
    conf = min((o["c"] for o in obs), default=0)
    return "\\N".join(out), conf


def plausible(text):
    flat = text.replace("\\N", " ")
    letters = sum(c.isalpha() for c in flat)
    if letters < 2:
        return False
    body = re.sub(r"[\s.,!?'\"…—\-]", "", flat)   # ellipses/punctuation don't count against a line
    if letters / max(1, len(body)) < 0.6:
        return False
    return bool(re.search(r"[aeiouyAEIOUY]", flat))


def clean_tokens(text):
    lines = []
    for ln in text.split("\\N"):
        toks = [w for w in ln.split() if re.search(r"[A-Za-z]", w) or re.fullmatch(r"[-.!?…\"'—]+", w)
                or re.fullmatch(r"\d{1,3}(,\d{3})*([.,!?]+)?|\d+%?[.,!?]*", w)]   # keep numbers like 4,000 / 30%
        if toks:
            lines.append(" ".join(toks))
    return "\\N".join(lines)


SUB_WORDS = set()   # words seen in real (non-OCR) subtitle scripts — stricter than the dictionary


def load_vocab():
    words = set()
    for p in ("/usr/share/dict/words",):
        if os.path.exists(p):
            words |= {w.strip().lower() for w in open(p, encoding="utf-8", errors="ignore")}
    for p in glob.glob(os.path.join(ROOT, "*", "*.ass")):
        if "zh-TW" in p:
            continue
        try:
            with open(p, encoding="utf-8-sig", errors="ignore") as fh:
                if "{Source: OCR" in fh.read(20000):
                    continue   # OCR-built sources may contain misreads; don't learn words from them
            for line in open(p, encoding="utf-8-sig", errors="ignore"):
                if line.startswith("Dialogue:"):
                    txt = re.sub(r"\{[^}]*\}", "", line.split(",", 9)[-1])
                    ws = {w.lower().strip("'’-") for w in re.findall(r"[A-Za-z][A-Za-z'’-]*", txt)}
                    words |= ws
                    SUB_WORDS.update(ws)
        except OSError:
            pass
    return words


def known(word, vocab, _depth=0):
    w = word.lower().strip("'’-").replace("’", "'")
    if not w or w in vocab:
        return True
    if _depth == 0:
        # deliberately stretched shouts: "loooost", "samuraaaai", "c'moooon"
        for squeezed in (re.sub(r"(.)\1{2,}", r"\1", w), re.sub(r"(.)\1{2,}", r"\1\1", w), re.sub(r"(.)\1+", r"\1", w)):
            if squeezed != w and known(squeezed, vocab, 1):
                return True
    if re.fullmatch(r"\w+(.)\1(ing|ed|er|est)", w) and w[:-len(re.search(r"(ing|ed|er|est)$", w).group())-1] in vocab:
        return True
    for suf in ("'s", "s", "es", "ed", "d", "ing", "'ll", "'re", "'ve", "'d", "n't", "ly", "er", "est"):
        if w.endswith(suf) and w[: -len(suf)] in vocab:
            return True
    if "-" in w:
        return all(known(p, vocab, _depth) for p in w.split("-") if p)
    return False


LEAD_JUNK = ("ooo", "coo", "oo", "cod", "co", "o", "c")
INTERJECTIONS = {"oof", "ooh", "oops", "oho", "ohh", "oi", "oy", "ow", "ouch", "oooh", "ooo", "oh", "ohoho", "coo"}


def fix_ellipsis_artifacts(ln, vocab):
    """'...' at line start/end is often read as 'ooo'/'co'/'o'; '!' after a word as 'l'."""
    words = ln.split(" ")
    if words and words[0]:
        w0 = re.sub(r"[^A-Za-z']", "", words[0])
        if w0 and w0.lower() not in SUB_WORDS and w0.lower() not in INTERJECTIONS:
            for j in LEAD_JUNK:
                if w0.lower().startswith(j) and len(w0) - len(j) >= 2 and w0[len(j):].lower() in SUB_WORDS:
                    words[0] = "..." + words[0][words[0].lower().index(j) + len(j):]
                    break
    for k, w in enumerate(words):
        m = re.fullmatch(r"(\.*)([A-Za-z']+?)(o{1,3})(\.*)", w)            # "amoo" -> "am..."
        if m and not known(m.group(2) + m.group(3), vocab) and known(m.group(2), vocab) and len(m.group(2)) > 1:
            words[k] = m.group(1) + m.group(2) + "..."
            continue
        m = re.fullmatch(r"(\.*)([A-Za-z']+)l([!?.]*)", w)                  # "Zorol!" -> "Zoro!", "piratel" -> "pirate!"
        if m and not known(m.group(2) + "l", vocab) and known(m.group(2), vocab):
            words[k] = m.group(1) + m.group(2) + (m.group(3) or "!")
    return " ".join(words)


def fix_typos(text, vocab):
    out = []
    text = text.replace("™", "").replace("®", "").replace("©", "")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    for ln in text.split("\\N"):
        ln = fix_ellipsis_artifacts(ln, vocab)
        for pat, rep in TYPO_FIXES:
            if pat == LETTER_L_FIX.pattern:
                continue
            ln = re.sub(pat, rep, ln)
        out.append(ln.strip())
    return "\\N".join(out)


def unknown_words(text, vocab):
    flat = text.replace("\\N", " ")
    return [w for w in re.findall(r"[A-Za-z][A-Za-z'’-]*", flat) if not known(w, vocab)]


def find_op_window(scans, fr):
    """Opening = longest run of caption-scan samples with text at the very top, gaps <= 6s, length >= 40s."""
    tops = sorted(s["f"] for s in scans
                  if any(o["c"] >= 0.5 and o["y"] + o["h"] / 2 > 0.86 for o in s["o"]))
    best, run = None, []
    for f in tops:
        if run and f - run[-1] > 6 * fr:
            run = []
        run.append(f)
        if len(run) >= 2 and (best is None or run[-1] - run[0] > best[1] - best[0]):
            best = (run[0], run[-1])
    if best and best[1] - best[0] >= 40 * fr:
        return max(0, best[0] - int(1.5 * fr)), best[1] + int(2.5 * fr)
    return None


def layout_blocks(obs):
    """Group OCR boxes into blocks: lines stacked above each other (horizontal overlap,
    small vertical gap) belong to the same sign/caption."""
    parent = list(range(len(obs)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i, a in enumerate(obs):
        for j in range(i + 1, len(obs)):
            b = obs[j]
            h = max(a["h"], b["h"])
            xov = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
            gap = max(a["y"], b["y"]) - min(a["y"] + a["h"], b["y"] + b["h"])
            same_line = abs((a["y"] + a["h"] / 2) - (b["y"] + b["h"] / 2)) < h * 0.6 and \
                max(a["x"], b["x"]) - min(a["x"] + a["w"], b["x"] + b["w"]) < h * 0.8
            stacked = xov > 0.5 * min(a["w"], b["w"]) and gap < h * 1.2
            if stacked or same_line:
                parent[find(i)] = find(j)
    groups = collections.defaultdict(list)
    for i, o in enumerate(obs):
        groups[find(i)].append(o)
    return list(groups.values())


CREDIT_RE = re.compile(r"^(Edited|Subtitles|Subtitled|Translated|Translation|Typeset|Typesetting|Timed|Timing|Encoded|Editing|Karaoke|QC)\b.*\bby\b", re.I)


def ts(frame, fr):
    cs = math.floor(frame / fr * 100 + 1e-6)
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("output")
    ap.add_argument("--template", default=DEFAULT_TEMPLATE, help="existing .ass whose [Script Info]/styles to reuse")
    ap.add_argument("--scan-json", help="reuse/save the raw scanner output here (skips rescanning if it exists)")
    ap.add_argument("--review-dir", help="where REVIEW.txt and contact sheets go (default: next to --scan-json or /tmp)")
    ap.add_argument("--band", type=float, default=0.24)
    a = ap.parse_args()

    scan_json = a.scan_json or os.path.join("/tmp", "hardsub_scan_" + re.sub(r"\W+", "_", os.path.basename(a.video)) + ".jsonl")
    review_dir = a.review_dir or os.path.join(os.path.dirname(scan_json), "review")
    os.makedirs(review_dir, exist_ok=True)

    if not os.path.exists(scan_json):
        ensure_binary()
        log("Scanning video (one pass)…")
        subprocess.run([BIN, a.video, scan_json, str(a.band)], check=True)

    meta, segs, scans = {}, [], []
    for line in open(scan_json):
        r = json.loads(line)
        if r["k"] == "meta":
            meta = r
        elif r["k"] == "seg":
            segs.append(r)
        elif r["k"] == "scan":
            scans.append(r)
    fr = meta["fps_num"] / meta["fps_den"]
    op = find_op_window(scans, fr)
    if op:
        log(f"Opening detected {ts(op[0], fr)} – {ts(op[1], fr)}; dropping text inside it")
    else:
        log("No opening detected")
    in_op = (lambda f: op[0] <= f <= op[1]) if op else (lambda f: False)
    vocab = load_vocab()

    # ---- bottom dialogue ----
    events = []  # dicts: s, e, text, flags, kind, pos
    for sg in segs:
        n = sg["e"] - sg["s"]
        if n < 3 or in_op(sg["s"]) or in_op(sg["e"] - 1):
            continue
        by_frame = collections.defaultdict(list)
        for o in sg["o"]:
            by_frame[o["f"]].append(o)
        samples = [obs_to_text(v) for _, v in sorted(by_frame.items())]
        samples = [(clean_tokens(t), c) for t, c in samples]
        samples = [(t, c) for t, c in samples if plausible(t)]
        if not samples:
            continue
        flags = []

        def score(tc):
            t, c = tc
            ws = re.findall(r"[A-Za-z][A-Za-z'’-]*", fix_typos(t, vocab))
            return (sum(known(w, vocab) for w in ws) / max(1, len(ws)), len(norm(t)) > 0, c)
        text, conf = max(reversed(samples), key=score)   # later (fully faded-in) sample wins ties
        if len(samples) > 1 and sim(samples[0][0], samples[-1][0]) < 0.85:
            flags.append("samples disagree: " + " | ".join(t for t, _ in samples))
        if conf < 0.5:
            flags.append(f"low confidence {conf:.2f}")
        events.append({"s": sg["s"], "e": sg["e"], "text": text, "flags": flags, "kind": "main"})

    # merge fade/flicker splits of the same line
    merged = []
    for ev in events:
        p = merged[-1] if merged else None
        if p and ev["s"] - p["e"] <= 2 and sim(p["text"], ev["text"]) >= 0.8:
            if ev["e"] - ev["s"] > p["e"] - p["s"]:
                p["text"] = ev["text"]
            p["e"] = ev["e"]
            p["flags"] = sorted(set(p["flags"] + ev["flags"]))
            continue
        merged.append(ev)
    events = merged

    for ev in events:
        before = ev["text"]
        ev["text"] = fix_typos(ev["text"], vocab)
        if ev["text"] != before:
            ev["fixed"] = before
        unk = [] if CREDIT_RE.match(ev["text"].replace("\\N", " ")) else unknown_words(ev["text"], vocab)
        if unk:
            ev["flags"].append("unknown words: " + ", ".join(unk))
        if re.search(r"[^A-Za-z0-9 .,!?'\"…—\-:;()&%\\]|[:;]$|\b[A-Z][a-z]+[A-Z]", ev["text"].replace("\\N", " ")):
            ev["flags"].append("odd characters/casing")
        if ev["e"] - ev["s"] < 5:
            ev["flags"].append("very short (<5 frames)")

    # ---- captions (caption scan above the band) ----
    step = None
    fs = sorted(s["f"] for s in scans)
    if len(fs) > 1:
        step = min(b - a_ for a_, b in zip(fs, fs[1:]) if b > a_)
    step = step or 12
    open_caps = []  # each: dict(s, last, texts, boxes)
    caps = []
    for sc in sorted(scans, key=lambda s: s["f"]):
        f = sc["f"]
        if in_op(f):
            continue
        seen = []
        for obs in layout_blocks([o for o in sc["o"] if o["c"] >= 0.6]):
            t, c = obs_to_text(obs, 0.6)
            t = clean_tokens(t)
            if not plausible(t) or len(norm(t)) < 3:
                continue
            cx = sum(o["x"] + o["w"] / 2 for o in obs) / len(obs)
            cy = sum(o["y"] + o["h"] / 2 for o in obs) / len(obs)
            match = next((oc for oc in open_caps if f - oc["last"] <= step * 2 and abs(oc["cx"] - cx) < 0.08
                          and abs(oc["cy"] - cy) < 0.08 and sim(oc["texts"][-1], t) > 0.6), None)
            if match:
                match["last"] = f; match["texts"].append(t); seen.append(id(match))
            else:
                oc = {"s": f, "last": f, "texts": [t], "cx": cx, "cy": cy, "conf": c}
                open_caps.append(oc); seen.append(id(oc))
        still = []
        for oc in open_caps:
            if f - oc["last"] > step * 2:
                caps.append(oc)
            else:
                still.append(oc)
        open_caps = still
    caps.extend(open_caps)
    kept = []
    for oc in caps:
        if len(oc["texts"]) < 2 and oc["conf"] < 0.95:
            continue
        # longest frequent reading (signs that scroll/fade in are read partially at first)
        cnt = collections.Counter(oc["texts"])
        top = cnt.most_common(1)[0][1]
        oc["text"] = max((t for t, k in cnt.items() if k >= max(1, top // 2)), key=lambda t: len(norm(t)))
        words = re.findall(r"[A-Za-z']+", oc["text"])
        if len(words) == 1 and (len(words[0]) <= 4 or words[0].isupper()) and len(oc["texts"]) < 4:
            continue   # a short word read off artwork/clothing ("QUEEN", "BriS")
        kept.append(oc)
    final = []
    for oc in sorted(kept, key=lambda c: -len(norm(c["text"]))):
        nt = norm(oc["text"])
        if any(c["s"] <= oc["last"] and oc["s"] <= c["last"] and (nt in norm(c["text"]) or sim(c["text"], oc["text"]) > 0.7)
               for c in final):
            continue   # fragment of a longer caption on screen at the same time
        final.append(oc)
    for oc in final:
        text = oc["text"]
        text = fix_typos(text, vocab)
        if text.upper().replace("\\N", " ").strip() in ("TO BE CONTINUED", "ONE PIECE"):
            continue
        x, y = round(oc["cx"] * 1920), round((1 - oc["cy"]) * 1080)
        events.append({"s": oc["s"], "e": oc["last"] + step, "text": text, "kind": "caption",
                       "pos": (x, y), "flags": ["caption (timing ±0.5s, check position/whether needed)"]})

    mains_all = [e for e in events if e["kind"] == "main"]
    events = [e for e in events if e["kind"] == "main" or not any(
        m["s"] < e["e"] and e["s"] < m["e"] and sim(m["text"], e["text"]) > 0.5 for m in mains_all)]
    events.sort(key=lambda e: e["s"])
    # trim dialogue overlaps
    mains = [e for e in events if e["kind"] == "main"]
    for p, n in zip(mains, mains[1:]):
        if p["e"] > n["s"]:
            p["e"] = n["s"]

    # ---- write .ass ----
    src = open(a.template, encoding="utf-8-sig").read()
    head = src.split("[Aegisub Project Garbage]")[0].split("[V4+ Styles]")[0].rstrip() + "\n\n"
    styles = "[V4+ Styles]" + src.split("[V4+ Styles]")[1].split("[Events]")[0]
    out = [head + styles + "[Events]",
           "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
           f"Comment: 0,0:00:00.00,0:00:00.00,Main-207+,,0,0,0,,{{Source: OCR of hardcoded English subs ({os.path.basename(a.video)}); opening lyrics omitted}}"]
    for ev in events:
        if CREDIT_RE.match(ev["text"].replace("\\N", " ")):
            out.append(f"Dialogue: 0,{ts(ev['s'], fr)},{ts(ev['e'], fr)},Credits-207+,,0,0,0,,{{\\an8}}{ev['text']}")
        elif ev["kind"] == "main":
            out.append(f"Dialogue: 0,{ts(ev['s'], fr)},{ts(ev['e'], fr)},Main-207+,,0,0,0,,{ev['text']}")
        else:
            x, y = ev["pos"]
            out.append(f"Dialogue: 0,{ts(ev['s'], fr)},{ts(ev['e'], fr)},Captions-207+,,0,0,0,,{{\\an5\\pos({x},{y})}}{ev['text']}")
    open(a.output, "w", encoding="utf-8-sig").write("\n".join(out) + "\n")

    # ---- review report + contact sheets ----
    flagged = [e for e in events if e["flags"]]
    rep = [f"OCR review for {os.path.basename(a.video)} -> {os.path.basename(a.output)}",
           f"{sum(e['kind'] == 'main' for e in events)} dialogue lines, {sum(e['kind'] == 'caption' for e in events)} captions, "
           f"{len(flagged)} flagged" + (f"; opening dropped {ts(op[0], fr)}–{ts(op[1], fr)}" if op else "; no opening detected"), ""]
    for e in events:
        if "fixed" in e:
            rep.append(f"auto-fixed  {ts(e['s'], fr)}  {e['fixed']}  ->  {e['text']}")
    rep.append("")
    crops = []
    for i, e in enumerate(flagged, 1):
        rep.append(f"[{i}] {ts(e['s'], fr)}-{ts(e['e'], fr)} {e['kind']}: {e['text']}")
        for fl in e["flags"]:
            rep.append(f"      - {fl}")
        t = (e["s"] + min(e["e"] - e["s"], 24) * 0.6) / fr
        png = os.path.join(review_dir, f"crop_{i:03d}.png")
        if e["kind"] == "main":
            vf = f"crop=iw:ih*{a.band}:0:ih*{1 - a.band},scale=960:-1"
        else:
            x, y = e["pos"]
            vf = f"crop=960:270:{max(0, min(960, x - 480))}:{max(0, min(810, y - 135))}"
        vf += f",pad=iw:ih+28:0:28:gray"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", a.video, "-frames:v", "1", "-vf", vf, png], check=False)
        if os.path.exists(png):
            crops.append((i, png))
    for old in glob.glob(os.path.join(review_dir, "review_*.png")):
        os.remove(old)
    for k in range(0, len(crops), 8):
        chunk = crops[k:k + 8]
        ins = sum([["-i", p] for _, p in chunk], [])
        # number each crop in its grey header strip (drawtext may be unavailable; fall back to plain stack)
        sheet = os.path.join(review_dir, f"review_{k // 8 + 1:02d}.png")
        flt = "".join(f"[{j}]scale=960:-1[v{j}];" for j in range(len(chunk))) + \
              "".join(f"[v{j}]" for j in range(len(chunk))) + f"vstack=inputs={len(chunk)}" if len(chunk) > 1 else "scale=960:-1"
        subprocess.run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", flt, sheet], check=False)
        rep.append(f"sheet {os.path.basename(sheet)}: items " + ", ".join(str(i) for i, _ in chunk))
    for _, p in crops:
        os.remove(p)
    open(os.path.join(review_dir, "REVIEW.txt"), "w").write("\n".join(rep) + "\n")
    log(f"Wrote {a.output}: {sum(e['kind'] == 'main' for e in events)} dialogue + "
        f"{sum(e['kind'] == 'caption' for e in events)} captions; {len(flagged)} flagged -> {review_dir}/REVIEW.txt")


if __name__ == "__main__":
    main()
