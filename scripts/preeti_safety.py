"""preeti_safety.py -- which songs can this PREETI font carry WITHOUT corrupting a word?

    py scripts/preeti_safety.py pawang mkali cv-haha arap007 \
                                himalayabold katmandu shreenath-bold

WHY THIS IS NEEDED
------------------
A PREETI-class font has ZERO Devanagari codepoints. It renders by TRANSCODING the
Unicode lyrics into the font's own ASCII key layout, which is a lossy operation:
if a character has no key, it falls through to the key stream as itself, the font
has no glyph for it, and Chromium silently substitutes a DIFFERENT typeface for
that one character.

The result is one word drawn in two typefaces, mid-word, with no error anywhere.
That is the failure this repo exists to prevent, and `passthrough.py` is the
documented gate for it -- but passthrough takes a LAYOUT FILE, and PREETI fonts
have none: they share npttf2utf's built-in "Preeti" layout. So there was no way
to ask the question for this class, which is 77 of the 214 fonts.

TWO FAILURES, AND BOTH MATTER
----------------------------
  1. A Devanagari character SURVIVING the encode means the layout had no key for
     it. Measured per word, because the symptom is a corrupted word and not a
     corrupted font.
  2. An emitted key the font's own cmap does not cover. The encode succeeded and
     the font still cannot draw it. This is the per-font half that a shared
     layout cannot answer, and it is why running this for ONE PREETI font and
     generalising to the class would be wrong.

The measured shape, on these seven songs: the survivors are all PRE-BASE I-MATRA
words -- the matra that is written to the LEFT of its consonant. The layout
carries it for most words and not for all, and AGENTS.md already documents that
a pre-base i-matra which keeps its carrier writes a stray KA and turns one word
into a different, valid, wrong word. Nothing errors. That is why this is measured
per song and reported per song.
"""
import os
import re
import sys
from fontTools.ttLib import TTFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import layout_encoder as E                                    # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(os.path.dirname(HERE), "fonts")
SONGS = r"H:\Lyric Video Making Folder"

TAG = re.compile(r"\[[A-Za-z]{2}:[^\]]*\]")
TS = re.compile(r"^\s*(?:\[\d{1,2}:\d{2}(?:\.\d{1,3})?\])+\s*")
DEV = re.compile(r"[\u0900-\u097F]")


def song_words():
    """{song dir: [word, ...]} of every Devanagari word in every song."""
    out = {}
    for entry in sorted(os.listdir(SONGS)):
        d = os.path.join(SONGS, entry)
        if not os.path.isdir(d):
            continue
        starts = [n for n in os.listdir(d)
                  if n.lower().endswith("remotion_start.lrc")]
        if not starts:
            continue
        words = []
        with open(os.path.join(d, starts[0]), encoding="utf-8",
                  errors="replace") as fh:
            for line in fh:
                s = line.strip()
                if TAG.fullmatch(s):
                    continue
                s = TS.sub("", s)
                words += [w for w in s.split() if DEV.search(w)]
        if words:
            out[entry] = words
    return out


def face(slug):
    d = os.path.join(FONTS, slug)
    if not os.path.isdir(d):
        return None
    for name in sorted(os.listdir(d)):
        if name.lower().endswith((".ttf", ".otf")):
            return os.path.join(d, name)
    return None


def encoded(word):
    try:
        out = E.encode(word, "Preeti")
    except Exception:
        return ""
    if isinstance(out, tuple):
        out = out[0]
    return str(out)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2

    songs = song_words()
    slugs = sys.argv[1:]

    print("")
    print("PREETI safety -- encode with the shared Preeti layout, then ask two")
    print("questions per font: does any Devanagari SURVIVE the encode, and does")
    print("the font's own cmap cover every key the encode emitted?")
    print("")

    for slug in slugs:
        path = face(slug)
        if not path:
            print("  %-18s NO FONT FILE" % slug)
            continue
        try:
            font = TTFont(path, fontNumber=0, lazy=True)
            cps = set(font.getBestCmap())
            font.close()
        except Exception as exc:
            print("  %-18s UNREADABLE: %s" % (slug, exc))
            continue

        devanagari = sum(1 for c in cps if 0x900 <= c <= 0x97F)
        print("  %s  (%s)" % (slug, os.path.basename(path)))
        print("    devanagari codepoints: %d  %s"
              % (devanagari,
                 "-- expected 0 for a PREETI font; it renders by transcoding"
                 if devanagari == 0 else "<-- NOT PREETI CLASS, use --font"))

        safe = []
        for song, words in songs.items():
            leaked = []
            uninked = set()
            for w in words:
                keys = encoded(w)
                survivors = DEV.findall(keys)
                if survivors:
                    leaked.append((w, "".join(survivors)))
                for ch in keys:
                    if not DEV.match(ch) and ord(ch) not in cps:
                        uninked.add(ch)
            n_bad = len(leaked) + len(uninked)
            if n_bad == 0:
                safe.append(song)
                print("      %-30s CLEAN   %3d words" % (song[:30], len(words)))
            else:
                parts = []
                if leaked:
                    parts.append("%d word(s) leak: %s"
                                 % (len(leaked),
                                    " ".join("%s->%s" % b for b in leaked[:3])))
                if uninked:
                    parts.append("%d emitted key(s) with no glyph: %s"
                                 % (len(uninked),
                                    " ".join("U+%04X" % ord(c)
                                             for c in sorted(uninked)[:8])))
                print("      %-30s UNSAFE  %s" % (song[:30], "; ".join(parts)))
        print("    -> usable on %d of %d songs: %s"
              % (len(safe), len(songs),
                 ", ".join(s[:12] for s in safe) if safe else "NONE"))
        print("")

    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
