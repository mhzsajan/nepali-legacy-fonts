"""qualify_unicode.py -- which UNICODE fonts could actually set these seven songs?

    py scripts/qualify_unicode.py "H:\\Lyric Video Making Folder"

WHY THIS EXISTS
---------------
There are four working Unicode fonts and seven songs, so "non-repetitive fonts"
is not achievable from the verdicts we have. The catalogue holds 54 UNICODE
fonts with no verdict at all. Testing those the obvious way -- render a song in
each -- is about ten minutes each, and most will fail for a reason that can be
known in milliseconds.

So this is the cheap filter that runs FIRST, and it is the same reasoning as
gotcha 23: "usable" means every codepoint the song actually uses reaches a real
glyph. A missing codepoint does not crash. Chromium falls through to another
face for that character, which is how you get a word with a stray letter in the
middle of it -- and that failure is invisible in a spec sheet that renders one
representative line and never the conjunct that was missing.

WHAT IT CHECKS, AND WHAT IT DELIBERATELY DOES NOT
-------------------------------------------------
It reads each font's OWN cmap and asks whether every distinct codepoint in the
seven songs' lyrics is covered. That is mechanical, exact, and takes
milliseconds.

It does NOT decide whether a font is good. Coverage is necessary and not
sufficient: a font can cover every codepoint and still shape क्ष badly, or put
the i-matra on the wrong side, or look like the previous one. That judgement is
a human looking at font_sheet.py output, which is why this prints a SHORTLIST
rather than a verdict. A script that says "working" here would be the exact
failure this repo has already shipped once.

OUTPUT
------
    FULL     covers every codepoint -- go and look at it
    PARTIAL  covers most; the missing codepoints are printed, because "which
             ones" is the whole diagnosis and a bare count is useless
    NONE     not worth a specimen
"""
import json
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

STAMP = re.compile(r"\[(\d{1,3}):([0-5]?\d(?:[.:]\d{1,3})?)\]")
META = re.compile(r"^\[(ti|ar|al|au|by|re|ve|length|offset|ti-font|ti-fontfile):", re.I)


def lyrics_from_folder(root):
    """Every lyric character across every song folder, with its codepoint set."""
    counter = Counter()
    songs = 0
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            if not re.search(r"remotion_start\.lrc$", fn, re.I):
                continue
            songs += 1
            with open(os.path.join(dirpath, fn), encoding="utf-8-sig") as f:
                for raw in f:
                    line = raw.strip()
                    if not line or META.match(line):
                        continue
                    for ch in STAMP.sub("", line):
                        if not ch.strip():
                            continue
                        counter[ch] += 1
    return counter, songs


def cmap_of(ttf):
    """The set of codepoints the font's cmap actually maps to a real glyph."""
    from fontTools.ttLib import TTFont
    font = TTFont(ttf, fontNumber=0, lazy=True)
    covered = set()
    for table in font["cmap"].tables:
        # Only a Unicode subtable counts. A symbol (3,0) subtable maps a few
        # codepoints and would make a font look like it covers Devanagari.
        if table.isUnicode():
            covered |= set(table.cmap.keys())
    font.close()
    return covered


def pick_font(fonts_dir):
    """One representative .ttf, preferring Bold -- these are lyric videos."""
    if not os.path.isdir(fonts_dir):
        return None
    ttfs = sorted(f for f in os.listdir(fonts_dir) if f.lower().endswith(".ttf"))
    if not ttfs:
        return None
    for want in ("bold", "black", "semibold", "medium"):
        for t in ttfs:
            if want in t.lower():
                return os.path.join(fonts_dir, t)
    return os.path.join(fonts_dir, ttfs[0])


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    root = sys.argv[1]
    if not os.path.isdir(root):
        print("Not a folder: " + root)
        return 1

    corpus, songs = lyrics_from_folder(root)
    if not corpus:
        print("No .remotion_start.lrc files under " + root)
        return 1

    wanted = set(ord(c) for c in corpus)
    print()
    print("  corpus: %d songs, %d distinct characters, %d codepoints"
          % (songs, len(corpus), len(wanted)))
    print("  (a conjunct is ONE codepoint here -- this is coverage, not shaping)")

    sweep = json.load(open(os.path.join(HERE, "sweep.json"), encoding="utf-8"))
    verdicts_path = os.path.join(HERE, "verdicts.json")
    decided = {}
    if os.path.exists(verdicts_path):
        decided = json.load(open(verdicts_path, encoding="utf-8")).get("verdicts", {})

    candidates = [r for r in sweep
                  if (r.get("class") or "").upper() == "UNICODE"
                  and r["slug"] not in decided]
    if not candidates:
        print("\n  Every UNICODE font in the catalogue already has a verdict.\n")
        return 0

    full, partial, none_ = [], [], []
    for rec in candidates:
        slug = rec["slug"]
        ttf = pick_font(os.path.join(HERE, "fonts", slug))
        if not ttf:
            none_.append((slug, "no .ttf on disk"))
            continue
        try:
            covered = cmap_of(ttf)
        except Exception as e:                      # a font we cannot open
            none_.append((slug, "unreadable: %s" % str(e)[:40]))
            continue
        missing = sorted(wanted - covered)
        if not missing:
            full.append((slug, os.path.basename(ttf)))
        elif len(missing) <= len(wanted) * 0.12:
            chars = "".join(chr(c) for c in missing)
            where = ", ".join("%s(x%d)" % (c, corpus[c]) for c in missing[:8])
            partial.append((slug, os.path.basename(ttf), len(missing), where))
        else:
            none_.append((slug, "%d/%d codepoints missing"
                          % (len(missing), len(wanted))))

    print()
    print("=== FULL COVERAGE (%d) -- worth a specimen and a human eye ===" % len(full))
    for slug, fn in full:
        print("    %-26s %s" % (slug, fn))

    print()
    print("=== NEAR MISS (%d) -- inspect the missing characters before writing off ===" % len(partial))
    for slug, fn, n, where in partial:
        print("    %-26s %s" % (slug, fn))
        print("        missing %d: %s" % (n, where))

    print()
    print("=== NOT VIABLE (%d) ===" % len(none_))
    for slug, why in none_:
        print("    %-26s %s" % (slug, why))

    print()
    print("  Next: font_sheet.py --slug <name>  (or --only a,b,c) for the FULL list.")
    print("  A specimen is a screenshot of Chromium, which is the renderer the")
    print("  video actually uses -- so it is the render, not an approximation.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())