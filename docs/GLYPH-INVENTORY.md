# What is actually inside these font files

Findings from 2026-09-29, in response to the question: *can we fix the legacy
fonts by changing the renderer, changing the engine, or rebuilding the fonts?*

**Short answer: not the renderer, not the engine, and rebuilding does not mean
drawing. The shapes are already in the files. They are simply unlabelled.**

Evidence in [`evidence/`](evidence/), produced by
`scripts/specimen_glyphs.py` and `scripts/specimen_widest.py`.

---

## 1. Measured facts

| | AMS Manthan | Abhinav |
|---|---:|---:|
| Glyphs in file | 134 | 161 |
| Devanagari codepoints (U+0900–U+097F) | **0** | **0** |
| `GSUB` (shaping) | **absent** | **absent** |
| `GPOS` (positioning) | **absent** | **absent** |
| ASCII codepoints mapped | 93 | 95 |

Both are pure ASCII-mapped display faces. There is not one Devanagari codepoint
in either, and no shaping or positioning tables at all.

## 2. But the conjuncts are in there

Rendering every glyph individually
([`ams-manthan-all-glyphs.png`](evidence/ams-manthan-all-glyphs.png),
[`abhinav-all-glyphs.png`](evidence/abhinav-all-glyphs.png)) shows the files
contain far more than isolated letters:

- **Abhinav's widest glyphs**
  ([`abhinav-widest-glyphs.png`](evidence/abhinav-widest-glyphs.png)) are
  unambiguously fused clusters: `र्या`, `था`, `ख्याल`, `स्याल`, `रवा`, `शा`,
  `ध्य`, `ह्म`, `ज्ञ`, `श्र`, `ह्र`, `स्र`, `क्र`, `ष्ट`.
- **AMS Manthan** is the same story in a heavier calligraphic hand: 131 real
  glyphs behind 69 published keys, so roughly half the file is not addressed by
  the layout at all.

So a conjunct is not composed at render time. It is a **single pre-drawn
outline** that the font addresses through an ASCII key — which is exactly how a
Preeti-era font is supposed to work, and exactly why these fonts need a layout
at all.

## 3. Why no renderer or engine can help

Text shaping is not a renderer responsibility. The pipeline is:

```
string ──▶ shaping engine (HarfBuzz / CoreText / DirectWrite) ──▶ glyph ids ──▶ rasteriser
```

Remotion contributes only the last box: it drives headless Chromium, draws React
components to frames, and encodes H.264. **It contains no font code at all** —
there is nothing in it to modify for this. Patching it would mean patching
Chromium's font fallback, which is not a video framework's job.

And a different engine changes nothing, because **every** mainstream text engine
needs the same two things these fonts lack:

| Engine | Needs a Devanagari cmap | Needs GSUB/GPOS |
|---|---|---|
| HarfBuzz (Chromium, Firefox, most Linux) | yes | yes |
| DirectWrite (Windows) | yes | yes |
| CoreText (macOS) | yes | yes |
| Pango / Cairo | yes | yes |
| Skia text | yes | yes |

A font with zero Devanagari codepoints and no shaping tables cannot be made to
produce a conjunct by any of them, because there is no `प्र` in the file to
address and no rule saying `प` + `्` + `र` becomes one glyph. The workaround is
not a better shaper. It is a **correct key map**, which is what this repo
generates.

## 4. So the real options

### Option A — keep transcode, close the gap by labelling (recommended)

The pipeline already works. `--font-slug ams-manthan` renders 20 of Allare's 35
lines correctly. The failure is confined to two characters that aNepali's
published table does not name:

- `U+094D` virama, `U+0901` candrabindu

The fix is to **map the glyphs that already exist but are unlabelled**. The
publisher's page names 69 slots; AMS Manthan has 131 real glyphs. A tool that
renders the unlabelled remainder and has a human name each one — a one-off
~20 minutes per font — yields a layout that reaches the conjuncts, and the
virama stops splitting words.

This is a **discovery** problem, not a drawing problem, and it is bounded. It
would take the coverage from "69 of 131 glyphs addressed" to "all of them".

Cheap semi-automation: propose labels by rendering each candidate glyph and
matching it against a reference Devanagari font's shapes (compare normalised
outlines, or just show the human a grid and accept corrections). The
specimen scripts here are the first half of that.

### Option B — build a real Unicode font from the legacy outlines

Take the legacy file, and emit a new one with:

1. a `cmap` mapping Devanagari codepoints onto the **existing** glyphs, and
2. `GSUB` rules for matra reordering (a pre-base `ि` must be placed left of its
   consonant) and for any conjunct the font does not carry as a single outline.

This is a bigger job than it sounds, and step 2 is where it gets honest:
**a conjunct with no pre-drawn outline cannot be synthesised by substitution.**
`fontTools` can point one glyph id at another; it cannot draw. Options B and A
share the same ceiling — every conjunct that is not already an outline stays
missing. B's advantage is that the result is a normal Unicode font that any tool
can use, including a browser, with no layout at all.

### Option C — use a Unicode font (what we do now)

58 Tier A faces need no layout and cannot lose a character. Yantramanav Black
gives the calligraphic weight that made the legacy fonts attractive, with none
of this machinery. **This is what the delivered Allare video uses.**

## 5. Recommendation

Do A as a bounded experiment on one font, because it is the only option that
adds coverage without a large build. Do C as the default. Skip B unless there is
a specific legacy typeface that a client requires by name, because B is a font
engineering project with a hard ceiling on the conjuncts it can ever reach.

**No change to Remotion is warranted under any option.** The bug was never in
the renderer.

## Reproducing

```bash
py scripts/specimen_glyphs.py  AMS-Mantthan  <path>/ams.manthan.ttf  out/glyphs.png
py scripts/specimen_widest.py  Abhinav       <path>/Abhinav.TTF      out/widest.png
```

Both take a label, a font path, and an output path. The widest script sorts by
ink advance, because a fused cluster is markedly wider than a single letter.
