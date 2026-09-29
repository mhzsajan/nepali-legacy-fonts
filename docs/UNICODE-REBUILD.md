# Rebuilding the legacy fonts as Unicode — findings

**Status: proof of concept works, not shipped.** Tested on AMS Manthan only,
on 2026-09-29. Everything below is measured, not assumed.

## The question that prompted this

Three options were put forward for making these fonts work:

1. Fork the Remotion engine from source so it supports them.
2. Switch to a different engine that already supports them.
3. Build the fonts ourselves.

**Option 3 is the right one, and a working PoC now exists. Options 1 and 2
cannot help** — because the refusal happens inside the *font*, not inside the
engine.

## Why forking Remotion cannot work

Remotion does not lay out text. It renders React DOM inside headless Chromium
and lets HarfBuzz do the shaping. The measured contents of the fonts explain
everything:

| Font | Glyphs | Codepoints | Devanagari cps | GSUB | GPOS | GDEF |
|---|---:|---:|---:|---|---|---|
| AMS Calligraphy 1 | 109 | 108 | **0** | no | no | no |
| AMS Aakash | 115 | 113 | **0** | no | no | no |
| AMS Manthan | 134 | 133 | **0** | no | no | no |

Chromium asks the font for `U+0915` and the font answers "nothing here".
Changing the engine does not change that answer — it is a property of the
`cmap` table, which lives in the `.ttf`.

Remotion will accept a custom browser (`--browser-executable`), so a custom
Chromium is *theoretically* the lever. Practically that means owning a Chromium
fork forever to fix a table that is 80 KB and can be edited with `fontTools`.

## Why changing engines does not help

Every mainstream text stack is HarfBuzz over a strict Unicode `cmap`:
Chromium and Firefox, `libass` (ffmpeg, Aegisub), Skia, Pango, Word. They all
refuse these fonts for the same reason, in the same place. The only engines
that help are ones where you place glyphs yourself — and at that point you have
re-implemented the font pipeline rather than fixing the font.

## What is actually inside the fonts

- **Every glyph is one ASCII codepoint.** With no GSUB there is no ligature
  substitution anywhere, so nothing is hidden behind a substitution rule.
- **Glyph names carry no identity.** They are `0061`, `0041`, `0020` — hex
  ASCII. The glyph for `क्ष` cannot be recognised from the file alone. This is
  the "no ground truth" problem that made the README mark Unicode rebuilds as
  deliberately not done.
- **The published layout covers only part of the font.** AMS Manthan has 92
  ASCII glyphs; the layout names 36 of them. The other **56 — 26 of which are
  letters** (`B G H J K L M N P Q S T V X Y Z b c g j l m n p s t v x y z`) —
  have a glyph and no published mapping at all.

That last point matters: the five characters recorded as unfixable
(`ङ`, `ञ`, `ज्ञ`, `्`, `ँ`) are unfixable **from the website**, because aNepali
does not publish those slots. It does not follow that the glyphs are absent
from the font. They are very plausibly sitting among those 26 unidentified
letter glyphs.

## The proof of concept

`scripts/build_unicode.py` inverts a layout back into a `cmap`:

```bash
py scripts/build_unicode.py --font fonts/.../ams.manthan.ttf \
    --layout layouts/ams-manthan.json --out out/ams.manthan.unicode.ttf
```

On AMS Manthan: **36 of 69 entries convert directly**, 33 do not (see below),
0 unusable.

It was then loaded in Chromium (Chrome 152 / Electron 44) through `@font-face`
and probed on a canvas — ink pixels and advance widths, comparing the rebuilt
font (`AMSU`) against the untouched original (`AMS0`), a real Unicode font
(`REF`, Arya), and a deliberately absent family.

| Test | Rebuilt | Original | Absent family | Reading |
|---|---:|---:|---:|---|
| Latin `A` | 26.68 | 26.68 | 33.22 | font is being applied at all |
| `अ` | **26.68** | 37.73 | 37.73 | **AMS Manthan's own glyph drew** |
| `क` | **28.98** | 39.71 | 39.71 | **same** |
| `छ` | **28.66** | 36.39 | 36.39 | **same** |

Of 21 Devanagari characters probed, **15 drew the font's own glyph**. The 6
that still fell back are `आ ई ऐ ओ औ` — exactly the composed characters, and
nothing else. The failure is precisely the predicted one.

**Conclusion: a `cmap` alone is enough for Chromium to treat a legacy font as a
Unicode font.** No GSUB was needed for any of the 36.

### The trap, so nobody repeats it

The first attempt wrote the Devanagari entries into the `(0, 3)` subtable and
left `(3, 1)` untouched. The result verified in Python and was **still
un-mapped in the browser**: Chromium on Windows reads `(3, 1)`, and
`fontTools.getBestCmap()` also prefers it — so the file reported 169 entries
while `getBestCmap()` returned 133 with no Devanagari at all.

The symptom is deceptive: the font loads, status is `loaded`, Latin renders in
the right typeface, and Devanagari silently falls back. It looks exactly like
"cmap remapping doesn't work". **Write to every Unicode subtable.**
`build_unicode.py` now does.

## What is not solved

1. **33 composed entries** — `आ ई ऐ ओ औ क्ष त्र अं अः …`. Their layout keys are
   two characters (`Aa`, `qQ`, `Fe`), because the legacy font draws them as two
   glyphs side by side. A `cmap` entry cannot express "two glyphs for one
   codepoint". They need composite glyphs or GSUB ligatures — authorable, but
   not yet done.
2. **The five known gaps.** Likely present in the font as unidentified glyphs.
   Identifying them needs visual ground truth: render the 26 unknown letter
   glyphs and match them against a Unicode reference.
3. **Matra ordering.** The probe measured ink and width, *not* whether a pre-base
   `ि` lands to the left of its consonant. That needs a rendered-frame
   comparison — the same standard AMS Manthan and AMS Aakash are held to.
4. **Coverage.** One font tested. The other 78 layouts have not been rebuilt.

## What would change if it works end to end

- `--legacy-font`, `--layout-file` and `scripts/layout_encoder.py` become
  optional rather than mandatory — no transcoding step at all.
- The fonts become normal fonts: they would work in PowerPoint, Word, any
  browser, not only through this repo's pipeline.
- **Verification gets the ground truth it currently lacks.** Once a font speaks
  Unicode, a glyph can be compared against a Unicode reference
  character-by-character — the check that today can only be done by eye on a
  rendered frame.

## Reproducing this

```bash
py scripts/build_unicode.py --font <legacy.ttf> --layout layouts/<slug>.json --out out/<name>.unicode.ttf
py scripts/verify_layouts.py --all          # unchanged: 79 passed, 0 failed
```

The browser probe was a canvas ink/width comparison in Chromium; it needs a
`@font-face` page loading the rebuilt font, the original, and a Unicode
reference, then measuring `measureText` widths and rasterised ink per character
for each family. Note that a `file://` page cannot be opened by the tooling
used here — serve the directory over `http://localhost` instead.

## Raw probe results

Full per-character result, rebuilt font (`U`) vs untouched original (`O`) vs a
Unicode reference (`R`, Arya). `REMAPPED` = the font's own glyph was drawn;
`FALLBACK` = identical to the untouched original, i.e. Chromium used a
different font.

| Char | U ink | O ink | R ink | Verdict |
|---|---:|---:|---:|---|
| अ | 404 | 504 | 520 | **REMAPPED** |
| आ | 720 | 720 | 700 | FALLBACK — composed (`Aa`) |
| इ | 795 | 447 | 442 | **REMAPPED** |
| ई | 472 | 472 | 477 | FALLBACK — composed (`qQ`) |
| उ | 476 | 411 | 303 | **REMAPPED** |
| ऊ | 533 | 567 | 483 | **REMAPPED** |
| ऋ | 730 | 617 | 604 | **REMAPPED** |
| ए | 416 | 440 | 471 | **REMAPPED** |
| ऐ | 463 | 463 | 505 | FALLBACK — composed (`Fe`) |
| ओ | 743 | 743 | 733 | FALLBACK — composed (`Aae`) |
| औ | 753 | 753 | 771 | FALLBACK — composed (`AaE`) |
| क | 560 | 562 | 593 | **REMAPPED** |
| छ | 555 | 571 | 512 | **REMAPPED** |
| ड | 440 | 445 | 360 | **REMAPPED** |
| ठ | 483 | 429 | 365 | **REMAPPED** |
| ढ | 479 | 448 | 389 | **REMAPPED** |
| ं | 3 | 115 | 178 | **REMAPPED** (near-zero ink — check the glyph) |
| ः | 116 | 182 | 242 | **REMAPPED** |
| र | 697 | 298 | 244 | **REMAPPED** |
| ी | 267 | 354 | 433 | **REMAPPED** |
| ि | 355 | 367 | 432 | **REMAPPED** (position not verified) |

15 `REMAPPED`, 6 `FALLBACK`, and every fallback is a composed character.

Advance widths (px, 46px):

| Family | `A` | `अ` | `क` | `छ` |
|---|---:|---:|---:|---:|
| rebuilt | 26.68 | **26.68** | **28.98** | **28.66** |
| original | 26.68 | 37.73 | 39.71 | 36.39 |
| Arya | 24.84 | 36.48 | 42.27 | 33.58 |
| absent family | 33.22 | 37.73 | 39.71 | 36.39 |

The rebuilt font's Devanagari widths equal its own Latin `A` width, not the
absent-family widths — the glyph is coming from the font.

Environment: `Mozilla/5.0 (Windows NT 10.0; Win64; x64) … Chrome/152.0.7977.130
Electron/44.4.3`. Note this is **Electron, not the Remotion renderer** — the
same Chromium engine and the same HarfBuzz, but a final check inside an actual
Remotion render is still owed.
