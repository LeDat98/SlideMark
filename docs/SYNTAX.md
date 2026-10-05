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
| `theme` | a preset (`default`, `midnight`, `jp-business`), `none` (bare schema defaults), or a path to `.yaml`/`.potx`/`.pptx` | `default` |
| `size` | `16:9`, `4:3`, `A4`, `16:10`, `<w>x<h>` (e.g. `10inx7.5in`) | `16:9` |
| `lang` | `ja`, `vi`, `en`, ... (fonts, line breaking) | auto |
| `title`, `author` | text | first slide title |
| `footer` | text | none |
| `num` | `on` / `off`: slide numbers | `off` |
| `density` | `normal` / `dense` (smaller default type for packed slides) | `normal` |
| `sections` | `on` / `off`: section slides start PowerPoint sections named after their title | `on` |

| `colors`, `fonts`, `sizes`, `style` | design tokens as `key=value` pairs (below) | from the theme |

A YAML front-matter block between `---` lines is accepted as well.

### Design tokens

Every visual decision is a token (`slidemark tokens` prints all of them with their values). Built-in themes
are presets written in the same schema (`src/slidemark/presets/*.yaml`); a deck extends one and overrides any
token inline. Values are colors (`#RRGGBB`, `#RRGGBBAA` or a color name), numbers, lengths (`12pt`, `0.3in`,
bare numbers = pt), `none`, or quoted text.

```markdown
theme: none
colors: bg=#0B1020 fg=#E6E8EF primary=#7C5CFF accent=#00D1B2 muted=#8A90A6
fonts: heading="Inter" body="Noto Sans JP" mono="JetBrains Mono"
sizes: title=40 body=16 caption=11
style: radius=14 gap=20 card.fill=#141A2E card.shadow="0 8 24 #00000055" title.band=none
```

| Line | Keys |
|---|---|
| `colors:` | any color name; new names (`brand=#FF5A1F`) are usable everywhere a color is |
| `fonts:` | `heading`, `body`, `mono`, `ea` (East Asian) |
| `sizes:` | text roles: `title`, `subtitle`, `heading`, `body`, `lead`, `quote`, `caption`, `footnote`, `code`, `table`, `cover-title`, `cover-subtitle` (pt) |
| `style:` | any other token: theme fields (`gap`, `margin_x`, `title.band`, `heading.band`, `table.header.fill`, `palette=primary,#FF5A1F`), `<class>.<field>` styles (`card.fill`, `card.shadow`, `kpi.color`; a new class name such as `hero.fill` creates the class for `{.hero}`), `layout.<x>` and `render.<x>` constants, and the shortcuts `radius`, `padding`, `shadow`, `border`, `border-width`, `card` (all for `card`), `bg`, `fg`, `margin`; element styles without a CSS fence: `<element>.<css-property>` (`h1.letter-spacing=2pt`, `h1.text-transform=uppercase`, `th.background=#123456`, `box.border-radius=14`; elements `slide h1 h2 p li table th td code img`, classes `lead conclusion footnote subtitle box kpi chart`) become deck-level CSS rules placed before header css fences; Theme fields and class tokens (`card.fill`, `title.band`) keep their meaning |

Class style fields: `fill` (a color or `linear-gradient(...)`/`radial-gradient(...)`), `line`, `line_width`,
`radius`, `padding`, `shadow` (`"x y blur [spread] color"` in pt), `opacity`, `color`, `font`, `font_size`,
`bold`, `italic`, `align`, `valign`, `line_spacing`. An unknown key gives a did-you-mean hint; a bad value is
skipped with a `bad-token` warning. A theme file is the same tokens as YAML (`colors: {primary: "#7C5CFF"}`,
`classes: {card: {radius: 14}}`), extends `default` unless it sets `extends: none` or another preset.

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

`@end` on its own line closes the current `##` box: what follows belongs to the slide again (a table under a
row of chevron boxes). Without it a box runs to the end of the slide; `check` hints when the last box holds a
table, chart or callout that its siblings do not. A `>` that ends the slide is the conclusion even without
`@end`.

**Row groups.** An `@` line after `@end` starts a new row group with its own grid: the boxes of each group
are laid out by that group's `@` line, and the groups are stacked top to bottom (each takes its natural height,
the rest of the body is shared).

```markdown
@2 flow
## 現状
- 手作業が多い
## 改善後
- 自動化
@end
@2
## 工数 {.kpi}
-40%
## ミス {.kpi}
-70%
```

Blocks beyond the cells of the slide grid (for example a table after `@end` under `@4 chevron`, or a fourth
block under `@aab/aac`) are stacked **full width below the grid**, each in its own row.

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
| `free` | absolute positioning: every block with `{x= y= w= h=}` (% of the area under the title, or lengths) sits exactly there, with no growth, balance or search; unplaced blocks stack on top (info `free-unplaced`) | `{x=10% y=30% w=40% h=20%}` |
| `key=value` | `bg=` color or image, `t=` transition (`fade`, `push`, `wipe`, `split`, `cover`, `zoom`, `morph`; `t=fade:0.5` sets seconds), `id=`, `gap=` | `@bg=#0F172A t=fade` |
| `a>b` `a-b` | **connector** from block `a` to block `b` (arrow / plain line). Letters count blocks in source order (`a` = 1st), digits work too (`1>3`). With `flow`, the links replace the flow arrows (info `flow-links`) | `@3 a>b a>c` |
| `hidden` | hide the slide in the show | |
| `build` | bullets and blocks appear one by one on click (`{.build}` on one block does it for that block only) | `@build` |
| any other word | class applied to the slide (`dense`, `dark`, ...) | `@3 dense` |

Inside a box, an `@` line lays out that box's `###` sub-boxes in the same way. An `@` line after the last box of a slide
whose box has no `###` sub-boxes applies to the slide (info `at-hoisted`).

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

## Components

**KPI box.** A box with `.kpi` shows its first line as a big number and the rest as a small caption; the
heading is the label.

```markdown
## 売上 {.kpi}
12.4億円
前年比 +8%
```

**Callout.** A quote whose first word is `[!note]`, `[!tip]`, `[!warn]` or `[!caution]` is a callout box (tinted,
colored border). It works anywhere a block can go, including inside a box, and is never a lead or conclusion.
`[!warning]` = `[!warn]`, `[!important]` = `[!note]`.

```markdown
> [!warn] 価格改定は11月から
```

**Icon.** `icon=name` on a box heading draws a native, recolorable vector icon next to the heading (above
the number in a `.kpi` box): `## 売上 {.kpi icon=chart}`. `slidemark docs icons` lists the names (check, x,
warning, info, user, users, building, factory, chart, money, yen, target, rocket, lightbulb, gear, clock,
calendar, document, mail, phone, globe, lock, shield, cloud, database, search, star, heart, truck, cart, leaf,
arrow-up, arrow-down, arrow-right). An unknown name is a warning with a did-you-mean hint.

**Badge.** `[text]{.badge}` is a small filled label inside text; add a color class to change it:
`[済]{.badge .success}`, `[NEW]{.badge .danger}`.

## Inline text

Each source line of plain text is its own line on the slide (no Markdown soft-break merging); a line right
under a list item still continues that item.

Inline text is Markdown: `**bold**`, `*italic*`, `~~strike~~`, `` `code` ``, `[link](url)`, and `[go](#5)` to jump
to slide 5. Additions:

- `==text==` emphasizes in the theme accent color (for the key number).
- `[text]{.danger}` colors text.
- `H~2~O` is subscript and `x^2^` is superscript.

Lists use `-` and `1.`, nested with two spaces.

## Images

`![alt](path-or-url)`. Always write the alt text: it is used for accessibility and by `check`.

SVG: `![logo](logo.svg)` or a ` ```svg ` fence with inline source (`{alt=...}` or `<title>` gives the alt text). It is
embedded as a native Office SVG picture with a PNG fallback; scripts, `on*` attributes, `<foreignObject>` and
external links are stripped.

### Video and audio

The same syntax with a media file embeds native, playable media: `![demo](demo.mp4)`. Video: `.mp4 .m4v .mov
.wmv .avi .webm`; audio: `.mp3 .m4a .wav .aac .wma`. Attributes: `{poster=frame.png autoplay loop}`. Without a
poster a neutral frame with a play icon is shown. A missing file becomes a placeholder and a diagnostic.

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

Chart options go in the fence attributes:

| Key | Values | Default |
|---|---|---|
| `title` | text | none |
| `legend` | `bottom`, `right`, `top`, `left`, `none` | `bottom` when >1 series, else `none` |
| `labels` | `on` (values), `percent` (pie/doughnut), `off` | `off` |
| `fmt` | Excel number format for labels and the value axis, e.g. `0.0`, `#,##0`, `0%` | general |
| `min`, `max` | value axis bounds | auto |
| `colors` | comma list of theme names or hex, one per series (per point for pie) | theme palette |
| `axis` | `off` hides the value axis and gridlines | `on` |

CSV cells may be quoted (`"1,240"`), may carry `%` or thousands separators (`1,240`, `12%` → number), and may
use full-width digits; an empty cell is a gap. A cell that is not a number becomes a gap plus a warning.

## Table options

Attributes on a table (`{...}` on the line before a GFM table, or on a `table` fence):

| Key | Meaning | Example |
|---|---|---|
| `widths` | column width ratios | `widths=3:1:1:1` |
| `align` | per-column alignment letters `l` `c` `r` | `align=lcrr` |
| `header` | number of header rows (0 = none) | `header=2` |
| `hcol` | number of header columns | `hcol=1` |
| `.zebra` | alternate row fill | |

Numeric columns are right-aligned automatically.

## CSS fence

A ` ```css ` fence styles SlideMark elements with CSS. In the deck header (before the first `#`) it applies to
every slide; inside a slide it applies to that slide only. It is never drawn.

````markdown
```css
h1 { color: #7C5CFF; letter-spacing: 1pt; text-transform: uppercase }
.box { background: linear-gradient(135deg, #141A2E, #1E2540); border-radius: 14px; box-shadow: 0 8px 24px #0006 }
.box > h2 { color: #00D1B2; border-bottom: 2px solid #00D1B2 }
tr:nth-child(even) td { background: #F6F7FB }
.hero { background: #FF5A1F; color: white; transform: rotate(-2deg) }
```
````

Selectors: `slide`, `slide.cover`, `slide.section`, `h1` (slide title), `h2` (box heading), `p`/`li` (body
text), `.lead`, `.conclusion`, `.footnote`, `.subtitle`, `.box` (any `##` box), `.kpi`, `.chevron`, `.callout`,
`table`, `tr`, `th`, `td`, `code`, `img`, `.chart`, and any `{.class}` / `{#id}`; combined with descendant
(` `) and child (`>`) combinators, `:nth-child(even|odd|N)`, `:first-child`, `:last-child`. Comma lists are
split. Later rules and higher specificity win; inline `{}` attributes win over CSS.

| Group | Properties (mapped to native PowerPoint) |
|---|---|
| Color and fill | `color`, `background`, `background-color` (color, `linear-gradient`, `radial-gradient`, `url()`) |
| Border | `border`, `border-top/right/bottom/left`, `border-color`, `border-width`, `border-style`, `border-radius` |
| Effects | `box-shadow`, `opacity` |
| Font | `font-family`, `font-size`, `font-weight`, `font-style` |
| Text | `letter-spacing`, `line-height`, `text-align`, `vertical-align`, `text-transform`, `text-decoration` |
| Box | `padding` (1–4 values), `padding-top/right/bottom/left`, `margin`, `gap` |
| Grid | `grid-template-columns` (`1fr 2fr` → `@1:2`, `repeat(3, 1fr)` → `@3`), `grid-template-areas` |
| Transform | `transform: rotate(<deg>)` |

Units: `px` (= 0.75 pt), `pt`, `em` (× the element's font size), `%` for opacity. Colors: hex (`#RGB`,
`#RGBA`, `#RRGGBB`, `#RRGGBBAA`), `rgb()/rgba()`, CSS named colors, theme names (`primary`) and
`var(--primary)`. Any other property, selector or value gives a one-line diagnostic and is never silently
dropped.

## HTML slides

`@html` on a slide makes the whole slide HTML: write the slide's HTML (with `<style>` if you like) in one
` ```html ` fence under the title. Chromium lays it out at the slide size (1280×720 px for 16:9) and SlideMark
converts it to native, editable shapes (text, rectangles, gradients, shadows, borders, tables, lists, inline
SVG); only what PowerPoint cannot draw becomes a picture, with a diagnostic naming the element.

````markdown
# Launch
@html
```html
<div style="height:100%;background:linear-gradient(135deg,var(--primary),var(--accent));color:#fff;padding:96px">
  <h1 style="font-size:72px;margin:0">Meet Aurora</h1>
</div>
```
````

`slidemark build deck.html` builds a whole HTML deck: one `<section>` per slide, a shared `<style>` in
`<head>`. A section made of headings, lists, tables, cards and grid/flex tracks becomes normal SlideMark
elements; a section with an `<svg>`, or background/border/padding/shadow/transform/position styles (inline or
from `<style>`), is laid out by Chromium as a whole-slide HTML slide. `data-render="html"` on a section or
`<html data-slidemark="native">` forces that for one slide or all. Theme tokens are CSS custom properties in every HTML slide (`var(--primary)`, `var(--font-body)`,
`var(--size-body)`), so HTML slides and SlideMark slides of one deck share one design.

## Other fences

| Fence | Result |
|---|---|
| ` ```python ` or any other language | code with native syntax highlighting |
| ` ```mermaid ` | diagram |
| ` ```math ` | native, editable equation (LaTeX subset: `\frac`, `^`, `_`, `\sqrt`, `\sum`, `\int`, Greek, `\times`, ...) |
| ` ```html ` | HTML/CSS: structural subset, else laid out by Chromium into native shapes/text (CSS grid, flex, cards), else an image; `{render=native\|image}` forces one (canvas, svg, gradients, transforms stay images) |
