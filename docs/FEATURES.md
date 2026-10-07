# Feature matrix

Definition of Done steps: D1 docs example · D2 parser test · D3 fuzz-safe · D4 render test · D5 opens in
LibreOffice · D6 gallery looks right · D7 lint rule · D8 bench no regression. Mark `x` when done, `-` when the
step does not apply (no visual risk to lint, or no syntax).

| Feature | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 |
|---|---|---|---|---|---|---|---|---|
| Deck header / front-matter | x | x | x | x | x | x | - | x |
| Slides, cover/section inference | x | x | x | x | x | x | - | x |
| Boxes (`##`), auto arrangement v2 | x | x | x | x | x | x | x | x |
| `@` grid line (N, CxR, ratios, areas), row groups | x | x | x | x | x | x | x | x |
| flow / chevron | x | x | x | x | x | x | x | x |
| lead / conclusion / footnotes | x | x | x | x | x | x | x | x |
| Inline styles, links, slide jumps | x | x | x | x | x | x | - | x |
| Lists (native bullets/numbers), line-per-line text | x | x | x | x | x | x | x | x |
| Images (contain/cover/stretch) | x | x | x | x | x | x | x | x |
| SVG pictures (`![](a.svg)`, ```` ```svg ````): native svgBlip + PNG fallback, sanitized | x | x | x | x | x | x | - | x |
| Video / audio (`![](a.mp4){poster autoplay loop}`) | x | x | x | x | x | x | x | x |
| Tables + merges, CSV table, table options | x | x | x | x | x | x | x | x |
| Charts (10 kinds) + options | x | x | x | x | x | x | - | x |
| Code highlighting | x | x | x | x | x | x | x | x |
| Speaker notes | x | x | x | x | x | - | - | x |
| `@end`, missing-end hint | x | x | x | x | x | x | x | x |
| `.kpi` boxes | x | x | x | x | x | x | x | x |
| Hero KPI (`@2:1:1:1` exact ratios, `{.kpi .hero}`, number scales with card width), KPI rows fill the body | x | x | x | x | x | x | - | x |
| Lead as the slide's message (preset size / ink, `sizes: lead=`) | x | - | - | x | x | x | x | x |
| Callouts `> [!note]` | x | x | x | x | x | x | x | x |
| Badges `[x]{.badge}` | x | x | x | x | x | x | x | x |
| Connectors `@ a>b` | x | x | x | x | x | x | x | x |
| Icons `icon=name` | x | x | x | x | x | x | x | x |
| Box heading band (jp-business) | x | - | - | x | x | x | x | - |
| Math (OMML) | x | x | x | x | x | | - | x |
| Mermaid flowcharts → native | x | x | x | x | x | x | x | x |
| HTML subset → native, image fallback | x | x | x | x | x | | - | x |
| HTML (Chromium-measured) → native shapes, `{render=native\|image}` | x | x | x | x | x | x | - | x |
| Themes default / midnight / jp-business | x | x | - | x | x | x | x | - |
| User templates `.pptx/.potx/.yaml` | x | x | x | x | x | x | - | - |
| Build animations, transitions, sections, hidden | x | x | x | x | x | - | - | x |
| `check` linter + JSON | x | x | x | - | - | - | x | - |
| `docs`, `schema`, `skill install`, JSON input | x | x | x | x | - | - | - | x |
| `check --fix [-o]` mechanical source repairs (`fix.py`) | x | x | x | - | - | - | - | - |
| `.pptx` import (round trip) | x | x | x | x | x | - | - | x |
| `review` design critique (`design-*` rules + score, `--png`) | x | x | x | - | - | - | x | - |
| Design tokens: presets as YAML, `theme: none`, `colors:`/`fonts:`/`sizes:`/`style:` lines, `slidemark tokens` | x | x | x | x | x | x | x | x |
| No hard-coded looks (`layout.*`/`render.*` tokens, DF1 scanner test) | x | - | - | x | x | x | - | x |
| Gradients, CSS shadows, opacity on shapes and cards | x | x | x | x | x | x | x | - |
| ` ```css ` fence: selectors + 34 properties native | x | x | x | x | x | x | x | x |
| `@html` slides, `build deck.html`, shared CSS vars | x | x | x | x | x | x | x | x |
| HTML → native fidelity (`bench/html_fidelity.py`, 30 slides) | x | - | - | x | x | x | x | x |
| One-call `build` (stdin `-`, `--save`, auto-fix, grouped diagnostics, facts + look line, `--png` contact sheet) | x | - | x | x | x | - | - | x |
| Contrast-safe derived ink (text on fills, theme colours as text, dark-brand surface/border) + paste-ready hints | x | - | x | x | x | x | x | - |
| Cover from `# Title` + `## subtitle`; full-width lone table; chevron interior text, no word breaks | x | x | x | x | x | x | x | - |
| Sparse slide completion (KPI rows, short lists, box rows, lone tables grow) | - | - | x | x | x | x | - | - |
| Decimal commas in chart CSV for vi/de/fr…; `※` kept in footnotes | x | x | x | x | x | - | - | - |
| Pie/doughnut per-point label ink | - | - | x | x | x | x | - | - |
| Orphan control (no-break space between the last two short words); `.muted` box = muted band/border, normal body ink | x | x | x | x | x | x | x | - |
| `waterfall` chart (bridge, `=` totals, native stacked columns) | x | x | x | x | x | x | x | - |
| Chart defaults (design wave 2): accent-free preset palettes, pie `labels=on` = share on the wedge, larger legend / labels (`render.chart_legend_scale`, `chart_pie_label_*`), line label collision (`chart_collide_em`), `chart-scale` info line (`chart_scale_ratio`; info, not a warning, so a brief that wants both series on one chart still builds with 0 warnings) | x | x | x | x | x | x | x | - |
| Chart takeaway: `hl=` emphasised points + `note=` callout with pointer (pinned plot area) | x | x | x | x | x | x | x | x |
| Table cell badges as native rounded pills (`layout.table_pills`, `pill` class, importer folds `Pill` back) | x | - | x | x | x | x | x | - |
| `{.gantt}` tables (native bars over period cells, `gantt` class) | x | x | x | x | x | x | x | - |
| Composed covers (`cover.band_h/pad/gap/rule/footer` tokens) | x | - | x | x | x | x | x | - |
| Stacked totals (`totals=`), negative-axis headroom, JP number+unit joiners, JP orphan squeeze | x | x | x | x | x | x | - | - |
| JP phrase-aware line breaks (BudouX soft breaks, render only; importer strips them) | x | x | x | x | x | x | - | - |
| Table row emphasis: `hl=` first-cell values, `table.hl.*` tokens, CSS `tr.hl`, lint, importer round trip (`hl=` in the shape name) | x | x | x | x | x | x | x | - |
| `@steps`: arrow row + outcome cards in the same columns (`steps-arrow` / `steps-card` classes, `layout.steps_*` tokens, importer folds it back) | x | x | x | x | x | x | - | - |
| Sparse slides use the body (design wave 2): short lead + bullets grow (`layout.list_*`), box cards stretch down the slide (`cards_to_body*`, `card_fill_text_max_pt`), `@chevron` with short bodies is built as `@steps` (`chevron_steps*`), a lone table grows its text and rows (`table_free*`) and the conclusion bar attaches to it (`bar_attach*`) | - | x | x | x | x | x | - | - |
| Design feedback, tightened (DL3c): `design-none` names each missing header line of `colors:` `fonts:` `sizes:` `style:`; `design-slide` checks form + emphasis + values per content slide (`@noemph` / `@defaults` opt out; two emphases = `keep one`); `design: colors fonts sizes style footer; 9/14 slides decided form+emphasis+values; short: 4 (values)` build line (`src/slidemark/design.py`, table-driven, `check --fix` leaves them) | x | x | x | - | - | - | x | - |
| Design coverage (wave 3, `docs/DESIGN_COVERAGE.md`): chrome tokens `top.bar` / `bottom.bar` / `title.rule` / `kpi.stripe`, `bullet=` + `bullet.color=`, element tokens `lead.*` `conclusion.*` `footnote.*` `footer.*` `kpi.label.*` `kpi.note.*` routed to CSS, `sizes: x=20!` pins a size, `sizes: conclusion=` | x | x | x | x | x | x | - | - |
| AC7 build feedback (`src/slidemark/fit.py`, `honour.py`): one fit line per slide in the `build` output (form used, text size asked->reached, free space, which attributes took / were ignored; `--quiet` / `fit: off`), `attr-ignored` warning from a (kind, attribute) table checked cell by cell against the renderer, `style:` tokens without their element, `h=` / `y=` of a lone KPI row honoured from the first card | x | x | x | x | - | - | x | - |
| Growth ceiling `layout.grow_max` (1.5, `grow.max=`; one cap for every text growth pass, row / card stretching stays) + `sparse: N% free` fit suffix and `sparse` info (`layout.sparse_note`); `{size=}` on a table is no longer grown | x | x | x | x | - | - | x | - |
| `@rows`: an ordered list alone on the slide as numbered bars (`rows` / `rows-num` classes, `layout.rows*`, importer folds `Row N` back) | x | x | x | x | x | x | x | - |
| `@steps` extras: `num` / `steps.caption` caption line, cyclic `steps-arrow.fill=a,b`, `.steps-card` / `:nth-child` CSS, `render.chevron_shape=pentagon` | x | x | x | x | x | x | - | - |
| Chart options `gap=` `marker=` `size=`, `labels=outside\|inside\|center\|above\|below`, `hl=` names a series, `render.chart_grid`, `colors=` takes names from `colors:` | x | x | x | x | x | x | - | - |
| Chart decisions (DL2 lane E, `tests/test_chart_decisions.py`): `labels.bold=` / `labels.color=`, `size=16,14` (labels, value-axis numbers), `legend.size=`, `overlap=`, `step=`, `totals=off\|on` accepted, pie `labels=outside+name` / `percent+name`, `slice.line=` + `render.chart_pie_line[_width]`; dotted fence keys; importer reads `labels.bold` `overlap` `step` `+name` back; contrast lint judges `labels.color` | x | x | x | x | x | - | x | - |
| DL2 part 2 (`docs/DESIGN_COVERAGE.md`): `kpi.rule=` divider between the KPI number and caption (caption split into its own box, importer folds it back) | x | x | x | x | x | x | - | - |
| Exact table row height `{rowh=0.8in,1.05in}`: pinned rows skip every stretch / growth pass (`tables.pinned`), overflow in a pinned row warns, importer emits `rowh=` | x | x | x | x | x | x | x | - |
| One colour per bar of a one-series column/bar (`colors=` with one entry per category, `hl=` still wins) | x | x | x | x | x | x | - | - |
| Per-point label position `labels=above,below,above,above` on line / column / bar (wrong count warns with the category count) | x | x | x | x | x | x | - | - |
| `h=` `y=` `w=` on `.kpi` cards in a row place the row (`layout/kpirow.py`); the sparse passes leave it where it is | x | x | x | x | x | x | - | - |
| Cover: `cover.bar` / `cover.band=none`, full-bleed rule over a slide `bg=`; `layout.html_footer` draws `footer:` / `num:` on `@html` slides | x | x | x | x | x | x | - | - |
| Design coverage part 1 (DL2): slide-scoped `sizes:` / `style:` lines (that slide only), text shorthand `kpi.label="20 bold primary"` (also `steps-card=` `heading=` `conclusion=` `lead=` `title=`), `fonts: font=`, `@kpi` (every box a KPI card), `kpi.h=4.4in`, table `hlcol=` (column emphasis, importer reads it back) | x | x | x | x | x | x | x | - |
| Item cards (DL2 lane F, `tests/test_design_dl2f.py`): `@4 items` / `box.items=cards` draw a box's bullets as `Item N` cards (`item.fill` `item.line` `item.border-left` `item.size` `item.bold` `item.valign`), `### x {.item}` sub-boxes are the same cards (their `item.*` / `{size=}` were ignored), importer folds cards back to bullets + `items` | x | x | x | x | x | x | x | x |
| Numbered boxes `@4 num` (`Num N` ellipse badge left of the heading, in the band with `heading.band`; `box.num.fill` / `color` / `size`), importer drops the badges and adds `num` | x | x | x | x | x | x | x | x |
| `heading.rule` / `heading.rule_h` (rule under a `##` heading or band, never `###` / KPI / item cards); `title.rule2` / `title.rule2_w` (short second segment on the title rule) | x | x | x | x | x | x | - | - |
| `@rows plain` (unnumbered bars, `Row N glyph` from `rows.glyph` / `bullet=`, `Row N stripe` from `rows.stripe=a,b`, also on numbered rows), importer folds back to `@rows plain` | x | x | x | x | x | x | x | x |
| Cover decoration inside the composed cover: `cover.bar=accent@edge`, `cover.rule_w` + `cover.rule_pos=above\|below`, `cover.stripes=color@x,...` (over `@cover bg= dark`; the title keeps clear of the first stripe) | x | x | x | x | x | x | x | - |
| `render.chevron_shape=pentagon,chevron` (a list per arrow in reading order, last repeats), `table.num_pad=0.6in` (right inset of right-aligned cells), `kpi.fill` / `kpi.line` as card aliases for `.kpi`, lint reads a KPI label on a tall `kpi.stripe` against the stripe colour | x | x | x | x | x | x | x | - |
| DL2 lane G (`tests/test_design_dl2g.py`): `kpi.band=<color>` (`kpi.band.color`, `kpi.band.size`; header band behind the label of every `.kpi` card, importer folds it back) and `kpi.unit.size=22` (`kpi.unit.color`; trailing unit of the value line in its own run size, `Run.size`; importer joins the runs); `sizes: kpi=NN` sets the KPI number size (was a silent no-op) | x | x | x | x | x | x | x | - |
| Element control (DL3, `tests/test_element_control.py`, `tests/test_honour.py`): every kind takes `x y w h size color fill line radius shadow align valign bold italic font opacity pad rotate shape z` (`honour.py` is the table: 16 kinds, 22 keys, each cell probed); `rotate=` turns a box with its heading and children, `shape=` (`src/slidemark/shapes.py`, 59 names, did-you-mean) draws any box / card / text with a fill / code / image / chart frame with a preset geometry, `z=1..9` stacks (`layout.z_default`), `shadow=on\|off\|"x y blur color"` | x | x | x | x | - | - | x | - |
| Pinned `x y w h` are never moved or resized by a layout pass (`Placed.pin`, `engine._restore_pins`); a title / cover title / cover subtitle takes `{x y w h fill line radius shape}`, a lone callout `y`, an `@rows` list a box (`align valign radius rotate z` act on the bars, a row takes its own `fill line`), a chart a frame (`fill line radius shadow pad`, `align` / `valign` in its cell, `bold` / `italic` labels), a picture `size pad align valign fill shape`, a table `pad shadow`, a KPI card `color bold align valign`, a code block `font`, a compact chevron `h align valign pad` | x | x | x | x | - | - | x | - |
| `@free grid`: `x y w h` snap to a 12 x 12 grid, `x=3c w=4c` = column 3, four columns wide (a title pin counts over the slide); list-item attributes `- text {color=danger bold=true}` (kinds `list item` / `row` in `honour.py`); importer writes back `shape=` / `rotate=` / `shadow=` of boxes and pictures | x | x | x | x | - | - | x | - |
| `@iconlist cols=2` (icon + bold title + text in 1-3 columns, `iconlist.icon.size` / `.icon.color` / `.gap`; `Iconlist N` text + native `icon` shapes, importer folds back) | x | x | x | x | x | x | x | x |
| `@quote align=` (large quotation, `quote.size` / `quote.mark` / `quote.mark.color`, attribution `— name`; `Quote text` / `Quote by`, importer folds back) | x | x | x | x | x | x | x | x |
| `@split side= ratio= bleed=on` (image or `fill=` block beside the text side, which the ordinary engine lays out on a virtual slide of its own width; `split.gap`) | x | x | x | x | x | x | x | x |
| `@proscons` / `@pros` (two boxes, `+` / `−` glyph discs in `proscons.plus.color` / `.minus.color`, verdict bar = last `>`; `Proscons k ...` shapes, importer folds back) | x | x | x | x | x | x | x | x |
| `@progress max=` (labelled bars from `- label 72%` or a table; `progress.fill` / `.track` / `.h` / `.label.size`; `Progress N ...` shapes, importer recovers `max=`) | x | x | x | x | x | x | x | x |
| `@harvey` (0-4 or 0/25/50/75/100% as native quarter-filled balls: ellipse + `pie` wedge; `harvey.size` / `.fill` / `.line`; importer rebuilds the table) | x | x | x | x | x | x | x | x |
| `@heatmap min= max= colors= text=` (numeric table, cell fills interpolated, ink picked per cell; `heatmap.colors` / `.text`; the table name carries the scale, importer folds back) | x | x | x | x | x | x | x | x |
| `@pins legend=` (image + `x= y=` pins as numbered circles at exact image positions + legend; `pins.fill` / `.size` / `.legend`; importer rebuilds the list) | x | x | x | x | x | x | x | x |
| Composition vocabulary part 1 (DL3b, `@word` + secondary keys + `<form>.*` tokens, `tests/test_vocabulary.py`): `@timeline dir=h\|v marks=on\|off\|num` (milestones on a line with dots, `{.accent}` = now; `timeline.line` `.dot` `.dot.size` `.now`) | x | x | x | x | x | x | x | - |
| `@vs` (two cards, `vs` badge between, optional `## 結論` verdict bar, `{.hero}` winner; `vs.badge.*` `vs.verdict.*` `vs.win.*`) and `@matrix x= y=` (2x2 of boxes, axis arrows + labels, vertical y label; `matrix.axis.*` `matrix.fill=a,b,c,d`) | x | x | x | x | x | x | x | - |
| `@funnel` / `@pyramid dir=up\|down` (native custom-geometry trapezoid stages, heading inside, body right; `funnel.fill` `.gap` `.taper` `.share`, `pyramid.*`) and `@cycle dir=cw\|ccw` (3-6 nodes on a ring, native `arc` arrows with arrowheads; `cycle.fill` `.arrow` `.node.size`) | x | x | x | x | x | x | x | - |
| `@agenda` (a `1.` list alone as numbered rows, `{.accent}` current, others dimmed; `agenda.num.size` `.num.color` `.num.text` `.rule` `.now` `.dim`) and `@statement align= valign=` (one huge line + caption; `statement.size` `.color` `.sub.*`); importer folds every form back from the shape names (`Timeline 2 now`, `Funnel 1 up`, `Cycle 3 arrow ccw`), `attr-ignored` knows the `stage` / `formtext` kinds, fit lines name the form | x | x | x | x | x | x | x | - |
| Foreign-deck recognition (DL3d lane B, `importer/recognise.py`, `tests/test_import_recognise.py`): number tiles -> `@kpi`, `01 02 03` cards -> number headings, badge bars -> `@rows` / `num`, quote card -> `@quote` + `quote.mark.color`, dark statement panel and big-number bars -> mixed-size spans + `rows.stripe=`; geometry only on decks without SlideMark shape names | x | x | x | x | - | - | - | - |
| Foreign-deck geometry recognition (DL3d lane C, `importer/recognise2.py`, `tests/test_import_recognise2.py`): chevron row + cards + dark bar -> `@steps` + `steps-arrow.fill` + conclusion, tinted table row -> `hl=` + `table.hl.fill`, cell runs -> `[x]{size= color=}` spans + table `size=`, chart `colors=` / `size=` / `gap=` from `c:dPt` and series fills, chart side panel spans, slide-filling rectangle -> `@bg=<c> dark`, cover `bar` / `top_bar` / `bottom_bar`, edge `top.bar` / `bottom.bar`, `title.rule`, hand-drawn page number -> `num: on`; new tokens `cover.top_bar` / `cover.bottom_bar` | x | x | x | x | x | x | - | x |
| Foreign-deck round trip, part 2 (DL3d lane E, `importer/recognise3.py`, `tests/test_import_recognise3.py`): pentagon row whose cards hold text + `STEP n` captions -> `@4 steps num` (+ `steps.caption=` / `_color` / `_size`, `steps-arrow.fill`; sizes left to the layout), centred KPI cards (label, number, rule, delta, top stripe) -> `@kpi` + `kpi.rule` / `kpi.stripe` / `kpi.label.*` / `kpi.note.*` / `kpi.h`, dark header-band cards with `■` bullets -> `heading.band` + `heading.align` + `bullet=`, takeaway bar ending above the footer line -> `conclusion.fill`; one threshold table `TH3`, a group fires only when every card matches | x | x | x | x | x | x | - | - |
| DL3d lane A (`tests/test_dl3d_forms.py`, `examples/25-roundtrip-forms.md`): span attributes `[420億円]{size=28 bold=true color=primary}` / `[x]{size=12 .muted}` (exact pt: `Run.size` + `Run.exact`, never grown / shrunk, a line is as tall as its biggest pinned span, a text holding one is not grown by the sparse passes; paragraphs, list items, `@rows`, table cells with `<br>`, box headings, KPI value lines; importer writes them back, `importer/runs.py`) | x | x | x | x | x | x | x | - |
| DL3d part 2 (lane F, `tests/test_dl3d_part2_forms.py`, `forms3.py`, `layout/stepspin.py`, `importer/shadows.py`): exact `@steps` geometry `steps-arrow.h` `steps-card.h` (pinned: no stretch / growth pass, bar follows the cards) `steps.gap`, `conclusion.h`; quote card `quote.bar` `quote.bar_w` `quote.by.align` `quote.fill` `quote.h` (+ `quote.width`); badge shapes `rows-num.shape` `box.num.shape`; importer writes them from the original's geometry, `card.shadow=` deck-wide (else `{shadow=}` per box, `off` for a card without) | x | x | x | x | x | x | x | - |
| DL3d part 2 (lane I, `tests/test_dl3d_part2_geometry.py`, `layout/boxpin.py`): `box.h` (every `##` box card exact) + `box.anchor=top|center|bottom` (last pass like `stepspin`, children and the note under the cards follow); `steps-arrow.point` (preset `adj`, one depth, also the `@chevron` strip); pinned `@steps` start at the body top; importer: deck `margin=` and `layout.top_gap=` from where the content sits (`recognise2._page_geometry`), `box.h` / `box.anchor` from header-band cards, `steps-arrow.point` from `a:avLst`, plain-table `rowh=` re-checked after `widths=` | x | x | x | x | x | x | x | - |
| Card stripes `box.stripe=a,b,c` `box.stripe_h` `box.stripe.side=top\|left\|right\|bottom`, same for `item.*` and `kpi.*` (list cycles in reading order, `{stripe=teal}` on one card, drawn from the final card rectangle, named `Stripe` / `rule`; importer drops the shape, tokens ride in the design part); `rows.stripe` documented beside them | x | x | x | x | x | x | x | - |
| Number as heading text: `@4 num=text` (`01` above every heading, `box.num.text` `{nn}` / `{n}`), `## 01 {.num}` / `## 2.1兆円 {.num}` (the heading is the number; `box.num.size` exact, `box.num.color=a,b,c` cycles, default = the card's stripe colour); `@kpi tile` / `{.kpi .tile}` (heading = value line, body = caption, left aligned); shapes `Number text` / `Number heading` / `Tile`, importer folds all three back | x | x | x | x | x | x | x | - |
| `cover.bottom.bar=<color>` `cover.bottom.bar_h=0.3in` (band on the cover's bottom edge, composed or plain cover); a box with its own `{fill=}` picks a readable ink for its heading and text (dark statement panel beside a list) | x | x | x | x | x | x | x | - |
