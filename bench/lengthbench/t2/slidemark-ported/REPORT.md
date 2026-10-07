# Porting the python-pptx deck's design decisions to SlideMark (lengthbench t2, design wave 3 lane 4)

Source: `../python-pptx/build.py` (the agent's 15-slide deck, render `../python-pptx/sheet.png`).
Port: `deck.md` (render `sheet.png`). Baseline for comparison: `../slidemark-wave2/deck.md`.
Everything uses syntax documented in `docs/SYNTAX.md`; no source or doc outside this folder changed.

## Build line (verbatim)

```
$ slidemark build deck.md -o /tmp/ported.pptx --png sheet.png
info slide 3 chart-scale: series '営業利益' (max 96) is under 10% of '売上高' (max 1280): it is drawn as a sliver -> ...
look: theme none, bg #FFFFFF, text #222B36, primary #142B4D, accent #E09F1F; fonts Yu Gothic (headings, body), Yu Gothic (ea); title band off; accent on 1 mark
wrote /tmp/ported.pptx: 15 slides 16:9, 4 charts, 2 tables, notes on 2 slides, 0 warnings (checked: fit, overlap, contrast, text size, word breaks)
$ python bench/agent_accept.py bench/lengthbench/t2/accept.json /tmp/ported.pptx
accepted
```

`slidemark review`: 94/100 (sparse-box warnings on the wide-card KPI/steps rows, which copy the python-pptx look).
The `chart-scale` info is the brief's data (1280 vs 96 on one axis); the python-pptx deck has the same sliver.

## 1. Tokens (o200k_base)

| File | Tokens | vs python-pptx |
|---|---|---|
| `python-pptx/build.py` | 5,263 | 100% |
| `slidemark-wave2/deck.md` (defaults, content only) | 1,261 | 24% |
| `slidemark-ported/deck.md` (all design stated) | **2,283** | **43%** |

Where the 2,283 go: deck header (colors/fonts/sizes/style + 1 css fence) 359; cover as `@html` 218; slide 8 as
`@html` 434; the other 13 slides (content + per-slide forms + chart options) 1,272. The two `@html` slides cost 652
(29% of the deck for 2 of 15 slides).

## 2. Decisions stated in native syntax or tokens

| python-pptx decision | SlideMark line |
|---|---|
| Font Yu Gothic (+ea/cs) | `fonts: heading="Yu Gothic" body="Yu Gothic" ea="Yu Gothic"` |
| 8 named colours | `colors: bg fg primary=#142B4D secondary=#1F5FA8 accent=#E09F1F teal muted surface border` |
| Series palette blue/amber/teal/purple | `palette=secondary,accent,#2A9D8F,#8A5AA8`; per chart `colors=secondary,accent` |
| Type scale title 28, lead 18, box head 20, box text 22, table 20, footnote 13, footer 10 | `sizes: title=28 lead=18 heading=20 body=22 table=20 footnote=13 caption=10` |
| Title navy, lead blue bold | `title.color=primary lead.color=secondary lead.bold=on` |
| Footer text + page number | `footer: 青葉フーズ株式会社` + `num: on` |
| Speaker notes (slides 5, 15) | `??? ...` |
| Square cards, LIGHT fill + LINE border | `card.radius=0` (fill/border from `surface`/`border`) |
| Navy header band on boxes | `heading.band=primary` |
| Table navy header, zebra, left aligned, widths, bold first column | `table.header.fill=primary table.header.color=#FFFFFF table.zebra.fill=surface` + `{align=llll widths=3.9:2.8:2.8:2.6 .zebra hcol=1}` |
| Blue conclusion bar | `conclusion.fill=secondary` + `> 冷凍食品と海外が成長をけん引` |
| Footnote | `※ 各戦略のKPIは個別資料を参照` |
| Column chart, labels outside end, `#,##0`, legend bottom | `column {labels=on legend=bottom fmt=#,##0 colors=secondary,accent}` |
| Pie per-point colours, white bold labels, legend right | `pie {labels=on legend=right colors=...}` |
| Line chart colours, 3.5 pt lines | `line {labels=on legend=bottom colors=...}` + `render.chart_line_width=3.5` |
| Line label above/below (台湾 below) | automatic (`label_collisions`) |
| Bar chart single series, reversed categories, no legend | `bar {labels=on legend=none colors=secondary}` (reversal automatic) |
| KPI form 3 and 4 up | `## 売上高 {.kpi}` + 2 lines |
| 4 / 3 boxes with bullets | `@4` + `##` boxes; 3 boxes need no `@` |
| Process row, chevron head + card, alternating navy/blue | `@4 steps`, `## 7–9月 {.secondary}` on every second step |
| Tall KPI cards (4.4 in) | `layout.kpi_lone_h=0.9 layout.kpi_lone_min_h=0.85` (token) |

## 3. Decisions that needed CSS or `@html`

| Decision | What I wrote | Proposed shortest syntax |
|---|---|---|
| Rule under the title | css `h1 { border-bottom: 2px solid #1F5FA8 }` | `title.rule=secondary` |
| KPI card top stripe | css `.kpi { border-top: 6pt solid #1F5FA8 }` | `kpi.stripe=secondary` |
| KPI label 20 bold navy / value 34 / note 20 bold teal | 3 css rules | `kpi.label.size=20 kpi.label.bold=on kpi.note.color=teal kpi.size=34` |
| Pin box heading 20 / text 22 (auto-growth gives 27/26) | css `.box > h2`, `.box li` font-size | `sizes: heading=20!` ("exact, no growth") or `grow=off` |
| Box heading centred bold | css `.box > h2 { text-align: center; font-weight: bold }` | `heading.align=center heading.bold=on` |
| Slide 10 heading 26 / text 24 | per-slide css fence | `{size=24}` on the `@3` line applying to the row |
| Conclusion 24 bold | css `.conclusion { font-size: 24pt; font-weight: bold }` | `sizes: conclusion=24`, `conclusion.bold=on` |
| Numbered rows (slide 8) | `@html` (434 tokens) | `@rows`: numbered bars from an ordered list, `rows.num.fill`, `rows.fill` |
| Cover: full navy, amber rule at 61%, teal bar, light-blue subtitle | `@html` (218 tokens); native `@cover bg=primary dark` + `cover.*` gave a plain navy slide | `cover.rule` working with `bg=`, `cover.bar=teal`, `cover.band=none` independent of `title.band` |
| Footer + number on an `@html` slide | typed by hand into the html | `footer:` / `num:` drawn on `@html` slides |

## 4. Decisions I could NOT state

| Decision | Tried | Proposed syntax |
|---|---|---|
| Navy strip across the top of every slide | css `slide { border-top }` -> `css-unsupported` x15 | `style: top.bar=primary top.bar_h=0.12in` |
| Divider between KPI value and note | none | `kpi.rule=border` |
| Teal "■" bullet glyph | none (`li::marker` not a selector) | `bullet=■ bullet.color=teal` |
| 22 pt spacing between box items | not tried (`layout.para_gap` is a ratio) | `para.gap=22pt` |
| "STEP 1..4" teal caption under each card | none | `@4 steps num` |
| Step card text bold, centred, 24 pt | css `.steps-card`: no effect, no diagnostic | `steps-card.align=center steps-card.bold=on steps-card.size=24` |
| Alternate chevron colours without touching the card | `{.secondary}` recolours arrow and outlines card; `nth-child` css ignored; `{fill=}` recolours card (2.2:1) | `steps-arrow.fill=primary,secondary` (cycling list) |
| Chart text 14 / axis 13 (SlideMark gives 20-24) | none per chart | chart option `size=14` |
| Column gap 80 per chart | `render.chart_gap` is deck-wide | chart option `gap=80` |
| Line markers filled 9 pt | none | chart option `marker=9` |
| Gridline colour, no value-axis line | none | `render.chart_grid=border`, `axis=grid` |
| Exact KPI card height 4.4 in | only body-share tokens | `{h=4.4in}` honoured on KPI rows |
| Custom colour name in `colors=` of a chart | warns `bad-chart-option` (only 10 preset names or hex) | accept names declared in `colors:` |

Count: 32 decisions listed -> 21 covered natively or by tokens, 9 CSS or `@html` workarounds, 13 not statable (a few
appear in two sections because they are partly native, partly CSS). Deviations kept to reach 0 warnings: teal note text
`#2A9D8F` -> `#217B70` (3.0:1 on `#EEF2F7`), KPI numbers shrink to fit (28 vs 34 pt, 49 vs 54 pt), alternate step cards
carry a blue outline, slide 8 rows start at 1.92 in instead of 2.0.

## 5. Defaults overridden vs kept

Overridden: theme (`none`), every colour and the palette, font family, the type scale, `title.band=none`,
`heading.band=primary`, `card.radius=0`, KPI class (colour, size, stripe, label), table header/zebra/widths/align,
conclusion fill and size, chart line width, per-chart series colours, KPI card height, two whole slides (`@html`).

Kept: grid, gaps, margins and card padding; title/footer/footnote/conclusion placement; `lang: ja` line breaking, CJK
squeeze, orphan control, U+2060 joiners; chart internals (plot placement, axis rules: bar with `labels=on` and 4
categories hides the value axis while python-pptx kept it; pie share labels; label-collision alternation; reversed bar
categories; text sizes); table row growth, bar attach, vertical centring of sparse slides, step arrow height; the
contrast safety net (it changed one of the agent's colours).

## 6. What this proves

SlideMark states most of the agent's deck frame and per-slide choices in 43% of the tokens (2,283 vs 5,263), and the
chart and table decisions in one fence line each. The remaining cost is chrome with no syntax yet: top strip, KPI
stripe/label styling, bullet glyph, step labels, numbered rows, styled cover. Closing the top five (`top.bar` /
`title.rule`, `kpi.*` tokens, `@rows`, `steps num` + cyclic arrow colours, chart `size= gap= marker=`) would bring the
port to about 1,500 tokens (29%) with no `@html` and no css fence (estimate, not measured).

Two silent failures worth a diagnostic: the css selectors `.steps-card` and `.steps-arrow:nth-child(even)` are
accepted with no effect and no warning.
