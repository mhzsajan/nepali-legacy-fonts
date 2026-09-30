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

## Preferred fonts, and what is fixed

**[`README.md` — "Preferred fonts"](README.md#preferred-fonts)** holds a
curated list of 42 fonts with the exact command for each, a **Status** table
of what is verified versus what is not, and the slugs for tooling. Read it
before recommending a font to anyone.

The short version:

- **Three tiers, and only one cannot go wrong.**
  [`README.md` — "Which fonts work without issue"](README.md#which-fonts-work-without-issue)
  has the table and all 58 names:
  **Tier A (58 `UNICODE`)** — native codepoints, nothing to get wrong;
  **Tier B (79 `GENERATED`)** and **Tier C (77 `PREETI`)** — verified, but
  carry the five characters below.
  **If you are asked for a font that works without issue, answer from Tier A
  only.**
- **42 of 42 preferred fonts are usable.** 29 `GENERATED` (layout file in
  `layouts/`), 10 `PREETI` (`--layout Preeti`), 3 `UNICODE` (`--font`).
- **"Usable" is not "song-tested".** For the list of fonts that have rendered
  a full real lyric video and passed a human eye-check — currently 11 of the
  42 — read [`docs/RENDER-TESTED.md`](docs/RENDER-TESTED.md) **before
  recommending any font for an actual video**. Notably: 5 "PREETI" fonts
  print raw ASCII with no error, and 2 PREETI fonts (deepankar, abhinav)
  spell some words wrong at the glyph level despite passing every check.
- **79 of 214** fonts are `GENERATED` overall;
  `py scripts/verify_layouts.py --all` reports **79 passed, 0 failed**. The
  `NOTABLE` class is empty — nothing needs a hand-written map.
- **AMS 1, 2, 4, 5 and 7** (all on the preferred list) were blocked as
  `NOTABLE` because the cell CSS selector was built from the catalogue slug
  (`font-ams-1`) while aNepali paints `font-ams-calligraphy-1`.
  `anepali_charmap.table_class()` resolves it from the page now.
- ⚠️ **Never describe a layout as proven.** Verification proves every key
  reaches a *real glyph* in that font's `.ttf`. It cannot prove the glyph is
  the *right* one — `द` and `ध` look nothing alike to a human and nothing
  alike to a hash. Only **AMS Manthan** and **AMS Aakash** have been
  confirmed on a rendered frame.
- ❌ **Broken for every legacy font, and unfixable from the source:**
  `ङ`, `ञ`, `ज्ञ`, the virama `्` and the candrabindu `ँ`. aNepali publishes
  those slots as Devanagari rather than as a key, so there is nothing to
  read. A word containing one renders those characters in a fallback
  typeface mid-word, with no error. The 3 `UNICODE` preferred fonts
  (`Arya`, `Kalam`, `Rajdhani`) do not have this problem.

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
layouts/<slug>.json  79 generated maps
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
hand-written map, and the tool should not pretend otherwise. No font is in that
state today: the eight `AMS Calligraphy` fonts that were are now `GENERATED`,
because the cell CSS class is resolved from the page by `table_class()` instead
of being assumed to equal `font-<slug>`.

## Before using any legacy font, check it will not corrupt words

The legacy path can pass an unmapped Devanagari character straight through to
a font that has no glyph for it, and Chromium then substitutes a *different*
font for that character. The word comes out drawn in two typefaces and the
stray mark can read as a `0` or an `O` — which is why this gets mistaken for
"the font is a bit odd" and shipped.

```bash
py scripts/passthrough.py layouts/<slug>.json "song.lrc"
```

Any output beyond "Every Devanagari character has a key" means words will be
corrupted. On real Nepali lyrics AMS Manthan fails this on 34 of 110 words —
virama, candrabindu and nya have no key.

**Then check the encoding itself:**

```bash
py scripts/diag_encode.py layouts/<slug>.json --lrc "song.lrc"
```

This prints the encoder's keys beside the source, which is the only way to
see a wrong matra order. A pre-base i-matra that kept its carrier writes a
stray KA and turns `रिसले` into `किस्तो` — valid Devanagari, wrong word, no
error anywhere else.

**Then read the render log.** `!! not round-trip exact: 'x' -> 'keys'` on
stderr means that word is wrong. Treat it as a stop condition; a clean run
prints only the `OK ... lines encoded` line.

`docs/LEGACY-PITFALLS.md` covers all of this with measurements.

## There are 58 Unicode fonts, not four — read this before saying "we only have a few"

The most common wrong answer in this repo is that only a handful of fonts are
usable for a lyric video. **58 of the 214 are `UNICODE`, and every one of them
is structurally safe** — see "The better answer is usually a Unicode font" below.
They have native Devanagari codepoints, so there is no key layout to transcode
into and therefore no way for a word to come out spelled wrongly. That is the
whole failure mode this repository's tooling exists to prevent, and Tier A does
not have it.

Only **4 of the 58** had ever been rendered and eye-checked, which is why
`verdicts.json` lists so few as `working`. That number is a measure of **past
effort, not of availability**. Reading it as a measure of what is usable is the
mistake, and it has already cost a plan that was built around "there are not
seven fonts" when there were fifty-eight.

### Qualifying the rest, in the right order

Two tools, and the order matters — the expensive one is last, on purpose.

```bash
# 1. MECHANICAL, milliseconds. Reads each font's own cmap and asks whether every
#    codepoint the real songs use is covered. Filters 214 -> the plausible ones.
py scripts/qualify_unicode.py "H:\Lyric Video Making Folder"

# 2. VISUAL, one page. Every surviving font, base64-embedded, Chromium-shaped,
#    showing the SAME three real lyric lines so the typeface is the only variable.
py scripts/unicode_showcase.py "H:\Lyric Video Making Folder" --per-page 12
```

`qualify_unicode.py` prints a shortlist and **no verdict**, and that is the point.
Coverage is necessary and not sufficient: a font can cover every codepoint and
still set a conjunct badly or put the i-matra on the wrong side. Only a person
looking at `unicode_showcase.py` output can decide that.

`unicode_showcase.py` exists because fifty-three separate specimen files is the
wrong shape for "which do you want". It is also the only instrument here that
shows all the candidates **on the same lines**, so a face can be compared across
pages. Two things to know about it:

- the fonts are **embedded as base64**, not `src: url(file://...)`. A blocked
  file-origin fetch fails SILENTLY: the page falls back to Nirmala UI and every
  row looks identical and perfect. Embedding removes the second fetch.
- Chrome's `--screenshot` captures the **window, not the page**, so the height
  is measured from the row count. The first version left it at a default and
  produced a clean, successful-looking PNG of 14 of 58 fonts.

There is deliberately **no size-based truncation check** in the showcase. One
existed and fired on every page, because a mostly-black image compresses to
~0.1 MB whether or not it is complete. A heuristic that is always wrong trains
you to ignore it.

### What "working" means here, and who decides

`verdicts.json` has four states. `broken` and `failed` are refused. `untested`
warns and proceeds — **that is the state where testing happens**. Promoting a
font to `working` requires a rendered frame and a human eye-check, not a script.
`check_verdicts.py` will accept a `working` you wrote by hand; that is a
deliberate trust boundary, not an oversight.

## The better answer is usually a Unicode font

If no specific classic typeface is required, `--font "Nirmala UI"` removes
every failure mode on this page at once. Nirmala UI ships with Windows 11, so
it needs no install and behaves identically on any machine. 58 of the 214
fonts are Unicode, and most of the rest of this repository's tooling exists
only for the case where you specifically need a legacy look.

Do not reach for the legacy path by default. Ask first whether a Unicode
font will do.

## Common tasks

```bash
py scripts/which_fonts.py fonts/            # what do I type for each font?
py scripts/passthrough.py layouts/ams-manthan.json "song.lrc"   # will words corrupt?
py scripts/diag_encode.py layouts/ams-manthan.json --lrc "song.lrc"  # is the encoding right?
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
