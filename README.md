# Nepali fonts for Remotion

Key layouts for 214 Nepali fonts, so a legacy face renders in Chromium instead
of silently falling back to a substitute typeface — plus the check that tells you
whether a font can write your lyrics *at all*.

**This repo makes fonts. It does not render video.** For that, see
[`lyric-video-remotion`](https://github.com/mhzsajan/lyric-video-remotion).

```bash
git clone https://github.com/mhzsajan/nepali-legacy-fonts
cd nepali-legacy-fonts
pip install -r requirements.txt
py scripts/verify_layouts.py ams-manthan     # proves the install works
```

---

## Read this before choosing a font

**A Unicode font is almost always the right answer.** "Usable" is three different
things here, and only one of them cannot produce a wrong letter:

| Tier | Fonts | What can still go wrong |
|---|---|---|
| **A — no issue possible** | **58 `UNICODE`** | **Nothing.** Native Devanagari codepoints, no transcoding, no layout file to be wrong. |
| **B — verified, 5 known gaps** | **79 `GENERATED`** | `ङ`, `ञ`, `ज्ञ`, `्`, `ँ` are in no layout. Silently dropped or drawn in a fallback typeface mid-word. |
| **C — verified, 5 known gaps** | **77 `PREETI`** | Same five, plus the map lives in the `npttf2utf` package, not here. |

**If you are asked for a font that works without issue, answer from Tier A
only.** Tier B and C are *verified* — every key reaches a real glyph in that
font's `.ttf` — but verification cannot cover the five characters aNepali never
publishes as a key, and there is no way to add them from this source.

`Nirmala UI` ships with Windows 11, so it needs nothing installed — which also
means it behaves identically on a home PC and on a show laptop.

```bash
node render.mjs song.mp3 song.lrc --no-audio --length 417.10 --font "Nirmala UI"
```

The 58 Tier A fonts: Akshar, Alkatra, Amiko, Amita, Anek Devanagari, Annapurna
SIL, Arya, Asar, Bakbak One, Baloo 2, Biryani, Cambay, Dekko, Eczar, Gajraj One,
Glegoo, Gotu, Halant, Hind, IBM Plex Sans Devnagari, Inknut Antiqua, Jaini,
Jaini Purva, Jaldi, Kadwa, Kalam, Karma, Khand, Khula, Kurale, Laila, Martel,
Martel Sans, Matangi, Modak, Mukta, Noto Sans Devanagari, Noto Serif Devanagari,
Palanquin, Palanquin Dark, Pragati Narrow, Rajdhani, Ranga, Rhodium Libre, Rozha
One, Sahitya, Sarala, Sarpanch, Sumana, Sura, Teko, Tillana, Tiro Devanagari
Hindi, Tiro Devanagari Marathi, Tiro Devanagari Sanskrit, Vesper Libre,
Yantramanav, Yatra One.

---

## Can this font write this song?

`verify_layouts.py` answers a question about the **font**. The question that
matters before a render is about the **song**, and the two disagree often enough
to cost an afternoon:

```bash
py scripts/verify_layouts.py --all              # 79 of 79 pass
py scripts/check_song.py --font ams-manthan song.lrc     # 0 of 79 can write Allare
```

`check_song.py` exits 1 when any line cannot survive, so it gates a render:

```bash
py scripts/check_song.py --font ams-manthan song.lrc || echo "pick a Tier A font"
```

On Allare, AMS Manthan — which passes every layout check — cannot write 15 of 35
lines:

```
15 of 35 lines (43%) contain a character with no key
U+094D virama       x14     U+0901 candrabindu  x13
16 distinct words affected
    फर्केर   प्रीति   सँगै   आउँछु   हराउँछु   झुट्टो   सम्हाल्ने   परेँ
```

**The virama is the dangerous one and it is not a missing diacritic.** It is the
instruction that *fuses* a conjunct; drop it and one character becomes two
letters. So `फर्केर` renders as **`फरकर`** — a different word, set perfectly, for
several seconds. The candrabindu is gentler: `सँगै` → `संगै` changes the spelling,
usually not the word.

**All 79 layouts fail this song**, confirmed across every layout rather than
just the one, because aNepali publishes neither character as a key. No different
legacy font helps.

Nothing downstream catches it. The render exits 0, is the right length, has a
pure-black background, and passes every output check — because every check looks
at the container, the timing, or the pixels *behind* the text, and none of them
look at the text. Full write-up: **[docs/SONG-CHECK.md](docs/SONG-CHECK.md)**.

Also: `--word "फर्केर" --font ams-manthan` tests one word instead of a file.

---

## The problem this repo solves

Nepali design fonts are mostly **legacy**: built for Preeti-era workflows, where
you typed ASCII and the font's ASCII glyphs *were drawn as* Devanagari. Such a
font has **zero Devanagari codepoints** in its `cmap` and **no GSUB/GPOS**.
Chromium — and therefore Remotion — substitutes another font character by
character. No error, no warning.

```bash
node render.mjs song.mp3 song.lrc --font "AMS Manthan"   # renders nothing useful
```

The workaround is to transcode the lyrics into the font's own key layout — but
that needs the layout, and there was nowhere to find it:

- **the font cannot say** — nothing inside it records what `;` was meant to be;
- **outlines are unreliable** — and a visual transcription of a key map had
  already produced wrong letters here (द/ध, श/ष confusion);
- **`npttf2utf` knows five** Nepali layouts, and most popular fonts speak none.

Feeding Preeti keys to `ams.manthan.ttf` gives exactly what the workaround should
prevent: glyphs collapsed onto each other, and a literal `==` where the danda
should be.

## The fix

**aNepali publishes a character table for every font.** Each cell is a **key**,
drawn in that font, under a Devanagari category heading — so a font's layout can
be *read* rather than guessed.

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

If the site ever changes, the tool **refuses to guess**. An off-by-one in the slot
order shifts every later character and yields text that looks fine and is wrong —
the one failure mode that matters here.

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
table** — the check a render cannot do, since a key can exist and still point at
the *wrong* glyph. Two fonts are additionally confirmed on rendered frames
through Remotion: **AMS Manthan** and **AMS Aakash**.

### How `NOTABLE` emptied out

Eight fonts — `AMS Calligraphy 1`–`9` — were listed as *legacy, but the page
publishes no character table*. That was wrong: the tables were there all along.
The parser built its CSS selector from the catalogue **slug** (`ams-1` →
`font-ams-1`), but aNepali paints those cells with a class derived from the
**family name** (`font-ams-calligraphy-1`), so the lookup found zero cells and
read a fully documented font as undocumented.

`anepali_charmap.table_class()` now resolves the class from the page itself — the
token present on cells under *every* calibratable heading — instead of assuming
it. The eight recovered with no other change: each reads the same 13/36/10/13
slots as every other legacy font and verifies against its own `.ttf`. **214 of 214
fonts are now usable**; nothing needs a hand-written map.

## Downloads

Releases carry one archive per class, so you take only what you need:

| Archive | Size | Use with |
|---|---:|---|
| `nepali-fonts-unicode.zip` | 94 MB | `--font "<family>"` — nothing else needed |
| `nepali-fonts-preeti.zip` | 5 MB | `--font-slug <slug>` or `--layout Preeti` |
| `nepali-fonts-generated.zip` | 14 MB | `--font-slug <slug>` — layout ships inside |
| `nepali-fonts-layouts-only.zip` | 40 KB | the 79 maps, no fonts |

The generated archive ships **with its layouts inside** — a generated font is
useless without its map, and shipping them apart is how someone ends up rendering
Preeti keys into a non-Preeti font.

> **Release note:** the `nepali-fonts-notable.zip` archive is retired. Its 8
> fonts moved to `GENERATED` with real layouts, so re-cut the archives with
> `py scripts/make_releases.py` before publishing — the counts above are what the
> repo now produces, not necessarily what a stale v1.0.0 contains.

## Using one

```bash
py scripts/which_fonts.py "C:\path\to\fonts"   # what do I type for this font?
```

`--font-slug` resolves the `.ttf` **and** its layout together, from this repo:

```bash
# 0. can it write this song?  exits 1 if not
py scripts/check_song.py --font ams-manthan song.lrc

# 1. check the cues -- instant
node render.mjs song.mp3 song.lrc --report-only

# 2. transcode and register the font, skip the render
node render.mjs song.mp3 song.lrc --font-slug ams-manthan --prepare-only

# 3. look at ONE frame  <-- not optional
npx remotion still src/index.js LyricOverlay out/check.png --frame=5900 --props=out/props.json

# 4. the real render
node render.mjs song.mp3 song.lrc --no-audio --length 417.10 \
    --font-slug ams-manthan --mode mix --mix-block 8 \
    --word-anim karaoke --letter-anim pop --letter-var 0.03
```

Step 3 is not optional. A wrong layout does not error — it renders the wrong
letters. Seconds here, minutes to spot later.

The renderer expects this repo as a sibling directory, or take `--fonts-repo
<dir>`. There is deliberately **no vendored copy of a layout** in the renderer: a
vendored copy is a copy that can be stale with nothing to warn you, and it
demonstrably was — the one the renderer used to carry still had the pre-fix
i-matra encoding, so `रिसले` rendered as `किस्तो`.

## Preferred fonts

A curated shortlist of 42 fonts, grouped by how much work each one is. **Every
entry is usable as-is** — 29 have a generated layout here, 10 speak Preeti, 3 are
already Unicode.

```bash
py scripts/which_fonts.py "C:\path\to\fonts"   # resolves a file to its slug
```

**GENERATED (29)** — the layout is in this repo, one file per font:

| Font | Slug |
|---|---|
| AMS 1, 2, 4, 5, 7 | `ams-1` `ams-2` `ams-4` `ams-5` `ams-7` |
| AMS Aaditya, Aakash, Aasmi | `ams-aaditya` `ams-aakash` `ams-aasmi` |
| AMS Aakul 4, 5 | `ams-aakul-4` `ams-aakul-5` |
| AMS Barakhadi 1, Chandrakant, Chhatrapati | `ams-barakhadi-1` `ams-chandrakant` `ams-chhatrapati` |
| AMS Darshana, Diya, Ganesha, Gourav Bold | `ams-darshana` `ams-diya` `ams-ganesha` `ams-gourav-bold` |
| AMS Harshdeep, Hastkala, Hastkala 1 | `ams-harshdeep` `ams-hastkala` `ams-hastkala-1` |
| AMS Jiwan, Kartik, Karuna, Kasturi 1 | `ams-jiwan` `ams-kartik` `ams-karuna` `ams-kasturi-1` |
| AMS Lekhan 1, 1 Bold, 4, 5 | `ams-lekhan-1` `ams-lekhan-1-bold` `ams-lekhan-4` `ams-lekhan-5` |
| AMS Manoja | `ams-manoja` |

**PREETI (10)** — the map lives in `npttf2utf`, not here: `0012-arap`,
`0017-arap`, `ananda-fanko-2`, `arap-010`, `arap007`, `cv-haha`, `deepankar`,
`ganga-1`, `mkali`, `pawang`.

**UNICODE (3)** — no transcoding, no layout file, no legacy pitfalls: `arya`,
`kalam`, `rajdhani` → `--font "Arya"` / `"Kalam"` / `"Rajdhani"`.

### Status — what is fixed, what is not

"Usable" and "proven" are not the same thing here, and the difference is silent
wrong letters, not an error.

| Item | Status | Evidence |
|---|---|---|
| All **42 preferred fonts usable** | ✅ **FIXED** | `verify_layouts.py --all` → **79 passed, 0 failed** |
| AMS 1, 2, 4, 5, 7 — were `NOTABLE`, blocked | ✅ **FIXED** | 69 keys each, **0 missing** against the real `.ttf` |
| AMS 6, 8, 9 — the other 3 `NOTABLE` | ✅ **FIXED** | same check, same result |
| `NOTABLE` class | ✅ **EMPTY** | 214 of 214 fonts have a usable path |
| Every key resolves to a real glyph in that `.ttf` | ✅ **VERIFIED** | all 79, checked against the binary |
| Every key resolves to the *correct* glyph | ⚠️ **PARTIAL** | only **AMS Manthan** and **AMS Aakash** confirmed on a rendered frame |
| `ङ` `ञ` `ज्ञ` `्` `ँ` | ❌ **NOT FIXED — cannot be** | aNepali publishes those slots as Devanagari, not as a key. **0 of 79 layouts have them.** |
| Symbols / punctuation mapping | ⛔ **DELIBERATELY NOT DONE** | not calibratable across pages; legacy fonts already keep punctuation on ASCII |
| Fonts rebuilt as Unicode | ⛔ **DELIBERATELY NOT DONE** | would need a `cmap` + GSUB with no ground truth |

**What an agent must not claim:** that a layout is *proven correct*. The verifier
proves the encoder is self-consistent and every key reaches a real glyph. It
cannot tell `द` from `ध`. The only check that can is one rendered frame, and
**only two fonts have had one**.

The ❌/⛔ rows apply to all 39 legacy entries on the preferred list, not to the 3
Unicode ones. Measured across two songs and 110 distinct words, **34 needed a
character no AMS layout exposes** — and the virama and candrabindu gaps were
found by rendering actual songs, not from any word list, because they only occur
in words like "हिस्सी" and "आँखा" that no frequency list flags.

**Zero-risk choice:** `Arya`, `Kalam`, `Rajdhani`, or any of the 58 Tier A fonts.

## Two things to know before trusting a layout

**Verification is necessary, not sufficient.** All 79 pass, meaning every key
reaches a real glyph. It cannot prove the glyph is the *right* one, and it cannot
say anything about your song — see `check_song.py` above.

**The five uncovered characters are not blanks.** Earlier revisions of this file
said they render as a blank box. They do not: the converter either drops them or
passes them through as Devanagari and the browser falls back to a different
typeface for that character alone — which is what produces a word drawn in two
typefaces, and what makes a stray mark read as a `0` or an `O` inside an
otherwise correct word. The virama case is worse than either: it splits a
conjunct, so the word itself changes.

## Deliberately not done

**Symbols are not mapped.** The published symbols section is not calibratable:
the same 29 slots hold *different characters* on different pages. It is also
unnecessary — a legacy font already keeps its Devanagari punctuation on the ASCII
codepoints, so punctuation passes through untouched. Mapping it twice is what
produced the literal `==`.

**Fonts are not converted.** Rebuilding one as Unicode means authoring a `cmap`
*and* GSUB ligature tables with no ground truth to check against.

## Licensing

The fonts are their authors' property and keep their own terms. aNepali:

> The fonts presented on this website are their authors' property, and are
> either freeware, shareware, demo versions or public domain. Please look at the
> readme-files in the archives or check the indicated author's website for
> details, and contact him/her if in doubt.

That is varying status, not a licence. Several fonts here are demo or shareware;
at least two belong to a commercial foundry. A readme ships in every archive — it
is the terms.

**For a broadcast, start with the 58 Unicode fonts**: no transcoding, and mostly
SIL OFL. `docs/FONTS-DIR.md` has the detail.

The **layouts** are the derived work here and carry no separate licence question.

## Documentation

| File | What it is for |
|---|---|
| **[docs/SONG-CHECK.md](docs/SONG-CHECK.md)** | **Why a verified layout still cannot write your lyrics.** Start here. |
| [docs/GETTING-STARTED.md](docs/GETTING-STARTED.md) | Install and first use |
| [AGENTS.md](AGENTS.md) | For an AI agent, and the Windows traps |
| [docs/METHOD.md](docs/METHOD.md) | How layouts are derived, and what that does **not** prove |
| [docs/LEGACY-PITFALLS.md](docs/LEGACY-PITFALLS.md) | The measured costs of the legacy path |
| [docs/REMOTION-PATCH.md](docs/REMOTION-PATCH.md) | Where rendering lives, and why the snapshot copy was removed |
| [docs/RELEASES.md](docs/RELEASES.md) | Which archive answers which need |
| [docs/FONTS-DIR.md](docs/FONTS-DIR.md) | The fonts, and the licensing question |
| [docs/SUMMARY.md](docs/SUMMARY.md) | One-screen state of the project |
| [docs/TONIGHT.md](docs/TONIGHT.md) | Handover notes: repo split, open tasks, commands |
