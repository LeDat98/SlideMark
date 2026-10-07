# Porting the python-pptx deck's design decisions to SlideMark (lengthbench t3, 25 slides; DL2 lane D)

Same method as `../../t2/slidemark-ported/REPORT.md`. Source `../python-pptx/build.py`; port `deck.md`
(render `sheet.png`); content-only baseline `../slidemark/deck.md`.

## Build line (verbatim)

```
$ slidemark build deck.md -o /tmp/t3.pptx --png sheet.png
info slide 3 chart-scale: series '営業利益' (max 96) is under 10% of '売上高' (max 1280): ...
design: colors fonts sizes style css footer num; 24/24 slides carry choices
wrote /tmp/t3.pptx: 25 slides 16:9, 6 charts, 4 tables, notes on 3 slides, 0 warnings (checked: fit, overlap, contrast, text size, word breaks)
$ python bench/agent_accept.py bench/lengthbench/t3/accept.json /tmp/t3.pptx
accepted
```

## Tokens (o200k_base)

| File | Tokens | vs python-pptx |
|---|---|---|
| `python-pptx/build.py` | 8,188 | 100% |
| `slidemark/deck.md` (content only) | 2,000 | 24% |
| `slidemark-ported/deck.md` | **2,755** | **33.6%** (header 475; about 755 tokens of per-slide design over the content-only deck) |

## Decisions (62; N = native, C = css only, M = missing)

| Group | Decision (build.py line) | SlideMark line | |
|---|---|---|---|
| Frame | size, fonts, colours (L12-21, L24) | default, `fonts:`, `colors:` incl. `sky` | N x3 |
| Frame | title 28 bold navy (L110) | `sizes: title=28`, `title.color=primary` | N |
| Frame | navy full-width title rule (L111) | `title.rule=primary title.rule_h=3pt` | N |
| Frame | orange 1.6 in segment on that rule (L112) | none | M |
| Frame | message bar fill + stripe, 18 bold (L115-117) | `lead.background=surface lead.border-left="7pt solid secondary" lead.padding=... lead.bold=on` | N |
| Frame | footer text 10 grey left (L121) | `footer: 青葉フーズ株式会社｜2027年度 事業計画`, `footer.color=muted`, `sizes: caption=10` | N |
| Frame | hairline above the footer (L120) | `footer.border-top="1pt solid border"` | N |
| Frame | page number right (L122) | `num: on` | N |
| Frame | notes on 3 slides (L125) | `??? ...` | N |
| Cover | full navy (L133) | `@cover bg=primary dark` | N |
| Cover | two right-hand stripes (L134-135) | none | M |
| Cover | short orange rule above the title (L136) | `cover.rule` is full width under the title; used `cover.band_h=55%` | M |
| Cover | title 48 / subtitle 20 light blue, no footer (L140, L143) | `sizes: cover-title=48 cover-subtitle=20`, `cover.footer=off` | N |
| KPI | white card + border (L163) | `card.fill=bg card.line=border` | N |
| KPI | navy top stripe 0.12 in (L164) | `kpi.stripe=primary kpi.stripe_h=0.12in` | N |
| KPI | label 20 bold grey (L165) | `kpi.label.size=20 kpi.label.bold=on kpi.label.color=muted` | N |
| KPI | value 42 (four-up) | `kpi.size=42` | N |
| KPI | value 60 (three-up, L160) | per-slide css `.kpi { font-size: 60pt }` (`{size=60}` ignored; auto-fit gives 48.9) | C |
| KPI | unit smaller than number (L166-169) | none | M |
| KPI | divider (L172) | none | M |
| KPI | note 22 bold blue (L173) | `kpi.note.size=22 kpi.note.bold=on kpi.note.color=secondary` | N |
| KPI | card height up to 4.4 in (L158) | `layout.kpi_lone_h=0.9 layout.kpi_lone_min_h=0.85` | N |
| Boxes | navy band, centred bold white (L189-191) | `heading.band=primary heading.align=center heading.bold=on`, `sizes: heading=20!` | N |
| Boxes | orange rule under the band (L192) | none | M |
| Boxes | item cards: fill, blue stripe, regular text (L195-197) | `###` makes every item a band; fell back to bullets with `bullet=■ bullet.color=accent` | M |
| Boxes | footnote 14 grey (L199) | `※ ...`, `sizes: footnote=14` | N |
| Steps | arrows alternate navy / blue (L216) | `steps-arrow.fill=primary,secondary` | N |
| Steps | first arrow pentagon (L215) | none | M |
| Steps | card light fill (L220) | `steps-card.fill=surface` | N |
| Steps | card orange top stripe (L221) | css `.steps-card { border-top: 5pt solid #E07B18 }` | C |
| Steps | card text bold navy centred (L222) | `steps-card.size=24 steps-card.bold=on steps-card.align=center` | N |
| Tables | first column wider, rest equal (L243-247) | `widths=3.4:2.9:2.9:2.9` (4.4 / 2.4 for 3 / 5 columns) | N |
| Tables | navy header, white bold (L260) | `table.header.fill=primary table.header.color=#FFFFFF` | N |
| Tables | zebra (L263) | `.zebra`, `table.zebra.fill=surface` | N |
| Tables | first column bold (L264) | `hcol=1` | N |
| Tables | alignment first left, numbers right, rest centre (L270) | `align=lrrr` / `lccc` / `lrrrr` / `lcc` | N |
| Tables | numeric right inset 0.6 in (L272) | none | M |
| Tables | cell margin 0.15 in (L257) | `layout.cell_pad_x=0.15in` | N |
| Tables | thin borders (L277-283) | `table.border` default (the border colour) | N |
| Tables | text 22 for 4 rows or fewer, 20 for 5 rows (L275) | `sizes: table=20`, `size=22` on the table fence | N |
| Tables | row heights 1.5 / 1.15 / 0.95 in (L231) | none | M |
| Tables | conclusion bar navy + orange stripe, 22 bold (L291-293) | `conclusion.fill=primary conclusion.bold=on conclusion.border-left="9pt solid accent"`, `sizes: conclusion=22` | N |
| Rows | light bars (L308) | `@rows`, `rows.fill=surface` | N |
| Rows | alternating navy / blue stripe (L309) | badges alternate (`rows-num.fill=primary,secondary`) | M |
| Rows | orange square glyph (L310) | `@rows` takes no `bullet=` | M |
| Rows | text 28 / 24 (L305) | `{size=28}` / `{size=24}` before `@rows` | N |
| Charts | column gap 80, labels outside, 16, legend bottom, colours (L452) | `gap=80 labels=outside size=16 legend=bottom colors=primary,secondary` | N |
| Charts | data labels bold (L368) | `labels.bold=on` | new |
| Charts | gridline colour, no axis line (L348-349) | `render.chart_grid=border` | N |
| Charts | tick 14 vs category 16 vs labels 16 (L350, L358) | `size=16,14` | new |
| Charts | pie slice colours (L383) | `colors=primary,secondary,sky,accent` | N |
| Charts | pie label = name + value, newline (L373-381) | `labels=outside+name` (also `percent+name`, `value+name`) | new |
| Charts | pie slice white outline (L388) | `slice.line=bg` (`,width`; token `render.chart_pie_line`) | new |
| Charts | pie side panel with stripes in slice colours (L477-487) | `@3:2` + `###` `.kpi` sub-boxes (13 pt labels, no stripes) | M |
| Charts | line colours, width 3, marker 9 (L394-400) | `colors= marker=9`, `render.chart_line_width=3` | N |
| Charts | per-series / per-point label positions (L405-421) | automatic collision rule only | M |
| Charts | axis min / max (L354-356) | `min= max=` | N |
| Charts | bar reversed, axis labels at the bottom, max 50 (L537-541) | automatic + `max=50` | N |
| Charts | stacked, labels centred white, gap 70 (L363-426) | `stacked-column {labels=center gap=70}` | N |
| Charts | stacked without totals (no totals in python-pptx) | `totals=off` | new |
| Charts | number formats (`#,##0`, `0.0`, `0"%"`) (L169, L369) | `fmt=` | N |

Count: 41 N, 5 new (data labels bold, size pair, pie name + value, slice outline, `totals=off`), 2 C, 14 M (lane E, DL2 chart decisions).

## Deviations accepted for 0 warnings

- Boxes on slides 4, 10 and 19 are bullets in a banded card, not item cards.
- Rows are numbered badges, not orange glyphs with alternating stripes.
- Cover rule is full width under the title; there are no right-hand stripes.
- The pie panel labels are 13 pt and have no slice-coloured stripes.
- Stacked columns show totals (`totals=off` is accepted now).
- Three-up KPI values are 48.9 pt (60 pt does not fit).
- Steps text is 24 pt on every slide (26 pt for three steps in the original).
- Table row heights are automatic, with no right inset.

## Proposed syntax for the missing items

`@4 items` · `heading.rule=accent` · `@rows plain` · `rows.glyph=■` · `rows.stripe=primary,secondary` ·
`cover.stripes=#1C3A68@8.9in,secondary@10.2in` · `cover.rule_w=1.6in cover.rule_pos=above` · `title.rule2=accent
title.rule2_w=1.6in` · `kpi.unit.size=22` · `kpi.rule=border` · `labels.bold=on` · `labels=outside+name` ·
`slice.line=bg` · `size=16,14` · `table.num_pad=0.6in` · `table.row_h=1.15in` · `labels.pos=タイ:above,北米:below` ·
accept `totals=off` as documented · `render.chevron_shape=pentagon,chevron`

## Silent failures found

- `kpi.fill=bg kpi.line=border` accepted and ignored (use `card.fill=bg`).
- `{.kpi size=60}` ignored; a slide css `.kpi { font-size: 60pt }` works.
- `item.font_size`, `item.bold`, `item.valign` on a `###` sub-box are ignored.
- `totals=off` is documented but rejected with `bad-chart-option` (fixed by lane E: parsed, no carrier series is drawn).
- `heading.border-bottom` hits every heading level.
- `kpi.stripe_h=0.7in` with a white label gives a false `contrast` warning (lint reads the label against the card fill).
