"""gate_probe.py -- run lyric-studio's font gate on a (font, song) pair, safely.

    py scripts/gate_probe.py <song dir> <font slug | UNICODE | PREETI> [--font-file PATH]

WHY THIS EXISTS
---------------
Three of the seven songs have NEPALI filenames. Passing those through a shell
mangles them -- PowerShell rendered "अल्लारे.remotion_start.lrc" as
"???????.remotion_start.lrc" and the gate exited 2 with "no such .lrc", which
reads like a broken gate and is actually a broken ARGUMENT.

So the gate is invoked from Python with the path as a real string, and this
script exists to be the one place that knows that. It prints the gate's own
verdict verbatim, because the point is to see what the gate says, not to
re-derive it here.

A second copy of the gate's logic in this file would be the exact failure the
gate's own docstring warns about -- "a vendored copy, and vendored copies go
stale". So there is none: this spawns the real gate and relays it.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# font_gate.py lives in the SIBLING repo, not here: lyric-studio owns the gate
# because lyric-studio is what renders. The two repositories are siblings under
# one parent, and the first version of this script looked for the gate beside
# itself and reported "COULD NOT RUN" for a gate that works fine.
STUDIO = os.path.join(os.path.dirname(os.path.dirname(HERE)), "lyric-studio")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    song_dir, font = sys.argv[1], sys.argv[2]

    starts = [n for n in os.listdir(song_dir)
              if n.lower().endswith("remotion_start.lrc")]
    if not starts:
        print("no .remotion_start.lrc in %s" % song_dir)
        return 2
    lrc = os.path.join(song_dir, starts[0])

    cmd = [sys.executable, os.path.join(STUDIO, "scripts", "font_gate.py"),
           "--lrc", lrc]
    if font.upper() == "UNICODE":
        cmd += ["--font-file", sys.argv[3]]
    elif font.upper() == "PREETI":
        # A PREETI font has NO layouts/<slug>.json -- by definition. It speaks one
        # of the five layouts npttf2utf knows, and for this class it is Preeti.
        #
        # Asking for --slug instead makes the gate refuse with "no such layout",
        # which is TRUE and USELESS: it looks like the gate caught a word-level
        # problem and in fact only failed to find a file. A gate that refuses for
        # the wrong reason is worse than no gate, because the message reassures
        # you that something was checked.
        cmd += ["--layout", "Preeti"]
    else:
        cmd += ["--slug", font]

    res = subprocess.run(cmd, capture_output=True, text=True,
                         encoding="utf-8", errors="replace")
    print("song   : %s" % starts[0])
    print("font   : %s" % font)
    print("gate   : exit %d  (%s)" % (
        res.returncode,
        "SAFE" if res.returncode == 0
        else "REFUSED" if res.returncode == 1 else "COULD NOT RUN"))
    print("-" * 66)
    sys.stdout.write(res.stdout or "")
    if res.stderr:
        sys.stdout.write(res.stderr)
    print("-" * 66)
    return res.returncode


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
