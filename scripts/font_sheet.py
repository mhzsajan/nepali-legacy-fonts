"""font_sheet.py -- an HTML specimen per font, screenshotted with Chromium.

    py scripts/font_sheet.py --slug katmandu
    py scripts/font_sheet.py --only katmandu,ritu,meghubold
    py scripts/font_sheet.py --state untested --limit 10
    py scripts/font_sheet.py --build-only          # just the HTML

WHY CHROMIUM AND NOT PILLOW
---------------------------
Pillow needs libraqm to shape Devanagari, and this machine has none. So the
Pillow sheet draws a conjunct as its component letters in codepoint order, and a
pre-base i-matra to the wrong side -- which is exactly the class of thing this
is meant to show. Those cells were marked "not reliable" rather than trusted.

Chromium shapes Devanagari properly, and it is the renderer the lyric video
actually uses. So a screenshot of an HTML page is not an approximation of the
render -- it IS the render, for a single frame. That is the honest instrument,
and it is why this exists rather than a nicer Pillow script.

THE FONT IS @font-face'd FROM ITS OWN FILE
-----------------------------------------
A Preeti-era font has no Devanagari cmap at all, so the page is handed the
Preeti KEY SEQUENCE, the same bytes the video gets. Handing it the Devanagari
codepoint would silently fall through to a fallback face and produce a sheet
that says nothing about the font under test -- which is how a font with no
letters at all can look like a font that draws them all wrong.

WHAT THE PAGE CONTAINS, IN ORDER
--------------------------------
    title       slug, class, verdict, and the file name
    1. words    real words first: these are what a lyric video shows
    2. vowels
    3. matras on a carrier, because a bare matra is a mark with nothing to judge
    4. consonants
    5. conjuncts -- CORRECTLY SHAPED, which Pillow could not do
    6. digits
    7. punctuation

Words first on purpose. The interesting question is not "does it have a glyph for
this codepoint" but "does a line of it read correctly", and a specimen that
leads with letters answers the easier question.
"""

import argparse
import glob
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "out")
sys.path.insert(0, HERE)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

# -- content ------------------------------------------------------------------

# Real words, which is what the video actually shows. Chosen for the things that
# break: a pre-base i-matra, conjuncts, a candrabindu, a virama, and the
# punctuation-heavy lines this genre uses.
WORDS = ["जाऊ", "फर्केर", "नलाऊ", "हावा", "सँगै", "आउँछु", "झुट्टो",
         "सोझो", "मेरो", "नेपाल", "रिसले", "किस्तो", "भएको", "तिमी", "छैन"]

VOWELS = "अआइईउऊऋएऐओऔ"
MATRAS = "ािीुूृेैोौंःँ"
# A carrier, so each matra is judged in the context it is used in. A bare matra
# is a mark with no baseline to compare it against, and the reference face draws
# it in a position that means nothing on its own.
MATRA_CARRIER = "क"
CONSONANTS = "कखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसहळ"
CONJUNCTS = "क्षत्रज्ञश्रञ्ण"
DIGITS = "०१२३४५६७८९"
PUNCT = "।॥ऽ"

SECTIONS = [
    ("शब्द / WORDS", None),
    ("स्वर / VOWELS", VOWELS),
    ("मात्रा / MATRAS on क", MATRAS),
    ("व्यञ्जन / CONSONANTS", CONSONANTS),
    ("संयुक्ताक्षर / CONJUNCTS", CONJUNCTS),
    ("अङ्क / DIGITS", DIGITS),
    ("विराम / PUNCTUATION", PUNCT),
]


def load_json(path):
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


def find_ttf(slug):
    hits = (glob.glob(os.path.join(ROOT, "fonts", slug, "*.ttf"))
            + glob.glob(os.path.join(ROOT, "fonts", slug, "*.TTF"))
            + glob.glob(os.path.join(ROOT, "fonts", slug, "*.otf")))
    return hits[0] if hits else None


def chrome_path():
    for p in CHROME_CANDIDATES:
        if os.path.exists(p):
            return p
    return None


def keys_for(text, cls, slug):
    """What the FONT must be handed, and a list of things it could not get."""
    if cls == "UNICODE":
        return text, []
    name = "Preeti" if cls == "PREETI" else slug
    from lrc_legacy import convert_line
    problems = []
    out = []
    for piece in text:
        k = convert_line(piece, name)
        if any(ord(c) > 0x7F for c in k):
            problems.append(piece)
        out.append(k)
    return " ".join(out), problems


def build_html(slug, row, ttf, cls):
    """One page per font. Everything inline so Chrome needs no network."""
    import base64
    with open(ttf, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode("ascii")
    fname = os.path.basename(ttf)
    state = row.get("state", "untested")
    look = row.get("look") or row.get("reason") or ""
    note = row.get("note") or ""

    blocks = []
    all_problems = []
    for title, chars in SECTIONS:
        if chars is None:
            items = WORDS
            text, probs = keys_for([w for w in items], cls, slug)
            cells = "".join("<span class=w>%s</span>" % w for w in items)
        else:
            if chars is MATRAS:
                items = [MATRA_CARRIER + m for m in chars]
                text, probs = keys_for(items, cls, slug)
                cells = "".join(
                    '<span class=m><b>%s</b>%s</span>' % (MATRA_CARRIER, m) for m in chars)
            else:
                items = list(chars)
                text, probs = keys_for(items, cls, slug)
                cells = "".join("<span>%s</span>" % c for c in items)
        all_problems.extend(probs)
        blocks.append(
            '<div class="sec"><h2>%s</h2><div class="row">%s</div></div>' % (title, cells))

    problem_note = ""
    if all_problems:
        uniq = sorted(set(all_problems))
        problem_note = (
            '<div class="warn">encoder has no Preeti key for %d of these: %s '
            '&mdash; those cells are drawn in a fallback face and say nothing '
            'about this font</div>'
            % (len(uniq), " ".join("&#x%04X;" % ord(c) for c in uniq)))

    return """<!doctype html>
<html><head><meta charset="utf-8">
<style>
  @font-face { font-family: "Specimen"; src: url(data:font/ttf;base64,%(b64)s) format("truetype"); }
  * { box-sizing: border-box; }
  body { margin:0; background:#fff; color:#111; font-family:"Specimen",monospace; }
  .head { padding:22px 30px 14px; border-bottom:3px solid #222; }
  .slug { font-size:52px; line-height:1.05; }
  .meta { font-size:19px; color:#555; margin-top:6px; font-family:monospace; }
  .badge { display:inline-block; padding:3px 11px; border:2px solid #222;
           font-family:monospace; font-size:17px; margin-left:10px; }
  .warn { margin:12px 30px 0; padding:10px 14px; border:2px solid #b00;
          color:#900; font-family:monospace; font-size:17px; }
  .sec { padding:16px 30px 4px; }
  h2 { font-family:monospace; font-size:17px; color:#777; font-weight:normal;
       margin:0 0 8px; letter-spacing:.4px; }
  .row { display:flex; flex-wrap:wrap; gap:10px; }
  .row span { font-size:54px; line-height:1.16; min-width:44px; text-align:center; }
  .row span.w { font-size:46px; min-width:150px; text-align:left; }
  .row span.m { font-size:50px; min-width:78px; }
  .foot { padding:14px 30px 24px; font-family:monospace; font-size:16px; color:#777;
          border-top:1px solid #ddd; margin-top:18px; }
</style></head>
<body>
  <div class="head">
    <div class="slug">%(slug)s <span class="badge">%(state)s</span></div>
    <div class="meta">%(cls)s &middot; %(fname)s%(look)s%(note)s</div>
  </div>
  %(warn)s
  %(blocks)s
  <div class="foot">Chromium, shaped. If a cell here is wrong, the word in the
  video is wrong &mdash; this is the same renderer, not an approximation.</div>
</body></html>""" % {
        "b64": b64, "slug": slug, "state": state.upper(), "cls": cls,
        "fname": fname,
        "look": (" &middot; " + look) if look else "",
        "note": (" &middot; " + note) if note else "",
        "warn": problem_note, "blocks": "\n".join(blocks),
    }


def shoot(html_path, png_path, w=1600, h=1400):
    """Full-page screenshot. --headless=new so font loading and shaping settle."""
    chrome = chrome_path()
    if not chrome:
        return False, "no Chrome or Edge found"
    profile = os.path.join(OUT, "_chrome_profile")
    cmd = [
        chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
        "--force-device-scale-factor=1",
        "--virtual-time-budget=4000",       # let @font-face and shaping finish
        "--default-background-color=FFFFFFFF",
        "--user-data-dir=" + profile,
        "--window-size=%d,%d" % (w, h),
        "--screenshot=" + png_path,
        "file:///" + html_path.replace("\\", "/"),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    ok = os.path.exists(png_path) and os.path.getsize(png_path) > 2000
    return ok, (r.stderr or "")[-400:] if not ok else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug")
    ap.add_argument("--only", help="comma-separated slugs")
    ap.add_argument("--state", help="comma-separated verdicts to include")
    ap.add_argument("--limit", type=int, default=0, help="cap the count")
    ap.add_argument("--build-only", action="store_true")
    ap.add_argument("--sheets-only", action="store_true",
                    help="make a video from the sheets, skip screenshots")
    args = ap.parse_args()

    v = load_json(os.path.join(ROOT, "verdicts.json"))
    cat = {e["slug"]: e for e in load_json(os.path.join(ROOT, "sweep.json"))}
    os.makedirs(OUT, exist_ok=True)

    only = set(x.strip() for x in args.only.split(",")) if args.only else None
    states = set(x.strip() for x in args.state.split(",")) if args.state else None

    slugs = []
    for e in cat.values():
        slug = e["slug"]
        if e.get("class") != "PREETI":
            continue                      # UNICODE needs no conversion at all
        if only and slug not in only:
            continue
        if states:
            st = v.get("verdicts", {}).get(slug, {}).get("state", "untested")
            if st not in states:
                continue
        if not find_ttf(slug):
            continue
        slugs.append(slug)
    slugs.sort()
    if args.limit:
        slugs = slugs[:args.limit]

    if not slugs:
        sys.exit("  no fonts matched -- check --only / --state")

    print("  %d PREETI font(s) with a binary on disk" % len(slugs))
    if not args.build_only:
        made, failed = 0, []
        for i, slug in enumerate(slugs, 1):
            row = v.get("verdicts", {}).get(slug, {})
            cls = cat[slug].get("class")
            ttf = find_ttf(slug)
            html = os.path.join(OUT, "sheet-%s.html" % slug)
            png = os.path.join(OUT, "sheet-%s.png" % slug)
            with io.open(html, "w", encoding="utf-8") as fh:
                fh.write(build_html(slug, row, ttf, cls))
            ok, err = shoot(html, png)
            if ok:
                made += 1
                print("  [%2d/%2d] ok    %-24s %s" % (i, len(slugs), slug,
                                                      os.path.basename(png)))
            else:
                failed.append(slug)
                print("  [%2d/%2d] FAIL  %-24s %s" % (i, len(slugs), slug, err[:90]))
        print("")
        print("  %d sheet(s) written to %s" % (made, OUT))
        if failed:
            print("  failed: %s" % ", ".join(failed))
    else:
        for slug in slugs:
            html = os.path.join(OUT, "sheet-%s.html" % slug)
            with io.open(html, "w", encoding="utf-8") as fh:
                fh.write(build_html(slug, v.get("verdicts", {}).get(slug, {}),
                                    find_ttf(slug), cat[slug].get("class")))
        print("  %d html page(s) written" % len(slugs))
    print("")
    print("  Next: py scripts\\sheet_video.py   to turn these into a slow video")
    return 0


if __name__ == "__main__":
    sys.exit(main())
