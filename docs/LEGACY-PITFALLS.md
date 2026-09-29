# Pitfalls in the legacy path, and why it is not the default

Everything here was found by rendering real songs, not by reading the
specification. Several of these produce output that *looks* plausible — which
is why they shipped.

Measured on two songs, 110 distinct lyric words, AMS Manthan.

---

## 1. A passthrough is never right, and it looks like a typo

`_cmap_keys` in `layout_encoder.py` is documented as "greedy longest-first
char-map translation; **unknown chars pass through**". That fallback is the
single most damaging thing in this path.

A legacy font has zero Devanagari codepoints. When an unmapped Devanagari
character is passed through to the key stream:

1. the chosen font has no glyph for it, so
2. Chromium substitutes a *different* font for that character alone.

The result is one word drawn in two typefaces, with a visible seam.

**Why it read as a `0` or an `O`** — the reason this is so hard to spot. The
passed-through character is not a key in the legacy font at all; it is a
codepoint with no meaning there. What appears is whatever the *fallback*
font has for it, which need not resemble the intended character. So the
output shows a loose glyph inside an otherwise correct word, and the natural
reading is "the font is a bit odd" or "the typography is busy" — not "three
characters are coming from the wrong font".

`--letter-anim` makes it worse: it wraps every letter in its own span, so
each unmapped character is isolated and gets its own fallback rather than
being absorbed by a neighbour.

**Detect it:** `scripts/passthrough.py <layout.json> <song.lrc>`

```
3 character(s) would PASS THROUGH to a legacy font with no glyph,
and 34 word(s) are affected.
```

This should be a hard error in a pipeline. It is a script here because making
it one is a change in the renderer.

---

## 2. Three characters have no key at all

| Character | Words affected | What it is |
|---|---:|---|
| `्` U+094D | 21 | virama — joins consonants into a conjunct |
| `ँ` U+0901 | 12 | candrabindu (आँ, सँ, कहिँ) |
| `ञ` U+091E | 1 | nya |

aNepali publishes these slots as **Devanagari rather than as a key**. There
is nothing to read and no ground truth to derive one from. They are dropped
from every generated layout and reported.

`ङ`, `ञ`, `ज्ञ` were the known gaps. The virama and candrabindu gaps were
found later and are the ones that actually hurt: they appear in ordinary
words — हिस्सी, विश्वास, प्रीति, आँखा, सँगै, कहिँ — which a character
survey never flags and only a real lyric does.

**Consequence:** a generated layout covers simple syllables well and conjuncts
not at all. If a song has conjuncts, it needs a **Preeti-family** font, where
`npttf2utf` supplies the virama key.

---

## 3. The matra carrier — a whole consonant appears from nowhere

aNepali publishes matras applied to a carrier: the heading is literally
*"Matras - with 'क'"*. The cell therefore **contains the carrier**, and the
mark's own key is what remains after removing it.

Which side the carrier sits on is not a detail — **it is the font's visual
order convention**, and getting it wrong inserts a spurious consonant.

Stripping only a prefix mapped the i-matra to two keys:

```
ि  ->  "ik"        the KA was never removed
```

The encoder then wrote a KA where none belonged:

```
source   रिसले
keys     ikrsalae
rendered किस्तो          <- valid Devanagari, wrong word, no error
```

**Fix:** try prefix, then suffix, then accept the cell as-is. Never guess
beyond those three. A *pre-base* matra is stored **after** its consonant in
Unicode but must be **drawn before** it, which is why its cell reads
mark-then-carrier (AMS Manthan publishes कि as `ik`).

Caught by `scripts/diag_encode.py`, which prints the encoder's output beside
the source. On the AMS Manthan battery:

```
0 correct, 31 wrong        before
```

---

## 4. Round-trip verification is meaningless for a generated layout

`candidates()` generates several candidate encodings and keeps the first that
decodes back to the source. For `npttf2utf`'s five layouts that check is
meaningful.

For a **generated** layout, `_decode` is the layout's *own inverse map* — a
naive codepoint↔key lookup that knows nothing about ordering. It will agree
with a candidate that is self-consistent and visually wrong.

It has to. A generated layout carries no pre-rules or post-rules, so the
"decoder rules fix order" comment in `candidates()` is simply false for it.

**Order is the whole problem.** A legacy font has no shaping engine — no
HarfBuzz, no GSUB. It draws glyphs strictly in codepoint order, so **the key
sequence *is* the visual order** and must be exactly right.

`verify_layouts.py` checks that every key resolves to a real glyph. It cannot
prove the glyph is the *correct* one. Only a rendered frame does.

---

## 5. `lrc_legacy.py` tells you, and it is easy to skip

The transcoder prints this on failure:

```
!! not round-trip exact: 'रिसले' -> 'ikrsalae'
```

AGENTS.md says plainly: *"Loud `!! not round-trip exact` on stderr means a
word needs a manual fix — do not ship it silently."*

On the AMS Manthan path it fires on nearly **every word**. It was visible in
the render log the whole time and read as noise.

**Treat any occurrence as a stop condition.** A clean run says:

```
OK out/_legacy-Kali Kali.lrc: 19 lines encoded with layout Preeti
```

with no `!!` lines above it.

---

## 6. Length came from lyrics, not audio

Unrelated to fonts, and it produced a video that was visibly wrong.

`calculateMetadata` sets the duration to `max(audio length, last cue end)`.
With no `.ends.txt` the cue ends are *estimated*, so the last cue can be far
short of the real end of the song.

Measured:

| Song | Audio | Last lyric | Video ended |
|---|---|---|---|
| Kali Kali | **6:49.1** | 5:47.5 | **5:49.5** — 60s short |

A song whose audio was copied into the render is safe, because the audio is
probed. A `--no-audio` text-only overlay has nothing to probe, so **the
length must be supplied explicitly**. A lyric video that stops before the
song does is a real defect, and it is invisible in a spot check.

---

## The summary

| | Unicode font | Legacy path |
|---|---|---|
| Setup | `--font "Nirmala UI"` | layout file + map + Python |
| Characters that can fail | none | 3, affecting ~⅓ of words |
| Wrong-typeface strays | impossible | the default failure mode |
| Map bugs to maintain | zero | one per font, times 79 |
| Needs the same machine | no | yes, for the tooling |

The legacy tooling in this repository is correct and verified for what it
covers. It is simply the wrong default when any Unicode font will do — and
58 of the catalogue, including one built into Windows, will.
