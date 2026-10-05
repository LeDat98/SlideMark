# Design: your own look

SlideMark has no fixed look. A theme is only a preset of design tokens; any deck can change every token.
Pick a preset (`default`, `midnight`, `jp-business`) or start from `theme: none` and declare the design:

```markdown
theme: none
colors: bg=#0B1020 fg=#E6E8EF primary=#7C5CFF accent=#00D1B2 muted=#8A90A6 surface=#141A2E border=#2A3150
fonts: heading="Inter" body="Inter"
sizes: title=40 body=16
style: radius=14 card.shadow="0 8 24 #00000055" title.band=none

# Launch plan
> Ship in three steps
## Build
- Core engine
## Test
- 20 pilot users
## Ship
- Public beta
```

Lines (header only, before the first `#`):
- `colors:` any name. `primary` is the accent of KPIs, badges, bars and charts; `surface` fills cards,
  `border` outlines them, `muted` is secondary text. New names (`brand=#FF5A1F`) work everywhere.
- `fonts:` `heading` `body` `mono` `ea` (Japanese/Chinese/Korean text).
- `sizes:` pt per role: `title` `heading` `body` `lead` `caption` `footnote` `table` `code` `cover-title`.
- `style:` everything else:
  - cards: `radius=14` `padding=12pt` `shadow="0 6 18 #00000055"` `border=none` `card.fill=#141A2E`
  - gradients: `card.fill="linear-gradient(135deg, #7C5CFF, #00D1B2)"`
  - title band: `title.band=primary` (`none` = no band), `title.band.color=#FFFFFF`
  - box heading band: `heading.band=primary`, `heading.color=accent`
  - tables: `table.header.fill=primary` `table.header.color=#FFFFFF`
  - charts: `palette=primary,accent,#FF5A1F`
  - spacing: `gap=12pt` `margin_x=0.6in` `layout.top_gap=0.3in`; `layout.grow=off` keeps your sizes
  - your own class: `hero.fill=#FF5A1F hero.color=#FFFFFF` then `## Title {.hero}`

`slidemark tokens` lists every token and its value (`slidemark tokens deck.md` for your deck). A theme
file `brand.yaml` holds the same tokens (`colors: {primary: "#7C5CFF"}`) and is used with `theme: ./brand.yaml`.

Tips: keep text/background contrast high (`check` warns), use 2–3 brand colors plus neutrals, and set
`surface`/`border` when you change `bg` so cards match a dark background.
