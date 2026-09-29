# Fonts for Remotion, and how to use them

Generated layouts for 214 legacy Nepali fonts, so they render in Remotion and
Chromium instead of silently falling back to a substitute typeface.

**Start here:** `docs/GETTING-STARTED.md`

```bash
git clone https://github.com/mhzsajan/nepali-legacy-fonts
cd nepali-legacy-fonts
pip install -r requirements.txt
py scripts/verify_layouts.py ams-manthan     # proves the install works
```

---

## The problem

Nepali design fonts are mostly **legacy**: built for Preeti-era workflows,
where you typed ASCII and the font's ASCII glyphs *were drawn as* Devanagari.
Such a font has **zero Devanagari codepoints** in its `cmap` and **no
GSUB/GPOS**. Chromium — and therefore Remotion — silently substitutes another
font character by character. No error, no warning.

```bash
node render.mjs song.mp3 song.lrc --font "AMS Manthan"   # renders nothing useful
```

The workaround is to transcode the lyrics into the font's own key layout — but
that needs the layout, and there was nowhere to find it:

- **the font cannot say** — nothing inside it records what `;` was meant to be;
- **outlines are unreliable** — and a visual transcription of a key map had
  already produced wrong letters here (द/ध, श/ष confusion);
- **`npttf2utf` knows five** Nepali layouts, and most popular fonts speak
  none of them.

Feeding Preeti keys to `ams.manthan.ttf` gives exactly what the workaround
should prevent: glyphs collapsed onto each other, and a literal `==` where the
danda should be.

## The fix

**aNepali publishes a character table for every font.** Each cell is a **key**,
drawn in that font, under a Devanagari category heading — so a font's layout
can be *read* rather than guessed.

```
Unicode lyrics ──► this repo ──► the font's own keys ──► the font ──► correct Devanagari
```

The page gives keys but not the Devanagari each slot means, so the order is
calibrated off the **Preeti** page where `npttf2utf` is ground truth. That
calibration is then **asserted, not trusted**:

```
(Vowels)     13 keys -> 13 distinct Devanagari
(Consonants) 36 keys -> 36 distinct Devanagari
(Numbers)    10 keys -> 10 distinct Devanagari
(Matras)     13 keys -> 13 bare matras
```

If the site ever changes, the tool **refuses to guess**. An off-by-one in the
slot order shifts every later character and yields text that looks fine and
is wrong — the one failure mode that matters here.

---

## Coverage — 214 fonts

| Class | Count | What it means |
|---|---:|---|
| `UNICODE` | 58 | Renders as-is. No transcoding. **Mostly SIL OFL.** |
| `PREETI` | 77 | npttf2utf already has it — `--layout Preeti`. |
| `GENERATED` | 71 | Layout read from the page. **All 71 verified.** |
| `NOTABLE` | 8 | Legacy, but no character table is published. |

```bash
py scripts/verify_layouts.py --all
# 71 passed, 0 failed, 0 not available
```

This downloads each font and checks every key against **that font's real glyph
table** — the check a render cannot do, since a key can exist and still point
at the *wrong* glyph. Two fonts are additionally confirmed on rendered frames
through Remotion: **AMS Manthan** and **AMS Aakash**.

## Downloads

Releases carry one archive per class, so you take only what you need:

| Archive | Size | Use with |
|---|---:|---|
| `nepali-fonts-unicode.zip` | 94 MB | `--font "<family>"` — nothing else needed |
| `nepali-fonts-preeti.zip` | 5 MB | `--legacy-font` + `--layout Preeti` |
| `nepali-fonts-generated.zip` | 14 MB | `--legacy-font` + `--layout-file layouts/<slug>.json` |
| `nepali-fonts-notable.zip` | 0.4 MB | needs a hand-written layout |
| `nepali-fonts-layouts-only.zip` | 40 KB | the 71 maps, no fonts |

The generated archive ships **with its layouts inside** — a generated font is
useless without its map, and shipping them apart is how someone ends up
rendering Preeti keys into a non-Preeti font.

## Using one

```bash
py scripts/which_fonts.py "C:\path\to\fonts"   # what do I type for this font?
```

```bash
# 1. check the cues -- instant
node render.mjs song.mp3 song.lrc --report-only

# 2. transcode and register the font, skip the render
node render.mjs song.mp3 song.lrc --legacy-font ams.manthan.ttf \
    --layout-file layouts/ams-manthan.json --prepare-only

# 3. look at ONE frame  <-- not optional
npx remotion still src/index.js LyricOverlay out/check.png --frame=5900 --props=out/props.json

# 4. the real render
node render.mjs song.mp3 song.lrc --no-audio \
    --legacy-font ams.manthan.ttf --layout-file layouts/ams-manthan.json \
    --mode roam --word-anim karaoke --letter-anim pop --letter-var 0.03
```

**Step 3 is not optional.** A wrong layout does not error — it renders the
wrong letters. Seconds here, minutes to spot later.

---

## Two bugs that blocked everything

Neither is about fonts, and both stopped any font from being tried at all.

**`npttf2utf` was never a declared dependency.** `layout_encoder.py` reads its
layouts from that package's `map.json`, so with it absent every legacy render
died at once:

```
FileNotFoundError: 'C:\...\scripts\map.json'
```

Nothing in that message says "install a Python package", which is much of why
this looked unfixable.

**Every preview render crashed.** `--frames` used `lastCue + 2s` while the
composition derives its duration from `max(audio, lastCue)`; on any song whose
audio is shorter than its own last cue plus two seconds the range ran past the
end. Allare is that case — 417.0 s of audio against a 415.3 s cue. One place
now owns the length.

Both are fixed in
[`lyric-video-remotion`](https://github.com/mhzsajan/lyric-video-remotion) and
mirrored in `remotion-patch/`. See `docs/REMOTION-PATCH.md`.

## Two things to know before trusting a layout

**Verification is necessary, not sufficient.** All 71 pass, meaning every key
reaches a real glyph. It cannot prove the glyph is the *right* one. Only a
rendered frame does.

**`ङ`, `ञ` and `ज्ञ` are not covered.** They have no Preeti key to calibrate
from, and the site publishes those three slots as Devanagari rather than as a
key. They render as a **blank box**. `ज्ञ` occurs in real lyrics — check any
word containing it.

## Deliberately not done

**Symbols are not mapped.** The published symbols section is not calibratable:
the same 29 slots hold *different characters* on different pages. It is also
unnecessary — a legacy font already keeps its Devanagari punctuation on the
ASCII codepoints, so punctuation passes through untouched. Mapping it twice
is what produced the literal `==`.

**Fonts are not converted.** Rebuilding one as Unicode means authoring a
`cmap` *and* GSUB ligature tables with no ground truth to check against.

---

# Read this before choosing a font

**A Unicode font is almost always the right answer.** If you do not need a
specific classic typeface, use `--font "Nirmala UI"` and stop. No
transcoding, no layout file, no Python, and no possibility of a character
rendering in the wrong typeface.

Everything above this line exists only for when you need a *specific* look
that no Unicode font provides. That path is real and the tooling is solid,
but it has costs which are measured in **`docs/LEGACY-PITFALLS.md`** rather
than guessed at.

## What the legacy path can and cannot do

Measured on real Nepali lyrics, two songs, 110 distinct words:
**34 words needed a character the AMS Manthan layout does not expose.**

| Character | Words | Consequence |
|---|---:|---|
| `्` virama | 21 | conjuncts unrenderable |
| `ँ` candrabindu | 12 | आँ, सँ, कहिँ broken |
| `ञ` | 1 | चञ्चल broken |

aNepali publishes those three slots as Devanagari rather than as a key, so
there is nothing to read and no way to derive them. They reach the font
unmapped, and Chromium substitutes a *different* font for exactly those
characters — which is what produces a word drawn in two typefaces, and what
makes a stray mark read as a `0` or an `O` instead of as obviously wrong.

`ङ`, `ञ` and `ज्ञ` were already documented gaps. The **virama and
candrabindu** gaps were found later, by rendering actual songs — they are in
the word "हिस्सी" and "आँखा", which no word list would have flagged.

## The Unicode fonts

58 of the 214 need no transcoding and no layout, so every character is
native. **Nirmala UI ships with Windows 11**, so it works on any machine with
nothing to install — which also means it will behave identically on a home PC
and on a show laptop.

The rest are in `fonts/` under the `UNICODE` class, mostly SIL OFL: Mukta,
Noto Sans/Serif Devanagari, Yantramanav, Kalam, Hind, Martel, Rozha One,
Teko, Laila, Alkatra, Akshar, Anek Devanagari.

```bash
node render.mjs song.mp3 song.lrc --font "Nirmala UI"
```

## Licensing

The fonts are their authors' property and keep their own terms. aNepali:

> The fonts presented on this website are their authors' property, and are
> either freeware, shareware, demo versions or public domain. Please look at
> the readme-files in the archives or check the indicated author's website for
> details, and contact him/her if in doubt.

That is varying status, not a licence. Several fonts here are demo or
shareware; at least two belong to a commercial foundry. A readme ships in every
archive — it is the terms.

**For a broadcast, start with the 58 Unicode fonts**: no transcoding, and
mostly SIL OFL. `docs/FONTS-DIR.md` has the detail.

The **layouts** are the derived work here and carry no separate licence
question.

## Documentation

| File | What it is for |
|---|---|
| `docs/GETTING-STARTED.md` | Install and first use |
| `AGENTS.md` | For an AI agent, and the Windows traps |
| `docs/METHOD.md` | How layouts are derived, and what that does **not** prove |
| `docs/REMOTION-PATCH.md` | The renderer changes |
| `docs/RELEASES.md` | Which archive answers which need |
| `docs/FONTS-DIR.md` | The fonts, and the licensing question |
