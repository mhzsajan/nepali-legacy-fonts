Generated layouts for 214 legacy Nepali fonts, so they render in Remotion and
Chromium instead of silently falling back to a substitute typeface.

Legacy Nepali fonts carry their Devanagari glyphs on ASCII codepoints, with no
Devanagari cmap and no GSUB. Chromium therefore substitutes another font
character by character, with no error. The fix is to transcode lyrics into the
font's own key layout — but that layout was unobtainable: the font cannot
report it, glyph outlines are unreliable, and `npttf2utf` knows only five Nepali
layouts.

aNepali publishes a character table per font, so the layout can be **read** from
the publisher rather than guessed. 79 of the 214 fonts now have a generated,
verified layout.

**Start here:** `docs/GETTING-STARTED.md`

| Class | Count | What it means |
|---|---:|---|
| `UNICODE` | 58 | Renders as-is. No transcoding. Mostly SIL OFL. |
| `PREETI` | 77 | npttf2utf already has the layout. |
| `GENERATED` | 79 | Layout read from the publisher. **All 79 verified.** |
| `NOTABLE` | 0 | Was 8 — all recovered. See the README. |

```bash
git clone https://github.com/mhzsajan/nepali-legacy-fonts
cd nepali-legacy-fonts
pip install -r requirements.txt
py scripts/verify_layouts.py ams-manthan     # proves the install works
```

Verified state: `79 passed, 0 failed` — every generated key checked against the
real font binary. Two fonts additionally confirmed on rendered frames.

Releases carry one archive per class, and the generated archive includes its
layouts. Each archive includes the authors' readmes, which are the terms: these
fonts are their authors' property and are a mix of freeware, shareware and demo.
For a broadcast, the 58 Unicode fonts are the ones with a licence you can name.
