"""letter_sheet.py -- every Nepali letter, numbered, for a human to look at.

    py scripts/letter_sheet.py --slug pawang
    py scripts/letter_sheet.py --slug arya --class UNICODE
    py scripts/letter_sheet.py --font-file "fonts/x.ttf" --class PREETI

WHY THIS EXISTS
---------------
Everything else in this repository is a machine check, and a machine check
cannot answer the question that actually matters: does this font draw `ढ` as
`ढ`, or as `ढ`'s neighbour? `ढ` and `ढ` are one stroke apart and no amount of
cmap or round-trip verification can tell them apart. Only a person looking at
the shapes can.

So the output is deliberately NOT a verdict. It is a numbered grid, and the
numbering is stable, so a person can say "number 34 is wrong" and that can be
recorded. `verdicts.json` gains per-letter findings from those reports.

THE ORDER IS FIXED AND PRINTED
------------------------------
The numbers mean nothing unless they mean the same thing in every sheet, so the
inventory below is the single source of the numbering and the sheet prints it.
Reordering it would silently invalidate every number anyone has already read.

SHAPING, AND WHAT THIS SHEET CANNOT SHOW
----------------------------------------
Pillow needs libraqm to shape Devanagari: conjuncts (क्ष), the reordering of a
pre-base matra (नि), and the virama. This machine has no raqm, so:

  * ISOLATED consonants, vowels, matras and digits render correctly. A single
    codepoint needs no shaping -- the font's own glyph is the answer.
  * CONJUNCTS and anything combining DO NOT render correctly here. They will
    come out as their component letters in codepoint order, which is not what
    the font draws in a real render.

That is why conjuncts are listed separately and marked. A conjunct row here is
a reminder to look at it in a real render, not evidence about the font. Getting
this right needs Chromium, which is the renderer the video actually uses:

    py scripts/letter_sheet.py --slug pawang --through-chromium

which is slower and needs lyric-studio, and is the honest way to see conjuncts.
"""

import argparse
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

from PIL import Image, ImageDraw, ImageFont

# -- THE INVENTORY. Fixed order. This defines what "number 34" means. ---------
#
# Grouped so a person can scan one section at a time, and so a wrong letter is
# reported as "34" rather than needing to be described in words.

VOWELS = "अआइईउऊऋएऐओऔ"
MATRAS = "ािीुूृेैोौंःँ"
CONSONANTS = ("कखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसह"
              "ळक्षज्ञ")
CONJUNCTS = "क्षत्रज्ञश्र"
DIGITS = "०१२३४५६७८९"
PUNCT = "।॥ऽ"

GROUPS = [
    ("Vowels (varna)", VOWELS),
    ("Matras (matra)", MATRAS),
    ("Consonants (anya)", CONSONANTS),
    ("Conjuncts -- NEEDS CHROMIUM", CONJUNCTS),
    ("Digits (ankhya)", DIGITS),
    ("Punctuation", PUNCT),
]


def build_inventory():
    """[(number, group, character, needs_chromium)] -- the stable numbering."""
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


def catalogue():
    p = os.path.join(ROOT, "sweep.json")
    with io.open(p, encoding="utf-8") as fh:
        return {e["slug"]: e for e in json.load(fh)}


def find_ttf(slug):
    fdir = os.path.join(ROOT, "fonts", slug)
    if not os.path.isdir(fdir):
        return None
    ttfs = [f for f in sorted(os.listdir(fdir)) if f.lower().endswith((".ttf", ".otf"))]
    return os.path.join(fdir, ttfs[0]) if ttfs else None


def keys_for(ch, layout_name):
    """The string to hand the FONT, so it draws `ch` itself.

    A Preeti-era font has no Devanagari cmap at all, so it must be given its own
    key sequence -- verified: pawang maps 183 codepoints and not one is in
    U+0900..U+097F. Drawing the Devanagari codepoint would show a fallback face
    and say nothing about the font, which is the mistake that made `abhinav` look
    fine to a round-trip check and wrong on screen.

    Returns (draw_this, is_converted).
    """
    if layout_name is None:
        return ch, False
    from lrc_legacy import convert_line
    keys = convert_line(ch, layout_name)
    return keys, True


def draw(path, rows, out, title, subtitle, font_size=64):
    """rows: [(number, group, character, needs_chromium, text_to_draw)]"""
    COLS = 8
    LABEL_W, HEAD_H, CELL_H = 74, 92, 104
    n = len(rows)
    grid_rows = (n + COLS - 1) // COLS
    W = LABEL_W + COLS * CELL_H
    H = HEAD_H + grid_rows * CELL_H + 40
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)

    # Labels and title in a font that definitely has ASCII. Not the font under
    # test: a number drawn in a broken font is unreadable, and the number is the
    # one thing that must never be ambiguous.
    ui = ImageFont.load_default()
    try:
        ui_big = ImageFont.truetype("arial.ttf", 22)
        ui_num = ImageFont.truetype("arialbd.ttf", 26)
    except OSError:
        ui_big = ui_num = ui

    d.text((14, 14), title, font=ui_big, fill="black")
    d.text((14, 44), subtitle, font=ui, fill=(70, 70, 70))
    d.text((14, 62), "Number each letter. Tell me which numbers are wrong.",
           font=ui, fill=(0, 90, 0))
    d.line([(0, HEAD_H - 8), (W, HEAD_H - 8)], fill=(200, 200, 200))

    fnt = ImageFont.truetype(path, font_size)
    # The character to DRAW is whatever the font must be handed, which for a
    # legacy font is its own key sequence and not the Devanagari codepoint. The
    # first version drew the codepoint, so all 89 cells came out as .notdef
    # boxes -- a sheet that looked like a font with no letters at all, and would
    # have been read as "this font is broken" for every font tested.
    for n, group, ch, needs_chromium, draw_text in rows:
        i = n - 1
        x = LABEL_W + (i % COLS) * CELL_H
        y = HEAD_H + (i // COLS) * CELL_H
        d.rectangle([x, y, x + CELL_H - 1, y + CELL_H - 1], outline=(215, 215, 215))
        d.text((x + 6, y + 30), str(n), font=ui_num, fill=(190, 30, 30))
        if needs_chromium:
            d.text((x + 6, y + 56), "chromium", font=ui, fill=(150, 150, 150))
        d.text((x + CELL_H // 2, y + 46), draw_text, font=fnt, fill="black", anchor="mm")

    d.line([(0, H - 34), (W, H - 34)], fill=(200, 200, 200))
    d.text((14, H - 24), "Groups: 1-%d vowels | %d-%d matras | %d-%d consonants | "
                         "%d-%d conjuncts | %d-%d digits | %d-%d punctuation"
          % (len(VOWELS),
             len(VOWELS) + 1, len(VOWELS) + len(MATRAS),
             len(VOWELS) + len(MATRAS) + 1, len(VOWELS) + len(MATRAS) + len(CONSONANTS),
             len(VOWELS) + len(MATRAS) + len(CONSONANTS) + 1,
             len(VOWELS) + len(MATRAS) + len(CONSONANTS) + len(CONJUNCTS),
             len(VOWELS) + len(MATRAS) + len(CONSONANTS) + len(CONJUNCTS) + 1,
             len(VOWELS) + len(MATRAS) + len(CONSONANTS) + len(CONJUNCTS) + len(DIGITS),
             len(VOWELS) + len(MATRAS) + len(CONSONANTS) + len(CONJUNCTS) + len(DIGITS) + 1,
             n),
          font=ui, fill=(70, 70, 70))
    img.save(out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", help="a font slug from this repo")
    ap.add_argument("--font-file", help="a .ttf directly")
    ap.add_argument("--class", dest="cls", help="PREETI | UNICODE | GENERATED")
    ap.add_argument("--out", help="output .png (default: out/letter-<slug>.png)")
    ap.add_argument("--only", help="a comma-separated list of numbers")
    ap.add_argument("--through-chromium", action="store_true",
                    help="render via lyric-studio (correct for conjuncts, slower)")
    args = ap.parse_args()

    if not args.slug and not args.font_file:
        ap.error("give --slug or --font-file")

    cls = args.cls
    ttf = args.font_file
    if args.slug:
        cat = catalogue()
        row = cat.get(args.slug)
        if row is None:
            sys.exit("  no font %r in sweep.json" % args.slug)
        cls = cls or row.get("class")
        ttf = ttf or find_ttf(args.slug)
        if not ttf or not os.path.exists(ttf):
            sys.exit("  no .ttf for %s under fonts/%s/\n"
                     "  Download it:  py scripts/fetch_fonts.py" % (args.slug, args.slug))
    else:
        cls = cls or "PREETI"
    if not os.path.exists(ttf):
        sys.exit("  no such font file: " + ttf)

    out = args.out or os.path.join(ROOT, "out", "letter-%s.png" % (args.slug or "font"))
    os.makedirs(os.path.dirname(out), exist_ok=True)

    layout_name = None if cls == "UNICODE" else (
        "Preeti" if cls == "PREETI" else args.slug)

    if args.only:
        wanted = {int(x) for x in args.only.replace(" ", "").split(",") if x}
        unknown = wanted - set(BY_NUMBER)
        if unknown:
            sys.exit("  no such number(s): %s  (1..%d)" % (sorted(unknown), len(INVENTORY)))
        chosen = [r for r in INVENTORY if r[0] in wanted]
    else:
        chosen = INVENTORY

    # Attach the text the FONT must be given, not the codepoint a person reads.
    rows = [(n, g, ch, needs, keys_for(ch, layout_name)[0])
            for n, g, ch, needs in chosen]
    converted = sum(1 for r in rows if r[4] != r[2])

    title = "letter sheet -- %s  (%s)" % (args.slug or os.path.basename(ttf), cls)
    sub = "%s   |   %d letters   |   %d need Chromium for conjuncts" % (
        os.path.basename(ttf), len(INVENTORY), len(CONJUNCTS))
    if cls != "UNICODE":
        sub += "   |   drawn via %s keys" % (layout_name or "its own layout")
    draw(ttf, rows, out, title, sub)

    print("  %s" % out)
    print("  %d letters, numbered 1..%d, stable across every sheet" % (len(rows), len(INVENTORY)))
    if cls != "UNICODE":
        print("  %d of the drawn letters go through the %s transform"
              % (converted, layout_name))
    print("")
    print("  READ THE NUMBERS, not the letters. Tell me the numbers that are wrong,")
    print("  e.g. '34, 51 are wrong'. I record them against this font in verdicts.json")
    print("  and try to fix the cause.")
    if not args.through_chromium:
        print("")
        print("  NOTE: the %d conjuncts (%s) are NOT reliable in this sheet -- Pillow on"
              % (len(CONJUNCTS), ", ".join(CONJUNCTS)))
        print("  this machine has no libraqm, so it draws their component letters in")
        print("  order instead of shaping them. Add --through-chromium to see them")
        print("  properly. Isolate and matra rows ARE trustworthy here.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
