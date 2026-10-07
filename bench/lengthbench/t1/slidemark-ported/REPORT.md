# Porting the python-pptx deck's design decisions to SlideMark (lengthbench t1, 5 slides; DL2 lane D)

Same method as `../../t2/slidemark-ported/REPORT.md`. Source `../python-pptx/build.py`; port `deck.md`
(render `sheet.png`); content-only baseline `../slidemark/deck.md`.

## Build line (verbatim)

```
$ slidemark build deck.md -o /tmp/t1.pptx --png sheet.png
info slide 3 chart-scale: series '営業利益' (max 96) is under 10% of '売上高' (max 1280): ...
design: colors fonts sizes style css num; 4/4 slides carry choices
wrote /tmp/t1.pptx: 5 slides 16:9, 1 chart, notes on 1 slide, 0 warnings (checked: fit, overlap, contrast, text size, word breaks)
$ python bench/agent_accept.py bench/lengthbench/t1/accept.json /tmp/t1.pptx
accepted
```

## Tokens (o200k_base)

| File | Tokens | vs python-pptx |
|---|---|---|
| `python-pptx/build.py` | 3,187 | 100% |
| `slidemark/deck.md` (content only) | 460 | 14% |
| `slidemark-ported/deck.md` | **912** | **28.6%** (header 385) |

## Decisions (44; N = native, C = css only, M = missing)

| # | Decision (build.py line) | SlideMark line | |
|---|---|---|---|
| 1 | 16:9 (L21) | default | N |
| 2 | Yu Gothic latin+ea+cs (L18, L34) | `fonts: heading="Yu Gothic" body="Yu Gothic" ea="Yu Gothic"` | N |
| 3 | six named colours (L11-17) | `colors: primary=#142B4D secondary=#1F5FA8 accent=#D9821E surface=#EEF3F9 border=#C5D0DE ...` | N |
| 4 | title 28 bold navy left (L92) | `sizes: title=28`, `style: title.color=primary title.band=none` | N |
| 5 | blue rule under title (L93) | `title.rule=secondary title.rule_h=3pt` | N |
| 6 | message bar light fill (L95) | `lead.background=surface lead.padding="5pt 12pt"` | N |
| 7 | accent stripe at the bar's left (L96) | `lead.border-left="7pt solid accent"` | N |
| 8 | message 18 bold navy (L97) | `sizes: lead=18`, `lead.bold=on` | N |
| 9 | page number 10 grey right, none on cover (L100) | `num: on`, `sizes: caption=10` | N |
| 10 | speaker notes (L227) | `??? ...` | N |
| 11 | cover full navy (L107) | `@cover bg=primary dark` | N |
| 12 | accent bar on the slide's left edge, full height, 0.35 in (L110) | `cover.bar=accent cover.bar_w=0.35in` draws beside the title block only | M |
| 13 | accent rule 6 in wide between title and subtitle (L111) | `cover.rule=accent` is full width at the band edge | M |
| 14 | title 54 bold white, subtitle 22 light blue (L119, L126) | `sizes: cover-title=54 cover-subtitle=22`, `subtitle.color=ink`, `cover.band_h=61%` | N |
| 15 | KPI card white fill + border (L140) | `card.fill=bg card.line=border` | N |
| 16 | navy header band with white label (L141-142) | none; used `kpi.stripe=primary` + navy label | M |
| 17 | value 34 bold blue (L143) | `kpi.color=secondary kpi.size=34` | N |
| 18 | divider rule between value and note (L144) | none | M |
| 19 | note 22 bold accent (L145) | `kpi.note.size=22 kpi.note.bold=on kpi.note.color=#A06016` (darker, contrast) | N |
| 20 | KPI card height 4.2 in (L137) | `layout.kpi_lone_h=0.9 layout.kpi_lone_min_h=0.85` | N |
| 21 | clustered column, navy + accent (L154, L174) | `column {colors=primary,accent}` | N |
| 22 | legend top, 14 (L160-162) | `legend=top size=14` | N |
| 23 | gap width 60 (L164) | `gap=60` | N |
| 24 | series overlap -5 (L165) | none | M |
| 25 | labels outside, `#,##0`, 14 (L166-172) | `labels=outside fmt=#,##0` | N |
| 26 | data labels bold (L173) | none | M |
| 27 | value axis 0..1400 (L178-179) | `min=0 max=1400` | N |
| 28 | major unit 200 (L180) | none (auto gave 200) | M |
| 29 | tick labels 12 vs category 14 (L181, L186) | one size only | M |
| 30 | gridline colour, no axis line (L184-185) | `render.chart_grid=border` | N |
| 31 | box card light fill + border (L200) | `strat.fill=surface strat.line=border` + `{.strat}` | N |
| 32 | accent stripe on top of the card (L201) | css `.strat { border-top: 6pt solid #D9821E }` | C |
| 33 | navy circle with 1-4 (L202-203) | none | M |
| 34 | heading 18 bold navy left (L204) | `sizes: heading=18!` | N |
| 35 | blue rule under the heading (L205) | `heading.border-bottom` hits every heading including `###` | M |
| 36 | item card white fill + border (L208) | `### item {.item}` + `item.fill=bg item.line=border item.radius=0` | N |
| 37 | item card blue left stripe (L209) | css `.item { border-left: 5pt solid #1F5FA8 }` | C |
| 38 | item text 14 regular, centred vertically (L210) | `###` text is heading-sized bold; `item.font_size/bold/valign` ignored | M |
| 39 | footnote 12 grey (L211) | `※ ...`, `sizes: footnote=12` | N |
| 40 | arrows alternate navy / blue (L221) | `steps-arrow.fill=primary,secondary` | N |
| 41 | first arrow a pentagon, others chevrons (L221) | `render.chevron_shape` is all or none | M |
| 42 | step card light fill + border (L224) | `steps-card.fill=surface steps-card.line=border` | N |
| 43 | step card accent left stripe (L225) | css `.steps-card { border-left: 5pt solid #D9821E }` | C |
| 44 | card text 24 bold navy left (L226) | `steps-card.size=24 steps-card.bold=on`, plain paragraph | N |

Count: 29 N, 3 C, 12 M.

## Deviations accepted for 0 warnings

- KPI note colour #D9821E became #A06016 (2.6:1 on the card fill).
- KPI cards have a navy 6 pt top stripe and a navy label, not the header band.
- The cover accent bar sits beside the title, and the cover rule is full width at 61%.
- Slide 4 item text is 18 bold and top-aligned, with no number circles and no heading rule.
- All four step arrows are chevrons.
- Chart labels are regular weight, tick size follows `size=14`, and the major unit is automatic.

## Proposed syntax for the missing items

`kpi.band=primary` · `kpi.rule=border` · `@4 num` · `@4 items` · `heading.rule=secondary` · `cover.bar=accent@edge` ·
`cover.rule_w=6in` · `render.chevron_shape=pentagon,chevron` · `labels.bold=on` · `overlap=-5` · `step=200` · `size=14,12`
