# 7-day foundation plan

Each day: one orchestrator session defines contracts and merges, 3–4 Sonnet subagents code in parallel
in separate git worktrees (one module each, so they don't conflict). The day ends with tests green,
the README gallery refreshed and the bench recorded.

Target at the end of day 7: `pip install slidemark` → Markdown with dense Japanese-style slides, native charts and
tables, layouts, themes, `check`/`preview`/`docs` CLI, SKILL.md for agents, CI gates.

| Day | Parser | Layout / theme | Renderer | Tooling / QA |
|---|---|---|---|---|
| **1** | Front-matter, slide split, titles, text, lists, inline, images, GFM tables + merges, code, chart CSV, `:::`, `{}` attrs, notes | Layout engine v0 (cover, section, content, two-column, auto inference, containers row/grid/column), text measurement v0, 2 extra themes | Title placeholder, rich text runs, native bullets, `<a:ea>` font, tables + merges, images, code highlight, charts, shapes, container fills, background, notes | CLI `build`/`preview`, LibreOffice preview, `scripts/gallery.py` + README gallery, CI, test helpers, example decks |
| **2** | Lenient parsing (Marp/Slidev variants), diagnostics with hints, fuzzing | Real font metrics, autofit (shrink to `min_font_size`), overflow diagnostics, CJK line breaking | Autofit flags, table styling (zebra, header), image crop/cover | Golden XML snapshots, image diff, `BASELINE.json` + CI token gate |
| **3** | Dense components: `kpi`, `steps`, `badge`, footnotes, side notes | **Dense layouts** for Japanese slides: 12-column grid, header band + lead, multi-box, `density: dense` | Shapes + connectors/arrows, numbered badges, callouts, rounded cards, icons | Dense JP example decks (≥ 5), gallery review, lessons |
| **4** | Chart options, table options, CSV edge cases | Chart/table sizing, legend space | All chart kinds, number formats, data labels; math (OMML) | `check` linter v1 (overflow, off-slide, overlap, contrast, missing alt), JSON output |
| **5** | Docs-example extraction | Templates: use a user `.potx`/`.pptx` (map placeholders) | Master/layout reuse, footer/slide number fields | `slidemark docs`, `schema`, `skill install`, SKILL.md + `reference/` with token budgets |
| **6** | `html` and `mermaid` fences | HTML → native via Playwright box measurement | HTML fallback to image, Mermaid → image | Agent eval harness v0 (tasks, token/iteration metrics in history) |
| **7** | Slide links, sections, `hidden` | Hyperlink/TOC helpers | Transitions, build animations (`.build`), hyperlinks, sections | Packaging (PyPI-ready), release notes, full gallery, AGENT_TIPS review |

## Day 1 status
- [ ] Contracts: `ir.py`, `theme.py`, `units.py`, stage stubs, `docs/SYNTAX.md`
- [ ] Parser v0
- [ ] Layout v0 + themes
- [ ] Renderer v0
- [ ] Tooling: CLI, preview, gallery, CI, examples
- [ ] Merge, end-to-end test, README gallery, bench
