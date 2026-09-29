"""Render the widest glyphs in a legacy font: the fastest way to spot conjuncts.

    py scripts/specimen_widest.py <label> <font.ttf> <out.png>

WHY WIDTH
---------
A Devanagari conjunct is two or more consonants sharing one shirorekha, so its
outline is markedly wider than a single letter. Sorting by ink advance and
rendering the top 30% surfaces the clusters without having to read all 131
glyphs. In Abhinav this immediately surfaces र्या, ख्याल, स्याल, रवा, ध्य, ज्ञ,
श्र, ह्र, स्र, क्र -- which is how we established that the conjunct outlines
already exist in the file and the real gap is that nothing labels them.

A trap worth naming: the widest glyphs are not *all* conjuncts. Ligature-length
decorative forms and some punctuation sit in the same band, so this narrows the
review to a human-sized list, it does not decide anything.
"""
import sys
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

if len(sys.argv) < 4:
    sys.exit("usage: specimen_widest.py <label> <font.ttf> <out.png>")

label, path, out = sys.argv[1], sys.argv[2], sys.argv[3]
f = TTFont(path, fontNumber=0)
order = [g for g in f.getGlyphOrder() if g not in (".notdef", "NULL", "nonmarkingreturn")]

widths = []
for gn in order:
    try:
        widths.append((f["hmtx"][gn][0], gn))
    except KeyError:
        pass

pct = int(sys.argv[4]) if len(sys.argv) > 4 else 30
widest = {gn for _, gn in sorted(widths, reverse=True)[:max(1, int(len(widths) * pct / 100.0))]}
cols = [gn for _, gn in sorted(widths, key=lambda t: t[1]) if gn in widest]

rev = {}
for t in f["cmap"].tables:
    for cp, gn in t.cmap.items():
        rev.setdefault(gn, set()).add(cp)

COLS, CELL, SIZE = 8, 150, 96
rows = (len(cols) + COLS - 1) // COLS
img = Image.new("RGB", (COLS * CELL, max(1, rows) * CELL), "white")
d = ImageDraw.Draw(img)
fnt = ImageFont.truetype(path, SIZE)

print("  %s: widest %d%% of %d glyphs by ink advance" % (label, pct, len(order)))
for i, gn in enumerate(cols):
    x, y = (i % COLS) * CELL, (i // COLS) * CELL
    d.rectangle([x, y, x + CELL - 1, y + CELL - 1], outline=(210, 210, 210))
    d.text((x + CELL // 2, y + CELL // 2 - 10), gn, font=fnt, fill="black", anchor="mm")
    cps = sorted(rev.get(gn, set()))
    lbl = " ".join(chr(c) if 0x20 <= c <= 0x7E else "U+%04X" % c for c in cps[:2])
    d.text((x + CELL // 2, y + CELL - 16), lbl, font=ImageFont.load_default(),
           fill=(150, 0, 0), anchor="mm")
    print("     %-10s %-14s width=%d" % (gn, lbl, f["hmtx"][gn][0]))

img.save(out)
print("  -> %s" % out)
