"""font_video.py -- one short video per font, for reading its letters by eye.

    py scripts/font_video.py --limit 10            # the first 10 untested
    py scripts/font_video.py --only katmandu,ritu
    py scripts/font_video.py --state untested --limit 10
    py scripts/font_video.py --list                 # what it would do

WHAT EACH VIDEO IS
------------------
One font. Roughly 20 seconds. It shows, slowly:

    0s   the font's name, class and verdict
    2s   real WORDS          जाऊ  सँगै  आउँछु  रिसले  नेपाल ...
    7s   vowels + matras on a carrier
    12s  consonants, in order
    17s  conjuncts, digits, punctuation
    20s  the name again, so you know what you just saw

You pause on any frame and read it. Nothing moves off before you have had time
to look, which is the whole point: a still image is easier to miss a letter on,
because you have no idea when to look back.

WHY CHROMIUM, AND WHY NOT THE STATIC SHEETS
-------------------------------------------
The Pillow sheets could not draw a conjunct. Pillow needs libraqm to shape
Devanagari, this machine has none, so क्ष came out as क + ् + ष in codepoint
order and a pre-base i-matra sat on the wrong side. Those cells were marked
"not reliable" rather than trusted.

This renders through Chromium, which shapes properly and is the SAME renderer
the lyric video uses. So a frame of this video is not an approximation of what
the song will look like -- it is what it will look like, for that font.

THE FONT IS HANDED ITS PREETI KEYS
---------------------------------
A Preeti-era font has no Devanagari cmap at all. The page is given the key
sequence, the same bytes the video gets. Handing it the Devanagari codepoint
would fall through to a fallback face, and the video would then be showing you
a different font while claiming to be about this one.

Letters the encoder cannot map are reported, not hidden: if a letter is missing
from the table the video says so on that card, because a blank cell is otherwise
indistinguishable from a wrong glyph.
"""

import argparse
import glob
import io
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "out")
VID = os.path.join(OUT, "videos")
sys.path.insert(0, HERE)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

W, H = 1280, 720
FPS = 30
# seconds each captured still is held on screen. The card durations are
# implemented by REPEATING the still this many times in the encode, not by
# any animation in the page -- see frames_via_screenshots.
HOLD = 0.5

CHROME = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]
FFMPEG_CANDIDATES = [
    r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
    os.path.join(os.path.dirname(HERE), "..", "lyric-studio", "node_modules",
                 "@remotion", "compositor-win32-x64-msvc", "ffmpeg.exe"),
]

# -- the cards, in order ------------------------------------------------------

WORDS = ["जाऊ", "फर्केर", "नलाऊ", "हावा", "सँगै", "आउँछु", "झुट्टो", "सोझो",
         "मेरो", "नेपाल", "रिसले", "किस्तो", "भएको", "तिमी"]
VOWELS = "अआइईउऊऋएऐओऔ"
MATRAS = "ािीुूृेैोौंःँ"
CONSONANTS = "कखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसहळ"
CONJUNCTS = "क्षत्रज्ञश्र"
DIGITS = "०१२३४५६७८९"
PUNCT = "।॥ऽ"

# (label, items, seconds). Words first: the question is whether a LINE reads
# correctly, not whether a codepoint resolves.
CARDS = [
    ("title", None, 2.0),
    ("words", WORDS, 5.0),
    ("vowels", VOWELS, 3.0),
    ("matras", MATRAS, 3.0),
    ("consonants", CONSONANTS, 5.0),
    ("conjuncts", CONJUNCTS + DIGITS + PUNCT, 3.0),
    ("title", None, 2.0),
]


def load_json(p):
    with io.open(p, encoding="utf-8") as fh:
        return json.load(fh)


def find_ttf(slug):
    h = (glob.glob(os.path.join(ROOT, "fonts", slug, "*.ttf"))
         + glob.glob(os.path.join(ROOT, "fonts", slug, "*.TTF"))
         + glob.glob(os.path.join(ROOT, "fonts", slug, "*.otf")))
    return h[0] if h else None


def which(cands):
    for p in cands:
        if p and os.path.exists(os.path.abspath(p)):
            return os.path.abspath(p)
    return None


def keys_for(text, cls, slug):
    """(string for the font, [items the encoder could not map])"""
    if cls == "UNICODE":
        return text, []
    name = "Preeti" if cls == "PREETI" else slug
    from lrc_legacy import convert_line
    missing, out = [], []
    for piece in text:
        k = convert_line(piece, name)
        if any(ord(c) > 0x7F for c in k):
            missing.append(piece)
        out.append(k)
    return " ".join(out), missing


PAGE = """<!doctype html><html><head><meta charset="utf-8"><style>
@font-face {{ font-family: Specimen;
  src: url(data:font/ttf;base64,{b64}) format("truetype"); }}
* {{ box-sizing:border-box; margin:0; }}
html,body {{ width:{w}px; height:{h}px; overflow:hidden; background:#000;
  color:#fff; font-family:Specimen,sans-serif; }}
#stage {{ width:{w}px; height:{h}px; position:relative; }}
.card {{ position:absolute; inset:0; padding:56px 64px; display:flex;
  flex-direction:column; justify-content:center; opacity:0; }}
.card.on {{ opacity:1; }}
.card.head {{ justify-content:center; text-align:left; }}
.slug {{ font-size:96px; line-height:1.02; }}
.vstate {{ font-family:monospace; font-size:30px; margin-top:18px;
  color:#bbb; letter-spacing:2px; }}
.fname {{ font-family:monospace; font-size:22px; color:#888; margin-top:10px; }}
.hint {{ font-family:monospace; font-size:24px; color:#9ad; margin-top:34px; }}
.cap {{ font-family:monospace; font-size:26px; color:#999; margin-bottom:26px; }}
.big {{ font-size:76px; line-height:1.32; word-spacing:14px; }}
.big span {{ display:inline-block; margin:0 20px 0 0; }}
.big.w span {{ font-size:68px; margin:0 34px 0 0; }}
.warn {{ font-family:monospace; font-size:22px; color:#e66; margin-top:22px; }}
#bar {{ position:absolute; left:0; bottom:0; height:6px; background:#4a4; }}
</style></head><body><div id="stage">{cards}<div id="bar"></div></div>
<script>
  // PINNED mode. The page is a static document and the video is assembled by
  // repeating stills, so there is no animation here at all.
  //
  // It used to drive its own requestAnimationFrame clock, which cannot work
  // headless: --virtual-time-budget fast-forwards to the end of the timeline
  // and captures that, so every frame of the first attempt was byte-identical.
  // The page now shows exactly one card, chosen by ?card=N, and does nothing
  // else. Dwell time is applied by the encoder, not here.
  var m = /[?&]card=(\\d+)/.exec(location.search);
  var only = m ? parseInt(m[1], 10) : 0;
  document.querySelectorAll('.card').forEach(function(c) {{ c.classList.remove('on'); }});
  var el = document.getElementById('card' + only);
  if (el) el.classList.add('on');
  document.getElementById('bar').style.width = '100%';
</script></body></html>"""


def build_page(slug, row, ttf, cls):
    import base64
    with open(ttf, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode("ascii")
    state = row.get("state", "untested")
    look = row.get("look") or row.get("reason") or ""
    cards, missing_all = [], set()

    for i, (kind, items, secs) in enumerate(CARDS):
        if kind == "title":
            body = (
                '<div class="slug">%s</div>'
                '<div class="vstate">%s &nbsp;&middot;&nbsp; %s</div>'
                '<div class="fname">%s%s</div>'
                '<div class="hint">%s</div>'
                % (slug, state.upper(), cls, os.path.basename(ttf),
                   (" &middot; " + look) if look else "",
                   "every letter, in this font, as the video will draw it"
                   if i == 0 else "that was %s" % slug))
        else:
            if items is MATRAS:
                shown = ["क" + m for m in items]
                text, miss = keys_for(shown, cls, slug)
            else:
                shown = list(items)
                text, miss = keys_for(shown, cls, slug)
            # keys_for reports the ITEMS it could not map, and for the words
            # card those are whole words, not single characters -- so they are
            # printed as they are rather than as codepoints. ord() on a word
            # raised TypeError, which is how this was found.
            missing_all.update(miss)
            cls_words = "big w" if kind == "words" else "big"
            body = '<div class="%s">%s</div>' % (
                cls_words,
                "".join("<span>%s</span>" % s for s in shown))
            if miss:
                printable = " ".join(
                    m if len(m) > 1 else "&#x%04X;" % ord(m) for m in miss)
                body += ('<div class="warn">%d of these have no Preeti key in '
                         'the table, so they show in a fallback face and say '
                         'nothing about this font: %s</div>'
                         % (len(miss), printable))
            body = '<div class="cap">%s</div>%s' % (kind.upper(), body)
        cards.append('<div class="card%s" id="card%d">%s</div>'
                     % (" on" if i == 0 else "", i, body))

    times = [c[2] for c in CARDS]
    return PAGE.format(b64=b64, w=W, h=H, cards="".join(cards),
                       dur=sum(times), times=times), sum(times)


def record(html_path, mp4_path, seconds, chrome, ffmpeg):
    """Record the page with Chrome's screencast, then mux to mp4.

    Chrome writes a webm screencast; ffmpeg converts it. Recording rather than
    screenshotting N frames because the page is a real animation and a
    screenshot would have to reproduce the timing by hand.
    """
    prof = os.path.join(OUT, "_chrome_vid")
    webm = mp4_path[:-4] + ".webm"
    for p in (webm, mp4_path):
        if os.path.exists(p):
            os.remove(p)
    cmd = [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
           "--force-device-scale-factor=1",
           "--autoplay-policy=no-user-gesture-required",
           "--window-size=%d,%d" % (W, H),
           "--screenshot-size=%d,%d" % (W, H),
           "--user-data-dir=" + prof,
           "--virtual-time-budget=%d" % int(seconds * 1000 + 4000),
           "--enable-logging", "--v=0",
           "file:///" + html_path.replace("\\", "/")]
    # Chrome cannot screencast to a file directly, so the reliable path is a
    # frame sequence via --screenshot in a loop -- slow. Instead use ffmpeg's
    # gdigrab on a real window: simpler to drive with a fixed frame count.
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return r


def frames_via_screenshots(html_path, outdir, chrome, hold=0.5):
    """One screenshot per CARD, pinned, then ffmpeg glues them with dwell time.

    The first version screenshotted the page repeatedly and let the page's own
    requestAnimationFrame clock decide which card was on screen. That cannot
    work headless: --virtual-time-budget fast-forwards the page's timeline and
    captures the END of it, so all 46 frames came out byte-identical -- 23
    seconds of one static title card. That is worse than useless, because it
    looks exactly like a successful render: right duration, right resolution,
    real font, and one card.

    So the timing is inverted. The page does no animation at all; the page is
    PINNED to one card per screenshot, and the dwell time comes from repeating
    that still frame in the ffmpeg concat. The frame on screen is then a static
    document, so what you see is what Chromium renders, with no dependence on how
    a headless clock happens to behave -- which is the whole reason for
    rendering through Chromium at all.

    `?card=N` picks the card; the page reads it and shows only that one.
    """
    os.makedirs(outdir, exist_ok=True)
    prof = os.path.join(OUT, "_chrome_cards")
    paths = []
    for i, (kind, items, secs) in enumerate(CARDS):
        p = os.path.join(outdir, "c%02d.png" % i)
        cmd = [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
               "--force-device-scale-factor=1",
               # small: nothing animates, we only need the font to load and
               # shape. A large budget re-introduces the same failure.
               "--virtual-time-budget=1500",
               "--user-data-dir=" + prof,
               "--window-size=%d,%d" % (W, H),
               "--screenshot=" + p,
               "file:///" + html_path.replace("\\", "/") + "?card=%d" % i]
        subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if not (os.path.exists(p) and os.path.getsize(p) > 2000):
            print("      card %d (%s) captured nothing" % (i, kind))
            continue
        paths.extend([p] * max(1, int(round(secs / hold))))
    return paths


CARDS_TOTAL = sum(c[2] for c in CARDS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug")
    ap.add_argument("--only", help="comma-separated")
    ap.add_argument("--state", help="comma-separated verdicts")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--list", action="store_true", help="show what it would do")
    ap.add_argument("--html-only", action="store_true")
    args = ap.parse_args()

    v = load_json(os.path.join(ROOT, "verdicts.json"))
    cat = {e["slug"]: e for e in load_json(os.path.join(ROOT, "sweep.json"))}
    os.makedirs(VID, exist_ok=True)

    only = set(x.strip() for x in args.only.split(",")) if args.only else None
    states = set(x.strip() for x in args.state.split(",")) if args.state else None

    slugs = []
    for e in cat.values():
        s = e["slug"]
        if e.get("class") != "PREETI" or (only and s not in only) or not find_ttf(s):
            continue
        if states:
            st = v.get("verdicts", {}).get(s, {}).get("state", "untested")
            if st not in states:
                continue
        slugs.append(s)
    slugs.sort()
    # put the ones the user already suspects first
    PRIORITY = ["katmandu", "shreenath-bold", "himalayabold", "ananda-lipi-bold-bt",
                "meghubold", "preeti", "ritu", "bhaktapur", "kanchan", "kirti",
                "timila", "bantawa", "dev-nep", "mulchand", "pagal", "kam"]
    slugs.sort(key=lambda s: (PRIORITY.index(s) if s in PRIORITY else 99, s))
    if args.limit:
        slugs = slugs[:args.limit]

    if args.list:
        print("  would make %d video(s), %.0fs each:" % (len(slugs), CARDS_TOTAL))
        for s in slugs:
            st = v.get("verdicts", {}).get(s, {}).get("state", "untested")
            print("    %-24s %s" % (s, st))
        return 0
    if not slugs:
        sys.exit("  no fonts matched")

    chrome = which(CHROME)
    ffmpeg = which(FFMPEG_CANDIDATES)
    if not chrome:
        sys.exit("  no Chrome/Edge found")
    if not ffmpeg and not args.html_only:
        sys.exit("  no ffmpeg found -- use --html-only to get the pages")

    print("  %d video(s), ~%.0fs each" % (len(slugs), CARDS_TOTAL))
    print("  chrome: %s" % os.path.basename(chrome))
    if ffmpeg:
        print("  ffmpeg: %s" % ffmpeg)
    print("")

    for i, slug in enumerate(slugs, 1):
        row = v.get("verdicts", {}).get(slug, {})
        cls = cat[slug].get("class")
        html, dur = build_page(slug, row, find_ttf(slug), cls)
        hp = os.path.join(OUT, "v-%s.html" % slug)
        with io.open(hp, "w", encoding="utf-8") as fh:
            fh.write(html)
        if args.html_only:
            print("  [%2d/%2d] html  %s" % (i, len(slugs), os.path.basename(hp)))
            continue
        frames = frames_via_screenshots(hp, os.path.join(OUT, "_fr_" + slug),
                                        chrome)
        mp4 = os.path.join(VID, "%s.mp4" % slug)
        if not frames:
            print("  [%2d/%2d] FAIL  %-20s no frames captured" % (i, len(slugs), slug))
            continue
        # ffmpeg needs a CONSECUTIVE sequence to read as a stream. The capture
        # writes one file per card (c00, c01, ...), so the list of stills is
        # written out with a numbered copy first. Doing it with a hardlink where
        # possible and a copy otherwise, because 46 real copies per font times
        # 66 fonts is a lot of disk for frames that are mostly duplicates.
        seq = os.path.join(OUT, "_seq_" + slug)
        if os.path.isdir(seq):
            shutil.rmtree(seq, ignore_errors=True)
        os.makedirs(seq, exist_ok=True)
        for n, src_png in enumerate(frames):
            dst = os.path.join(seq, "f%04d.png" % n)
            try:
                os.link(src_png, dst)
            except (OSError, AttributeError):
                shutil.copyfile(src_png, dst)

        cmd = [ffmpeg, "-y", "-framerate", str(1 / HOLD), "-i",
               os.path.join(seq, "f%04d.png"),
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
               "-vf", "scale=%d:%d" % (W, H), mp4]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if r.returncode == 0 and os.path.exists(mp4):
            kb = os.path.getsize(mp4) // 1024
            print("  [%2d/%2d] ok    %-20s %s  (%d KB, %d frames)"
                  % (i, len(slugs), slug, os.path.basename(mp4), kb, len(frames)))
        else:
            print("  [%2d/%2d] FAIL  %-20s ffmpeg: %s"
                  % (i, len(slugs), slug, (r.stderr or "")[-120:]))
    print("")
    print("  videos in %s" % VID)
    return 0


if __name__ == "__main__":
    sys.exit(main())
