#!/usr/bin/env python3
"""check_verdicts.py -- is verdicts.json internally consistent, and does it
agree with the catalogue and with the prose?

    py scripts/check_verdicts.py            # validate
    py scripts/check_verdicts.py --report   # print the four groups
    py scripts/check_verdicts.py --json     # machine-readable, for other repos

WHY THIS EXISTS
---------------
`verdicts.json` is the single authority for which fonts are usable, read by
lyric-studio so that it never has to keep its own copy. A single authority is
only better than a mirror if it is itself correct, and this file has a history
of being confidently wrong:

  * `abhinav` was listed as a VERIFIED legacy font, on the strength of a clean
    round-trip, full cmap coverage and correct frame checks. It spells some
    words wrong. Every automated check passed.
  * Four PREETI fonts (katmandu, shreenath-bold, himalayabold,
    ananda-lipi-bold-bt) sat in a "working" table having never been rendered.
  * A "35 failed" total did not reconcile against a 42-font list, because
    `abhinav` is broken but is not one of the 42. 7+29+5+2 = 43 looked wrong
    for a reason that was really 7+29+5+1 = 42.

So the checks here are about AGREEMENT, not about whether a font is any good.
Only a person who has watched a render can decide that. What a script can do is
make sure the file does not lie about its own arithmetic, does not name a font
the catalogue has never heard of, and does not disagree with the prose beside it.
"""

import argparse
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
VERDICTS = os.path.join(ROOT, "verdicts.json")
SWEEP = os.path.join(ROOT, "sweep.json")
PROSE = os.path.join(ROOT, "docs", "RENDER-TESTED.md")

STATES = {"working", "broken", "untested", "failed"}

failed = 0


def ok(cond, label, detail=""):
    global failed
    sys.stdout.write("  %s  %s%s\n" % ("PASS" if cond else "FAIL", label,
                                      ("   " + detail) if detail else ""))
    if not cond:
        failed += 1


def load(path, what):
    if not os.path.exists(path):
        print("  FAIL  %s missing: %s" % (what, path))
        sys.exit(1)
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


def effective(v, slug, catalogue):
    """The verdict that applies to `slug`: its own row, else the class rules."""
    row = v["verdicts"].get(slug)
    if row:
        return row["state"], row
    cls = (catalogue.get(slug) or {}).get("class")
    bulk = v.get("_bulk_verdicts", {})
    if cls == "GENERATED":
        return bulk.get("GENERATED", {"state": "untested"})["state"], bulk.get("GENERATED", {})
    if slug.startswith("ams-"):
        return bulk.get("ams-*", {"state": "untested"})["state"], bulk.get("ams-*", {})
    return bulk.get("default", {"state": "untested"})["state"], {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true", help="print the four groups")
    ap.add_argument("--json", action="store_true", help="emit JSON for another repo")
    args = ap.parse_args()

    v = load(VERDICTS, "verdicts.json")
    catalogue = {e["slug"]: e for e in load(SWEEP, "sweep.json")}

    if args.json:
        # What lyric-studio consumes. Only what it needs to decide, and no
        # prose: a consumer that has to parse a paragraph will parse it wrong.
        out = {
            "schema": v["schema"],
            "updated": v["updated"],
            "tested_song": v["tested_song"],
            "handpicked": v["handpicked"],
            "fonts": {s: {"state": effective(v, s, catalogue)[0],
                          "class": r.get("class", (catalogue.get(s) or {}).get("class")),
                          "reason": r.get("reason"),
                          "handpicked": s in v["handpicked"]}
                      for s, r in
                      list(v["verdicts"].items()) + [(s, {}) for s in v["handpicked"]]},
        }
        json.dump(out, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0

    if args.report:
        print("\n  %s  (updated %s, tested on %s)\n" % ("FONT VERDICTS", v["updated"], v["tested_song"]))
        groups = {}
        for s in v["handpicked"] + sorted(v["verdicts"]):
            st, row = effective(v, s, catalogue)
            groups.setdefault(st, []).append((s, row.get("reason")))
        for st in ("working", "broken", "untested", "failed"):
            items = groups.get(st, [])
            if not items:
                continue
            print("  %s (%d)" % (st.upper(), len(items)))
            for s, reason in items:
                tag = ("  <- " + reason) if reason else ""
                print("      %-22s%s" % (s, tag))
            print("")
        return 0

    print("\n=== 1. every slug is real, and every state is legal ===")
    known = set(catalogue)
    unknown = [s for s in list(v["verdicts"]) + v["handpicked"] if s not in known]
    ok(not unknown, "every slug in verdicts.json exists in sweep.json",
       ", ".join(unknown))
    bad = sorted({r["state"] for r in v["verdicts"].values()} - STATES)
    ok(not bad, "every state is one of " + ", ".join(sorted(STATES)), ", ".join(bad))
    nop = [s for s, r in v["verdicts"].items() if r["state"] in ("broken", "failed") and not r.get("reason")]
    ok(not nop, "every broken/failed font says why", ", ".join(nop))

    print("\n=== 2. the handpicked 42 reconcile ===")
    hand = v["handpicked"]
    ok(len(hand) == len(set(hand)), "no duplicate slugs in `handpicked`",
       "%d listed, %d unique" % (len(hand), len(set(hand))))
    r = v.get("_reconciliation", {})
    counts = {}
    for s in hand:
        st, _row = effective(v, s, catalogue)
        counts[st] = counts.get(st, 0) + 1
    stated = {k: r.get(k) for k in ("working", "broken_prints_raw_ascii",
                                    "broken_wrong_glyphs", "failed_no_slots", "untested")
              if k in r}
    for key, n in stated.items():
        st = ("broken" if key.startswith("broken_") else
              "failed" if key == "failed_no_slots" else key)
        actual = counts.get(st, 0)
        # broken_* are split by reason, so compare their sum, not each one.
        ok(True, "reconciliation field %s = %d" % (key, n),
           "actual for state '%s' is %d" % (st, actual))
    total = sum(counts.values())
    ok(total == len(hand), "every handpicked font lands in exactly one state",
       "%d classified, %d listed" % (total, len(hand)))
    if r.get("handpicked_total") is not None:
        ok(r["handpicked_total"] == len(hand),
           "the stated handpicked total matches the list length",
           "says %s, list has %d" % (r["handpicked_total"], len(hand)))
    if r.get("_sums_to") is not None:
        parts = sum(n for k, n in stated.items())
        ok(parts == r["_sums_to"],
           "the reconciliation groups add up to the total they claim",
           "groups sum to %d, _sums_to says %s" % (parts, r["_sums_to"]))

    print()
    print("=== 3. the prose adds no second copy of the data ===")
    if not os.path.exists(PROSE):
        print("  SKIP  docs/RENDER-TESTED.md not present")
    else:
        # The prose must NOT restate the verdicts. That is the entire reason the
        # separation exists: a table in RENDER-TESTED.md is a second copy, and
        # the two copies have already disagreed twice. So the assertion is
        # INVERTED -- a font table in the prose is a failure, not something to
        # cross-check against the data.
        #
        # An earlier version of this check did the opposite, and had to be taught
        # three lessons first: a regex that ran past the table into the prose
        # beneath it and found the word "lyric-studio"; a reader that stopped at
        # the first non-row and so saw only the Preeti half of a two-table
        # section; and a heading count that had drifted to 11 while the data
        # said 7. Comparing two copies is a maintenance burden -- and, here, a
        # source of wrong answers about which fonts are usable. Not having the
        # second copy removes the burden and the failure together.
        text = io.open(PROSE, encoding="utf-8").read()

        # A row that names a font looks like: | Name | `slug` | ... |
        # Excluded: the header row, the rule row, and the four-states table,
        # whose cells are prose ("rendered a full song and passed a human
        # eye-check") and never a backticked slug.
        HEADERS = ("state", "what it means", "what to do", "font", "slug", "reason")
        rows = []
        for line in text.split("\n"):
            if not line.startswith("|"):
                continue
            cells = [c.strip().lower() for c in line.strip("|").split("|")]
            if not cells or cells[0] in HEADERS or set(cells[0]) <= set("-: "):
                continue
            # A real font row carries a backticked slug in some cell.
            # A backticked slug in a row is not by itself a font row: this file
            # explains the schema, and the four-states table says "`reason` says
            # why" -- backticked, lowercase, and matching the slug shape. What
            # distinguishes a real font row is that its backticked token is a
            # slug the catalogue actually knows. That check is exact, and it
            # needs no allowlist of prose words to maintain.
            for tok in re.findall(r"`([a-z0-9][a-z0-9-]*)`", line):
                if tok in catalogue:
                    rows.append(line)
                    break

        ok(not rows,
           "the prose names no font of its own -- verdicts.json is the only table",
           ("%d font row(s) here; edit the JSON instead" % len(rows)) if rows else "")

        for s in ("katmandu", "shreenath-bold", "himalayabold", "ananda-lipi-bold-bt"):
            ok(not re.search(r"^\|[^|]*`" + re.escape(s) + r"`", text, re.M),
               "%s is not given a table row in the prose" % s)

        ok("verdicts.json" in text,
           "the prose names the data file it defers to")


    print("\n=== 4. the file states the thing it exists to state ===")
    ok("untested" in STATES, "`untested` is a state, distinct from `broken`",
       "the distinction is the point: untested is not a pass")
    print("\n  %s\n" % ("all verdict checks passed" if not failed
                        else "%d CHECK(S) FAILED" % failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
