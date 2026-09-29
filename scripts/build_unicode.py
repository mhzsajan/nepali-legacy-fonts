"""Add a Devanagari cmap to a legacy Nepali font, using a generated layout.

A legacy font carries every Devanagari glyph already -- it just has them on
ASCII codepoints, with no Devanagari cmap and no GSUB. The layout files in
`layouts/` are the inverse of that mapping, so they can be turned straight
back into a cmap, and the font becomes usable as a normal Unicode font
(`--font "AMS Manthan"`) with no transcoding and no `--layout-file`.

    py scripts/build_unicode.py --font fonts/ams-manthan/ams.manthan.ttf \
        --layout layouts/ams-manthan.json --out out/ams.manthan.unicode.ttf

What it does and does not cover is documented in docs/UNICODE-REBUILD.md.
"""
import argparse
import json
import os
import sys

from fontTools.ttLib import TTFont


def build(font_path, layout_path, out_path, dry_run=False):
    f = TTFont(font_path)
    with open(layout_path, encoding="utf-8") as fh:
        blob = json.load(fh)
    charmap = blob[next(iter(blob))]["rules"]["character-map"]   # key -> Devanagari

    # Every Unicode subtable, not just one. Chromium on Windows reads (3,1) and
    # fontTools' getBestCmap() prefers it over (0,3), so writing only to (0,3)
    # produces a file that verifies in Python and is still un-mapped in the
    # browser -- the first attempt at this did exactly that, silently.
    targets = [t for t in f["cmap"].tables
               if t.platformID == 0 or (t.platformID == 3 and t.platEncID in (1, 10))]
    if not targets:
        from fontTools.ttLib.tables._c_m_a_p import CmapSubtable
        sub = CmapSubtable.newSubtable(4)
        sub.platformID, sub.platEncID, sub.language, sub.cmap = 3, 1, 0, {}
        f["cmap"].tables.append(sub)
        targets = [sub]

    live = f.getBestCmap() or {}
    direct, composed, unusable = [], [], []
    for key, deva in charmap.items():
        if len(key) != 1:
            # "Aa" -> आ: two glyphs drawn side by side, not one glyph. Needs a
            # composite or a ligature; a cmap entry cannot express it.
            composed.append((key, deva))
            continue
        glyph = live.get(ord(key))
        if not glyph:
            unusable.append((key, deva, "key has no glyph"))
            continue
        if len(deva) != 1:
            composed.append((key, deva))
            continue
        for t in targets:
            t.cmap.setdefault(ord(deva), glyph)
        direct.append((key, deva))

    if not dry_run:
        f.save(out_path)

    return {
        "direct": direct,
        "composed": composed,
        "unusable": unusable,
        "subtables": [(t.platformID, t.platEncID) for t in targets],
        "out": out_path,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--font", required=True, help="legacy .ttf")
    ap.add_argument("--layout", required=True, help="layout json from layouts/")
    ap.add_argument("--out", required=True, help="where to write the Unicode .ttf")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    r = build(a.font, a.layout, a.out, dry_run=a.dry_run)
    size = os.path.getsize(a.out) if not a.dry_run and os.path.exists(a.out) else 0

    print(f"layout entries            : {len(r['direct']) + len(r['composed']) + len(r['unusable'])}")
    print(f"cmap directly convertible : {len(r['direct'])}")
    print(f"needs composition, not cmap: {len(r['composed'])}  "
          f"{[k for k, _ in r['composed'][:8]]}")
    print(f"unusable                  : {len(r['unusable'])}  {r['unusable'][:4]}")
    print(f"subtables written         : {r['subtables']}")
    if not a.dry_run:
        print(f"wrote {a.out} ({size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
