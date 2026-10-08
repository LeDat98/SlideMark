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
| `fit` | `on` / `off`: the per-slide fit lines of `slidemark build` (below; `--quiet` does the same for one run) | `on` |

| `colors`, `fonts`, `sizes`, `style` | design tokens as `key=value` pairs (below) | from the theme |

A YAML front-matter block between `---` lines is accepted as well.

### Design tokens

Every visual decision is a token (`slidemark tokens` prints all of them with their values). A deck that sets `bg`/`fg` but not `muted` gets a readable muted color mixed from them when the preset grey would fail contrast. Built-in themes
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
| `style:` | any other token: theme fields (`gap`, `margin_x`, `title.band`, `heading.band`, `table.header.fill`, `palette=primary,#FF5A1F`), `<class>.<field>` styles (`card.fill`, `card.shadow`, `kpi.color`; a new class name such as `hero.fill` creates the class for `{.hero}`), `layout.<x>` and `render.<x>` constants, and the shortcuts `radius`, `padding`, `shadow`, `border`, `border-width`, `card` (all for `card`), `bg`, `fg`, `margin`; element styles without a CSS fence: `<element>.<css-property>` (`h1.letter-spacing=2pt`, `h1.text-transform=uppercase`, `th.background=#123456`, `box.border-radius=14`, any property of the CSS fence; aliases `title`=h1, `heading`=h2, `body`=p and `weight`, `size`, `font`, `bold=on`, `italic=on`: `title.weight=bold` = `h1.font-weight=bold`; elements `slide h1 h2 p li table th td code img`, classes `lead conclusion footnote subtitle box kpi chart`) become deck-level CSS rules placed before header css fences; Theme fields and class tokens (`card.fill`, `title.band`) keep their meaning |

Class style fields: `fill` (a color or `linear-gradient(...)`/`radial-gradient(...)`), `line`, `line_width`,
`radius`, `padding`, `shadow` (`"x y blur [spread] color"` in pt), `opacity`, `color`, `font`, `font_size`,
`bold`, `italic`, `align`, `valign`, `line_spacing`. An unknown key gives a did-you-mean hint; a bad value is
skipped with a `bad-token` warning. A theme file is the same tokens as YAML (`colors: {primary: "#7C5CFF"}`,
`classes: {card: {radius: 14}}`), extends `default` unless it sets `extends: none` or another preset.

**Slide chrome and element tokens** (one `style:` line each, no CSS fence; the python-pptx frame in one line):

```markdown
style: top.bar=primary top.bar_h=0.12in title.rule=secondary kpi.stripe=secondary bullet=■ bullet.color=teal
```

| Token | Draws |
|---|---|
| `top.bar=<color>` `top.bar_h=0.1in` | a full-width strip on the top edge of every slide but the cover (`bottom.bar` / `bottom.bar_h`: the bottom edge) |
| `title.rule=<color>` `title.rule_h=2pt` | a rule on the bottom edge of the slide title |
| `title.rule2=<color>` `title.rule2_w=1.6in` | a second, short segment of the title rule's height on its left end (an accent over the rule) |
| `heading.wrap=on` | card headings may wrap. Default `off`: in a row or grid of cards (`@3` `@4` `@2x2` `@4 num` `@steps` `@items`) a `##` heading that would wrap shrinks, with its siblings (one size for the group), to one line, down to the card body size; when even that wraps, every heading keeps its size and wraps. The number badge / icon disc width counts. A pinned heading size (`sizes: heading=20!`, `h2.size=`, a `[x]{size=}` span) keeps the row. The sparse growth gives up a step that would wrap a heading |
| `heading.rule=<color>` `heading.rule_h=2pt` | a rule under every `##` box heading (on the lower edge of the band with `heading.band`); not on `###`, KPI cards or item cards |
| `icon.disc=<color>` `icon.disc.size=0.7in` `icon.disc.shape=circle` `icon.color=<c>` | every `icon=` (box heading, `.kpi` card, `@iconlist` item, `@steps` / chevron arrow) sits centred on a native filled disc named `Icon disc` (`circle`, `rounded` or `square`; `none` = the bare glyph, the default). Diameter: `icon.disc.size`, else `layout.icon_disc_ratio` (2.2) x the glyph side; the glyph is `layout.icon_disc_glyph` (0.46) of it, in `icon.color` or an ink that reads on the disc (white on dark, the text colour on light). The heading text starts after the disc. `{icon=bolt disc=accent}` on one heading (or `- icon=bolt disc=accent **Title** text` in `@iconlist`) sets that disc, `disc=none` takes it away |
| `card.elevation=0\|1\|2\|3` | one word for the card shadow: `0` none, `1` = `0 1 4 #0000001F`, `2` = `0 3 12 #00000030` (the soft pptxgenjs look), `3` = `0 8 24 #00000040`; it sets `card.shadow`, so it reaches boxes, `.kpi` cards, `@items`, `@steps` cards and `@iconlist fill=` cards (`rows.shadow=` for `@rows` bars). A card with a shadow and no border of its own is drawn WITHOUT a line (a line flattens the shadow): `card.line=border`, `{line=}`, a CSS border or `kpi.line=` keep it |
| `card.heading.max=30` `card.text.max=24` | a box card (`@2x2` `@3` `@4`, icon or number + `##` heading + text) with free height inside (its content fills under `layout.card_fill_max`, 0.7, of its height) grows its heading to at most `card.heading.max` pt and its text to at most `card.text.max` pt, the icon disc following the heading; never beyond `layout.grow_max` x the role size, never when the text is pinned (`size=`, `sizes: body=16!`), never a heading that would wrap to another line. A cap under the size the layout already reached keeps that size. The cards keep their size and their top-anchored content |
| `conclusion.icon=<name>` | an icon at the left end of the `>` conclusion bar (the text shifts right; the bar is at least `layout.conclusion_icon_h` tall): white on the bar fill, on an `icon.disc` disc when that is set; drawn from the bar's final rectangle |
| `kpi.stripe=<color>` `kpi.stripe_h=6pt` `kpi.stripe.side=top` | a stripe on the top edge of every `.kpi` card (a tall stripe is a header band: a label on it is judged against the stripe colour); a list `kpi.stripe=a,b,c` cycles over the cards in order, `kpi.stripe.side=left\|right\|bottom` moves it, `{stripe=teal}` on one card wins ("Card stripes" below) |
| `kpi.rule=<color>` `kpi.rule_h=1pt` `kpi.rule_w=100%` | a divider rule between the number and its caption in every `.kpi` card (off by default). The caption becomes its own text box under the rule; `layout.kpi_rule_gap_em` is the air around it |
| `kpi.band=<color>` `kpi.band.color=<c>` `kpi.band.size=20` | a header band on every `.kpi` card, flush on its top edge, holding the label in the band's ink (white, or what reads on the fill; like `heading.band` on boxes); `kpi.band.size` also pins the label size; an `icon=` sits under the band; `layout.kpi_band_pad` is the air around the label |
| `kpi.unit.size=22` `kpi.unit.color=<c>` | the unit of a KPI value (the trailing non-digit run of the value line: `億円` in `1,280億円`, `名`, `%`) in its own size, smaller than the digits (never larger than the number); a value without digits or without a tail is left alone; per slide: `style: kpi.unit.size=32` inside the slide |
| `kpi.fill=<c>` `kpi.line=<c>` | the card fill and border of every `.kpi` card (aliases of `card.fill` / `card.line` for KPI cards; also `kpi.radius` `kpi.shadow`) |
| `table.num_pad=0.6in` | the right inset of right-aligned (numeric) table cells, header included |
| `bullet=■` `bullet.color=<color>` | the glyph and color of bullet lists (default `•`, text color) |
| `footer.color=` `footer.size=` | the footer text and the slide number (CSS `.caption`) |
| `lead.bold=on` `lead.border-left="4pt solid secondary"` | any CSS property of `lead` `conclusion` `footnote` `subtitle` `box` `chart` (`lead.color` is the theme field) |
| `kpi.label.size=20` `kpi.label.bold=on` `kpi.value.color=` `kpi.note.color=teal` | the KPI label (`.kpi h2`), number and caption line; `kpi.size` / `kpi.color` stay the number's class style |
| `sizes: conclusion=24` `sizes: kpi=34` | the conclusion bar text size; the KPI number's size |
| `sizes: heading=20!` | `!` pins a size: the layout never grows it (`{size=}` and CSS already do) |

**Text look in one token.** A bare element or class name takes the look as words: `style: kpi.label="20 bold primary" kpi.note="20 bold teal" steps-card="24 bold center" heading=center conclusion="24 bold" lead="bold secondary" title=primary`. Words: a number = size (pt), `bold` `italic` `underline`, `left|center|right|justify`, anything else = a color; each word is the same token written long (`kpi.label.size=20 kpi.label.bold=on kpi.label.color=primary`). Names: `title heading body lead subtitle conclusion footnote footer num box chart kpi steps-card steps-arrow rows rows-num` and `kpi.label` / `kpi.value` / `kpi.note`. A word it cannot place is a `bad-token` warning that lists the words. `fonts: font="Yu Gothic"` sets heading, body and ea at once (`mono` keeps its own).

**Per slide.** `sizes:` and `style:` lines work inside a slide too, with the same keys as the header; they change that slide only (sizes, class and element styles, `kpi.*`, `layout.*`; chrome such as `top.bar` stays deck-wide). A line counts only when every word is `key=value`, so prose like `style: modern` stays text.

```markdown
# 海外展開の重点地域
sizes: heading=26! body=24!
## タイ
- 工場の生産能力を1.5倍に
```

**KPI row.** `@kpi` on the slide (not inside a box) makes every `##` box a KPI card, the same as `{.kpi}` on each; `style: kpi.h=4.4in` sets the height of a lone KPI row's cards (without it the cards take a share of the body, `layout.kpi_lone_h`).

A declared color name beats the CSS color of the same name (`colors: teal=#2A9D8F` makes `teal` yours everywhere).
`slide { border-top }` in CSS is not drawn (`css-unsupported` names `top.bar`). `layout.html_footer=on` draws the deck `footer:` and
`num:` on `@html` slides too.

## Slides

- `# Title` starts a new slide. You do not need a separator.
- A line `---` starts a slide that has no title.
- Code fences are never parsed for structure, so a `#` comment inside code is safe.
- **Cover and section slides are automatic.** A slide with a title and at most two short lines of text is a cover
  (when it is the first slide) or a section divider. Those lines become the subtitle.
  On a cover or section slide (`@cover`, `@section`, or inferred) a `## line` is one more subtitle line, not a
  box (info `cover-heading`); `##` boxes belong on content slides.
  Cover tokens (`style:`): `cover.band_h=60%` (band anchored to the top, filled by `title.band`; title block
  bottom-aligned in it; `0` = the older centred block), `cover.pad=0.55in` (air under the block), `cover.gap=0.2in`
  (title to subtitle), `cover.rule=accent` + `cover.rule_h=0.06in` (rule on the band edge, `none` = off),
  `cover.footer=off` (the deck `footer:` shows on the cover as a bottom caption), `cover.bar=teal` + `cover.bar_w=0.12in` (a vertical bar left of the title block), `cover.band=none` (no band although `title.band` is set, so a slide `bg=` shows; the rule is full width over a `bg=`). `cover.top_bar=<color>` / `cover.bottom_bar=<color>` (+ `cover.top_bar_h` / `cover.bottom_bar_h`, default 0.1in) draw a full-width strip on the cover's top / bottom edge (`top.bar` / `bottom.bar` skip the cover). `{size=}` or CSS (other than `color`) on the cover keeps the old look. A full-bleed cover with a rule and a bar: `style: cover.band_h=61% cover.rule=accent cover.bar=teal cover.band=none` + `@cover bg=primary dark`.
  More decoration, all inside the composed cover (`cover.band_h` above 0), all working over a slide `bg=` and `dark`: `cover.bar=accent@edge` (the bar sits on the slide's left edge over the full height, width `cover.bar_w`), `cover.rule_w=6in` (the rule is short and sits at the title, left aligned: `cover.rule_pos=above` over the title, `below` (default) between title and subtitle) and `cover.stripes=#1C3A68@8.9in,secondary@10.2in` (vertical stripes, each from its x to the right edge, drawn behind the text; the title keeps left of the first). `cover.rule_w` shortens the `cover.rule=<color>` you set. Decor shapes are named `rule` and the importer skips them.
  Cover art: `cover.art=network|dots|rings` (default `none`) draws a decorative motif of native shapes in the right part of the cover and of a closing `@cover` / title slide: `network` = 8-12 dots joined by thin lines, `dots` = a grid of small discs fading out towards the title, `rings` = three concentric thin circles; one node is `accent`, the rest `cover.art.color` (default `secondary`) at `cover.art.opacity` (0.65), the same `cover.art.seed` (7) draws the same motif, and the title block keeps the left `cover.art.split` (0.6) of the width (so it wraps in it). Shapes: `Cover art N` (the importer drops them). `layout.cover_art_nodes` `cover_art_node_ratio` `cover_art_line_pt` `cover_art_margin` size it. A `cover.art` without a cover slide is `attr-ignored`.
  A band on the cover's bottom edge: `cover.bottom.bar=<color>` + `cover.bottom.bar_h=0.3in` (works on any cover; the deck `footer:` caption sits above it, `cover.footer=off` hides it). Slide 1 of a navy cover with an amber bar and a blue foot: `style: cover.band_h=70% cover.band=none cover.bar=accent cover.bottom.bar=secondary` + `@cover bg=primary dark`.
- **Dark slides pick their own ink.** A slide `bg=` (color, token name or `linear-gradient(...)`, every stop
  judged) that gives the theme `fg` less than 4.5:1 turns the text on the slide (title, lead, subtitle, footnote,
  loose paragraphs) to `render.ink_light` or `render.ink_dark`, whichever contrasts more; lead, subtitle and
  footnote get a softer mix. The class `dark` always means light ink and `light` dark ink on whatever bg (unless
  the theme defines that class). Cards, tables and anything with its own fill keep their colors. Colors you
  declare for the slide win: a slide ```css fence or `{color=}` on `slide` / `h1` / `p` / `.lead` ... (a
  deck-wide `h1 { color }` yields to a slide's own `bg=`/`dark`). Example: `@cover bg=#2E7D32 dark`.
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
| `> text` right after the title | **lead**: the key message under the title (body ink, bigger than body text, below the title: `sizes: lead=` and `style: lead.color=` / CSS `.lead` override) |
| `> text` as the last thing on the slide | **conclusion**: a bar at the bottom |
| `※ text` or `^ text` | **footnote**: small text at the bottom (sources, notes) |

A `>` anywhere else is a quote. `style: conclusion.h=1.05in` makes the bar exactly that tall (default: its text's height).
The bar text is never smaller than the body text of its slide (`conclusion.floor=1`, x the largest body text, `0` = off; the bar
text itself is capped by `layout.conclusion_max_pt`, 28): a sentence that does not fit one line at that size wraps to a second line
instead of shrinking; `sizes: conclusion=18` pins the size. The fit line ends with `bar 24pt`.

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
| `a:b:...` | column width ratios (kept exact; close ratios such as `1:2` snap to the 12-track grid) | `@1:2` (one third / two thirds), `@2:1:1:1` |
| `rows/rows` | **areas**: block 1 = `a`, block 2 = `b`, ... in source order; repeat a letter to span; `.` = empty | `@aab/aac` |
| `flow` | arrows between blocks in reading order (process diagrams) | `@4 flow` |
| `chevron` | blocks drawn as chevrons (steps) | `@4 chevron` |
| `rows` | an ordered list (`1.` `2.`) alone on the slide drawn as numbered bars (below; `layout.rows=on` does it for every such slide) | `@rows` |
| `steps` | a process row: each `##` heading is an arrow, its bullets sit in a card under that arrow (below) | `@4 steps` |
| `items` | the bullets of every box are drawn as item cards (below); `style: box.items=cards` does it for every slide | `@4 items` |
| `num` | a numbered circle (1..n) left of every box heading (below; on `@steps head=arrow` it is the `STEP n` caption, on the card look the arrow already shows the number) | `@4 num` |
| `timeline` `vs` `matrix` `funnel` `pyramid` `cycle` `agenda` `statement` `stairs` `nested` | a composition form: the `##` boxes (or the list / line) are drawn as that diagram (below); each takes secondary keys (`dir=` `marks=` `x=` `y=` `align=` `valign=` `center=` `side=`) and the common `size=` `fill=` `gap=` | `@timeline dir=v marks=num` |
| `flow disc` | `@flow` with the second word `disc`: every `##` box is an icon disc joined to the next by an arrow line, heading and text under it (below) | `@flow disc` |
| `iconlist` `quote` `split` `proscons` `progress` `harvey` `heatmap` `pins` | composition forms with secondary attributes ("Composition forms, part 2" below) | `@iconlist cols=2` |
| `cover` `section` `blank` `center` | force a slide type | `@section` |
| `free` | absolute positioning: every block with `{x= y= w= h=}` sits exactly there, with no growth, balance or search; unplaced blocks stack on top (info `free-unplaced`). `%` is a share of the body under the title (not the slide): the fit line prints it once (`free area 0.5,1.4 12.3x5.5in`, x,y then width x height). A `{x= y= w= h= shape= fill=}` line with nothing after it draws a shape (below) | `{x=10% y=30% w=40% h=20%}` |
| `grid` | with `@free`: `x y w h` snap to a 12-column x 12-row grid over the body, and `3c` is a grid unit: `x=3c` / `y=2c` = the left / top edge of column / row 3 (counting from 1), `w=4c` / `h=3c` = four columns / three rows wide (a percentage snaps to the nearest twelfth). A title or subtitle pin counts over the whole slide. `3c` without `@free grid` warns `bad-length` | `@free grid` then `## a {x=1c y=2c w=6c h=5c}` |
| `key=value` | `bg=` color or image, `t=` transition (`fade`, `push`, `wipe`, `split`, `cover`, `zoom`, `morph`; `t=fade:0.5` sets seconds), `id=`, `gap=` | `@bg=#0F172A t=fade` |
| `a>b` `a-b` | **connector** from block `a` to block `b` (arrow / plain line). Letters count blocks in source order (`a` = 1st), digits work too (`1>3`). With `flow`, the links replace the flow arrows (info `flow-links`) | `@3 a>b a>c` |
| `hidden` | hide the slide in the show | |
| `build` | bullets and blocks appear one by one on click (`{.build}` on one block does it for that block only) | `@build` |
| `noemph` `defaults` | decisions, no visual effect: `noemph` = this slide has no focal figure, `defaults` = the deck frame already serves this slide's values (they satisfy `design-slide`, see "Diagnostics: design feedback") | `@2 noemph defaults` |
| any other word | class applied to the slide (`dense`, `dark`, ...) | `@3 dense` |

Inside a box, an `@` line lays out that box's `###` sub-boxes in the same way. An `@` line after the last box of a slide
whose box has no `###` sub-boxes applies to the slide (info `at-hoisted`).

`@aab/aac` reads as two rows. In the first row, block `a` takes two columns and `b` one. In the second row, `a`
continues and `c` takes the last column. The result: a tall box on the left two-thirds and two stacked boxes on
the right.

**Steps.** `@steps` is a process row with an outcome per step: every `## heading` is an arrow (a chevron),
and its bullets sit in a card under that arrow, in the same column. A step with no bullets shows only its
arrow. The cards grow down to the conclusion bar / footnote (as far as their text fills them). Other blocks
after the steps (use `@end`) stay full width below. `@4 chevron` is the compact form: heading and bullets
inside the arrow. A chevron row alone on the slide whose steps all have short bodies (at most
`layout.chevron_steps_items` paragraphs each) is built as `@steps` too, so `@chevron` with one bullet per
step also fills the slide (`style: layout.chevron_steps=off` keeps the thin strip).

```markdown
@4 steps
## 現状分析
- 全店の業務を棚卸し
- 課題を30件に整理
## 設計
- 標準フローを策定
```

**Card look (the default, `steps.head=card`).** The arrow shows the step number (or the glyph of `{icon=bolt}` when there is no `icon.disc`) and the heading is written once, in the card, top-anchored: icon disc (with `icon.disc=`), the caption (only when `steps.caption="Bước {n}"` is stated: the arrow already shows the number, so `num` adds no second label), the bold `##` heading, then the bullets, left aligned, with no rules between them. The cards take the free height down to the conclusion bar / footnote; the content stays at the top and grows by one factor (disc, heading, text; at most `layout.grow_max`, never below `sizes: body`). `@4 steps head=arrow` (one slide) or `style: steps.head=arrow` (the whole deck) is the old look: the heading in the arrow, the bullets in the card, a step without bullets has no card; `@4 chevron` rows turned into steps keep it. `steps-card.align=center` and `steps-card.valign=middle|bottom` (default `left` / `top`) place the content; `layout.steps_card_pad` (0.2in) is its air, `layout.steps_arrow_card_h` (0.8in) the tallest number arrow. Shapes: `Step n arrow`, `Step n card`, `Heading n` (caption + heading), `Text n`; the importer reads the heading back into `##` and writes `head=arrow` only for the old look.

The cards take the free height first (down to the conclusion bar / footnote, items spread inside), so the text never shrinks while room is left; the fit line names the card text (`card text 16->18pt (grown)`, never the `STEP n` caption) and says `cards grown to fill` when the cards were stretched. `## Token hóa {icon=code}` puts the glyph inside the arrow; a sparse group with icons grows like one without (arrow label, icon, cards, text).

`@4 steps head=arrow num` adds a caption line first in every card (`STEP 1` ...; on the card look `num` draws nothing, the arrow shows the number); `style: steps.caption="STEP {n}" steps.caption_color=teal steps.caption_size=14` sets its text, color and size for every `@steps` slide (a size of its own: `layout.steps_caption_ratio` x body). `steps-arrow.fill=primary,secondary` (a list) cycles the arrow colors over the steps, `steps-card.fill=a,b` the cards; `steps-card.size=24 steps-card.bold=on` style the card text. `render.chevron_shape=pentagon` draws flat-tailed arrows (the importer reads them as chevrons); a list names the arrows in reading order, the last word repeats: `render.chevron_shape=pentagon,chevron` (first arrow flat, the rest notched). CSS reaches both parts: `.steps-arrow:nth-child(even) { background: ... }`, `.steps-card { ... }`.

**Exact geometry.** `style: steps-arrow.h=0.45in steps-card.h=2.7in steps.gap=0.2in` states the arrow row height, the card height and
the arrow-to-card gap in lengths: the layout would choose all three itself (arrow aspect, stretch to the bar, sparse growth). A card
height is pinned: no stretch or growth pass changes it, and the conclusion bar follows the cards one gutter below (`conclusion.h=`
sets the bar's height). Without `steps-card.h` the cards keep their bottom edge. `steps-arrow.color=bg steps-arrow.align=left`
set the arrow text's ink and alignment. A bad value is `bad-token` with a hint; a token without `@steps` is `attr-ignored`.
The importer writes all of these from the original's geometry.
`steps-arrow.point=0.5` is the point depth of every arrow (the preset's `adj`: a share of the arrow's shorter side, `0.5` = the
PowerPoint preset, `30%` works too; the build's own is `layout.chevron_adj`, 0.3). It is one depth: the layout does not search flatter points
for text room any more, and a growth pass cannot rescale it. It also draws the arrows of a plain `@chevron` strip. With a stated
arrow or card height the group starts at the body top (no centring), where a foreign deck draws it.

Looks are tokens: `style: steps-arrow.fill=accent steps-card.fill=#EEF2FF` (classes `steps-arrow` / `steps-card`,
or per step `## 設計 {.accent}`), `layout.steps_gap` (arrow row to cards), `layout.steps_arrow_aspect` /
`steps_arrow_min_h` / `steps_arrow_max_h` (arrow height), `layout.steps_arrow_text_ratio` (arrow text vs card
text), `layout.steps_stretch=off` (cards keep their content height). Fewer than two `##` steps: warning
`steps-few`. Column ratios work (`@1:2:1 steps`). A sparse group (at most two short bullets per card) grows its text
(`layout.steps_text_max_pt`, `steps_arrow_text_max_pt`), arrows and cards, and sits centred in the body
(`layout.steps_sparse_fill`, `steps_top_share`; `layout.steps_sparse=off` keeps the compact strip).

**Rows.** `@rows` draws an ordered list that is alone on the slide (a lead, conclusion and footnotes may surround it) as one bar per item with a number badge on the left. Other content on the slide: info `rows-skipped`.

```markdown
# 価格改定の方針
@rows
1. 主力3ブランドを平均6%改定
2. 容量変更は行わない
```

**Plain rows.** `@rows plain` draws the same bars without number badges: a list with `-` or `1.` is fine. The marker is a glyph (`style: rows.glyph=■ rows.glyph.color=accent`; without `rows.glyph` the `bullet=` token is the glyph, `rows.glyph.color` falls back to `bullet.color`) and/or a left stripe: `rows.stripe=primary,secondary` (a list cycles over the bars; also on numbered `@rows`, `layout.rows_stripe_w`, 0.14in). Shapes: `Row N`, `Row N glyph`, `Row N stripe`; the importer folds them back to `@rows plain`.

```markdown
style: rows.glyph=■ rows.glyph.color=accent rows.stripe=primary,secondary
@rows plain
- 主力3ブランドを平均6%改定
- 改定は2027年5月出荷分から
```

Looks: classes `rows` (bar: `rows.fill=surface`) and `rows-num` (badge: `rows-num.fill=primary,secondary` cycles; `rows-num.shape=square|circle|rounded`, default `square`), `layout.rows_h` (bar height, 1.05in), `rows_gap`, `rows_pad`, `rows_text_ratio` / `rows_text_max_pt` (text size; `{size=}` pins it). The bars are native rectangles named `Row N` and `Row N num`; the importer folds them back to `@rows`.

**Item cards.** `@4 items` draws the bullets of every `##` box as cards (a `1xN` grid inside the box, one card per bullet, a deeper bullet joins the card above); `style: box.items=cards` does it for every slide. The cards are the class `item`: `style: item.fill=bg item.line=border item.border-left="5pt solid secondary" item.size=14 item.bold=off item.valign=middle` (defaults: `bg` fill, the card line, text vertically centred; `item.color` `item.align` `item.radius` work too). Text size, bold and valign act on the card text, never on a heading band. A box that holds anything but bullets keeps them as bullets (info `items-skipped`). `### text {.item}` sub-boxes are the same cards, so `item.*` and `{size=}` reach them too. Shapes: `Item N`; the importer reads cards back as bullets and adds `items`.

**Numbered boxes.** `@4 num` puts a circle with 1..n left of every `##` heading (with `heading.band` inside the band): `style: box.num.fill=primary box.num.color=bg box.num.size=20` (fill defaults to `primary`, or the heading ink on a band; digit color to a readable ink; digit size to the heading size, the circle is `layout.num_badge_ratio` = 1.9 x the digit). Not on `###`, KPI cards or `@steps`. `box.num.shape=circle|square|rounded` (default `circle`) draws the badge as that shape (`rect` / `ellipse` / `roundRect`). Shapes: `Num N` (decor: the importer drops them and adds `num`).

```markdown
style: heading.band=primary heading.rule=accent heading.rule_h=0.06in item.border-left="5pt solid secondary" item.size=14
@4 items num
## 既存事業の収益改善
- 主力3ブランドの価格改定
- 不採算SKUを15%削減
```

**Box height and anchor.** `style: box.h=4.2in box.anchor=top` makes every `##` box card of the slide (or of the deck, in the header)
exactly 4.2 in tall and puts the row at the top of the body: `top`, `center` or `bottom` (without `box.anchor` the row keeps the
layout's place, moved up only to stay in the body). Without `box.h` the cards are as tall as their content (and stretched); `box.anchor`
alone only moves the row. The heading, band, badge and icon keep their place on the card's top edge, the last text box grows with the
card, a note under the cards follows the last row, rows of a grid keep their gaps. KPI, step and item cards are not boxes (`kpi.h` is
theirs); a box with its own `{h=}` is left alone. The importer writes both for a header-band card row it reads (`top` when the cards
start at the body top, `center` / `bottom` at the middle / bottom of the body, nothing when the row floats).

**Page margin and body top.** `style: margin=0.6in layout.top_gap=0.45in` set the side margin (title, body, footer) and the gap between the
title area (or the lead line) and the body: a deck made elsewhere often has 0.6 in and 0.45 in where the build has 0.5 in and 0.25 in,
so every body item would sit a little off. The importer writes both deck-wide when most slides agree (the left edge that is also a
right edge, the commonest distance from the title's bottom to the first item; slides that start with a lead line are left out).

**Card stripes.** A stripe on one edge of every card, in a colour per card: `style: box.stripe=primary,secondary,accent` (a list is applied in reading order and cycles, like `steps-arrow.fill=a,b`), `box.stripe_h=6pt` (thickness), `box.stripe.side=top|left|right|bottom` (default `top`). The same three tokens exist for item cards (`item.stripe` `item.stripe_h` `item.stripe.side`, side default `left`), KPI cards (`kpi.stripe` `kpi.stripe_h` `kpi.stripe.side`) and `@rows` bars (`rows.stripe=a,b`, always on the left, width `layout.rows_stripe_w`). `## 現状 {stripe=teal}` colours that one card and still takes its place in the cycle. A stripe is drawn from the final card rectangle (a card a pass stretched keeps it), named `Stripe` (a KPI stripe `rule`), and the importer drops the shape and keeps the tokens. Only cards with a fill or border get one (`{.plain}` boxes do not).

```markdown
style: box.stripe=primary,secondary,accent box.stripe.side=left
@3
## 現状 {stripe=danger}
- 手作業が多い
## 課題
- 解約率が上昇
```

**Number as heading text.** `@4 num=text` writes `01` `02` ... as big coloured text above every `##` heading instead of a badge (`@4 num` = the circle, `num=badge` is the same word); `## 01 {.num}` / `## 2.1兆円 {.num}` draws the heading text itself as the number. Look: `style: box.num.size=36 box.num.color=primary,secondary,accent box.num.text="{nn}"` (`{nn}` = 01, `{n}` = 1, `"第{n}章"`; size defaults to `layout.num_text_ratio` 1.7 x the heading size; the colour list cycles over the boxes, default = the card's own stripe colour, else `primary`; `box.num.fill` / `box.num.color` also cycle the badges of `@num`). Shapes: the heading is named `Number text` / `Number heading`, the importer folds both back.

```markdown
style: box.stripe=primary,secondary,accent box.num.size=34
@3 num=text
## 3年で売上を2倍
営業利益率を 20% へ
```

**Number tiles.** `@kpi tile` (or `## 2.1兆円 {.kpi .tile}` on one card) makes a card whose heading is the number and whose body is the description: the heading becomes the value line (in the card's stripe colour), the body the caption, text left-aligned unless `{align=center}`. With `kpi.stripe=teal,teal,accent,muted kpi.stripe.side=left` this is the "four number tiles" slide. The text shape is named `Tile` and the importer folds the card back to `{.kpi .tile}`.

```markdown
style: kpi.stripe=primary,secondary,accent,muted kpi.stripe.side=left kpi.stripe_h=0.08in
@2x2 kpi tile
## 2.1兆円
国内の中小企業向けSaaS市場は2029年に2.1兆円へ
## 38%
クラウド会計の導入率
```

**Dark panel.** A box with its own `fill` picks a readable ink for its heading and text (no `color=` needed), so a statement panel beside a list is one box: `@1:2` then `## スタンダードプラン {fill=primary valign=middle}` with `[9,800円]{size=32 bold=true}` / `▼` / `[10,800円]{size=32 bold=true color=accent}` lines (spans of different sizes, "Inline text").

## Composition forms

One `@word` line turns the blocks under it into a diagram, with secondary keys on the same line. Every form takes
`size=14` (its text, pt; a pinned size never shrinks or grows), `fill=a,b,c` (colors, cycled) and `gap=`; a
ratio token (`@1:2:1 timeline`) sets column widths as it does for `@steps`. Looks are tokens named after the form
(`style: timeline.dot=accent funnel.fill=#1F3A8A,#5A73B4`; list below). The layout names every shape it draws
(`Timeline 2 dot`, `Funnel 1 up`, `Cycle 3 arrow ccw`), so `slidemark import` writes the form back. A slide that
lacks what the form needs (`@cycle` with two boxes) warns `<form>-skipped` and is laid out as ordinary blocks; an
unknown key, a wrong choice (`dir=x`) or a key without its form warns with the valid words. One form per slide
(`form-conflict`). The `build` fit line names the form: `slide 4: timeline 5 (h, marks on), text 16->22pt (grown)`.

```markdown
@timeline dir=h marks=on
## 2027年4月
パイロット開始
- 3拠点で試行
## 2027年10月 {.accent}
全国展開
```

| Form | Blocks | Keys | Tokens (`style:`) |
|---|---|---|---|
| `@timeline` | 2-10 `##` boxes: heading = date / label, body = text. `{.accent}` = the current milestone | `dir=h` (default; text alternates above / below a line) `v` (all text right of a vertical line); `marks=on` (dots) `off` (stems only) `num` (numbered dots) | `timeline.line` `timeline.line.w` `timeline.dot` `timeline.dot.size` `timeline.now` `timeline.date.color`; `layout.timeline_stem` `timeline_text_w`; a box's own `{fill= color=}` = its dot and heading |
| `@vs` | 2 `##` cards side by side + an optional 3rd `## 結論` verdict bar below. `{.hero}` = the winner | `@2:1 vs` card widths | `vs.badge.text` (`vs`) `vs.badge.fill` `vs.badge.color` `vs.badge.size`; `vs.verdict.fill` `vs.verdict.color`; `vs.win.line` `vs.win.w` `vs.win.fill` |
| `@matrix` | exactly 4 `##` boxes in reading order: top-left, top-right, bottom-left, bottom-right | `x="低←重要度→高"` `y="低←緊急度→高"` (label + arrow along the bottom / left; leave one out and its axis is not drawn); `@1:2 matrix` column ratio; `fill=a,b,c,d` quadrant fills | `matrix.axis.color` `matrix.axis.size` `matrix.axis.w`; `matrix.fill=a,b,c,d` |
| `@funnel` | 2-8 `##` boxes: heading inside the stage, body to its right | `dir=down` (default: the narrow end at the bottom) `up`; `@3:1 funnel` shapes : bodies | `funnel.fill=a,b,c` (cycled; default tints of `primary`) `funnel.color` `funnel.gap` `funnel.taper` (narrow / wide end, 0.3) `funnel.share` (width of the shapes, 0.5) |
| `@pyramid` | 2-8 `##` boxes, first = the top | `dir=up` (default: narrow end on top) `down`; `@3:1 pyramid` | `pyramid.fill` `pyramid.color` `pyramid.gap` `pyramid.taper` (0.2; 0 = a point) `pyramid.share` |
| `@cycle` | 3-6 `##` boxes around a ring: heading in the node, body outside it, curved arrows between. A node is as large as its heading needs (never below the body size, up to what the ring holds; a heading even the largest node cannot hold goes beside it like an icon heading, the node showing the step number); `## Plan {icon=target}` puts the glyph inside the node (45% of its diameter) and the heading, bold, beside it above the body | `dir=cw` (default) `ccw`; `center="Vòng lặp agent"` (a label at the ring centre) | `cycle.fill=a,b` `cycle.color` `cycle.arrow` `cycle.arrow.w` `cycle.node.size`; `cycle.center` (text) `cycle.center.size` `cycle.center.color` `cycle.center.fill` (a disc behind it); `cycle.icon.ratio` (0.45) `cycle.icon.color` `cycle.head.color` |
| `@stairs` | 2-6 `##` boxes as cards whose heights rise left to right (bottoms aligned, the last reaches the body top); heading bold, every card text at one size (the largest the lowest card holds). An optional lead `>` stays above | `dir=up` (default) `down`; `@1:2:1 stairs` widths | `stairs.fill=a,b,c` (cycled; default tints of `primary`, light to dark) `stairs.color` `stairs.step` (height difference) `stairs.gap` `stairs.low` (lowest card, share of the body, 0.4) `stairs.tint` (lightest default, 0.3) |
| `@nested` | 3-4 `##` boxes as concentric rings, first = the largest, heading at the top of its ring (the innermost in its middle); the bodies are an icon list on the other half (`## Học sâu {icon=cpu}` gives its list item the icon) | `side=left` (default, rings left) `right` | `nested.fill=a,b,c` (outer to inner; default tints of `secondary`) `nested.color` `nested.size` (heading pt) `nested.core` (inner / outer diameter, 0.4) `nested.share` (width of the rings' half, 0.5) `nested.line` `nested.line.w` `nested.list.title` (`off` = the list item starts with its text, not the ring heading) |
| `@agenda` | one `1.` list alone (a `   - note` under an item is its second line). `{.accent}` at the end of an item = the current one | `@1:5 agenda` number column : text | `agenda.num.size` `agenda.num.color` `agenda.num.text` (`"第{n}章"`, `"0{n}"`) `agenda.rule` (`none` = no rules) `agenda.rule.w` `agenda.now` `agenda.dim` (the other items once one is current) |
| `@statement` | one or two plain lines under the title: the number / sentence, then a caption | `align=left\|center\|right` `valign=top\|middle\|bottom` | `statement.size` `statement.color` `statement.sub.size` `statement.sub.color` |

Text grows into the room (up to `layout.vocab_grow` x the body size) and shrinks to fit; `size=` pins it. `@vs` and
`@matrix` draw their `##` boxes as ordinary cards (`card.*`, `heading.band`, `{fill=}` all apply); a box of the
other forms takes `{fill= color=}` only (other attributes warn `attr-ignored`, hint names the form's tokens).
Shapes: stages are native custom-geometry trapezoids, cycle arrows native `arc` shapes with arrowheads, axes
and stems native connectors, the matrix y label vertical text (`vert270`); all editable in PowerPoint.

**Composition forms, part 2 (DL3b).** Eight more `@word` slides, each with secondary attributes on the same line and a
`<word>.*` token for every fill, line and size (`style:` header or slide line; `slidemark tokens` lists them). Every form
also takes the generic attributes `gap=` (gutters), `size=` (text, pt) and `fill=` (the form's main colour). The parsed
slide stays as written: the layout composes the body on a copy, names the shapes, and the importer folds them back to
the same words. Example: `examples/24-vocabulary-2.md`.

| Word | Source | Attributes | Tokens |
|---|---|---|---|
| `@iconlist` | `- icon=bolt **Title** text` items (or `:bolt:`); a bold lead is the title, nested bullets are more text; `icon.disc=<color>` puts every icon on a disc (it takes the icon slot, text starts after it), `- icon=bolt disc=accent **Title**` sets one item's disc, `disc=none` removes it. The items share the body evenly (`iconlist.fill=on`, default; `off` keeps a centred block) and the icons / discs grow into the room left once the text is at its ceiling, up to `layout.grow_max` x (not with `icon.disc.size=` / `iconlist.icon.size=`); with `fill=` the cards stretch to their rows; `iconlist.valign=top` sits an item at the top of its row (default `center`); the title grows to `iconlist.title.max` (32pt) and the text to `iconlist.text.max` (28pt), both under `layout.grow_max` and never below the role size; a row of 3+ columns stacks the icon above the text (`iconlist.icon.pos=auto`; `left` / `top` force it) and a stacked card is at most its content / `layout.iconlist_fill_min` (0.6) tall | `cols=1..3` (default by item count) | `iconlist.icon.size` `.icon.color` `.gap` `.fill` `.valign` `.title.max` `.text.max` `.icon.pos` |
| `@quote` | a `>` block or the body text; the last line `— Name` is the attribution | `align=left\|center\|right` | `quote.size` `quote.mark` `quote.mark.color` `quote.by.color` |
| `@split` | an image (`![alt](x.png)`) or, without one, a `fill=` colour block; everything else sits on the other side | `side=left\|right` `ratio=1:1` (image : text) `bleed=on` `fit=cover\|contain` | `split.gap` `split.fill` `split.ratio` |
| `@proscons` (`@pros`) | two `##` boxes (any headings): first is `+`, second `−`; a last `>` line is the verdict bar. The headers and discs follow the palette: `secondary` for the pros, `accent` for the cons (ink readable); `style: proscons.plus.color=success proscons.minus.color=danger` brings back green / red | | `proscons.plus.color` `.minus.color` `.plus` `.minus` `.gap` |
| `@progress` | `- label 72%` (or `7/10`, `72`), or a table `label \| value` | `max=100` | `progress.fill` `.track` `.h` `.label.size` |
| `@harvey` | a table whose cells are 0-4 or 0/25/50/75/100%; header row and label column stay text | | `harvey.size` `.fill` `.line` `.band` |
| `@heatmap` | a numeric table; the first column is row labels when it holds text | `min=` `max=` `colors=a,b[,c]` `text=auto\|on\|off` | `heatmap.colors` `heatmap.text` |
| `@pins` | an image + `- x=32% y=58% label` items (positions are % of the image) | `legend=right\|bottom\|off` | `pins.fill` `.color` `.size` `.legend` |

```markdown
@iconlist cols=2
- icon=bolt **Faster builds** median 38 s
- icon=shield **Safer releases** signed and reversible
```

```markdown
@quote align=center
> "We stopped arguing about the deck."
> — Mika Tanaka, Northwind
```

```markdown
@split side=right ratio=2:3 bleed=on
> Quiet floors and one shared board
![studio](assets/studio.png)
- 3 floors, 140 desks
```

```markdown
@proscons
## Why buy
- Live in eight weeks
## Why build
- Nine months of engineering
> Verdict: buy now
```

```markdown
@progress max=100
- Billing engine 92%
- Partner API 12%
```

```markdown
@harvey
| Vendor | Price | Support |
|-|-|-|
| Ledgerly | 4 | 2 |
```

```markdown
@heatmap min=0 max=100 colors=#F3F6FA,primary
| Region | Free | Team |
|-|-|-|
| Japan | 22 | 48 |
```

```markdown
@pins legend=right
![map](map.png)
- x=26% y=36% **Harbor HQ** product
```

**`@flow disc`.** `@flow` draws cards and arrows; the second word `disc` draws every `##` box as a disc (the `icon=` glyph on its heading, else its step number) joined to the next by a line with an arrowhead, the heading bold under the disc and the text under the heading. `## Kho tài liệu {.above icon=database}` (or `@flow disc above=1`) lifts the first box above the row as a side node: its disc sits over the second step, joined to it by a vertical line, its text beside it. 2-7 boxes (`flow-skipped` otherwise). Tokens: `flow.disc.size` (a length; default from the room) `flow.disc.fill=a,b` (cycled, default `primary`) `flow.disc.color` `flow.line` (default `muted`) `flow.line.w`. Shapes `Flow N disc` / `Flow N line` / `Flow N text`; the importer folds them back (`{.above}` from the node's height). Example: `examples/26-ai-overview.md`.

Details. `@iconlist`: the text column is `Iconlist N`, the icon a native `icon <name>` shape; an unknown icon is `unknown-icon` with
a did-you-mean, a missing one `iconlist-icon` (info); `iconlist.icon.size` is a length, else 2.2 x the title size
(`iconlist.icon_ratio`); `fill=` puts each item on a card. `@quote`: the text grows up to `quote.grow` x body (`quote.size`
or `size=` pins it); shapes `Quote mark` / `Quote text` / `Quote by` (`Quote panel` with `fill=` or the deck-wide `quote.fill=<c>`;
`quote.bar=<c> quote.bar_w=0.15in` adds a bar on the card's left edge, `Quote bar`; `quote.h=3in|full` gives the card that height
(`full` = the whole body, content centred in it, card at the top), `quote.width=1` makes it as wide as the body (default 0.82);
`quote.by.align=right` aligns the `— Name` line, default = the quote's `align=`); `-- name` and `~ name` also
read as attributions, and so does a final `. — Name` of one joined `>` paragraph. `@split`: the text side is laid out by
the ordinary engine on a slide as wide as that side (title, lead, boxes, bars, footer, every growth pass), so any content
works there; `bleed=on` runs the image over the slide height to the edge, otherwise it is inset by the slide margins
(corner radius from `card.radius`); shapes `Split fill`; the importer reads a full-height image beside text as
`@split bleed=on`. `@proscons`: glyph discs `Proscons k item N glyph` (`+` / `−`), card `Proscons k`, band
`Proscons k head` in the sign colour (ink picked for contrast); write `+` / `−` per item only inside one box
(`- a` `− b` lines join in Markdown, a ` − ` between spaces splits them again). `@progress`: shapes `Progress N label` /
`track` / `fill` / `value`; a value above `max` is clamped (info `progress-range`), a line with no number is
`progress-value`; `progress.track=none` draws no track. `@harvey`: quarter-filled balls are a native ellipse
(`Harvey r,c qN`) plus a `pie` wedge (`Harvey r,c pie`; attrs `pie_start` / `pie_end`), other cell text stays text, any
other value is `harvey-value`. `@heatmap`: the table keeps its numbers (`text=off` leaves them out); the ink is picked
per cell for contrast (`text=on` keeps the table ink); `colors=` takes theme names or hex, two or more stops, linear in
RGB; the table's shape name carries ` heatmap=lo;hi;colors;text` for the importer; `fill=<c>` is the high end of
the default scale. `@pins`: the image is drawn at its true aspect so `x= y=` land exactly; circles `Pin N`, legend
`Pin N legend` + `Pins legend N`; a position outside 0..100% is `pins-position`. Secondary attributes a form does not take
warn (`@quote cols=2` -> `unknown-token`, hint lists the form's keys); a bad value warns `bad-attr` with the accepted
values and the default is used. Fit line: `slide 5: pros / cons 2 boxes, 6 items 27pt`.

## Attributes `{...}`

Use attributes only when the default is wrong. They follow Pandoc style: `{.class #id key=value key="two words"}`.

- At the end of a heading line: `## 課題 {.danger}`.
- At the end of an image: `![図](a.png){w=40%}`.
- On its own line directly before any other block: `{size=10}`.

Keys:

| Group | Keys |
|---|---|
| Position | `x y w h`, in `%` of the parent area (the body area inside the margins and under the title, not the slide), `in`, `cm`, `mm`, `pt`, `px`; a bare number is pt |
| Style | `size` (pt; on a `##` box it sizes the box text, not its heading: `sizes: heading=` or `h2.size=` does), `color`, `fill`, `line` (a one-off on one `{.kpi}` card works: `## 売上 {.kpi fill=accent}`), `font`, `align`, `valign`, `bold`, `italic`, `radius`, `opacity`, `pad` |
| Element | `shadow` (`on` = `render.shadow`, default `0 3 12 #00000030`; `off`; or `"0 4 12 #00000040"` = x y blur color in pt), `rotate` (`rotate=15`: degrees clockwise, the whole box with its heading and children turns about its center), `shape` (`shape=hexagon`: a preset geometry, below), `z` (`z=1` to `z=9`: stacking, a shape without `z` sits at level 5, `z=1` goes behind it, `z=9` in front; a box takes its children along) |
| Image | `fit=contain` (default), `cover`, `stretch`; `size=60` is the share of its cell the picture fills (5-100), `pad` insets it, `align` / `valign` anchor it in the cell, `fill` shows behind a transparent picture |
| Classes | theme colors (`.primary`, `.accent`, `.danger`, `.success`, `.muted`), `.plain` (box without card), `.kpi` (big number box) |

`stripe=teal` (outside the table: it is a card look, see "Card stripes") colours the stripe on one `##` box, item card or KPI card; any other kind reports `attr-ignored`.

Every element kind takes the whole set (title, cover, box, item card, KPI card, step, chevron, text, callout, image,
table, chart, code, `@rows` list), and a pinned `x y w h` is never grown, shrunk or moved by a layout pass
(`Placed.pin`, `engine._restore_pins`): the explicit wins. Where a key means something specific the kind says so
in the table under "Build output": a title with `fill line radius` is a styled title box (`{x= y= w= h=}` place it);
a chart with `fill line radius shadow pad` is a framed chart (`align` / `valign` place it in its cell when `w` / `h` leave
room, `bold` / `italic` style its labels); a table's `pad` pads every cell; a KPI card's `color` / `bold` style the
number and `align` / `valign` place its text; `font` on a code block replaces the mono font; `align valign radius` on an
`@rows` list act on the bars. A list item takes its own text style on its line: `- 要確認 {color=danger bold=true}` (also
`{.danger}`; size color font bold italic align, plus fill line on a row of `@rows`).

**Shape block.** An attribute line with a position (any of `x y w h`) and a look (`shape` `fill` `line`) and no content
after it draws a native shape named `Shape N`, on any slide (an arrow between cards, a badge, a plate):
`{x=24.4% y=36% w=2.4% h=8% shape=chevron fill=accent}`. `shape=` is the preset (default `rect`; `radius=` rounds a
rectangle), with `fill line line.w=2pt radius rotate opacity shadow z`. `shape=line` is a straight connector from the
top-left to the bottom-right corner of the box (`h=0` horizontal, `w=0` vertical; needs `line=`; `head=arrow` adds
an arrowhead): `{x=10% y=50% w=30% h=0 shape=line line=accent line.w=2pt}`. A line followed by content is that
block's attributes, as before. Fit line: `free 8 blocks, 8 pinned, 3 shapes`. The importer turns a text-less preset
shape (not a rectangle or an arrow) of a foreign deck into such a block and the slide into `@free`, positions as
inches from the body's top-left corner.

**`shape=`** draws a box, card, text block (with a fill or border), code block, image or chart frame with a preset
geometry instead of a rectangle (`shape=pill` is a rounded rectangle with half-round ends, `radius=` still sets a
`rounded` corner): `rect rounded pill snip snip2 round1 round2 round-diag snip-round folded plaque bevel frame ellipse
circle diamond triangle right-triangle parallelogram trapezoid pentagon regular-pentagon hexagon heptagon octagon decagon
dodecagon donut chevron arrow-right arrow-left arrow-up arrow-down arrow-both arrow-notched star star4 star6 star8 burst
heart lightning sun moon cloud plus cross gear cylinder cube funnel wave ribbon scroll tear callout callout-round
callout-oval callout-cloud` (also `oval`, `capsule`, `square`, `can`, `bolt`, ...; the table is `src/slidemark/shapes.py`).
An unknown name warns `bad-attr` with the nearest names. `style: card.shape=hexagon` makes it a token.

An attribute the layout does not honour where it is written is not silent: `build` and `check` print
`attr-ignored` with the form that works (table under "Build output" below). One KPI row takes its height from the
first card: `## 売上 {.kpi h=55%}` sets the card height (share of the body) of every card in a row that stands alone on
the slide (a lead and a conclusion bar may surround it), and `y=` its top offset; the other cards need no copy.

`.muted` on a **box** reads as lower priority, not disabled: muted border and (with a heading band) a muted band; body text keeps its normal ink. Restore grey body text with `style: muted-box.color=muted`; turn the band off with `muted.band=none`. `.muted` on text, spans and badges stays grey text.

Orphan control: the last two words of a paragraph (3+ words, each up to 12 characters, not CJK/URL/code) are joined by a no-break space so a line never ends with a lone word; the importer turns it back into a plain space.

Japanese line breaks: a wrapping CJK paragraph breaks at phrase boundaries (BudouX) with soft `<a:br>` marked `bmk="sm"`, only when the line count does not grow; the importer drops them. No syntax.

## Components

**KPI box.** A box with `.kpi` shows its first line as a big number and the rest as a small caption; the
heading is the label. CSS: `.kpi { color; font-size; font-family; font-weight }` styles the big number;
`.kpi .caption` (or `.kpi p`) the caption, `.kpi h2` the label.

```markdown
## 売上 {.kpi}
12.4億円
前年比 +8%
```

**Sparse slides use the body** (themes with a small body size, such as `jp-business`; nothing to write). A lead
plus a short bullet list grows its text (up to `layout.list_text_max_pt`) and spacing; a few text cards alone
stretch down the slide (`cards_to_body*`, text up to `card_fill_text_max_pt`); a table alone (up to
`table_free_max_rows` rows) grows its text (`table_free_text_max_pt`) and rows (`table_free_row_em`), and a `>`
conclusion bar under it attaches to the table (`bar_attach=grow|move|off`, gap `bar_attach_gap`). Sizes you set
(`{size=}`, CSS, `sizes: table=`) are never changed; `style: layout.list_fill=off` (and `cards_to_body`,
`table_free`) switch a pass off. A KPI row alone (a lead may sit above it) stretches its cards to
`layout.kpi_to_body_h` of the body, and a sparse `@steps` group (also `@chevron` with short bodies) fills it
(`steps_to_body_fill`, card text up to `steps_to_body_text_max_pt`); `kpi_to_body=off` / `steps_to_body=off`
restore the content-sized look.

**Growth ceiling (`layout.grow_max`, default 1.5).** One deck-wide limit on text growth: no growth pass (list,
cards, `@steps` cards and labels, lone table text, KPI number / label / caption, chevron text, the general sparse
growth and sparse step) takes text beyond `grow_max` x the size of its role, on top of the pass's own absolute cap
(`list_text_max_pt`, `card_fill_text_max_pt`, `steps_to_body_text_max_pt`, `table_free_text_max_pt`,
`kpi_lone_value_max_pt`, `chevron_text_max_pt` ...); the smaller wins. Only text is capped: rows, cards and gaps may
still stretch to fill the body. Write it as a token, `style: grow.max=1.3` (or `layout.grow_max=1.3`);
`grow.max=1` switches text growth off entirely. A pinned size (`size=`, CSS, `sizes: body=14!`) is never grown, a
table with `{size=22}` stays at 22pt. A dense slide counts from the theme's role size (it may grow back to
`grow_max` x that). A slide that stays empty after growth is named by its fit line and a `sparse` info (below):
change its form, not its type size.

**Place a KPI row yourself.** `h=` `y=` `w=` on the `.kpi` cards of one row size and place the row, not the card
(an `x=` still makes a card absolute): the row is as tall as the largest `h=` (a share of the body), starts at `y=`
(from the top of the body), and a card with `w=` takes that width, the others share the rest. The cards keep
their columns; no pass stretches, shifts or grows a row you placed.

```markdown
## 売上高 {.kpi .hero w=45% h=55% y=24%}
```

**Hero KPI.** A wider card gets a bigger number (never wrapping), so a ratio grid makes one KPI the hero:
`@2:1:1:1` before the cards gives the first twice the width. Shorter without an `@` line: add `.hero` to the
card, `## 売上高 {.kpi .hero}` (a `.hero` card weighs `layout.kpi_hero_w` = 2 normal ones; an explicit `@` grid
wins; on a box that is not `.kpi` the class stays free for your own `hero.fill=` style). A KPI row that stands
alone (with a lead, a conclusion bar or a list after `@end`) grows to use the body: numbers up to
`layout.kpi_lone_value_max_pt`, cards `kpi_lone_min_h`..`kpi_lone_h` of the body height. Sizes you set (`{size=}`,
CSS `.kpi { font-size }`) are never changed. Tokens: `layout.kpi_hero_w`, `kpi_value_exp` (number size ~ card
width^exp), `kpi_card_fill`, `kpi_lone_*`.

```markdown
@2:1:1:1
## 売上高 {.kpi}
1,280億円
前年比 +8%
## 営業利益 {.kpi}
96億円
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
arrow-up, arrow-down, arrow-right, headphones, battery, music, sparkles, smile, camera, book, graduation-cap,
home, map-pin, wifi, code, cpu, bell, flag, gift, coffee, plane, wrench, key, play, trophy, briefcase, chat, bolt,
tooth, refresh, tag, eye, brain, layers, microphone, list, video; close synonyms such as `house`, `message`,
`lightning`, `sync`, `label`, `tags`, `arrow`, `image`, `robot`, `tool`, `loop` work too). `icon=assets/logo.svg` (path relative to
the deck) uses your own SVG: simple filled shapes (path, rect, circle, polygon) become native geometry recolored
like the built-in icons (white fills are cut-outs); strokes, gradients or transforms embed it as a picture. A
missing file is a warning. An unknown name is a warning listing up to three close names; `build` rewrites the
source only for the one name within one letter (`chrt` -> `chart`, never `eye` -> `yen`), and the icon is left out.

**Badge.** `[text]{.badge}` is a small filled label inside text; add a color class to change it:
`[済]{.badge .success}`, `[NEW]{.badge .danger}`.

In a table body cell a badge (alone, or after the cell text: `4.2 万台 [首位]{.badge .success}`) is drawn as a
native rounded pill shape over the cell (name `Pill`, editable text, fill = the badge color, ink chosen for
contrast, bold only for non-CJK). Pills of one column share one width; `layout.table_pills=off` keeps the old
text highlight; `style: pill.radius=4` / CSS `.pill { }` change the look. `{.gantt}` bars are not affected.

## Inline text

Each source line of plain text is its own line on the slide (no Markdown soft-break merging); a line right
under a list item still continues that item.

Inline text is Markdown: `**bold**`, `*italic*`, `~~strike~~`, `` `code` ``, `[link](url)`, and `[go](#5)` to jump
to slide 5. Additions:

- `==text==` emphasizes in the theme accent color (for the key number).
- `[text]{.danger}` colors text.
- **Mixed sizes and colours in one line.** A span takes `size=` (pt, **exact**: no pass grows, shrinks or clamps it),
  `bold=` `italic=` and `color=` (a colour name or `#RRGGBB`; `.muted` / `.primary` ... are the class form; a flag
  alone is `=true`, one token): `[売上高]{size=14 bold} [420億円]{size=28 bold color=primary} [（2026年度 210億円）]{size=12 .muted}`.
  It works in paragraphs, list items (`@rows` bars too), table cells (`<br>` is a line break in a cell), `##` box
  headings and KPI value lines. A line is as tall as its largest pinned span, and a text with a
  pinned span is not grown by the sparse-slide passes (the unpinned rest still follows autofit shrinking).
  A bad `size=` (not a number, outside 1-400) is ignored. The importer writes spans back for a paragraph whose runs
  differ in size or colour (`importer/runs.py`).
- `H~2~O` is subscript and `x^2^` is superscript.

Lists use `-` and `1.`, nested with two spaces.

Task lists: `- [ ] todo` and `- [x] done` start with a ☐ / ☑ glyph (U+2610 / U+2611) instead of a bullet.
`[x]{.badge}` is still a badge.

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

A cell may hold `<br>` (a line break inside the cell, no warning) and spans of different sizes (`[月額]{size=10 .muted}<br>[9,800円]{size=20 bold=true color=primary}`: a small label over a big value).

A ` ```table ` fence takes CSV instead. Its first row is the header.

## Charts (native, editable)

Name the fence after the chart: `bar`, `column`, `stacked-bar`, `stacked-column`, `line`, `area`, `pie`,
`doughnut`, `scatter`, `radar`, `waterfall`. The body is CSV. The first row holds the categories (its first cell is ignored),
and each following row is one series.

````markdown
```column {title="売上推移" legend=bottom}
,Q1,Q2,Q3
2025,10,12,15
2026,12,16,21
```
````

A `waterfall` (bridge) takes one series: the first value is the starting total, the next values are changes,
and a lone `=` cell is a total bar (the running sum). Up, down and total bars use `render.waterfall_up`,
`render.waterfall_down` and `render.waterfall_total` (theme color names or hex); the bars are native and editable.
It is drawn as a stacked column chart with a hidden `base` series; bars may cross zero. Labels show `+18` / `-33` / the total,
formatted by `fmt`, above each bar.

````markdown
```waterfall {title="営業利益の増減（億円）" labels=on}
,2026,再編,PB,その他,2029
営業利益,44,18,24,-33,=
```
````

Chart options go in the fence attributes:

| Key | Values | Default |
|---|---|---|
| `title` | text | none |
| `legend` | `bottom`, `right`, `top`, `left`, `none` | `bottom` when >1 series, else `none` |
| `labels` | `on` (values; on a pie/doughnut the share, `render.chart_pie_labels`), `percent` / `value` (pie/doughnut), `off`; or a position (implies `on`): `outside` `inside` `center` on bar/column (`inside` / `center` on stacked), `above` `below` `left` `right` `center` on line, `outside` `inside` `center` `best` on pie; on a pie/doughnut a `+name` suffix adds the category name above the value or share (`outside+name`, `percent+name`, `value+name`); **one word per category** (`labels=above,below,above,above`, `auto` = the automatic collision rule) on line and column/bar overrides the position of each point; a wrong count warns with the category count | `off` |
| `labels.bold`, `labels.color` | `on` / `off`: data labels bold (a pie's are bold by default, `off` unbolds them); a color name or `#hex` for every data label (replaces the automatic readable ink: the contrast check still judges it) | automatic |
| `totals` | stacked kinds: `off` drops, `on` forces the stack total at the end of each stack (default: shown with `labels=on`) | `on` with labels |
| `fmt` | Excel number format for labels and the value axis, e.g. `0.0`, `#,##0`, `0%` | general |
| `min`, `max` | value axis bounds | auto |
| `colors` | comma list of color names (theme, or declared in `colors:`) or hex, one per series (per point for pie; **one-series column/bar with as many colors as categories: one per bar**, `hl=` still wins for its point; another count warns) | theme palette |
| `axis` | `off` hides the value axis and gridlines, `on` keeps them | auto: bar/column with `labels=on` and <= 4 categories hide them (the labels carry the numbers) |
| `gap` | gap between bars, 0-500 (% of a bar): `gap=80` | `render.chart_gap` |
| `overlap` | clustered bar/column: overlap of the bars of one category, -100..100 (% of a bar; negative = a gap between them): `overlap=-5` | PowerPoint's (0) |
| `step` | distance between value-axis gridlines (the major unit): `step=200`. It asks for the axis to be shown (see `axis`), and an automatic max is rounded up onto a gridline; a step that would draw more than 60 lines is ignored with a warning | automatic |
| `marker` | line / radar marker size in pt, 2-72: `marker=9` | theme |
| `size` | chart text size in pt (exact: no automatic growth), 6-72: `size=14`. Two values state two sizes: `size=16,14` = data labels (exactly 16, also the category axis and the base of the title) and the value-axis numbers (14) | automatic |
| `legend.size` | legend text size in pt, 6-72 (otherwise `render.chart_legend_scale` x chart text) | scaled |
| `slice.line` | pie/doughnut wedge outline: a color name or `#hex`, optionally `,width` in pt, or `none`: `slice.line=bg`, `slice.line=#FFFFFF,2.5` | `render.chart_pie_line`, `render.chart_pie_line_width` |
| `hl` | comma list of categories **or series** to emphasise (a series name wins; on several series the whole series takes `render.chart_hl`, a line gets a thicker stroke; a name that matches nothing is a `chart-hl` warning listing both): their points take `render.chart_hl` (default `accent`); on a one-series bar/column/waterfall the other points keep their color | none |
| `note` | one-line takeaway: a native callout (class `.chart-note`) inside the chart frame, pointing at the first `hl` point when there is one | none |

CSV cells may be quoted (`"1,240"`), may carry `%` or thousands separators (`1,240`, `12%` → number), and may
use full-width digits; an empty cell is a gap. A cell that is not a number becomes a gap plus a warning.
Dotted keys (`labels.bold=on`, `slice.line=bg`, `legend.size=14`) are plain attributes of the fence. Decisions in one line:
`` ```column {labels=outside labels.bold=on size=16,14 overlap=-5 step=200 min=0 max=1400 gap=60} ``,
`` ```pie {labels=outside+name slice.line=bg,2 size=14} ``, `` ```stacked-column {labels=center totals=off} ``.
A bad value (an out-of-range number, `overlap` on a stacked chart, `+name` on a bar chart, `labels.bold` without
`labels=`) is a `bad-chart-option` warning with a one-line hint and the option is dropped.
A takeaway is two attributes: `` ```bar {hl=郊外大型 note="赤字42店の半数は郊外大型"} ``. Several series keep their colors: an `hl` category gets a `render.chart_hl` outline in each; a line gets a larger marker. A `note` pins the plot area and value axis so the pointer hits the bar; a too-long note shrinks, wraps, then warns (`chart-note`).

Chart look defaults are tokens (`style: render.chart_legend_scale=1.4`; `render.chart_grid=border` is the gridline color, `render.chart_line_width=3.5` the line width in pt, `render.chart_pie_line=bg` / `render.chart_pie_line_width=2` the wedge outline): legend size = `chart_legend_scale` x chart text,
data labels = `chart_label_scale`, pie/doughnut wedge labels = `chart_pie_label_scale` (bold, `chart_pie_label_bold`,
inside the wedge, `chart_pie_label_pos`; a wedge under `chart_pie_label_min` of the total labels outside). The series
palette (`palette`) holds no accent colour in the built-in presets: `accent` is reserved for `hl=`. On a pie, `labels=on`
shows each share once (`36%`), also when the values already add up to 100; `fmt=` keeps the raw values instead. On a
line chart, labels of two series closer than `render.chart_collide_em` label heights alternate above / below the point.
A series under `render.chart_scale_ratio` (10%) of another on the same axis (sales 1280 next to profit 96) gets an info line
`chart-scale`: split it into two charts or state the ratio as a KPI; the chart itself is never changed.

Whole numbers written with thousands separators (`1,240`, `2.100` with `lang: vi`) keep them: labels and the
axis use `#,##0` (shown in the viewer's locale) unless `fmt` is set.

## Table options

Attributes on a table (`{...}` on the line before a GFM table, or on a `table` fence):

| Key | Meaning | Example |
|---|---|---|
| `widths` | column width ratios | `widths=3:1:1:1` |
| `align` | per-column alignment letters `l` `c` `r` | `align=lcrr` |
| `rowh` | exact row height: one value pins every row, a list pins row by row (the last repeats, `auto` frees a row). Pinned rows are never stretched, shrunk or regrown (text size included); text that outgrows a row warns `overflow` | `rowh=0.8in` or `rowh=0.8in,1.05in` |
| `header` | number of header rows (0 = none) | `header=2` |
| `hcol` | number of header columns | `hcol=1` |
| `.zebra` | alternate row fill | |
| `hl` | emphasise the body rows whose **first cell** equals one of these values (comma list; quote a value that holds a comma): tinted fill + bold text | `hl=冷凍食品,海外` |

| `hlcol` | emphasise whole body columns: header texts or 1-based numbers (comma list); the same look as `hl` | `hlcol=2027計画` or `hlcol=3` |

Numeric columns are right-aligned automatically.

**Row emphasis.** `hl=` takes the first-cell values of the rows to stress, the same option name a chart uses:
`{hl=冷凍食品,海外}` (or `{hl="Metro, East",Other}`). Look = tokens `table.hl.fill` (default `accent`, mixed into the
body fill by `table.hl.strength` 0.2; `none` = bold only), `table.hl.color` (default: the cell ink, made readable),
`table.hl.bold`; CSS `tr.hl { background: ...; color: ... }` overrides them. An unknown value is a warning
(`table-hl`) with the closest first cell. `<tr class="hl">` in HTML tables does the same.

**Column emphasis.** `hlcol=` does the same for whole body columns, named by their header text or a 1-based number (`{hlcol=2027計画}`, `{hlcol=2,4}`); with `hl=` both apply. Same look tokens. An unknown name is a `table-hl` warning that lists the header cells; the importer reads the column back (`hlcol=3` in the shape name).

**Gantt.** `{.gantt}` on a table draws every filled body cell after the first column as a native bar spanning its
merged range (`<` continues the bar), with the cell text inside; cells holding only `―`, `-` or nothing stay empty.
The bar look is the `gantt` class (`style: gantt.fill=accent gantt.radius=4`, or `.gantt` in CSS).

```markdown
{.gantt header=2}
| 施策 | 2027 | < | 2028 | < |
|-|-|-|-|-|
| ^ | 上期 | 下期 | 上期 | 下期 |
| IoT標準化 | 新機種へ搭載 | < | 既設機へ | ― |
```

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
`table`, `tr` (`tr.hl` = rows emphasised by `hl=`), `th`, `td`, `code`, `img`, `.chart`, and any `{.class}` / `{#id}`; combined with descendant
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
| Width | `width` (`fit-content` / `max-content` / `display: inline-block` = a text block hugs its text and padding and sits left, or right/center per `text-align`; `40%`, `3in` = fixed width) on blocks in the flow; `auto` resets |
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

## Import: forms read from a foreign deck

`slidemark import` reads the shape names SlideMark draws (`Row 2 num`, `Quote text`, `Timeline 3 dot`, ...). A deck
made elsewhere (python-pptx, PowerPoint: `Rectangle 7`, `TextBox 9`) has no such names, so
`importer/recognise.py` reads the geometry instead, before the title is chosen, and writes the form. It fires only
when every card of a group matches; otherwise the slide stays plain boxes and text. A slide that holds a SlideMark
shape name (`Card 3`, `Text 5`, `Title`) is a built deck and is never read by geometry. Thresholds: `recognise.TH`.

| Drawn as | Imported as |
|---|---|
| cards (same size, 2-8) whose first line is a short figure (`2.1兆円`, `38%`, `+22%`) at least 1.8 x the other text, optional stripe on the card edge | `@kpi` and a label-less `##` per card: the figure line, then the caption; `style:` carries `sN.border-left="9pt solid #1F5FA8"` classes (`{.s1 color=#1F5FA8}` per card), `kpi.fill=` `kpi.align=left` `kpi.note.size=` and `sizes: kpi=48` |
| cards whose first line is `01 02 03` (1.2 x the body), stripe on top | `## [01]{color=#1F5FA8} {.s1}` + body, `sizes: heading=44! body=30!`, `sN.border-top=` |
| a filled square / circle holding only `1 2 3 ...` inside a wide bar, bars alone on the slide (a lead above and a footnote below are fine) | `@rows` with `rows-num.fill=#a,#b,#c`, `rows.fill=`, `rows.size=` |
| the same badges above a card body, or bars beside other content | the slide word `num` (the badges leave, `box.num.fill=` keeps their colour) |
| badges that are squares (beside cards) or circles / rounded (in bars) | `box.num.shape=square` (default circle), `rows-num.shape=circle\|rounded` (default square): only what differs from the default |
| a big quote glyph + one text + a `— name` line (+ panel) | `@quote fill= size=` and `quote.mark.color=` (the glyph is never the title); a bar on the card's left edge: `quote.bar= quote.bar_w=`; the card's height and width: `quote.h= quote.width=`; a right-aligned name line: `quote.by.align=right` |
| a dark filled rectangle with 3-7 short lines of different sizes | one box `{fill=#122B4A color=#FFFFFF}`: label heading, every line a span of its own size (`[9,800円]{size=40 bold=true}`); with `num` on the slide it is a `.kpi` card (so `num` skips it) |
| bars with a left stripe whose one line mixes label, figure and note sizes | `@rows plain` + `rows.stripe=` (bars alone on the slide) or boxes with a stripe class; runs that differ from the first one are spans: `**売上高** [420億円]{size=34 bold=true color=#1F5FA8}` |
| a dark filled card holding one text (not full width) | `{fill=#122B4A color=#FFFFFF}` on the box |

A span `[text]{size=28 color=#E08A1E bold=true}` is the mixed-size inline syntax; a parser without it still reads the
line (the span is plain text then, at the box size).

## Import: foreign decks

`slidemark import deck.pptx` writes SlideMark text. A deck SlideMark built comes back from its stored design and
from shape names. A deck made elsewhere (python-pptx, PowerPoint, Keynote) has loose shapes, so the importer
recognises its design from **geometry** (`importer/recognise2.py`; thresholds in one table, `T`) and writes the
token instead of the boxes. Each recognition is conservative: it fires only when the geometry matches, else
the older fallback (boxes, plain text) stays. Decks with their own design part are never touched.

| Drawn with loose shapes | Imported as |
|---|---|
| a slide-filling rectangle behind the cover | `@bg=primary dark` (a declared colour name when the fill matches one, else `#hex`) |
| a thin bar at the cover's left / a strip on its top or bottom edge | `cover.bar=#E08A1E` (`@edge` at the slide edge) + `cover.bar_w`, `cover.top_bar` / `cover.bottom_bar` (+ `_h`), with `cover.band=none cover.band_h=66%` placing the title block where the text was |
| thin full-width strips on the top / bottom edge of most slides | `top.bar` / `bottom.bar` (+ `_h`) |
| content that starts at another margin (0.6 in left and right) / another distance under the title (0.45 in) | `margin=0.6in layout.top_gap=0.45in` in the header |
| a row of tall header-band cards from the body top | `box.h=4.2in box.anchor=top` on the slide (+ `heading.band=` `bullet=■`) |
| a thin full-width line under the title band on most slides (a short segment at its left end) | `title.rule=#E08A1E title.rule_h=0.06in` (`title.rule2` + `title.rule2_w`) |
| a bare number text at the bottom right equal to the slide number | `num: on` (it is not a footnote) |
| a row of chevron / pentagon shapes of one size, each with a card under it | `@3 steps` + `style: steps-arrow.fill=a,b,c steps-arrow.size=24 steps-card.size=26`; pentagons: `render.chevron_shape=pentagon`; the exact geometry `steps-arrow.h=0.75in steps-card.h=2.7in steps.gap=0.2in`, arrow ink `steps-arrow.color= steps-arrow.bold=on steps-arrow.align=left`; the point depth of the original's `a:avLst` as `steps-arrow.point=0.5` (deck-wide when most arrows share it) |
| a full-width dark filled bar in the lower part with one text in it, nothing but the footer below it | the `>` conclusion + `conclusion.fill=` (when it is not `primary`), `conclusion.size=` and, under a steps row, `conclusion.h=` |
| a shadow (`a:outerShdw`) on the cards of the deck | `card.shadow="0 3 6 #00000040"` in the header when most cards (at least two, at least half) share it; a card with another shadow says `{shadow="..."}`, one with none `{shadow=off}`; when the cards differ every box states its own. A shadow that only the theme's effect style gives (`a:effectRef`, no `a:outerShdw`) is not read |
| a body table row whose cells share a tinted fill the other rows do not (zebra rows are plain) | `{hl=<first cell>}` + `style: table.hl.fill=#FDF1DE table.hl.strength=1` |
| table cells with runs of another size or colour | `[9,800円]{size=26 color=#E08A1E}` spans against the table's base size `{size=15}` (a table's text size is `size=`) and the deck ink; a glyph cell (`▶`) keeps its colour |
| a chart with per-bar / per-series fills, label size, gap | `colors=#E08A1E,#1F5FA8,#1F5FA8` (one per bar on a one-series bar/column, else per series / slice), `size=18`, `gap=45` (only what differs from the build's default palette and gap) |
| the one big card beside a chart (a total, then coloured values) | a `##` box with spans, `@2:1` kept |
| pentagons / chevrons of one size, a card under each (a little narrower than its arrow) holding its own text, a `STEP n` caption under every card (`importer/recognise3.py`, thresholds `TH3`) | `@4 steps num` + `steps-arrow.fill=a,b` + `steps.caption_color=` `steps.caption_size=` (`steps.caption="Phase {n}"` when the pattern is not `STEP {n}`), `steps-card.bold` `steps-card.align` `steps-card.fill` `steps-card.line`; text sizes are left out on purpose (an explicit size turns the sparse-group layout off and the strip sticks to the title) |
| equal cards, each with a centred label on top, a big number, an optional thin divider rule, a coloured delta below, an optional top stripe | `@kpi` + `kpi.rule=#C9D2DE kpi.rule_h= kpi.rule_w=1.68in`, `kpi.stripe= kpi.stripe_h=`, `kpi.label.size/bold/color`, `kpi.note.size/bold/color`, `kpi.color`, `kpi.fill` `kpi.line`, `kpi.h=4.4in`, `sizes: kpi=34`; centred is the default (a left-aligned card in the group: not read) |
| equal cards with a dark header rectangle holding the title on the top edge and a body of `■ text` lines | boxes (`@4`) with `heading.band=primary heading.align=center`, `- text` bullets with `bullet=■ bullet.color=#2A9D8F`, `card.line=`, `sizes: heading=20! body=22!` |
| a filled bar low on the slide that ends above the footer text (up to 93% of the height; `recognise2` stops at 90%), one text in it, dark | the `>` conclusion + `conclusion.fill=` + `conclusion.size=` |

```markdown
# 3年間のプロダクト計画
style: steps-arrow.fill=#1F5FA8,#1B8A8F,secondary steps-card.size=26 conclusion.size=26
@3 steps
## 2027年度：
在庫管理と請求書の自動照合をリリース
> 各年度の第1四半期に大型リリース、第3四半期に改善リリース
```

A span's `size=` needs the span-size syntax of lane A (DL3d); until the parser reads it the size is ignored and the colour still applies.

## Diagnostics: design feedback

`build` and `check` print two deck-level warnings (no slide number, never fixed by `--fix`, never fail a build) that
tell an agent whether it made design decisions (`docs/DESIGN_REQUIRED.md`, "Tightened rules"):

| Rule | Fires when | Message -> hint |
|---|---|---|
| `design-none` | the header lacks some of `colors:` `fonts:` `sizes:` `style:`; one warning names every missing line. A deck ` ```css ` fence or a theme file (`theme: ./brand.yaml`, `template.pptx`) stands in for `style:`; `theme: <preset>` alone never counts | `design: fonts: sizes: not stated` -> `add fonts: sizes: to the header` (when `style:` is missing the hint adds `(a css fence or theme file also counts for style:)`) |
| `design-slide` | a content slide is short of one of the three groups below; one warning per deck lists the slides | `slides 4 (values), 8 (form, emphasis) are short of a decision` -> `per slide state form (@N @steps table chart), one emphasis (.hero hl= ==x==) or @noemph, a value (size= color= fill= x y w h) or @defaults` |

The three groups a content slide states (cover, section and slides with nothing but a title and notes are exempt):

1. **form**: a layout directive (`@3` `@2x2` `@1:2` `@aab/aac`, `@steps` `@chevron` `@flow` `@rows` `@items` `@kpi`
   `@free` `@blank` `@center` `@html` `@timeline` ..., `a>b` connectors) or a block that is not the default list:
   table, chart, image, code, boxes with headings, KPI cards, mermaid diagram, callout.
2. **emphasis**: exactly one: `.hero`, `{.accent}` / `{.danger}` / `{.success}` on one element, `hl=` / `hlcol=` /
   `note=` on a table or chart (`hl=` + `note=` on one chart is one takeaway), `==x==`, `[x]{.class}`, a badge (a column of
   badges in one table is one), or the directive `@noemph` (no focal figure on this slide). Counted per element, so
   two emphasised elements are reported as `slide 5 (emphasis: 2 stated, keep one)`.
3. **values**: at least one chosen value: `size=` `color=` `fill=` `line=` `x y w h` on an element, chart `colors=`
   `size=` `labels=<pos>` `legend=` `fmt=` ..., table `widths=` `rowh=` `align=`, `.zebra`, `icon=`, `@bg=` `@gap=`
   `@dark` `@light` `@dense`, a slide-scoped `sizes:` / `style:` line or ` ```css ` fence, or the directive `@defaults`
   (the deck frame already serves this slide).

Not decisions: `{.kpi}`, `labels=on`, a chart `title=`, plain bold/italic/links, `@build`, `@t=`, `@hidden`, and what the
parser derives itself. `@noemph` and `@defaults` are ordinary slide directives (`@2 noemph defaults`): they draw nothing,
and the importer keeps them (they ride in the design part). Colour-coding boxes is a value, not an emphasis:
`{line=success}`, not `{.success}`.

`build` also prints the stated keys before the `look:` line, one line, no colour:
`design: colors fonts sizes style footer; 9/14 slides decided form+emphasis+values`, with `; short: 4 (values), 8 (form,
emphasis)` appended when some slides are short (`design: none; 0/15 ...` when nothing is stated). The count leaves out
the exempt slides and counts slides with all three groups, so `n == total` means no `design-slide` warning. Keys:
`colors fonts sizes style css theme-file footer num`. `slidemark check --format json` carries both warnings with their
`rule` names (`design-none`, `design-slide`; `slide` is `null`).

## Build output: fit lines and ignored attributes

`slidemark build` prints, in this order: auto-fixes, diagnostics (grouped), **one fit line per slide**, `design:`,
`look:`, and the facts line. The fit line is read off the layout result (no second layout, no render) and answers what
an agent otherwise opens an image for: did my choice take effect, and how does the slide sit.

```text
slide 2: lead + 4 kpi cards 72% of body, value 48->29pt (shrunk to fit), free 12% above, 16% below
slide 4: 4 boxes (2x2), text 14->24pt (grown), free 17% below, took icon
slide 5: steps 4, arrows + cards fill 92%, card text 14->24pt (grown)
slide 6: table 5x4 at 13->18pt (grown), zebra, hl 2 rows, fills body
slide 8: lead + list 4 items 14->28pt (grown), free 22% below
slide 11: line chart, 3 series, labels on, hl=北米, note, fills body
```

A line is `slide N: <form> [+ <form>], <facts>`:

| Part | Says |
|---|---|
| form | what the slide became, joined with ` + `: `timeline 5 (h, marks on)`, `vs 2 sides`, `matrix 2x2`, `funnel 4 stages`, `cycle 4 nodes`, `agenda 5 rows`, `statement + caption`, `lead`, `N kpi (hero) cards NN% of body`, `steps N`, `chevron N (compact)`, `N boxes (2x2 / row / stack)`, `table RxC at NNpt`, `<kind> chart, N series`, `list N items NNpt`, `rows N bars`, `image`, `code`, `callout`, `free N blocks, M pinned`; `html, N shapes` for `@html`; `cover` / `section` with the title size and `band composed` or `centred block` (a `{size=}` on the cover title keeps the old centred look) |
| `A->Bpt (shrunk to fit / grown)` | the text size asked (the role size in `sizes:`, `kpi.value.size=`, `{size=}`) against the size drawn; a size within 4% of the ask prints once. Sizes you pin (`size=`, `sizes: body=14!`) never move |
| `value`, `card text`, `text`, `at` | which text: the KPI number, step card text, box text, table text |
| `free N% below / above / right / beside` | the empty part of the body under (over, beside) the content, from 10% (above: 20%); `fills body` when nothing is left |
| `sparse: 42% free` | last on the line: the body stays more than `layout.sparse_note` (0.35) empty after every growth pass (text is capped by `layout.grow_max`); replaces `free N% ...`. A composition cue, not a size cue (see `sparse` below) |
| `bar 24pt` | the size of the `>` conclusion bar text (never under the slide's body text, `conclusion.floor`) |
| `conclusion bar attached` | the `>` bar moved up under a lone table |
| chart facts | `labels on`, `hl=<points>`, `note` when the option took; table facts `zebra`, `hl N rows` |
| `took size=44 icon` | the attributes written on the slide's elements that the layout honoured (`size` with its value) |
| `ignored h y` | the ones it did not (each also has an `attr-ignored` warning) |

`--quiet` (`-q`) or the header line `fit: off` leaves the lines out; the lines stay out of `check`. A slide the map
cannot read prints `slide N: (no fit data)`.

### `sparse`

An **info** (it must not cost a rebuild), once per content slide that ends sparse, on the same number as the end of
its fit line: `info slide 7 sparse: slide 7 is sparse (42% free) -> merge it into a neighbour, add a figure/table/chart,
or change its form (@rows, @items, @steps, side by side); bigger text is capped by layout.grow_max=1.5`. Several
sparse slides print one line (`info slides 7,9 sparse: slide 7 is sparse (42% free); slide 9 ...`). The free share is
the part of the body rectangle outside the bounding box of the content (chrome and a conclusion bar attached to the
body count as content); covers, sections, `@free` and `@html` slides are never sparse. `layout.sparse_note` is the
threshold (`0.99` silences it); the check lives in `src/slidemark/fit.py` (`SPARSE`, `fit_report`).

### `attr-ignored`

A warning (`attr-ignored: bold= on a KPI card is not honoured -> style: kpi.value.bold=on bolds the number`) for every attribute the layout or renderer does not act on, once per
slide, kind and attribute. The detection is the table `HONOURED` / `IGNORED` in `src/slidemark/honour.py`: for each
element kind, each attribute of `x y w h size color fill line font align valign bold italic radius opacity pad fit
icon shadow rotate shape z` is honoured or ignored, never undecided; `tests/test_honour.py` checks that, probes every cell against the real
layout and renderer, and checks that the warning carries the hint. `@free` honours `x y w h` on every kind. Ignored:

| Kind | Ignored attributes |
|---|---|
| `title`, `cover` (slide titles) | `fit` `icon` |
| `box` (a `##` box in any grid, `flow`) | `fit` |
| `item` (`### text {.item}` card) | `icon` `fit` |
| `kpi` (`y` `h` `w` place the row, also beside a list or table; `x` makes a card absolute) | `fit` |
| `step` (box of an `@steps` row; `valign` moves the text once a conclusion bar or `fill_steps` stretched the card) | `x` `y` `w` `h` `fit` |
| `chevron` (compact `@chevron` row) | `radius` `fit` |
| `text` (a paragraph or list outside a box; `radius` and shape show with `fill` or `line`) | `fit` `icon` |
| `callout` | `fit` `icon` |
| `image` | `color` `font` `bold` `italic` `icon` |
| `table` (`align` is one letter per column) | `radius` `rotate` `shape` `fit` `icon` |
| `chart` (`radius` and shape show with `fill` or `line`, `opacity` with `fill`, `align` with `w`, `valign` with `h`) | `rotate` `fit` `icon` |
| `code` | `fit` `icon` |
| `rows` (an `@rows` list) | `fit` `icon` |
| `row` (one line of an `@rows` list) | `x` `y` `w` `h` `valign` `radius` `opacity` `pad` `shadow` `rotate` `shape` `z` `fit` `icon` |
| `list item` (`- text {color=danger}`) | `x` `y` `w` `h` `fill` `line` `radius` `opacity` `pad` `valign` `shadow` `rotate` `shape` `z` `fit` `icon` |
| `stage` (a `##` box of `@timeline` `@funnel` `@pyramid` `@cycle` `@stairs` `@nested` `@flow disc`: honours `fill` `color`, and `icon` on `@cycle` `@nested` `@flow disc`) | `x` `y` `w` `h` `size` `line` `font` `bold` `italic` `align` `valign` `radius` `opacity` `pad` `shadow` `rotate` `shape` `z` `fit` `icon` |
| `shape` (a content-less `{x= y= w= h= shape= fill=}` block: honours `x y w h fill line radius opacity shadow rotate shape z`) | `size` `color` `font` `align` `valign` `bold` `italic` `pad` `fit` `icon` |
| `formtext` (the text of `@agenda` `@statement`: honours `size` `color`) | `x` `y` `w` `h` `font` `bold` `italic` `align` `valign` `fill` `line` `radius` `opacity` `pad` `shadow` `rotate` `shape` `z` `fit` `icon` |

`size=` on a box with no text of its own sizes nothing (it sizes the box text, not its heading): `sizes: heading=` or
`h2.size=` does. `style:` tokens that need an element the deck does not contain warn the same way, once per token on its
header line: `kpi.*` without a `.kpi` card, `steps*` / `steps-arrow` without `@steps`, `rows*` without `@rows`,
`table.*` without a table, `palette` / `render.chart_*` without a chart, `bullet*` without a list, `heading.*` / `card.*` /
`box.*` without a box, `box.num.*` without an `@num` slide, `item.*` without item cards, `rows.glyph*` without `@rows plain`,
`timeline.*` `vs.*` `matrix.*` `funnel.*` `pyramid.*` `cycle.*` `agenda.*` `statement.*` `stairs.*` `nested.*` `flow.*` (without `@flow disc`) `iconlist.*` `quote.*` `split.*` `proscons.*` `progress.*` `harvey.*` `heatmap.*` `pins.*` without that form's slide, `render.chevron_shape` without arrows, `cover.rule_w` / `rule_pos` without `cover.rule=<color>`, `footer.*` without `footer:` / `num:`, `lead.*` without a lead; the `cover.*` chrome (`rule` `bar`
`pad` `gap` `footer`) needs the composed cover (`cover.band_h` above 0 and no `{size=}` on the cover title); and
`chevron.*` styles nothing (arrows follow `primary`, `steps-arrow.fill=` colours `@steps`). The table is `STYLE_NEEDS`
in the same module.
