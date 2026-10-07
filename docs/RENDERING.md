# Rendering fonts (previews, goldens, round-trip measure)

Office and brand fonts are not installed on Linux, so LibreOffice substitutes something. What it picks must not
depend on the machine, or a golden image, a gallery PNG and the DL3d round-trip number drift for reasons that
have nothing to do with the deck.

## What is installed (this container, 2026-10-07)

IPAGothic, IPAPGothic (Japanese), WenQuanYi Zen Hei (+ Mono, Sharp), Liberation Sans / Serif / Mono, DejaVu Sans /
Serif / Sans Mono, FreeSans / FreeSerif / FreeMono. No Noto CJK, Carlito, Inter, Montserrat.

## What each requested font really falls back to

Measured by converting a one-slide deck per font (`Hello Rg 123 日本語テキスト`, regular and bold, `a:latin` + `a:ea`
+ `a:cs` set to the font) to PDF with `soffice` and reading the embedded fonts with `pdffonts`.

| requested font | system fontconfig (no config) | HEAD preview aliases (before) | `fonts/fonts.conf` (now) |
| --- | --- | --- | --- |
| Meiryo, Yu Gothic, Yu Gothic UI, MS PGothic | DejaVu Sans + WenQuanYi Zen Hei | IPAPGothic | IPAPGothic |
| MS Gothic | DejaVu Sans + WenQuanYi | IPAGothic | IPAGothic |
| Hiragino Sans / Kaku Gothic, Noto Sans JP | DejaVu Sans + WenQuanYi | DejaVu Sans + WenQuanYi | IPAPGothic |
| Yu Mincho, MS Mincho | DejaVu Sans + WenQuanYi | DejaVu Sans + WenQuanYi | Liberation Serif + IPAPGothic |
| Arial, Helvetica | Liberation Sans (+ WenQuanYi for CJK) | same | Liberation Sans + IPAPGothic |
| Calibri | DejaVu Sans | Liberation Sans (Carlito if present) | Liberation Sans (Carlito if present) |
| Inter, Segoe UI, Verdana, Montserrat, unknown | DejaVu Sans | DejaVu Sans (Segoe UI: IPAPGothic) | Liberation Sans + IPAPGothic |
| Georgia, Cambria | DejaVu Serif | DejaVu Serif | Liberation Serif + IPAPGothic |
| Times New Roman | Liberation Serif | Liberation Serif | Liberation Serif + IPAPGothic |
| Consolas | DejaVu Sans Mono | Liberation Mono | Liberation Mono + IPAGothic |
| Courier New | Liberation Mono | Liberation Mono | Liberation Mono + IPAGothic |

Bold is the family's own bold where it exists (Liberation, DejaVu) and a synthetic bold for IPA fonts (no bold
face). `fc-match` alone is not enough: LibreOffice also asks fontconfig for per-glyph fallback, so a Latin family
paired with Japanese text pulled WenQuanYi in for the kanji.

## The fix

`src/slidemark/fonts/fonts.conf` aliases every family above to one installed family (generic `sans-serif` /
`serif` / `monospace` too, so an unknown family ends in Liberation, not DejaVu), and lists IPAPGothic second so
missing CJK glyphs come from it. `slidemark.preview` passes it to LibreOffice as `FONTCONFIG_FILE` on Linux when
the variable is not set (set it yourself to use another file; `/etc/fonts/fonts.conf` gives the raw system
behaviour). Decks are never touched: the XML still names Meiryo / Yu Gothic / Inter.

Optional, not used by the goldens: `apt-get install fonts-noto-cjk` (about 60 MB) gives a real bold Gothic. To use
it, put `Noto Sans CJK JP` first in the CJK lists of `fonts.conf`, then regenerate the goldens.
Goldens and the gallery are made with the installed set above; do not make tests depend on the network.

## Font floor of the round-trip measure (DL3d)

Mean per-slide difference of the 320x180 grayscale renders (`bench/roundtrip_compare.py` measure), 15 slides.

| measurement | t4 (Meiryo) | t2 (Yu Gothic) |
| --- | --- | --- |
| original rendered twice (determinism) | 0.00 | 0.00 |
| original vs a copy with the importer's font names (`latin` / `ea` rewritten), system fontconfig | 0.00 | 0.00 |
| same, HEAD preview aliases | 0.00 | 0.00 |
| same, `fonts.conf` | 0.00 | 0.00 |
| round trip (import, build, render), system fontconfig | 25.27 | 21.37 |
| round trip, HEAD preview aliases | 24.95 | 21.10 |
| round trip, `fonts.conf` | 24.95 | 21.10 |

The floor from font names is zero: the importer states the original's families (t4: latin Meiryo, ea Yu Gothic;
t2: Yu Gothic), and in every mode both names fall to the same family, so the original and the rebuild were never
rendered in different fonts. The remaining 21 to 25 points are design, not fonts. What this cannot measure is the
distance to real Meiryo / Yu Gothic in PowerPoint; only a render with those fonts could.

## What the change did move

Goldens whose decks ask for Georgia, Inter, Montserrat or other non-aliased families (DejaVu before, Liberation
now) shifted by up to 8.7 of 255 per slide and were regenerated in one commit (changed: 01, 03, 09, 10, 11, 13,
14, 15, 17, 18, 19, 20, 21, 22, 25; the tolerance is 8). `19-vi-consulting-brand` (Montserrat + Inter), red for
weeks at 9.5 on the unaliased fonts, rendered at 8.0 or less against its old golden with `fonts.conf` and is
now stable by construction.
