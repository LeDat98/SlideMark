# Foreign-deck round trip, t4 (python-pptx open-brief deck → `slidemark import` → `build`)

Measure: `bench/roundtrip_compare.py` (per-slide mean pixel difference on 320×180 grey, golden tolerance 8).
`report.json` holds `before_title_fix`, `after_title_fix` (lane D) and `after_lanes_abc` (lanes A + B + C merged, 2026-10-07). Sheets: `compare-1.png`, `compare-2.png`; the imported text is `deck.md`.

| Run | Mean | Slides over 8 | deck.md vs build.py | Import warnings |
|---|---|---|---|---|
| Before the title fix | 36.43 | 15 / 15 | 2,074 / 7,560 = 27% | 0 |
| After the title fix | 36.20 | 15 / 15 | 2,049 / 7,560 = 27% | 0 |
| After lanes A + B + C | 24.95 (t2: 21.10) | 15 / 15 | 3,472 / 7,560 = 46% | 0 |

The title fix (glyphs and bare numbers are never the title) repairs slides 13 and 15 structurally and moves the
mean by only 0.2: what remains is design (backgrounds, colours, sizes, badges), not structure. The token gate
(≤ 40%) already passes.

## After lanes A + B + C (merged; my read of the new sheets)

The deck now looks like the original at a glance: navy cover with its bars, number cards, mixed-size metric rows,
per-bar chart colours, chevrons, highlighted table row, dark price panel, quote card, badge rows. Every slide is
still above 8: what is left is mostly font rendering (Meiryo is not installed, so the original and the rebuild both
fall back and differ by a few percent on every text pixel), card shadows, and a few structural gaps. The token
ratio rose from 27% to 46% because the spans and style tokens now state the sizes and colours; the gate (<= 40%)
is missed on t4 (t2: 37.5%, passes).

| Slide | Diff | What still differs |
|---|---|---|
| 1 | 10.9 | cover: layout matches; title block a little larger, footer caption added (fonts) |
| 2 | 20.6 | three cards: card shadow and text size differ, "01" / "02" numerals smaller than the original (fonts + card inset) |
| 3 | 15.4 | four tiles match; shadows and the 40 pt figures a touch smaller (fonts) |
| 4 | 17.3 | metric rows match in structure; the row bars are flat (no shadow), spans a size off (fonts) |
| 5 | 16.3 | chart colours restored; the panel's rows sit higher and the panel heading is bold (importer coverage) |
| 6 | 46.2 | chevrons and bar recognised; chevron point and heading size, card heights and text size differ (syntax: steps heights are not exact) |
| 7 | 22.8 | highlighted row restored; row heights and header cell text size differ (fonts) |
| 8 | 33.3 | dark panel and badges recognised; panel text positions, badge shape (circle vs the original square) and row heights differ (importer coverage) |
| 9 | 24.8 | stripe colours restored; card height and numeral size differ (fonts) |
| 10 | 27.2 | zebra rows and arrow column present; row heights (table `rowh` is not read for plain rows) and text size differ (importer coverage) |
| 11 | 14.8 | chart + panel match; panel text sizes smaller (fonts) |
| 12 | 32.1 | metric rows and bar recognised; the navy bar is shorter, rows differ in height, stacked chart gap (importer coverage) |
| 13 | 17.8 | quote text wraps in three lines instead of two (fonts), orange left bar and right-aligned attribution still lost (syntax: no `quote.bar`) |
| 14 | 49.5 | chevrons: shape and heading size, card text wraps differently, the takeaway bar is shorter (syntax: chevron geometry) |
| 15 | 25.4 | badges and rows present; row shadow gone, row text smaller (fonts) |

t2 (`bench/lengthbench/t2/roundtrip/`): 38.07 -> 21.10, token ratio 37.5% (1,974 / 5,263). Largest left: the four-chevron
schedule with cards and STEP labels is not recognised (slides 5 and 13, 32.2 / 32.8: plain boxes), centred KPI cards
(label, big number, rule, delta; slides 2, 9, 14) import as left-aligned plain cards (importer coverage), dark header
bands over cards (slides 4 and 10, 31.9 / 30.0) are plain headings, and the blue takeaway bar of slide 6 (32.0) is
shorter and dark instead of blue.
