"""fetch_fonts.py -- download font binaries from aNepali to your machine.

WHY THIS EXISTS AND WHY IT IS NOT PART OF THE SWEEP
---------------------------------------------------
aNepali states on its own index: "The fonts presented on this website are
their authors' property, and are either freeware, shareware, demo versions or
public domain. Please look at the readme-files in the archives or check the
indicated author's website for details, and contact him/her if in doubt."

So this repository publishes the LAYOUTS -- derived work describing each
font's own key encoding -- and never the fonts. Downloading them is a
separate, deliberate step you run for the ones you actually want, into a
folder you keep out of version control.

THE DOWNLOAD NAME IS NOT THE SLUG
---------------------------------
The site's file names are the display name with spaces replaced by
underscores, and they do not follow the slug:

    ams-manthan        -> AMS_Manthan.zip
    ananda-fanko-2     -> Ananda_Fanko_2.zip
    0012-arap-bi       -> 0012_ARAP_BI.zip
    noto-sans-devanagari -> Noto_Sans_Devanagari.zip   (may be absent)

sweep.py reads the real name out of each page, so this script uses that
rather than deriving one. A 404 means the site has no archive for that font,
which is reported rather than guessed around.

Usage:
    py scripts/fetch_fonts.py --list                 # show what is available
    py scripts/fetch_fonts.py ams-manthan abhinav    # get these
    py scripts/fetch_fonts.py --class GENERATED      # get every generated one
    py scripts/fetch_fonts.py --all --dest "E:\\...\\01 Fonts"
"""
import argparse
import io
import json
import os
import sys
import time
import urllib.request
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SWEEP = os.path.join(HERE, "sweep.json")
ASSETS = "https://assets.anepali.com/fonts"
WORKERS = 4
PAUSE = 0.3


def load_sweep():
    if not os.path.exists(SWEEP):
        raise SystemExit("  no sweep.json -- run: py scripts/sweep.py")
    with open(SWEEP, encoding="utf-8") as f:
        return {r["slug"]: r for r in json.load(f)}


def download(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def safe(name):
    return "".join(c for c in name if c.isalnum() or c in " ._-").strip()


def one(slug, rec, dest):
    """Fetch and unpack one font. Returns (slug, note)."""
    import urllib.parse

    zip_name = rec.get("zip")
    if not zip_name:
        return slug, "no .zip on the site"
    url = f"{ASSETS}/{urllib.parse.quote(zip_name)}"
    slugdir = os.path.join(dest, slug)
    os.makedirs(slugdir, exist_ok=True)
    try:
        blob = download(url)
    except Exception as e:
        code = getattr(getattr(e, "response", None), "code", "")
        return slug, f"download failed ({code or type(e).__name__})"
    try:
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            for member in z.namelist():
                # Refuse anything that is not a font or a readme: a zip from
                # the internet is not a place to run things from.
                base = os.path.basename(member)
                low = base.lower()
                if not (low.endswith((".ttf", ".otf", ".ttc", ".txt", ".md"))):
                    continue
                if base.startswith(".") or ".." in member:
                    continue
                with open(os.path.join(slugdir, safe(base)), "wb") as f:
                    f.write(z.read(member))
    except zipfile.BadZipFile:
        return slug, "not a zip (site served something else)"
    time.sleep(PAUSE)
    return slug, "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slugs", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--class", dest="cls", help="UNICODE | PREETI | GENERATED")
    ap.add_argument("--dest", default=os.path.join(HERE, "fonts"))
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()

    recs = load_sweep()

    if a.list:
        for slug, r in sorted(recs.items()):
            print(f"  {r['class']:<10} {slug:<28} {r.get('zip') or '(no zip)'}")
        return 0

    if a.cls:
        want = [s for s, r in recs.items() if r["class"] == a.cls]
    elif a.all:
        want = list(recs)
    elif a.slugs:
        want = [s for s in a.slugs if s in recs]
        missing = [s for s in a.slugs if s not in recs]
        if missing:
            print("  not in the sweep: " + ", ".join(missing))
    else:
        ap.print_help()
        return 1

    os.makedirs(a.dest, exist_ok=True)
    print(f"  downloading {len(want)} fonts to {a.dest}")

    from concurrent.futures import ThreadPoolExecutor

    ok = bad = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for slug, note in ex.map(lambda s: one(s, recs[s], a.dest), want):
            if note == "ok":
                ok += 1
            else:
                bad += 1
                print(f"    {slug:<28} {note}")
    print(f"  done: {ok} ok, {bad} not available")
    print("  These fonts are their authors' property -- check each archive's")
    print("  readme before commercial or broadcast use.")
    return 0


if __name__ == "__main__":
    import urllib.parse  # noqa: E402  (used inside one())

    raise SystemExit(main())
