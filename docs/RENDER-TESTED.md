# Song-tested fonts — what actually rendered a real lyric video correctly

This is the list to answer from when someone asks *"which font can I make a
lyric video with?"* It is **not** the layout-verifier's list
(`verify_layouts.py` = 79/79 pass) and not the preferred-fonts list (42
entries). It is the list of fonts that rendered an **entire real song** —
Allare, 35 lines, 6:54, candrabindu + virama + punctuation-heavy — and
survived a **human eye-check** of the video.

Verified ≠ song-tested. `verify_layouts.py` proves keys reach real glyphs;
`check_song.py` proves the layout has the song's characters; **neither can
prove the glyphs are the right ones in that font** — only a rendered video
watched by a human does that. Two fonts below pass every automated check and
still spell words wrong.

Method, per font: class check in `sweep.json` → round-trip encode → render
the full song with strict end timings → eye-check the known-hard window
(1:37–2:25: जाऊ, फर्केर जाऊ, नलाऊ, प्रीति, हो.. म त हावा सँगै आउँछु,
झुट्टो, सोझो) → human verdict. Renderer: `lyric-studio`'s `render.mjs`
(see its `docs/FONTS-VERIFIED.md` for the same list from the renderer's
side). Date of record: **2026-09-30**.

## ✅ WORKING — 11 fonts, safe for lyric videos

**Legacy / PREETI class** — render with `--legacy-font fonts/<slug>/<file>.ttf`
(resolve the file with `py scripts/which_fonts.py fonts/<slug>/`):

| Font | Slug | Look |
|---|---|---|
| ARAP007 | `arap007` | brush-stroke bold |
| CV Haha | `cv-haha` | rounded soft |
| Katmandu | `katmandu` | thin classic serif-like |
| MKali | `mkali` | thin, light |
| PawanG | `pawang` | clean bold |
| Shreenath Bold | `shreenath-bold` | condensed tall display |
| Himalayabold | `himalayabold` | soft rounded classic |
| Ananda Lipi Bold BT | `ananda-lipi-bold-bt` | heavy traditional headline |

**Unicode** — render with `--font-file fonts/<slug>/<file>.ttf`; lyrics are
handed over unchanged, no transcoding, no legacy pitfalls:

| Font | Slug | Look |
|---|---|---|
| Arya Bold | `arya` | modern serif-bold |
| Kalam Bold | `kalam` | handwritten bold |
| Rajdhani Bold | `rajdhani` | condensed display |

(Yantramanav Black is also pipeline-verified end to end on this song and
remains the lyric-studio default; it was not part of this user eye-check.)

## ❌ NOT WORKING for real songs — 34 of the 42 preferred

**29 AMS/GENERATED fonts — gate-rejected in seconds.** Their aNepali layouts
have no candrabindu `ँ` or virama `्` slots, and any real Nepali song needs
both (`सँगै`, `आउँछु`, `फर्केर`). This is the same finding as
[SONG-CHECK.md](SONG-CHECK.md), now confirmed per font on a real render:
AMS 1/2/4/5/7, Aaditya, Aakash, Aasmi, Aakul 4/5, Barakhadi 1, Chandrakant,
Chhatrapati, Darshana, Diya, Ganesha, Gourav Bold, Harshdeep, Hastkala,
Hastkala 1, Jiwan, Kartik, Karuna, Kasturi 1, Lekhan 1/1 Bold/4/5, Manoja.

**5 fonts declared PREETI but cannot speak it** — `0012-arap`, `0017-arap`,
`ananda-fanko-2`, `arap-010`, `ganga-1`. Their binaries have no ink on the
Preeti key slots, so the video prints raw ASCII (`hfpm,` instead of जाऊ,)
**with exit 0 and no error from any gate**. Caught only by a pixel test
(top-22%-band ink ratio ≈0.089 = raw ASCII vs >0.10 = real Devanagari
shirorekha) and by eye. **`sweep.json`'s "declared preeti" class is not
evidence a font can render Preeti keys.**

**2 fonts spell some words wrong at the glyph level** — `deepankar`,
`abhinav`. Both are genuine PREETI-class fonts; the converter hands them the
same correct keys the 8 working PREETI fonts render fine, their cmaps cover
every key, and frame-checks of the known-hard words are correct — yet the
human spotted wrong spellings elsewhere in the video. This is a defect inside
the font's own glyph drawing (some key combination it was drawn to render
incorrectly), **unreachable by any converter fix**. Until the exact words are
catalogued, treat both as do-not-use for lyric videos.

## Rules for agents

1. **Answer font recommendations from this file, not from the preferred list.**
   "Usable as-is" means the plumbing exists, not that the video is correct.
2. **A class is a claim, not a proof.** 5 of 10 "PREETI" fonts print raw
   ASCII. If a font has no row in the WORKING table, run the full method
   above before shipping it.
3. **The human eye-check is the acceptance test.** Every automated gate
   passed for deepankar and abhinav; the videos were still wrong.
4. When a new song's font set is eye-verified, add it to the WORKING table
   with the date and the song name.
