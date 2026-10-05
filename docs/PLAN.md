# Foundation plan

The plan is split into **plan days** (units of scope, below). A **run** is one routine session. Each run is
led by an **Opus orchestrator** that settles contracts, merges, and owns tooling/docs, with **at most 2 Sonnet
subagents** coding in parallel, each in its own git worktree and file set: **A = front** (parser, CLI) and
**B = back** (layout, renderer). Layout and renderer share one agent so the `Placed` hand-off never drifts.

**Run size: at least 2 hours of implementation, targeting 2 plan days per run.** Subagents work in *waves*:
when a wave is merged and green, the orchestrator starts the next wave (next work packages) until the time
rules in "Run routine" say stop. Every run ends with tests green, the README gallery refreshed, the bench
recorded, and a push to `main`.

Levels: plan days 1–2 → **L1**, 3–4 → **L2**, 5–7 → **L3** (see `docs/TARGETS.md`). After plan day 7 each run
keeps climbing L4 → L7, picking the unchecked gates with the best value.

| Day | Subagent A: parser + CLI | Subagent B: layout + renderer | Orchestrator: tooling, docs, merge |
|---|---|---|---|
| **1** | Parser v1 (whole `SYNTAX.md` except html/mermaid/math bodies), CLI `build`/`check` | Auto block arrangement, `@` grid specs, boxes, lead/conclusion/footnotes, measurement v0; renderer for text, lists, tables + merges, images, code, charts, boxes, notes | preview (LibreOffice → PNG), `scripts/gallery.py` + README, CI, examples (basics, JP dense, VI report), `FEATURES.md` |
| **2** | Lenient parsing (Slidev/Marp/Markdown variants), diagnostics with hints, fuzzing | Real font metrics, autofit, overflow diagnostics, CJK line breaking; table styling, image cover crop | Golden XML + image diff, `BASELINE.json` + CI token gate |
| **3** | Components: `.kpi`, `flow`, `chevron`, badges, nested `@` in boxes | **Dense JP**: 12-col grid math, header band, `density: dense`, connectors/arrows, callouts | ≥ 5 dense JP example decks, visual review, lessons |
| **4** | Chart/table options, CSV edge cases | All chart kinds, number formats, data labels; OMML math | `check` linter v1 (overflow, off-slide, overlap, contrast, alt), JSON output |
| **5** | `slidemark docs`, `schema`, `skill install` | User templates `.potx`/`.pptx`, masters, footer/number fields | SKILL.md + `reference/` with token budgets |
| **6** | `html`, `mermaid` fences | HTML → native (Playwright measurement), image fallback | Agent eval harness v0 |
| **7** | Slide links, `hidden`, sections | Transitions, build animations, hyperlinks, sections | Packaging (PyPI-ready), release notes, AGENT_TIPS review |

## Run routine (02:45 JST daily, or fired manually)
1. Note the start time (`date -u`). Read `CLAUDE.md`, `docs/LESSONS.md`, this plan, `docs/TARGETS.md`,
   `docs/SYNTAX.md`, the end of `docs/DAILY_LOG.md`.
2. **Run goal:** leftovers first, then the next **two** unchecked plan days (after plan day 7: a set of
   `TARGETS.md` gates worth ≥ 2 hours). Write the run goal as a checklist at the top of today's
   `DAILY_LOG.md` entry, and write missing "Day N work packages" sections here before delegating.
3. Commit any contract change (`ir.py`, `theme.py`, `SYNTAX.md`) yourself **before** spawning a wave.
4. **Wave:** spawn **at most 2** subagents in one message (Agent tool, `model: sonnet`, `isolation: worktree`),
   with self-contained prompts: owned files, spec, Definition of Done, own `.venv`, ruff + pytest, commit in the
   worktree, report ≤ 300 words (branch, commit, contract changes, deps, lessons). Subagents never edit
   `docs/LESSONS.md`, `AGENT_TIPS.md`, `PLAN.md`, `TARGETS.md`, `DAILY_LOG.md` or `README.md`.
   While they work, do the orchestrator lane yourself.
5. Merge the wave, make ruff + pytest green, push. **Review the gallery images yourself** (open the PNGs) and
   turn visual defects into work packages for the next wave.
6. Repeat waves until a stop rule fires:
   - **Minimum:** do not stop before 2 hours unless BLOCKED. If the run goal is done early, extend it with the
     next plan day or `TARGETS.md` gates and keep going.
   - **Wrap-up:** at about 3h30, start no new wave; finish and merge the running one.
   - **Hard stop:** about 4 hours: merge only what is green, leave the rest unchecked (next run's leftovers).
   - **BLOCKED:** something you cannot fix yourself (push refused, install/network denied, a package fails
     twice): push what is green, log the blocker, stop.
7. Finish: `scripts/gallery.py`, bench (`--record`), checkboxes (here and `TARGETS.md`), `LESSONS.md`,
   `AGENT_TIPS.md` (verified tips only), `DAILY_LOG.md` entry (≤ 15 lines). Push to `main`. Never end with
   unpushed commits.

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
- [x] Box terminator `@end` + `dropped-content` diagnostic (day 2)
- [x] Slide-level table after an `@end` (with `chevron` grid) is placed in ONE grid cell, cramped; slide-level visuals should get their own full-width row below the grid (jp-dense slide 2)

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
- [x] Contract: `@end` in SYNTAX.md
- [x] A: lenient parsing + hints + `@end` + fuzz
- [x] B: dropped-content diag, autofit/kinsoku, table styling, image cover
- [x] Orchestrator: golden images, BASELINE.json token gate
- [x] Merge, gallery, bench

## Day 3 work packages (incl. day 2 leftover)
Contract (committed by orchestrator): `ir.Link` + `Slide.links`/`Container.links`; theme `heading_band`,
`heading_band_color`, `columns`, classes `note`/`tip`/`warn`/`caution`/`badge`; SYNTAX.md Components section.
- **A: parser + CLI** (`src/slidemark/parser/`, `src/slidemark/cli.py`, `tests/test_parser*.py`, `tests/test_cli.py`):
  - `@` tokens `a>b`, `a-b`, `1>3` → `Link` on the slide (or on the box for a box `@` line); out-of-range → warning + hint.
  - `> [!note|tip|warn|warning|caution|important] text` → `Text(role="body", classes=["callout", kind])`, never lead/conclusion; works inside boxes.
  - `[x]{.badge .success}` → `Run(highlight=<color class or "primary">, color="bg", bold=True)`.
  - `.kpi` box: keep first line and caption lines as separate paragraphs (no list markers); verify nested `@` in boxes (`###` sub-boxes) end-to-end.
  - Fuzz covers the new tokens.
- **B: layout + renderer** (`src/slidemark/layout/`, `src/slidemark/render/`, `tests/test_layout*.py`, `tests/test_render*.py`):
  - Leftover: blocks beyond the grid's cell count → full-width rows below the grid; a chevron/flow row takes its natural height (compact), not half the slide.
  - Bug: jp-dense slide 2 table (5 cols, one `colspan=3`) renders 7 columns.
  - `.kpi` (big number + caption, centered), callouts (tinted fill + left accent bar/border by kind), badges (run highlight), connectors (`Link` → `Shape(shape="line")` edge-to-edge between block rects, arrowhead via `a:tailEnd`).
  - Box heading band (`theme.heading_band`): heading drawn as a filled band across the card top (jp-business).
  - `density: dense` / `.dense` also tightens gaps and paddings; ratio/area columns snap to `theme.columns` tracks.
- **Orchestrator:** ≥ 5 dense JP example decks (`examples/04-…`), visual review, lessons.

## Day 4 work packages
- **A: parser + CLI**: chart fence options (`legend labels fmt min max colors axis`, validated with hints) into
  `Chart.options`; CSV edge cases (quotes, `1,240`, `12%`, full-width digits, ragged rows, blank lines, BOM);
  table attrs `widths align header hcol` → `col_widths`/cell styles/`header_rows`/`header_cols`;
  `check --format json` runs the layout linter (`slidemark.lint`) as well.
- **B: layout + renderer**: all 10 chart kinds native with the options above (legend position, data labels,
  number formats, axis bounds, per-series/per-point colors, axis off), numeric table columns right-aligned;
  ` ```math ` → native OMML equation (LaTeX subset) instead of a placeholder.
- **Orchestrator:** `src/slidemark/lint.py` v1 on `Placed` lists: overflow, off-slide, overlap, low contrast,
  missing alt → `Diagnostic`s; JSON output; tests.

## Day 3 status
- [x] Contract: Link, theme tokens, SYNTAX.md components
- [x] Leftover: slide-level visuals under a chevron/grid row get full-width rows
- [x] A: links, callouts, badges, kpi parsing
- [x] B: kpi/callout/badge/connector rendering, heading band, dense spacing, 12-col snap
- [x] Orchestrator: ≥ 5 dense JP examples, review

## Day 4 status
- [x] A: chart/table options, CSV edge cases, check JSON via linter
- [x] B: all chart kinds + options, OMML math
- [x] Orchestrator: lint v1

## Day 5 work packages
Contract: skill files live in `src/slidemark/skill/` (`SKILL.md` ≤ 1,500 tokens, `reference/*.md` ≤ 800 tokens
each, o200k proxy), shipped as package data; written by the orchestrator.
- **A: parser + CLI**: `slidemark docs [topic]` (SKILL.md, or `reference/<topic>.md`; unknown topic → list),
  `slidemark schema` (JSON schema of `Deck`), `build`/`check` accept a `.json` Deck, `slidemark skill install
  [--dir]` (default `~/.claude/skills/slidemark`, copies SKILL.md + reference/, idempotent, prints the path).
- **B: layout + renderer**: `theme: path.pptx|.potx` → the file is the base presentation (masters, layouts, slide
  size), theme colors/fonts read from its `a:theme` into a `Theme` (rest from `default`); title goes into the
  layout's title placeholder; footer and slide number use the master's footer/sldNum placeholders when present
  (native fields). Existing slides of the template are removed. Never raise: missing/corrupt file → default theme + diagnostic.
- **Orchestrator:** SKILL.md + reference/ (syntax, components, charts-tables, jp-dense, diagnostics), token
  budget test, AGENT_TIPS review.

## Day 5 status
- [x] Orchestrator: SKILL.md + reference/ + budget test
- [x] A: docs, schema, JSON input, skill install
- [x] B: user templates, master placeholders for footer/number

## Day 6 work packages
- **A: parser + CLI**: ` ```mermaid ` flowcharts (`graph`/`flowchart` TD/LR, `A[text]`, `A(text)`, `A{text}`,
  `A-->B`, `A---B`, `A-->|label|B`, chains, `;`) → a `Container(classes=["diagram"])` of node `Text`/boxes with
  `links` and an areas `grid` from a layered layout (rank = longest path); unsupported diagrams stay `Raw` +
  info diagnostic. ` ```html ` fences and `.html` input: structural subset (`section.slide`, `h1`, `p.lead`, `h2`
  cards, `ul/ol`, `table`, `mark`, `b/i`, inline `grid-template-columns`/areas, `footer .note`, `.callout`,
  `.kpi`, `.badge`) → the same IR as the Markdown form; anything else → `Raw(kind="html")` + info diagnostic.
- **B: layout + renderer**: `Raw(kind="html")` leftovers rendered via Playwright (Chromium) to a PNG image
  fallback at the block size; measurement of HTML text with Chromium when available.
- **Orchestrator:** agent eval harness v0 (`bench/tasks/*.md` prompts + `bench/eval.py` scoring check/lint
  results), docs.

## Day 6 status
- [x] A: mermaid flowchart → native, HTML subset → IR
- [x] B: HTML image fallback via Playwright
- [x] Orchestrator: eval harness v0

## Next layout package (auto-arrangement v2, from the gallery review)
- A run of `##` boxes closed by `@end` and followed by visuals = boxes in ONE row + visuals full width below,
  without any `@` token (09-midnight-tech slide 2 gets a 2×2 today).
- `flow`/`chevron` without N → N = number of leading boxes (05-jp-process slide 1, 08-jp-roadmap slide 3).
- 3 blocks where block 1 has a visual or ≥ 2× the text of the others → `aab/aac` automatically.
- Slide links forming a tree from one root → tree layout like mermaid (`.a./bcd`) automatically.
- Math blocks scale up (≈ 1.6× body) and center; code blocks grow like text when the slide is sparse.
- Goal: `bench/layout_inference.py` ≥ 90% with the `@` grid tokens removed from examples where redundant.

## Day 7 work packages
Contract (SYNTAX.md, committed by orchestrator): `@build` (or `{.build}` on a block) = bullets/blocks appear one
by one on click; `t=` transitions `fade push wipe split cover zoom morph` (+ `t=fade:0.5` duration s);
PowerPoint sections from `@section` slides (the section is named after the slide title) — `sections: off` in
the header disables them; `[text](#id)` / `[text](#5)` jumps; `@hidden`.
- **A+B combined (no layout changes)**: parser for `@build`/`.build`, transition durations, header
  `sections:`; renderer: `p:timing` build animations (appear per paragraph for text, per shape for blocks),
  more transitions with duration, `p14:sectionLst` sections, slide-jump hyperlinks by id and number, hidden.
- **Orchestrator**: packaging (wheel build check, sdist excludes), `CHANGELOG.md`, release notes, AGENT_TIPS review.

## Day 7 status
- [x] A+B: build animations, transitions, sections, jumps
- [x] Orchestrator: packaging, changelog

## After plan day 7: TARGETS gates (run 2026-10-05)
- [x] L3 icons: `icon=name` on boxes → native custGeom icons (34 names, did-you-mean), `slidemark docs icons`
- [x] L6 import: `slidemark import deck.pptx` → SlideMark text; build → import → build stable for our decks
- [x] L2 layout inference ≥ 90% (auto-arrangement v2): 100%
- [x] L4 fuzz: 0 crashes in 100k inputs (`bench/fuzz_long.py`)

## Leftovers for the next run (from the 2026-10-05 review)
- [ ] Very sparse box slides (01-basics slide 3) still ~70% empty boxes: rethink (center the row, or smaller cards)
- [ ] L3 consulting-grade pass on JP slides (02 slide 1 right boxes sparse, 07 slide 2 empty band)
- [ ] Video/audio; Chromium measurement for HTML; XSD validation of output; PowerPoint repair check (owner)
- [ ] Importer: reconstruct connectors (`a>b`) and mermaid

## Run 2026-10-05 (manual, 04:10 UTC) work packages
- **Wave 1 A: importer** (`src/slidemark/importer/`, `tests/test_import*.py`): reconstruct connectors between
  boxes as `@ a>b` tokens (glued `stCxn/endCxn` first, else nearest box edges), and mermaid diagrams
  (`.diagram` containers built by us) back into a ` ```mermaid ` fence; round trip stays stable.
- **Wave 1 B: layout consulting-grade pass** (`src/slidemark/layout/`, `tests/test_layout*.py`, goldens):
  card height follows content (no 70%-empty cards; very sparse rows centered vertically), table rows capped
  near their natural height (no stretched 64 px rows of 10.5 pt text), same title→body gap on every slide,
  box rows above a chart/table take their natural height, no empty band above the conclusion bar (07 slide 2),
  stacked boxes in one column get height in proportion to content (02 slide 1), chevron lists without bullets.
- **Wave 2 A: video/audio end to end** (contract `ir.Media` committed): parser (`![](x.mp4)`, `{poster= autoplay
  loop}`), small hooks in layout (Media sized like Image) and render (`render/media.py`, python-pptx
  `add_movie`, generated poster with a play icon), lint alt; `slidemark preview deck.pptx` accepts a .pptx.
- **Wave 2 B: charts and tables from the 11-jp-consulting review**: stacked-bar series 3 and 4 share a color
  (palette repeats), data labels dark on dark fills (auto white), chart `axId` written negative (XSD error,
  python-pptx template), table column widths from content (numeric columns too wide), org tree boxes far taller
  than one line of content.
- **Orchestrator:** `examples/11-jp-consulting.md` (≥ 8 dense slides, L3 gate), CI on 3 Python versions +
  coverage report, XSD/schema validation script for generated decks (L6), docs.
- **Wave 3 A: HTML → native via Chromium measurement** (`src/slidemark/htmlnative.py`): unsupported HTML blocks
  are laid out in headless Chromium and converted to native rects/text/images; `{render=image}` opts out;
  canvas/complex SVG keep the image fallback.
- **Wave 3 B: fixes from the wave 2 gallery review.**
