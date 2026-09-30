"""letter_sheet.py -- every Nepali letter, numbered, with a reference beside it.

    py scripts/letter_sheet.py --slug pawang
    py scripts/letter_sheet.py --slug arya
    py scripts/letter_sheet.py --slug X --only 25,26,31     # re-check some

WHY A SHEET AND NOT A CHECK
---------------------------
Nothing else in this repository can answer the question that decides whether a
font is usable: does this font draw this letter as itself, or as its one-stroke
neighbour? cmap coverage, a clean round-trip and a correct frame check all pass
on a font that gets that wrong -- which is how `abhinav` came to be certified as
verified, and how four never-rendered fonts came to be listed as working.

So this produces no verdict. It produces a numbered grid with a REFERENCE
letter drawn beside every candidate, and a person reads the numbers back. The
reference is the point: the defect being looked for is the font drawing the
wrong shape, and you can only see that if the right shape is on the page.

THE REFERENCE SET
-----------------
Each cell draws the letter twice:

    [ n ]   reference   |   candidate

The reference is set in a Unicode Devanagari face (Nirmala UI, which ships with
Windows) and the candidate in the font under test, through whatever transform
that font needs. Nirmala has native Devanagari codepoints, so it is an
INDEPENDENT answer -- a legacy font cannot be wrong in the same way, because it
has no Devanagari cmap at all (pawang maps 183 codepoints and not one is in
U+0900..U+097F, verified against the binary).

A missing or broken candidate is marked, never silently blank:

    no key     the encoder has no key for this letter, so it passed the
               Devanagari codepoint straight through and the font had nothing
               to draw. A fault in the ENCODER, not the font -- every Preeti
               font does this identically.
    no glyph   the encoder produced a key the font's cmap does not map. The
               font is missing that letter.
    drawn      there is a candidate to compare against the reference.

THE NUMBERING IS FROZEN
-----------------------
It comes from one INVENTORY in this file, so a given number means the same
letter in every sheet ever made. Letters are grapheme CLUSTERS, not codepoints:
`क्ष` is three codepoints forming one letter, and iterating a string of them
splits it into three meaningless cells. Once a person has read a number off a
sheet, renumbering silently invalidates every report already collected.

CONJUNCTS ARE MARKED, NOT SHOWN
-------------------------------
Pillow needs libraqm to shape Devanagari. This machine has none, so the
conjuncts would come out as their component letters in codepoint order, which
is not what the font draws. Those cells are labelled and --through-chromium is
offered. Isolates and matras are trustworthy in this sheet.
"""

import argparse
import glob
import hashlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

# -- THE INVENTORY. Frozen. This defines what "number 34" means. --------------

VOWELS = "अआइईउऊऋएऐओऔ"
MATRAS = "ािीुूृेैोौंःँ"
CONSONANTS = "कखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसहळ"
CONJUNCTS = ("क्ष", "त्र", "ज्ञ", "श्र")
DIGITS = "०१२३४५६७८९"
PUNCT = ("।", "॥", "ऽ")

GROUPS = [
    ("Vowels", tuple(VOWELS)),
    ("Matras", tuple(MATRAS)),
    ("Consonants", CONSONANTS),
    ("Conjuncts*", CONJUNCTS),
    ("Digits", tuple(DIGITS)),
    ("Punctuation", PUNCT),
]


def build_inventory():
    out = []
    n = 0
    for group, chars in GROUPS:
        for ch in chars:
            n += 1
            out.append((n, group, ch, group.startswith("Conjuncts")))
    return out


INVENTORY = build_inventory()
BY_NUMBER = {n: (g, c, needs) for n, g, c, needs in INVENTORY}
BY_CHAR = {c: n for n, _g, c, _x in INVENTORY}

# Stamped onto every sheet, so two sheets can never be confused.
#
# This exists because the numbering silently changed once already. The first
# pawang sheet had 89 cells; `क्ष` and `ज्ञ` had been typed inside the CONSONANT
# string, and Python iterated them by codepoint, so each became three separate
# cells and twelve phantoms landed in the middle of the numbering. Every number
# after the consonants meant something different on the two sheets, and the
# only way to notice was to already know the answer.
#
# A number is only meaningful relative to an inventory. So the sheet carries the
# inventory's own fingerprint: if two PNGs disagree, the images say so instead of
# relying on the reader to spot a shift.
INVENTORY_FINGERPRINT = hashlib.sha256(
    "\n".join("%d\t%s\t%s" % (n, g, c) for n, g, c, _x in INVENTORY).encode("utf-8")
).hexdigest()[:8].upper()
INVENTORY_DATE = "2026-09-30"

# Nirmala is a .ttc (a collection), so PIL needs the face INDEX. Collection
# index 0 is Nirmala UI Regular, which is the one with Devanagari.
REFERENCE_CANDIDATES = [
    # this repo's own yantramanav first: it is the lyric-studio default, it has
    # native Devanagari codepoints, and it is guaranteed present because it is
    # a font this repository is about
    (os.path.join(ROOT, "fonts", "yantramanav", "Yantramanav-Regular.ttf"), 0),
    (os.path.join(ROOT, "fonts", "yantramanav", "Yantramanav-Bold.ttf"), 0),
    (os.path.join(ROOT, "fonts", "yantramanav", "Nirmala.ttc"), 0),
    (os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "Nirmala.ttc"), 0),
    (os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "Nirmala.ttf"), 0),
    ("/System/Library/Fonts/Supplemental/DevanagariMT.ttc", 0),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 0),
]


def _has_deva(path):
    """True only if the face actually maps Devanagari. Otherwise it is useless
    as a reference -- and a face that lacks them draws blank boxes beside every
    real candidate, which looks like the font under test being empty."""
    try:
        cps = font_cmap(path)
    except Exception:
        return False
    return any(0x900 <= c <= 0x97F for c in cps)


REFERENCE = None          # path
REFERENCE_INDEX = 0


def reference_path():
    for p, idx in REFERENCE_CANDIDATES:
        if p and os.path.exists(p) and _has_deva(p):
            return p, idx
    return None, 0


def catalogue():
    with io.open(os.path.join(ROOT, "sweep.json"), encoding="utf-8") as fh:
        return {e["slug"]: e for e in json.load(fh)}


def find_ttf(slug):
    hits = glob.glob(os.path.join(ROOT, "fonts", slug, "*.ttf")) + \
        glob.glob(os.path.join(ROOT, "fonts", slug, "*.TTF")) + \
        glob.glob(os.path.join(ROOT, "fonts", slug, "*.otf"))
    return hits[0] if hits else None


def font_cmap(path):
    f = TTFont(path, fontNumber=0)
    cps = set()
    for t in f["cmap"].tables:
        cps.update(t.cmap)
    return cps


def convert(ch, layout_name):
    """(text_to_draw, keys, ok) -- ok False means the encoder had no key."""
    if layout_name is None:
        return ch, ch, True
    from lrc_legacy import convert_line
    keys = convert_line(ch, layout_name)
    # A pass-through is the tell: the encoder handed back the Devanagari
    # codepoint, so it has no key for this letter. Visible as a non-ASCII
    # character in the key string.
    if any(ord(c) > 0x7F for c in keys):
        return keys, keys, False
    return keys, keys, True


# -- drawing ------------------------------------------------------------------

def draw(path, rows, out, title, sub1, sub2, font_size=46, ref_size=40):
    global REFERENCE
    COLS = 6
    NUM_W, HALF, HEAD_H, ROW_H = 52, 96, 122, 122
    n = len(rows)
    grid = (n + COLS - 1) // COLS
    W = NUM_W + COLS * (2 * HALF)
    H = HEAD_H + grid * ROW_H + 92
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)

    ui = ImageFont.load_default()
    try:
        ui_t = ImageFont.truetype("arial.ttf", 21)
        ui_n = ImageFont.truetype("arialbd.ttf", 24)
        ui_s = ImageFont.truetype("arial.ttf", 15)
    except OSError:
        ui_t = ui_n = ui_s = ui

    d.text((14, 12), title, font=ui_t, fill="black")
    d.text((14, 40), sub1, font=ui_s, fill=(70, 70, 70))
    d.text((14, 58), sub2, font=ui_s, fill=(150, 60, 0))
    d.text((14, 76), "Compare the two. Tell me the NUMBERS where the right-hand "
                     "letter is wrong.", font=ui_s, fill=(0, 90, 0))
    d.text((14, 92), "The inventory number is the contract: a number means the "
                     "same letter only on a sheet with the same #.",
           font=ui_s, fill=(120, 120, 120))
    d.line([(0, HEAD_H - 6), (W, HEAD_H - 6)], fill=(205, 205, 205))

    fnt = ImageFont.truetype(path, font_size)
    ref = (ImageFont.truetype(REFERENCE, ref_size, index=REFERENCE_INDEX)
           if REFERENCE else None)

    for num, group, ch, needs, keys, status in rows:
        i = num - 1
        x = NUM_W + (i % COLS) * (2 * HALF)
        y = HEAD_H + (i // COLS) * ROW_H
        d.rectangle([x, y, x + 2 * HALF - 1, y + ROW_H - 1], outline=(215, 215, 215))
        d.line([(x + HALF, y), (x + HALF, y + ROW_H - 1)], fill=(235, 235, 235))
        d.text((x + 5, y + ROW_H // 2 - 12), str(num), font=ui_n, fill=(190, 30, 30))

        # left: the reference. right: the candidate.
        if ref is not None:
            d.text((x + HALF // 2, y + 44), ch, font=ref, fill=(120, 120, 120),
                   anchor="mm")
        if status == "no key":
            d.text((x + HALF + HALF // 2, y + 34), "NO KEY", font=ui_s,
                   fill=(190, 0, 0), anchor="mm")
            d.text((x + HALF + HALF // 2, y + 56), "encoder has", font=ui_s,
                   fill=(190, 0, 0), anchor="mm")
            d.text((x + HALF + HALF // 2, y + 72), "no mapping", font=ui_s,
                   fill=(190, 0, 0), anchor="mm")
        elif status == "no glyph":
            d.text((x + HALF + HALF // 2, y + 40), "NO GLYPH", font=ui_s,
                   fill=(190, 0, 0), anchor="mm")
            d.text((x + HALF + HALF // 2, y + 60), "font is", font=ui_s,
                   fill=(190, 0, 0), anchor="mm")
            d.text((x + HALF + HALF // 2, y + 76), "missing it", font=ui_s,
                   fill=(190, 0, 0), anchor="mm")
        else:
            d.text((x + HALF + HALF // 2, y + 44), keys, font=fnt, fill="black",
                   anchor="mm")
            if needs:
                d.text((x + HALF + HALF // 2, y + ROW_H - 16), "chromium",
                       font=ui_s, fill=(150, 150, 150), anchor="mm")
        # a pale hint of what the letter is, for anyone unsure of the number
        if ref is not None and not needs:
            d.text((x + HALF // 2, y + ROW_H - 16), ch, font=ui_s,
                   fill=(200, 200, 200), anchor="mm")

    # legend
    y = H - 84
    d.line([(0, y), (W, y)], fill=(205, 205, 205))
    d.text((14, y + 10), "LEFT of the divider = reference (Nirmala UI, a Unicode "
                         "font, so it cannot fail the legacy way).", font=ui_s,
           fill=(70, 70, 70))
    d.text((14, y + 28), "RIGHT = the font under test, drawn through its own "
                         "transform. That is what the video will show.", font=ui_s,
           fill=(70, 70, 70))
    d.text((14, y + 46), "NO KEY = the encoder has no mapping, so it passed the "
                         "Devanagari codepoint through. A fault in the ENCODER, "
                         "not the font.", font=ui_s, fill=(150, 0, 0))
    d.text((14, y + 64), "NO GLYPH = the key is right but the font has no glyph "
                         "there. A fault in the FONT.", font=ui_s, fill=(150, 0, 0))
    img.save(out)
    return out


def main():
    global REFERENCE, REFERENCE_INDEX
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug")
    ap.add_argument("--font-file")
    ap.add_argument("--class", dest="cls", help="PREETI | UNICODE | GENERATED")
    ap.add_argument("--out")
    ap.add_argument("--only", help="comma-separated numbers")
    ap.add_argument("--through-chromium", action="store_true",
                    help="conjuncts need lyric-studio to shape correctly")
    args = ap.parse_args()

    if not args.slug and not args.font_file:
        ap.error("give --slug or --font-file")

    cls, ttf = args.cls, args.font_file
    if args.slug:
        row = catalogue().get(args.slug)
        if row is None:
            sys.exit("  no font %r in sweep.json" % args.slug)
        cls = cls or row.get("class")
        ttf = ttf or find_ttf(args.slug)
        if not ttf or not os.path.exists(ttf):
            sys.exit("  no .ttf under fonts/%s/\n  py scripts/fetch_fonts.py"
                     % args.slug)
    else:
        cls = cls or "PREETI"
    if not os.path.exists(ttf):
        sys.exit("  no such font file: " + ttf)

    REFERENCE, REFERENCE_INDEX = reference_path()
    if not REFERENCE:
        print("  WARNING: no reference face found. The sheet will have an empty")
        print("  left column, which makes it much harder to judge. Install")
        print("  Nirmala UI (ships with Windows) or pass --reference-font.")

    out = args.out or os.path.join(ROOT, "out", "letter-%s.png" % (args.slug or "font"))
    os.makedirs(os.path.dirname(out), exist_ok=True)

    layout_name = None if cls == "UNICODE" else (
        "Preeti" if cls == "PREETI" else args.slug)
    cmap = font_cmap(ttf)

    if args.only:
        wanted = {int(x) for x in args.only.replace(" ", "").split(",") if x}
        unknown = wanted - set(BY_NUMBER)
        if unknown:
            sys.exit("  no such number(s): %s  (1..%d)" % (sorted(unknown), len(INVENTORY)))
        chosen = [r for r in INVENTORY if r[0] in wanted]
    else:
        chosen = INVENTORY

    rows = []
    counts = {"drawn": 0, "no key": 0, "no glyph": 0}
    for num, group, ch, needs in chosen:
        keys, _raw, ok = convert(ch, layout_name)
        if not ok:
            status = "no key"
        elif any(ord(c) not in cmap for c in keys if c.strip()):
            status = "no glyph"
        else:
            status = "drawn"
        counts[status] += 1
        rows.append((num, group, ch, needs, keys, status))

    title = "letter sheet -- %s  (%s)" % (args.slug or os.path.basename(ttf), cls)
    sub1 = "%s   |   %d letters   |   drawn %d, no key %d, no glyph %d" % (
        os.path.basename(ttf), len(INVENTORY), counts["drawn"],
        counts["no key"], counts["no glyph"])
    sub2 = "reference: %s      inventory #%s  (%s, %d letters)" % (
        os.path.basename(REFERENCE) if REFERENCE else "NONE FOUND",
        INVENTORY_FINGERPRINT, INVENTORY_DATE, len(INVENTORY))
    draw(ttf, rows, out, title, sub1, sub2)

    print("  %s" % out)
    print("  %d letters, numbered 1..%d, stable across every sheet"
          % (len(rows), len(INVENTORY)))
    print("  drawn %d | NO KEY %d | NO GLYPH %d"
          % (counts["drawn"], counts["no key"], counts["no glyph"]))
    if counts["no key"]:
        print("")
        print("  NO KEY means the ENCODER cannot map those letters, so it passes the")
        print("  Devanagari codepoint through and the font draws nothing. That is a")
        print("  bug in the mapping table, not in the font -- and every Preeti font")
        print("  does it identically, which is how you can tell the two apart.")
    if counts["no glyph"]:
        print("")
        print("  NO GLYPH means the key was produced and the font has no outline")
        print("  there. That IS a font defect.")
    print("")
    print("  Tell me the numbers where the right-hand letter is wrong.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
