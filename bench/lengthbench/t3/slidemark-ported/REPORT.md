# Porting the python-pptx deck's design decisions to SlideMark (lengthbench t3, 25 slides; DL2 lanes D, E, F and G)

Same method as `../../t2/slidemark-ported/REPORT.md`. Source `../python-pptx/build.py`; port `deck.md`
(render `sheet.png`); content-only baseline `../slidemark/deck.md`.

## Build line (verbatim)

```
$ slidemark build deck.md -o /tmp/t3.pptx --png sheet.png
info slide 3 chart-scale: series '営業利益' (max 96) is under 10% of '売上高' (max 1280): ...
design: colors fonts sizes style footer num; 24/24 slides carry choices
wrote /tmp/t3.pptx: 25 slides 16:9, 6 charts, 4 tables, notes on 3 slides, 0 warnings (checked: fit, overlap, contrast, text size, word breaks)
$ python bench/agent_accept.py bench/lengthbench/t3/accept.json /tmp/t3.pptx
accepted
```

## Tokens (o200k_base)

| File | Tokens | vs python-pptx |
|---|---|---|
| `python-pptx/build.py` | 8,188 | 100% |
| `slidemark/deck.md` (content only) | 2,000 | 24% |
| `slidemark-ported/deck.md` before lane F (lane D port) | 2,755 | 33.6% (header 475) |
| `slidemark-ported/deck.md` after lane F (box, row, cover and chart forms; css fence only for the 60 pt KPI value) | 2,889 | 35.3% (header 559; about 890 tokens of per-slide design over the content-only deck) |
| `slidemark-ported/deck.md` after lane G (no css fence; `kpi.unit.size`, `kpi.rule`, `rowh=`, `@kpi`, integer widths, text-look shorthand, no restated default) | **2,622** | **32.0%** (header 394; about 620 tokens of design over the 1,930-token content) |

## Decisions (63, the "N x3" row counted three times; N = native, C = css only, M = missing)

| Group | Decision (build.py line) | SlideMark line | |
|---|---|---|---|
| Frame | size, fonts, colours (L12-21, L24) | default, `fonts:`, `colors:` incl. `sky` | N x3 |
| Frame | title 28 bold navy (L110) | `sizes: title=28`, `title.color=primary` | N |
| Frame | navy full-width title rule (L111) | `title.rule=primary title.rule_h=3pt` | N |
| Frame | orange 1.6 in segment on that rule (L112) | `title.rule2=accent title.rule2_w=1.6in` | N |
| Frame | message bar fill + stripe, 18 bold (L115-117) | `lead.background=surface lead.border-left="7pt solid secondary" lead.padding=... lead.bold=on` | N |
| Frame | footer text 10 grey left (L121) | `footer: 青葉フーズ株式会社｜2027年度 事業計画`, `footer.color=muted`, `sizes: caption=10` | N |
| Frame | hairline above the footer (L120) | `footer.border-top="1pt solid border"` | N |
| Frame | page number right (L122) | `num: on` | N |
| Frame | notes on 3 slides (L125) | `??? ...` | N |
| Cover | full navy (L133) | `@cover bg=primary dark` | N |
| Cover | two right-hand stripes (L134-135) | `cover.stripes=#1C3A68@8.9in,secondary@10.2in` | N |
| Cover | short orange rule above the title (L136) | `cover.rule=accent cover.rule_w=1.6in cover.rule_pos=above`, `cover.band_h=55%` | N |
| Cover | title 48 / subtitle 20 light blue, no footer (L140, L143) | `sizes: cover-title=48 cover-subtitle=20`, `cover.footer=off` | N |
| KPI | white card + border (L163) | `card.fill=bg card.line=border` | N |
| KPI | navy top stripe 0.12 in (L164) | `kpi.stripe=primary kpi.stripe_h=0.12in` | N |
| KPI | label 20 bold grey (L165) | `kpi.label="20 bold muted"` | N |
| KPI | value 42 (four-up) | `sizes: kpi=42` (42 on slide 14; 34 on slide 2, whose lead leaves less width) | N |
| KPI | value 60 (three-up, L160) | `sizes: kpi=60` inside the slide (60 pt reached: the unit is measured at its own size) | N |
| KPI | unit smaller than number (L166-169) | `kpi.unit.size=22`, `style: kpi.unit.size=32` inside the three-up slides (lane G) | N |
| KPI | divider (L172) | `kpi.rule=border kpi.rule_w=60%` (lane C) | N |
| KPI | note 22 bold blue (L173) | `kpi.note="22 bold secondary"` | N |
| KPI | card height up to 4.4 in (L158) | `kpi.h=4.4in` | N |
| Boxes | navy band, centred bold white (L189-191) | `heading.band=primary heading.align=center heading.bold=on`, `sizes: heading=20!` | N |
| Boxes | orange rule under the band (L192) | `heading.rule=accent heading.rule_h=0.06in` | N |
| Boxes | item cards: fill, blue stripe, regular text (L195-197) | `@4 items` / `@3 items`, `item.fill=surface item.line=surface item.border-left="7pt solid secondary"` | N |
| Boxes | footnote 14 grey (L199) | `※ ...`, `sizes: footnote=14` | N |
| Steps | arrows alternate navy / blue (L216) | `steps-arrow.fill=primary,secondary` | N |
| Steps | first arrow pentagon (L215) | `render.chevron_shape=pentagon,chevron` | N |
| Steps | card light fill (L220) | `steps-card.fill=surface` | N |
| Steps | card orange top stripe (L221) | `steps-card.border-top="5pt solid accent"` (a class token; was css) | N |
| Steps | card text bold navy centred (L222) | `steps-card.size=24 steps-card.bold=on steps-card.align=center` | N |
| Tables | first column wider, rest equal (L243-247) | `widths=7:6:6:6`, `8:7:7`; the 5-column table is equal columns (default) | N |
| Tables | navy header, white bold (L260) | `table.header.fill=primary table.header.color=#FFFFFF` | N |
| Tables | zebra (L263) | `.zebra`, `table.zebra.fill=surface` | N |
| Tables | first column bold (L264) | `hcol=1` | N |
| Tables | alignment first left, numbers right, rest centre (L270) | `align=lrrr` / `lccc` / `lrrrr` / `lcc` | N |
| Tables | numeric right inset 0.6 in (L272) | `table.num_pad=0.6in` | N |
| Tables | cell margin 0.15 in (L257) | `layout.cell_pad_x=0.15in` | N |
| Tables | thin borders (L277-283) | `table.border` default (the border colour) | N |
| Tables | text 22 for 4 rows or fewer, 20 for 5 rows (L275) | `sizes: table=20`, `size=22` on the table fence | N |
| Tables | row heights 1.5 / 1.15 / 0.95 in (L231) | `rowh=0.86in`, `0.95in`, `1.5in`, `1.15in` per table (python-pptx shrinks 0.95 to 0.86 under the conclusion bar) | N |
| Tables | conclusion bar navy + orange stripe, 22 bold (L291-293) | `conclusion.fill=primary conclusion.bold=on conclusion.border-left="9pt solid accent"`, `sizes: conclusion=22` | N |
| Rows | light bars (L308) | `@rows`, `rows.fill=surface` | N |
| Rows | alternating navy / blue stripe (L309) | `@rows plain`, `rows.stripe=primary,secondary` | N |
| Rows | orange square glyph (L310) | `@rows plain` takes `bullet=■ bullet.color=accent` as the glyph (or `rows.glyph=`) | N |
| Rows | text 28 / 24 (L305) | `{size=28}` / `{size=24}` before `@rows` | N |
| Charts | column gap 80, labels outside, 16, legend bottom, colours (L452) | `gap=80 labels=outside size=16` (legend bottom and the two palette colours are the defaults) | N |
| Charts | data labels bold (L368) | `labels.bold=on` | N |
| Charts | gridline colour, no axis line (L348-349) | `render.chart_grid` is `border` by default | N |
| Charts | tick 14 vs category 16 vs labels 16 (L350, L358) | `size=16` (the tick size `size=16,14` is statable, not stated) | N |
| Charts | pie slice colours (L383) | `palette=primary,secondary,sky,accent` (the deck palette) | N |
| Charts | pie label = name + value, newline (L373-381) | `labels=outside+name` (also `percent+name`, `value+name`) | N |
| Charts | pie slice white outline (L388) | `slice.line=bg` is the default (`slice.line=bg,2` sets the width) | N |
| Charts | pie side panel with stripes in slice colours (L477-487) | `@3:2` + `###` `.kpi` sub-boxes (13 pt labels, no stripes) | M |
| Charts | line colours, width 3, marker 9 (L394-400) | `colors= marker=9`, `render.chart_line_width=3` | N |
| Charts | per-series / per-point label positions (L405-421) | `labels=above,below,...` is one word per category for every series: no per-series position, automatic collision rule only | M |
| Charts | axis min / max (L354-356) | `min= max=` | N |
| Charts | bar reversed, axis labels at the bottom, max 50 (L537-541) | automatic + `max=50` | N |
| Charts | stacked, labels centred white, gap 70 (L363-426) | `stacked-column {labels=center gap=70}` | N |
| Charts | stacked without totals (no totals in python-pptx) | `totals=off` | N |
| Charts | number formats (`#,##0`, `0.0`, `0"%"`) (L169, L369) | `fmt=` | N |

Count: **61 N, 0 C, 2 M** = 96.8% statable, all native (lane F port: 57 N, 1 C, 5 M = 92%; lane D port: 47 N, 2 C, 14 M). The 2 missing: the pie side
panel with slice-coloured stripes, and a label position per series (the deck keeps the collision rule).
The token share is the open gate: 32.0%, 166 tokens over the 30% line (see "Why 32%").

## Deviations accepted for 0 warnings

- Item cards fill their box (a `1xN` grid), the original used fixed cards 1.2 in apart; item text is body size (20 pt, shrunk to fit), not 17 / 20 by box count.
- The numbered badge and glyph of `@rows plain` are native shapes; the original square glyph is the character `■` at 0.7 x the text size.
- The cover title block is bottom-anchored in the 55% band (the original centres it on 3.5 in).
- The pie panel labels are 13 pt and have no slice-coloured stripes.
- Four-up KPI values are 42 pt on slide 14 and 34 pt on slide 2 (python-pptx 42 on both).
- Steps text is 24 pt on every slide (26 pt for three steps in the original).
- Not stated, to save tokens: `kpi.stripe_h=0.12in` (6 pt), `title.rule_h=3pt` (2 pt), `heading.rule_h=0.06in`, `cover.rule_h=0.07in`,
  `render.chart_line_width=3`, `layout.cell_pad_x=0.15in`, the value-axis tick size 14 (`size=16,14`), `item.line=surface`.
- Data label colours match the series colour in the original line chart; here they follow the label ink (`labels.color` is one colour).

## What the lane F port changed

Fences and fallbacks that went away: the css fence for `.steps-card` (a class token now), the bullets-in-a-band fallback for item
cards (`@items`), numbered row badges (`@rows plain` + glyph + stripe). New tokens added to the header (`item.*`, `heading.rule*`,
`title.rule2*`, `cover.stripes`, `cover.rule_w`, `cover.rule_pos`, `rows.stripe`, `table.num_pad`, `render.chevron_shape`) and the
chart forms of lane E on six charts (`labels.bold`, `size=16,14`, `labels=outside+name`, `slice.line`, `totals=off`: 43 tokens)
raise the header from 475 to 559 tokens: 2,755 -> 2,889 tokens (33.6% -> 35.3%); lane F alone is 2,846 (+91, 34.8%). The gain is in
coverage (19 -> 5 missing, 2 -> 1 CSS-only), not in size.

## Silent failures found

- `kpi.fill=bg kpi.line=border` accepted and ignored (fixed in lane F: aliases of the card look for `.kpi`).
- `{.kpi size=60}` ignored; a slide css `.kpi { font-size: 60pt }` works.
- `item.font_size`, `item.bold`, `item.valign` on a `###` sub-box were ignored (fixed: sub-boxes of class `item` are item cards).
- `totals=off` was documented but rejected with `bad-chart-option` (fixed by lane E).
- `heading.border-bottom` hits every heading level (use `heading.rule`).
- `kpi.stripe_h=0.7in` with a white label gave a false `contrast` warning (fixed: judged against the stripe).
- Four `cover.* has no effect here` warnings on this deck (the `honour.py` cover test read `h2 {}` as a cover rule; fixed).

## What the lane G port changed

The css fence is gone (`.kpi { font-size: 60pt }` became `sizes: kpi=60` inside the two three-up slides); the KPI unit, the divider and the exact
row heights are native; every `{.kpi}` became one `@kpi` line; the header uses the text-look shorthand (`kpi.label="20 bold muted"`,
`steps-card="24 bold center"`, `conclusion="22 bold"`, `lead="bold primary"`), `fonts: font=`, border shorthands without the default
`solid`, integer `widths=`; tokens found to restate a default were removed by deleting each word in turn and diffing the .pptx XML of
all 25 slides (`bg=#FFFFFF`, `ink=`, `card.line=border`, `kpi.color=primary`, `footer.color=muted`, `title.band=none`,
`title.rule2_w=1.6in`, `conclusion.fill=primary`, `cover.band=none`, `rows.fill=surface`, per-chart `colors=` equal to the palette,
`legend=bottom|none`, `min=0`, `align=` on all-numeric tables, `labels.bold=on` and `slice.line=bg` on the pie).

## Why 32%

The deck has 1,930 tokens of content (the content-only deck: 1,924). The gate leaves 526 tokens for 62 decisions; the ported deck
spends about 620. The header is 394 tokens: 12 colours and fonts, 14 sizes, and 80 style words, each already the shortest form
(`lead="bold primary"` is 5 tokens, `cover.stripes=#1C3A68@8.9in,secondary@10.2in` 21). Per slide: five chart option lists
(`labels.bold=on size=16 ...`, 20-30 tokens each), four table option lists with `widths=` and `rowh=` (30-36), two KPI slides with
two style lines. The cost that does not come from decisions the agent could omit is repetition: `labels.bold=on` x5, `hcol=1 .zebra` x4,
`size=16` x5. A deck-wide default for those (not built: out of lane G's scope) would save about 60 tokens; closing the other 106
means dropping stated decisions, which this port did not do.
- `sizes: kpi=NN` was documented (SYNTAX.md, DESIGN_COVERAGE.md) but never read: it reached `theme.sizes` and no layout code (fixed in lane G: it sets the KPI number size, `kpi.size=` still wins).
- The width estimate of a KPI value counted its unit at the digit size, so `sizes: kpi=60` was shrunk to 49 pt (fixed in lane G: the unit is measured at `kpi.unit.size`).
