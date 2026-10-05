# Changelog

All notable changes. Versions follow semver once 0.1.0 is published.

## Unreleased (0.1.0 candidate)

### Design freedom
- No fixed look: every color, font, size, spacing, band, card style and layout constant is a token
  (`slidemark tokens`); built-in themes are YAML presets (`src/slidemark/presets/`); `theme: none` is a neutral canvas.
- Header token lines `colors:` `fonts:` `sizes:` `style:` (new classes such as `hero.fill=` too), validated with
  did-you-mean hints; shorthands `border="0.75pt solid #B08D57"`, `fill=none`, `shadow=none`.
- ` ```css ` fences (deck or slide): 34 CSS properties mapped to native PowerPoint (gradients, shadows, per-side
  borders, letter-spacing, text-transform, rotation, grid templates, table cell styles), selector matching.
- `@html` slides and `slidemark build deck.html`: Chromium layout converted to native shapes (gradients, shadows,
  rotation, ellipses, pills, simple inline SVG); theme tokens as CSS custom properties.
- `@free` slides: explicit `{x y w h}` positions, no automatic arrangement.
- The design source (tokens, CSS, HTML) survives `slidemark import` (customXml part).

### Syntax
- Headings as structure (`#` slide, `##` box), one `@` grid line (`@3`, `@2x2`, `@1:2`, `@aab/aac`), `@end`.
- Components: `.kpi` boxes, callouts `> [!note|tip|warn|caution]`, badges `[x]{.badge}`, connectors `@ a>b a-b`,
  `flow` arrows, `chevron` steps.
- Charts as CSV fences (10 kinds) with options `legend labels fmt min max colors axis`; tables with merges and
  options `widths align header hcol .zebra`; CSV edge cases (quotes, `1,240`, `12%`, full-width digits, `▲`).
- SVG images (`![x](a.svg)`, ` ```svg `): native Office SVG with a PNG fallback, sanitized.
- Video/audio: `![alt](x.mp4)` / `.mp3` embed native media (poster, `autoplay`, `loop`).
- ` ```html {render=native} `: any HTML/CSS laid out in Chromium and converted to native shapes.
- ` ```math ` → native OMML equations; ` ```mermaid ` flowcharts → native shapes + connectors; HTML subset input.
- Lenient input: Marp/Slidev/Markdown variants accepted with warnings and did-you-mean hints.

### Layout and rendering
- Auto arrangement, 12-column tracks, full-width rows below a grid, sparse-slide growth and vertical balance.
- Consulting-grade layout: top-anchored body, content-sized cards/chevrons/trees/table columns, distinct chart
  palettes with contrast-aware data labels.
- Bounded layout search (≤ 6 candidates scored like the design critic; rule choice wins ties).
- Real font metrics, autofit with `min_font_size`, CJK measurement and kinsoku line breaking.
- Themes `default`, `midnight`, `jp-business`; user `.pptx`/`.potx`/`.yaml` themes with native footer and
  slide-number placeholders.

### Tooling
- CLI: `build`, `check` (`--format json`, layout linter), `preview`, `docs [topic]`, `schema`, `skill install`,
  JSON and HTML deck input.
- Linter: overflow, off-slide, overlap, contrast, tiny-text, alt, connector-crosses, missing-end.
- Skill: `SKILL.md` (≤ 1,500 tokens) + 5 reference pages (≤ 800 tokens each).
- Bench: token corpus + gate, layout-inference metric, agent eval harness.
- `slidemark review` (design critique + score), `slidemark check --fix` (mechanical source repairs).
- `.pptx` import round trip: 98% of 111 decks lossless (OMML → LaTeX, transitions, build, sections, code
  language); foreign python-pptx decks import at 0.975 fidelity.
- `python -m slidemark.xsd deck.pptx`: ECMA-376 schema validation (markup compatibility resolved to the
  fallback); `bench/xsd_fuzz.py` validates fuzzed decks. CI on Python 3.10–3.12 with a coverage report.
