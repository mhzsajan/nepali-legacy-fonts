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
| `GENERATED` | 79 | Layout read from the page. **All 79 verified.** |
| `NOTABLE` | 0 | Was 8. The class is now empty — see below. |

```bash
py scripts/verify_layouts.py --all
# 79 passed, 0 failed, 0 not available
```

This downloads each font and checks every key against **that font's real glyph
table** — the check a render cannot do, since a key can exist and still point
at the *wrong* glyph. Two fonts are additionally confirmed on rendered frames
through Remotion: **AMS Manthan** and **AMS Aakash**.

### How `NOTABLE` emptied out

Eight fonts — `AMS Calligraphy 1`–`9` — were listed as *legacy, but the page
publishes no character table*. That was wrong: the tables were there all
along. The parser built its CSS selector from the catalogue **slug** (`ams-1`
→ `font-ams-1`), but aNepali paints those cells with a class derived from the
**family name** (`font-ams-calligraphy-1`), so the lookup found zero cells and
read a fully documented font as undocumented.

`anepali_charmap.table_class()` now resolves the class from the page itself —
the token present on cells under *every* calibratable heading — instead of
assuming it. The eight recovered with no other change: each reads the same
13/36/10/13 slots as every other legacy font and verifies against its own
`.ttf`. **214 of 214 fonts are now usable**; nothing needs a hand-written map.

## Downloads

Releases carry one archive per class, so you take only what you need:

| Archive | Size | Use with |
|---|---:|---|
| `nepali-fonts-unicode.zip` | 94 MB | `--font "<family>"` — nothing else needed |
| `nepali-fonts-preeti.zip` | 5 MB | `--legacy-font` + `--layout Preeti` |
| `nepali-fonts-generated.zip` | 14 MB | `--legacy-font` + `--layout-file layouts/<slug>.json` |
| `nepali-fonts-layouts-only.zip` | 40 KB | the 79 maps, no fonts |

The generated archive ships **with its layouts inside** — a generated font is
useless without its map, and shipping them apart is how someone ends up
rendering Preeti keys into a non-Preeti font.

> **Release note:** the `nepali-fonts-notable.zip` archive is retired. Its 8
> fonts moved to `GENERATED` with real layouts, so re-cut the archives with
> `py scripts/make_releases.py` before publishing — the counts above are what
> the repo now produces, not necessarily what a stale v1.0.0 contains.

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

**Verification is necessary, not sufficient.** All 79 pass, meaning every key
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

**Fonts are not converted — yet.** Rebuilding one as Unicode means authoring a
`cmap` *and* GSUB ligature tables with no ground truth to check against. The
`cmap` half has since been shown to work: inverted straight from an existing
layout, Chromium draws the font's own glyphs for Devanagari with **no GSUB at
all**. The ligature half and the ground-truth problem are unsolved, so nothing
is shipped — but the premise that it cannot be done is no longer true.
See `docs/UNICODE-REBUILD.md` and `scripts/build_unicode.py`.

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

## Preferred fonts

A curated shortlist of 42 fonts, grouped by how much work each one is. **Every
entry is usable as-is** — 29 have a generated layout in this repo, 10 speak
Preeti, 3 are already Unicode.

> **Pick from here, in this order. The tables below are grouped by *effort*,
> not by *safety* — the first font listed is not the best answer.**
>
> 1. **`Arya`, `Kalam`, `Rajdhani`** — Unicode. Nothing to transcode, no
>    layout that can be wrong. This is the answer to *"which font should I
>    use?"* and to *"which font works without issue"* — see **Tier A**.
> 2. **`AMS Aakash`** — when you specifically want a classic legacy look.
>    It is the only font on this list **confirmed on a rendered frame**;
>    verification alone cannot tell `द` from `ध`, so every other entry here
>    is verified but not proven.
> 3. Everything else on the list — verified against its `.ttf`, but it
>    inherits the five unfixable characters below.

```bash
py scripts/which_fonts.py "C:\path\to\fonts"   # resolves a file to its slug
```

**GENERATED (29)** — the layout is in this repo, one file per font:

| Font | Use it with |
|---|---|
| AMS 1 | `--legacy-font <file> --layout-file layouts/ams-1.json` |
| AMS 2 | `--legacy-font <file> --layout-file layouts/ams-2.json` |
| AMS 4 | `--legacy-font <file> --layout-file layouts/ams-4.json` |
| AMS 5 | `--legacy-font <file> --layout-file layouts/ams-5.json` |
| AMS 7 | `--legacy-font <file> --layout-file layouts/ams-7.json` |
| AMS Aaditya | `--legacy-font <file> --layout-file layouts/ams-aaditya.json` |
| AMS Aakash | `--legacy-font <file> --layout-file layouts/ams-aakash.json` |
| AMS Aakul 4 | `--legacy-font <file> --layout-file layouts/ams-aakul-4.json` |
| AMS Aakul 5 | `--legacy-font <file> --layout-file layouts/ams-aakul-5.json` |
| AMS Aasmi | `--legacy-font <file> --layout-file layouts/ams-aasmi.json` |
| AMS Barakhadi 1 | `--legacy-font <file> --layout-file layouts/ams-barakhadi-1.json` |
| AMS Chandrakant | `--legacy-font <file> --layout-file layouts/ams-chandrakant.json` |
| AMS Chhatrapati | `--legacy-font <file> --layout-file layouts/ams-chhatrapati.json` |
| AMS Darshana | `--legacy-font <file> --layout-file layouts/ams-darshana.json` |
| AMS Diya | `--legacy-font <file> --layout-file layouts/ams-diya.json` |
| AMS Ganesha | `--legacy-font <file> --layout-file layouts/ams-ganesha.json` |
| AMS Gourav Bold | `--legacy-font <file> --layout-file layouts/ams-gourav-bold.json` |
| AMS Harshdeep | `--legacy-font <file> --layout-file layouts/ams-harshdeep.json` |
| AMS Hastkala | `--legacy-font <file> --layout-file layouts/ams-hastkala.json` |
| AMS Hastkala 1 | `--legacy-font <file> --layout-file layouts/ams-hastkala-1.json` |
| AMS Jiwan | `--legacy-font <file> --layout-file layouts/ams-jiwan.json` |
| AMS Kartik | `--legacy-font <file> --layout-file layouts/ams-kartik.json` |
| AMS Karuna | `--legacy-font <file> --layout-file layouts/ams-karuna.json` |
| AMS Kasturi 1 | `--legacy-font <file> --layout-file layouts/ams-kasturi-1.json` |
| AMS Lekhan 1 | `--legacy-font <file> --layout-file layouts/ams-lekhan-1.json` |
| AMS Lekhan 1 Bold | `--legacy-font <file> --layout-file layouts/ams-lekhan-1-bold.json` |
| AMS Lekhan 4 | `--legacy-font <file> --layout-file layouts/ams-lekhan-4.json` |
| AMS Lekhan 5 | `--legacy-font <file> --layout-file layouts/ams-lekhan-5.json` |
| AMS Manoja | `--legacy-font <file> --layout-file layouts/ams-manoja.json` |

**PREETI (10)** — one flag, no layout file; the map lives in `npttf2utf`:

| Font | Use it with |
|---|---|
| 0012 ARAP | `--legacy-font <file> --layout Preeti` |
| 0017 ARAP | `--legacy-font <file> --layout Preeti` |
| Ananda Fanko 2 | `--legacy-font <file> --layout Preeti` |
| ARAP 010 | `--legacy-font <file> --layout Preeti` |
| ARAP007 | `--legacy-font <file> --layout Preeti` |
| CV Haha | `--legacy-font <file> --layout Preeti` |
| Deepankar | `--legacy-font <file> --layout Preeti` |
| Ganga 1 | `--legacy-font <file> --layout Preeti` |
| MKali | `--legacy-font <file> --layout Preeti` |
| PawanG | `--legacy-font <file> --layout Preeti` |

**UNICODE (3)** — no transcoding, no layout file, no legacy pitfalls:

| Font | Use it with |
|---|---|
| Arya | `--font "Arya"` |
| Kalam | `--font "Kalam"` |
| Rajdhani | `--font "Rajdhani"` |

### Status — what is fixed, what is not

Read this before picking a font. "Usable" and "proven" are not the same thing
here, and the difference is silent wrong letters, not an error.

| Item | Status | Evidence |
|---|---|---|
| All **42 preferred fonts usable** | ✅ **FIXED** | `verify_layouts.py --all` → **79 passed, 0 failed** |
| AMS 1, 2, 4, 5, 7 — were `NOTABLE`, blocked | ✅ **FIXED** | 69 keys each, **0 missing** against the real `.ttf` |
| AMS 6, 8, 9 — the other 3 `NOTABLE` (not on your list) | ✅ **FIXED** | same check, same result |
| `NOTABLE` class | ✅ **EMPTY** | 214 of 214 fonts have a usable path |
| Every key resolves to a real glyph in that font's `.ttf` | ✅ **VERIFIED** | all 79, checked against the binary |
| Every key resolves to the *correct* glyph | ⚠️ **PARTIAL** | only **AMS Manthan** and **AMS Aakash** confirmed on a rendered frame |
| `ङ`, `ञ`, `ज्ञ` | ❌ **NOT FIXED — cannot be** | aNepali publishes those three slots as Devanagari, not as a key |
| virama `्`, candrabindu `ँ` | ❌ **NOT FIXED** | same cause; found by rendering songs, not by any word list |
| Symbols / punctuation mapping | ⛔ **DELIBERATELY NOT DONE** | not calibratable across pages; legacy fonts already keep punctuation on ASCII |
| Fonts rebuilt as Unicode | 🟡 **INVESTIGATED — PoC works** | A `cmap` inverted from the layout is enough on its own: in Chromium, 15 of 21 probed characters drew the font's own glyph. Not shipped — 33 composed entries and the five gaps remain. See [`docs/UNICODE-REBUILD.md`](docs/UNICODE-REBUILD.md) |

**What an agent must not claim:** that a layout is *proven correct*. The
verifier proves the encoder is self-consistent and every key reaches a real
glyph. It cannot tell `द` from `ध`. The only check that can is one rendered
frame, and **only two fonts have had one**.

**The five ❌/⛔ rows apply to all 39 legacy entries on this list**, not to
the 3 Unicode ones. A word containing one of those characters comes out
drawn in a fallback typeface mid-word, with no error — check
[`docs/LEGACY-PITFALLS.md`](docs/LEGACY-PITFALLS.md) for the measured
counts (34 of 110 real words needed a character no AMS layout exposes).

**Zero-risk choice:** `Arya`, `Kalam`, `Rajdhani`. Unicode, so nothing to
transcode and no layout that can be wrong.

### Which fonts work without issue

"Usable" is not one thing here. Three tiers, and only the first one is
incapable of producing a wrong character:

| Tier | Fonts | What can still go wrong |
|---|---|---|
| **A — no issue possible** | **58 `UNICODE`** | Nothing. Native Devanagari codepoints, no transcoding, no layout file to be wrong. |
| **B — verified, 5 known gaps** | **79 `GENERATED`** | `ङ`, `ञ`, `ज्ञ`, `्`, `ँ` are in no layout — they render in a **fallback typeface mid-word**, silently. |
| **C — verified, 5 known gaps, map external** | **77 `PREETI`** | Same five, plus the map lives in the `npttf2utf` package, not in this repo. |

**If you are asked for a font that works without issue, answer from Tier A
only.** Tier B and C are verified — every key reaches a real glyph in that
font's `.ttf` — but verification cannot cover the five characters aNepali
never publishes as a key, and there is no way to add them from this source.

The 58 Tier A fonts (one per name, comma separated):

> Akshar, Alkatra, Amiko, Amita, Anek Devanagari, Annapurna SIL, Arya, Asar, Bakbak One,
> Baloo 2, Biryani, Cambay, Dekko, Eczar, Gajraj One, Glegoo, Gotu, Halant, Hind,
> IBM Plex Sans Devnagari, Inknut Antiqua, Jaini, Jaini Purva, Jaldi, Kadwa, Kalam, Karma,
> Khand, Khula, Kurale, Laila, Martel, Martel Sans, Matangi, Modak, Mukta,
> Noto Sans Devanagari, Noto Serif Devanagari, Palanquin, Palanquin Dark, Pragati Narrow,
> Rajdhani, Ranga, Rhodium Libre, Rozha One, Sahitya, Sarala, Sarpanch, Sumana, Sura, Teko,
> Tillana, Tiro Devanagari Hindi, Tiro Devanagari Marathi, Tiro Devanagari Sanskrit,
> Vesper Libre, Yantramanav, Yatra One

Of the 42 preferred fonts: **Arya, Kalam, Rajdhani** are Tier A. The other 39
are Tier B or C and carry the five gaps above.

### Slugs, for tooling

The table above is the human view; these are the slugs `--layout-file` and
`which_fonts.py` expect:

```
GENERATED (29)  ams-1 ams-2 ams-4 ams-5 ams-7 ams-aaditya ams-aakash
                ams-aakul-4 ams-aakul-5 ams-aasmi ams-barakhadi-1
                ams-chandrakant ams-chhatrapati ams-darshana ams-diya
                ams-ganesha ams-gourav-bold ams-harshdeep ams-hastkala
                ams-hastkala-1 ams-jiwan ams-kartik ams-karuna
                ams-kasturi-1 ams-lekhan-1 ams-lekhan-1-bold ams-lekhan-4
                ams-lekhan-5 ams-manoja

PREETI   (10)   0012-arap 0017-arap ananda-fanko-2 arap-010 arap007
                cv-haha deepankar ganga-1 mkali pawang

UNICODE  (3)    arya kalam rajdhani        → --font "Arya" / "Kalam" / "Rajdhani"
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
| `docs/UNICODE-REBUILD.md` | Rebuilding the fonts as Unicode — findings, PoC, what is left |
| `docs/REMOTION-PATCH.md` | The renderer changes |
| `docs/RELEASES.md` | Which archive answers which need |
| `docs/FONTS-DIR.md` | The fonts, and the licensing question |
