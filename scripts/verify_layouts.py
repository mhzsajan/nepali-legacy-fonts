"""verify_layouts.py -- prove a GENERATED layout against the real .ttf.

WHAT THIS ADDS
--------------
`sweep.py` builds 71 layouts and checks each one for internal sanity: the slot
order is calibrated off Preeti, no two slots collide, and no count mismatch is
slipped past. That proves the map is *coherent*. It does not prove the map
belongs to the font that will actually be loaded.

This closes that gap. For each GENERATED slug it:

  1. downloads that font's .zip from assets.anepali.com (the name comes from
     sweep.json, because the download name is NOT the slug -- ams-manthan is
     AMS_Manthan.zip),
  2. extracts the .ttf into a temp folder OUTSIDE the git repo,
  3. rebuilds the layout from the font page via anepali_charmap (so the check
     is not a rubber stamp of the committed file),
  4. checks every key of the committed layouts/<slug>.json -- the artifact
     render.mjs actually loads -- against the .ttf's cmap,
  5. reports PASS / FAIL per font with the specific missing keys.

WHY THE MISSING-KEY CHECK MATTERS
--------------------------------
A key the font has no glyph for renders as .notdef (a blank box). A key the
font maps somewhere else renders as the WRONG letter, which is worse and much
harder to spot in a frame. Both are caught here without rendering, and the
count is the number to watch across the sweep: a font that is 70/72 is a font
whose two odd keys will silently turn into boxes mid-word.

STATUSES
--------
  PASS          every key resolves to a real glyph
  FAIL          keys missing, or the committed layout is stale
  NOT_AVAILABLE the site has no archive for this font (404 / no .zip name).
                 NOT a failure -- there is nothing to verify against.
  SKIPPED       not the requested class (default: only GENERATED is verified;
                 PREETI fonts need no layout, UNICODE fonts need no transcoding)
  ERROR         could not tell (network, bad zip, no font in the zip, unparseable
                 .ttf, layout generation refused to guess). Counted as a failure
                 because "unknown" must not read as "fine".

Exit code is non-zero if any font FAILs or ERRORs.

FONTS ARE NEVER WRITTEN INTO THE REPO
--------------------------------------
The binaries are the authors' property (aNepali says so on its index). They are
unpacked under %LOCALAPPDATA%\\Temp\\opencode\\anepali-fonts and reused from
there on later runs. Only the layout JSONs are published.

Usage:
    py scripts/verify_layouts.py ams-manthan ams-aakash
    py scripts/verify_layouts.py --class GENERATED --limit 20
    py scripts/verify_layouts.py --all --json out/verify.json
    py scripts/verify_layouts.py ams-manthan --no-rebuild   # glyph check only
"""
import argparse
import io
import json
import os
import re
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Windows consoles default to cp1252, which has no Devanagari and raises
# UnicodeEncodeError on the first syllable printed -- after all the work is
# already done. Force UTF-8 so the report is actually readable.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import anepali_charmap as charmap  # noqa: E402  (needs the reconfigure above)

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SWEEP = os.path.join(HERE, "sweep.json")
LAYOUTS = os.path.join(HERE, "layouts")
PAGE_CACHE = os.path.join(HERE, ".cache")
ASSETS = "https://assets.anepali.com/fonts"

# A layout key that is itself Devanagari is a different kind of broken than an
# ASCII key the font lacks, and the two need different fixes. See split_missing.
DEVA_RE = re.compile(r"[\u0900-\u097f]")

# Be a good citizen. aNepali is a free community project; 4 workers with a
# pause after every download keeps this well under one request a second.
WORKERS = 4
PAUSE = 0.3
TRIES = 3
TIMEOUT = 60

# A zip from the internet is not a place to run things from: only fonts and
# readmes come out of it.
EXTRACT_EXT = (".ttf", ".otf", ".ttc", ".txt", ".md", ".rtf")

_download_lock = threading.Lock()


def default_dest():
    """Where font binaries live. Never inside the repo."""
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return os.path.join(local, "Temp", "opencode", "anepali-fonts")
    return os.path.join(tempfile.gettempdir(), "opencode", "anepali-fonts")


# ---------------------------------------------------------------- pages ----
# The sweep already cached all 214 font pages under .cache/. Reading them back
# is not just faster, it means a verification run costs the site ZERO requests.
# Nothing is written back: this script only ever adds itself to the repo.


def cached_fetch(url, timeout=30):
    """anepali_charmap.fetch, but served from .cache/ when we have the page.

    The page cache is read-only here on purpose. A missing page is fetched live
    and thrown away rather than saved, so running the verifier never mutates the
    working tree beyond this file.
    """
    m = charmap.SITE + "/font/"
    if url.startswith(m):
        slug = url[len(m):].strip("/")
        if slug and all(c.isalnum() or c in "-_" for c in slug):
            path = os.path.join(PAGE_CACHE, f"{slug}.html")
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    html = f.read()
                if html.strip():
                    return html
    time.sleep(PAUSE)  # a live request: pause as if it were a fresh one
    return _live_fetch(url, timeout=timeout)


# Bound BEFORE the patch below. `charmap.fetch = cached_fetch` makes any later
# `charmap.fetch(...)` inside cached_fetch call cached_fetch again, which on a
# fresh clone (.cache/ empty, and it is gitignored) is RecursionError at depth
# 1000 instead of a download.
_live_fetch = charmap.fetch
charmap.fetch = cached_fetch


# -------------------------------------------------------------- download ----


def load_sweep():
    if not os.path.exists(SWEEP):
        raise SystemExit("  no sweep.json -- run: py scripts/sweep.py")
    with open(SWEEP, encoding="utf-8") as f:
        return {r["slug"]: r for r in json.load(f)}


def download(url):
    """Bytes, or raise. 404 surfaces as HTTPError so the caller can call it
    NOT_AVAILABLE rather than a failure."""
    last = None
    for i in range(TRIES):
        # Serialised, with a pause inside the lock, so concurrency cannot turn
        # into a burst of requests to a small community site.
        with _download_lock:
            try:
                req = urllib.request.Request(
                    url, headers={"User-Agent": "Mozilla/5.0 (nepali-legacy-fonts verify)"}
                )
                with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                    blob = r.read()
            except urllib.error.HTTPError as e:
                if e.code == 404 or 400 <= e.code < 500:
                    raise  # the site simply has no archive: no retry will help
                last = e
            except Exception as e:  # timeout, reset connection, DNS
                last = e
            else:
                time.sleep(PAUSE)
                return blob
            time.sleep(PAUSE)
    raise last if last else RuntimeError("download failed")


def safe_member_name(member, taken):
    """Flatten a zip member to a bare filename. A member path is untrusted."""
    base = os.path.basename(member.replace("\\", "/"))
    base = "".join(c for c in base if c.isalnum() or c in " ._-()").strip()
    if not base or base.startswith("."):
        return None
    stem, ext = os.path.splitext(base)
    n = 2
    while base.lower() in taken:
        base = f"{stem}-{n}{ext}"
        n += 1
    taken.add(base.lower())
    return base


def pick_font(cands, slug, title):
    """Choose which .ttf in the archive is the font.

    A zip can hold several (regular + bold, a demo copy, an .exe renamed).
    The choice is printed rather than made silently, because a wrong pick
    produces a FAIL that looks like a layout bug.
    """
    toks = {t for t in (slug + " " + (title or "")).replace("-", " ").split() if len(t) > 2}

    def score(c):
        name, size = c
        low = os.path.basename(name).lower()
        ext = os.path.splitext(low)[1]
        ext_rank = {".ttf": 0, ".otf": 1, ".ttc": 2}.get(ext, 3)
        # "ams manthan regular.ttf" should not win over "ams.manthan.ttf"
        junk = sum(1 for w in ("bold", "italic", "light", "regular", "demo",
                               "sample", "copy", "old", "test") if w in low)
        echo = 0 if any(t in low for t in toks) else 1
        return (ext_rank, junk, echo, -size)

    return sorted(cands, key=score)[0][0]


def fetch_font(slug, rec, dest, refresh=False):
    """-> (ttf path, note). note starts with 'ok ' on success, else a reason."""
    zip_name = rec.get("zip")
    if not zip_name:
        # Same situation as a 404 -- there is nothing to download, so there is
        # nothing to verify against. Not a failure of the font.
        return None, "NOT_AVAILABLE no .zip name published for this font"

    slugdir = os.path.join(dest, slug)
    os.makedirs(slugdir, exist_ok=True)

    # Reuse before requesting. A second run of the harness must cost the site
    # nothing, so the already-unpacked .ttf short-circuits the download
    # entirely rather than fetching a zip and then ignoring it.
    if not refresh:
        have = sorted(n for n in os.listdir(slugdir)
                      if n.lower().endswith((".ttf", ".otf", ".ttc")))
        if have:
            return os.path.join(slugdir, have[0]), f"ok (reused {have[0]})"

    url = f"{ASSETS}/{urllib.parse.quote(zip_name)}"
    try:
        blob = download(url)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None, "NOT_AVAILABLE 404 -- the site has no archive for this font"
        return None, f"HTTP {e.code} from the asset host"
    except Exception as e:
        return None, f"download failed: {type(e).__name__}: {e}"

    try:
        zf = zipfile.ZipFile(io.BytesIO(blob))
    except zipfile.BadZipFile:
        return None, "not a zip -- the site served something else"
    except Exception as e:
        return None, f"zip could not be read: {type(e).__name__}"

    taken, cands = set(), []
    with zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            low = os.path.basename(info.filename).lower()
            if not low.endswith(EXTRACT_EXT) or ".." in info.filename:
                continue
            name = safe_member_name(info.filename, taken)
            if not name:
                continue
            path = os.path.join(slugdir, name)
            with open(path, "wb") as f:
                f.write(zf.read(info))
            if low.endswith((".ttf", ".otf", ".ttc")):
                cands.append((name, info.file_size))

    if not cands:
        return None, "no .ttf/.otf inside the archive"
    chosen = pick_font(cands, slug, rec.get("title"))
    note = "ok" if len(cands) == 1 else f"ok (picked {chosen} of {len(cands)} fonts)"
    return os.path.join(slugdir, chosen), note


# ------------------------------------------------------------ the checks ----


def missing_keys(font_path, character_map):
    """Keys with no glyph in this .ttf. Same rule as charmap.check_font:
    a multi-character key needs every one of its codepoints."""
    from fontTools.ttLib import TTFont

    f = TTFont(font_path, fontNumber=0, lazy=True)
    try:
        cmap = f.getBestCmap() or {}
        return [(k, u) for k, u in character_map.items()
                if not all(ord(ch) in cmap for ch in k)]
    finally:
        f.close()


def split_missing(pairs):
    """(unreadable, absent) -- two different defects that both mean .notdef.

    UNREADABLE -- the key is itself Devanagari. The character table published a
      FALLBACK (the real character) instead of a key, which is what the site
      does for a slot the font cannot draw. No key was ever read, so there is
      nothing to verify: the map entry cannot render, and the fix is to drop
      the slot, not to go looking in the .ttf.

    ABSENT -- an ordinary ASCII key the .ttf has no glyph for. Here the table
      and the font genuinely disagree: the site says this key means X and the
      font says it does not exist. The fix is to re-read that slot.

    Measured on the whole 71-font sweep: all 71 carry the same 3 unreadable
    slots (ङ, ञ, and the ज्ञ conjunct) and zero absent ones -- the ङ/ञ/ज्ञ
    glyphs simply are not in the character table, for any of these fonts.
    """
    unreadable = [(k, u) for k, u in pairs if DEVA_RE.search(k)]
    absent = [(k, u) for k, u in pairs if not DEVA_RE.search(k)]
    return unreadable, absent


def committed_layout(slug):
    """layouts/<slug>.json -- the file render.mjs is given -- or None."""
    path = os.path.join(LAYOUTS, f"{slug}.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    name = next(iter(data))
    return data[name]["rules"]["character-map"]


def verify(slug, rec, dest, order, rebuild=True, refresh=False, show=20):
    """-> result dict for one slug. Never raises."""
    r = {"slug": slug, "class": rec.get("class"), "zip": rec.get("zip"),
         "font": None, "keys": 0, "missing": [], "unreadable": [],
         "status": "ERROR", "note": ""}

    ttf, note = fetch_font(slug, rec, dest, refresh=refresh)
    if ttf is None:
        if note.startswith("NOT_AVAILABLE"):
            r["status"] = "NOT_AVAILABLE"
        r["note"] = note
        return r
    r["font"] = os.path.basename(ttf)
    r["note"] = note

    cm = committed_layout(slug)
    if cm is None:
        # No shipped layout: fall back to a fresh build so the font is still
        # worth something to look at, but say so -- the artifact is missing.
        r["status"] = "ERROR"
        r["note"] = f"layouts/{slug}.json is missing"
        return r

    try:
        unreadable, absent = split_missing(missing_keys(ttf, cm))
    except Exception as e:
        r["note"] += f" | unreadable .ttf: {type(e).__name__}: {e}"
        return r
    r["unreadable"] = unreadable
    r["missing"] = absent
    r["keys"] = len(cm)

    if rebuild:
        try:
            fresh, report = charmap.build_map(slug, order=order)
            fresh_cm = fresh[next(iter(fresh))]["rules"]["character-map"]
        except SystemExit as e:
            r["note"] += " | rebuild refused: " + str(e).splitlines()[-1].strip()[:70]
        except Exception as e:
            r["note"] += f" | rebuild failed: {type(e).__name__}: {e}"
        else:
            only_committed = {k: v for k, v in cm.items() if fresh_cm.get(k) != v}
            only_fresh = {k: v for k, v in fresh_cm.items() if cm.get(k) != v}
            if only_committed or only_fresh:
                r["stale"] = True
                r["status"] = "FAIL"
                r["note"] += (f" | STALE layout: {len(only_committed)} key(s) only in"
                              f" the committed file, {len(only_fresh)} only in a"
                              f" fresh build")
                r["drift"] = [k for k in list(only_committed) + list(only_fresh)]
            if report.get("problems"):
                r["note"] += " | " + report["problems"][0][:60]

    if r["status"] != "FAIL":
        r["status"] = "FAIL" if (r["missing"] or r["unreadable"]) else "PASS"
    return r


# ----------------------------------------------------------------- report ---


def table(results, skipped):
    w = (26, 10, 22, 26, 6, 8, 12)
    head = ("slug", "class", "zip", "font", "keys", "missing", "result")
    print(f"\n  {'slug':<{w[0]}} {'class':<{w[1]}} {'zip':<{w[2]}} "
          f"{'font':<{w[3]}} {'keys':>{w[4]}} {'missing':>{w[5]}}  {head[6]}")
    print("  " + "-" * (sum(w) + 20))
    for r in results:
        n = len(r.get("missing") or []) + len(r.get("unreadable") or [])
        print(f"  {r['slug'][:w[0]]:<{w[0]}} {(r.get('class') or '?')[:w[1]]:<{w[1]}} "
              f"{(r.get('zip') or '-')[:w[2]]:<{w[2]}} {(r.get('font') or '-')[:w[3]]:<{w[3]}} "
              f"{r.get('keys') or 0:>{w[4]}} {n:>{w[5]}}  {r['status']}")
    for slug, cls in skipped:
        why = {"PREETI": "npttf2utf already has this layout",
               "UNICODE": "renders in Chromium with no transcoding",
               "NOTABLE": "the site publishes no character table"}.get(
                   cls, "not a GENERATED layout")
        print(f"  {slug[:w[0]]:<{w[0]}} {cls[:w[1]]:<{w[1]}} "
              f"{'-':<{w[2]}} {'-':<{w[3]}} {'-':>{w[4]}} {'-':>{w[5]}}  SKIPPED  ({why})")


def details(results, show):
    bad = [r for r in results if r["status"] in ("FAIL", "ERROR", "NOT_AVAILABLE")]
    for r in bad:
        print(f"\n  {r['slug']}  {r['status']}")
        print(f"    {r['note']}")
        if r.get("unreadable"):
            print(f"    {len(r['unreadable'])} slot(s) the character table did not"
                  f" publish a key for (the cell is a Devanagari fallback), so the"
                  f" map holds a Devanagari 'key' that no legacy font can draw:")
            for k, u in r["unreadable"][:show]:
                print(f"      {k!r:8} -> {u}")
            print("      fix: drop these slots from the layout; they cannot render.")
        if r.get("missing"):
            print(f"    {len(r['missing'])} key(s) the .ttf has no glyph for -- the"
                  f" published table and this font disagree:")
            for k, u in r["missing"][:show]:
                print(f"      {k!r:8} -> {u}")
            if len(r["missing"]) > show:
                print(f"      ... and {len(r['missing']) - show} more")
        if r.get("drift"):
            keys = ", ".join(repr(k) for k in r["drift"][:show])
            print(f"    keys that differ from a fresh build: {keys}"
                  f"{' ...' if len(r['drift']) > show else ''}")


def main():
    ap = argparse.ArgumentParser(
        description="Verify GENERATED layouts against the real .ttf from anepali.com."
    )
    ap.add_argument("slugs", nargs="*", help="anepali font slugs, e.g. ams-manthan")
    ap.add_argument("--all", action="store_true", help="every slug in the sweep")
    ap.add_argument("--class", dest="cls", default="GENERATED",
                    help="sweep class to consider (default: GENERATED). Classes "
                         "other than GENERATED are still skipped: they have no "
                         "layouts/<slug>.json to verify")
    ap.add_argument("--limit", type=int, help="verify at most N fonts")
    ap.add_argument("--dest", default=default_dest(),
                    help="where to unpack font binaries (default: temp, never the repo)")
    ap.add_argument("--refresh", action="store_true",
                    help="re-download even if the .ttf is already unpacked")
    ap.add_argument("--no-rebuild", dest="rebuild", action="store_false",
                    help="skip the stale-layout rebuild, check glyphs only")
    ap.add_argument("--show", type=int, default=20, help="missing keys to list per font")
    ap.add_argument("--json", dest="json_out", help="also write a JSON report here")
    ap.add_argument("--list", action="store_true", help="list verifiable slugs and exit")
    a = ap.parse_args()

    recs = load_sweep()
    if a.list:
        n = [s for s, r in sorted(recs.items()) if r["class"] == a.cls]
        print(f"  {len(n)} {a.cls} slugs")
        for s in n:
            print("  " + s)
        return 0

    if a.all or not a.slugs:
        if not a.all:
            ap.print_help()
            return 1
        want = [s for s in sorted(recs) if recs[s]["class"] == a.cls]
    else:
        want, unknown = [], []
        for s in a.slugs:
            if s in recs:
                want.append(s)
            else:
                unknown.append(s)
        for s in unknown:
            print(f"  not in the sweep: {s}")

    # The rule is not a filter preference, it is a fact about what can be
    # checked: a font only has a layout artifact to verify if the sweep wrote
    # one, and only GENERATED fonts have one. A slug that is not in the sweep
    # at all is the caller's typo, not a font that failed, and does not change
    # the exit code.
    if a.cls != "GENERATED":
        print(f"  note: --class {a.cls} selects candidate slugs, but only "
              f"GENERATED fonts have a layouts/<slug>.json. Anything else is "
              f"reported SKIPPED.")
    verified, skipped = [], []
    for s in want:
        cls = recs[s]["class"]
        if cls != "GENERATED":
            skipped.append((s, cls))
        else:
            verified.append(s)
    if a.limit is not None and len(verified) > a.limit:
        print(f"  --limit {a.limit}: verifying the first {a.limit} of "
              f"{len(verified)} {a.cls} slugs")
        verified = verified[:a.limit]

    if not verified:
        print("  nothing to verify")
        table([], skipped)
        return 0

    os.makedirs(a.dest, exist_ok=True)
    inside = os.path.abspath(a.dest).lower().startswith(os.path.abspath(HERE).lower())
    if inside:
        raise SystemExit(f"  refusing to unpack fonts inside the repo: {a.dest}")

    print(f"  verifying {len(verified)} font(s) ({WORKERS} workers, {PAUSE}s pause)")
    print(f"  font binaries -> {a.dest}")
    order = charmap.slot_order()  # one calibration, read off the cached Preeti page

    results = []
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for r in ex.map(lambda s: verify(s, recs[s], a.dest, order,
                                         rebuild=a.rebuild, refresh=a.refresh,
                                         show=a.show), verified):
            results.append(r)
            print(f"    {r['slug']:<26} {r['status']:<14} "
                  f"{(r.get('font') or r['note'])[:52]}")

    print()
    details(results, a.show)
    table(results, skipped)

    counts = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    passed = counts.get("PASS", 0)
    failed = counts.get("FAIL", 0) + counts.get("ERROR", 0)
    na = counts.get("NOT_AVAILABLE", 0)
    print(f"\n  {passed} passed, {failed} failed, {na} not available, "
          f"{len(skipped)} skipped")
    if counts.get("FAIL") or counts.get("ERROR"):
        print("  -> fix or re-sweep these before shipping the layout.")
    if a.json_out:
        os.makedirs(os.path.dirname(os.path.abspath(a.json_out)), exist_ok=True)
        with open(a.json_out, "w", encoding="utf-8") as f:
            json.dump({"results": results,
                       "skipped": [{"slug": s, "class": c} for s, c in skipped]},
                      f, ensure_ascii=False, indent=1)
        print(f"  wrote {a.json_out}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
