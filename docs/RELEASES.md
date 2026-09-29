# Fonts, arranged so you only download what you need

Five archives, split by what a font needs to work.

| Archive | Size | Fonts | How to use it |
|---|---:|---:|---|
| `nepali-fonts-unicode.zip` | 94 MB | 58 | Install the font, then `--font "<family>"`. No transcoding, no layout file. |
| `nepali-fonts-preeti.zip` | 5 MB | 77 | `--legacy-font <file>` with `--layout Preeti`. |
| `nepali-fonts-generated.zip` | 14 MB | 79 | `--legacy-font <file>` with `--layout-file layouts/<slug>.json`. Layouts are inside. |
| `nepali-fonts-layouts-only.zip` | 40 KB | — | The 79 layout files alone, with no fonts. |

**If a font is for a show, start with the Unicode archive.** Those 58 render in
Chromium with no transcoding at all, and they are mostly SIL OFL — a licence
you can name, which covers commercial and broadcast use. The legacy archives
are for when you need a specific decorative look.

The generated archive ships with its layouts inside on purpose: a generated
font is useless without its map, and shipping them apart is how someone ends up
rendering Preeti keys into a non-Preeti font and getting collapsed glyphs.

## Checking a font before you commit to a render

```bash
py scripts/verify_layouts.py <slug>
```

Downloads the font and checks every key in its layout against that font's real
glyph table. Current state:

```
79 passed, 0 failed
```

## Reading a frame

Passing verification is necessary, not sufficient — it proves each key reaches
a real glyph, not that the glyph is the right one. Render a single frame and
look at it:

```bash
node render.mjs song.mp3 song.lrc --legacy-font ams.manthan.ttf \
    --layout-file layouts/ams-manthan.json --prepare-only
npx remotion still src/index.js LyricOverlay out/check.png --frame=5900 --props=out/props.json
```

Seconds, not minutes. This is the only step that catches a wrong-glyph mapping.

## Three characters are not covered

`ङ`, `ञ` and `ज्ञ` are absent from every generated layout, because the site
publishes those three consonant slots as Devanagari rather than as a key and
there is nothing to calibrate from. They render as a **blank box**.

`ज्ञ` occurs in real lyrics, so check any word containing it before shipping.

## Licensing

Each font is its author's property. aNepali says so on its own index:

> The fonts presented on this website are their authors' property, and are
> either freeware, shareware, demo versions or public domain. Please look at
> the readme-files in the archives or check the indicated author's website for
> details, and contact him/her if in doubt.

That is a statement of varying status, not a licence. Several fonts here are
demo or shareware, and at least two are the property of a commercial foundry.
Every archive includes the original readmes — they travel with the fonts
because they are the terms.

**Read the readme before a font goes on screen in front of an audience.**
