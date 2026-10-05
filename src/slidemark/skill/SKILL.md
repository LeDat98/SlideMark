---
name: slidemark
description: Write PowerPoint decks as compact SlideMark text and build native, editable .pptx files. Use when asked for slides, a deck, or a presentation (.pptx), including dense Japanese business slides.
---

# SlideMark

```bash
slidemark check deck.md     # "warning slide 2 L14 rule: message -> hint"; fix only what it names
slidemark build deck.md -o deck.pptx
```

More: `slidemark docs syntax|components|charts-tables|jp-dense|icons|diagnostics`.

```markdown
theme: jp-business
lang: ja
footer: ACME株式会社
num: on

# 新規事業の検討状況
> 3つの課題を解決し、来期の黒字化を目指す
## 現状
- 売上 12億円（前年比 +8%）
## 課題
- 解約率が ==2.1%== に上昇
## 施策
1. オンボーディング刷新
※ 出所: 社内調査（2026年9月）
```

- Header (optional): `theme` (`default` `midnight` `jp-business` or a .pptx path), `lang`, `footer`, `num: on`.
- `# Title` = slide. First slide with title + 1–2 short lines = cover; later ones = section dividers.
- `## Heading` = box; boxes arrange themselves. `>` after the title = key message, `>` last = conclusion
  bar, `※` = footnote, `??? ` = speaker notes. Each line is its own line.
- `@end` closes the last box: a following table/chart/callout goes full width below the boxes.

`@` line, only when the automatic layout is wrong: `@3` columns, `@2x2`, `@1:2` ratios, `@aab/aac` areas
(big left box + two stacked), `chevron` steps, `flow` arrows, `a>b` connectors (letters = blocks in order),
`@section`, `@dense`, `@build` (click to reveal), `@t=fade`. An `@` line after `@end` starts a new row of boxes.

Content:
- `**b**` `*i*` `==accent==` `[x]{.danger}` `[済]{.badge .success}` `[link](url)`; lists `-` / `1.`.
- `## 売上 {.kpi icon=yen}` + `12.4億円` + caption line = KPI card. `icon=` on any box heading: check x warning
  info user users building factory chart money yen target rocket lightbulb gear clock calendar document mail
  phone globe lock shield cloud database search star heart truck cart leaf arrow-up arrow-down arrow-right.
- `> [!warn] text` callout (`note` `tip` `warn` `caution`).
- GFM table; a lone `<` merges left, `^` merges up; `{align=lrr}` on the line before.
- Chart fence (`column bar line pie doughnut area scatter radar stacked-column stacked-bar`), CSV: first row =
  categories, one row per series; options `title legend=bottom|none labels=on|percent fmt="0%"`:

````markdown
```column {title="売上（億円）" labels=on}
,Q1,Q2,Q3
2025,10,12,15
```
````

- Branches/loops: ` ```mermaid ` `graph TD` / `A[申請] --> B{承認?}` / `B -->|yes| C` → native shapes.
- ` ```math ` LaTeX → native equation. `![alt](a.png)` images (always alt). Other fences = code.

Rules: no positions or font sizes; table emphasis = `**bold**`/`==x==` in cells; one message per slide (the
`>` lead); ≤ 4 boxes × 6 bullets, tables ≤ 8 rows, else split; `check` until zero warnings.
