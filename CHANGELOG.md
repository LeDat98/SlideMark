# Changelog

All notable changes. Versions follow semver once 0.1.0 is published.

## Unreleased (0.1.0 candidate)

### Syntax
- Headings as structure (`#` slide, `##` box), one `@` grid line (`@3`, `@2x2`, `@1:2`, `@aab/aac`), `@end`.
- Components: `.kpi` boxes, callouts `> [!note|tip|warn|caution]`, badges `[x]{.badge}`, connectors `@ a>b a-b`,
  `flow` arrows, `chevron` steps.
- Charts as CSV fences (10 kinds) with options `legend labels fmt min max colors axis`; tables with merges and
  options `widths align header hcol .zebra`; CSV edge cases (quotes, `1,240`, `12%`, full-width digits, `▲`).
- ` ```math ` → native OMML equations; ` ```mermaid ` flowcharts → native shapes + connectors; HTML subset input.
- Lenient input: Marp/Slidev/Markdown variants accepted with warnings and did-you-mean hints.

### Layout and rendering
- Auto arrangement, 12-column tracks, full-width rows below a grid, sparse-slide growth and vertical balance.
- Real font metrics, autofit with `min_font_size`, CJK measurement and kinsoku line breaking.
- Themes `default`, `midnight`, `jp-business`; user `.pptx`/`.potx`/`.yaml` themes with native footer and
  slide-number placeholders.

### Tooling
- CLI: `build`, `check` (`--format json`, layout linter), `preview`, `docs [topic]`, `schema`, `skill install`,
  JSON and HTML deck input.
- Linter: overflow, off-slide, overlap, contrast, tiny-text, alt, connector-crosses, missing-end.
- Skill: `SKILL.md` (≤ 1,500 tokens) + 5 reference pages (≤ 800 tokens each).
- Bench: token corpus + gate, layout-inference metric, agent eval harness.
