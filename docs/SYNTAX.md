# SlideMark syntax (v1)

Text inside slides is ordinary Markdown. The structure is SlideMark's own design, built so that an agent
writes almost no layout tokens:

- **Headings are the structure.** `#` starts a slide, `##` makes a box. Boxes are arranged automatically.
- **One `@` line overrides the layout** with a tiny grid notation (like CSS grid-template-areas).
- **Data is CSV**, inside fences named after what they produce (`bar`, `table`, ...).

There are no closing tags. Indentation carries no meaning except inside Markdown lists.

## Overview

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
- 顧客数 1,240社
## 課題
- 解約率が ==2.1%== に上昇
## 施策
1. オンボーディング刷新
2. CS体制の強化
※ 出所: 社内調査（2026年9月）
```

## Deck header

`key: value` lines at the very top of the file, before the first `#` or `---`. Every key is optional.

| Key | Values | Default |
|---|---|---|
| `theme` | `default`, `midnight`, `jp-business`, or a path to `.yaml`/`.potx`/`.pptx` | `default` |
| `size` | `16:9`, `4:3`, `A4`, `16:10`, `<w>x<h>` (e.g. `10inx7.5in`) | `16:9` |
| `lang` | `ja`, `vi`, `en`, ... (fonts, line breaking) | auto |
| `title`, `author` | text | first slide title |
| `footer` | text | none |
| `num` | `on` / `off`: slide numbers | `off` |
| `density` | `normal` / `dense` (smaller default type for packed slides) | `normal` |

A YAML front-matter block between `---` lines is accepted as well.

## Slides

- `# Title` starts a new slide. You do not need a separator.
- A line `---` starts a slide that has no title.
- Code fences are never parsed for structure, so a `#` comment inside code is safe.
- **Cover and section slides are automatic.** A slide with a title and at most two short lines of text is a cover
  (when it is the first slide) or a section divider. Those lines become the subtitle.
- `??? ` starts speaker notes. Everything after it until the next slide is notes.

## Blocks and boxes

Everything below the title is split into **blocks**:

| Source | Block |
|---|---|
| `## Heading` and the content under it | a **box** (card with a heading; style comes from the theme) |
| text and lists outside any box | a text block |
| an image, chart, table, code or diagram outside any box | a block of its own |

Three things are not blocks and have fixed places:

| Source | Position |
|---|---|
| `> text` right after the title | **lead**: the key message under the title |
| `> text` as the last thing on the slide | **conclusion**: a bar at the bottom |
| `※ text` or `^ text` | **footnote**: small text at the bottom (sources, notes) |

A `>` anywhere else is a quote.

`### Heading` inside a box is a sub-heading. It becomes a nested box only when the box has its own `@` line.

## Layout: `@` line

Without an `@` line, blocks are arranged automatically:

| Blocks | Arrangement |
|---|---|
| 1 | full width |
| 2 | two columns |
| 3 | three columns |
| 4 | 2×2, or 4 columns if the blocks are short |
| 5–6 | 3×2 |
| text + one visual | text on the left, visual on the right |

An `@` line (anywhere in the slide, usually right after the title) overrides this. Tokens are separated by spaces:

| Token | Meaning | Example |
|---|---|---|
| `N` | N equal columns | `@3` |
| `CxR` | grid with C columns and R rows | `@2x2` |
| `a:b:...` | column width ratios | `@1:2` (one third / two thirds) |
| `rows/rows` | **areas**: block 1 = `a`, block 2 = `b`, ... in source order; repeat a letter to span; `.` = empty | `@aab/aac` |
| `flow` | arrows between blocks in reading order (process diagrams) | `@4 flow` |
| `chevron` | blocks drawn as chevrons (steps) | `@4 chevron` |
| `cover` `section` `blank` `center` | force a slide type | `@section` |
| `key=value` | `bg=` color or image, `t=` transition (`fade`, `push`, ...), `id=`, `gap=` | `@bg=#0F172A t=fade` |
| `hidden` | hide the slide in the show | |
| any other word | class applied to the slide (`dense`, `dark`, ...) | `@3 dense` |

Inside a box, an `@` line lays out that box's `###` sub-boxes in the same way.

`@aab/aac` reads as two rows. In the first row, block `a` takes two columns and `b` one. In the second row, `a`
continues and `c` takes the last column. The result: a tall box on the left two-thirds and two stacked boxes on
the right.

## Attributes `{...}`

Use attributes only when the default is wrong. They follow Pandoc style: `{.class #id key=value key="two words"}`.

- At the end of a heading line: `## 課題 {.danger}`.
- At the end of an image: `![図](a.png){w=40%}`.
- On its own line directly before any other block: `{size=10}`.

Keys:

| Group | Keys |
|---|---|
| Position | `x y w h`, in `%` of the parent area, `in`, `cm`, `mm`, `pt`, `px`; a bare number is pt |
| Style | `size` (pt), `color`, `fill`, `line`, `align`, `valign`, `bold`, `radius`, `pad` |
| Image | `fit=contain` (default), `cover`, `stretch` |
| Classes | theme colors (`.primary`, `.accent`, `.danger`, `.success`, `.muted`), `.plain` (box without card), `.kpi` (big number box) |

## Inline text

Inline text is Markdown: `**bold**`, `*italic*`, `~~strike~~`, `` `code` ``, `[link](url)`, and `[go](#5)` to jump
to slide 5. Additions:

- `==text==` emphasizes in the theme accent color (for the key number).
- `[text]{.danger}` colors text.
- `H~2~O` is subscript and `x^2^` is superscript.

Lists use `-` and `1.`, nested with two spaces.

## Images

`![alt](path-or-url)`. Always write the alt text: it is used for accessibility and by `check`.

## Tables

Write a GFM table. To merge cells, put a lone `<` in a cell to merge it into the cell on its left, or a lone `^`
to merge it into the cell above.

```markdown
| 区分 | 4月 | 5月 |
|-|-|-|
| 売上 | 10 | 12 |
| 合計 | 22 | < |
```

A ` ```table ` fence takes CSV instead. Its first row is the header.

## Charts (native, editable)

Name the fence after the chart: `bar`, `column`, `stacked-bar`, `stacked-column`, `line`, `area`, `pie`,
`doughnut`, `scatter`, `radar`. The body is CSV. The first row holds the categories (its first cell is ignored),
and each following row is one series.

````markdown
```column {title="売上推移" legend=bottom}
,Q1,Q2,Q3
2025,10,12,15
2026,12,16,21
```
````

## Other fences

| Fence | Result |
|---|---|
| ` ```python ` or any other language | code with native syntax highlighting |
| ` ```mermaid ` | diagram |
| ` ```math ` | equation (LaTeX) |
| ` ```html ` | HTML/CSS rendered to native shapes, falling back to an image |
