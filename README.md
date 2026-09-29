# nepali-legacy-fonts

Make **any** legacy Nepali font render inside **Remotion** (and Chromium) —
the fonts from [anepali.com](https://www.anepali.com) that predate Unicode and
carry their Devanagari glyphs on ASCII codepoints.

Built for [lyric-video-remotion](https://github.com/mhzsajan/lyric-video-remotion),
usable anywhere else too.

---

## The problem

Nepali design fonts are mostly **legacy**: they were made for Preeti-era
workflows, where you typed ASCII and the font's ASCII glyphs *were drawn as*
Devanagari. Such a font has:

- **0 Devanagari codepoints** in its `cmap`
- **no GSUB/GPOS** shaping tables

Chromium (and therefore Remotion) refuses them for real Unicode text and
silently falls back per character. No error, no warning — you just get the
wrong typeface mid-word. `--font "AMS Manthan"` on its own does nothing.

The known workaround is to transcode the **text** into the font's own key
layout. That only works if you know the font's layout, and there is nowhere to
look one up:

- The font file cannot tell you — there is nothing inside it that records what
  `;` was meant to be.
- Inferring it from glyph outlines is unreliable; visual transcription of a
  key map has already produced wrong letters (द/ध, श/ष).
- `npttf2utf` ships five Nepali layouts (Preeti, Sagarmatha, Kantipur,
  PCS NEPALI, FONTASY_HIMALI_TT). Most of the popular fonts speak **none**
  of them.

Rendering Allare with `ams.manthan.ttf` and Preeti keys gives exactly the
failure this package removes — glyphs collapsed onto each other and a literal
`==` where the danda should be, because AMS Manthan is not a Preeti font.

## The fix

**aNepali publishes the answer.** Every font page renders a character table
where each cell is a **key**, drawn in that font, under a Devanagari category
heading. This package reads that table and emits the font's own
`key → Unicode` layout.

```
Unicode lyrics ──► this package ──► font's own keys ──► the font ──► correct Devanagari
```

### Why the reading is trustworthy

The page gives keys but not the Devanagari each slot means. The order is
calibrated off the **Preeti** page, where `npttf2utf` is ground truth for
every key — so "the 14th consonant slot is श" is *read off Preeti*, not
assumed. That calibration is then asserted, not trusted:

```
(Vowels)        13 keys -> 13 distinct Devanagari
(Consonants)    36 keys -> 36 distinct Devanagari
(Numbers)       10 keys -> 10 distinct Devanagari
(Matras)        13 keys -> 13 bare matras
```

No collisions. If the site ever changes, `slot_order()` **refuses to guess**
rather than emitting a plausible, wrong map.

Every generated map is then checked against the actual `.ttf`: each key must
resolve to a real glyph, or the map is rejected.

## Install

```bash
pip install fonttools npttf2utf
```

`npttf2utf` is required — it supplies `map.json` and the decoder used to
verify round-trips. **Without it the whole legacy path fails** with a
`FileNotFoundError` on `map.json`.

## Use

```bash
# 1. see what a font is
py scripts/font_survey.py "path/to/fonts"

# 2. generate its layout, checking it against the real .ttf
py scripts/anepali_charmap.py ams-manthan \
    --font "path/to/ams.manthan.ttf" \
    --out layouts/ams-manthan.json

# 3. hand it to the renderer
node render.mjs song.mp3 song.lrc \
    --legacy-font ams.manthan.ttf \
    --layout-file layouts/ams-manthan.json
```

## Tools

| Script | What it does |
|---|---|
| `anepali_charmap.py` | Generate a layout from an anepali font page. `--font` validates every key against the `.ttf`. |
| `calibrate_slots.py` | Prove the slot order against npttf2utf. Run this first when a font looks wrong. |
| `diff_slots.py` | Print two font pages side by side, per category. Shows where they diverge. |
| `font_survey.py` | Classify a folder: `UNICODE-OK` / `LEGACY` / `NO-SHAPING`. |
| `layout_probe.py` | Group fonts by outline profile — do they share a layout? |

## Two things this deliberately does NOT do

**Symbols.** aNepali publishes a symbols section but it is not calibratable —
the same 29 slots hold *different characters* on different pages:

```
preeti       . ॥ ¿ < Û - _ [ ] { } , = M Ù – _ ± Ö * ÷ Ü & @ # $ € £ ¥
ams-manthan  । ॥ @ ? ! ( ) [ ] { } , . : ; - _ + = * / % & @ # $ € £ ¥
```

It is also unnecessary: a legacy font already keeps its Devanagari
punctuation on the ASCII codepoints, so a comma or full stop passes through
the transcoder untouched and the font draws its own glyph. Mapping them twice
is what produced the literal `==`.

**Font conversion.** Rebuilding a legacy font as Unicode would mean authoring
a `cmap` *and* GSUB ligature tables with no ground truth to check against.
Converting the text needs neither.

## Integration notes for lyric-video-remotion

Three changes are needed on the Remotion side; all three are in the fork at
[`mhzsajan/lyric-video-remotion`](https://github.com/mhzsajan/lyric-video-remotion):

1. `layout_encoder.load_extra_layouts(path)` — merge a generated layout so the
   transcoder can target it.
2. `render.mjs --layout-file` — pass it through to `lrc_legacy.py`.
3. **The preview frame-range fix.** `render.mjs` passed
   `--frames=0-<lastCue+2s>` while `calculateMetadata` set the duration from
   `max(audio, lastCue)`. On any song where the audio is shorter than its own
   last cue plus 2s the range ran past the end and Remotion refused:
   *`durationInFrames ... 6257, but frame range 0-6259`*. The cap now lives in
   `calculateMetadata` so one place owns the length.

`--prepare-only` (transcode and register the font, skip the render) plus
`remotion still` makes checking a new font a few seconds instead of a full
render.

## Status

| Font | Layout | Result |
|---|---|---|
| Abhinav | Preeti | Works (pre-existing) |
| AMS Manthan | generated | **Works** — verified on a rendered frame |

Other layouts (Sagarmatha, Kantipur, PCS NEPALI, FONTASY_HIMALI_TT) remain
available from `npttf2utf` directly. Verify each font with a rendered frame
before shipping; `docs/METHOD.md` explains the method and its limits.

## Licence

The generated layouts describe each font's own key encoding as published by
its author. The **fonts themselves** are not included and keep their authors'
own terms.
