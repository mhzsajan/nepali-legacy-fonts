"""sweep.py -- build a layout for every font aNepali publishes.

215 font pages is too many to handle by hand, and generating them one at a
time is how subtle per-font differences get missed. This walks the whole
catalogue, classifies each font, and emits a layout for the ones that need
one.

WHAT IT DOES PER FONT
---------------------
  * fetches the page (cached, so a re-run costs nothing)
  * reads the character's mapping tag -- preeti / unicode / AMS
  * extracts the .zip name from the page payload
  * classifies:
      UNICODE -> has a Devanagari cmap; renders in Chromium with no work
      PREETI  -> npttf2utf already knows the layout; use --layout Preeti
      GENERATED -> nobody knows the layout; read it off the character table
  * writes layouts/<Slug>.json for the GENERATED ones

FONTS ARE NOT DOWNLOADED
------------------------
The .ttf binaries belong to their authors -- aNepali says so on its own
index: "the fonts presented on this website are their authors' property, and
are either freeware, shareware, demo versions or public domain". This repo
publishes the layouts, which are derived work describing each font's
encoding, and a separate script (fetch_fonts.py) downloads the binaries to
your machine when you want them. Nothing here redistributes a font.

Usage:
    py scripts/sweep.py                 # full sweep, cached
    py scripts/sweep.py --report        # re-read the cache, print the table
    py scripts/sweep.py --only ams-manthan
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from anepali_charmap import (  # noqa: E402
    SITE, build_map, parse_slugs, read_table, slot_order, strip_tags,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(HERE, ".cache")
LAYOUTS = os.path.join(HERE, "layouts")

# Be a good citizen: 6 workers, a short pause between requests. aNepali is a
# free community project and 215 pages is a real amount of traffic.
WORKERS = 6
PAUSE = 0.25


def fetch(url, tries=3, timeout=30):
    for i in range(tries):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0 (nepali-legacy-fonts sweep)"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            if i == tries - 1:
                return f"__ERROR__{e}"
            time.sleep(1.5 * (i + 1))
    return "__ERROR__unknown"


def cached_page(slug, refresh=False):
    """Fetch once, keep the HTML. A sweep that re-downloads 215 pages on every
    run is a sweep nobody runs twice."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"{slug}.html")
    if os.path.exists(path) and not refresh:
        with open(path, encoding="utf-8") as f:
            return f.read()
    html = fetch(f"{SITE}/font/{slug}/")
    if not html.startswith("__ERROR__"):
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
    time.sleep(PAUSE)
    return html


def page_meta(html, slug):
    """Pull the Next.js payload: mapping tag, zip name, style count.

    The download name is not the slug and not always the display name --
    AMS Manthan is AMS_Manthan.zip, ARAP 006 is ARAP__006.zip -- so it is read
    from the page rather than guessed.
    """
    chunks = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', html)
    payload = "".join(chunks).replace("\\n", "").replace('\\"', '"')

    zips = re.findall(r"([A-Za-z0-9_.%\- ]{2,60}\.zip)", payload)
    zip_name = zips[0].strip() if zips else None

    # The mapping tag is rendered as "Character mapping preeti" immediately
    # followed by the Download button, so the naive capture also swallows
    # "download". Bound the word to the tags the site actually uses instead
    # of taking whatever follows.
    mapping = None
    m = re.search(
        r"[Cc]haracter\s*mapping\s*(unicode|preeti|ams|legacy|encoded)",
        strip_tags(html),
        re.I,
    )
    if m:
        mapping = m.group(1).lower()

    # Cross-check, and a fallback where the label is missing: a UNICODE font
    # renders its own characters in the table, so the cells come back as
    # Devanagari. A legacy font's cells are ASCII keys.
    deva_cells = 0
    cells = re.findall(r'<span[^>]*\bfont-' + re.escape(slug) + r'\b[^>]*>(.*?)</span>', html)
    for c in cells:
        if re.search(r"[\u0900-\u097f]", strip_tags(c)):
            deva_cells += 1
    if mapping is None:
        mapping = "unicode" if deva_cells > len(cells) / 2 else "legacy"
    deva_ratio = round(deva_cells / len(cells), 2) if cells else None

    title = None
    m = re.search(r"<title>(.*?)Nepali Font", html)
    if m:
        title = strip_tags(m.group(1)).strip()

    return {"zip": zip_name, "mapping": mapping, "title": title,
            "deva_cell_ratio": deva_ratio}


def classify(meta, tables):
    """UNICODE / PREETI / GENERATED, from the mapping tag the page declares.

    The presence of a character table says nothing: EVERY page has one,
    including Unicode fonts, where the cells are the real Devanagari
    characters the font is already able to draw. So the table proves nothing
    and the tag decides.
    """
    mapping = (meta.get("mapping") or "").lower()
    if mapping == "unicode":
        return "UNICODE", "declared unicode; renders in Chromium with no work"
    if mapping == "preeti":
        return "PREETI", "declared preeti; npttf2utf already has this layout"
    if not tables.get("(Consonants)"):
        # The site publishes no character table for this one, so there is
        # nothing to read a layout from. That is a different situation from a
        # failure -- it needs a human, not a retry -- and calling it GENERATED
        # would produce a layout from nothing.
        return "NOTABLE", "legacy, but the page publishes no character table"
    return "GENERATED", f"declared {mapping or 'unknown'}; layout must be read"


def one(slug, order, refresh=False):
    html = cached_page(slug, refresh)
    if html.startswith("__ERROR__"):
        return {"slug": slug, "class": "ERROR", "why": html[:120]}

    # aNepali answers an unknown slug with HTTP 200 and a "Font Not Found"
    # page, so status alone cannot detect a miss. ams-calligraphy-9 is a real
    # example: it 200s, has no character table, and its actual page is
    # ams-calligraphy-9-2. Cached as a miss, it silently becomes NOTABLE and
    # looks like a font the site simply does not document.
    if re.search(r"<title>\s*Font Not Found", html, re.I):
        return {"slug": slug, "class": "MISSING",
                "why": "soft 404: the site returned a 'Font Not Found' page"}

    meta = page_meta(html, slug)
    tables = read_table(html, slug)
    cls, why = classify(meta, tables)

    rec = {"slug": slug, "class": cls, "why": why, **meta,
           "sections": {k: len(v) for k, v in tables.items()}}

    if cls == "GENERATED":
        try:
            layout, report = build_map(slug, html=html, order=order)
            rec["keys"] = report["keys"]
            rec["problems"] = report["problems"]
            os.makedirs(LAYOUTS, exist_ok=True)
            name = next(iter(layout))
            rec["layout"] = name
            with open(os.path.join(LAYOUTS, f"{slug}.json"), "w", encoding="utf-8") as f:
                json.dump(layout, f, ensure_ascii=False, indent=1)
        except SystemExit as e:
            rec["class"] = "ERROR"
            rec["why"] = f"layout generation failed: {str(e)[:160]}"
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="just these slugs")
    ap.add_argument("--refresh", action="store_true", help="ignore the page cache")
    ap.add_argument("--report", action="store_true", help="print the summary and exit")
    a = ap.parse_args()

    if a.report:
        path = os.path.join(HERE, "sweep.json")
        if not os.path.exists(path):
            print("  no sweep.json yet; run without --report first")
            return 1
        with open(path, encoding="utf-8") as f:
            recs = json.load(f)
    else:
        slugs = a.only or [s for s in parse_slugs(fetch(f"{SITE}/")) if s != "author"]
        print(f"  sweeping {len(slugs)} font pages ({WORKERS} workers, cached)...")
        order = slot_order()
        recs = []
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            futures = {ex.submit(one, s, order, a.refresh): s for s in slugs}
            for i, fut in enumerate(futures, 1):
                rec = fut.result()
                recs.append(rec)
                if i % 25 == 0:
                    print(f"    {i}/{len(slugs)}")
        recs.sort(key=lambda r: r["slug"])
        with open(os.path.join(HERE, "sweep.json"), "w", encoding="utf-8") as f:
            json.dump(recs, f, ensure_ascii=False, indent=1)

    counts = {}
    for r in recs:
        counts[r["class"]] = counts.get(r["class"], 0) + 1

    print(f"\n  {'class':<10} {'count':>6}  meaning")
    print("  " + "-" * 62)
    for k in sorted(counts):
        note = {
            "UNICODE": "renders in Chromium as-is; nothing to do",
            "PREETI": "npttf2utf already knows it; --layout Preeti",
            "GENERATED": "layout read from the page; layouts/<slug>.json",
            "NOTABLE": "legacy, but the site publishes no character table",
            "MISSING": "soft 404 - wrong slug, or not on the site",
            "ERROR": "fetch or generation failed",
        }.get(k, "")
        print(f"  {k:<10} {counts[k]:>6}  {note}")

    gen = [r for r in recs if r["class"] == "GENERATED"]
    if gen:
        nkeys = [r.get("keys", 0) for r in gen]
        withprob = [r for r in gen if r.get("problems")]
        print(f"\n  layouts written: {len(gen)}"
              f"   keys min/median/max: {min(nkeys)}/"
              f"{sorted(nkeys)[len(nkeys)//2]}/{max(nkeys)}")
        print(f"  with reported problems: {len(withprob)}")
        for r in withprob[:10]:
            print(f"    {r['slug']:<26} {r['problems'][:80]}")

    errs = [r for r in recs if r["class"] == "ERROR"]
    if errs:
        print(f"\n  errors: {len(errs)}")
        for r in errs[:10]:
            print(f"    {r['slug']:<26} {r.get('why','')[:90]}")

    nozip = [r for r in recs if r["class"] != "ERROR" and not r.get("zip")]
    if nozip:
        print(f"\n  no .zip name found for {len(nozip)} (cannot auto-download):")
        print("    " + ", ".join(r["slug"] for r in nozip[:12]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
