"""make_ends_txt.py -- derive the .ends.txt companion from an AbleSet end export.

    py scripts/make_ends_txt.py "<song folder>" "<start.lrc>" "<remotion_end.lrc>"

WHY THIS IS NOT A STRAIGHT COPY
-------------------------------
The renderer wants a `.ends.txt` beside the `.lrc`: one row per rendered cue,
`start | end | text`. Song Timer's AbleSet export carries the same information,
but in a shape that does not line up with the cues:

  * the .lrc is a LINE-ORIENTED export. A lyric that repeats is written once,
    with several timestamps on that one line -- one per time it is sung. Kali
    Kali's second line is
        [00:21.23][01:09.25][01:47.47][02:03.54]हेर न कस्तो आँखा तरेकी..
    which is that line sung four times, at 21s, 69s, 107s and 123s.
  * the end file is INSTANCE-ORIENTED. One row per sung instance, in playing
    order, so the same lyric appears several times as separate rows.

Joining on timestamp therefore matches almost nothing -- on Kali Kali exactly
1 of 48 -- and an earlier version of this script called that "different takes",
which was wrong. It is the same take, described two ways.

So the ends are matched to cues by ORDER and CONFIRMED BY TEXT:

  1. expand the .lrc into cues: every timestamp on a line becomes its own cue
     (time, text), ordered by time
  2. read the end rows in file order
  3. pair them positionally, and require the TEXT to agree
  4. if the text ever disagrees, STOP and report the position

Step 3 is what makes this safe. Positional pairing alone would silently attach
a chorus end time to a verse cue and produce a plausible wrong file -- the exact
shape of the bug this whole repository keeps hitting. If the texts line up for
all 48 rows the pairing is proven; if they do not, nothing is written.

The renderer distinguishes `timed` from `timed-clamped` (a tapped end that ran
past the next cue's start, so it was trimmed to the next line) and counts the
two separately, so a clamped row is honest data and is copied through as-is.
"""

import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

STAMP = re.compile(r"\[(\d+):(\d+(?:[.:]\d+)?)\]")
ROW = re.compile(r"^\s*(\d+):(\d+(?:[.:]\d+)?)\s*\|\s*(\d+):(\d+(?:[.:]\d+)?)\s*\|")


def secs(m, s):
    return int(m) * 60 + float(s.replace(":", "."))


def norm(t):
    """For comparing lyric text: collapse whitespace, drop zero-width marks."""
    t = t.replace("", "").replace("‌", "").replace("‍", "")
    return re.sub(r"\s+", " ", t).strip()


def stamp(t):
    """Seconds -> `m:ss.ss`.

    The format matters and is not obvious. Song Timer writes `1:04.74`, and so
    does the renderer's parser. Writing bare seconds (`64.74`) produces a file
    that looks completely reasonable and is rejected by every row with
    "unreadable time" -- which is what happened on the first run of this script.
    A plausible wrong file is worse than none, and this one was plausible.
    """
    m = int(t // 60)
    return "%d:%06.3f" % (m, t - m * 60)


def expand_lrc(path):
    """[(time, text)] -- one cue per TIMESTAMP, ordered by time.

    This is the part the .lrc format hides: several timestamps on one line
    means the line is sung several times, and each is its own cue with its own
    end. Treating it as one cue with one start throws away the rest of the song.
    """
    out = []
    for line in io.open(path, encoding="utf-8").read().split("\n"):
        stamps = STAMP.findall(line)
        if not stamps:
            continue
        text = STAMP.sub("", line).strip()
        if not text:
            continue
        for m, s in stamps:
            out.append((secs(m, s), text))
    out.sort(key=lambda x: x[0])
    return out


def read_ends(path):
    rows = []
    for line in io.open(path, encoding="utf-8").read().split("\n"):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = ROW.match(line)
        if not m:
            continue
        text = line.split("|", 2)[2].strip() if line.count("|") >= 2 else ""
        rows.append((secs(m.group(1), m.group(2)), secs(m.group(3), m.group(4)),
                     text))
    return rows


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    folder, lrc_path, end_path = sys.argv[1], sys.argv[2], sys.argv[3]
    for p, what in ((lrc_path, ".lrc"), (end_path, "end file")):
        if not os.path.exists(p):
            sys.exit("  no such %s: %s" % (what, p))

    base = os.path.splitext(os.path.basename(lrc_path))[0]
    out_path = os.path.join(folder, base + ".ends.txt")
    if os.path.exists(out_path):
        rows = [l for l in io.open(out_path, encoding="utf-8").read().split("\n")
                if l.strip()]
        if rows:
            sys.exit("  %s already has %d row(s) -- not overwriting."
                     % (os.path.basename(out_path), len(rows)))

    cues = expand_lrc(lrc_path)
    ends = read_ends(end_path)
    print("  %s" % base)
    print("     .lrc  expands to %d cues (one per timestamp)" % len(cues))
    print("     ends  has %d rows" % len(ends))

    if len(cues) != len(ends):
        print("")
        print("     REFUSING: %d cues but %d end rows. Pairing them positionally"
              % (len(cues), len(ends)))
        print("     would attach the wrong end to some cue, which is worse than")
        print("     having no ends file at all. Fix the export, or use --allow-short.")
        return 1

    # Prove the pairing with the TEXT before writing anything.
    mismatch = None
    for i, ((ct, cx), (es, ee, ex)) in enumerate(zip(cues, ends)):
        if norm(cx) != norm(ex):
            mismatch = (i, cx, ex, ct, es)
            break
    if mismatch:
        i, cx, ex, ct, es = mismatch
        print("")
        print("     REFUSING: cue %d text does not match the end file." % i)
        print("       .lrc  at %.2fs: %s" % (ct, cx[:60]))
        print("       ends  at %.2fs: %s" % (es, ex[:60]))
        print("     These are different takes, or the export is unordered.")
        return 1

    # Also sanity-check the TIMES. Text matching proves the pairing; a start that
    # is minutes away from the cue's own time means the two files are not in
    # playing order together, even though the words agree.
    worst = max(abs(cues[i][0] - ends[i][0]) for i in range(len(cues)))
    if worst > 1.0:
        print("")
        print("     REFUSING: text matches but the largest start-time difference is")
        print("     %.2fs, so the files are not in the same order." % worst)
        return 1

    with io.open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        for (ct, _cx), (_es, ee, ex) in zip(cues, ends):
            fh.write("%s | %s | %s\n" % (stamp(ct), stamp(ee), ex))

    clamped = sum(1 for i in range(len(cues))
                  if ends[i][1] > (cues[i + 1][0] if i + 1 < len(cues) else 1e9))
    print("     all %d rows matched by BOTH text and time (worst %.3fs)"
          % (len(cues), worst))
    print("     wrote %s" % os.path.basename(out_path))
    if clamped:
        print("     note: %d end(s) ran past the next line's start and will be"
              % clamped)
        print("     clamped to it. That is the tapped data, not an error.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
