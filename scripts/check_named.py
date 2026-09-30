"""check_named.py -- does a NAMED set of fonts cover the songs' real characters?

    py scripts/check_named.py rajdhani pawang mkali kalam cv-haha arya \
                              arap007 himalayabold katmandu shreenath-bold

WHY A SEPARATE TOOL
-------------------
qualify_unicode.py deliberately reports only on fonts with NO verdict, because a
verdict means somebody already looked at the thing. That is the right default
and it makes this tool necessary the moment someone reports "these work too":
the fonts you have just looked at are exactly the ones the qualifier skips.

So this asks the mechanical half of the question again -- does every codepoint the
seven songs actually use reach a real glyph -- for a list you name by hand.

It does not second-guess your verdict. Coverage is necessary, not sufficient: a
font can cover all 98 codepoints and still shape a conjunct wrongly, and only
your eye settles that. The output therefore pairs the two facts rather than
replacing one with the other, and prints the MISSING CODEPOINTS because "which
ones" is the whole diagnosis.

The failure this guards against is silent. A gap does not crash: Chromium falls
through to another face for that character, so you get a word with a stray letter
in the middle of it -- invisible in a specimen that renders one clean line.
"""
import os
import re
import sys
from fontTools.ttLib import TTFont

# A whole-line .lrc metadata tag: [ti:...], [ar:...], [al:...], [by:...].
# Anything matching this is a title or a credit, not a sung character.
TAG = re.compile(r"\[[A-Za-z]{2}:[^\]]*\]")
# A sung-line timestamp: [mm:ss.xx]. A line may carry several, one per repeat.
TS = re.compile(r"^\s*(?:\[\d{1,2}:\d{2}(?:\.\d{1,3})?\])+\s*")

SONGS = r"H:\Lyric Video Making Folder"
HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(os.path.dirname(HERE), "fonts")


def corpus():
    """Every distinct codepoint in the seven songs' lyrics.

    Read from the .lrc text itself, not from a hand-kept list: a list would go
    stale the moment a song is re-tapped, and a stale list is a coverage number
    for text nobody is going to render.
    """
    chars = set()
    for entry in sorted(os.listdir(SONGS)):
        d = os.path.join(SONGS, entry)
        if not os.path.isdir(d):
            continue
        for name in os.listdir(d):
            if not name.endswith(".lrc"):
                continue
            with open(os.path.join(d, name), encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    stripped = line.strip()
                    # A metadata line is [ti:...] / [ar:...] / [al:...] and is
                    # WHOLE LINE. Those are Latin titles and must not enter the
                    # corpus: the first version of this tool stripped the leading
                    # bracket and kept the tag's text, which put 17 Latin
                    # characters into a Devanagari coverage count and made the
                    # number disagree with qualify_unicode.py's 98.
                    if TAG.fullmatch(stripped):
                        continue
                    # An [mm:ss.xx] timestamp prefixes the sung text, and there
                    # is often MORE THAN ONE -- a repeated chorus line carries
                    # every timestamp it is sung at. Strip them all, not just the
                    # first: the second version of this tool stripped one and
                    # counted the remaining brackets, digits and colons as glyphs
                    # the font had to carry.
                    line = TS.sub("", stripped)
                    for ch in line:
                        if not ch.isspace() and ord(ch) > 0x20:
                            chars.add(ch)
    return sorted(chars)


def face_files(slug):
    d = os.path.join(FONTS, slug)
    if not os.path.isdir(d):
        return []
    out = []
    for name in sorted(os.listdir(d)):
        if name.lower().endswith((".ttf", ".otf")):
            out.append(os.path.join(d, name))
    return out


def covered(path, chars):
    """Codepoints the font's own cmap maps to a real glyph."""
    try:
        font = TTFont(path, fontNumber=0, lazy=True)
    except Exception as exc:                      # a font that will not open
        return None, set(), str(exc)
    try:
        cmap = font.getBestCmap()
        names = {r.nameID for r in font["name"].names if r.nameID}
        return cmap, set(cmap), None
    finally:
        font.close()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2

    chars = corpus()
    print("")
    print("corpus: %d distinct characters across the seven songs" % len(chars))
    print("")

    worst = 0
    for slug in sys.argv[1:]:
        files = face_files(slug)
        if not files:
            print("  %-18s NO FONT FILE" % slug)
            worst = 1
            continue
        for path in files:
            cmap, cps, err = covered(path, chars)
            name = os.path.basename(path)
            if cmap is None:
                print("  %-18s %-28s UNREADABLE: %s" % (slug, name, err))
                worst = 1
                continue
            missing = [c for c in chars if ord(c) not in cps]
            if not missing:
                print("  %-18s %-28s FULL   all %d codepoints" % (slug, name, len(chars)))
            else:
                worst = 1
                shown = " ".join("U+%04X %s" % (ord(c), c) for c in missing[:24])
                more = "  (+%d more)" % (len(missing) - 24) if len(missing) > 24 else ""
                print("  %-18s %-28s MISSING %d/%d  %s%s"
                      % (slug, name, len(missing), len(chars), shown, more))
    print("")
    return worst


if __name__ == "__main__":
    sys.exit(main())
