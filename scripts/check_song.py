"""check_song.py -- can this font actually write THIS song?

    py scripts/check_song.py --layout layouts/ams-manthan.json "song.lrc"
    py scripts/check_song.py --layout layouts/arya.json "song.lrc"      # (no layout = fine)
    py scripts/check_song.py --font ams-manthan --all "song.lrc"

WHY THIS EXISTS
---------------
`verify_layouts.py --all` answers "does every key in this layout reach a real
glyph in the font". That is a statement about the FONT, and it is the wrong
question. The question that matters before a render is "can this layout write
the words in this song", and those two answers disagree often enough to matter:

    AMS Manthan passes every layout check, and still cannot write Allare.

        12 of 35 lines (34%) contain a character with no key
        U+0901 candrabindu  x13      U+094D virama  x11
        15 distinct words affected

The renderer does not stop. It exits 0, the file is the right length, the plate
is pure black, and every output check passes -- because none of those can see a
wrong letter. `फर्केर` comes out as `फरकर`, a different word, with the े matra and
the र् half-form simply dropped.

The reason is that aNepali publishes the candrabindu and the virama as
*Devanagari* rather than as a key, so no generated layout can contain them.
There is no layout file that fixes this; it is a property of the encoding.

WHAT IT PRINTS
--------------
For each unencodable character: the code point, what it is, and how many times
it occurs. Then the words, so the failure is concrete rather than a percentage.
Then a verdict, and the words to use when handing the result to someone.

Exit code 0 when every line survives, 1 when any do not -- so it can gate a
render in a script.

Usage:
    py scripts/check_song.py --layout <layout.json> <song.lrc>
    py scripts/check_song.py --font <slug> <song.lrc>      # looks in layouts/
    py scripts/check_song.py --font <slug> --all <song.lrc>  # every layout
    py scripts/check_song.py --word "रिसले" --layout <layout.json>
"""
import argparse
import collections
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

STAMP = re.compile(r"\[(\d{1,3}):[0-5]?\d(?:[.:]\d{1,3})?\]")
META = re.compile(r"^\[(ti|ar|al|au|by|re|ve|length|offset|ti-font|ti-fontfile):",
                  re.I)

# The characters aNepali publishes as Devanagari rather than as a key, so no
# generated layout can hold them. Named, because "U+0901" on its own is a thing
# you look up and "the candrabindu" is a thing you remember.
#
# The virama matters more than it looks: a conjunct is written consonant +
# virama + consonant, and dropping the virama does not merely lose a mark, it
# splits one glyph into two and changes the word. फर्केर -> फरकर.
KNOWN_UNENCODABLE = {
    0x0901: "candrabindu",
    0x094D: "virama (joins a conjunct; dropping it changes the word)",
}


def read_lines(path):
    """The lyric text of an .lrc, with stamps and metadata removed.

    Multi-stamp lines (`[00:10.00][01:20.00]chorus`) are one line of words, so
    the stamps come off and the text is deduplicated rather than counted twice.
    """
    out = []
    with open(path, encoding="utf-8-sig") as f:
        for raw in f:
            raw = raw.strip()
            if not raw or META.match(raw):
                continue
            text = STAMP.sub("", raw).strip()
            if text:
                out.append(text)
    return out


def load_layout(path):
    """{key: devanagari} from a layout file, whatever the nesting is.

    The files are written by several tools over time and have ended up with
    different shapes -- a bare map, {family: map}, {family: {rules: {map}}}.
    Rather than assume one and fail on the others, take the largest character
    map found anywhere in the document.

    A character map is recognised by its VALUES, not its keys: they are
    Devanagari, and mostly single Devanagari characters. Two things this has got
    wrong already, both of which produce a confident wrong answer:

      - requiring every value to be length 1 rejects the REAL map, because some
        keys produce a two-character sequence. That yielded an empty map, so
        every character read as unencodable and the song scored 100% broken --
        the exact opposite of the truth, from a check that looked like it ran.
      - testing keys instead of values asks "is ा a key", which is never true,
        and reports the whole script as unwritable.
    """
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)

    def is_devanagari(s):
        return bool(s) and all(0x900 <= ord(c) <= 0x97F for c in s)

    def map_score(node):
        if not isinstance(node, dict) or len(node) < 9:
            return None
        vals = list(node.values())
        if not all(isinstance(v, str) and is_devanagari(v) for v in vals):
            return None
        # Mostly single characters, but not exclusively: some keys emit a
        # sequence. A genuine map is well above half single-character.
        single = sum(1 for v in vals if len(v) == 1)
        if single * 2 < len(vals):
            return None
        return len(node)

    best, best_score = {}, -1
    stack = [doc]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            score = map_score(node)
            if score is not None and score > best_score:
                best, best_score = node, score
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return best


def unencodable(text, charmap):
    """Characters in this line that the layout has no key for.

    A character is encodable when the layout produces it: the map is
    key -> Devanagari, so the test is "does any key produce this character",
    not "is this character a key". Getting that backwards reports every
    Devanagari character as missing, which is the same class of confidently
    wrong answer this repo keeps producing.
    """
    produced = set(charmap.values())
    return [c for c in text if 0x900 <= ord(c) <= 0x97F and c not in produced]


def report(lines, charmap, label):
    bad_lines = []
    counts = collections.Counter()
    words = collections.OrderedDict()

    for text in lines:
        missing = unencodable(text, charmap)
        if not missing:
            continue
        bad_lines.append((text, missing))
        for c in missing:
            counts[c] += 1
        # Only the words that actually contain one of THIS LINE's missing
        # characters. Testing against the running totals instead flags every
        # word on every line that had a failure anywhere -- so "हो" and "म",
        # which contain neither a virama nor a candrabindu, were listed as
        # affected, and the count came out at 40 instead of the real number.
        for w in re.split(r"\s+", text):
            w = w.strip(" ,.:;!?।॥")
            if w and any(c in w for c in missing):
                words.setdefault(w, w)

    total = len(lines)
    print("\n  %s" % label)
    print("    lines total            : %d" % total)

    if not bad_lines:
        print("    lines that survive     : %d (100%)" % total)
        print("\n  VERDICT: every line is writable in this font.")
        return True

    print("    lines with no key      : %d (%.0f%%)"
          % (len(bad_lines), 100.0 * len(bad_lines) / total))
    print("    characters with no key :")
    for c, n in counts.most_common():
        name = KNOWN_UNENCODABLE.get(ord(c), "")
        print("        U+%04X  %-3s x%-4d %s" % (ord(c), c, n, name or "(unknown)"))

    print("    distinct words affected: %d" % len(words))
    shown = list(words)[:10]
    for w in shown:
        print("        %s" % w)
    if len(words) > len(shown):
        print("        ... and %d more" % (len(words) - len(shown)))

    print("\n  VERDICT: NOT SAFE for this song. A Unicode font is the fix -- there")
    print("           is no layout file that adds these keys, because the")
    print("           publisher emits them as Devanagari rather than as a key.")
    return False


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("lrc", nargs="?", help="the song's .lrc")
    ap.add_argument("--layout", help="a layout .json to test against")
    ap.add_argument("--font", help="a layout slug, looked up in layouts/")
    ap.add_argument("--all", action="store_true",
                    help="with --font, test every layout in layouts/")
    ap.add_argument("--word", help="test one word instead of a file")
    a = ap.parse_args()

    if a.word:
        if not (a.layout or a.font):
            ap.error("--word needs --layout or --font")
        paths = [resolve(a.layout, a.font, None)] if not a.all else all_layouts()
    elif a.lrc:
        paths = all_layouts() if a.all else [resolve(a.layout, a.font, a.lrc)]
    else:
        ap.error("give an .lrc or --word")

    if a.word:
        ok = report([a.word], load_layout(paths[0]), os.path.basename(paths[0]))
        sys.exit(0 if ok else 1)

    lines = read_lines(a.lrc)
    if not lines:
        sys.stderr.write("no lyric lines found in " + a.lrc + "\n")
        return 2

    results = []
    for p in paths:
        results.append((p, report(lines, load_layout(p), os.path.basename(p))))

    passed = [os.path.basename(p) for p, ok in results if ok]
    print("\n  %d of %d layouts can write this song." % (len(passed), len(results)))
    if passed:
        print("  Usable here: " + ", ".join(passed[:8]) +
              (" ..." if len(passed) > 8 else ""))
    else:
        print("  No layout can write this song. Use a Unicode font instead -- they")
        print("  need no layout at all, so there is nothing that can be wrong.")
    return 0 if passed else 1


def resolve(layout, font, lrc):
    if layout:
        if not os.path.exists(layout):
            sys.exit("no such layout file: " + layout)
        return layout
    if font:
        p = os.path.join(ROOT, "layouts", font + ".json")
        if not os.path.exists(p):
            sys.exit("no such layout: " + p)
        return p
    ap_error()


def ap_error():
    sys.stderr.write("give --layout <file.json> or --font <slug>\n")
    sys.exit(2)


def all_layouts():
    d = os.path.join(ROOT, "layouts")
    if not os.path.isdir(d):
        sys.exit("no layouts/ directory in " + ROOT)
    return [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.endswith(".json")]


if __name__ == "__main__":
    sys.exit(main() or 0)
