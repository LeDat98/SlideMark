---
name: slidemark
description: Write PowerPoint decks as compact SlideMark text and build native, editable .pptx files. Use when asked for slides, a deck, or a presentation (.pptx), including dense Japanese business slides.
---

# SlideMark

Write a `.md` file in SlideMark syntax, then run:

```bash
slidemark check deck.md          # one diagnostic per line: "warning slide 2 L14 rule: message -> hint"
slidemark build deck.md -o deck.pptx
slidemark preview deck.pptx      # PNGs per slide (needs LibreOffice), look at them
```

Fix only what `check` reports, on the slide and line it names. More: `slidemark docs <topic>` with topic
`syntax`, `components`, `charts-tables`, `jp-dense`, `diagnostics`.

## Core syntax

```markdown
theme: jp-business
lang: ja
footer: ACME株式会社
num: on

# 新規事業の検討状況
> 3つの課題を解決し、来期の黒字化を目指す
@aab/aac
## 現状
- 売上 12億円（前年比 +8%）
## 課題
- 解約率が ==2.1%== に上昇
## 施策
1. オンボーディング刷新
※ 出所: 社内調査（2026年9月）
```

- Header lines `key: value` before the first `#` (all optional): `theme` (`default`, `midnight`,
  `jp-business`, or a .pptx/.potx template path), `lang` (`ja` sets Japanese fonts and line breaking), `size` (`16:9`, `4:3`, `A4`), `footer`, `num: on`, `density: dense`.
- Cover: `# Deck title` + one subtitle line (+ an optional date line) as the first slide. `# Title` starts a slide. A title with ≤ 2 short lines and nothing else becomes a cover (first slide) or a
  section divider; force it with `@cover` / `@section`.
- `## Heading` makes a box. Boxes are arranged automatically (2 → columns, 3 → columns, 4 → 2×2, …).
- `>` right after the title = lead message; `>` as the last line = conclusion bar; `※ text` = footnote.
- `??? ` starts speaker notes.
- `@end` closes the current box, so a following table/chart belongs to the slide (full-width row below).
  An `@` line after `@end` starts a new row group (e.g. a `@2 flow` row, `@end`, then a `@2` row of KPI boxes).

## Layout: one `@` line

| Token | Meaning |
|---|---|
| `@3` / `@2x2` / `@1:2` | 3 columns / grid / column ratios |
| `@aab/aac` | areas: block 1 = `a` (spans two columns, two rows), `b`, `c` stacked right |
| `@4 chevron` / `@3 flow` | step chevrons / arrows between blocks |
| `@3 a>b b>c` | connectors between blocks (letters = blocks in order; `a-b` = plain line) |
| `@section` `@cover` `@center` `@blank` | force a slide type |
| `@dense` | smaller type for one packed slide |
| `@build` / `@t=fade` / `@hidden` | bullets appear on click / transition / hidden slide |

Blocks beyond the grid's cells are stacked full width below it.

## Content

- Inline: `**bold**`, `*italic*`, `==key number==` (accent), `[text]{.danger}`, `[済]{.badge .success}`,
  `H~2~O`, `x^2^`, `[link](url)`, `[go](#5)`.
- KPI box: `## 売上 {.kpi}` then `12.4億円` then a caption line.
- Callout: `> [!note] text` (`tip`, `warn`, `caution`), anywhere a block can go.
- Table: GFM; a lone `<` merges into the left cell, `^` into the cell above. `{widths=3:1:1 align=lrr}` on the line before.
- Chart: a fence named `bar column line pie doughnut area scatter radar stacked-bar stacked-column`, CSV body:

````markdown
```column {title="売上推移" labels=on fmt="#,##0"}
,Q1,Q2,Q3
2025,10,12,15
2026,12,16,21
```
````

- Image: `![alt text](path.png){w=40% fit=cover}` (always write alt).
- Flowchart with branches or loops: a ` ```mermaid ` fence (`graph TD` or `graph LR`, `A[text] --> B{question?}`,
  `B -->|yes| C`) → native boxes, diamonds and connectors. Use `@3 flow` only for a straight sequence.
- ` ```math ` LaTeX (`\frac`, `\sqrt`, `\sum`, `^`, `_`, `\left( \right)`) → native equation, also inside a box;
  other fences → highlighted code.
- Attributes `{.class #id key=value}` at the end of a heading or on their own line before a block. Positions
  `{x y w h}` exist but avoid them: the layout engine places everything.

## Rules that save retries

1. Do not write positions or font sizes; let the theme decide. Use `@` only when the automatic layout is wrong.
2. One message per slide; put it in the lead `>` line. Put sources in `※` footnotes.
3. Dense slides: ≤ 4 boxes, ≤ 6 bullets per box, tables ≤ 8 rows; split instead of shrinking.
4. Close a row of boxes with `@end` before a slide-level table or chart.
5. Run `check` before `build`; zero warnings is the goal.
