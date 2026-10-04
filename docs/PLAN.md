# 7-day foundation plan

Each day: one orchestrator session defines contracts and merges, 3–4 Sonnet subagents code in parallel
in separate git worktrees (one module each, so they don't conflict). The day ends with tests green,
the README gallery refreshed and the bench recorded.

Levels: days 1–2 → **L1**, days 3–4 → **L2**, days 5–7 → **L3** (see `docs/TARGETS.md`). After day 7 the
daily routine keeps climbing L4 → L7, picking the unchecked gates with the best value per day.

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

## Daily routine (runs automatically at 02:45 JST)
1. Read `CLAUDE.md`, `docs/LESSONS.md`, this plan, `docs/TARGETS.md`, the last entries of `docs/DAILY_LOG.md`.
2. Pick the first day below that is not fully checked. If the previous day left unchecked items, finish them first.
3. Split the day into 3–4 work packages with **disjoint file ownership**; spawn one Sonnet subagent per package
   (Agent tool, `model: sonnet`, `isolation: worktree`), all in one message so they run in parallel.
   Each subagent: reads the contracts, codes + tests its package, commits in its worktree, reports branch,
   changed contracts, new deps, lessons (≤ 300 words). Subagents never edit LESSONS/AGENT_TIPS/PLAN/README.
4. Merge every branch, resolve conflicts, make tests + ruff green, run `scripts/gallery.py` (README images),
   `bench/count_tokens.py --record`.
5. Update: checkboxes here and in `TARGETS.md`, `LESSONS.md` (pitfalls met), `AGENT_TIPS.md` (verified tips),
   one entry in `DAILY_LOG.md` (≤ 10 lines: done, metrics, problems, next). Commit and push.

## Day 1 work packages
- **Parser** (`src/slidemark/parser/`, `tests/test_parser*.py`): implement `parse()` per `docs/SYNTAX.md`.
  Pre-split slides on `---` outside fences; deck head-matter keys → `Deck`, slide keys → `Slide`; markdown-it-py +
  mdit-py-plugins (attrs, attrs_block, colon fence or custom `:::` parsed recursively with line offsets);
  contiguous paragraphs/lists merge into one `Text`; lone image → `Image`; GFM table with `<`/`^` merges; chart CSV
  fences; `table`/`csv` fences; `mermaid`/`math`/`html` → `Raw`; `???` and `<!-- -->` notes; `[x]{.primary}` → run
  color; `{}` keys → `Box`/`Style`/classes/`attrs`. Never raise: `Diagnostic` with line + hint. Hypothesis fuzz test.
- **Layout + themes** (`src/slidemark/layout/`, `src/slidemark/theme.py`): `layout_slide()` → `Placed` list in
  z-order: title/subtitle/lead area, cover/section/content/two-column/blank + inference rules, containers
  (column/row/grid, gap, padding, fill → a `Placed` for the container itself), explicit `{x y w h}` relative to
  parent, footnotes at bottom, footer + slide number. Style merge: theme role defaults → classes → inline.
  `layout/measure.py`: Pillow metrics (Liberation Sans ≈ Arial, IPAGothic for CJK), word wrap for Latin,
  per-char wrap for CJK, autofit `font_scale` down to `min_font_size`, `overflow` diagnostic. Themes: `default`,
  `midnight` (dark), `jp-business` (dense, navy title band, 10.5–12pt). Tests: in-bounds, no sibling overlap.
- **Renderer** (`src/slidemark/render/`, `tests/test_render*.py`): tests build `Placed` by hand. Title in the title
  placeholder (outline/accessibility), other text in text boxes; runs (bold/italic/underline/strike/sup/sub/code/
  color/highlight/link, `#3` → slide jump in a second pass); native bullets/numbering per level; `<a:latin>` +
  `<a:ea>` fonts, `lang`; tables with merges and explicit fills (no default blue style); images contain/cover/
  stretch, missing → placeholder + diagnostic; code with pygments colored runs; all chart kinds python-pptx
  supports with theme colors; auto shapes by name; container fill/border; `Raw` → labeled dashed placeholder;
  background color; notes; hidden; core properties. Reopen the file in tests and assert.
- **Tooling + QA** (`src/slidemark/cli.py`, `src/slidemark/preview.py`, `scripts/gallery.py`, `.github/workflows/`,
  `tests/helpers.py`, `examples/`, `bench/BASELINE.json`, `tests/test_bench.py`, `docs/FEATURES.md`):
  CLI `build`/`check`/`preview`/`version` (argparse, one-line diagnostics, `--format json`, exit 1 on errors);
  preview via `soffice --headless` (isolated `-env:UserInstallation`, timeout) → PDF → PNG with pypdfium2;
  gallery builds `examples/*.md` → `docs/gallery/<example>/slide-NN.png` (≤ 1280px, optimized) and rewrites the
  README block between `<!-- gallery:start -->`/`<!-- gallery:end -->` with date + commit; examples: `01-basics.md`,
  `02-jp-dense.md` (dense Japanese business slides), `03-vi-report.md`; CI (uv, py3.10 + 3.12, ruff, pytest;
  preview tests skip without soffice); token gate: corpus ≤ baseline × 1.02, `AGENT_TIPS.md` ≤ 1,000 tokens,
  `SYNTAX.md` ≤ 2,500 tokens.

## Day 1 status
- [x] Contracts: `ir.py`, `theme.py`, `units.py`, stage stubs, `docs/SYNTAX.md`
- [ ] Parser v0
- [ ] Layout v0 + themes
- [ ] Renderer v0
- [ ] Tooling: CLI, preview, gallery, CI, examples
- [ ] Merge, end-to-end test, README gallery, bench
