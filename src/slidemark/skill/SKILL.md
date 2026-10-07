---
name: slidemark
description: Write PowerPoint decks as compact SlideMark text, with your own stated design choices, and build native, editable .pptx files. Use when asked for slides, a deck, or a presentation (.pptx), including dense Japanese business slides.
---

# SlideMark

This page is complete: do not look for other docs.

## Recipe: decide, then write and build in ONE command

```bash
slidemark build - -o deck.pptx --save deck.md <<'EOF'
# Title
...
EOF
```

`build` checks, fixes simple mistakes, builds and ends with a facts line (`wrote deck.pptx: 5 slides 16:9,
1 chart, 1 table, design: colors fonts sizes style footer; 5/5 slides carry choices, 0 warnings`) and a
`look:` line. 0 warnings and the counts your brief asks for = done: reply now, no render, re-open or other
command. A warning names the slide, line and fix: edit `deck.md` once, run `slidemark build deck.md -o deck.pptx`.
(No heredoc? Write `deck.md` and build it in the same turn.) To see slides: `--png sheet.png`.

## Decide first (decide and state; the choices are yours, none is the right one)

Before the heredoc, settle these in your reasoning, then write the choices into the deck:

1. **Deck frame:** colours, fonts, type scale, chrome (title band, cards, rules), `footer:` / `num:`, a `css`
   fence for what tokens cannot say. A `theme:` preset alone is a starting point, not a decision.
2. **Each slide:** its form (list, cards, `@steps`, grid, table, chart kind, KPI row, `@html`), its one
   emphasis (`.hero` `hl=` `==x==` `{.accent}`), and an override wherever the default would not serve that
   slide's message (`size=` `fill=` `color=` `align=` `x y w h`).
3. **Each chart and table:** series colours, labels, legend, the takeaway (`hl=` + `note=`), `widths=` `align=`
   `.zebra`.

Header lines and attributes are the written record (`build` echoes them in `design:`). Warnings `design-none`
(no `colors:` `fonts:` `sizes:` `style:`, no deck `css`) and `design-slide` (slides where no element carries a
choice) are advisory: clear them by stating the choice the hint names.

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
## Revenue {.kpi .hero}
$4.2M
+18% QoQ
## Churn {.kpi}
2.1%
-0.4 pt
## NPS {.kpi}
61
@end
- ==14 enterprise logos== signed, 3 in the last week

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
@steps num
## Oct {.accent}
- Hire 4 AEs
## Nov
- Launch partner tier
## Dec
- Renewal push

# Two asks
@free
{x=6% y=25% w=40% h=45% size=28 fill=primary color=#FFFFFF align=center valign=middle}
+$300k for partner marketing
{x=54% y=25% w=40% h=45% size=28 fill=accent color=#FFFFFF align=center valign=middle}
4 account executives

# Thank you
@html
```html
<div style="height:100%;background:linear-gradient(135deg,var(--primary),#000);color:#fff;padding:96px">
  <h1 style="font-size:72px;margin:0">Next review: January</h1>
  <p style="font-size:28px;color:var(--accent)">Questions to finance@example.com</p>
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
## 商談数 {.kpi .hero}
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
```bar {title="今期 受注額（億円）" colors=primary labels=on legend=none hl=西日本 note="西日本が最大の伸び"}
,東日本,西日本,海外
今期,2.1,1.7,0.3
```
````

Japanese: half-width digits, units in Japanese (`12.4億円`), one-line bullets (≈ 25 full-width chars per
column of a 3-column slide), `▲3` = −3 in tables. `jp-business` is already compact: `@dense` only on a slide
that is still too full.

## Syntax

**Header** (`key: value` lines before the first `#`): `theme` (`default` `midnight` `jp-business` `none`,
`./brand.yaml`, `template.pptx`), `lang` (`en` `ja` `vi` …), `title`, `footer`, `num: on`, `size` (`16:9`
default, `4:3`, `A4`), `density: dense`, and the design lines `colors:` `fonts:` `sizes:` `style:` (below).

**Slides.** `# Title` starts a slide. A title with only a `## subtitle` (or ≤ 2 short lines) is a cover
(first slide) or section divider (`@cover` / `@section` force it). `??? text` = speaker notes to the slide
end. `@hidden` hides a slide. `[go](#5)` links to slide 5.

**Blocks.** `## Heading` + its lines = a box; boxes arrange themselves (2 → 2 columns, 3 → 3, 4 → 2×2 or a
row, 5–6 → 3×2; text + one chart/table/image → side by side). `>` right after the title = key message (lead),
`>` last = conclusion bar, `※ text` = footnote. `@end` closes the last box: what follows (table, chart, list)
goes full width below. Each table/chart/image/code outside a box is its own block.

**`@` line** (only if the automatic layout is wrong; one per slide, tokens space separated):
`@3` columns · `@2x2` grid · `@1:2` ratios · `@aab/aac` areas (letters = blocks in order, `.` empty) ·
`chevron` steps (heading + 1–2 short bullets) · `steps` arrows, bullets in a card below (`steps num` adds a
"STEP n" caption) · `rows` a `1.` list alone as numbered bars · `flow` cards with arrows · `a>b` arrow, `a-b` line between blocks · `@dense` · `@build` click-to-reveal · `@t=fade` transition ·
`@bg=#0B1020` or `@bg="linear-gradient(135deg,#1A0B2E,#7A1FA2)"` background (dark flips text light; `@dark`
`@light` force it) · `@free` no automatic layout: blocks sit at their own `{x y w h}`.

**Attributes** `{.class key=value}` at the end of a heading or image, or alone on the line before a
block: `x y w h` (`%` `in` `cm` `pt`), `size`, `color`, `fill`, `align`, `valign`, `bold`, `icon=name`.
Classes: `.primary .accent .danger .success .muted` (colours), `.plain` (no card), `.kpi`, `.zebra` (table
rows), `.badge` (inline pill). On a heading, `size` `fill` `color` style the whole box.

**Inline:** `**b**` `*i*` `~~s~~` `` `code` `` `==accent==` `[text]{.danger}` `[済]{.badge .success}`
`[link](url)` `H~2~O` `x^2^`. Lists: `-` / `1.`, nest with two spaces; `- [ ] todo` `- [x] done`.

## Components

- **KPI card:** `## Label {.kpi icon=yen}` + value line + caption line; `{.kpi .hero}` = the lead metric,
  wider with a bigger number. Up to 4 in a row; `@end` + a list or table below them.
- **Callout:** `> [!note] text` (`tip` `warn` `caution`), at slide level or inside a box.
- **Icons:** `icon=` on a box heading: `check warning info user users building chart money yen target rocket
  lightbulb gear clock calendar globe shield cloud database truck leaf trophy flag` (a wrong name is fixed to
  the nearest), or `icon=logo.svg`.
- **Flowchart:** ` ```mermaid ` with `graph TD` / `graph LR`, `A[申請] --> B{承認?}`, `B -->|yes| C`.
- **Org chart:** `@.a./bcd a>b a>c a>d` then four `##` boxes.
- **Math:** ` ```math ` LaTeX → native equation. **Images:** `![what it shows](a.png)` (alt text required);
  `![alt](demo.mp4)` video/audio; ` ```svg ` inline SVG. Other fences are code.

## Tables and charts

Table: ` ```table ` fence with CSV (first row = header; quote cells with commas: `"1,240"`), or a GFM table.
Options on the fence or the line before: `{widths=3:1:1 align=lrr header=1 hcol=1 .zebra}` (one `align` letter
per column); `.gantt` draws filled period cells as bars; `hl=Metro,Kyoto` emphasises the rows whose first cell
matches. Merge: a lone `<` joins the cell to the left, `^` the cell above. Numbers align right by themselves.

Chart fence kinds: `column bar line area pie doughnut scatter radar stacked-column stacked-bar waterfall` (waterfall: one row, `=` cell = total). CSV body:
first row = categories (first cell empty), then one row per series (name first). Options: `title="..."`
`labels=on|percent|off` `legend=bottom|right|top|none` `fmt="0.0"|"#,##0"|"0%"` `min=` `max=`
`colors=primary,accent,#888888` (names from `colors:` work) `gap=80` `marker=9` `size=14` (exact)
`labels=outside|inside|above|below` `axis=off`; takeaway: `hl=Metro note="Metro: 40% of visits"` (`hl=` names a
category or a series). Numbers may be
`1,240`, `12%`, `▲3`; a decimal comma needs quotes (`"1,6"`). One value axis.

## Design tokens (header lines)

- `colors:` `bg fg primary accent surface border muted danger success` or any new name (`brand=#FF5A1F`).
  `primary` colours KPI numbers, badges, bars, charts and the title band.
- `fonts:` `heading body mono ea` (ea = Japanese/Chinese text).
- `sizes:` pt per role: `title heading body lead conclusion caption footnote table code cover-title`; a trailing
  `!` (`heading=20!`) pins the size against automatic growth.
- `style:` `radius=14` `gap=12pt` `padding=12pt` `shadow="0 6 18 #00000055"` `card.fill=#141A2E` (`none` =
  no card; a `linear-gradient(...)` works) `title.band=primary|none` `title.band.color=#FFFFFF`
  `heading.band=primary` `table.header.fill=primary` `table.header.color=#FFFFFF`
  `palette=primary,accent,#FF5A1F` (chart series) `h1.letter-spacing=2pt` (any `selector.css-property`)
  `hero.fill=#FF5A1F` (your own class, used as `## X {.hero}`). Chrome: `top.bar=primary` `title.rule=secondary` `kpi.stripe=secondary` `kpi.label.size=20` `kpi.note.color=teal` `bullet=■`
  `bullet.color=teal` `lead.bold=on` `heading.align=center` `footer.color=muted` `steps-arrow.fill=a,b`
  `rows-num.fill=a,b` `cover.bar=teal` `cover.band=none` `render.chart_grid=border`.
- A ` ```css ` fence (header = whole deck, in a slide = that slide) styles `slide h1 h2 p li .lead
  .conclusion .footnote .box .kpi table th td tr code img .chart` and your `{.class}`: colours, gradients,
  borders, radius, shadows, fonts, spacing, `text-transform`, `transform: rotate()`.
- `@html` + one ` ```html ` fence = a slide written in HTML/CSS, converted to editable shapes (`var(--primary)`
  reads your tokens).

## Rules

- One message per slide (the `>` lead); at most 4 boxes × 6 bullets and 8 table rows, else split the slide.
- Set a position or size only where you decided the default would not serve the slide; otherwise the layout fits text itself.
- Every image has alt text.
- Warnings: `overflow` (shorten or split), `contrast` (paste the colour from the hint), `missing-end` (add
  `@end`), `unknown-*` (follow the did-you-mean), `design-*` (state a choice). Fix only the named line.
