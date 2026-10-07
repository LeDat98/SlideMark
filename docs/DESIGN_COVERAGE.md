# Design coverage: every decision of the python-pptx deck, stated in SlideMark

Reference: `bench/lengthbench/t2/python-pptx/build.py` (an agent's 15-slide deck). Rule from
`docs/DESIGN_REQUIRED.md`: every value the agent decided with python-pptx must be statable in SlideMark in the
shortest unambiguous form, as a token (`style:` / `colors:` / `sizes:`), an attribute (`{key=value}`) or a
fence option, never a theme-specific code path. Status: **covered** (before this wave), **new** (added in design
wave 3, lane 2), **CSS only** (statable, but only with a ` ```css ` fence; none left), **missing** (not statable; reason given).

Tests: `tests/test_design_coverage.py` (parser, render, importer, bad values). Syntax: `docs/SYNTAX.md`.

## DL2 on all three deck lengths (measured 2026-10-07)

Each agent's python-pptx deck ported to `deck.md` with the wave-3 forms (`bench/lengthbench/t*/slidemark-ported`);
every build 0 warnings and `agent_accept` accepted. N = token or attribute, C = css fence only, M = missing.

| Deck | Decisions | N | C | M | Statable (N+C) | Native only | deck.md tokens vs build.py | Content-only deck |
|---|---|---|---|---|---|---|---|---|
| t1, 5 slides | 44 | 42 | 0 | 2 | 95% | 95% | 890 / 3,187 = 27.9% | 460 = 14% |
| t2, 15 slides | 64 | 60 | 0 | 4 | 94% | 94% | 1,577 / 5,263 = 30.0% (DL2 part 1) | 1,261 = 24% |
| t3, 25 slides | 62 | 56 | 1 | 5 | 92% | 90% | 2,889 / 8,188 = 35.3% | 2,000 = 24% |

After DL2 lane F (box, row, cover and chrome decisions; t1 and t3 re-ported with the chart forms of lane E too) the 5-slide
deck meets DL2 (>= 95% statable, <= 30% of the tokens); the 25-slide deck is at 92% statable and 35% of the tokens. The 7
missing decisions are lane C's (KPI header band and divider, KPI unit size, exact table row heights, per-point chart
label positions) and the pie side panel with slice-coloured stripes. Token share on t3: the header is 559 tokens (a fixed
cost: 385 on t1), the 25 slides pay 2,330 for content (2,000) and per-slide choices; `@items` / `@rows plain` / chart
forms replaced a css fence and 14 deviations but add header tokens (`item.*`, `rows.stripe`, `cover.stripes`, ...).

## Slide frame

| Decision | python-pptx | SlideMark form | Status |
|---|---|---|---|
| Slide size 13.333 x 7.5 in | L24-25 | default `size: 16:9` | covered |
| Fonts (latin + ea + cs) | L11, L31-43 | `fonts: font="Yu Gothic"` (heading + body + ea; or each role) | covered |
| Named colours, series palette | L12-21 | `colors: primary=#142B4D ...`, `style: palette=...` | covered |
| Top strip, full width, 0.12 in | L91 | `style: top.bar=primary top.bar_h=0.12in` (also `bottom.bar`) | new |
| Title size 28 bold navy | L92 | `sizes: title=28`, `style: title.color=primary` | covered |
| Rule under the title | L93 | `style: title.rule=secondary title.rule_h=2pt` | new |
| Message line 18 bold blue | L95 | `> message` + `sizes: lead=18`, `style: lead.color=secondary lead.bold=on` | covered (`lead.bold` was silently dropped: routing fixed) |
| Footer text 10 grey | L96 | `footer: text`, `style: footer.color=muted`, `sizes: caption=10` | covered (`footer.*` new) |
| Page number right | L97 | `num: on` | covered |
| Speaker notes | L101 | `??? text` | covered |
| Pin a size against auto-growth | explicit sizes everywhere | `sizes: heading=20!`; per slide the same line inside the slide (`sizes: heading=26! body=24!`) | new (per slide: DL2) |
| Deck footer on an `@html` slide | n/a (all hand-placed) | `style: layout.html_footer=on` | new |

## Cards (boxes)

| Decision | python-pptx | SlideMark form | Status |
|---|---|---|---|
| Fill + border | L138 | `card.fill`, `card.line`, `card.border-width` (`surface` / `border` colours) | covered |
| Square corners | `MSO_SHAPE.RECTANGLE` | `style: card.radius=0` | covered |
| Header band, centred bold white text | L139-140 | `style: heading.band=primary heading=center` (bold is the default; `heading="center bold"` states it) | covered |
| Bullet glyph and colour | L149-150 | `style: bullet=■ bullet.color=teal` | new |
| Body / heading size | L134-135 | `sizes: body=22 heading=20` (`20!` pins) | covered / new |
| Vertical anchor top | default | `style: card.valign=top` | covered |
| Space between items 22 pt | L147 | `style: layout.para_gap=1` (em, ratio of the text size) | covered (ratio, not pt) |
| Footnote 13 grey | L155 | `※ text`, `sizes: footnote=13` | covered |
| Conclusion bar (fill, 24 bold white) | L305-306 | `> text`, `style: conclusion.fill=secondary conclusion="24 bold"` (or `sizes: conclusion=24`) | covered (`conclusion.*` routing fixed, `sizes: conclusion` new) |

## KPI cards

| Decision | python-pptx | SlideMark form | Status |
|---|---|---|---|
| Card fill + border | L114 | `.kpi` card = `card` class | covered |
| Top colour stripe | L115 | `style: kpi.stripe=secondary kpi.stripe_h=6pt` | new |
| Label 20 bold navy | L116 | `style: kpi.label="20 bold primary"` (long form `kpi.label.size=20 ...`) | new (was CSS only) |
| Value 34 / 54 pt | L118 | `sizes: kpi=34`, per slide `sizes: kpi=54` inside the slide (auto-fit to the card) | covered |
| Divider rule between value and note | L121 | none: the rule needs the caption's position inside the number's text frame | missing |
| Note / delta 20 bold teal | L122 | `style: kpi.note="20 bold teal"` | new (was CSS only) |
| Card height 4.4 in | L110 | `style: kpi.h=4.4in` (a lone row); `{h=4.4in}` on one card | new (DL2) |
| One card in another colour | n/a | `## A {.kpi fill=accent}` | covered |
| Every box of the slide is a KPI card | `kpi_slide` | `@kpi` (instead of `{.kpi}` on each `##`) | new (DL2) |

## Process rows

| Decision | python-pptx | SlideMark form | Status |
|---|---|---|---|
| Arrow row with a card under each | L167-171 | `@4 steps` | covered |
| Pentagon instead of chevron | L167 | `style: render.chevron_shape=pentagon` | new |
| Alternating navy / blue arrows | L167 | `style: steps-arrow.fill=primary,secondary` (cycles) or CSS `.steps-arrow:nth-child(even)` | new |
| Card text 24 bold centred | L170 | `style: steps-card="24 bold center"` | covered |
| "STEP n" caption | L172 | `@4 steps num`, or `style: steps.caption="STEP {n}" steps.caption_color=teal` | new |

## Tables

| Decision | python-pptx | SlideMark form | Status |
|---|---|---|---|
| Column widths | L273-275 | `{widths=3.9:2.8:2.8:2.6}` | covered |
| Row height 0.8 / 1.05 in | L267, L277 | automatic (rows grow with the free height, `layout.table_*` tokens); an exact pin is not statable | missing |
| Header fill / colour | L284, L292 | `style: table.header.fill=primary table.header.color=#FFFFFF` | covered |
| Zebra | L286 | `{.zebra}`, `table.zebra.fill=surface` | covered |
| Bold first column | L292 | `{hcol=1}` | covered |
| Cell alignment | L289 | `{align=llll}` (numbers right-align automatically) | covered |
| Cell padding 0.15 in | L281 | `style: layout.cell_pad_x=0.15in layout.cell_pad_y=0.05in` or `td.padding=` | covered |
| Text size 20 | L292 | `sizes: table=20` | covered |
| One cell / row / column fill or colour | n/a | rows: `{hl=a,b}` + `table.hl.*`; columns: `{hlcol=2027計画}` (header text or number, same look tokens); run colour `[+11%]{.danger}` | covered / new (columns: was CSS only) |

## Charts

| Decision | python-pptx | SlideMark form | Status |
|---|---|---|---|
| Series colours | L219 | `colors=secondary,accent` (theme names, names from `colors:`, hex) | covered (declared names were rejected: fixed) |
| Gap width 80 | L209 | `gap=80` | new (was `gap_width=`, undocumented) |
| Label position outside / above / below / inside | L210, L355, L318 | `labels=outside` `inside` `center` `above` `below` `left` `right` `best` | new |
| Label size / number format | L205, L203 | `fmt=#,##0`, `size=14`, `render.chart_label_scale` | covered |
| Legend position / size | L182-184, L312-313; t1 L160-162 | `legend=bottom`, `legend.size=14` (`render.chart_legend_scale` for a deck) | new (`legend.size`) |
| Chart text 14, axis 13 | L177, L214; t1 L181, L186; t3 L350, L358 | `size=14` (one size: labels, axes, title base), `size=16,14` = data labels exactly 16 and value-axis numbers 14 | new |
| Data labels bold / a label colour | t1 L173; t3 L368 | `labels.bold=on`, `labels.color=primary` (`off` unbolds a pie) | new |
| Series overlap -5 | t1 L165 | `overlap=-5` (clustered bar / column) | new |
| Value-axis major unit 200 | t1 L180 | `step=200` (implies the axis is shown; the max rounds onto a gridline) | new |
| Stacked chart without totals | t3 (python-pptx draws none) | `totals=off` (was documented but a `bad-chart-option`) | new |
| Pie label = name + value, newline | t3 L373-381 | `labels=outside+name`, `percent+name`, `value+name` | new |
| Pie slice outline colour / width | t3 L388 | `slice.line=bg,2` or `style: render.chart_pie_line=bg render.chart_pie_line_width=2` | new |
| Gridline colour | L213, L366 | `style: render.chart_grid=border` | new |
| Line width 3.5 | L359 | `style: render.chart_line_width=3.5` | covered |
| Marker size 9 | L363 | `marker=9` | new |
| Per-point colours on a pie | L319-322 | `colors=a,b,c,d` (one per slice) | covered |
| Per-point colours on a one-series bar | n/a | `hl=` (one emphasised point); a colour per bar is not statable | missing |
| Per-point label position | L370-371 | automatic collision rule (`render.chart_collide_em`); a manual per-point position is not statable | missing |
| Emphasise a series or a category | n/a | `hl=営業利益` (series wins) or `hl=2027計画`; no match = `chart-hl` warning | new (series) |
| Pie labels white bold inside | L316-318 | default (`render.chart_pie_label_*`) | covered |
| Reversed bar categories, no value-axis line | L403, L215 | automatic | covered |

## Cover and numbered rows

| Decision | python-pptx | SlideMark form | Status |
|---|---|---|---|
| Full-bleed fill | L226 | `@cover bg=primary dark` | covered |
| Light-blue subtitle on the dark cover | L231 | `style: subtitle.color=#D6E2F0` on the cover slide (a deck-level rule yields to a slide `bg=`) | new (DL2) |
| Horizontal rule at 61% | L227 | `style: cover.band_h=61% cover.rule=accent cover.rule_h=0.06in` (full width over a `bg=`) | new (was ignored over `bg=`) |
| Vertical bar left of the title | L228 | `style: cover.bar=teal cover.bar_w=0.12in` | new |
| No band although `title.band` is set | n/a | `style: cover.band=none` | new |
| Title 54, subtitle 24 | L229-231 | `sizes: cover-title=54 cover-subtitle=24` | covered |
| Numbered bars with a badge | L328-333 | `@rows` + `1.` list; `rows-num.fill=primary,secondary`, `rows.fill=` | new |

## Summary

Rows listed: 70. **covered 38** (4 of them only after a routing fix: `lead.bold`, `conclusion.*`, `footnote.*`, a
deck-declared colour named like a CSS colour), **new 28** (21 from design wave 3; 6 from the 5- and 25-slide ports, DL2
lane E: chart label weight, size pairs, overlap, step, totals, pie name and outline; DL2 part 1 added `kpi.h`, `@kpi`,
the cover subtitle colour and moved the KPI label / note, per-slide pins and column emphasis from CSS only to a
native form), **CSS only 0**, **missing 4** (KPI divider rule, exact table row height, a colour per bar of one series,
a manual per-point label position).

DL2 part 1 (CSS only -> native): `{hlcol=}` (table columns), slide-scoped `sizes:` / `style:` lines (per-slide pins,
`sizes: kpi=54`, the light cover subtitle), the text shorthand (`kpi.label="20 bold primary"`), `fonts: font=`, `@kpi`,
`kpi.h=4.4in`. The ported deck (`bench/lengthbench/t2/slidemark-ported/deck.md`) uses no css fence and no `@html`.

Silent failures closed in this wave (they looked statable and did nothing):

- `style: lead.bold=on` / `conclusion.bold=on` / `footnote.size=9` created an unused class; they are CSS rules now.
- `.steps-card` and `.steps-arrow:nth-child(even)` selectors matched nothing; both parts of `@steps` are CSS nodes now.
- `colors: teal=#2A9D8F` was shadowed by the CSS colour `teal` in CSS and `style:` values.
- A chart `colors=` with a name declared in `colors:` was a `bad-chart-option`.
- `@cover bg=... dark` switched the composed cover off (a colour-only rule is not a style choice).
- `slide { border-top }` says what to write instead (`top.bar`).

## t1 and t3

Decisions of the 5- and 25-slide decks (`bench/lengthbench/t1|t3/python-pptx/build.py`) that the t2 table above does
not already hold. Ported in `bench/lengthbench/t1|t3/slidemark-ported/deck.md`. Status as above (**covered**, **CSS only**,
**missing**). Line numbers: t1 / t3.

| Decision | python-pptx | SlideMark form | Status |
|---|---|---|---|
| Message bar: light fill, padding | L95 / L115 | `style: lead.background=surface lead.padding="5pt 12pt"` | covered |
| Message bar: accent stripe at its left | L96 / L116 | `style: lead.border-left="7pt solid accent"` | covered |
| Footer hairline above the footer text | n/a / L120 | `style: footer.border-top="1pt solid border"` | covered |
| Cards white with a border (KPI and boxes) | L140 / L163 | `style: card.fill=bg card.line=border`; `kpi.fill=` / `kpi.line=` are aliases for `.kpi` cards only | covered / new (the alias was silently ignored) |
| No footer on the cover | n/a / L130 | `style: cover.footer=off` | covered |
| Second rule segment (orange, 1.6 in) on the title rule | n/a / L112 | `style: title.rule2=accent title.rule2_w=1.6in` | new |
| Cover bar on the slide's left edge, full height | L110 | `style: cover.bar=accent@edge cover.bar_w=0.35in` | new |
| Cover rule short (6 / 1.6 in), above or under the title | L111 / L136 | `style: cover.rule=accent cover.rule_w=6in cover.rule_pos=below|above` | new |
| Cover stripes on the right (two colours, fixed x) | n/a / L134-135 | `style: cover.stripes=#1C3A68@8.9in,secondary@10.2in` | new |
| KPI header band (navy, white label) | L141-142 | none: `heading.band` skips `.kpi` | missing |
| KPI unit (億円, 名) smaller than the number | n/a / L166-169 | none: one run size per card | missing |
| KPI value size by cards per row (42 for 4, 60 for 3) | n/a / L160 | slide css `.kpi { font-size: 60pt }` (`{size=}` on the card is ignored) | CSS only |
| Accent stripe on top of a box card | L201 | `style: strat.border-top="6pt solid accent"` with `{.strat}` (a class token; the css fence was never needed) | covered |
| Number circle on a box heading | L202-203 | `@4 num`, `style: box.num.fill=primary box.num.color=bg box.num.size=20` | new |
| Rule under a box heading, or under the band | L205 / L192 | `style: heading.rule=secondary heading.rule_h=0.03in` (not on `###`) | new |
| Items as cards inside a box (fill, left stripe, regular text) | L208-210 / L195-197 | `@4 items` (or `box.items=cards`): `style: item.fill=surface item.border-left="7pt solid secondary" item.size=14 item.bold=off`; `### x {.item}` takes the same tokens | new |
| First arrow a pentagon, the rest chevrons | L221 / L215 | `style: render.chevron_shape=pentagon,chevron` | new |
| Step card stripe (top or left, accent) | L225 / L221 | `style: steps-card.border-left="5pt solid accent"` (or `border-top`) | covered |
| Numeric table column inset 0.6 in at the right | n/a / L272 | `style: table.num_pad=0.6in` (right-aligned cells, header included) | new |
| Unnumbered bar rows with a glyph and alternating stripe | n/a / L308-310 | `@rows plain` + `style: rows.glyph=■ rows.glyph.color=accent rows.stripe=primary,secondary` (`bullet=■` is the glyph too) | new |
| Chart data labels bold | L173 / L368 | `labels.bold=on` | new (lane E) |
| Series overlap (-5, 100) | L165 / L364 | `overlap=-5` (a stacked kind sets 100 itself) | new (lane E) |
| Value axis major unit | L180 | `step=200` | new (lane E) |
| Tick size apart from label and legend size | L181, L186 / L350, L358 | `size=14,12` | new (lane E) |
| Pie label = category name + value, newline separator | n/a / L373-381 | `labels=outside+name` | new (lane E) |
| Pie slice outline (white) | n/a / L388 | `slice.line=bg` | new (lane E) |
| Pie with a side panel of rows with slice-coloured stripes | n/a / L477-487 | `@3:2` + `###` `.kpi` sub-boxes: label 13 pt, no slice stripe | missing |
| Stacked column without totals | n/a / L363-368 | `totals=off` (was documented but rejected) | new (lane E) |

### Summary, t1 and t3

28 rows: **covered 7** (two were listed as CSS only and already worked as class tokens: `strat.border-top`,
`steps-card.border-left`; one gained the `kpi.fill` alias), **new 17** (10 from lane F: second title rule, cover bar on
the edge, short cover rule, cover stripes, number circle, heading rule, item cards, pentagon list, numeric inset, plain
rows with glyph and stripe; 7 from lane E: chart labels, overlap, step, tick size, pie name, pie outline, `totals=off`),
**CSS only 1** (the KPI value size per row, slide css), **missing 3** (KPI header band and KPI unit size: lane C; the pie
side panel with slice-coloured stripes). With the t2 rows above the whole table is 98 rows: covered 45, new 45, CSS
only 1, missing 7 (distinct decisions: KPI header band, KPI divider, KPI unit size, exact table row heights, a colour
per bar, per-point label positions, the pie side panel). Per deck the DL2 counts are in the table at the top of this file.

Silent failures found while porting (they look statable and do nothing):

- `kpi.fill=bg kpi.line=border`: accepted, the KPI card kept `card.fill` (fixed: aliases of the card look for `.kpi`).
- `item.font_size=14 item.bold=off item.valign=middle` on a `### {.item}` sub-box: accepted, no effect (fixed: the sub-box is an item card).
- `{.kpi size=60}` on a KPI heading: accepted, no effect (slide css works).
- `totals=off` on a chart: documented in `docs/SYNTAX.md`, rejected by the parser (fixed by lane E).
- `kpi.stripe_h=0.7in` with a white label: a `contrast` warning, because the lint read the label against the card fill (fixed: judged against the stripe when the label overlaps it; the stripe still is not a header band, see lane C's `kpi.band`).
- Four `cover.* has no effect here` warnings on decks with `kpi.label.*` or `heading.bold=on` (the cover test read `.kpi h2` and `h2 {}` as cover rules; fixed in `honour.py`).
