# Method, and what it does not prove

## Why a legacy font cannot describe itself

A Preeti-era Nepali font has a `cmap` covering ASCII (U+0020–U+007E) plus a
few symbols, and **no GSUB/GPOS**. Nothing inside the file records what a key
was *meant* to be — the encoding lived in the word processor, not the font.
Open it in a modern browser and Chromium substitutes another font character by
character, with no error.

So the encoding has to come from outside the file.

## Why not infer it from glyph outlines

It is possible to hash a glyph's outline and compare fonts — `layout_probe.py`
does exactly that — and it groups the 15 fonts in `01 Fonts` into 15 distinct
profiles. But that measures **typeface identity**, not encoding. A heavier
weight of the same typeface is a different profile with the same key meaning,
and two different typefaces can share an encoding. Outline similarity answers
"are these the same design?", not "what letter is this?".

A visual transcription of a key map has already been shown to be unreliable in
this project (द/ध and श/ष confusion), so the map is read, not guessed.

## What is read, and how it is calibrated

1. **Fetch the Preeti page.** aNepali publishes a character table per font:
   each cell is a key, rendered in that font, under a Devanagari category
   heading (Vowels / Consonants / Numbers / Matras / Conjuncts / Symbols).

2. **Calibrate the slot order from Preeti.** `npttf2utf` knows the meaning of
   every Preeti key, so the Nth Preeti key in a category fixes the Devanagari
   of slot N. Measured: 13/13 vowels, 36/36 consonants, 10/10 numbers, 13/13
   matras — all distinct, no collisions.

3. **Read any other font in that order.** Different keys, same meanings.

The site is internally consistent in slot order: `diff_slots.py preeti
ams-manthan` shows the Devanagari meaning column lining up row for row across
two fonts that share no keys at all (`k`/`Ka`/`ga` versus `s`/`v`/`u`).

## Two details that are easy to get wrong

**The matra carrier.** Matras are published as a consonant plus the mark —
the heading literally reads *"Matras - with 'क'"*. So the cell is `क`'s key
followed by the matra's key. Both sides need stripping:

- npttf2utf decodes Preeti's matra cell to `का`, not `ा` — the carrier
  consonant comes off.
- the cell key is the font's own `क` key, which differs per font (Preeti `s`,
  AMS Manthan `k`) — so `ka` is the cell but the matra is `a`.

Missing either one is what produced the original broken render: consonants
correct, every vowel missing its top line.

**Symbols are skipped, not calibrated.** The same 29 slots hold different
characters on different pages, so a positional assignment would bind Preeti's
`¿` to a Manthan slot that is really a bracket. They are also unnecessary — a
legacy font already holds its Devanagari punctuation on the ASCII codepoints,
so punctuation passes through untouched and the font draws its own glyph.

## What this does not prove

Round-trip verification for a generated layout uses the layout's own inverse
map, because npttf2utf's decoder only knows its five. That proves the
encoder is self-consistent — nothing was mangled in transit — and it does
**not** prove the published map is correct.

That is why the map is checked two other ways, and why a generated map is not
shipped on its own:

1. `anepali_charmap.py --font <ttf>` asserts every key resolves to a real
   glyph. A missing one renders as a blank box; a *mismapped* one renders as
   the wrong letter, which is worse and harder to spot.
2. Render one frame and look at it:

```bash
node render.mjs song.mp3 song.lrc --legacy-font ams.manthan.ttf \
    --layout-file layouts/ams-manthan.json --prepare-only
npx remotion still src/index.js LyricOverlay out/check.png --frame=5900 --props=out/props.json
```

Verified for AMS Manthan: `आहा..` renders correctly, shirorekha continuous.

## Known limits

- `ङ`, `ञ` and `ज्ञ` have no Preeti key to calibrate from, so those three
  slots stay unmapped for generated layouts. They are rare in lyrics; the
  validator reports them rather than guessing.
- Only a single style per font is read. Multi-style families on the site
  publish one table.
- The site is a third party. If it changes, the calibration assertions fail
  loudly instead of producing a quietly wrong map.
