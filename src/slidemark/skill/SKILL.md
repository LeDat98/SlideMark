---
name: slidemark
description: Make slides, a slide deck or a presentation as a native, editable PowerPoint (.pptx) file, written as compact SlideMark text with your own stated design choices. Use for every request to make slides, a deck, a pitch deck or a presentation, in any language, however short or informal. Whoever installed this skill wants their decks as .pptx files, so a request that names no format still means a .pptx file. Not for reading or editing an existing .pptx file.
---

# SlideMark

This page is complete: do not look for other docs.
If `slidemark` is missing: `pip install -U "slidemark[preview]"` (Python 3.10+). `--png` also needs LibreOffice;
`@html` also needs `pip install "slidemark[html]"` and `playwright install chromium`.

## Recipe: decide, then write and build in ONE command

```bash
slidemark build - -o deck.pptx --save deck.md --png sheet.png <<'EOF'
# Title
...
EOF
```

`build` checks, fixes simple mistakes, builds and prints: warnings (slide, line, fix), one **fit line per
slide**, `design:`, `look:` and the counts. The fit line answers "did my choice take effect, how does the slide
sit": `slide 2: lead + 4 kpi cards 46% of body, value 48->40pt (shrunk to fit), free 31% below, took size=44` =
the form used, text size asked->reached (grown or shrunk to fill unless pinned: `size=`, `sizes: body=14!`),
free space, attributes `took` / `ignored` (`attr-ignored` names what works).

**0 warnings, the counts your brief asks for, fit lines that match what you decided, and one look at
`sheet.png` that finds none of the defects in "Check before handing back" = done: reply.**
Else edit `deck.md` once and run `slidemark build deck.md -o deck.pptx --png sheet.png`. The only look is
`sheet.png` (written by that same build) with ONE Read per build; never render, re-open the .pptx or run
another command. Usual path: read, build + look, hand back = 3 calls; one fix round = 4. (No heredoc? Write
`deck.md`, build in the same turn.)

## Decide first (the choices are yours, none is the right one)

Settle these in your reasoning, then write them into the deck (`build` echoes them in `design:`):

1. **Deck frame:** colours, fonts, type scale, chrome (title band, cards, rules), `footer:` / `num:`, a `css`
   fence for what tokens cannot say. A `theme:` preset alone does not count.
2. **Each slide:** its form (list, cards, `@steps`, grid, table, chart kind, KPI row, `@html`), its one
   emphasis (`.hero` `hl=` `==x==` `{.accent}`), an override where the default fails its message
   (`size=` `fill=` `color=` `align=` `x y w h`).
3. **Each chart and table:** series colours, labels, legend, the takeaway (`hl=` + `note=`), `widths=` `align=`
   `.zebra`.
4. **Expected fit:** per slide, what its fit line should say (form, size, how full); a line that differs is
   the cue to change one thing. Text grows to fill a sparse slide only up to `layout.grow_max` (1.5 x; `grow.max=1` = never)
   and the fit line / `sparse` info (`sparse: 42% free`) name slides that stay empty: decide their form (merge,
   add a figure, `@rows` / `@items` / side by side) rather than raising `size=`.

`design-none` names the missing header lines (`colors:` `fonts:` `sizes:` `style:`); `design-slide` the slides
short of a form, one emphasis (or `@noemph`), values (or `@defaults`). Advisory.

## Design guide (what separates a deck people keep from one they close)

**Before the first slide: palette and motif, chosen for THIS topic.**
- A palette that would fit any other deck is not specific enough. One colour carries 60–70% of the visual
  weight (`primary`), one or two support it (`secondary`, `surface`), one accent is rare and means something
  (`accent`: the key number, the current step, the verdict). Never split the weight evenly.
- Light/dark contrast: dark cover and closing slide, light content between ("sandwich": `@cover bg=primary dark`
  on the first and last slide), or dark throughout for a premium feel (`@bg=` on every slide or `theme: midnight`).
- One repeating visual motif, carried by every content slide: an icon on each card heading (`icon=`), numbered
  discs (`@rows`, `num`), one chart style, one card style. Bars and stripes are not a motif.
- Starting points (write your own hexes when the brand or topic suggests them; do not default to blue):
  navy + teal + amber `colors: primary=#0B2A3C secondary=#1B8A8F accent=#F2A33A surface=#EEF4F6` ·
  forest + moss + cream `primary=#1E3A2F secondary=#6B8F71 accent=#D9A441 bg=#FBF8F1` ·
  charcoal + coral `primary=#2B2D42 secondary=#8D99AE accent=#EF6F4C surface=#F4F5F7` ·
  plum + rose `primary=#4A1D3F secondary=#9A5B82 accent=#E8B44A surface=#F7F1F4` ·
  slate + lime `primary=#1F2A37 secondary=#5B6B7F accent=#A4D65E surface=#F1F4F7`.

**Every slide carries a visual element**: a chart, a table, icons, a diagram or shaped blocks. A slide of only
text is a defect, not a style. Forms that give a slide its shape (see "Composition forms"):
- Two columns, text beside a figure: a box + chart/table/image, or `@split`.
- Icon rows: `@iconlist cols=2` (icon, bold title, text), or `## Title {icon=bolt}` cards.
- Grids: `@2x2` / `@3` cards with icons; `@kpi` for numbers; `@matrix` for two axes.
- A picture bleeding over half the slide with content on top: `@split bleed=on`.
- Numbers: `@statement` (one 60–72pt figure + a small label) or `{.kpi .hero}`; before/after and pros/cons
  as `@vs` / `@proscons`; a sequence as `@timeline`, `@steps num` or `@cycle` with arrows.
- Finish: an icon beside each heading, the one key figure or claim in the accent (`==x==`, `hl=`, `{.hero}`).

**Type and spacing** (set once in `sizes:` and `style:`, then leave them):
slide title 36–44pt bold · box headings 20–24pt bold · body 14–16pt · captions 10–12pt in `muted` · slide
margin ≥ 0.5in (`margin=0.6in`) · one gap between blocks, kept throughout. Safe fonts that render at the
measured width everywhere: Arial, Calibri, Cambria, Georgia, Times New Roman, Courier New; pair a serif heading
with a sans body (`fonts: heading="Cambria" body="Calibri"`) for contrast. Not Aptos (older Office has no
equivalent fallback). Japanese: Meiryo or Yu Gothic.

**Never**: a rule under the slide title (`title.rule`, `heading.rule`) and decorative bars or stripes
(`top.bar`, `bottom.bar`, `box.stripe`, `kpi.stripe`, `item.border-left`, a vertical band beside the content).
Both read as machine-made. To lift a card use a tinted `fill`, `shadow=on` or an icon.
**Avoid**: the same form on consecutive slides; a full stop at the end of a title; titles that move, change
font or size between slides of one kind; centred paragraphs (centre titles only); titles under 36pt or body
under 14pt (pin floors: `sizes: title=36! body=14!`, then cut text, widen the block or split the slide
instead of letting text shrink); low contrast of text or icons on their fill; blue or cream/beige by default
when nothing asks for them (white or the brand colour); text spilling out of its block; one decorated slide
and the rest plain.

**Check before handing back** (the visual pass catches the most):
1. Content: every fact of the brief is on a slide, no typos, the order follows the argument.
2. File: `build` reports 0 warnings (its lint covers overflow, overlap, contrast, missing alt text).
3. Visual: read `sheet.png` once, slide by slide, with fresh eyes. Look for text cut at a block or slide
   edge, overlapping blocks, uneven gaps or margins under 0.5in, a title that sits elsewhere than on its
   siblings, low contrast, a number split from its unit, template text left over, a slide that is only text.
   Fix what you find in `deck.md` and rebuild once.

**Structure of the deck file** (so one change applies everywhere and the .pptx stays editable): declare the
palette and the two fonts in the header, never a hex on a slide; group slides with `@section` dividers;
footer and page number in the header (`footer:` `num: on`), not on slides; one form per slide kind (cover,
section, agenda, content, chart + takeaway, table, closing) reused with the same `sizes:`; each slide's own
cards, icons, numbers and pictures sit on that frame.

## Pattern 1: English deck, every slide decided

````markdown
theme: none
lang: en
colors: bg=#FAF7F2 fg=#1F2933 primary=#0F4C5C accent=#E36414 surface=#FFFFFF border=#D9D2C5
fonts: heading="Georgia" body="Calibri"
sizes: title=34 heading=18 body=16 lead=20
style: radius=6 title.band=none card.shadow="0 2 8 #00000022" table.header.fill=primary palette=primary,#5F9EA0,#B8B8AA
footer: Q3 review
num: on

# Q3 Review {size=60 align=left}
## Revenue and the Q4 plan

# Revenue grew 18% on one segment
> Enterprise carried the quarter
@defaults
## Revenue {.kpi .hero}
$4.2M
+18% QoQ
## Churn {.kpi}
2.1%
-0.4 pt
## NPS {.kpi}
61
@end
- 14 enterprise logos signed, 3 in the last week

# Enterprise drove the growth
```column {title="Revenue by segment ($M)" colors=#B8B8AA,primary labels=on legend=bottom hl=Enterprise note="Enterprise: 62% of growth"}
,SMB,Mid,Enterprise
Q2,0.8,1.1,1.6
Q3,0.9,1.2,2.1
```

# Enterprise also retains best
```table {widths=3:1:1 align=lrr hl=Enterprise .zebra}
Segment,Q2,Q3
SMB,4.0%,3.6%
Mid,2.8%,2.4%
Enterprise,1.1%,0.8%
```
> Keep the success team on enterprise accounts

# Q4 plan
@steps num defaults
## Oct {.accent}
- Hire 4 AEs
## Nov
- Launch partner tier
## Dec
- Renewal push

# Two asks
@free noemph
{x=6% y=25% w=40% h=45% size=28 fill=primary color=#FFFFFF align=center valign=middle}
+$300k for partner marketing
{x=54% y=25% w=40% h=45% size=28 fill=accent color=#FFFFFF align=center valign=middle}
4 account executives

# Thank you
@html noemph defaults
```html
<div style="height:100%;background:var(--primary);color:#fff;padding:96px">
  <h1 style="font-size:72px;margin:0">Next review: January</h1>
</div>
```
````

## Pattern 2: dense Japanese business deck, every slide decided

````markdown
theme: jp-business
lang: ja
colors: primary=#0B3D91 accent=#C8102E
fonts: ea="Yu Gothic"
sizes: body=11 table=10 footnote=9
style: title.band=primary heading.band=primary table.header.fill=primary top.bar=accent kpi.stripe=primary
footer: ACME株式会社
num: on

# 営業DXの進捗報告
## 営業企画部

# 主要指標
> 商談化率が目標を上回った
@defaults
## 商談数 {.kpi}
420件
前月比 +12%
## 商談化率 {.kpi}
31%
目標 28%
## 受注額 {.kpi}
3.8億円
前月比 +5%
@end
- インサイドセールスの架電数が倍増
- 失注理由の記録率は ==60%== に留まる

# 課題と対策
> 入力負荷を下げ、記録率を90%に高める
@2x2
## 入力負荷
- 1件あたり8分
## 項目過多
- 必須項目が24個
## 定着 {.danger}
- 研修は年1回のみ
## 対策 {fill=#EAF1FB}
- 音声入力で自動記録
※ 出所: 営業部アンケート（2026年9月）

# 部門別の受注額
```table {widths=3:1:1:1 align=lrrr hl=西日本 .zebra}
部門,前期,今期,増減
東日本,1.9,2.1,+0.2
西日本,1.2,1.7,+0.5
海外,0.4,0.3,▲0.1
```
````

Japanese: half-width digits, units in Japanese (`12.4億円`), one-line bullets (≈ 25 full-width chars per
column of a 3-column slide), `▲3` = −3 in tables. `jp-business` is compact: `@dense` only on a full slide.

## Syntax

**Header** (`key: value` lines before the first `#`): `theme` (`default` `midnight` `jp-business` `none`,
`./brand.yaml`, `template.pptx`), `lang` (`en` `ja` `vi` …), `title`, `footer`, `num: on`, `size` (`4:3`, `A4`),
`density: dense`, `fit: off` (no fit lines), and the design lines `colors:` `fonts:` `sizes:` `style:` (below).

**Slides.** `# Title` starts a slide. A title with only a `## subtitle` (or ≤ 2 short lines) is a cover
(first slide) or section divider (`@cover` / `@section` force it). `??? text` = speaker notes to the slide
end. `@hidden` hides a slide.

**Blocks.** `## Heading` + its lines = a box; boxes arrange themselves (2 → 2 columns, 3 → 3, 4 → 2×2 or a
row, 5–6 → 3×2; text + one chart/table/image → side by side). `>` right after the title = key message (lead),
`>` last = conclusion bar, `※ text` = footnote. `@end` closes the last box: what follows (table, chart, list)
goes full width below. Each table/chart/image/code outside a box is its own block.

**`@` line** (only if the automatic layout is wrong; one per slide, tokens space separated):
`@3` columns · `@2x2` grid · `@1:2` ratios · `@aab/aac` areas (letters = blocks in order, `.` empty) ·
`chevron` steps (heading + 1–2 short bullets) · `steps` arrows, bullets in a card below (`steps num` adds a
"STEP n" caption) · `rows` a `1.` list alone as numbered bars (`rows plain` = unnumbered, `rows.glyph=■ rows.stripe=a,b`) ·
`items` bullets of each box as item cards (`item.fill` `item.border-left="5pt solid secondary"` `item.size`) · `num` a
numbered circle on each box heading (`box.num.fill`) · `flow` cards with arrows · `a>b` arrow, `a-b` line between blocks · `@dense` · `@build` click-to-reveal · `@t=fade` transition ·
`@bg=#0B1020` or `@bg="linear-gradient(135deg,#1A0B2E,#7A1FA2)"` background (dark flips text light; `@dark`
`@light` force it) · `@free` no automatic layout: blocks sit at their own `{x y w h}` (`%` = share of the area under the title, not of the slide; `@free grid`: 12×12 cells, `x=3c w=4c`); a line of attributes with no text draws nothing yet.

**Attributes** `{.class key=value}` at the end of a heading, image, title or list line, or alone on the line
before a block; every element takes `x y w h` (`%` `in` `cm` `pt`; never moved by the layout once set), `size`,
`color`, `fill`, `line`, `radius`, `shadow=on`, `align`, `valign`, `bold`, `italic`, `font`, `opacity`, `pad`,
`rotate=-4`, `shape=pill|hexagon|chevron|parallelogram|ellipse|…` (59 names), `z=1..9` (stacking), `icon=name`.
Classes: `.primary .accent .danger .success .muted` (colours), `.plain` (no card), `.kpi`, `.zebra` (table
rows), `.badge` (inline pill). On a heading, `size` `fill` `color` style the whole box; `- 要確認 {color=danger}`
styles one list line; a chart frame takes `{fill= radius= pad=}`.

**Inline:** `**b**` `*i*` `~~s~~` `` `code` `` `==accent==` `[text]{.danger}` `[済]{.badge .success}`
`[link](url)`. Lists: `-` / `1.`, nest with two spaces; `- [ ] todo`.

## Composition forms (one `@word` line under the title; secondary attributes on the same line; looks via `word.*` tokens)

- `@timeline dir=h|v marks=on|off|num` + `## date` boxes (heading = date, body = text, `{.accent}` = now).
- `@vs` + two `##` cards and an optional `## 結論` verdict bar (`{.hero}` = the winner).
- `@matrix x="低←容易性→高" y="低←効果→高"` + exactly four `##` boxes in reading order (`fill=a,b,c,d` per quadrant).
- `@funnel` / `@pyramid dir=up|down` + `##` boxes (heading inside the stage, body right; `funnel.fill=a,b,c` `.taper`).
- `@cycle dir=cw|ccw` + 3–6 `##` boxes in loop order (heading in the node, body outside; `cycle.fill` `.arrow`).
- `@agenda` + one `1.` list alone, `{.accent}` on the current item (`agenda.num.size` `.num.text="第{n}章"` `.rule=none`).
- `@statement align= valign=` + `**+18%**` then one caption line (one huge number or sentence; `statement.size`).
- `@iconlist cols=2` + `- icon=bolt **Title** text` items (icon, bold title, text in 1–3 columns; `iconlist.icon.size/.color`).
- `@quote align=center` + `> "text"` then `> — Name` (large quotation with mark and attribution; `quote.size` `quote.mark.color`).
- `@split side=right ratio=2:3 bleed=on` + `![alt](x.png)` (or a `fill=` block) + any text/boxes (picture beside content).
- `@proscons` + two `##` boxes (pros, cons) + optional last `> verdict` (+/− discs, verdict bar; `proscons.plus.color`).
- `@progress max=100` + `- label 72%` (or a table label|value) → labelled bars (`progress.fill/.track/.h`).
- `@harvey` + a table of 0–4 (or 0/25/50/75/100%) → native Harvey balls (`harvey.size/.fill/.line`).
- `@heatmap min=0 max=100 colors=#F3F6FA,primary` + a numeric table → interpolated cell fills, auto ink (`text=auto|on|off`).
- `@pins legend=right|bottom|off` + image + `- x=32% y=58% label` → numbered pins on the image plus a legend (`pins.fill/.size`).

## Components

- **KPI row:** `@kpi` under the title makes every `##` box a card; `style: kpi.h=4.4in` sets card height, `kpi.rule=border`
  draws a rule between number and note, `kpi.band=primary` a label band, `kpi.unit.size=22` a smaller unit (億円 %); place the row yourself with `{.kpi .hero w=45% h=55% y=24%}` (shares of the body).
  **KPI card:** `## Label {.kpi icon=yen}` + value line + caption line; `{.kpi .hero}` = the lead metric,
  wider with a bigger number. Up to 4 in a row; `@end` + a list or table below them.
- **Callout:** `> [!note] text` (`tip` `warn` `caution`), at slide level or inside a box.
- **Icons:** `icon=` on a box heading: `check warning info user chart money yen target rocket gear clock
  globe shield flag` or `icon=logo.svg`.
- **Flowchart, org chart:** ` ```mermaid ` with `graph TD` / `graph LR`, `A[申請] --> B{承認?}`, `B -->|yes| C`.
- **Math:** ` ```math ` LaTeX → native equation. **Images:** `![what it shows](a.png)` (alt text required);
  `![alt](demo.mp4)` video/audio; ` ```svg ` inline SVG. Other fences are code.

## Tables and charts

Table: ` ```table ` fence with CSV (first row = header; quote cells with commas: `"1,240"`), or a GFM table.
Options on the fence or the line before: `{widths=3:1:1 align=lrr header=1 hcol=1 rowh=0.8in .zebra}` (one `align` letter
per column); `.gantt` draws filled period cells as bars; `hl=Metro,Kyoto` emphasises the rows whose first cell
matches, `hlcol=Q3` a column. Merge: a lone `<` joins the cell to the left, `^` the cell above.

Chart fence kinds: `column bar line area pie doughnut scatter radar stacked-column stacked-bar waterfall` (waterfall: one row, `=` cell = total). CSV body:
first row = categories (first cell empty), then one row per series (name first). Options: `title="..."`
`labels=on|percent|off` `legend=bottom|right|top|none` `fmt="0.0"|"#,##0"|"0%"` `min=` `max=`
`colors=primary,accent,#888888` (names from `colors:` work) `gap=80` `marker=9` `size=14` (exact)
`labels=outside|inside|above|below` (`+name` on a pie) `labels.bold=on` `labels.color=` `size=16,14` (labels, axis)
`legend.size=` `overlap=-5` `step=200` `totals=off` `slice.line=bg` `axis=off`; one word per category
(`labels=above,below,above,above`) places each point's label; a one-series bar takes `colors=a,b,c,d` (one per bar); takeaway: `hl=Metro note="Metro: 40% of visits"` (`hl=` names a
category or a series). Numbers may be
`1,240`, `12%`, `▲3`; a decimal comma needs quotes (`"1,6"`). One value axis.

## Design tokens (header lines; `sizes:` / `style:` lines inside a slide change that slide only)

- `colors:` `bg fg primary accent surface border muted danger success` or any new name (`brand=#FF5A1F`).
  `primary` colours KPI numbers, badges, bars, charts and the title band.
- `fonts:` `heading body mono ea` (ea = Japanese/Chinese text) or `font="Yu Gothic"` for all three.
- `sizes:` pt per role: `title heading body lead conclusion caption footnote table code cover-title`; a trailing
  `!` (`heading=20!`) pins the size against automatic growth.
- `style:` `radius=14` `gap=12pt` `padding=12pt` `shadow="0 6 18 #00000055"` `card.fill=#141A2E` (`none` =
  no card; a `linear-gradient(...)` works) `title.band=primary|none`
  `heading.band=primary` `table.header.fill=primary`
  `palette=primary,accent,#FF5A1F` (chart series) `h1.letter-spacing=2pt` (any `selector.css-property`)
  `hero.fill=#FF5A1F` (your own class, used as `## X {.hero}`). Chrome: `top.bar=primary` `title.rule=secondary` `kpi.stripe=secondary` `kpi.label.size=20` `bullet=■` `lead.bold=on`
  `footer.color=muted` `steps-arrow.fill=a,b` `rows-num.fill=a,b` `heading.rule=accent` `title.rule2=accent` `cover.bar=teal|accent@edge`
  `cover.rule_w=6in cover.rule_pos=above|below` `cover.stripes=a@9in` `render.chevron_shape=pentagon,chevron`
  `table.num_pad=0.6in` `render.chart_grid=border`. A text look in one token:
  `kpi.label="20 bold primary"` `steps-card="24 bold center"` `heading=center` (size, bold, italic, left/center/right, colour).
- A ` ```css ` fence (header = whole deck, in a slide = that slide) styles `slide h1 h2 p li .lead
  .conclusion .footnote .box .kpi table th td tr code img .chart` and your `{.class}`: colours, gradients,
  borders, radius, shadows, fonts, spacing, `transform: rotate()`.
- `@html` + one ` ```html ` fence = a slide written in HTML/CSS, converted to editable shapes (`var(--primary)`
  reads your tokens).

## Rules

- One message per slide (the `>` lead); at most 4 boxes × 6 bullets and 8 table rows, else split the slide.
- Set a position or size only where you decided the default would not serve the slide; otherwise the layout fits text itself.
- Every image has alt text.
- Warnings: `overflow` (shorten or split), `contrast` (paste the hint's colour), `missing-end` (add `@end`),
  `unknown-*` (did-you-mean), `design-*` (state a choice), `attr-ignored` (use the hint's form). Fix only the named line.
