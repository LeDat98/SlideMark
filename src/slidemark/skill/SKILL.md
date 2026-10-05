---
name: slidemark
description: Write PowerPoint decks as compact SlideMark text and build native, editable .pptx files. Use when asked for slides, a deck, or a presentation (.pptx), including dense Japanese business slides.
---

# SlideMark

This page is complete: everything you need is here, so do not look for other docs.

## Recipe: write and build in ONE command

```bash
slidemark build - -o deck.pptx --save deck.md <<'EOF'
# Title
...
EOF
```

`build` checks, fixes simple mistakes, builds, and ends with one facts line:
`wrote deck.pptx: 5 slides 16:9, 1 chart, 1 table, notes on 1 slide, 0 warnings`.
If it says 0 warnings and the counts match your brief, you are done: no render, no re-open, no other command.
A warning names the slide, the line and the fix: edit `deck.md` once, run `slidemark build deck.md -o
deck.pptx`. (No heredoc in your shell? Write `deck.md`, then build it, in the same turn.)

## Pattern 1: business deck (default look)

````markdown
title: Quarterly Business Review

# Quarterly Business Review
## Q3 2026 results and outlook

# Revenue grew 18% year over year
> Growth came from the enterprise segment
```table {align=lrrr}
Segment,Q3 2025,Q3 2026,Change
Enterprise,4.2,5.6,+33%
SMB,3.1,3.2,+3%
```
> Enterprise now drives two thirds of growth

# Three options
## Hire
- Add 6 agents
- Ready in 4 months
## Outsource
- Partner covers nights
## Automate
- AI answers top 30 questions
> We recommend Automate plus 2 hires

# Pipeline doubled since Q1
```column {title="Pipeline ($M)" labels=on legend=none}
,Q1,Q2,Q3
Pipeline,12,17,24
```
??? Pipeline counts qualified opportunities only.
````

## Pattern 2: dense Japanese business slides

````markdown
theme: jp-business
lang: ja
footer: ACME株式会社
num: on

# 中期経営計画 2027–2029
## 取締役会 説明資料

# 2029年の目標
> 売上と利益率を同時に高める
## 売上高 {.kpi}
1,500億円
2026年比 +30%
## 営業利益率 {.kpi}
12%
+4pt
## ROE {.kpi}
10%
+3pt
@end
- 既存事業は収益性を重視
- 新規事業に3年で200億円を投資

# 4つの重点施策
> 価格・海外・DX・人材の4本柱で実行する
## 価格改定
- 主力製品を平均5%改定
## 海外展開
- ベトナム工場の稼働
## DX推進
- 需要予測のAI化
## 人材
- 技術職を300名採用
※ 出所: 社内資料（2026年9月）

# 実行ロードマップ
@chevron
## 2027年 上期
- 体制構築
## 2027年 下期
- 価格改定
## 2028年
- 海外拠点稼働
````

Japanese: half-width digits, units in Japanese (`12.4億円`), one-line bullets (≈ 25 full-width chars per
column of a 3-column slide), `▲3` = −3 in tables, `density: dense` (deck) or `@dense` (slide) for packed slides.

## Pattern 3: brand colours and fonts

````markdown
theme: none
colors: bg=#0B1F3A fg=#FFFFFF primary=#FF6B57 accent=#FFB4A8 surface=#132B4F border=#24406B
fonts: heading="Montserrat" body="Open Sans"
lang: en

# Northwind Mobility
## Series B investor update

# Traction at a glance
## Riders {.kpi}
1.2M
+64% YoY
## Cities {.kpi}
14
+5 this year

# Revenue by year ($M)
```column {labels=on legend=none}
,2024,2025,2026
Revenue,7.8,15.2,26.0
```
````

Brand recipe: `colors:` + `fonts:` is enough; title, cards, tables, KPIs and charts follow those tokens. On a
dark `bg` also set `surface` (card fill) and `border`, and keep `fg` light. Text colours that fail contrast
are reported with a passing shade to paste.

## Syntax

**Header** (`key: value` lines before the first `#`): `theme` (`default` `midnight` `jp-business` `none`,
`./brand.yaml`, `template.pptx`), `lang` (`en` `ja` `vi` …), `title`, `footer`, `num: on`, `size` (`16:9`
default, `4:3`, `A4`), `density: dense`, and the design lines `colors:` `fonts:` `sizes:` `style:` (below).

**Slides.** `# Title` starts a slide. A title with only a `## subtitle` (or ≤ 2 short lines) is a cover
(first slide) or a section divider; `@cover` / `@section` force it. `??? text` = speaker notes (to the end of
the slide). `@hidden` hides a slide. `[go](#5)` jumps to slide 5.

**Blocks.** `## Heading` + its lines = a box; boxes arrange themselves (2 → 2 columns, 3 → 3, 4 → 2×2 or a
row, 5–6 → 3×2; text + one chart/table/image → side by side). Fixed places: `>` right after the title = key
message (lead), `>` last = conclusion bar, `※ text` = footnote. `@end` closes the last box: what follows
(table, chart, list) goes full width below the boxes. Each table/chart/image/code outside a box is its own block.

**`@` line** (only if the automatic layout is wrong; one per slide, tokens space separated):
`@3` columns · `@2x2` grid · `@1:2` ratios · `@aab/aac` areas (letters = blocks in order, `.` empty) ·
`chevron` steps (heading + 1–2 short bullets each) · `flow` cards with arrows · `a>b` arrow, `a-b` line
between blocks · `@dense` · `@build` click-to-reveal · `@t=fade` transition · `@bg=#0B1020` or
`@bg="linear-gradient(135deg,#1A0B2E,#7A1FA2)"` slide background (dark bg flips text light; `@dark`/`@light`
force it) · `@free` absolute positions only.

**Attributes** `{.class #id key=value}` at the end of a heading or image, or alone on the line before a
block: `x y w h` (`%` `in` `cm` `pt`), `size`, `color`, `fill`, `align`, `valign`, `bold`, `radius`,
`icon=name`. Classes: `.primary .accent .danger .success .muted` (colours), `.plain` (no card), `.kpi`,
`.zebra` (table rows), `.badge` (inline pill).

**Inline:** `**b**` `*i*` `~~s~~` `` `code` `` `==accent==` `[text]{.danger}` `[済]{.badge .success}`
`[link](url)` `H~2~O` `x^2^`. Lists: `-` / `1.`, nest with two spaces; `- [ ] todo` `- [x] done`.

## Components

- **KPI card:** `## Label {.kpi icon=yen}` + value line + caption line. Up to 4 in a row; `@end` + a list or
  table below them.
- **Callout:** `> [!note] text` (`tip` `warn` `caution`), at slide level or inside a box.
- **Icons:** `icon=` on any box heading: `check x warning info user users building factory chart money yen
  target rocket lightbulb gear clock calendar document mail phone globe lock shield cloud database search star
  heart truck cart leaf arrow-up arrow-down arrow-right trophy briefcase chat bolt flag key code`, or
  `icon=logo.svg`.
- **Flowchart:** ` ```mermaid ` with `graph TD` / `graph LR`, `A[申請] --> B{承認?}`, `B -->|yes| C`.
- **Org chart:** `@.a./bcd a>b a>c a>d` then `## 社長` `## 営業` `## 開発` `## 管理`.
- **Math:** ` ```math ` LaTeX → native equation. **Images:** `![what it shows](a.png)` (alt text required);
  `![alt](demo.mp4)` video/audio; ` ```svg ` inline SVG. Other fences are code.

## Tables and charts

Table: ` ```table ` fence with CSV (first row = header; quote cells with commas: `"1,240"`), or a GFM table.
Options on the fence or the line before: `{widths=3:1:1 align=lrr header=1 hcol=1 .zebra}`. Merge: a lone
`<` joins the cell to the left, `^` the cell above. Numeric columns align right by themselves. ≤ 8 rows.

Chart fence kinds: `column bar line area pie doughnut scatter radar stacked-column stacked-bar`. CSV body:
first row = categories (first cell empty), then one row per series (name first). Options: `title="..."`
`labels=on|percent|off` `legend=bottom|right|top|none` `fmt="0.0"|"#,##0"|"0%"` `min=` `max=`
`colors=primary,accent,#888888` `axis=off`. Numbers may be `1,240`, `12%`, `▲3`. One value axis per chart.

## Design tokens (header lines)

- `colors:` `bg fg primary accent surface border muted danger success` or any new name (`brand=#FF5A1F`).
  `primary` colours KPI numbers, badges, bars, charts and the title band.
- `fonts:` `heading body mono ea` (ea = Japanese/Chinese text).
- `sizes:` pt per role: `title heading body lead caption footnote table code cover-title`.
- `style:` `radius=14` `gap=12pt` `padding=12pt` `shadow="0 6 18 #00000055"` `card.fill=#141A2E` (`none` =
  no card) `card.fill="linear-gradient(135deg,#7C5CFF,#00D1B2)"` `title.band=primary|none`
  `title.band.color=#FFFFFF` `heading.band=primary` `table.header.fill=primary` `table.header.color=#FFFFFF`
  `palette=primary,accent,#FF5A1F` (chart series) `h1.letter-spacing=2pt` (any `selector.css-property`)
  `hero.fill=#FF5A1F` (own class, use `## X {.hero}`).
- A ` ```css ` fence (header = whole deck, in a slide = that slide) styles `slide h1 h2 p li .lead
  .conclusion .footnote .box .kpi table th td tr code img .chart` and your `{.class}`: colours, gradients,
  borders, radius, shadows, fonts, spacing, `text-transform`, `transform: rotate()`.
- `@html` under a title + one ` ```html ` fence = a slide designed in HTML/CSS, converted to editable
  shapes; `var(--primary)` reads your tokens.

## Rules

- One message per slide (the `>` lead); at most 4 boxes × 6 bullets and 8 table rows, else split the slide.
- Never set positions unless asked; the layout fits and sizes text by itself.
- Every image has alt text. Keep text colours readable on their fill.
- Warnings: `overflow` (shorten or split), `contrast` (paste the colour from the hint), `missing-end` (add
  `@end`), `unknown-*` (follow the did-you-mean). Fix only the named line.
