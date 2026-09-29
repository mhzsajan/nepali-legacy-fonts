# What this repository solves

## The problem, in one paragraph

Nepali design fonts are mostly **legacy**: they were made for Preeti-era
workflows, where you typed ASCII and the font's ASCII glyphs *were drawn as*
Devanagari. Such a font has **zero Devanagari codepoints** in its `cmap` and
**no GSUB/GPOS** tables. Chromium — and therefore Remotion — refuses them for
real Unicode text and silently substitutes another font character by
character. No error, no warning; you just get the wrong typeface mid-word.
`--font "AMS Manthan"` on its own does nothing at all.

The established workaround is to transcode the lyrics into the font's own key
layout. That works — but it only works if you know the font's layout, and
**there was nowhere to look one up**:

- the font file cannot say, because there is nothing inside it that records
  what `;` was meant to be;
- reading the meaning off glyph outlines is unreliable, and a visual
  transcription of a key map had already produced wrong letters here
  (द/ध and श/ष confusion);
- `npttf2utf` ships five Nepali layouts (Preeti, Sagarmatha, Kantipur,
  PCS NEPALI, FONTASY_HIMALI_TT) and most of the popular fonts speak **none**
  of them.

Feeding Preeti keys to `ams.manthan.ttf` gives exactly what the workaround is
supposed to prevent: glyphs collapsed onto each other, and a literal `==`
where the danda should be.

## The fix

**aNepali publishes a character table for every font.** Each cell is a **key**,
drawn in that font, under a Devanagari category heading. So a font's layout
can be **read** rather than guessed.

```
Unicode lyrics ──► this repo ──► the font's own keys ──► the font ──► correct Devanagari
```

### Why the reading is trustworthy

The page gives keys but not the Devanagari each slot means. The order is
calibrated off the **Preeti** page, where `npttf2utf` is ground truth for every
key — so "the 14th consonant slot is श" is read off Preeti, not assumed.

That calibration is then **asserted, not trusted**:

```
(Vowels)        13 keys -> 13 distinct Devanagari
(Consonants)    36 keys -> 36 distinct Devanagari
(Numbers)       10 keys -> 10 distinct Devanagari
(Matras)        13 keys -> 13 bare matras
```

No collisions. If the site ever changes, the tool **refuses to guess** rather
than emitting a plausible, wrong map — an off-by-one in the slot order shifts
every later character and produces text that looks fine and is wrong.

---

# Coverage

The whole [aNepali catalogue](https://www.anepali.com) is swept — **214 fonts**:

| Class | Count | What it means |
|---|---:|---|
| `UNICODE` | 58 | Renders in Chromium as-is. Nothing to do. Mostly SIL OFL. |
| `PREETI` | 77 | npttf2utf already has it — `--layout Preeti`. |
| `GENERATED` | 71 | Layout read from the page — `layouts/<slug>.json`. |
| `NOTABLE` | 8 | Legacy, but the site publishes no character table. |

## Verified — all 71 generated layouts

```bash
py scripts/verify_layouts.py --all
```

```
71 passed, 0 failed, 0 not available
```

This downloads each font and checks every generated key against **that font's
real glyph table**. It is the check a render cannot do: a key can exist in the
font and still point at the *wrong* glyph, which renders the wrong letter
rather than raising an error.

Two fonts are additionally confirmed on an actual **rendered frame** through
Remotion → Chromium: **AMS Manthan** and **AMS Aakash**, both correct.

---

# Quick start

```bash
pip install fonttools npttf2utf pillow

# What do I type for THIS font?
py scripts/which_fonts.py "path/to/your/fonts"

# Generate a layout, validated against the real .ttf
py scripts/anepali_charmap.py ams-manthan --font "ams.manthan.ttf" --out layouts/ams-manthan.json

# Verify a layout against the font binary
py scripts/verify_layouts.py ams-manthan

# Render (from a lyric-video-remotion checkout)
node render.mjs song.mp3 song.lrc --legacy-font "ams.manthan.ttf" \
    --layout-file layouts/ams-manthan.json --prepare-only
npx remotion still src/index.js LyricOverlay out/check.png --frame=5900 --props=out/props.json
```

That `--prepare-only` + one `still` costs **seconds** and is the step that
catches a wrong font. A bad map does not error — it renders the wrong letters,
which is exactly the failure that is easy to miss in a four-minute video.

---

# Releases

Pre-built archives are attached to the **Releases** page, one per class:

| Archive | Contents |
|---|---|
| `nepali-fonts-unicode.zip` | 58 fonts, no layout needed |
| `nepali-fonts-preeti.zip` | 77 fonts, `--layout Preeti` |
| `nepali-fonts-generated.zip` | 71 fonts **+ their layouts** |
| `nepali-fonts-notable.zip` | 8 fonts, no layout published |
| `nepali-fonts-layouts-only.zip` | The 71 layout files alone |

The `generated` archive ships with its layouts inside, because a generated font
is useless without its map and shipping them apart is how someone ends up
rendering Preeti keys into a non-Preeti font.

Each archive carries `docs/FONTS-DIR.md` — the readmes are the licences, and
they travel with the fonts for a reason.

---

# Tools

| Script | What it does |
|---|---|
| `which_fonts.py` | Match a local font folder to the sweep; print the exact command per font. |
| `anepali_charmap.py` | Generate a layout from a font page. `--font` validates every key against the `.ttf`. |
| `verify_layouts.py` | Check a generated layout against the real font binary. Catches wrong-glyph mappings. |
| `sweep.py` | Walk the whole catalogue, classify every font, write `layouts/` + `sweep.json`. |
| `fetch_fonts.py` | Download font binaries (never committed by default). |
| `make_releases.py` | Pack the per-class release archives. |
| `calibrate_slots.py` | Prove the slot order against npttf2utf. Run this when a font looks wrong. |
| `diff_slots.py` | Print two font pages side by side, per category. |
| `font_survey.py` | Classify a folder: `UNICODE-OK` / `LEGACY` / `NO-SHAPING`. |
| `layout_probe.py` | Group fonts by outline profile. |

---

# Integration with lyric-video-remotion

Three changes are needed, all in
[`mhzsajan/lyric-video-remotion`](https://github.com/mhzsajan/lyric-video-remotion)
and mirrored in `remotion-patch/`:

1. `layout_encoder.load_extra_layouts(path)` — merge a generated layout.
2. `render.mjs --layout-file` — pass it to the transcoder.
3. **The preview frame-range fix** (below).

`docs/REMOTION-PATCH.md` has the full list and the copy commands.

## Two bugs that made the whole path unusable

Neither is about fonts, and both blocked everything before a font could even
be tried.

**`npttf2utf` was never a declared dependency.** `layout_encoder.py` reads its
five layouts from the package's `map.json`, so with the package absent every
`--legacy-font` render died at once:

```
FileNotFoundError: 'C:\...\scripts\map.json'
```

Nothing in that message says "install a Python package", which is a large part
of why this looked unfixable.

**Every preview render crashed.** `render.mjs` passed
`--frames=0-<lastCue + 2s>` while `calculateMetadata` derives the duration
from `max(audio length, last cue)`. Whenever a song's audio is shorter than its
own last cue plus two seconds the range ran past the end:

```
Error: The "durationInFrames" of the <Composition /> was evaluated to be
6257, but frame range 0-6259 is not within the frame range of the
composition (0-6256).
```

Allare is exactly that case — 417.0 s of audio against a 415.3 s last cue. The
cap now lives in `calculateMetadata`, so one place owns the length and the two
cannot drift apart again.

---

# Three characters are not covered

`ङ`, `ञ` and `ज्ञ` are absent from every generated layout.

They have no Preeti key to calibrate from, and aNepali publishes those three
consonant slots as **Devanagari rather than as a key**. Recording them as keys
asked the transcoder to emit Devanagari into a font with zero Devanagari
codepoints, so they rendered as **blank boxes**. They are now dropped from
every layout and reported loudly instead.

`ज्ञ` is the one that actually occurs in lyrics — check any word containing it
before shipping. `docs/METHOD.md` has the detail.

---

# Two things this deliberately does not do

**Symbols are not mapped.** aNepali publishes a symbols section, but the same
29 slots hold *different characters* on different pages:

```
preeti       . ॥ ¿ < Û - _ [ ] { } , = M Ù – _ ± Ö * ÷ Ü & @ # $ € £ ¥
ams-manthan  । ॥ @ ? ! ( ) [ ] { } , . : ; - _ + = * / % & @ # $ € £ ¥
```

Positional assignment would bind Preeti's `¿` to a Manthan slot that is really
a bracket. It is also unnecessary: a legacy font already keeps its Devanagari
punctuation on the ASCII codepoints, so a comma or full stop passes through
the transcoder untouched and the font draws its own glyph. Mapping them twice
is what produced the literal `==`.

**Fonts are not converted.** Rebuilding a legacy font as Unicode would mean
authoring a `cmap` *and* GSUB ligature tables with no ground truth to check
against. Converting the text needs neither.

---

# Fonts included

`fonts/` holds all 214 fonts unpacked from their published archives — 479
`.ttf` files, ~113 MB. This repository is **private**, for your own use.

> aNepali's own words: *"The fonts presented on this website are their
> authors' property, and are either freeware, shareware, demo versions or
> public domain. Please look at the readme-files in the archives or check the
> indicated author's website for details, and contact him/her if in doubt."*

That is a statement of varying status, not a licence. Each font's terms belong
to its author, several are demo or shareware, and at least two here are the
property of a commercial foundry. **Private use does not change what you may
publish or broadcast** — read the readme in a font's folder before it goes on
screen in front of an audience. `docs/FONTS-DIR.md` has the detail.

If a licence matters for a show, the 58 `UNICODE` fonts are mostly SIL OFL and
cover commercial and broadcast use outright.

The **layouts** are the derived work here — a description of each font's own
key encoding — and carry no separate licence question.
