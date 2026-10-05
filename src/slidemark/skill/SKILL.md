---
name: slidemark
description: Write PowerPoint decks as compact SlideMark text and build native, editable .pptx files. Use when asked for slides, a deck, or a presentation (.pptx), including dense Japanese business slides.
---

# SlideMark

```bash
slidemark check deck.md     # warnings with hints; --fix repairs simple ones
slidemark review deck.md    # design critique + score
slidemark build deck.md -o deck.pptx
```

More: `slidemark docs syntax|design|components|charts-tables|jp-dense|icons|diagnostics`.

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

- Header: `theme` (`default` `midnight` `jp-business`, .pptx, `none`), `lang`, `footer`, `num: on`.
- Own design: `colors: primary=#7C5CFF bg=#0B1020`, `fonts: body="Inter"`, `style: radius=14 title.band=none`
  header lines, CSS or `@html` slides (`slidemark docs design`).
- `# Title` = slide; title + ≤ 2 short lines = cover or section divider.
- `## Heading` = box; boxes arrange themselves. `>` after the title = key message, `>` last = conclusion
  bar, `※` = footnote, `??? ` = speaker notes.
- `@end` closes the last box; a table/chart after it goes full width.

`@` line, only if the auto layout is wrong: `@3` columns, `@2x2`, `@1:2` ratios, `@aab/aac` areas,
`chevron` steps, `flow` arrows, `a>b` connectors (letters = blocks in order),
`@section`, `@dense`, `@build` (click to reveal), `@t=fade`. `@` after `@end` = new row of boxes.

Content:
- `**b**` `*i*` `==accent==` `[x]{.danger}` `[済]{.badge .success}` `[link](url)`.
- `## 売上 {.kpi icon=yen}` + `12.4億円` + caption line = KPI card; `icon=` on any box heading.
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

- Flowcharts: ` ```mermaid ` `graph TD` / `A[申請] --> B{承認?}` / `B -->|yes| C`.
- ` ```math ` LaTeX → native equation. `![alt](a.png)` images (always alt); `![alt](demo.mp4)` video/audio.
  Other fences = code. `[go](#5)` jumps to slide 5; `@hidden` hides a slide.

Rules: no positions; one message per slide (the `>` lead); ≤ 4 boxes × 6 bullets, tables ≤ 8 rows, else split; `check` to zero warnings.
