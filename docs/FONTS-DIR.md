# Fonts

`fonts/<slug>/` holds the font binaries fetched from
[assets.anepali.com](https://www.anepali.com), unpacked from each font's
published archive. 214 fonts, ~479 `.ttf` files plus readmes, about 113 MB.

## Read this before using one commercially

aNepali states on its own index:

> The fonts presented on this website are their authors' property, and are
> either freeware, shareware, demo versions or public domain. Please look at
> the readme-files in the archives or check the indicated author's website for
> details, and contact him/her if in doubt.

That is the publisher's own statement, and it is not a licence. It says the
status varies per font and that the readme is the thing to check.

**Each font's terms are its author's.** Several are explicitly free for
commercial use, several are demo or shareware, and at least two in this
collection are the property of a commercial foundry. This repository is
private and is for your own use — it does not make the licensing question go
away, and it does not cover a video you publish or broadcast.

What to do before a font goes on screen in front of an audience:

1. Read the readme in that font's folder. It travels with the archive for a
   reason.
2. Prefer a font that states a licence you can name — the `UNICODE` class
   (58 of the 214) is mostly SIL OFL, which covers commercial and broadcast
   use outright.
3. If the readme is absent or unclear, ask the author.

## What is here

| Class | Count | Use |
|---|---:|---|
| `UNICODE` | 58 | Install, then `--font "<family>"`. No transcoding, no layout file. |
| `PREETI` | 77 | `--legacy-font` with `--layout Preeti`. |
| `GENERATED` | 71 | `--legacy-font` with `--layout-file layouts/<slug>.json`. |
| `NOTABLE` | 8 | Legacy with no published character table. No generated layout. |

`py scripts/which_fonts.py fonts/` prints the exact command for any font in
here.

## The layouts are separate, and they are ours

`layouts/*.json` are the derived work in this repository: a description of
each font's own key encoding, read from its published character table. They
are not the fonts and carry no separate licence question.

Three characters — `ङ`, `ञ`, `ज्ञ` — are absent from every generated layout.
See `docs/METHOD.md` for why, and `README.md` for what to do about `ज्ञ`, which
does occur in lyrics.

## Refreshing

```bash
py scripts/fetch_fonts.py --all          # re-fetch everything
py scripts/fetch_fonts.py ams-manthan    # just one
py scripts/fetch_fonts.py --list         # what is available
```

Nothing is deleted on a re-fetch; archives are only re-downloaded when asked
with `--refresh`.
