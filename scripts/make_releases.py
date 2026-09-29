"""make_releases.py -- build per-class font archives for GitHub Releases.

The repository carries the fonts in git, which is fine for a private repo but
poor for grabbing one class on its own. This packs them into one archive per
class, so a release offers "just the Unicode ones I need for the show"
without a 113 MB clone.

Each archive keeps the per-font folder and its readme, because the readme is
the licence and travels with the archive for a reason. The class name is in
the archive name, so a licence question can be answered before unpacking
rather than after.

Usage:
    py scripts/make_releases.py                 # build into dist/
    py scripts/make_releases.py --class UNICODE # just one
    py scripts/make_releases.py --dest "D:\\downloads"
"""
import argparse
import json
import os
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(HERE, "fonts")
LAYOUTS = os.path.join(HERE, "layouts")
SWEEP = os.path.join(HERE, "sweep.json")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ORDER = ["UNICODE", "PREETI", "GENERATED", "NOTABLE"]
WORKERS = 4

BLURB = {
    "UNICODE": "Renders in Chromium and Remotion as-is. No transcoding, no "
               "layout file. Mostly SIL OFL - check the readme in each folder.",
    "PREETI": "Legacy Preeti fonts. Use --legacy-font with --layout Preeti "
              "(npttf2utf already knows the layout).",
    "GENERATED": "Legacy fonts whose layout nothing knew. Use --legacy-font "
                 "with --layout-file layouts/<slug>.json. Every layout here "
                 "is verified against the real font binary.",
    "NOTABLE": "Legacy fonts, but aNepali publishes no character table for "
               "them, so no layout could be generated. They need a "
               "hand-written map.",
}


def pack(dest, label, slugs, extra_dirs=()):
    """One zip per class, plus the layouts inside the GENERATED archive.

    The layouts go in with the fonts they describe rather than as a separate
    download: a GENERATED font is useless without its map, and shipping them
    apart is how someone ends up rendering Preeti keys into a non-Preeti font.
    """
    path = os.path.join(dest, f"nepali-fonts-{label.lower()}.zip")
    files = 0
    total = 0
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for slug in slugs:
            d = os.path.join(FONTS, slug)
            if not os.path.isdir(d):
                continue
            for root, _dirs, names in os.walk(d):
                for n in sorted(names):
                    if n.lower().endswith((".ttf", ".otf", ".ttc", ".txt", ".md")):
                        full = os.path.join(root, n)
                        rel = os.path.relpath(full, FONTS)
                        z.write(full, rel)
                        files += 1
                        total += os.path.getsize(full)
        for d in extra_dirs:
            for n in sorted(os.listdir(d)):
                full = os.path.join(d, n)
                if os.path.isfile(full):
                    z.write(full, os.path.join(os.path.basename(d), n))
                    files += 1
                    total += os.path.getsize(full)
        # The readme travels with every archive: these are the authors' terms
        # and the reason a font may or may not be usable on a broadcast.
        for name in ("docs/FONTS-DIR.md", "README.md"):
            full = os.path.join(HERE, *name.split("/"))
            if os.path.exists(full):
                z.write(full, name)
    return path, files, total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--class", dest="cls", action="append", choices=ORDER)
    ap.add_argument("--dest", default=os.path.join(HERE, "dist"))
    a = ap.parse_args()

    with open(SWEEP, encoding="utf-8") as f:
        recs = json.load(f)
    by_class = {c: sorted(r["slug"] for r in recs if r["class"] == c) for c in ORDER}

    os.makedirs(a.dest, exist_ok=True)
    want = a.cls or ORDER
    print(f"  packing {len(want)} archive(s) into {a.dest}")

    made = []
    for c in want:
        # GENERATED ships with its layouts; nothing else needs them.
        extra = [LAYOUTS] if c == "GENERATED" else []
        p, n, b = pack(a.dest, c, by_class[c], extra)
        made.append(p)
        print(f"    {os.path.basename(p):<34} {len(by_class[c]):>3} fonts  "
              f"{n:>4} files  {b/1024/1024:>6.1f} MB")
        print(f"        {BLURB[c]}")

    # A layouts-only archive too: the maps are the reusable part of this repo
    # and worth having without 113 MB of fonts.
    lp = os.path.join(a.dest, "nepali-fonts-layouts-only.zip")
    with zipfile.ZipFile(lp, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for n in sorted(os.listdir(LAYOUTS)):
            z.write(os.path.join(LAYOUTS, n), os.path.join("layouts", n))
        z.write(os.path.join(HERE, "docs", "METHOD.md"), "docs/METHOD.md")
    print(f"    {os.path.basename(lp):<34} "
          f"{len(os.listdir(LAYOUTS)):>3} layouts")
    made.append(lp)

    print(f"\n  {len(made)} archive(s) in {a.dest}")
    print("  Upload with:  gh release create v1.0.0 <files> --notes-file <notes>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
