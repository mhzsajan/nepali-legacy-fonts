# A verified layout is not a writable song

`verify_layouts.py` asks whether every key in a layout reaches a real glyph in
that font's `.ttf`. It passes 79 of 79 layouts. **It cannot tell you whether a
layout can write a particular song**, and those two answers disagree often
enough to cost an afternoon.

```bash
py scripts/verify_layouts.py --all          # 79/79 pass
py scripts/check_song.py --font ams-manthan song.lrc
                                      # 0/79 can write Allare
```

## The worked case

AMS Manthan is a real font, with a real generated layout, verified end to end.
It still cannot write Allare:

```
lines total            : 35
lines with no key      : 15 (43%)
characters with no key :
    U+094D  ्   x14   virama (joins a conjunct; dropping it changes the word)
    U+0901  ँ   x13   candrabindu
distinct words affected: 16
    फर्केर   प्रीति   सँगै   आउँछु   हराउँछु   झुट्टो   सम्हाल्ने
    परेँ   अल्लारे   पर्यो   ...
```

Two characters. That is the entire cause.

## Why the virama is not a missing diacritic

This is the part worth being careful about, because the virama looks like a
mark and behaves like a letter.

A Devanagari conjunct is written consonant + virama + consonant. The virama is
not decoration on the first consonant — it is the instruction that fuses them
into one glyph. Remove it and `प्र` stops being one character and becomes two:
`प` then `र`.

So the failure does not read as "a mark is missing". It reads as a *different
word*:

```
फर्केर   p + virama + r + ka + e-matra + r
        -> फ + r + ka + r
        =  फरकर
```

`फर्केर` and `फरकर` are different words, and the video shows one of them in
perfect Devanagari at full size for several seconds. A viewer who knows the
language reads the wrong lyric. Nobody notices in a four-minute file.

The candrabindu is a gentler failure — it is a genuine diacritic, so losing it
changes the spelling (`सँगै` → `संगै`) but usually not the word.

## The cause is upstream, so no layout file can fix it

aNepali publishes a font's key table, and this repo generates a layout from it.
The candrabindu and the virama **are not in that table** — aNepali emits them
as Devanagari characters rather than as a key. There is therefore nothing for
`anepali_charmap.py` to read, and no generated layout anywhere that contains
them. All 79 layouts fail this song for the identical reason, which is why
`check_song.py --all` reports zero rather than suggesting a different legacy
font.

The full set of five, from the Tier table in the [README](../README.md#which-fonts-work-without-issue):

| Character | Code point(s) | Note |
|---|---|---|
| `ङ` | U+0919 | plain letter, drops silently |
| `ञ` | U+091E | plain letter, drops silently |
| `्` | U+094D | **splits a conjunct into two letters** |
| `ँ` | U+0901 | candrabindu, drops silently |
| `ज्ञ` | U+091C U+094D U+091E | a *sequence*, not a codepoint |

`ज्ञ` is the awkward one: it has no precomposed code point of its own, so even
if a publisher exposed a key for it the layout would still have to carry two
letters and a virama. It cannot be a single-key entry, ever.

## Nothing downstream catches this

This is the reason the check is worth having as a separate script. The render
of Allare in AMS Manthan:

- exits **0**
- is the right length — 417.5 s, matching the audio
- is 1920×1080, H.264, no audio as requested
- has a **pure black** background where no lyric is due
- passes every output check this repo or the renderer has

All true, all worthless. A wrong letter is not a malformed file. Every check
that exists looks at the container, the timing, the geometry or the pixels
*behind* the text; none of them looks at the text. And the converter does not
warn, because from its side there was nothing to encode.

Two downstream behaviours, both silent:

- the converter **drops** the unmappable character (`फर्केर` → `फरकर`); or
- it passes the character through as Devanagari and the browser **falls back to
  a different typeface mid-word**, so a word is set in two fonts and nobody
  says so.

Which one you get is a property of the converter, not of the font. Neither is
an error.

## Tier A exists because of this

A Unicode font needs no layout, no key table and no conversion, so there is no
step at which a character can be lost. The 58 Tier A fonts in the README are
not "nicer looking" — they are the only ones where this entire class of failure
does not exist.

Reach for Tier B or C when the typeface specifically matters (a client's brand
font, a period-correct look), and run `check_song.py` first. Reach for Tier A
otherwise.

## Using it

```bash
py scripts/check_song.py --font ams-manthan song.lrc        # one layout
py scripts/check_song.py --font x --all song.lrc            # all 79
py scripts/check_song.py --word "फर्केर" --font ams-manthan # one word
```

Exit code is 0 when every line survives and 1 when any do not, so it gates a
render in a script:

```bash
py scripts/check_song.py --font "$SLUG" song.lrc || {
  echo "font $SLUG cannot write this song -- pick a Tier A font" >&2
  exit 1
}
```

It reads the `.lrc` the same way the renderer does: stamps and `[ti:]/[ar:]`
metadata off, multi-stamp lines deduplicated rather than counted twice.
