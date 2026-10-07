# Design coverage: every decision of the python-pptx deck, stated in SlideMark

Reference: `bench/lengthbench/t2/python-pptx/build.py` (an agent's 15-slide deck). Rule from
`docs/DESIGN_REQUIRED.md`: every value the agent decided with python-pptx must be statable in SlideMark in the
shortest unambiguous form, as a token (`style:` / `colors:` / `sizes:`), an attribute (`{key=value}`) or a
fence option, never a theme-specific code path. Status: **covered** (before this wave), **new** (added in design
wave 3, lane 2), **CSS only** (statable, but only with a ` ```css ` fence; none left), **missing** (not statable; reason given).

Tests: `tests/test_design_coverage.py` (parser, render, importer, bad values). Syntax: `docs/SYNTAX.md`.

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
| Legend position / size | L182-184, L312-313 | `legend=bottom`, `render.chart_legend_scale` | covered |
| Chart text 14, axis 13 | L177, L214 | `size=14` (one size; axis and labels follow it) | new |
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

Rows listed: 66. **covered 38**, **new 24** (21 from design wave 3, 3 more in DL2 part 1: `kpi.h`, `@kpi`, the cover
subtitle colour; the KPI label / note, per-slide pins and column emphasis moved from CSS only to a native form),
**CSS only 0**, **missing 4** (KPI divider rule, exact table row height, a colour per bar of one series, a manual
per-point label position).

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
