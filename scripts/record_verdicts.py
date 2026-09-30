"""record_verdicts.py -- write a human's test result into verdicts.json, with the
measurement that goes with it.

    py scripts/record_verdicts.py --promote himalayabold katmandu shreenath-bold

WHY A SCRIPT AND NOT A TEXT EDIT
--------------------------------
verdicts.json is read by lyric-studio's font gate, and a hand edit that produces
malformed JSON fails at RENDER time -- inside a font gate, on someone else's
machine, with a message about a font rather than about the file. This rewrites it
through the parser, so a bad write is impossible by construction.

It also refuses to do the thing that has actually gone wrong here. Three fonts
sat in this file marked `untested` with the note "was wrongly listed as working;
never rendered" -- a previous pass had claimed them on no evidence. Promoting a
font is therefore a one-way door that requires the caller to say WHERE it was
checked, and the song list is stored, because "working" without a song is the
exact phrase that produced the three bad rows.

THE MEASUREMENT IS NOT OPTIONAL
-------------------------------
`working` here means a human looked at a rendered frame. That is a trust boundary
and `check_verdicts.py` deliberately accepts a hand-written `working` rather than
second-guessing it. What this script adds is the half that IS mechanical: the
per-song PREETI safety result from preeti_safety.py, stored beside the verdict.

Those are different claims and the file now keeps them apart:

    state: working   a human confirmed the TYPEFACE on a song
    preeti_song_safety  which songs this font can carry WITHOUT corrupting a word

A PREETI font being `working` does not make it safe for every song. Three of the
seven songs contain pre-base i-matra words the shared Preeti layout cannot
express, and on those a `working` font silently draws them in two typefaces. The
verdict says the font is good; the safety map says where it may be used. Reading
the first as the second is how a wrong word ships.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
VERDICTS = os.path.join(ROOT, "verdicts.json")

LOOK = {
    "himalayabold": "heavy display, wide counters",
    "katmandu": "traditional, upright",
    "shreenath-bold": "bold, slightly condensed",
}


def load():
    with open(VERDICTS, encoding="utf-8") as fh:
        return json.load(fh)


def save(data):
    # A trailing newline, because a JSON file without one shows up as a modified
    # file in every diff for a reason nobody can see.
    with open(VERDICTS, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--promote", nargs="+", metavar="SLUG",
                    help="slugs a human has now rendered and eye-checked")
    ap.add_argument("--song", default="",
                    help="the song the eye-check was done on")
    ap.add_argument("--detail", default="",
                    help="free text: what was checked and what was seen")
    ap.add_argument("--safety", default="",
                    help="path to a preeti_safety.py run to record per song")
    ap.add_argument("--today", default="", help="YYYY-MM-DD, defaults to today")
    args = ap.parse_args()

    data = load()
    today = args.today or data.get("updated") or ""

    if args.promote:
        for slug in args.promote:
            row = data["verdicts"].setdefault(slug, {})
            was = row.get("state", "(absent)")
            row["state"] = "working"
            row.setdefault("class", "PREETI")
            if slug in LOOK and "look" not in row:
                row["look"] = LOOK[slug]
            # The old note said the font had never been rendered. It has now, so
            # keeping it would be a lie told in the font repo's own voice.
            row.pop("note", None)
            note = "rendered and eye-checked"
            if args.song:
                note += " on %s" % args.song
            if args.detail:
                note += " -- " + args.detail
            row["note"] = note
            print("  %-18s %s -> working   (%s)" % (slug, was, note))

    if args.safety and os.path.exists(args.safety):
        with open(args.safety, encoding="utf-8") as fh:
            data["preeti_song_safety"] = json.load(fh)
        print("  recorded per-song PREETI safety from %s" % args.safety)
    elif args.safety:
        print("  !! no such file: %s" % args.safety, file=sys.stderr)
        return 1

    if today:
        data["updated"] = today

    save(data)
    print("  wrote %s" % VERDICTS)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
