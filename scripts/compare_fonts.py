"""compare_fonts.py -- several fonts side by side, grouped by letter class.

    py scripts/compare_fonts.py                    # every font, letters
    py scripts/compare_fonts.py --words            # real words instead
    py scripts/compare_fonts.py --state working    # just the proven ones
    py scripts/compare_fonts.py --only arya,kalam  # a subset
    py scripts/compare_fonts.py --page 2           # next 16 columns

WHY A COMPARISON AND NOT MORE LETTER SHEETS
-------------------------------------------
A letter sheet answers "is this font CORRECT". It cannot answer "which of these
do I want", because that is a judgement about weight, colour and rhythm across
a whole face, and you cannot hold seven sheets in your head at once. So this puts
them in one image, one column per letter, sharing a baseline -- which is the only
way the differences are actually visible.

COLUMNS ARE GROUPED, WITH HEADINGS
---------------------------------
Vowels, then matras, then consonants, then conjuncts, then digits, then
punctuation -- each under its own banner. The grouping is not decoration: the
classes fail in different ways, and a reader who knows that can skip most of the
sheet. Matras are marks that only look right beside a base letter, so a lone
mark in that column is expected rather than a fault. Conjuncts cannot be shaped
by Pillow on this machine and are drawn from the components. Digits and
punctuation fail wholesale or not at all.

The inventory and this grouping are the SAME lists as letter_sheet.py, imported
rather than copied, so a letter cannot be numbered one way in one sheet and
another way here.

ROWS COME FROM verdicts.json
----------------------------
Grouped by verdict -- working, then untested, then broken -- so a font is never
presented as a candidate while the data calls it unusable. A broken font is still
shown, because each has a specific recorded reason and seeing it is the fastest
way to confirm that reason by eye.

HOW TO READ IT
--------------
    COLUMN  = one letter across every font. This is the comparison.
    ROW     = one font's whole range. This is the character.
"""

import argparse
import glob
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

import letter_sheet as LS

# Words, for judging a face in running text rather than in isolation. Chosen for
# what breaks: a pre-base i-matra (नि), conjuncts, a candrabindu (सँगै), a
# virama, and the punctuation-heavy lines this genre actually uses.
WORDS = ["जाऊ", "फर्केर", "नलाऊ", "हावा", "सँगै", "आउँछु", "झुट्टो",
         "मेरो", "नेपाल", "रिसले", "किस्तो", "भएको"]

WORD_GROUP = ("Words", WORDS)

# label, characters -- imported from letter_sheet so the two can never disagree
LETTER_GROUPS = [
    ("VOWELS  (varna)", LS.VOWELS),
    ("MATRAS  (matra)", LS.MATRAS),
    ("CONSONANTS  (anya)", LS.CONSONANTS),
    ("CONJUNCTS  -- not shaped here", LS.CONJUNCTS),
    ("DIGITS  (ankhya)", LS.DIGITS),
    ("PUNCTUATION", LS.PUNCT),
]

PAGE = 16


def load_verdicts():
    with io.open(os.path.join(ROOT, "verdicts.json"), encoding="utf-8") as fh:
        return json.load(fh)


def ttf_for(slug):
    hits = (glob.glob(os.path.join(ROOT, "fonts", slug, "*.ttf"))
            + glob.glob(os.path.join(ROOT, "fonts", slug, "*.TTF"))
            + glob.glob(os.path.join(ROOT, "fonts", slug, "*.otf")))
    return hits[0] if hits else None


def layout_name_for(cls, slug):
    if cls == "UNICODE":
        return None
    return "Preeti" if cls == "PREETI" else slug


def render_item(slug, cls, item):
    """(string_to_draw, error_or_None)."""
    ttf = ttf_for(slug)
    if not ttf:
        return None, "no binary"
    name = layout_name_for(cls, slug)
    if name is None:
        return item, None
    from lrc_legacy import convert_line
    try:
        keys = convert_line(item, name)
    except Exception:
        return item, None
    if any(ord(c) > 0x7F for c in keys):
        return keys, "no key"
    try:
        f = TTFont(ttf, fontNumber=0)
        cps = set()
        for t in f["cmap"].tables:
            cps.update(t.cmap)
        if any(ord(c) not in cps for c in keys if c.strip()):
            return keys, "no glyph"
    except Exception:
        pass
    return keys, None


def build_rows(v, only, state_filter):
    order = {"working": 0, "untested": 1, "broken": 2, "failed": 3}
    rows = []
    for slug, row in v.get("verdicts", {}).items():
        st = row.get("state", "untested")
        if only and slug not in only:
            continue
        if state_filter and st not in state_filter:
            continue
        if not ttf_for(slug):
            continue
        rows.append((slug, row.get("look") or "", slug,
                     row.get("class"), st))
    rows.sort(key=lambda r: (order.get(r[4], 9), r[0]))
    return rows


def columns_for(args):
    """[(group_label, [items])] for the requested page."""
    if args.words:
        groups = [WORD_GROUP]
    else:
        groups = list(LETTER_GROUPS)

    flat = []
    for label, chars in groups:
        for ch in chars:
            flat.append((label, ch))

    if args.page > 1:
        start = (args.page - 1) * PAGE
        flat = flat[start:start + PAGE]
    elif len(flat) > PAGE and not args.all:
        flat = flat[:PAGE]
    return groups, flat


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated slugs")
    ap.add_argument("--state", help="comma-separated states")
    ap.add_argument("--words", action="store_true", help="real words, not letters")
    ap.add_argument("--page", type=int, default=1, help="which 16 columns")
    ap.add_argument("--all", action="store_true", help="every column, one wide image")
    ap.add_argument("--out")
    ap.add_argument("--size", type=int, default=38)
    args = ap.parse_args()

    v = load_verdicts()
    only = set(x.strip() for x in args.only.split(",")) if args.only else None
    states = set(x.strip() for x in args.state.split(",")) if args.state else None

    ref_path, ref_index = LS.reference_path()
    if not ref_path:
        sys.exit("  no reference Devanagari face found; install Nirmala UI")

    rows = build_rows(v, only, states)
    if not rows:
        sys.exit("  no fonts matched -- check --only / --state")

    groups, cols = columns_for(args)
    if not cols:
        sys.exit("  page %d is past the end" % args.page)

    LABEL_W, CELL_W, CELL_H = 176, 128, 70
    BAND_H = 26
    # The distinct group labels on this page, in the order they appear. The
    # inventory is grouped, so a page usually cuts across one or two groups and
    # a banner is drawn each time the label changes.
    band_seq = []
    for lab, _c in cols:
        if not band_seq or band_seq[-1] != lab:
            band_seq.append(lab)

    BAND_TOP = 96
    extra_bands = max(0, len(band_seq) - 1) * BAND_H
    H = BAND_TOP + extra_bands + len(rows) * CELL_H + 86
    W = LABEL_W + len(cols) * CELL_W

    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    ui = ImageFont.load_default()
    try:
        ui_t = ImageFont.truetype("arial.ttf", 20)
        ui_b = ImageFont.truetype("arialbd.ttf", 16)
        ui_s = ImageFont.truetype("arial.ttf", 14)
        ui_n = ImageFont.truetype("arialbd.ttf", 18)
        ui_g = ImageFont.truetype("arialbd.ttf", 15)
    except OSError:
        ui_t = ui_b = ui_s = ui_n = ui_g = ui

    # The reference face, loaded FIRST because the column headers are drawn in
    # it. Headers used to be drawn in arialbd, which has no Devanagari, so every
    # column title came out as a .notdef box and the sheet was unusable: you
    # could not tell which column was which letter, and the red colour made the
    # boxes look deliberate.
    ref_f = ImageFont.truetype(ref_path, args.size, index=ref_index)

    what = "words" if args.words else "letters"
    d.text((14, 10), "font comparison -- %s" % what, font=ui_t, fill="black")
    d.text((14, 38), "%d fonts, rows from verdicts.json   |   columns %d-%d of the "
                     "inventory" % (len(rows) + 1, 1, len(cols)), font=ui_s,
           fill=(70, 70, 70))
    d.text((14, 56), "Read a COLUMN to compare one letter across fonts. "
                     "Read a ROW to see one font's character.", font=ui_s,
           fill=(0, 90, 0))
    d.text((14, 74), "Grey row = the reference. A legacy font is handed its own "
                     "key sequence, which is what the video shows.", font=ui_s,
           fill=(120, 120, 120))

    # group banners across the columns each group occupies
    ytop = BAND_TOP
    prev = None
    for i, (lab, ch) in enumerate(cols):
        if lab != prev:
            if prev is not None:
                d.line([(0, ytop - 4), (W, ytop - 4)], fill=(205, 205, 205))
            x0 = LABEL_W + i * CELL_W
            d.text((x0 + 6, ytop + 4), lab, font=ui_g, fill=(150, 60, 0))
            ytop += BAND_H
            prev = lab
        # The column header is a DEVANAGARI LETTER, so it must be drawn in a
        # Devanagari face. It used to be drawn in arialbd, which has no
        # Devanagari, so every header came out as a .notdef box and the whole
        # sheet was unusable -- you could not tell which column was which
        # letter. The red colour made it look deliberate.
        d.text((LABEL_W + i * CELL_W + CELL_W // 2, ytop - 16), ch,
               font=ref_f, fill=(190, 30, 30), anchor="mm")
    d.line([(0, ytop - 4), (W, ytop - 4)], fill=(205, 205, 205))

    STATE_INK = {"working": (0, 110, 0), "untested": (170, 110, 0),
                 "broken": (180, 0, 0), "failed": (120, 120, 120),
                 "reference": (120, 120, 120)}

    # reference row
    body = [("reference", "Nirmala / Yantramanav", "reference", ref_f,
             [c for _l, c in cols], None)]
    for slug, look, _s, cls, st in rows:
        ttf = ttf_for(slug)
        try:
            fnt = ImageFont.truetype(ttf, args.size)
        except Exception:
            fnt = None
        vals, err = [], None
        for _lab, ch in cols:
            s, e = render_item(slug, cls, ch)
            vals.append(s if s else ch)
            if e and not err:
                err = e
        body.append((slug, look, st, fnt, vals, err))

    y0 = ytop + 10
    for r, (label, look, st, fnt, vals, err) in enumerate(body):
        y = y0 + r * CELL_H
        d.rectangle([0, y, W - 1, y + CELL_H - 1],
                    outline=(228, 228, 228) if r else (180, 180, 180))
        ink = STATE_INK.get(st, (0, 0, 0))
        d.text((10, y + 9), label, font=ui_b, fill=ink)
        if look:
            d.text((10, y + 29), look[:21], font=ui_s, fill=(135, 135, 135))
        d.text((10, y + 47), st.upper(), font=ui_s, fill=ink)
        for c in range(len(cols)):
            x = LABEL_W + c * CELL_W
            d.line([(x, y), (x, y + CELL_H - 1)], fill=(242, 242, 242))
            if fnt is None:
                d.text((x + CELL_W // 2, y + CELL_H // 2), "no font",
                       font=ui_s, fill=(190, 0, 0), anchor="mm")
            else:
                d.text((x + CELL_W // 2, y + CELL_H // 2), vals[c], font=fnt,
                       fill="black" if r else (135, 135, 135), anchor="mm")

    y = y0 + len(body) * CELL_H + 10
    d.line([(0, y), (W, y)], fill=(200, 200, 200))
    notes = [
        "Rows are ordered by verdict: WORKING, then UNTESTED, then BROKEN. A font is",
        "never shown as a candidate while the data calls it unusable -- it is marked.",
        "'no key' means the encoder has no mapping, so the Devanagari codepoint is",
        "passed through and the font draws nothing. That is a table bug, not a font",
        "bug, and every Preeti font does it identically -- which is how you tell.",
        "'no glyph' means the key was produced and the font has no outline there.",
    ]
    ny = y + 8
    for line in notes:
        d.text((14, ny), line, font=ui_s, fill=(80, 80, 80))
        ny += 15
    if not args.all and len(cols) >= PAGE:
        d.text((14, ny + 4), "next columns:  py scripts\\compare_fonts.py --page %d"
               % (args.page + 1), font=ui_s, fill=(0, 90, 0))

    out = args.out or os.path.join(ROOT, "out", "compare-%s%s.png"
                                   % (what, "" if args.page == 1 else "-p%d" % args.page))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    img.save(out)
    print("  %s" % out)
    print("  %d fonts x %d %s, page %d" % (len(body), len(cols), what, args.page))
    print("  groups on this page: %s" % ", ".join(band_seq))
    return 0


if __name__ == "__main__":
    sys.exit(main())
