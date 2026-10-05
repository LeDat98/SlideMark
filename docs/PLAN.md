# 7-day foundation plan

Each day has three lanes. The orchestrator session settles contracts, merges, and owns tooling/docs.
**At most 2 Sonnet subagents** code in parallel, each in its own git worktree and file set:
**A = front** (parser, CLI) and **B = back** (layout, renderer). Layout and renderer share one agent so the
`Placed` hand-off never drifts. The day ends with tests green, the README gallery refreshed, the bench recorded,
and a push to `main`.

Levels: days 1–2 → **L1**, days 3–4 → **L2**, days 5–7 → **L3** (see `docs/TARGETS.md`). After day 7 the
daily routine keeps climbing L4 → L7, picking the unchecked gates with the best value per day.

| Day | Subagent A: parser + CLI | Subagent B: layout + renderer | Orchestrator: tooling, docs, merge |
|---|---|---|---|
| **1** | Parser v1 (whole `SYNTAX.md` except html/mermaid/math bodies), CLI `build`/`check` | Auto block arrangement, `@` grid specs, boxes, lead/conclusion/footnotes, measurement v0; renderer for text, lists, tables + merges, images, code, charts, boxes, notes | preview (LibreOffice → PNG), `scripts/gallery.py` + README, CI, examples (basics, JP dense, VI report), `FEATURES.md` |
| **2** | Lenient parsing (Slidev/Marp/Markdown variants), diagnostics with hints, fuzzing | Real font metrics, autofit, overflow diagnostics, CJK line breaking; table styling, image cover crop | Golden XML + image diff, `BASELINE.json` + CI token gate |
| **3** | Components: `.kpi`, `flow`, `chevron`, badges, nested `@` in boxes | **Dense JP**: 12-col grid math, header band, `density: dense`, connectors/arrows, callouts | ≥ 5 dense JP example decks, visual review, lessons |
| **4** | Chart/table options, CSV edge cases | All chart kinds, number formats, data labels; OMML math | `check` linter v1 (overflow, off-slide, overlap, contrast, alt), JSON output |
| **5** | `slidemark docs`, `schema`, `skill install` | User templates `.potx`/`.pptx`, masters, footer/number fields | SKILL.md + `reference/` with token budgets |
| **6** | `html`, `mermaid` fences | HTML → native (Playwright measurement), image fallback | Agent eval harness v0 |
| **7** | Slide links, `hidden`, sections | Transitions, build animations, hyperlinks, sections | Packaging (PyPI-ready), release notes, AGENT_TIPS review |

## Daily routine (runs automatically at 02:45 JST)
1. Read `CLAUDE.md`, `docs/LESSONS.md`, this plan, `docs/TARGETS.md`, `docs/SYNTAX.md`, the end of `docs/DAILY_LOG.md`.
2. Pick the first day below that is not fully checked. Finish leftovers from the previous day first.
   If that day has no "work packages" section yet, write it first, in the style of Day 1.
3. Commit any contract change (`ir.py`, `theme.py`, `SYNTAX.md`) yourself **before** spawning subagents.
4. Spawn **at most 2** subagents in one message (Agent tool, `model: sonnet`, `isolation: worktree`), with
   self-contained prompts: owned files, spec, Definition of Done, own `.venv`, ruff + pytest, commit in the
   worktree, report ≤ 300 words (branch, commit, contract changes, deps, lessons). Subagents never edit
   `docs/LESSONS.md`, `AGENT_TIPS.md`, `PLAN.md`, `TARGETS.md`, `DAILY_LOG.md` or `README.md`.
5. While they work, do the orchestrator lane yourself.
6. Merge both branches, make ruff + pytest green, run `scripts/gallery.py` and the bench (`--record`).
   Never push red: revert what can't be fixed today and log it.
7. Update checkboxes (here and `TARGETS.md`), `LESSONS.md`, `AGENT_TIPS.md` (verified tips only), and append to
   `DAILY_LOG.md` (≤ 10 lines). Commit and push straight to `main`.

## Day 1 work packages
- **A: parser + CLI** (`src/slidemark/parser/`, `src/slidemark/cli.py`, `tests/test_parser*.py`, `tests/test_cli.py`):
  `parse()` per `docs/SYNTAX.md` v1.
  - Header `key: value` lines (and `---` YAML front-matter) → `Deck`.
  - `#` starts a slide (ignore `#` inside code fences); `---` starts an untitled slide; cover/section inference
    (title + ≤ 2 short lines → subtitle).
  - `@` lines → `Slide.layout`/`grid`/classes/attrs, or a box's `grid`.
  - `##` → `Container(title=...)`; `###` → heading text, or a nested box when its box has an `@` line.
  - Top-level text, lists and visuals → separate blocks in source order.
  - `>` → lead/conclusion/quote by position; `※`/`^` → footnotes; `???` → notes.
  - `{}` attrs → `Box`/`Style`/classes/`attrs`. Inline: `==x==`, `[x]{.c}`, sub/sup, links incl. `#5`.
  - GFM tables with `<`/`^` merges; ` ```table ` CSV; chart fences with CSV and fence attrs;
    `mermaid`/`math`/`html` → `Raw`; other fences → `Code`.
  - markdown-it-py + mdit-py-plugins for inline and blocks; split structure on raw lines first, keeping line numbers.
  - Never raise: a `Diagnostic` with line + hint. Hypothesis fuzz test.
  - CLI (argparse): `build in.md -o out.pptx`, `check in.md [--format json]`, `version`; one diagnostic per
    line; exit 1 on errors. `preview` is wired to `slidemark.preview.pptx_to_pngs` (written by the orchestrator).
- **B: layout + renderer** (`src/slidemark/layout/`, `src/slidemark/render/`, `src/slidemark/theme.py`,
  `tests/test_layout*.py`, `tests/test_render*.py`):
  - **Layout:**
    - `layout_slide()` → `Placed` list in z-order.
    - Slide frame: title area, lead under the title, footnotes + footer + slide number at the bottom,
      conclusion bar above the footnotes, body area in between.
    - Auto arrangement by block count, "text + one visual" split, `@` grid specs (`N`, `CxR`, ratios,
      areas with spans and `.`), `flow` arrows as `Shape` items, `chevron` boxes.
    - Boxes: card `Placed` + heading band + children inset by padding; nested `@` inside boxes.
    - Explicit `{x y w h}` relative to the parent area.
    - Style merge: theme role defaults → classes → inline.
    - `layout/measure.py`: Pillow metrics (Liberation Sans ≈ Arial, IPAGothic for CJK); word wrap for Latin,
      per-char for CJK; `font_scale` autofit down to `min_font_size`; `overflow` diagnostic.
    - Themes: `default`, `midnight` (dark), `jp-business` (dense, navy title band, 10.5–12pt).
  - **Renderer:**
    - Title in the title placeholder; runs with every inline style, and links (`#n` → slide jump in a second pass).
    - Native bullets and numbering; `<a:latin>` + `<a:ea>` fonts and `lang`.
    - Tables with merges and explicit fills (no default blue style); images contain/cover/stretch, missing →
      placeholder + diagnostic; pygments code runs; charts with theme colors; auto shapes by name.
    - Container fill/border/radius; `Raw` → labeled placeholder; background; notes; hidden; core properties.
  - Tests reopen the .pptx and assert; layout tests check in-bounds and no sibling overlap.
- **Orchestrator:** `src/slidemark/preview.py` (`soffice --headless` with isolated `-env:UserInstallation` and a
  timeout → PDF → PNG with pypdfium2), `scripts/gallery.py` (`examples/*.md` → `docs/gallery/<name>/slide-NN.png`
  ≤ 1280px, rewrite the README block between `<!-- gallery:start -->` and `<!-- gallery:end -->` with date +
  commit), `examples/01-basics.md`, `02-jp-dense.md`, `03-vi-report.md`, `.github/workflows/ci.yml` (uv,
  py3.10 + 3.12, ruff, pytest; preview tests skip without soffice), `tests/helpers.py`, `docs/FEATURES.md`.

## Day 1 status
- [x] Contracts: `ir.py`, `theme.py`, `units.py`, stage stubs, `docs/SYNTAX.md` v1
- [x] A: parser + CLI
- [x] B: layout + renderer
- [x] Orchestrator: preview, gallery, CI, examples
- [x] Merge, end-to-end test, README gallery, bench

## Day 1 leftovers (carried to day 2)
- [ ] Table/`>` after the last `##` box become children of that box and (in a chevron box) vanish: add a way to end a box + diagnostic when a visual is dropped (found in `examples/02-jp-dense.md` slide 2)

## Day 2 work packages (incl. day 1 leftover)
- **A: parser + CLI** (`src/slidemark/parser/`, `src/slidemark/cli.py`, `tests/test_parser*.py`, `tests/test_cli.py`):
  - `@end` line closes the current `##` box (SYNTAX.md, committed by orchestrator); `@end` outside a box → info diagnostic.
  - Lenient variants accepted with a warning + hint: Marp `<!-- _class: x -->`/`<!-- paginate: true -->` and
    `marp: true` header, Slidev per-slide YAML frontmatter (`layout:`, `class:`), `::right::`-style slot lines,
    `Note:` / `<!-- notes -->` comments → notes, `* ` bullets, `###` used as slide start when no `#` exists,
    `![w:200](a.png)` Marp sizing, `<br>` in text.
  - Every diagnostic has `rule` + one-line actionable `hint`; unknown `@` tokens/attrs suggest the closest valid one.
  - Extend hypothesis fuzz (random line mixes incl. new variants): never raises.
- **B: layout + renderer** (`src/slidemark/layout/`, `src/slidemark/render/`, `tests/test_layout*.py`, `tests/test_render*.py`):
  - Layout emits a `Diagnostic` (rule `dropped-content`) when a chevron/flow box drops non-text children.
  - Autofit: verify/make font_scale shrink with measured metrics for Latin and CJK, `overflow` diagnostic below
    `min_font_size` (check it fires with a hint); CJK line breaking: no line starting with closing punctuation
    (、。）」) or ending with an opening one (kinsoku).
  - Table styling: header fill, zebra option via class `.zebra`, borders; image `fit=cover` real crop (srcRect).
  - Tests reopen the .pptx and assert.
- **Orchestrator:** golden image diff test (preview PNG vs stored, tolerance; skip without soffice), `bench/BASELINE.json`
  + token gate test (fail if slidemark tokens regress >3%), examples, gallery, docs.

## Day 2 status
- [ ] Contract: `@end` in SYNTAX.md
- [ ] A: lenient parsing + hints + `@end` + fuzz
- [ ] B: dropped-content diag, autofit/kinsoku, table styling, image cover
- [ ] Orchestrator: golden images, BASELINE.json token gate
- [ ] Merge, gallery, bench
