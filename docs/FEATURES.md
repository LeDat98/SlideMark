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
| Design feedback (design wave 3): `design-none` / `design-slide` warnings (`src/slidemark/design.py`, table-driven choice detection, `check --fix` leaves them) + `design: colors fonts style footer; 12/15 slides carry choices` build line | x | x | x | - | - | - | x | - |
| Design coverage (wave 3, `docs/DESIGN_COVERAGE.md`): chrome tokens `top.bar` / `bottom.bar` / `title.rule` / `kpi.stripe`, `bullet=` + `bullet.color=`, element tokens `lead.*` `conclusion.*` `footnote.*` `footer.*` `kpi.label.*` `kpi.note.*` routed to CSS, `sizes: x=20!` pins a size, `sizes: conclusion=` | x | x | x | x | x | x | - | - |
| AC7 build feedback (`src/slidemark/fit.py`, `honour.py`): one fit line per slide in the `build` output (form used, text size asked->reached, free space, which attributes took / were ignored; `--quiet` / `fit: off`), `attr-ignored` warning from a (kind, attribute) table checked cell by cell against the renderer, `style:` tokens without their element, `h=` / `y=` of a lone KPI row honoured from the first card | x | x | x | x | - | - | x | - |
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
