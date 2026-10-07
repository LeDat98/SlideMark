# Porting the python-pptx deck's design decisions to SlideMark (lengthbench t2, design wave 3 lane 4; DL2 part 1 update at the end of section 1)

Source: `../python-pptx/build.py` (the agent's 15-slide deck, render `../python-pptx/sheet.png`).
Port: `deck.md` (render `sheet.png`). Baseline for comparison: `../slidemark-wave2/deck.md`.
Everything uses syntax documented in `docs/SYNTAX.md`; no source or doc outside this folder changed.

## Build line of the first port (verbatim; the current one is in section 1)

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
| `slidemark-ported/deck.md` before DL2 part 1 (css fence + 2 `@html` slides) | 2,283 | 43% |
| `slidemark-ported/deck.md` after DL2 part 1 (**no css fence, no `@html`**) | **1,577** | **29.96%** |

DL2 part 1 (this update): the cover `@html` (218 tokens) became `@cover bg=primary dark` + 3 `cover.*` tokens + one
`style:` line for the light subtitle; the slide 8 `@html` (434) became `@rows`; the css fence (7 rules) and the two
per-slide css fences became header tokens and per-slide `sizes:` lines. Where the 1,577 go: deck header lines
(`colors` 46, `fonts` 8, `sizes` 38, `style` about 150) about 250; the 15 slides (content, per-slide forms, chart
options) about 1,320. Build line now:

```
$ slidemark build deck.md -o /tmp/ported.pptx --png sheet.png
info slide 3 chart-scale: series '営業利益' (max 96) is under 10% of '売上高' (max 1280): it is drawn as a sliver -> ...
design: colors fonts sizes style footer num; 14/14 slides carry choices
look: theme none, bg #FFFFFF, text #222B36, primary #142B4D, accent #E09F1F; fonts Yu Gothic (headings, body), Yu Gothic (ea); title band off; accent on 3 charts
wrote /tmp/ported.pptx: 15 slides 16:9, 4 charts, 2 tables, notes on 2 slides, 0 warnings (checked: fit, overlap, contrast, text size, word breaks)
$ python bench/agent_accept.py bench/lengthbench/t2/accept.json /tmp/ported.pptx
accepted
```

`slidemark review`: 99/100 (infos only: no key message on 4 slides, 31% empty bottom on slide 10, as in python-pptx).

Native forms added for it (`docs/SYNTAX.md`, `tests/test_design_native.py`): slide-scoped `sizes:` / `style:` lines,
the text shorthand (`kpi.label="20 bold primary"`, `steps-card="24 bold center"`, `heading=center`), `fonts: font=`,
`@kpi`, `kpi.h=4.4in`, table `hlcol=`. Known deviations from python-pptx kept to reach 0 warnings: `teal` is `#217B70`
(text contrast; the pie and line series use it too, python-pptx has `#2A9D8F`), KPI numbers shrink to the card width
(27 pt on 4 cards, 47 on 3; python-pptx 34 / 54), `top.bar` 0.10 in (python-pptx 0.12), cards start at 2.22 in (2.0).
Not stated: KPI divider rule, exact table row height (section 4).

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

## 3. Decisions that needed CSS or `@html` (all native now)

| Decision | First port (css / `@html`) | Native form in the current deck |
|---|---|---|
| Rule under the title | css `h1 { border-bottom }` | `title.rule=secondary` |
| KPI card top stripe | css `.kpi { border-top }` | `kpi.stripe=secondary` |
| KPI label 20 bold navy / note 20 bold teal | 2 css rules | `kpi.label="20 bold primary" kpi.note="20 bold teal"` |
| KPI card height 4.4 in | row tokens | `kpi.h=4.4in` |
| KPI rows | `{.kpi}` on every box | `@kpi` under the title |
| Pin box heading 20 / text 22 (auto-growth gives 27/26) | css font-size rules | `sizes: heading=20! body=22!` |
| Box heading centred bold | css `.box > h2` | `heading=center` (bold is the default) |
| Slide 9 KPI value 54 / slide 10 heading 26 text 24 | per-slide css fences | `sizes: kpi=54` / `sizes: heading=26! body=24!` inside the slide |
| Conclusion 24 bold | css `.conclusion` | `conclusion="24 bold"` |
| Numbered rows (slide 8) | `@html` (434 tokens) | `@rows` (+ 4 `N.` lines) |
| Cover: full navy, amber rule at 61%, teal bar, light-blue subtitle | `@html` (218 tokens) | `cover.band_h=61% cover.rule=accent cover.bar=teal` + `@cover bg=primary dark` + `style: subtitle.color=#D6E2F0` in the slide |
| Footer + number on an `@html` slide | typed by hand | `footer:` / `num:` (no `@html` slide left); `layout.html_footer=on` otherwise |

## 4. Decisions I could NOT state (first port) and where they stand now

| Decision | Status now |
|---|---|
| Navy strip across the top of every slide | `top.bar=primary` (design wave 3) |
| Teal "■" bullet glyph | `bullet=■ bullet.color=teal` |
| "STEP 1..4" teal caption, step card text bold centred 24, alternating arrow colours, pentagon heads | `@steps num`, `steps.caption_color=teal`, `steps-card="24 bold center"`, `steps-arrow.fill=primary,secondary`, `render.chevron_shape=pentagon` |
| Chart text 14, gap 80, markers 9, gridline colour, custom colour names in `colors=` | chart options `size=14 gap=80 marker=9`, `render.chart_grid`, names accepted |
| Exact KPI card height 4.4 in | `kpi.h=4.4in` |
| 22 pt spacing between box items | `layout.para_gap` is a ratio (em); an absolute pt value is not stated |
| Divider between KPI value and note | **still missing** (the note sits in the number's text frame) |
| Exact table row height (0.8 / 1.05 in) | **still missing** (rows grow with the free height) |

## 5. Defaults overridden vs kept

Overridden: theme (`none`), every colour and the palette, font family, the type scale, `title.band=none`,
`heading.band=primary`, `card.radius=0`, KPI class (colour, size, stripe, label), table header/zebra/widths/align,
conclusion fill and size, chart line width, per-chart series colours, KPI card height, (no whole slide in `@html` any more).

Kept: grid, gaps, margins and card padding; title/footer/footnote/conclusion placement; `lang: ja` line breaking, CJK
squeeze, orphan control, U+2060 joiners; chart internals (plot placement, axis rules: bar with `labels=on` and 4
categories hides the value axis while python-pptx kept it; pie share labels; label-collision alternation; reversed bar
categories; text sizes); table row growth, bar attach, vertical centring of sparse slides, step arrow height; the
contrast safety net (it changed one of the agent's colours).

## 6. What this proves

SlideMark states the agent's deck frame and per-slide choices in 29.96% of the python-pptx tokens (1,577 vs 5,263)
with no css fence and no `@html`. What remains outside the native vocabulary is in section 4: the KPI divider rule
and an exact table row height (and a colour per bar / a manual per-point label position, which this deck does not use).
