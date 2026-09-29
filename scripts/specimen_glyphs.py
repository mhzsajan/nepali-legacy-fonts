"""Render every glyph in a legacy Nepali font, so the shapes can be looked at.

    py scripts/specimen_glyphs.py <label> <font.ttf> <out.png>

WHY
---
The question this was written to answer: does the font CONTAIN the conjunct
outlines (प्र, स्, हिस्) or only isolated letters? A font with no conjunct
outline cannot be made to draw one by any engine, because there is nothing to
substitute.

The answer turned out to be that the conjuncts ARE in the file, addressed by
ASCII keys -- which is how a Preeti-era font works. The problem is that the
publisher's character table names only 69 slots while the file holds 131 real
glyphs, so the conjuncts are unlabelled and unreachable. See
docs/GLYPH-INVENTORY.md.

Worth knowing before extending this: PowerShell cannot render Devanagari in the
console, so labels print as `?`. The PNG is the reliable output, not stdout.
"""
import sys
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

if len(sys.argv) < 4:
    sys.exit("usage: specimen_glyphs.py <label> <font.ttf> <out.png>")

label, path, out = sys.argv[1], sys.argv[2], sys.argv[3]

f = TTFont(path, fontNumber=0)
order = [g for g in f.getGlyphOrder() if g not in (".notdef", "NULL", "nonmarkingreturn")]

# Reverse the cmap so each glyph can be labelled with what reaches it.
rev = {}
for t in f["cmap"].tables:
    for cp, gn in t.cmap.items():
        rev.setdefault(gn, []).append(cp)


def label_for(gn):
    cps = rev.get(gn)
    if not cps:
        return "(unmapped)"
    best = sorted(cps)[0]
    return chr(best) if 0x20 <= best <= 0x7E else "U+%04X" % best


COLS, CELL, SIZE = 12, 96, 56
rows = (len(order) + COLS - 1) // COLS
img = Image.new("RGB", (COLS * CELL, max(1, rows) * CELL), "white")
d = ImageDraw.Draw(img)
font = ImageFont.truetype(path, SIZE)

for i, gn in enumerate(order):
    x, y = (i % COLS) * CELL, (i // COLS) * CELL
    d.rectangle([x, y, x + CELL - 1, y + CELL - 1], outline=(220, 220, 220))
    d.text((x + CELL // 2, y + CELL // 2 - 4), gn, font=font, fill="black", anchor="mm")
    d.text((x + CELL // 2, y + CELL - 14), label_for(gn),
           font=ImageFont.load_default(), fill=(150, 0, 0), anchor="mm")

img.save(out)
print("  %s: %d glyphs -> %s" % (label, len(order), out))
print("  Devanagari codepoints in cmap: %d"
      % len([c for c in rev if any(0x900 <= x <= 0x97F for x in rev[c])]))
print("  GSUB present: %s   GPOS present: %s" % ("GSUB" in f, "GPOS" in f))
