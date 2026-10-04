# SlideMark syntax (v0)

Markdown (CommonMark + GFM tables) with a few additions. Everything is optional: plain Markdown already
produces a good deck. Write the shortest form; only add attributes when the default is wrong.

## Deck and slides

```markdown
---
title: Q3 Review          # all keys optional
theme: default
size: 16:9                # 16:9 | 4:3 | A4 | 16:10 | <w>x<h> e.g. 10inx7.5in
lang: ja                  # ja | vi | en ... (CJK fonts, line breaking)
footer: ACME Corp
slide-number: true
---

# First slide title
```

- A line containing only `---` separates slides (it is never a horizontal rule).
- Per-slide options: a YAML block right after the separator, closed by another `---`:

```markdown
---
layout: two-column
bg: "#0F172A"
---
```

  Keys: `layout`, `bg` (alias `background`), `transition`, `class`, `id`, `hidden`. Unknown keys go to `slide.attrs`.
  Marp-style `<!-- layout: two-column -->` comments are also accepted.
- Speaker notes: a line `???`; everything after it in the slide is notes.

## Titles and text

- The first heading of a slide (`#` or `##`) is the slide title.
- A heading right after the title is the subtitle.
- Other headings (`###`...) are section headings inside the slide.
- A slide containing only a title (and subtitle) becomes a cover slide (first slide) or a section slide.
- `>` right after the title is the **lead** (key message under the title). Other `>` blocks are quotes.
- A paragraph starting with `※` or `^ ` is a footnote (placed at the bottom of the slide, small text).
- Inline: `**bold**`, `*italic*`, `~~strike~~`, `` `code` ``, `[link](url)`, `[link](#3)` (jump to slide 3),
  `[text]{.primary}` (color by theme color name or class), `==highlight==`, `H~2~O`, `x^2^`.
- Lists: `-` / `1.`, nest with 2 spaces.

## Attributes `{...}`

Pandoc style: `{#id .class key=value key="two words"}`.

- After a heading or an image on the same line: `## Title {.dense}`, `![](a.png){w=40%}`.
- On its own line directly **before** a block (paragraph, list, table, code): `{.card w=50%}`.
- Position and size: `x y w h`, in `%` of the parent, `in`, `cm`, `mm`, `pt`, `px` (bare number = pt).
- Style: `size` (font pt), `color`, `fill`, `line`, `align`, `valign`, `bold`, `italic`, `radius`, `padding`.
- Theme classes: `.card`, `.callout`, `.muted`, `.dense`, plus theme color names (`.primary`, `.danger`, ...).

## Containers `:::`

```markdown
::: left
- text on the left
:::

::: right
![](chart.png)
:::
```

- `::: <name> [args] [{attrs}]` ... `:::` groups blocks. Nest by using more colons for the outer block (`::::`).
- Region names used by layouts: `left`, `right`, `main`, `side`, `top`, `bottom`.
- `::: row` lays out children horizontally; `::: grid 3` makes a 3-column grid.
- Any other name is applied as a class: `::: card`, `::: callout`.
- `::: shape chevron` is an auto shape whose content is its text (`rect`, `rounded-rect`, `ellipse`,
  `arrow-right`, `chevron`, `pentagon`, ...).

## Images

`![alt](path-or-url){w=40% fit=cover}`. `fit`: `contain` (default), `cover`, `stretch`.
Always write the alt text: it is used for accessibility and by `check`.

## Tables

GFM tables. In a cell, `<` alone merges it into the cell on the left, `^` alone merges it into the cell above.

```markdown
| Region | Q1  | Q2 |
|--------|-----|----|
| APAC   | 10  | 12 |
| Total  | 22  | <  |
```

A ` ```table ` (or ` ```csv `) fence takes CSV instead; the first row is the header.

## Charts (native, editable)

Fence language = chart kind: `bar`, `column`, `stacked-bar`, `stacked-column`, `line`, `area`, `pie`,
`doughnut`, `scatter`, `radar`. Body is CSV: first row = categories (first cell ignored), then one row per series.

````markdown
```column {title="Revenue" legend=bottom}
,Q1,Q2,Q3
2025,10,12,15
2026,12,16,21
```
````

## Code and other fences

- ` ```python ` etc.: code block with native syntax highlighting.
- ` ```mermaid `, ` ```math `, ` ```html `: diagram, equation, HTML (rendered in a later version).

## Layouts

Usually inferred from content; set `layout:` only to override.

| Layout | Inferred when |
|---|---|
| `cover` | first slide with only a title/subtitle |
| `section` | other slides with only a title/subtitle |
| `two-column` | `::: left` / `::: right` regions, or text plus one chart/image |
| `content` | everything else: blocks stacked top to bottom |
| `blank` | never inferred: no title area |
