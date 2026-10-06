---
name: slidemark
description: Write PowerPoint decks as compact SlideMark text and build native, editable .pptx files. Use when asked for slides, a deck, or a presentation (.pptx), including dense Japanese business slides.
---

# SlideMark

This page is complete: do not look for other docs.

## Recipe: write and build in ONE command

```bash
slidemark build - -o deck.pptx --save deck.md <<'EOF'
# Title
...
EOF
```

`build` checks, fixes simple mistakes, builds and ends with a facts line (`wrote deck.pptx: 5 slides 16:9,
1 chart, 1 table, notes on 1 slide, 0 warnings`) and, for your own design, a `look:` line.
0 warnings and the counts your brief asks for = done: reply now, no render, re-open or other command.
A warning names the slide, line and fix: edit `deck.md` once, run `slidemark build deck.md -o deck.pptx`.
(No heredoc? Write `deck.md` and build it in the same turn.) To see slides: `--png sheet.png`, one image.

## Pattern 1: business deck (default look)

````markdown
title: Hiring Plan 2027

# Hiring Plan 2027
## Engineering leadership offsite

# Attrition fell to 9%
> Retention programs paid off in every team
```table {align=lrr}
Team,2025,2026
Platform,14%,8%
Mobile,11%,10%
```
> Keep the mentoring budget in 2027

# Where we hire
## Backend
- 6 senior engineers
- Remote first
## Data
- 3 analysts
## Design
- 2 product designers
> Start with backend in Q1

# Offer acceptance is rising
```line {title="Acceptance (%)" labels=on legend=bottom}
,Jan,Apr,Jul,Oct
2026,61,66,70,74
```
??? Mention the new referral bonus.
````

## Pattern 2: dense Japanese business slides

````markdown
theme: jp-business
lang: ja
footer: ACME株式会社
num: on

# 営業DXの進捗報告
## 営業企画部 定例会議

# 主要指標
> 商談化率が目標を上回った
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
- 失注理由の記録率は60%に留まる

# 課題と対策
> 入力負荷を下げ、記録率を90%に高める
## 入力負荷
- 1件あたり8分
## 項目過多
- 必須項目が24個
## 定着
- 研修は年1回のみ
## 対策
- 音声入力で自動記録
※ 出所: 営業部アンケート（2026年9月）

# 導入ステップ
@chevron
## 10月
- 試験導入
## 11月
- 全課展開
## 12月
- 効果測定
````

Japanese: half-width digits, units in Japanese (`12.4億円`), one-line bullets (≈ 25 full-width chars per
column of a 3-column slide), `▲3` = −3 in tables. `jp-business` is already compact: add `@dense` only to a slide
that is still too full, not `density: dense` for the whole deck.

## Pattern 3: brand colours and fonts

````markdown
theme: none
colors: bg=#101820 fg=#F2F2F2 primary=#FEE715 accent=#7FDBFF surface=#1B2733 border=#2E3F50
fonts: heading="Poppins" body="Source Sans 3"
lang: en

# Solar Roofs for Every Home
## Partner briefing

# Installs this year
## Homes {.kpi}
8,400
+40% YoY
## Saved per home {.kpi}
$1,150
per year

# Installs per quarter
```bar {labels=on legend=none}
,Q1,Q2,Q3
Installs,1600,2100,2600
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
(first slide) or section divider (`@cover` / `@section` force it). `??? text` = speaker notes to the slide
end. `@hidden` hides a slide. `[go](#5)` jumps to slide 5.

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

**Attributes** `{.class key=value}` at the end of a heading or image, or alone on the line before a
block: `x y w h` (`%` `in` `cm` `pt`), `size`, `color`, `fill`, `align`, `valign`, `bold`, `icon=name`. Classes: `.primary .accent .danger .success .muted` (colours), `.plain` (no card), `.kpi`,
`.zebra` (table rows), `.badge` (inline pill).

**Inline:** `**b**` `*i*` `~~s~~` `` `code` `` `==accent==` `[text]{.danger}` `[済]{.badge .success}`
`[link](url)` `H~2~O` `x^2^`. Lists: `-` / `1.`, nest with two spaces; `- [ ] todo` `- [x] done`.

## Components

- **KPI card:** `## Label {.kpi icon=yen}` + value line + caption line. Up to 4 in a row; `@end` + a list or
  table below them.
- **Callout:** `> [!note] text` (`tip` `warn` `caution`), at slide level or inside a box.
- **Icons:** `icon=` on a box heading: `check warning info user users building chart money yen target rocket
  lightbulb gear clock calendar document globe shield cloud database truck leaf trophy flag` (more exist; a
  wrong name is fixed to the nearest), or `icon=logo.svg`.
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
`colors=primary,accent,#888888` `axis=off`. Numbers may be `1,240`, `12%`, `▲3`; a decimal comma needs
quotes (`"1,6"`) or `;` rows (`T1;1,6;1,9`). Charts show numbers in the viewer's locale. One value axis.

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
- Every image has alt text.
- Warnings: `overflow` (shorten or split), `contrast` (paste the colour from the hint), `missing-end` (add
  `@end`), `unknown-*` (follow the did-you-mean). Fix only the named line.
