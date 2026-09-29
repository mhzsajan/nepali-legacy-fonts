# Remotion patch

These are the changes `lyric-video-remotion` needs so it can use a generated
layout. They are already pushed to
[mhzsajan/lyric-video-remotion](https://github.com/mhzsajan/lyric-video-remotion)
(commit `95f7fa8`), so if you are on that version you need nothing. They are
included here so this repo is usable on its own, and as a reference if you
need to apply them to a different checkout.

## What each change is for

| File | Change | Why |
|---|---|---|
| `layout_encoder.py` | `load_extra_layouts(path)` | Merges a generated layout so the transcoder can target a font outside npttf2utf's five. |
| `lrc_legacy.py` | `--layout-file` | Passes that file through from the CLI. |
| `render.mjs` | `--layout-file`, `--layout` | Chooses which layout a legacy font speaks. |
| `render.mjs` | `--gpu` | NVENC via bitrate mode. |
| `render.mjs` | `--prepare-only` | Transcode and register the font, skip the render. |
| `src/Root.jsx` | preview length cap in `calculateMetadata` | Fixes a crash that made **every** preview fail. |

## The two bugs that made the whole path unusable

Neither is about fonts, and both blocked everything before a font could even
be tried.

### 1. `npttf2utf` was never a dependency

`scripts/layout_encoder.py` reads its five layouts from
`npttf2utf`'s `map.json`. With the package absent, every `--legacy-font`
render died at once:

```
FileNotFoundError: 'C:\...\scripts\map.json'
```

Nothing about that message says "install a Python package", which is a large
part of why this looked unfixable. Now:

```bash
pip install fonttools npttf2utf pillow
```

### 2. Every preview render crashed

`render.mjs` passed `--frames=0-<lastCue + 2s>`, computed from a different
number than the composition's own duration, which `calculateMetadata` derives
from `max(audio length, last cue)`. Whenever a song's audio is shorter than
its own last cue plus two seconds, the range ran past the end and Remotion
refused:

```
Error: The "durationInFrames" of the <Composition /> was evaluated to be
6257, but frame range 0-6259 is not within the frame range of the
composition (0-6256).
```

Allare is exactly that case — 417.0 s of audio against a 415.3 s last cue. The
cap now lives in `calculateMetadata`, so one place owns the length and the two
cannot drift apart again.

## Applying to another checkout

Copy the four files over the originals. They are self-contained: no new
package, no new npm dependency.

```bash
cp remotion-patch/render.mjs            <repo>/render.mjs
cp remotion-patch/scripts/layout_encoder.py <repo>/scripts/layout_encoder.py
cp remotion-patch/scripts/lrc_legacy.py  <repo>/scripts/lrc_legacy.py
cp remotion-patch/src/Root.jsx           <repo>/src/Root.jsx
```

## Using a generated layout

```bash
# 1. check the cues -- instant, no render
node render.mjs song.mp3 song.lrc --report-only

# 2. transcode and register the font, skip the render
node render.mjs song.mp3 song.lrc --legacy-font fonts/ams.manthan/ams.manthan.ttf \
    --layout-file layouts/ams-manthan.json --prepare-only

# 3. look at ONE frame before committing to a full render
npx remotion still src/index.js LyricOverlay out/check.png --frame=5900 --props=out/props.json

# 4. the real thing
node render.mjs song.mp3 song.lrc --no-audio \
    --legacy-font fonts/ams.manthan/ams.manthan.ttf \
    --layout-file layouts/ams-manthan.json \
    --mode roam --word-anim karaoke --letter-anim pop --letter-var 0.03
```

Step 3 costs seconds and is the step that catches a wrong font. A wrong map
does not error — it renders the wrong letters, which is exactly the failure
that is easy to miss in a four-minute video.
