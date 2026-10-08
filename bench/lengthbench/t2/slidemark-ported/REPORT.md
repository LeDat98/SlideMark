# Porting the python-pptx deck's design decisions to SlideMark (lengthbench t2, 15 slides; DL2 part 1, then lane G re-port)

Source: `../python-pptx/build.py` (the agent's 15-slide deck, render `../python-pptx/sheet.png`).
Port: `deck.md` (render `sheet.png`). Content-only baseline: `../slidemark-wave2/deck.md`.
Everything uses syntax documented in `docs/SYNTAX.md`; the deck has no css fence and no `@html`.

History: first port (wave 3, css fence + 2 `@html` slides) 2,283 tokens; DL2 part 1 (native forms for everything CSS-only) 1,577
tokens, 4 decisions missing; **lane G re-port** (this file) uses the forms that came after it (`kpi.rule`, `rowh=`, `@kpi`,
text-look shorthand, integer `widths=`, `@steps num`, `rows-num.fill`) and drops every token that restated a default.

## Build line (verbatim)

```
$ slidemark build deck.md -o /tmp/t2.pptx --png sheet.png
info slide 3 chart-scale: series '営業利益' (max 96) is under 10% of '売上高' (max 1280): it is drawn as a sliver -> split into two charts, ...
design: colors fonts sizes style footer num; 14/14 slides carry choices
look: theme none, bg #FFFFFF, text #222B36, primary #142B4D, accent #E09F1F; fonts Yu Gothic (headings, body), Yu Gothic (ea); title band off; accent on 3 charts
wrote /tmp/t2.pptx: 15 slides 16:9, 4 charts, 2 tables, notes on 2 slides, 0 warnings (checked: fit, overlap, contrast, text size, word breaks)
$ python bench/agent_accept.py bench/lengthbench/t2/accept.json /tmp/t2.pptx
accepted
```

The `chart-scale` info is the brief's data (1280 vs 96 on one axis); the python-pptx deck has the same sliver.

## 1. Tokens (o200k_base)

| File | Tokens | vs python-pptx |
|---|---|---|
| `python-pptx/build.py` | 5,263 | 100% |
| `slidemark-wave2/deck.md` (defaults, content only) | 1,261 | 24% |
| `slidemark-ported/deck.md` before DL2 part 1 (css fence + 2 `@html` slides) | 2,283 | 43% |
| `slidemark-ported/deck.md` after DL2 part 1 (no css fence, no `@html`; 4 decisions missing) | 1,577 | 29.96% |
| `slidemark-ported/deck.md` after lane G (all but one decision statable) | **1,577** | **29.96%** (header 294) |

How the lane G deck stays at the same size while it states more: it adds `kpi.rule=border kpi.rule_w=60%` (12 tokens), two `rowh=`
(10), `size=14` on two charts, `rows-num.fill=primary,secondary`, `sizes: kpi=54` on slide 9, `@steps num` text without
bullets; it drops `title.band=none`, `dark`, `legend=bottom|right|none`, `align=llll` on the second table, `sizes: kpi=54`
(all no-ops, found by removing each word and diffing the .pptx XML of every slide), and writes `widths=7:5:5:5`-style
integers. The margin to the gate is 2 tokens: do not add to this deck without removing something. The slide 8 text size
(`{size=26}`, 4 tokens) and the pie label size (`size=22`, 3) were left out to pay for `sizes: kpi=54`, which changes the render
(36 -> 47 pt).

## 2. Decisions (64; S = stated in deck.md, D = statable and equal to the default, M = not statable)

| # | Decision (build.py line) | SlideMark line | |
|---|---|---|---|
| 1 | slide 13.333 x 7.5 in (L24) | default | D |
| 2 | Yu Gothic latin + ea + cs (L11, L31) | `fonts: font="Yu Gothic"` | S |
| 3 | eight named colours (L12-20) | `colors: fg primary secondary accent teal muted surface border` | S |
| 4 | series palette blue / amber / teal / purple (L21) | `palette=secondary,accent,teal,#8A5AA8` | S |
| 5 | navy top strip across every slide (L91) | `top.bar=primary` (0.10 in, python-pptx 0.12 in: `top.bar_h=0.12in` not stated) | S |
| 6 | title 28 bold navy (L92) | `sizes: title=28`, `title=primary` | S |
| 7 | blue rule under the title (L93) | `title.rule=secondary` | S |
| 8 | message 18 bold blue (L95) | `sizes: lead=18`, `lead="bold secondary"` | S |
| 9 | footer text 10 grey (L96) | `footer: ...`, `sizes: caption=10` | S |
| 10 | page number right (L97) | `num: on` | S |
| 11 | speaker notes on 2 slides (L101) | `??? ...` | S |
| 12 | type scale (box head 20, box text 22, table 20, footnote 13) | `sizes: heading=20! body=22! table=20 footnote=13` | S |
| 13 | square cards, light fill + line border (L138) | `card.radius=0` (fill and line are the `surface` / `border` defaults) | S |
| 14 | navy header band, centred bold white 20 (L139-140) | `heading.band=primary heading=center` | S |
| 15 | teal "■" bullet (L149-150) | `bullet=■ bullet.color=teal` | S |
| 16 | 3-box slide: heading 26, text 24 (L132) | `sizes: heading=26! body=24!` inside the slide | S |
| 17 | 22 pt between items (L147) | `layout.para_gap=1` (not stated; the default gap is close) | D |
| 18 | footnote 13 grey (L155) | `※ ...` | S |
| 19 | box vertical anchor top, box height 4.4 / 4.6 in | default | D |
| 20 | KPI card light fill + line (L114) | the `.kpi` card is a `card` | D |
| 21 | KPI top stripe (L115) | `kpi.stripe=secondary` | S |
| 22 | KPI label 20 bold navy (L116) | `kpi.label="20 bold primary"` | S |
| 23 | KPI value 34 / 54 bold blue (L118) | `kpi.color=secondary`, `sizes: kpi=54` inside slide 9 (47 pt after the card-width fit; the four-up rows are 27 / 36 pt without a token: 34 is not stated) | S |
| 24 | divider between value and note (L121) | `kpi.rule=border kpi.rule_w=60%` (lane C) | S |
| 25 | KPI note 20 bold teal (L122) | `kpi.note="20 bold teal"` | S |
| 26 | KPI card height 4.4 in (L110) | `kpi.h=4.4in` (slides 9 and 14 are 4.9 in in python-pptx: not stated) | S |
| 27 | 3- and 4-up KPI rows (L108) | `@kpi` | S |
| 28 | KPI text centred in the card | default | D |
| 29 | arrow row with a card under each (L167-171) | `@steps num` | S |
| 30 | pentagon instead of chevron (L167) | `render.chevron_shape=pentagon` | S |
| 31 | arrows alternate navy / blue (L167) | `steps-arrow.fill=primary,secondary` | S |
| 32 | card text 24 bold centred (L170) | `steps-card="24 bold center"` | S |
| 33 | "STEP n" caption teal (L172) | `@steps num`, `steps.caption_color=teal` (above the card; python-pptx puts it below) | S |
| 34 | arrow text 26 bold white (L168) | default | D |
| 35 | table column widths 3.9 / 2.8 / 2.8 / 2.63 (L273) | `widths=7:5:5:5` | S |
| 36 | row height 0.8 / 1.05 in (L267, L277) | `rowh=0.8in`, `rowh=1.05in` (lane C) | S |
| 37 | navy header, white bold (L284) | `table.header.fill=primary` (ink derived) | S |
| 38 | zebra (L286) | `.zebra`, `table.zebra.fill=surface` | S |
| 39 | first column bold (L292) | `hcol=1` | S |
| 40 | left-aligned cells (L289) | `align=llll` (needed on the numeric table only) | S |
| 41 | cell padding 0.15 in (L281) | `layout.cell_pad_x=0.15in` (not stated; the default is close) | D |
| 42 | table text 20 (L292) | `sizes: table=20` | S |
| 43 | conclusion bar blue, 24 bold white (L305-306) | `conclusion.fill=secondary conclusion="24 bold"` | S |
| 44 | series colours (L219) | the palette (#4) | D |
| 45 | gap width 80 / 60 (L209) | `gap=80`; 60 is the default | S |
| 46 | labels outside end (L210) | `labels=on` | S |
| 47 | number format `#,##0` (L203) | `fmt=#,##0` | S |
| 48 | data label size 14 (L205) | `size=14` | S |
| 49 | legend bottom (L182) | default | D |
| 50 | axis tick size 13 vs 14 (L213-214) | `size=14,13` (statable; not stated: 4 tokens over the gate) | D |
| 51 | gridline colour (L213) | `render.chart_grid` default is `border` | D |
| 52 | no value-axis line (L215) | automatic | D |
| 53 | pie slice colours (L319-322) | the palette (#4) | D |
| 54 | pie labels white bold 22 inside (L316-318) | white bold inside is the default; `size=22` not stated (3 tokens) | D |
| 55 | pie legend right 18 (L312-313) | right is the default; `legend.size=18` not stated (5 tokens) | D |
| 56 | line width 3.5, markers 9 (L359-363) | `render.chart_line_width=3.5 marker=9` | S |
| 57 | line label above, Taiwan below (point 2027 above) (L355-371) | `labels=above,above,above,above` is per category, not per series: automatic collision rule only | M |
| 58 | bar: reversed categories, no legend (L403) | automatic | D |
| 59 | cover full navy (L226) | `@cover bg=primary` | S |
| 60 | amber rule at 61% (L227) | `cover.band_h=61% cover.rule=accent` | S |
| 61 | teal bar left of the title (L228) | `cover.bar=teal` | S |
| 62 | cover title 54 bold white (L229) | `sizes: cover-title=54` | S |
| 63 | cover subtitle 24 light blue (L231) | `style: subtitle.color=#D6E2F0` inside the slide (24 is the default size) | S |
| 64 | numbered bars, badges alternate navy / blue, text 26 (L328-333) | `@rows`, `rows-num.fill=primary,secondary` (`{size=26}` not stated: 4 tokens) | S |

Count: **S 47, D 16, M 1** = 63 / 64 = **98.4% statable, all native** (no css fence, no `@html`). The one missing decision is a line
label position per series (a position list applies to the categories of every series).

## 3. Deviations kept for 0 warnings or for the gate

- `teal` is `#217B70` (python-pptx `#2A9D8F` fails the contrast check on the card fill); pie and line use it too.
- KPI numbers shrink to the card width (27 pt on the four-up row with a lead, 47 on three; python-pptx 34 / 54): the layout keeps
  28% headroom in the card, and `sizes: kpi=` cannot raise it past that.
- `top.bar` is 0.10 in (0.12), KPI cards are 4.4 in on every slide (4.9 in on slides 9 and 14), the STEP caption is above the
  card, the pie legend and axis ticks are not sized (rows 50, 55), Taiwan labels follow the collision rule (row 57).

## 4. What the lane G re-port proves

Token share 29.96% (1,577 / 5,263) with 98.4% of the decisions statable natively: DL2 holds on this deck. Two of the four
decisions that were missing after DL2 part 1 (KPI divider, exact row heights) are stated now; the colour per bar is not used
by this deck; the per-point label position exists per category only (row 57). Finding while re-porting: `sizes: kpi=NN`, documented
in SYNTAX.md and DESIGN_COVERAGE.md since part 1, was a silent no-op (it reached `theme.sizes` and nothing read it); lane G
makes it set the KPI number size (`kpi.size=` still wins), which is why `sizes: kpi=54` appears on slide 9.
