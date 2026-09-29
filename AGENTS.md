# AGENTS.md

Orientation for an AI agent picking this up cold, on a machine that is not the
one it was built on. Read this before running anything.

## What this is

A set of **generated font layouts** plus the tooling that produced them.
It makes legacy Nepali fonts render inside **Remotion** and **Chromium**.

A legacy Nepali font carries its Devanagari glyphs on ASCII codepoints, with
**no Devanagari cmap and no GSUB**. Chromium therefore substitutes another
font character by character, silently. The fix is to transcode the lyrics into
the font's own key layout — which requires knowing that layout, which is what
this repository provides.

Read `README.md` for the problem and the reasoning, and `docs/METHOD.md` for
what the method does and does not prove. `docs/METHOD.md` is the one to read
before trusting a result.

## First run on a new machine

Nothing here depends on the machine it was built on. Python 3.9+ and Node 16+
are the only requirements; there is no dependency on any local path, no
absolute path in any script, and no state outside the repo except a temp
directory.

```bash
git clone <this repo>
cd nepali-legacy-fonts
pip install -r requirements.txt
py scripts/verify_layouts.py ams-manthan      # proves the install works
```

`verify_layouts.py` is the best smoke test: it exercises `npttf2utf`, the
network, the cache, the layout files and `fontTools` in one command.

### Windows specifics that are easy to lose an hour to

| Trap | What happens | Do this |
|---|---|---|
| The interpreter is `py`, not `python` | `python` may not exist at all | Use `py`. `py -3` to pin. |
| Console is cp1252 | Any script printing Devanagari dies with `UnicodeEncodeError` | Every script here already calls `sys.stdout.reconfigure(encoding="utf-8")`. Keep it if you edit one. |
| `pip install -r requirements.txt` is per-interpreter | Packages land somewhere `py` cannot see | Confirm with `py -m pip list`, not bare `pip list`. |
| No `System.Web.HttpUtility` on PowerShell 5.1 | HTML decoding raises | Use Python for HTML, as these scripts do. |
| `npttf2utf` missing | `FileNotFoundError: map.json` from *any* legacy render | `pip install npttf2utf`. It is required, not optional. |

The `npttf2utf` one is the important one. It is a hard dependency of the whole
approach and its absence produces a bare `FileNotFoundError` that says nothing
about what to do.

## What is safe to run

- Anything in `scripts/`. They are read-only with respect to this repo, apart
  from `.cache/`, `dist/` and `verify.json`, all gitignored.
- They are polite to aNepali by default: 4–6 workers and a short pause. Keep
  it that way. It is a free community project and a full sweep is 214 page
  requests.
- The page cache in `.cache/` makes a re-run of `sweep.py` free. Do not commit
  it and do not delete it unless you want to refetch.

## What needs care

**Never guess a slot order.** `anepali_charmap.slot_order()` calibrates the
published table against Preeti using `npttf2utf` and *asserts* the result
(13/13 vowels, 36/36 consonants, 10/10 numbers, 13/13 matras, all distinct).
If those assertions fail, the site has changed: **stop and investigate, do not
relax the check.** An off-by-one in the slot order shifts every later character
and produces text that looks correct and is wrong.

**A layout passing `verify_layouts.py` is not a layout that is right.**
Verification proves every key resolves to a real glyph. It cannot prove the
glyph is the *correct* one for that character. The only check that does that is
rendering a frame and looking at it:

```bash
node render.mjs song.mp3 song.lrc --legacy-font font.ttf \
    --layout-file layouts/font.json --prepare-only
npx remotion still src/index.js LyricOverlay out/check.png --frame=5900 --props=out/props.json
```

Do this for any new font. It costs seconds and catches what nothing else can.

**`ङ`, `ञ`, `ज्ञ` are not in any generated layout.** They have no Preeti key
to calibrate from, and the site publishes those three slots as Devanagari
rather than as a key. They will render as a blank box. `ज्ञ` occurs in real
lyrics, so grep the lyrics for it before shipping a render.

**Do not map symbols.** The published symbols section is not calibratable —
the same 29 slots hold different characters on different pages. Leave
punctuation alone; a legacy font already holds its Devanagari punctuation on
the ASCII codepoints.

## Where things are

```
anepali_charmap.py   generate a layout from a font page   <- the core
verify_layouts.py    check a layout against the real .ttf  <- the gate
sweep.py             walk all 214 fonts, write layouts/ + sweep.json
which_fonts.py       "what command do I type for THIS font?"
fetch_fonts.py       download font binaries
make_releases.py     pack the per-class release archives
calibrate_slots.py   prove the slot order (run when a font looks wrong)
diff_slots.py        compare two font pages side by side
font_survey.py       classify a folder of fonts
layout_probe.py      group fonts by outline profile
layouts/<slug>.json  71 generated maps
fonts/<slug>/        214 fonts, ~113 MB, gitignored content is documented
sweep.json           the catalogue with each font's class
```

## Adding a font that is not in the sweep

1. `py scripts/anepali_charmap.py <slug> --out layouts/<slug>.json`
2. `py scripts/verify_layouts.py <slug>` — must reach 0 missing
3. Render one frame and look at it
4. Only then use it

If the page publishes no character table, the tool says `NOTABLE` and refuses
to invent a layout. That is the correct outcome — such a font needs a
hand-written map, and the tool should not pretend otherwise.

## Common tasks

```bash
py scripts/which_fonts.py fonts/            # what do I type for each font?
py scripts/sweep.py --report                # summarise without refetching
py scripts/sweep.py --only ams-manthan      # one font
py scripts/verify_layouts.py --all          # check every generated layout
py scripts/calibrate_slots.py               # is the site still consistent?
```

## Conventions

- Python 3.9+ compatible, standard library plus `fonttools` / `npttf2utf` /
  `pillow`. No other dependencies.
- Comments explain **why**, especially why an approach was rejected. Several
  here look over-cautious until you know what they are preventing.
- Windows-first (that is where this is used), but nothing is
  Windows-only except the `py` examples in docstrings.
- Every script prints a plain-ASCII summary by default; Devanagari is only
  emitted when the caller asks for it.
