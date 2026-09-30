"""check_song_render.py -- the font gate a RENDER depends on, and nothing else.

    py scripts/check_song_render.py --lrc song.lrc --slug pawang
    py scripts/check_song_render.py --lrc song.lrc --layout layouts/x.json
    py scripts/check_song_render.py --lrc song.lrc --font-file fonts/pawang/x.ttf

WHY THIS IS NOT scripts/check_song.py
-------------------------------------
Two different questions, and this repository now answers both:

    check_song.py        "can this LAYOUT write this song?"    -- a font question
    check_song_render.py  "can this FONT, as a render would use it,
                           write this song?"                    -- a render gate

The difference is not academic. `check_song.py` reads `layouts/<slug>.json`.
A render loads a .ttf and passes a `--font-family` string, and the family name
is what Chromium is actually told to use.

This script checks the things that only exist at render time:

  * the .ttf actually has ink for every key the transform emits
  * the family name resolves, so --font-family is not a guess

THE CMAP CHECK IS NOT OPTIONAL, AND ITS ABSENCE MUST BE VISIBLE.
------------------------------------------------------------
A layout can round-trip perfectly against a font that never had those glyphs.
Five fonts that DECLARE Preeti are in exactly that state: their binaries have no
ink on the key slots, so Chromium substitutes another font per character and the
video prints `hfpm,` where the lyrics say जाऊ, — with exit 0 and no error from
any other check in this repository.

A first version of this gate resolved the .ttf from `fonts/<slug>/*.ttf` and
treated a missing file as "skip the check". On this machine that made the gate
report **OK** for `ganga-1` — one of the five known raw-ASCII fonts — because
`fonts/ganga-1/` happens to hold only a README. The gate passed the exact font
it exists to catch. A check that cannot fail is not a check, so:

  * no .ttf found  ->  FAIL, loudly, naming the font and the fix
  * fontTools absent -> FAIL, not a skip (it is in requirements.txt)
  * UNICODE class  -> the one legitimate no-transform case, said plainly

Moved here from lyric-studio/scripts/font_gate.py. Exit 0 = the render may
proceed. Non-zero = stop, with the offending words named.

It still cannot tell you the glyphs are the RIGHT ones. Nothing in this
repository can. Only a rendered frame watched by a person does that, which is
why verdicts.json has a `working` state that no script may grant.
"""

import argparse
import io
import json
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8")

try:
    from lrc_legacy import convert_line
except ImportError:                                   # pragma: no cover
    sys.stderr.write(
        "check_song_render.py needs lrc_legacy.py, which is beside it in\n"
        "  scripts/ (it moved here from lyric-studio). If you are reading this\n"
        "  from a partial clone, finish the clone.\n")
    raise

try:
    from fontTools.ttLib import TTFont
except ImportError:                                   # pragma: no cover
    TTFont = None


def die(msg, hint=None):
    sys.stderr.write("\n  font gate FAILED: %s\n" % msg)
    if hint:
        for line in hint.strip().split("\n"):
            sys.stderr.write("    %s\n" % line)
    sys.stderr.write("\n")
    sys.exit(1)


def note(msg):
    sys.stdout.write("  font gate: %s\n" % msg)


def read_lrc(path):
    """Lyrics with timestamps stripped, one entry per line."""
    out = []
    with io.open(path, encoding="utf-8") as fh:
        for line in fh:
            s = re.sub(r"\[\d+:\d+(?:[.:]\d+)?\]", "", line)
            s = re.sub(r"^\s*\[[a-zA-Z]+:[^\]]*\]\s*$", "", s)   # [ti:Allare]
            s = s.strip()
            if s:
                out.append(unicodedata.normalize("NFC", s))
    return out


def catalogue(repo):
    p = os.path.join(repo, "sweep.json")
    if not os.path.exists(p):
        die("no sweep.json in " + repo + " -- the font repo is incomplete.",
            "git clone https://github.com/mhzsajan/nepali-legacy-fonts")
    with io.open(p, encoding="utf-8") as fh:
        return {e["slug"]: e for e in json.load(fh)}


def find_ttf(repo, slug):
    """The .ttf for a slug, or None. Never guesses past the slug's own folder."""
    fdir = os.path.join(repo, "fonts", slug)
    if not os.path.isdir(fdir):
        return None
    ttfs = [fn for fn in sorted(os.listdir(fdir)) if fn.lower().endswith((".ttf", ".otf"))]
    return os.path.join(fdir, ttfs[0]) if ttfs else None


def resolve(slug, repo):
    """slug -> (layout_file|None, layout_name|None, ttf|None).

    A PREETI font has NO layouts/<slug>.json: it uses npttf2utf's built-in
    Preeti table, and its layout name is literally "Preeti". Requiring a layout
    file (as a first version did) made every working legacy font look broken --
    pawang, arap007, cv-haha and mkali are all PREETI, and the gate refused
    four of the seven fonts this project is known to work with. The class comes
    from sweep.json, the font repo's own catalogue.
    """
    row = catalogue(repo).get(slug)
    if row is None:
        die("%r is not in sweep.json -- no such font in the catalogue." % slug)
    cls = row.get("class")
    layout = os.path.join(repo, "layouts", slug + ".json")
    if os.path.exists(layout):
        return layout, slug, find_ttf(repo, slug)
    if cls == "PREETI":
        return None, "Preeti", find_ttf(repo, slug)
    return None, None, find_ttf(repo, slug)      # UNICODE: no transform


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lrc", required=True, help="the song's .lrc (Unicode)")
    ap.add_argument("--slug", help="a font slug from this repo")
    ap.add_argument("--layout", help="a layout .json (hand-wired legacy path)")
    ap.add_argument("--font-file", help="the .ttf the render will load")
    ap.add_argument("--fonts-repo", default=ROOT, help="this repo")
    args = ap.parse_args()

    repo = os.path.abspath(args.fonts_repo)
    if not os.path.exists(args.lrc):
        die("no such .lrc: " + args.lrc)

    layout_file, layout_name, slug_ttf = (None, None, None)
    if args.slug:
        layout_file, layout_name, slug_ttf = resolve(args.slug, repo)
    elif args.layout:
        layout_file = args.layout
        layout_name = os.path.splitext(os.path.basename(layout_file))[0]
    if args.font_file is None and slug_ttf:
        args.font_file = slug_ttf

    # -- the Unicode case: no transform, so no transform to fail --------------
    if layout_name is None:
        note("%s is a UNICODE font (per sweep.json)." % (args.slug or "this font"))
        note("The lyrics are handed over unchanged, so there is nothing to gate.")
        note("Whether it is any GOOD font is a different question, answered in")
        note("verdicts.json -- and only a person can put a font there.")
        return 0

    if layout_file and not os.path.exists(layout_file):
        die("no such layout: " + layout_file)

    if layout_file is None:
        note("%s is PREETI-class -- npttf2utf's built-in table." % args.slug)
        note("(there is no layouts/%s.json, and there should not be.)" % args.slug)

    lines = read_lrc(args.lrc)
    if not lines:
        die("no lyric lines in " + args.lrc)

    # -- 1. what keys does the transform emit? ---------------------------------
    keys = set()
    for line in lines:
        for tok in re.findall(r"[!-~]+", convert_line(line, layout_name)):
            keys.update(tok)
    if not keys:
        die("the transform emitted no keys at all -- is %r a layout?" % layout_name,
            "A layout is a JSON object of {unicode: key}.")

    # -- 2. does the FONT have ink for every one of them? ----------------------
    # This is the check that catches the raw-ASCII fonts, and it is the reason
    # this gate exists separately from check_song.py. It cannot be skipped by
    # accident: no font file is a FAILURE, not a pass.
    if TTFont is None:
        die("fontTools is not installed, so the cmap check cannot run.",
            "pip install fonttools\n"
            "  It is in requirements.txt. Skipping it would defeat the purpose:\n"
            "  five fonts that DECLARE Preeti print raw ASCII, and this is the\n"
            "  only automated check that catches them.")

    if not args.font_file:
        die("no .ttf to check, and the cmap check is not optional.",
            "Pass --font-file, or use --slug so it can be resolved.\n"
            "  A layout can round-trip perfectly against a font that never had\n"
            "  those glyphs. That is precisely the raw-ASCII failure.")

    if not os.path.exists(args.font_file):
        die("no such font file: " + args.font_file,
            "If the binary is not downloaded:  py scripts/fetch_fonts.py")

    font = TTFont(args.font_file, fontNumber=0)
    cmap = set()
    for tbl in font["cmap"].tables:
        cmap.update(tbl.cmap.keys())
    missing = sorted(c for c in keys if ord(c) not in cmap)
    if missing:
        die("the font has no glyph for %d of the %d key characters the transform "
            "emits.\n  That is the raw-ASCII failure: Chromium will substitute "
            "another font per character, so the\n  video prints Latin where the "
            "lyrics say Devanagari, and no other check catches it."
            % (len(missing), len(keys)),
            "missing (first 20): %s\n"
            "  font: %s\n"
            "  This font is recorded as broken in verdicts.json -- see\n"
            "    py scripts/check_verdicts.py --report"
            % ("".join(missing[:20]), args.font_file))

    # The family name a render must pass to Chromium. Resolving it here means
    # --font-family is a fact rather than a guess; a wrong family name makes the
    # keys resolve in a different font with no error anywhere else.
    families = set()
    try:
        for rec in font["name"].names:
            if rec.nameID in (1, 4, 16):
                try:
                    families.add(str(rec.toUnicode()))
                except Exception:
                    pass
    except Exception:
        pass

    note("OK -- %d lyric lines, %d distinct key characters, all present in %s"
         % (len(lines), len(keys), os.path.basename(args.font_file)))
    if families:
        note("family name(s) in the font: %s" % ", ".join(sorted(families)))
    note("This proves the keys reach real glyphs and the text survives the")
    note("transform. It CANNOT prove they are the RIGHT glyphs -- watch a frame,")
    note("and see verdicts.json for the eye-check.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
