# Getting started

Clone it, install three packages, done. Nothing depends on the machine it was
built on.

```bash
git clone https://github.com/mhzsajan/nepali-legacy-fonts
cd nepali-legacy-fonts
pip install -r requirements.txt
```

Requires **Python 3.9+**. Node is only needed if you also want to render with
Remotion.

## Prove the install works

```bash
py scripts/verify_layouts.py ams-manthan
```

That one command exercises everything: `npttf2utf`, the network, the page
cache, the layout files and `fontTools`. If it prints `PASS`, the install is
good.

## Find out what to type for a font

```bash
py scripts/which_fonts.py "C:\path\to\your\fonts"
```

It matches the folder against the catalogue and prints the exact command for
each one:

```
font file                  slug                     class      action
----------------------------------------------------------------------------
ams.manthan.ttf            ams-manthan              GENERATED  --layout-file layouts/ams-manthan.json
mukta.ttf                  mukta                    UNICODE    install it, then --font "<family>"
```

## Use a font in a render

```bash
# 1. check the cues -- instant, no render
node render.mjs song.mp3 song.lrc --report-only

# 2. transcode and register the font, skip the render
node render.mjs song.mp3 song.lrc --legacy-font ams.manthan.ttf \
    --layout-file layouts/ams-manthan.json --prepare-only

# 3. look at ONE frame
npx remotion still src/index.js LyricOverlay out/check.png --frame=5900 --props=out/props.json

# 4. the real render
node render.mjs song.mp3 song.lrc --no-audio \
    --legacy-font ams.manthan.ttf --layout-file layouts/ams-manthan.json \
    --mode roam --word-anim karaoke --letter-anim pop --letter-var 0.03
```

**Step 3 is not optional.** A wrong layout does not error — it renders the
wrong letters. That is the failure this whole repository exists to prevent, so
look at the frame before committing to a four-minute render.

## On Windows

| Trap | Fix |
|---|---|
| The interpreter is `py`, not `python` | Use `py`. `py -3` to pin a version. |
| `pip` and `py` disagree | Install with `py -m pip install -r requirements.txt` |
| Devanagari output raises `UnicodeEncodeError` | The scripts already handle this. Keep `sys.stdout.reconfigure(encoding="utf-8")` if you edit one. |
| `npttf2utf` missing → `FileNotFoundError: map.json` | `pip install npttf2utf`. Required, not optional. |

## What to read next

| File | What it is for |
|---|---|
| `README.md` | What the problem is, how it was solved, coverage |
| `AGENTS.md` | Orientation for an AI agent, and the traps |
| `docs/METHOD.md` | How the layouts are derived, and what that does **not** prove |
| `docs/REMOTION-PATCH.md` | The renderer changes this needs |
| `docs/FONTS-DIR.md` | The fonts, and the licensing question |

## If something looks wrong

Run the calibration first:

```bash
py scripts/calibrate_slots.py
```

It proves the published table still decodes 1:1 against `npttf2utf`'s Preeti
map. If the counts are not 13/13 vowels, 36/36 consonants and 10/10 numbers,
**the site has changed** — stop and investigate rather than relaxing the
check. An off-by-one in the slot order shifts every later character and
produces text that looks correct and is wrong.
