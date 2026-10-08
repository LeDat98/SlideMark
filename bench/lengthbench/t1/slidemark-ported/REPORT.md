# Porting the python-pptx deck's design decisions to SlideMark (lengthbench t1, 5 slides; DL2 lanes D, E, F and G)

Same method as `../../t2/slidemark-ported/REPORT.md`. Source `../python-pptx/build.py`; port `deck.md`
(render `sheet.png`); content-only baseline `../slidemark/deck.md`.

## Build line (verbatim)

```
$ slidemark build deck.md -o /tmp/t1.pptx --png sheet.png
info slide 3 chart-scale: series '営業利益' (max 96) is under 10% of '売上高' (max 1280): ...
slide 4: 4 boxes (row), text 18->14pt (shrunk to fit), fills body
design: colors fonts sizes style num; 4/4 slides carry choices
wrote /tmp/t1.pptx: 5 slides 16:9, 1 chart, notes on 1 slide, 0 warnings (checked: fit, overlap, contrast, text size, word breaks)
$ python bench/agent_accept.py bench/lengthbench/t1/accept.json /tmp/t1.pptx
accepted
```

## Tokens (o200k_base)

| File | Tokens | vs python-pptx |
|---|---|---|
| `python-pptx/build.py` | 3,187 | 100% |
| `slidemark/deck.md` (content only) | 460 | 14% |
| `slidemark-ported/deck.md` before lane F (lane D port) | 912 | 28.6% (header 385) |
| `slidemark-ported/deck.md` after lane F (**no css fence**, chart forms of lane E) | 890 | 27.9% (header 382) |
| `slidemark-ported/deck.md` after lane G (`kpi.band`, `kpi.rule`) | **882** | **27.7%** (header 373) |

## Decisions (44; N = native, C = css only, M = missing)

Rows changed by lane F (box, cover and chrome forms) and lane E (chart forms) are marked; every other row is as in the lane D port.

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
| 12 | accent bar on the slide's left edge, full height, 0.35 in (L110) | `cover.bar=accent@edge cover.bar_w=0.35in` (lane F) | N |
| 13 | accent rule 6 in wide between title and subtitle (L111) | `cover.rule=accent cover.rule_w=6in` (`cover.rule_pos=below` is the default; lane F) | N |
| 14 | title 54 bold white, subtitle 22 light blue (L119, L126) | `sizes: cover-title=54 cover-subtitle=22`, `subtitle.color=ink`, `cover.band_h=61%` | N |
| 15 | KPI card white fill + border (L140) | `card.fill=bg card.line=border` | N |
| 16 | navy header band with white label (L141-142) | `kpi.band=primary kpi.band.size=20` (lane G; the ink is white by itself) | N |
| 17 | value 34 bold blue (L143) | `kpi.color=secondary kpi.size=34` | N |
| 18 | divider rule between value and note (L144) | `kpi.rule=border` (lane C) | N |
| 19 | note 22 bold accent (L145) | `kpi.note.size=22 kpi.note.bold=on kpi.note.color=#A06016` (darker, contrast) | N |
| 20 | KPI card height 4.2 in (L137) | `layout.kpi_lone_h=0.9 layout.kpi_lone_min_h=0.85` | N |
| 21 | clustered column, navy + accent (L154, L174) | `column {colors=primary,accent}` | N |
| 22 | legend top, 14 (L160-162) | `legend=top legend.size=14` | N |
| 23 | gap width 60 (L164) | `gap=60` | N |
| 24 | series overlap -5 (L165) | `overlap=-5` (lane E) | N |
| 25 | labels outside, `#,##0`, 14 (L166-172) | `labels=outside fmt=#,##0` | N |
| 26 | data labels bold (L173) | `labels.bold=on` (lane E) | N |
| 27 | value axis 0..1400 (L178-179) | `min=0 max=1400` | N |
| 28 | major unit 200 (L180) | `step=200` (lane E) | N |
| 29 | tick labels 12 vs category 14 (L181, L186) | `size=14,12` (lane E) | N |
| 30 | gridline colour, no axis line (L184-185) | `render.chart_grid=border` | N |
| 31 | box card light fill + border (L200) | `strat.fill=surface` + `{.strat}` | N |
| 32 | accent stripe on top of the card (L201) | `strat.border-top="6pt solid accent"` (a class token; was a css rule) | N |
| 33 | navy circle with 1-4 (L202-203) | `@4 items num`, `box.num.fill=primary` (lane F) | N |
| 34 | heading 18 bold navy left (L204) | `sizes: heading=18!` | N |
| 35 | blue rule under the heading (L205) | `heading.rule=secondary heading.rule_h=0.03in` (lane F) | N |
| 36 | item card white fill + border (L208) | `@4 items`; the `item` class defaults to the `bg` fill and the card line (lane F) | N |
| 37 | item card blue left stripe (L209) | `item.border-left="5pt solid secondary"` (was css) | N |
| 38 | item text 14 regular, centred vertically (L210) | `item.size=14 item.bold=off` (valign middle is the default; was ignored) | N |
| 39 | footnote 12 grey (L211) | `※ ...`, `sizes: footnote=12` | N |
| 40 | arrows alternate navy / blue (L221) | `steps-arrow.fill=primary,secondary` | N |
| 41 | first arrow a pentagon, others chevrons (L221) | `render.chevron_shape=pentagon,chevron` (lane F) | N |
| 42 | step card light fill + border (L224) | `steps-card.fill=surface` | N |
| 43 | step card accent left stripe (L225) | `steps-card.border-left="5pt solid accent"` (was css) | N |
| 44 | card text 24 bold navy left (L226) | `steps-card.size=24 steps-card.bold=on`, plain paragraph | N |

Count: **44 N, 0 C, 0 M** = 100% statable, all native (lane F port: 42 N + 2 M; lane D port: 33 N + 3 C + 8 M). DL2
(>= 95% statable, <= 30% of the tokens) holds on this deck.

## Deviations accepted for 0 warnings

- KPI note colour #D9821E became #A06016 (2.6:1 on the card fill).
- The two step arrows after the first are chevrons as in the original; the pentagon is the first (as in the original).
- Slide 4 items are 14 pt regular as in the original; the cards fill the box height (the original used fixed 1 in cards).

## What the lane F port changed

The css fence is gone (three rules became the class tokens `strat.border-top`, `item.border-left`, `steps-card.border-left`), the
`### {.item}` sub-boxes and their `@1x2` lines became `@4 items`, and `item.fill=bg item.line=border item.radius=0` are the
defaults now. The chart line uses the lane E forms (16 tokens). Tokens 912 -> 890 (874 without the chart forms).

## What the lane G port changed

The KPI header band and the divider are native now: `kpi.stripe=primary` + `kpi.label.size=20 kpi.label.bold=on kpi.label.color=primary`
became `kpi.band=primary kpi.band.size=20 kpi.rule=border` (the band label is bold and white on its own). Tokens 890 -> 882
(27.7%), 0 warnings, `agent_accept` accepted.
