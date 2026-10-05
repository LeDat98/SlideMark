# Feature matrix

Definition of Done steps: D1 docs example · D2 parser test · D3 fuzz-safe · D4 render test · D5 opens in
LibreOffice · D6 gallery looks right · D7 lint rule · D8 bench no regression. Mark `x` when done, `-` when the
step does not apply (no visual risk to lint, or no syntax).

| Feature | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 |
|---|---|---|---|---|---|---|---|---|
| Deck header / front-matter | x | x | x | x | x | x | - | x |
| Slides, cover/section inference | x | x | x | x | x | x | - | x |
| Boxes (`##`), auto arrangement v2 | x | x | x | x | x | x | x | x |
| `@` grid line (N, CxR, ratios, areas), row groups | x | x | x | x | x | x | x | x |
| flow / chevron | x | x | x | x | x | x | x | x |
| lead / conclusion / footnotes | x | x | x | x | x | x | x | x |
| Inline styles, links, slide jumps | x | x | x | x | x | x | - | x |
| Lists (native bullets/numbers), line-per-line text | x | x | x | x | x | x | x | x |
| Images (contain/cover/stretch) | x | x | x | x | x | x | x | x |
| SVG pictures (`![](a.svg)`, ```` ```svg ````): native svgBlip + PNG fallback, sanitized | x | x | x | x | x | | - | x |
| Video / audio (`![](a.mp4){poster autoplay loop}`) | x | x | x | x | x | x | x | x |
| Tables + merges, CSV table, table options | x | x | x | x | x | x | x | x |
| Charts (10 kinds) + options | x | x | x | x | x | x | - | x |
| Code highlighting | x | x | x | x | x | x | x | x |
| Speaker notes | x | x | x | x | x | - | - | x |
| `@end`, missing-end hint | x | x | x | x | x | x | x | x |
| `.kpi` boxes | x | x | x | x | x | x | x | x |
| Callouts `> [!note]` | x | x | x | x | x | x | x | x |
| Badges `[x]{.badge}` | x | x | x | x | x | x | x | x |
| Connectors `@ a>b` | x | x | x | x | x | x | x | x |
| Icons `icon=name` | x | x | x | x | x | x | x | x |
| Box heading band (jp-business) | x | - | - | x | x | x | x | - |
| Math (OMML) | x | x | x | x | x | | - | x |
| Mermaid flowcharts → native | x | x | x | x | x | x | x | x |
| HTML subset → native, image fallback | x | x | x | x | x | | - | x |
| HTML (Chromium-measured) → native shapes, `{render=native\|image}` | x | x | x | x | x | | - | x |
| Themes default / midnight / jp-business | x | x | - | x | x | x | x | - |
| User templates `.pptx/.potx/.yaml` | x | x | x | x | x | x | - | - |
| Build animations, transitions, sections, hidden | x | x | x | x | x | - | - | x |
| `check` linter + JSON | x | x | x | - | - | - | x | - |
| `docs`, `schema`, `skill install`, JSON input | x | x | x | x | - | - | - | x |
| `check --fix [-o]` mechanical source repairs (`fix.py`) | x | x | x | - | - | - | - | - |
| `.pptx` import (round trip) | x | x | x | x | x | - | - | x |
| `review` design critique (`design-*` rules + score, `--png`) | x | x | x | - | - | - | x | - |
