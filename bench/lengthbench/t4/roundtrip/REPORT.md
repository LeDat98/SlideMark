# Foreign-deck round trip, t4 (python-pptx open-brief deck → `slidemark import` → `build`)

Measure: `bench/roundtrip_compare.py` (per-slide mean pixel difference on 320×180 grey, golden tolerance 8).
`report.json` holds `before_title_fix` and `after_title_fix` (lane D, 2026-10-07). Sheets: `compare-1.png`, `compare-2.png`.

| Run | Mean | Slides over 8 | deck.md vs build.py | Import warnings |
|---|---|---|---|---|
| Before the title fix | 36.43 | 15 / 15 | 2,074 / 7,560 = 27% | 0 |
| After the title fix | 36.20 | 15 / 15 | 2,049 / 7,560 = 27% | 0 |

The title fix (glyphs and bare numbers are never the title) repairs slides 13 and 15 structurally and moves the
mean by only 0.2: what remains is design (backgrounds, colours, sizes, badges), not structure. The token gate
(≤ 40%) already passes.

## Per slide (after the title fix; my own read of the sheets)

| Slide | Diff | What differs |
|---|---|---|
| 1 | 93.8 | cover: navy full-slide background, orange left rule and blue bottom bar gone (white slide) |
| 2 | 20.2 | three cards lose the coloured top stripe, shadow and big coloured numerals 01/02/03 |
| 3 | 19.3 | four big-number tiles: the 40 pt coloured numbers fall to body size, stripe colours lost |
| 4 | 17.8 | five metric rows: large blue values and small grey "(2026)" runs become one uniform line |
| 5 | 27.2 | bar chart: per-point colours lost (all bars navy); the side panel loses its coloured numbers |
| 6 | 53.7 | three chevrons: colours lost (all navy), cards plain, takeaway bar not navy, text sizes shrink |
| 7 | 28.7 | table: the highlighted first row (amber tint, large coloured values) is plain |
| 8 | 70.5 | price slide: the dark statement panel with big 9,800 / 10,800 is white and tiny; the numbered badges (four colours) are bare digits |
| 9 | 22.6 | four cards: stripe colours, shadow and big numerals lost |
| 10 | 30.2 | risk table: the orange arrow column and zebra rows differ |
| 11 | 23.9 | bar chart with per-point colours lost; the side panel's big "150億円" total is body size |
| 12 | 36.6 | three metric rows plus a navy takeaway bar (now plain grey); a stacked chart whose grey series became teal |
| 13 | 17.6 | quote card: title now correct, but the 96 pt orange quote mark is tiny, the quote is 16 pt instead of 38 pt, the orange left bar and right-aligned attribution are lost |
| 14 | 56.9 | chevrons as slide 6, plus the navy takeaway bar and larger card text lost |
| 15 | 24.0 | numbered rows: title now correct, but the coloured square badges and 30 pt row text are gone |

Lanes A (span sizes, card stripes, number headings, cover bands), B (tiles, badges, quote, panel recognition) and
C (chevrons, table highlight, chart colours, backgrounds) target these rows.
