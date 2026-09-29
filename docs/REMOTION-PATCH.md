# Using a layout with the renderer

**This repo makes fonts. It does not render videos.** If you are here to
produce a video, you want
[mhzsajan/lyric-video-remotion](https://github.com/mhzsajan/lyric-video-remotion).

## What was here, and why it is gone

Until 2026-09-29 this repo carried a `remotion-patch/` directory: four copied
files (`render.mjs`, `scripts/layout_encoder.py`, `scripts/lrc_legacy.py`,
`src/Root.jsx`) so that the layout generation in this repo was usable on its
own.

It was removed, for two reasons that only became clear together:

1. **It was already stale.** The snapshot was taken at `95f7fa8`; the renderer
   has moved on, so all four features were already upstream and the copy was
   147 lines behind `render.mjs` alone. Copying it over a current checkout is a
   *revert*.
2. **A copy of a renderer inside a font repo cannot be maintained.** It drifted
   silently and nothing failed — the files are not imported, they are dead
   weight that looks authoritative.

The split is now: this repo answers *what can this font write*, the renderer
answers *how do I draw it*. Neither keeps a copy of the other.

## Getting a layout into a render

The renderer reads a layout straight from this repo's `layouts/`. There is no
vendored copy anywhere, which is deliberate — a vendored layout goes stale the
moment this repo regenerates it, and nothing warns you.

```bash
# point the renderer at a layout from this repo
node render.mjs song.mp3 song.lrc --no-audio \
    --font-slug ams-manthan          # resolves font + layout together
```

Or give the two paths directly:

```bash
node render.mjs song.mp3 song.lrc --no-audio \
    --legacy-font fonts/ams.manthan/ams.manthan.ttf \
    --layout-file layouts/ams-manthan.json
```

The renderer's [docs/FONTS.md](https://github.com/mhzsajan/lyric-video-remotion/blob/main/docs/FONTS.md)
covers the render-side workflow, including the two bugs that made the legacy
path unusable at all (`npttf2utf` never being a dependency, and every preview
crashing on a frame range past the composition's own duration). Both are fixed
upstream and both write-ups moved with the code they describe.

## Before you render

Check the font against the *song*, not just against itself. Every layout in
this repo passes verification, and a verified layout still cannot write a song
containing a virama or a candrabindu:

```bash
py scripts/check_song.py --font ams-manthan song.lrc
```

See [SONG-CHECK.md](SONG-CHECK.md) for why that check is separate from
`verify_layouts.py`, and what it catches that nothing else does.
