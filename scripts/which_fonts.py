"""which_fonts.py -- what does the sweep say about the fonts I actually have?

The sweep covers aNepali's whole catalogue, but a folder on disk is a
different list. This matches a local folder of .ttf files against the sweep
by slug and prints, per font, what still has to be done: nothing, use Preeti
directly, or pass a generated layout.

It is the "what do I type for this font?" answer, so it prints the exact
command line for each one that needs work.

Usage:
    py scripts/which_fonts.py "E:\\...\\01 Fonts"
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SWEEP = os.path.join(HERE, "sweep.json")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def slugify(name):
    """Best-effort local filename -> aNepali slug.

    The site's slugs are lowercase-hyphenated display names, so this is a
    normalisation, not a derivation. A miss is reported rather than guessed
    at: the sweep is the only thing that knows the real slug list.
    """
    base = os.path.splitext(os.path.basename(name))[0]
    base = re.sub(r"^ams[._]", "ams-", base, flags=re.I)
    base = re.sub(r"[^a-zA-Z0-9]+", "-", base).strip("-").lower()
    base = re.sub(r"-{2,}", "-", base)
    return base


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    with open(SWEEP, encoding="utf-8") as f:
        recs = {r["slug"]: r for r in json.load(f)}

    root = sys.argv[1]
    files = []
    if os.path.isdir(root):
        for n in sorted(os.listdir(root)):
            if n.lower().endswith((".ttf", ".otf", ".ttc")):
                files.append(os.path.join(root, n))
    else:
        files = [root]

    if not files:
        print("  no font files found in " + root)
        return 1

    print(f"\n  {'font file':<26} {'slug':<24} {'class':<10} action")
    print("  " + "-" * 92)

    todo = {"UNICODE": [], "PREETI": [], "GENERATED": [], "NOTABLE": [], "MISSING": []}
    for p in files:
        name = os.path.basename(p)
        slug = slugify(name)
        r = recs.get(slug)
        if not r:
            todo["MISSING"].append((name, slug))
            print(f"  {name[:26]:<26} {slug[:24]:<24} {'?':<10} not in the sweep")
            continue

        cls = r["class"]
        todo.setdefault(cls, []).append((name, slug, p, r))

        if cls == "UNICODE":
            act = 'install it, then --font "<family>" (no transcoding)'
        elif cls == "PREETI":
            act = "--layout Preeti  (default; no layout file needed)"
        elif cls == "GENERATED":
            act = f"--layout-file layouts/{slug}.json"
        else:
            act = "no character table published - needs a hand-made layout"
        print(f"  {name[:26]:<26} {slug[:24]:<24} {cls:<10} {act}")

    print()
    for cls in ("UNICODE", "PREETI", "GENERATED", "NOTABLE", "MISSING"):
        if todo[cls]:
            print(f"  {cls:<10} {len(todo[cls])}")

    if todo["GENERATED"]:
        print("\n  command for a generated-layout font:")
        name, slug, p, r = todo["GENERATED"][0]
        print(f"    py scripts/anepali_charmap.py {slug} --font \"{p}\" "
              f"--out layouts/{slug}.json")
        print(f"    node render.mjs song.mp3 song.lrc --legacy-font \"{p}\" "
              f"--layout-file layouts/{slug}.json")

    if todo["NOTABLE"]:
        print("\n  these publish no character table, so nothing can be read "
              "from them:")
        print("    " + ", ".join(s for _, s, _, _ in todo["NOTABLE"]))
    if todo["MISSING"]:
        print("\n  these filenames did not match a sweep slug:")
        print("    " + ", ".join(f"{n} (tried {s})" for n, s in todo["MISSING"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
