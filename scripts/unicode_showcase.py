"""unicode_showcase.py -- ONE page, every UNICODE font, the same real lyrics.

    py scripts/unicode_showcase.py "H:\\Lyric Video Making Folder"
    py scripts/unicode_showcase.py "H:\\..." --only noto-serif-devanagari,rozha-one
    py scripts/unicode_showcase.py "H:\\..." --columns 2

WHY ONE PAGE AND NOT FIFTY-THREE
--------------------------------
53 of the 54 undecided UNICODE fonts have full cmap coverage of the seven songs,
so they are all structurally usable -- this repo's own AGENTS.md says Tier A
(UNICODE) has "nothing to get wrong", because there is no key layout to
transcode into and therefore no way for a word to come out spelled wrongly.

That leaves exactly one question, and it is not mechanical: which of them do you
want to look at. Fifty-three separate specimen files is the wrong shape for that
question. It asks you to open, close, and remember fifty-three screenshots and
hold fifty-three typefaces in your head at once, which is the one thing a human
cannot do.

So: one page, one lyric block per font, same three lines everywhere so the ONLY
variable is the typeface. You pick seven by pointing at them.

THE LINES ARE REAL, AND THAT IS THE WHOLE POINT
-----------------------------------------------
They are taken from the seven songs' own .lrc files -- not a pangram, not
"the quick brown fox". A font can cover every codepoint and still set a
conjunct badly, and the conjunct is where Devanagari fonts differ. A specimen
that shows a representative line instead of the lyrics will happily pass a font
that mangles the one word you care about.

The lines are chosen for what they CONTAIN, not for how they look:
    line 1  a four-word phrase, the ordinary case
    line 2  conjuncts and a pre-base i-matra -- the case that separates faces
    line 3  short words, where a loose face falls apart

CHROMIUM, AND WHY THE SCREENSHOT IS THE RENDER
----------------------------------------------
Chromium shapes Devanagari properly and it is the renderer the lyric video
actually uses, so this page is not an approximation of the deliverable -- for a
single frame it IS the deliverable. Pillow without libraqm would draw a
conjunct as its component letters in codepoint order and put the i-matra on the
wrong side, which is precisely the defect being looked for.

FONTS ARE EMBEDDED, NOT LINKED
------------------------------
Each .ttf is base64'd into an @font-face. A src: url(file://...) is blocked by
Chrome's file-origin rules in some configurations, and the failure mode is
SILENT: the page falls back to Nirmala UI and every row looks identical and
perfect. Embedding removes that failure because there is no second fetch to
fail. (Every row looking identical is the thing to check for first.)
"""
import argparse
import base64
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = os.path.join(HERE, "out")
STAMP = re.compile(r"\[(\d{1,3}):([0-5]?\d(?:[.:]\d{1,3})?)\]")
META = re.compile(r"^\[(ti|ar|al|au|by|re|ve|length|offset|ti-font|ti-fontfile):", re.I)

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def chrome_path():
    for p in CHROME_CANDIDATES:
        if os.path.exists(p):
            return p
    return None


def find_ttf(slug):
    d = os.path.join(HERE, "fonts", slug)
    if not os.path.isdir(d):
        return None
    ttfs = sorted(f for f in os.listdir(d) if f.lower().endswith(".ttf"))
    if not ttfs:
        return None
    for want in ("bold", "black", "semibold", "medium"):
        for t in ttfs:
            if want in t.lower():
                return os.path.join(d, t)
    return os.path.join(d, ttfs[0])


def real_lines(root):
    """Three real lyric lines, chosen by what they contain rather than by looks."""
    buckets = {"phrase": [], "conjunct": [], "short": []}
    for dirpath, _dirs, files in os.walk(root):
        for fn in files:
            if not re.search(r"remotion_start\.lrc$", fn, re.I):
                continue
            song = os.path.basename(dirpath)
            with open(os.path.join(dirpath, fn), encoding="utf-8-sig") as f:
                for raw in f:
                    line = raw.strip()
                    if not line or META.match(line):
                        continue
                    text = STAMP.sub("", line).strip()
                    if not text:
                        continue
                    words = text.split()
                    # A pre-base i-matra, or a stacked conjunct: these are where
                    # Devanagari faces differ and where a font can be wrong.
                    hard = bool(re.search(r"[\u093f\u094d\u0940-\u094d\u094b]", text))
                    rec = (song, text)
                    if len(words) >= 4 and len(buckets["phrase"]) < 40 and not hard:
                        buckets["phrase"].append(rec)
                    elif hard and len(buckets["conjunct"]) < 40:
                        buckets["conjunct"].append(rec)
                    elif len(words) <= 2 and len(buckets["short"]) < 40:
                        buckets["short"].append(rec)
    return buckets


def pick_three(buckets):
    """One from each bucket, spread across different songs so three fonts are not
    compared on the luck of the draw."""
    out = []
    used = set()
    for key in ("phrase", "conjunct", "short"):
        for song, text in buckets[key]:
            if song in used:
                continue
            used.add(song)
            out.append((song, text))
            break
    return out or [("?", "-")]


def build_html(slugs, lines, columns):
    rows = []
    for slug in slugs:
        ttf = find_ttf(slug)
        if not ttf:
            continue
        with open(ttf, "rb") as fh:
            b64 = base64.b64encode(fh.read()).decode("ascii")
        fname = os.path.basename(ttf)
        cells = "".join(
            '<div class="ln"><span class="song">%s</span>%s</div>' % (esc(song), esc(text))
            for song, text in lines
        )
        rows.append(
            '<div class="card">'
            '<div class="meta"><b>%s</b><span>%s</span></div>'
            '<div class="spec" style="font-family:\'%s\'">%s</div>'
            '</div>' % (esc(slug), esc(fname), esc(slug), cells)
        )

    return """<!doctype html><html><head><meta charset="utf-8"><style>
@font-face { font-family: '%(first)s'; src: url(data:font/ttf;base64,%(b64)s); }
%(faces)s
* { box-sizing: border-box; }
body { margin:0; padding:22px 26px; background:#0a0a0a; color:#fff;
       font-family: 'Nirmala UI', sans-serif; }
h1 { font-size:19px; margin:0 0 4px; font-family:Consolas,monospace; color:#ffd; }
p.lede { font-size:13px; margin:0 0 20px; color:#bbb; font-family:Consolas,monospace; }
.grid { display:grid; grid-template-columns:repeat(%(cols)d, 1fr); gap:14px; }
.card { background:#000; border:1px solid #2a2a2a; border-radius:8px; padding:12px 14px 14px; }
.meta { display:flex; justify-content:space-between; align-items:baseline;
        font-family:Consolas,monospace; font-size:11px; color:#8f8; margin-bottom:8px; }
.meta span { color:#666; font-size:10px; }
.spec { font-size:34px; line-height:1.34; }
.ln { white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.song { font-family:Consolas,monospace; font-size:9px; color:#777;
        display:inline-block; width:118px; vertical-align:middle; }
</style></head><body>
<h1>UNICODE fonts on REAL lyric lines &mdash; %(n)d candidates</h1>
<p class="lede">Identical three lines for every face. Chromium-shaped, embedded, so there is no fallback
to hide behind: if two rows look the same, the font did not load. Pick the ones you want song-tested.</p>
<div class="grid">%(rows)s</div>
</body></html>""" % {
        "first": slugs[0] if slugs else "x",
        "b64": "",
        "faces": "\n".join(
            "@font-face { font-family: '%s'; src: url(data:font/ttf;base64,%s); }"
            % (s, base64.b64encode(open(find_ttf(s), "rb").read()).decode("ascii"))
            for s in slugs if find_ttf(s)
        ),
        "cols": columns,
        "n": len(slugs),
        "rows": "".join(rows),
    }


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def shoot(html_path, png_path, w=2200, h=1400):
    chrome = chrome_path()
    if not chrome:
        return False, "no Chrome or Edge found"
    os.makedirs(OUT, exist_ok=True)
    profile = os.path.join(OUT, "_chrome_profile_showcase")
    cmd = [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
           "--force-device-scale-factor=1",
           "--virtual-time-budget=20000",       # 50-odd embedded faces need time
           "--default-background-color=FF0A0A0A",
           "--user-data-dir=" + profile,
           "--window-size=%d,%d" % (w, h),
           "--screenshot=" + png_path,
           "file:///" + html_path.replace("\\", "/")]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    ok = os.path.exists(png_path) and os.path.getsize(png_path) > 5000
    return ok, (r.stderr or "")[-500:] if not ok else ""


# One card is ~236px tall at spec-size 34px. Chrome's --screenshot captures the
# WINDOW, not the full page, so a height that does not match the row count
# SILENTLY TRUNCATES: the first run of this produced a clean 0.1 MB PNG showing
# 14 of 58 fonts and reported success, because a truncated screenshot is still a
# screenshot. Hence measured_png_height(), and main() splitting into pages rather
# than trusting one enormous capture.
CARD_H = 236
HEAD_H = 120


def measured_png_height(n_fonts, columns):
    rows = (n_fonts + columns - 1) // columns
    return HEAD_H + rows * CARD_H + 40


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("songs", help="folder holding the song subfolders")
    ap.add_argument("--only", help="comma-separated slugs")
    ap.add_argument("--columns", type=int, default=2)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--per-page", type=int, default=12,
                    help="fonts per PNG (default 12; 0 = all on one page)")
    ap.add_argument("--html-only", action="store_true")
    a = ap.parse_args()

    if not os.path.isdir(a.songs):
        print("Not a folder: " + a.songs)
        return 1

    sweep = json.load(open(os.path.join(HERE, "sweep.json"), encoding="utf-8"))
    slugs = sorted(r["slug"] for r in sweep
                   if (r.get("class") or "").upper() == "UNICODE" and find_ttf(r["slug"]))
    if a.only:
        want = set(x.strip() for x in a.only.split(","))
        slugs = [s for s in slugs if s in want]
    if a.limit:
        slugs = slugs[:a.limit]
    if not slugs:
        print("No UNICODE fonts with a binary on disk.")
        return 1

    buckets = real_lines(a.songs)
    lines = pick_three(buckets)
    print()
    print("  %d UNICODE fonts on disk" % len(slugs))
    for song, text in lines:
        print("    line from %-22s %s" % (song[:22], text[:40]))
    print()

    os.makedirs(OUT, exist_ok=True)
    # Paged rather than one enormous capture. A 58-font page is ~7000px tall,
    # which is past what a single --window-size reliably renders, and a
    # truncated screenshot still exits 0 and still looks like a successful run.
    per_page = a.per_page or len(slugs)
    pages = [slugs[i:i + per_page] for i in range(0, len(slugs), per_page)]
    written = []
    for pi, chunk in enumerate(pages, 1):
        html_path = os.path.join(OUT, "unicode_showcase-%d.html" % pi)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(build_html(chunk, lines, a.columns))
        png_path = os.path.join(OUT, "unicode_showcase-%d.png" % pi)
        if a.html_only:
            print("  html  %s  (%.1f MB)" % (html_path, os.path.getsize(html_path) / 1048576))
            continue
        h = measured_png_height(len(chunk), a.columns)
        ok, err = shoot(html_path, png_path, h=h)
        if not ok:
            print("  page %d screenshot FAILED: %s" % (pi, err))
            return 1
        size_mb = os.path.getsize(png_path) / 1048576
        # NOTE: there is deliberately NO size-based truncation check here. The
        # first version had one ("a page of many fonts under 0.4 MB has been cut
        # short") and it fired on every single page, because a page that is 90%
        # black compresses to about 0.1 MB whether or not it is complete. A
        # heuristic that is always wrong trains you to ignore it. The real
        # protection is that the window height is MEASURED from the row count
        # above rather than left at a default.
        print("  png   %s  (%.1f MB, %d fonts, %dpx tall)"
              % (png_path, size_mb, len(chunk), h))
        written.append(png_path)

    print()
    print("  %d page(s), %d fonts. The lines are IDENTICAL on every page, so a face"
          % (len(pages), len(slugs)))
    print("  can be compared across pages. Tell me the slugs you want and I will")
    print("  song-test those, then set them in verdicts.json.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())