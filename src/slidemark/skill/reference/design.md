# Design: your own look

A theme is a preset of design tokens. Pick a preset (`default`, `midnight`, `jp-business`) or start
from `theme: none` and declare the design:

```markdown
theme: none
colors: bg=#0B1020 fg=#E6E8EF primary=#7C5CFF accent=#00D1B2 surface=#141A2E border=#2A3150
fonts: heading="Inter" body="Inter"
sizes: title=40 body=16
style: radius=14 card.shadow="0 8 24 #00000055" title.band=none

# Launch plan
## Build
- Core engine
## Ship
- Public beta
```

Lines (header only, before the first `#`):
- `colors:` any name. `primary` is the accent of KPIs, badges, bars and charts; `surface` fills cards,
  `border` outlines them, `muted` is secondary text. New names (`brand=#FF5A1F`) work.
- `fonts:` `heading` `body` `mono` `ea` (CJK text).
- `sizes:` pt per role: `title` `heading` `body` `lead` `caption` `footnote` `table` `code` `cover-title`.
- `style:` everything else:
  - cards: `radius=14` `padding=12pt` `shadow="0 6 18 #00000055"` `border="0.75pt solid #B08D57"`
    `card.fill=#141A2E` (`none` = off)
  - gradient: `card.fill="linear-gradient(135deg, #7C5CFF, #00D1B2)"`
  - title band: `title.band=primary` (`none` = no band), `title.band.color=#FFFFFF`
  - box heading band: `heading.band=primary`, `heading.color=accent`
  - tables: `table.header.fill=primary` `table.header.color=#FFFFFF`
  - charts: series colors = `palette=primary,accent,#FF5A1F` 
  - spacing: `gap=12pt` `margin_x=0.6in`; `layout.grow=off` keeps sizes
  - element css: `h1.letter-spacing=2pt` `th.background=#123456` `box.border-radius=14` (selector.property)
  - your own class: `hero.fill=#FF5A1F hero.color=#FFFFFF` then `## Title {.hero}`

`slidemark tokens [deck.md]` lists every token; a YAML file of them is a `theme: ./brand.yaml`.

CSS fence (header = whole deck, inside a slide = that slide), for looks tokens cannot say:

````markdown
```css
h1 { text-transform: uppercase; letter-spacing: 2pt }
.box > h2 { border-bottom: 2px solid #FF6B6B }
tr:nth-child(even) td { background: #FAFAFA }
```
````

Selectors: `slide` `slide.cover` `h1` `h2` `p` `li` `.lead` `.conclusion` `.footnote` `.box` `.kpi` `table` `th`
`td` `tr` `code` `img` `.chart`, your `{.class}` / `{#id}`. Unsupported properties warn.

Whole-slide HTML: `@html` under the title, then one ` ```html ` fence (absolute positioning, flex/grid,
gradients, shadows, inline SVG become editable shapes). `var(--primary)` reads your tokens.

Dark `bg`: also set `surface` and `border`. Keep contrast high.
