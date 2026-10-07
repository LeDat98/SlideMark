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

## Current direction: design freedom (owner, 2026-10-05)
Until the DF gates in `docs/TARGETS.md` are done, **every run's goal is the DF gates** (spec: `docs/DESIGN_FREEDOM.md`),
leftovers that conflict with it are dropped, and other L3–L7 work waits. Suggested order: DF1 + DF2 (tokens, presets
as data, remove hard-coded looks) → DF3 (CSS fence) → DF4 + DF5 (HTML fidelity, whole-deck HTML) → DF6 (eval).

## Current direction: agent cost (owner, 2026-10-06)
Review and spec: `docs/AGENT_COST.md`. An A/B pilot with real agents found the deck source at 10–19% of the
python-pptx script but the whole agent run at 112% of its cost: model calls decide the cost, not file size.
Until the AC gates are done, **every run's goal is the work packages in that file, in order**; design freedom
stays a constraint on how they are done. First step of the next run: work package 1 (add the AC gate group to
`docs/TARGETS.md`, re-open the L4 "total agent tokens" gate, build `bench/agent_cost.py`).

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
- **Wave 3 B: fixes from the wave 2 gallery review.** (done)
- **Wave 3 A (done): import fidelity** on 19 agent-written python-pptx decks (`bench/import_fidelity.py`, 0.955 → 0.977).
- **Wave 4 A: `slidemark review`** (`critique.py`): design critic with source-level hints and a 0–100 score.

## Run 2026-10-05 (manual, 04:10 UTC) status
- [x] Leftover: sparse box slides + consulting-grade layout pass (top anchoring, content-sized cards/chevrons/trees/tables, growth, search)
- [x] Leftover: importer reconstructs connectors and mermaid; round trip 98.2% lossless on 111 decks; foreign decks 0.975
- [x] L5: video/audio; HTML → native via Chromium
- [x] L6: XSD validation (10k fuzzed decks valid), CI 3.10–3.12 + coverage 93%
- [x] L7: agent eval 100 tasks (99%), `slidemark review`, layout search, `check --fix`
- [x] Waves 6–9: diagram growth, consistent growth in grids, heading ≥ body, paragraph spacing, SVG, `check --fix`

## Leftovers for the next run
- [ ] L3 consulting-grade: examples/11 slides 8–9 fuller (cards 49–72% filled) but slide 9 leaves a ~35% band below the cards
- [x] Chromium HTML imports back to an html fence (design part; xfail removed run 4); math shows LibreOffice fallback
- [ ] Owner: open media/SVG/animation/morph decks in real PowerPoint (repair check); PyPI token
- [ ] L7 tokens ≤ 20% of python-pptx (now 30%): needs a syntax design pass

## Run 2026-10-05 (run 3, design freedom) work packages
Contract (orchestrator, committed first): `theme.py` token schema (`LayoutTokens`, `RenderTokens`, `classes`
open to new names), presets as YAML (`src/slidemark/presets/*.yaml`), `theme: none`, `apply_tokens` /
`canonical_token` / `schema_table`, `template.deck_theme`, `ir.Deck.tokens`, `Style.fill` gradients and
`Style.shadow` CSS strings, SYNTAX.md "Design tokens".
- **Wave 1 A: inline tokens front** (`parser/`, `cli.py`): `colors:`/`fonts:`/`sizes:`/`style:` header lines
  and YAML front-matter maps → `Deck.tokens` with did-you-mean diagnostics; `slidemark tokens [--theme]
  [--format json]`, `slidemark themes`; `import` keeps tokens; fuzz.
- **Wave 1 B: no hard-coded looks back** (`layout/`, `render/`): constants → `theme.layout`/`theme.render`;
  color literals → tokens; gradient fills, CSS shadows, opacity rendered natively; literal-scanner test (DF1);
  `theme: none` + tokens render test.
- **Wave 2 A: CSS fence parsing** (DF3): ` ```css ` in header/slide → per-element `Style` via selectors.
- **Wave 2 B: CSS native mappings** (DF3): new `Style` fields rendered (per-side borders, letter-spacing,
  line-height, text-transform, rotation …).
- **Orchestrator:** SKILL.md tokens section, brand-look examples, gallery review, docs.
- **Wave 3 B: CSS matching + native rendering** (layout/css.py, render): selectors → merged styles, every CSS
  Style field drawn natively, table cell CSS, slide backgrounds; lint judges merged colors only.
- **Wave 3 A: `@html` slides, deck.html, shared CSS vars, htmlnative fidelity** (gradients, shadows, rotation,
  ellipses, pill badges, simple inline SVG native) on `bench/html_corpus` (baseline native 0.633, 19/30 ≥ 0.9).
- **Wave 4 (DF6):** 20 brand-brief eval tasks (`bench/tasks/101-120`, Sonnet, SKILL.md only) → `bench/brand_eval.py`.
- Open defect (gallery): sparse box slides on non-dense decks leave a 35–40% empty band (13-brand-aurora slide 2).

## Run 2026-10-05 (run 3) status
- [x] Contracts: token schema, YAML presets, `Deck.tokens`, `CssRule`/`Deck.css`/`Slide.css`, Style CSS fields, `Slide.html`
- [x] W1 A tokens header + `slidemark tokens`/`themes`; B constants → tokens, gradients/shadows, DF1 scanner
- [x] W2 A CSS parser (34 properties); W3 B CSS matching + native render; W3 A `@html`, deck.html, htmlnative fidelity 0.63 → 1.00
- [x] W4 A token value validation + shorthands; B unknown-font metrics, radial position, Latin badges, sparse balance
- [x] W5 A design round trip (customXml part); B sparse slides (bar penalty, text + card growth); W6 A round-trip fixes
- [x] W6 B `@free` slides + text-first fill; W7 A html fence source on import, B dense paragraph spacing, A element tokens
- [x] W8 B sparse flow/html/table slides; A foreign import derives look tokens (color fidelity 0.47 → 0.85)

## Leftovers for the next run
- [ ] Sparse cards: some cards still ~50% empty (05 s2, 11 s9, 12 s1 html); consider content-width cards
- [ ] Round trip: 1 deck left (114/115)
- [ ] Owner: open a design deck (gradients, shadows, customXml design part) in real PowerPoint: repair check
- [ ] L3 consulting-grade judgement; L7 tokens ≤ 20% of python-pptx (syntax design pass)

## Run 2026-10-05 (run 4, chained, 10:55 UTC) work packages
Goal: close L3 (consulting-grade dense JP set), then the best-value open gates (harder brand briefs, larger
HTML corpus, L7 token research). Design freedom stays the rule: fixes are mechanisms/tokens, never looks.
- **Wave 1 A: HTML text zoom + harder HTML corpus** (`htmlnative.py`, `bench/html_corpus/`, `bench/html_fidelity.py`,
  `tests/test_htmlnative*.py`): an HTML block whose content is much smaller than its box renders at a narrower
  viewport (zoom ≤ `layout.html_zoom_max`, opt-out `{zoom=1}`) so default 16px text is not 12pt in a large box;
  corpus 30 → 45 harder slides (dense JP, nested flex, tables in cards, SVG icons, absolute positioning).
- **Wave 1 B: sparse cards v3** (`layout/`, `render/`): no card interior < 60% filled on 05 s2, 11 s9 and the other
  examples (measure with `bench/whitespace.py`); paragraph gaps never larger than ~1 line; leftover goes to a
  balanced band, not inside cards. New knobs are `layout.*` tokens.
- **Orchestrator:** consulting-grade dense JP set (examples/16, ≥ 8 slides) reviewed slide by slide; L7 token
  floor research (content-only floor of q3 vs python-pptx); harder brand briefs (`bench/tasks/121-140`).
- **Wave 1 status:** A zoom (`html_zoom_max`, `{zoom=}`) + corpus 45 (native 0.999) merged; B cards hug content,
  dense type cap, box beside a visual aligns, zero labels hidden merged. Orchestrator: examples/16 (10 slides),
  token floor research, brand briefs 121–140 + eval run-8 (16/20 first pass), import box classes, html 100% height,
  derived muted.
- **Wave 2 A: eval gaps** (`parser/`, `layout/css.py`, `icons/`): `.kpi` CSS styles the number, element tokens take
  every CSS property + alias hints, ~20 more icons + `icon=file.svg`.
- **Wave 2 B: sparse fill v4** (`layout/`, `render/`, `bench/whitespace.py`): card-tail metric; no card tail > 25%;
  leftover as one bottom band; deck-consistent type.
- **Wave 2 status:** A `.kpi` CSS on the number, element tokens = any CSS property (+aliases), 26 icons + `icon=file.svg`,
  CSS `width`/`inline-block`; B hugging on all decks (`hug_cards`), centered cards beside visuals, explicit sizes never
  grow, `grow_max`, card-tail metric (row leaders 0/62 > 25%). Both merged (1291 tests).
- **Wave 3 A: CSS deck round trip** (`importer/`): examples/17-editorial-css (width, lead CSS vs runs, text-transform
  casing, KPI misdetection, `@1`, `@html`).
- **Wave 3 B: sparse step** (`layout/`): one deck-wide step-up type size for slides < 55% filled; band ≤ 35%.
- **Wave 3 status:** A CSS-deck round trip (examples/17 lossless, roundtrip 116/117) + transparent-card fix; B sparse
  step (`sparse_*` tokens; 16 s6/s8 bands 42/39% → 16/18%). Independent designer review: decks 11/16 not yet consulting-grade.
- **Wave 4 A:** `slidemark review --fix` self-review loop (L7 gate) merged. Then eval run-9 (hard brand briefs, fresh).
- **Wave 4 B: consulting polish** from the review: body block distribute + center when > 20% free, top-anchored panels
  beside charts, card text ≤ table text, reserved lead slot, chart/footnote gap, padded notes.
- **Waves 4–6 status:** B vfill (distribute, center ≥ 60% fill, else top-anchor + bigger step), body size unify,
  reserved lead slot, chart/footnote gap, padded notes; A run-9 gaps (auto light ink, cover `##`, task lists, katakana
  units, SKILL.md backgrounds). All merged, 1403 tests.

## Leftovers for the next run
- [ ] L3 consulting-grade: designer review 3.2/5 (16) and 3.3/5 (11); open: two-card decision slides (16 s10, 11 s9) and
      text panels beside charts (16 s3, 11 s3) half empty; badges are tight run highlights; 16 s9 header vs merged body
- [ ] Katakana words still break inside chevrons in LibreOffice (needs a `\v` break or inset correction in render)
- [ ] Owner: real PowerPoint repair check (gradients, shadows, customXml design part, media); PyPI token; decide the L7 token gate (`docs/TOKEN_FLOOR.md`)

## Run 2026-10-05 (run 5, agent cost, 17:45 UTC) work packages
Goal: `docs/AGENT_COST.md` work packages 1–6 in order; design freedom stays a constraint (derive, never hard-code).
- **Orchestrator (WP1):** AC gates in TARGETS.md; `bench/agent_cost.py` (transcript → calls, output, cost, cost
  above start, images, docs attempts); `bench/agent_accept.py` (required strings, slide count, 16:9, native charts/
  tables, notes); first brief set `bench/briefs/` (9 briefs: 3/5/10 slides × EN default / JA dense / VI brand).
- **Orchestrator (WP2):** SKILL.md as the only document: fold in the reference pages agents fetched, drop the docs
  pointer, one-command recipe first, one example per deck shape; `tests/test_skill.py` budget ≤ 3,000 tokens.
- **Wave 1 A (WP3): one command** (`cli.py`, `preview.py`, `tests/test_cli*.py`): `build` = parse + safe fixes +
  lint + build + facts line; `build -` reads stdin, `--save deck.md`; identical warnings grouped with a count;
  `--png sheet.png` contact sheet; `SLIDEMARK_NO_DOCS=1` disables `docs` (eval switch).
- **Wave 1 B (WP4): four silent defects** (`layout/`, `lint.py`, `critique.py`): `# T` + `## sub` alone = cover;
  list after a KPI row gets body size and fills; a full-width table spans the content width like the conclusion
  bar; chevron text box uses the chevron interior so Vietnamese/katakana words never break. Golden/regression tests.
- **Wave 2 (WP5, WP6):** one-edit contrast warning (token + nearest passing shade, contrast-safe derived defaults);
  brand deck from `colors:` + `fonts:` alone (title band, table header, chart palette, KPI colour derived).
- **Then:** smoke test 3 briefs × `skill-only` × 1 with fresh subagents outside the repo; record in bench history.
- **Status (18:35 UTC):** WP1 harness + acceptance + 9 briefs ✓, python-pptx baseline for all 9 briefs (4–6 calls,
  37–96k units above start); WP2 SKILL.md ✓ (patterns must never reuse brief content: sm1-b01 copied one, invalid);
  WP3 one-command build ✓; `※` kept in footnotes; decimal commas for vi/de/fr + `contrast.py` ✓. Smoke before WP4:
  b01 3 calls / 48% cost, b05 9 calls rejected (`※`), b09 5 calls / 42%. Running: WP4 (B), WP5+6 colours.
- **Final status:** WP1–WP6 done; extra waves: sparse slide completion, KPI value fit, table text growth, pie label
  ink, 5-step chevron headings, `look:` line, contact-sheet labels. Lead/footnote growth on sparse slides
  (c1d65ec) reverted for build time.

## Leftovers for the next run
- [ ] AC full matrix: 9 briefs × 3 runs × skill-only + skill-open (`SM_DOCS_OPEN=1`), fresh brief set 2 for tuning checks
- [ ] AC4 cost ≤ 35%: the python-pptx arm needs only 4–6 calls here; remaining SlideMark overhead = SKILL.md read (~3k tokens
      carried in every call) + optional looks. Ideas: shorter SKILL.md first screen, `--png` only on request
- [ ] Five-step chevrons: headings stay on one line but text shrinks to ~17pt in tall chevrons (agent replaced them with cards)
- [ ] Perf: layout back under the 50 ms/slide gate with margin; then re-apply lead/footnote growth on sparse slides (c1d65ec)
- [ ] Tables are not contrast-linted; chart label contrast is not linted
- [ ] Owner: real PowerPoint check (gradients, shadows, customXml, media, per-point dLbl); PyPI token; L7 token gate decision

## Run 2026-10-05 (run 6, chained, 21:03 UTC) work packages
Goal: run-5 leftovers (AC matrix, AC4, chevrons, sparse lead growth + perf, table/chart contrast lint, L3 fill).
- **Wave 1 B (layout):** perf margin (best-of-3 build ≤ 35 ms/slide on the gate deck), re-land c1d65ec lead/footnote
  growth on sparse slides, 5-step chevron headings may wrap to two lines at spaces (never inside a word) before text shrinks.
- **Wave 1 A (lint):** contrast lint for table cells (header + body + banding) and chart data labels / axis text;
  one-edit hints (token + nearest passing shade), shared colour resolver with render.
- **Orchestrator:** brief set 2 (`bench/briefs2/`, fresh content), eval runner dirs `/opt/smeval`, python-pptx
  baseline for set 2, then the AC matrix (2 eval agents at a time); SKILL.md first-screen cut.
- **Wave 2 B (layout):** L3 two-card decision slides and chart + text panel slides fill their space.
- **Status (23:35 UTC):** wave 1 A table/chart contrast lint ✓, B perf (38 → 22 ms/slide cold), sparse lead/footnote growth
  re-landed, two-line chevron headings ✓; wave 2 B L3 fill (top-anchored rows, KPI rows, chart side panels) ✓; wave 3 B
  card tails, flow rows, JA chevron word breaks ✓; wave 4 B auto-fit instead of stretching ✓; orchestrator: brief set 2,
  full AC matrix (9 python-pptx + 27 skill-only + 27 skill-open, 63/63 accepted), blind review, post-fix check (4/4 at
  3 calls, 0 images), grouped-number chart labels, zero-based bar axes, deck-locale previews, accent usage in `look:`.

## Leftovers for the next run
- [ ] AC4 cost: 47% (≥ 5 slides 41%) on set 2; the floor analysis in `docs/AGENT_COST.md` needs an owner decision
      (≥ 5-slide briefs only, or a gate net of shared re-reads); remaining levers are SKILL.md size and output tokens
- [ ] L3 consulting-grade: designer review run 6 = 3.5 (16) / 3.0 (11) before wave 4; content-bound decision slides keep an
      empty bottom band; re-score after wave 5 (summary cards above a KPI table, panel top vs chart plot top)
- [ ] Lone chevron rows are tall with modest text after the JA word-break fix (text could grow inside the chevron)
- [ ] Owner: real PowerPoint check (gradients, shadows, customXml, media, per-point dLbl); PyPI token; L7 token gate; AC4 gate wording

## Run 2026-10-06 (run 7, chained, 00:23 UTC) work packages
Goal: L3 consulting-grade per the run-6 designer review; AC4 gate text unchanged (owner), cut SKILL.md/output tokens.
- **Wave 1 B1 (`layout/vfill.py`, `layout/l3fill.py`, `layout/engine.py`):** card rows and 2x2 grids above a conclusion
  bar reach it (grow text up to the sparse step, then stretch the row so its bottom sits one gap above the bar; no
  centered floating block); conclusion bar ≥ `layout.conclusion_foot_gap` above the footnote; lone chevron rows grow
  their text to fill the chevron interior (no word breaks).
- **Wave 1 B2 (`layout/diagram.py`, `layout/tables.py`):** org charts / issue trees scale up to the body (box size, text
  step, level gaps, top-anchored); table header rows stay compact (body rows take the slack); multi-row headers with
  `<`/`^` merges render as merged, centered header cells (roadmap: year over halves).
- **Orchestrator:** SKILL.md cut (≤ 2,700 tokens, same patterns), examples/16 s9 two-row roadmap header, designer re-score.
- **Wave 1 status:** B1 cards/grids reach the conclusion bar, bar–footnote gap 4 → 13px, lone chevron text 19.7 → 26pt
  (JA 3 steps); B2 trees fill the body (top-anchored, bigger boxes/text, wider lone nodes), compact table headers,
  centered merged sub-headers; examples/16 roadmap uses `{header=2}`. 1607 tests.
- **Wave 2 B1 (`layout/l3fill.py`, `layout/engine.py`):** stretched cards that stay hollow (16 s10 left card: 3 items
  in the top half) spread their items over the card height (equal gaps, capped) instead of a dead lower half;
  sibling cards in a row share the rhythm.
- **Wave 2 B2 (`layout/tables.py`, `layout/vfill.py`, `render/objects.py`):** stretched tables grow their text with
  the row height (16 s9 rows ≈ 3 lines tall at 13pt; 11 s4 / 16 s6 chevron + table leave a 100px band), capped by
  `layout.table_text_max`; badges in table cells keep side padding.
- **Wave 2 status:** hollow stretched cards spread their items (gap cap tuned 5.5 → 2.2 em by the orchestrator: wide gaps
  read as broken lists); stretched tables grow text (16 s9 14.2 → 16.8pt) and reach the footnote; padded badges;
  examples/19 (VI, custom brand) added as a stress deck. 1620 tests; round trip 116/119 (16 s3, 58-html pre-existing; 19 s4 new).
- **Wave 3 B1 (`layout/l3fill.py`, `layout/engine.py`, `layout/measure.py`):** lone chevron rows (19 s2: 60% of the body
  empty) grow taller (capped share of the body) with text, and the row sits in the body's optical center; thin chevrons
  above a table (11 s4) grow their text so the table text cap rises too; no line break after an en dash between digits
  (`2027–2029` on 19 s1 cover).
- **Wave 3 B2 (`layout/diagram.py`, `layout/tables.py`, `render/text.py`, `importer/`):** `@.a./bcd` area-grid org charts
  fill the body like `@a>b` trees (19 s3) and a lone root box widens until its heading fits on one line; a badge never
  wraps alone onto its own line in a table cell; importer keeps centered merged header cells (19 s4 round trip).
- **Wave 3 status:** lone chevron rows taller + optically centered, chevrons above tables grow text (11 s4 14.2 → 19.1pt),
  area-grid org charts widen a lone root, badges measured unbreakable, importer `header=2`; orchestrator: table growth
  never wraps a one-line cell (narrow-column guard), `2027–2029` kept together (U+2060 in render). 1640 tests.
- **Designer re-score (run 7, Sonnet, PNGs only):** 11 = 3–3.5, 16 = 3–3.5, 19 = 3; still "no". Top asks: gaps around the
  conclusion bar, floating text in tall decision cards, empty bands, chips (clipped/tight), chart axis max near the data,
  fat bars for 2–3 categories, deliberate covers.
- **Wave 4 B1 (`layout/engine.py`, `layout/l3fill.py`):** conclusion bar keeps one card gutter above it and below it
  (to the footnote); spread hollow cards stay top-anchored (no lead air); covers: larger title in the band.
- **Wave 4 B2 (`render/`):** value axis max = a nice number just above the data max (stacked: category sums) unless
  `max=`; bar gap width scales with few categories; CJK badges never clip glyphs.
- **Wave 4 status:** card gutter above/below the conclusion bar, top-anchored spread cards, composed covers (11 title
  34 → 60pt), nice value-axis max (11 s3 0–140 → 0–125), gap width 180% for ≤ 3 categories, non-bold CJK badges. 1653 tests.
- **Designer re-score 2 (same prompt):** 11 = 3, 16 = 3, 19 = 2.5–3, "no": decision cards still sparse, card body text
  too large (20pt+), conclusion bar text smaller than card text, chevrons vs table columns, greyed `.muted` cards.
- **Eval smoke (skill-only, brief set 2):** c05 3 calls 20.0k, c08 3 calls 21.6k above start, both accepted, 0 images (unchanged).
- **Wave 5 B1 (`layout/engine.py`, `layout/l3fill.py`, `layout/vfill.py`):** a lone KPI row (eval c05 s2: four cards
  stretched to the full body, value floating mid-card) hugs its content, KPI values grow, the row sits at the optical center.
- **Wave 5 B2 (`theme.py` role sizes / `render/`):** conclusion bar text never smaller than the card body text on its slide.
- **Wave 5 status:** lone KPI rows hug content (card 5.05 → 2.51in, value 54 → 66pt, optical center); conclusion bar text ≥
  card body text (13 → 17pt), one line when it fits. 1663 tests.

## Leftovers for the next run
- [ ] L3 consulting-grade: re-score 3/3 ("no"); open: chevron steps aligned to the table columns below, decision slides
      (content-bound: sparse cards vs oversized text), `.muted` cards read as disabled, bar touching the footer without a
      footnote, orphan last words in card list items (VI "đồng", "số")
- [ ] AC4 (owner decision on the gate wording still pending); SKILL.md trims give ≤ 1–2 points (AGENT_COST.md floor analysis)
- [ ] Owner: real PowerPoint check (gradients, shadows, customXml, media, per-point dLbl, U+2060 range joiners); PyPI token; L7 token gate

## Run 2026-10-06 (run 8, chained, 03:41 UTC) work packages
Goal: run-7 leftovers (L3), then an independent re-score with a content-rich dense deck; AC4 gate text unchanged (owner).
- **Wave 1 B1 (`layout/engine.py`, `layout/l3fill.py`, `layout/vfill.py`):** sparse decision cards (16 s10, 19 s5): card
  list text capped (`layout.card_text_max`), spread items separated by thin rules (`layout.card_spread_rules`, off-able);
  conclusion bar shrinks (down to a floor) before it wraps; bar keeps one gutter above the footer when no footnote.
- **Wave 1 B2 (`render/`, `layout/measure.py`, `importer/`, `theme.py`, `presets/`):** orphan control for space-separated
  scripts (bind the last two short words with U+00A0 in measure and render, importer restores spaces); `.muted` boxes
  mute the header band/border via preset tokens and keep body text at fg contrast.
- **Wave 1 status:** card text capped at 18pt (19 s5 21.8 → 18pt), hollow cards spread as ruled lists (`card_spread_rules`),
  bar shrinks before wrapping (`conclusion_min_scale`), bar keeps a gutter above the footer; last two short words bound
  with U+00A0 (measure + render, importer restores); `.muted` boxes get a muted band/border and fg body text (`muted-box`).
- **Wave 2 B1 (`layout/engine.py`, `layout/l3fill.py`):** a chart after `@N … @end` spans the full width like a table
  (20 s4: half width); stacked hollow cards beside a chart spread as ruled lists like cards above a bar (20 s6);
  chevron rows over a table with the same column count share its column edges.
- **Wave 2 B2 (`render/charts*`, `layout/tables.py`, `layout/vfill.py`):** negative bars: category labels at the low
  end (20 s3/s8 label over the bar); a table beside a taller chart takes the chart height (rows + text, no new wraps;
  20 s3/s8 lower half empty); full-width tables reach the footnote gutter (20 s7/s10 70–110px bands).
- **Wave 2 status:** lone block after a full `@N` row spans the width (20 s4 chart 4.0 → 12.3in); hollow stacked cards beside a
  chart spread as ruled lists (20 s6); chevrons follow table columns when counts match (`chevron_table_align`); negative
  bars put category labels low; tables fill to a visual's bottom / the footnote gutter (`table_fit`; 20 s8 325 → 489pt). 1707 tests.
- **Wave 3 B (`layout/measure.py`, `render/text.py`):** JP numbers keep their units and signs (`38万円`, `▲8%`) via U+2060;
  generic on/off parsing for bool layout/render tokens. **Orchestrator:** independent L3 re-score (11, 16, 19, 20).
- **Re-score (run 8, `bench/l3_review_prompt.md`, Sonnet, PNGs only):** 11 = 3.5, 16 = 3.5, 19 = 3, 20 = 3.5 (run 7: 3 / 3 / 2.5–3), "no".
  Top asks: Gantt bars instead of text tables, bridge charts and totals, chevrons that map to table columns, composed
  covers, chips on the text baseline, JP orphans in dense cards.
- **Wave 4 A (`parser/blocks.py`, `render/objects.py`, `importer/`):** native `waterfall` chart (contract committed fd5c20f).
- **Wave 3/4A status:** JP number + unit/sign groups joined with U+2060 (`layout.cjk_unit_join`), generic on/off for bool
  tokens; native `waterfall` (bridge) chart with totals (`=`), importer round trip (118/121). 1728 tests.
- **Wave 4B:** `{.gantt}` tables draw native bars (16 s9, 20 s10); composed covers via cover tokens (jp-business, default).
- **Wave 4B/5 status:** `{.gantt}` bars (16 s9, 20 s10), composed covers (`cover.*` tokens), stacked totals (`totals=`),
  distinct jp-business palette, callouts inside panels at body size, panels beside charts span the chart. 1764 tests.
- **Re-score 2 (same prompt):** 11 = 3.5, 16 = 3.5, 19 = 3.5, 20 = 4 "yes (with polish)"; others "no". Top asks: badge
  boxes (white inverted badge in gantt bars), loose panels, cover bottom, JP orphans in narrow cards, chart takeaways.
- **Wave 6 A (`render/objects.py`, `layout/gantt.py`):** badges inside gantt bars read as pills (no hard white boxes);
  negative bar labels never collide with category labels. **Wave 6 B (`layout/diagram.py`, `layout/engine.py`):** org
  charts keep the body gutter under the lead and use the body height (19 s3, 11 s6 level widths).
- **Wave 6/7 status:** gantt badges as tinted pills, negative-axis headroom (`chart_neg_pad`), balanced org charts
  (`tree_parent_span`, `tree_box_air_max`), JP orphan squeeze (`cjk_squeeze_max`, render-only spc). 1780 tests.

## Leftovers for the next run
- [ ] L3 consulting-grade: re-score 2 = 11/16/19 at 3.5 "no", 20 at 4 "yes (with polish)"; open: loose ruled panels with a
      callout at the bottom, JP orphans where LibreOffice wraps earlier than the model, Gantt equal time columns (decide
      widths after the last growth pass), chart takeaways (annotations), single-item bullets in org boxes
- [ ] AC4 (owner decision on the gate wording still pending)
- [ ] Owner: real PowerPoint check (waterfall carrier labels, stacked totals legend on bars, U+2060 between ideographs,
      gradients, customXml); PyPI token; L7 token gate

## Run 2026-10-06 (run 9, chained, 09:19 UTC) work packages
Goal: run-8 leftovers (L3) then a same-prompt re-score; finish by 16:30 UTC; AC4 gate text unchanged (owner).
- **Wave 1 A (`parser/tabular.py`, `parser/blocks.py`, `render/objects.py`, new `layout/chartnote.py`, `importer/`, one hook in
  `layout/engine.py`):** chart takeaways: `hl=` emphasised points (`render.chart_hl`), `note=` native callout (`.chart-note`)
  inside the chart frame pointing at the first `hl` point; round trip.
- **Wave 1 B (`layout/gantt.py`, `layout/tables.py`, `layout/vfill.py`, `layout/l3fill.py`, `layout/engine.py`):** gantt time
  columns equal after the last growth pass (bars still fit, else nearest feasible); ruled panels keep the callout right after
  the list (11 s3); a table beside a taller chart reaches the chart bottom (20 s3).
- **Orchestrator:** examples with a chevron row over a matching table; contact-sheet review.
- **Wave 1 status:** `hl=`/`note=` chart takeaways (manualLayout plot, `ChartNote` shapes, round trip), gantt period columns
  even after growth (`gantt_even`; badge bars may pin a column), ruled panels keep the callout after the list (11 s3), tables
  beside charts reach the chart bottom (`table_fit_row_max_em`), first-slide long taglines are covers, `min=` axes use the
  visible span, examples/22 (English, chevrons over matching columns). 1831 tests.
- **Wave 2 A (`layout/measure.py`, `render/text.py`, `layout/chartnote.py`, `render/charthl.py`):** CJK near-full lines squeezed
  so LibreOffice keeps them whole (21 s2, 20 s2, 11 s2); horizontal-bar note pointer ends on the bar (22 s4).
- **Wave 2 B (`layout/engine.py`, `l3fill.py`, `vfill.py`, `tables.py`):** Latin/default-theme fill: lone table grows and reaches
  the footnote gutter (22 s6), cards over a table hug content and the table takes the height (22 s2), dark-pitch cards
  top-anchored and grown (21 s2).
- **Wave 2 status:** CJK near-full lines squeezed with a render-only viewer model (lone 円 fixed; ≥ 3.4em tails remain), bar-chart
  note pointer lands on the bar, Latin tables wrap-grow and fill (22 s6 14 → 19.7pt), cards over tables hug content, sparse
  dark cards top-anchored (21 s2). 1859 tests.
- **Wave 3 A (`layout/measure.py`, `render/text.py`, `importer/`):** phrase-aware Japanese line breaks (年|齢, 費|用) via soft
  breaks at phrase boundaries when the line count is unchanged; importer strips them.
- **Wave 3 B (`layout/engine.py`, `l3fill.py`, `vfill.py`, `tables.py`, `grid.py`):** sparse brand/CSS slides (13 s2, 17 s2/s3,
  14 s1, 21 s2, 22 s2) grow un-sized text and balance leftover bands; explicit CSS sizes never change.
- **Wave 3 A status:** BudouX phrase breaks (`cjk_phrase_break`), soft breaks marked `bmk="sm"`, importer strips them;
  21 s2 / 20 s2 break at phrases ("点検技術者の / 平均年齢 54歳"). 1868 tests.
- **Wave 4 A (`layout/jbreak.py`, `render/text.py`, `layout/chartnote.py`, `importer/`):** phrase breaks in chevrons and gantt
  bars; chart note never below the axis label size (22 s4).
- **Re-score (run 9, same prompt, Sonnet, PNGs only):** 11 = 3.5, 16 = 3.5, 19 = 3, 20 = 4 "yes, borderline", 22 = 3.5 (new).
  Top asks: action titles (content), card/panel dead space, chevrons vs table columns (16 s6 is 4 vs 5 by content), tiny
  low-contrast status chips (→ wave 4 B native pills), chart emphasis/axes (callout touches bar tip, sparse 3-bar axes).
- **Examples:** 19 s4 now a `{.gantt}` table, 16 s9 footnote no longer cites a missing symbol, 22 s3 header row is the regions,
  22 s5 waterfall back to a zero axis.
- **Wave 4 B (`layout/tables.py`, new `layout/pills.py`, engine hook, importer helper):** badge-only table cells become native
  rounded pills with column-shared width and contrast ink.
- **Wave 4 status:** chevron/gantt phrase breaks, note floor = axis label size, orphan binding only when it fits (15 s2
  "unchange / d" fixed), number + unit bound (`2 ns`); native table pills (`table_pills`). 1892 tests.
- **Wave 5 A (charts):** segment label size, sparse charts (≤ 3 categories), note clearance, line axes above zero.
- **Wave 5 B (`layout/diagram.py`, `l3fill.py`, `vfill.py`, `engine.py`):** tree boxes hug content, ruled panel dead third,
  sibling decision cards share a grown text size, aligned rules across 2x2 cards.
- **Wave 5 status:** sparse-chart axes/labels, segment labels scale + hide, line axes above zero, note inset; tree boxes hug
  content (2pt connectors), ruled panels end under their note, card rows aligned; lone chart text scales with the frame,
  lone chevron rows capped. 1913 tests. Smoke c05 skill-only: 3 calls, 0 images, accepted, cost above start 20.0k (19.8–20.0k).
- **Wave 6 status:** gantt bar badges are native pills inside the bar (16 s9, 19 s4, 20 s10). 1917 tests.
- **Re-score 2 (same prompt):** 11 = 3.5, 16 = 3.5, 19 = 3.5, 20 = 3.5, 22 = 4 "yes (nearly)" (reviewer variance: 20 was 4 in
  re-score 1). Top asks: dead space in panels, flat badge tags inside rounded gantt bars, tall one-line table rows / 9pt
  headers on dense slides, chart callouts touching bars, small-delta waterfalls, covers.

## Leftovers for the next run
- [ ] L3: callout clearance from bars (20 s3/s8, 22 s4); dense table
      rows too tall for one line + 9pt headers (20 s3/s5/s7); waterfall with small deltas (break or delta mode); covers
- [ ] U+2060 number+unit joiners break Ctrl+F/copy in PowerPoint → replace by phrase packing for CJK where possible
- [ ] 16 s9: a badge in the first gantt column still pins that column wider than the rest
- [x] Owner decisions (PowerPoint check, PyPI deferred, AC4 on >= 5-slide briefs, L3 on content-rich decks) recorded
      in TARGETS.md and AGENT_COST.md (c22c3d7, 2026-10-06)
- [ ] AC4 (open; >= 5-slide briefs at 41%, gate 35%)
- [x] Deck-length bench (owner, 2026-10-06; replaces the 20–30 slide brief idea): ONE shared topic for both arms,
      three briefs of the same topic: T1 at most 5 slides, T2 at most 15, T3 at most 25. One run per arm per brief
      (SlideMark skill-only + python-pptx = 6 runs total), python-pptx numbers reused until the brief set changes.
      Topic: a fictional company's FY2027 business plan, Japanese business style (dense JA is the first-class target),
      content given word for word, T2/T3 extend T1 with more sections rather than a new subject. Report per brief:
      model calls, output tokens, cost above common start, ratio vs python-pptx, accepted yes/no. Hypothesis: the ratio
      falls with deck length (run 6 medians above start: 3 slides 55%, 5 slides 44%, 10 slides 32%).
      Keep every artifact for side-by-side review (owner): `bench/lengthbench/<t1|t2|t3>/brief.md`,
      `slidemark/deck.md`, `python-pptx/build.py` (exactly as the agents wrote them, never edited), one contact-sheet
      PNG per arm (`sheet.png`), and the run numbers in `result.json`; no .pptx in git. Then generate
      `docs/COMPARE.md` (English) with, per brief, the two sources side by side (collapsed blocks), their o200k token
      counts, calls, output tokens, cost above start, ratio, and both contact sheets; link it from README (Vietnamese).
- [ ] Deck-length bench result (2026-10-06, docs/COMPARE.md): SlideMark 4/5/7 calls vs 8/11/10, 18/40/70 s vs
      86/140/198 s, cost 32%/40%/32%, all 6 accepted. Visual gap seen in the 25-slide sheets: the python-pptx arm
      looks richer (accent-bar KPI cards, carded bullets, chevron + label boxes, footers); SlideMark KPI rows are small
      with large empty bands (t3 s2/s9/s14/s20), bullet and chevron slides are sparse (s5/s8/s13/s16/s23/s25).
      Fix the defaults (fill, size, card look) so a plain deck matches without more agent tokens.
- [ ] Design reviewer (owner, 2026-10-06): add a design-review agent next to the cost bench. Prompt:
      `bench/design_review_prompt.md` (blind, absolute top-designer bar, 8 criteria incl. colour, visual devices,
      details; the L3 prompt skipped colour and only listed defects). Run it on the contact sheets of every
      deck-length bench run and after each wave's gallery; record per-criterion scores in `bench/design_review.jsonl`.
      Owner verdict on the first bench: both arms still look plain; SlideMark has fewer components, less colour and
      fewer details than python-pptx. Goal: SlideMark's default output scores >= 4 overall on the absolute bar with no
      extra agent tokens, by richer defaults per slide type (KPI cards with accent bars and unit styling, carded
      bullets, chevrons with label boxes, accent on the key number/takeaway, footer + page number + source line,
      designed cover and closing), all as tokens/presets an agent can override (design freedom).
- [ ] Design experiment 1 (2026-10-06, reverted): a neutral "Design is yours" section in SKILL.md (decide a look
      up front, one focal point, form fits content, space as a choice, one system, use css/@html instead of
      dropping an idea). 15-slide brief, one run: 11 calls / 6 builds / 99 s / cost 171k vs 5 / 2 / 40 s / 85k
      before, and the blind judge (`bench/design_review_prompt.md`, scores in `bench/design_review.jsonl`) ranked
      it lowest: python-pptx 3.5, SlideMark baseline 3.0, SlideMark + advice 2.5 (generic icons, hollow cards).
      The agent read the advice, tried to design, then fought the tool (asked for 48pt KPI values, got 30pt from
      fitting; "could not enlarge those blocks"; read SlideMark source). Lesson: advice without matching
      capability adds calls and decoration. Next, capability before advice: what the judge says separates the
      decks is structure that carries meaning (one hero metric, a step paired with its outcome, the growth rows
      highlighted, cards that hug their text, the plan bar highlighted, a closing slide). Check which of these the
      syntax already has (`hl=`/`note=`, `.accent`, chevron bullets) and why agents do not reach for them; add the
      missing ones as syntax, then document them as capabilities (not rules) in SKILL.md and re-run the judge.
- [ ] Design wave 1 (2026-10-06, merged): table `hl=` rows, `@steps` (arrows + outcome cards, sparse groups fill
      the body), `{.kpi .hero}` and exact KPI ratio grids, lone KPI rows that fill, lead in body colour and larger,
      all as tokens; SKILL.md patterns now use them. Agent run on the 15-slide brief: 4 calls, 27 s, cost 61k (was
      5 / 40 s / 85k). Blind judge round 2: python-pptx 3.5, old SlideMark 3.0, new run 2.5 (n = 1, noisy). The
      hero KPI was called the new deck's real strength; still weak: the agent kept `@chevron` (thin strip), sparse
      bullet and box slides float, table/bullet text small for the space, red accent used as a data colour in
      jp-business charts, no closing slide. Wave 2 candidates: give `@chevron` the same sparse composition as
      `@steps`; sparse bullet/box slides compose (grow text, balance); tables grow text to fill; chart palettes
      keep the accent for emphasis (`hl=`) rather than as a series colour; then re-judge with 3 runs per arm.
- [ ] Design experiment 2 (2026-10-06, not adopted): SKILL.md + the "Design Ideas" section of Anthropic's pptx
      skill (read in place; its licence forbids copying it into this repo). 15-slide brief: 13 calls, 6 builds,
      120 s, cost 230k (more than python-pptx 212k); the agent guessed undocumented layout tokens to stretch cards.
      Blind judge round 3: python-pptx 3.5, this run 3.0, wave-1 run 3.0 (same deck scored 2.5 in round 2: judge
      noise is about ±0.5). Verdict: external design prose adds cost, not score. Defects the judge named in all
      three rounds (fix as defaults, wave 2): accent red used as a data series colour in jp-business charts; pie
      without % labels and a tiny legend; line labels overlapping at the last point; sparse slides that float
      (chevron strip, mid-slide bullets, cards in the top third); takeaway bar detached far below its table;
      equal-weight KPI rows when no hero is set; a list of policies could read as a numbered list.
- [ ] Design experiment 3 (2026-10-06, not adopted): one owner-written paragraph at the top of SKILL.md (picture
      the components the topic and audience need, weigh every element's position, shape, format, colour and
      content, build as if you had one chance to convince). 15-slide brief: 4 calls, 1 build, 27 s, cost 72k
      (wave-1 run: 4 calls, 61k). Blind judge round 4: python-pptx 3.5, this run 3.0, wave-1 run 3.0; the judge
      called the two SlideMark decks almost identical. Deck in `bench/lengthbench/t2/slidemark-onechance/`.
      Verdict: three kinds of design prose (rules-free advice, external guide, intent paragraph) moved no score;
      the gap is in the defaults the judge names every round (same list as experiment 2), so fix those (wave 2).
- [x] Design wave 2 (2026-10-06, merged 61cefe3): the judge-named defects fixed as token defaults, SKILL.md
      unchanged. Lane A `layout.*`: short list grows into the body (`list_fill*`), text cards stretch to the body
      (`cards_to_body*`), `@chevron` with short bodies is built as `@steps` (`chevron_steps`), the conclusion
      bar attaches to its table (`bar_attach=grow`), a lone table grows its text to 22pt (`table_free*`), KPI
      rows and `@steps` fill the body (`kpi_to_body*`, `steps_to_body*`); small-body themes only. Lane B
      `render.*`: preset palettes without the accent, pie `labels=on` = share labels (`chart_pie_*`), bigger
      legend / labels (`chart_legend_scale` 1.2, `chart_label_scale` 1.0), line label collisions alternate
      (`chart_collide_em`), `chart-scale` info line (info, not warning: a brief may want both series on one
      chart). Fresh-agent run on the 15-slide brief: 5 calls, 2 builds, 36 s, cost 73k, accepted. Blind judge
      round 5: python-pptx 3.5, this run 3.0, wave-1 deck 2.5 (it scored 3.0 in rounds 3 and 4: noise ±0.5;
      within one round wave 2 is +0.5 over wave 1). Deck in `bench/lengthbench/t2/slidemark-wave2/`.
      Still named: tall cards holding one short bullet look like padding (steps, boxes); a plain list for an
      ordered set of policies; the accent-free palette is now too single-hue to tell pie wedges / lines apart;
      the python-pptx deck's footer + page number on every slide reads as "finished".
- [x] Design wave 3 (2026-10-07, owner direction `docs/DESIGN_REQUIRED.md`: SlideMark assists decisions, it does
      not replace them; the agent states position, colour, shape and type like python-pptx forces it to).
      Lane 1 SKILL.md "Decide first" step + two patterns where every slide carries choices (3,797 tokens, budget
      3,800). Lane 2 `docs/DESIGN_COVERAGE.md` (64 python-pptx decisions: 39 covered, 21 new, 4 skipped): chrome
      tokens `top.bar` `title.rule` `kpi.stripe` `kpi.label/value/note.*` `bullet=` `footer.*`, `@rows`, `steps
      num`, cyclic `steps-arrow.fill`, cover `bar`/`band=none`, chart `gap= marker= size= labels=<pos>`, `hl=`
      names a series, `colors:` names in `colors=`, pinned sizes `20!`, `layout.html_footer`. Lane 3
      `design-none` / `design-slide` warnings + `design:` facts line (`src/slidemark/design.py`). Lane 4 port
      of the python-pptx deck: 2,283 tokens (43%), `bench/lengthbench/t2/slidemark-ported/REPORT.md`. Lane 5
      examples state their design. Fresh-agent run on the 15-slide brief: 9 calls, 5 builds, 91 s, cost 129k,
      deck 1,595 tokens, `14/14 slides carry choices`, accepted. Blind judge round 6: **this run 3.5 (rank 1)**,
      wave-2 deck 3.0, python-pptx 2.5 (rank 3; it scored 3.5 in rounds 1–5, so cross-round noise is large, but
      within the round the judge named why: one accent used as a rule, takeaways on the charts). Cost rose from
      73k to 129k (61% of python-pptx 212k; 9 calls vs 11; 91 s vs 140 s): the price of decisions, accepted by
      the owner. Deck in `bench/lengthbench/t2/slidemark-wave3/`. Still named: tall cards with one bullet
      (steps, boxes), KPI rows all equal when the agent sets no hero, two reds in the pie (`palette` had the
      accent twice), tiny chart note boxes.
- [ ] Call path (owner, 2026-10-06): the current path is 3 calls (1 read brief + SKILL.md, 2 write + `build` in one
      tool call, 3 read the facts line and hand back). 51/68 run-6 runs took exactly 3; the other 17 (25%) took 4–9,
      mostly from opening preview PNGs and rebuilding. (a) Remove that tail: find what made those agents look or
      rebuild and turn it into a build-line fact, a lint rule or an auto-fix. (b) Measure a 2-call path where SKILL.md
      is already in the agent's starting context (installed skill or prompt), so call 1 writes + builds and call 2
      hands back; report the saving and the cost of carrying SKILL.md when no deck is made.
