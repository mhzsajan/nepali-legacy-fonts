# Font verdicts — what is usable, and what is merely untested

**`verdicts.json` in the repository root is the authority.** This file explains
it. It deliberately contains **no font tables** — a table here would be a second
copy to keep in step, and a second copy is how `abhinav` came to be listed as a
verified legacy font it is not, and how four PREETI fonts came to sit in a
"working" list having never been rendered.

## Read it

```bash
py scripts/check_verdicts.py            # is the data self-consistent?
py scripts/check_verdicts.py --report   # the four groups, human-readable
py scripts/check_verdicts.py --json     # for another program to consume
```

`lyric-studio` calls the `--json` form. It holds no copy of any of this; if you
find font verdicts in that repository they are stale by definition, and the
fix belongs here.

## The four states

| state | what it means | what to do |
|---|---|---|
| **working** | rendered a full song **and** passed a human eye-check | use it |
| **broken** | tested, and rejected — `reason` says why | do not use; that is a font bug |
| **untested** | **no evidence either way** | render it, look at it, then move it |
| **failed** | cannot write real songs at all (no candrabindu / virama slot) | never use for lyrics |

> **Untested is not a pass.** A font nobody has rendered has told you nothing.
> The states are kept apart because they call for different next actions: a
> broken font needs a fix or a replacement, an untested font needs ten minutes
> and a pair of eyes.

## What "song-tested" costs to earn

It is **not** the layout-verifier's list (`verify_layouts.py`, 79/79 pass) and
not the preferred-fonts list. Per font: class check in `sweep.json` → round-trip
encode → render the full song with strict end timings → eye-check the
known-hard window → human verdict.

Verified ≠ song-tested. `verify_layouts.py` proves keys reach real glyphs.
`check_song.py` proves the layout has the song's characters. **Neither can prove
the glyph is the right one** — only a watched render does that, and two fonts
here pass every automated check and still spell words wrong.

Renderer: `lyric-studio`'s `render.mjs`. Test song: **Allare** (35 lines, 6:54,
candrabindu + virama + punctuation-heavy). Date of record: **2026-09-30**,
extended **2026-10-01** with production renders from a seven-video batch.

## "working" is a claim about a SONG, not about a font

A `working` verdict means *this font rendered this song and a person looked at
it*. It does not mean the font is right on the next song, and the two are
routinely confused because the schema has one state and a song has many.

The failure is specific and it is the worst kind: a legacy face can pass every
mechanical check on a new song — no leaked words, no uncovered keys, the round
trip clean, the render log silent — and still draw the **wrong glyph shape**,
because "the key resolves to a real glyph" and "the glyph is the right
character" are different claims and only a person can make the second one.

`preeti_song_safety` is a **mechanical** table. It answers "will a word be
corrupted?". It does not answer "will the word be spelled correctly?", and a row
in `safe_songs` is not a promise that the glyphs are right. Two entries in this
repository are `working` on the strength of one song each.

So: **before putting a legacy font on a song it was not tested on, render a frame
and look at it.** It costs seconds, and on this class of failure nothing else in
either repository will tell you.

## The handpicked 42, accounted for

7 working, 5 broken (print raw ASCII), 1 broken (wrong glyphs), 29 failed (no
candrabindu/virama slot), 0 untested. That is 42.

The wrong-glyphs group is **1** of the 42 and **2** overall: `abhinav` is
broken but is not one of the handpicked. That one off-by-one is what made
`7 + 29 + 5 + 2` look like 43 against a stated 42. `check_verdicts.py` asserts
the arithmetic, so the next discrepancy is a red check rather than a paragraph
of hedging.

Beyond the 42, 166 of the 214 catalogue fonts are untested. Only the 62
PREETI-class ones are worth a song render: `GENERATED` layouts cannot write
real songs, and `UNICODE` fonts cannot fail the legacy way.

## Rules for agents

1. **Answer font questions from `verdicts.json`, and from nowhere else.** No
   WORKING row means: say so, and offer to test it. Never infer usability from
   the preferred list, from a class in `sweep.json`, or from a clean
   round-trip.
2. **A class is a claim, not a proof.** Five of ten "PREETI" fonts print raw
   ASCII with exit 0 and no error from any gate.
3. **The human eye-check is the acceptance test.** Every automated gate passed
   for `deepankar` and `abhinav`; the videos were still wrong.
4. **Do not mark a font working without rendering the song and looking at it.**
   Record the date and the song alongside the verdict.
5. **Edit `verdicts.json`, not this file.** This file explains the data.
6. **A `working` verdict is about a song, not a font.** See "working is a claim
   about a SONG" above. A row in `preeti_song_safety.safe_songs` means the
   encoding will not corrupt a word; it does **not** mean the glyphs are the right
   characters. Render a frame before putting a legacy face on a song it was never
   tested on.
