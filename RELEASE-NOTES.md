Fonts for Remotion — 214 legacy Nepali fonts with generated, verified layouts.

## What is in these archives

| Archive | Size | Fonts | How to use |
|---|---:|---:|---|
| `nepali-fonts-unicode.zip` | 94 MB | 58 | Install the font, then `--font "<family>"`. No transcoding, no layout file. |
| `nepali-fonts-preeti.zip` | 5 MB | 77 | `--legacy-font <file>` with `--layout Preeti`. |
| `nepali-fonts-generated.zip` | 14 MB | 71 | `--legacy-font <file>` with `--layout-file layouts/<slug>.json`. **Layouts are inside.** |
| `nepali-fonts-notable.zip` | 0.4 MB | 8 | Legacy, but no character table is published; these need a hand-written map. |
| `nepali-fonts-layouts-only.zip` | 40 KB | — | The 71 layout files alone, no fonts. |

**If a font is for a show, start with the Unicode archive.** Those 58 render in
Chromium with no transcoding at all, and they are mostly SIL OFL — a licence you
can name. The legacy archives are for when you need a specific decorative look.

The generated archive ships with its layouts inside on purpose. A generated font
is useless without its map, and shipping them apart is how someone ends up
rendering Preeti keys into a non-Preeti font and getting collapsed glyphs.

## Verification

Every generated layout was checked against the font binary it describes:

```
71 passed, 0 failed
```

That proves each key resolves to a real glyph. It does **not** prove the glyph
is the right one — render a single frame and look at it:

```bash
node render.mjs song.mp3 song.lrc --legacy-font ams.manthan.ttf \
    --layout-file layouts/ams-manthan.json --prepare-only
npx remotion still src/index.js LyricOverlay out/check.png --frame=5900 --props=out/props.json
```

## Not covered

`ङ`, `ञ` and `ज्ञ` are absent from every generated layout. They have no Preeti
key to calibrate from, and the publisher's table lists those three consonant
slots as Devanagari rather than as a key. They render as a **blank box**.
`ज्ञ` occurs in real lyrics, so check any word containing it.

## Licensing

These fonts are their authors' property and keep their own terms. aNepali, the
source:

> The fonts presented on this website are their authors' property, and are
> either freeware, shareware, demo versions or public domain. Please look at
> the readme-files in the archives or check the indicated author's website for
> details, and contact him/her if in doubt.

That is a statement of varying status, not a licence. Several fonts here are
demo or shareware, and at least two belong to a commercial foundry. Every
archive includes the original readmes — they are the terms, and they travel with
the fonts because of it.

**Read the readme before a font goes on screen in front of an audience.**

## Repository

Full tooling, method and documentation:
https://github.com/mhzsajan/nepali-legacy-fonts
