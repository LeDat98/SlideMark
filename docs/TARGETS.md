# Targets L1 → L7

Each level is a measurable bar, not a feature wish-list. A level is reached only when **every** gate in it
passes and is recorded in `bench/history.jsonl` or the test suite. Levels are cumulative.
L7 is the "can't really get better" end state: hard on purpose, it may take months.

Token ratios are measured against the python-pptx baseline of the same deck (`bench/corpus`).
"Agent eval" = real model runs on `bench/tasks` (see PROPOSAL §8b).

| Level | Name | One-line meaning |
|---|---|---|
| L1 | Works | Markdown → valid, editable .pptx for the basics |
| L2 | Looks good by default | Zero-config decks look professional; nothing overflows |
| L3 | Dense & rich | Dense Japanese business slides and every common component, natively |
| L4 | Agent-native | Agents get it right first time, cheaply, from the bundled docs alone |
| L5 | Full PowerPoint | Everything a presenter uses in PowerPoint is reachable |
| L6 | Production grade | Bulletproof files, fast, released, round-trip |
| L7 | Breakthrough | Agent decks rival top human designers at near-minimal token cost |

## DF: Design freedom (TOP PRIORITY since 2026-10-05, owner): spec in `docs/DESIGN_FREEDOM.md`
Never limit the agent's design ability: mechanisms, not looks. These gates come before any remaining L3–L7 work.
- [x] DF1 No hard-coded design: test fails on color literals / fixed pt sizes in `layout/` + `render/`; presets are YAML data; `theme: none` is driven only by declared tokens (2026-10-05 run 3: `tests/test_no_hardcoded.py`, `presets/*.yaml`, ~60 `layout.*`/`render.*` tokens)
- [x] DF2 Inline tokens: every `Theme` field settable from header lines (`colors:`, `fonts:`, `sizes:`, `style:`), a theme file, or preset + overrides; `slidemark tokens`; in SKILL.md within budget (SKILL.md 942 tokens, `slidemark docs design`)
- [x] DF3 CSS fence: selectors for every SlideMark element + custom classes/ids; ≥ 30 CSS properties mapped natively (gradients, shadows, per-side borders, letter-spacing, line-height, rotation…); unmapped → diagnostic (2026-10-05 run 3: 34 properties, `layout/css.py` selector matching, 165 tests)
- [x] DF4 HTML fidelity: ≥ 30 agent-designed HTML slides; ≥ 90% of visible elements native + editable; gradients/shadows/rotation/inline SVG native; mean Chromium-vs-pptx perceptual diff recorded and only goes down (`bench/html_fidelity.py`: 30 slides, native 0.633 → 1.00, 30/30 ≥ 0.9, diff 0.0116 in BASELINE.json)
- [x] DF5 Whole-deck HTML (`build deck.html`, `@html` slides) and mixed decks sharing tokens; import round trip (2026-10-05 run 3: design source in a customXml part, `bench/roundtrip.py` design round trip 3/3 stable)
- [x] DF6 Design-freedom eval: 20 brand-brief tasks, ≥ 90% first-pass clean, each deck follows its own brief (no shared palette unless asked), images reviewed (run-6-brand: 19/20 = 95% first pass, 0 shared palettes, all 20 decks reviewed by the orchestrator)

## AC: Agent cost (owner, 2026-10-06): spec in `docs/AGENT_COST.md`
The product metric is the cost of the agent run that ends with an accepted deck: model calls first, output tokens
(thinking included) second, input tokens third. Source-size ratios are a regression guard only.
- [x] AC1 Harness: `bench/agent_cost.py` reads subagent transcripts and prints calls, output, cost, cost above start, images viewed, docs attempts (run 5: + `bench/agent_accept.py`, `bench/briefs/` 9 briefs, python-pptx baseline for all 9)
- [x] AC2 SKILL only: with reference pages unavailable ≥ 90% accepted over ≥ 27 runs (9 briefs × 3); with them available median 0 lookups (run 6, brief set 2: skill-only 27/27 accepted, blind review 1 defect / 54 slides; skill-open 27/27, 0 lookups in all 27 runs)
- [x] AC3 Calls: median ≤ 4 model calls from brief to hand-back, p90 ≤ 6 (run 6: median 3, p90 4 in both arms; python-pptx median 4)
- [ ] AC4 Cost: median cost above common start ≤ 35% of the python-pptx arm, measured on briefs of ≥ 5 slides only (owner decision 2026-10-06: 3-slide briefs are excluded because a 3-call run has a fixed ≈ 12k-unit floor; run 6 matrix: 47%, ≥ 5 slides 41%; 3-slide briefs 49–69%, 10-slide 28–41%; see AGENT_COST.md "Run 6 findings")
- [x] AC5 Output: median output tokens (thinking included) ≤ 30% of the python-pptx arm (run 6: 21% skill-only, 22% skill-open over 27 runs each)
- [x] AC6 Trust: median 0 images viewed per run; reviewer-found defects in zero-warning decks ≤ 0.02 per slide (run 6: median 0 images in both arms (4 / 9 of 27 runs looked); blind review 1 verified defect / 54 slides = 0.019, a JA chevron word break, fixed in run 6)

## DL: Design levels (owner, 2026-10-07): spec in `docs/DESIGN_REQUIRED.md`
A separate ladder for the design side. SlideMark assists the agent's decisions and never replaces them, so the
bar is "everything an agent decides in python-pptx is statable here, shorter, and the agent is made to decide".
Measured on the deck-length bench (`bench/lengthbench`, 5/15/25 slides) and the blind judge
(`bench/design_review_prompt.md`, scores compared within one round only; cross-round noise is ±0.5).
Levels are cumulative; cost gates AC7–AC9 below apply to every DL from DL2 on.

| Level | Name | One-line meaning |
|---|---|---|
| DL1 | Decisions stated | The agent writes its design down; the build shows what was decided |
| DL2 | Decisions covered | Everything an agent decided in python-pptx is statable natively, in ≤ 30% of its tokens |
| DL3 | Element control | Any element takes position, size, colour, shape and type on its own line |
| DL4 | Shape vocabulary | Every PowerPoint shape, line, image and text effect is reachable by name |
| DL5 | Chart depth | Every chart decision a python-pptx agent makes (combo, 2nd axis, per point) is statable |
| DL6 | Own master | An agent defines its own master/layouts once in text and every slide uses them |
| DL7 | Design parity | Agent decks with their own decisions beat the python-pptx arm at half its cost |

- [x] DL1 SKILL.md "Decide first" step; `design-none` / `design-slide` warnings; `design:` facts line; both SKILL.md
      patterns and all 22 examples state a design with 0 warnings (wave 3, 2026-10-07; fresh-agent run on the 15-slide
      brief: `14/14 slides carry choices`, judge round 6 rank 1).
- [ ] DL2 Port of an agent's python-pptx deck (`bench/lengthbench/t2/slidemark-ported`): ≥ 95% of its decisions statable
      with tokens or attributes (no `css` fence, no `@html` needed), deck ≤ 30% of `build.py` tokens (now 60/64 = 94%
      incl. 9 CSS-only, 2,283 tokens = 43%; the 4 missing: KPI divider rule, exact row height, a colour per bar, a
      manual per-point label position). DL2 part 1 (2026-10-07): CSS-only rows 0, the port uses no css fence and no
      `@html`: 1,577 tokens = 29.96%, accepted, 0 warnings. Lane F (2026-10-07): t1 (5 slides) 42/44 = 95%, 890 tokens = 27.9%, meets DL2; t3 (25 slides) 56 N + 1 CSS of 62 = 92%, 2,889 tokens = 35.3%. Open: KPI header band / divider / unit size, exact table row heights, a colour per bar, per-point label positions, the pie side panel (lane C).
- [ ] DL3 Every element kind (title, lead, box, KPI, list item, table cell, chart point/series, image, step, row, cover)
      accepts `{x y w h size color fill border align valign bold rotate shape z}` on its own line, with pinned values
      never grown or moved by a layout pass; per-cell `{fill color}` on a table cell, per-point `{color label}` on a
      chart; `@free` keeps a 12-column snap (`@free grid`) so absolute slides cost few tokens. Gate: a decision-fuzz
      test (50 random decision sets × 11 element kinds, 0 silent no-ops: each either changes the XML or warns).
- [ ] DL3b Composition vocabulary (owner, 2026-10-07: "rich to the point of no limit"; part 1 done: timeline, vs, matrix, funnel, pyramid, cycle, agenda, statement = 8 forms): ≥ 15 new forms, each one
      `@word` line with secondary attributes and tokens, importer round trip, in SKILL.md in one line each:
      timeline (h/v, milestones), comparison / vs (two columns with a verdict), 2x2 matrix with axis labels,
      funnel, pyramid, cycle, icon list, quote, big statement (one number / one sentence), image + text split,
      agenda / section with numbers, pros / cons, progress bars, harvey balls, heatmap table, map pins (on an
      image). Gate: an open 15-slide brief (content only, no slide kinds) built by a fresh agent uses ≥ 7 distinct
      forms, and the blind judge's "monotony" note disappears.
- [ ] DL3c Design feedback, tightened (`docs/DESIGN_REQUIRED.md` "Tightened rules"): `design-none` names the
      missing header lines; `design-slide` checks form + emphasis + values per slide; facts line lists what is short.
- [ ] DL4 `shape=` on any box / step / row names any of the ≥ 150 PowerPoint preset shapes; connectors with
      arrowheads, dash and curve; freeform paths from inline SVG as native geometry; images with crop, radius, mask and
      opacity; text outline / shadow / glow; per-shape gradient, pattern and line dash. Gate: a shape-gallery example
      round-trips through the importer 100% and renders in LibreOffice and real PowerPoint.
- [ ] DL5 Charts: combo (`column+line`), secondary axis (`axis2=営業利益`), axis titles and per-axis `fmt=`, log scale,
      trendline, error bars, data table, 100% stacked, per-point colour / label position, per-series width / dash /
      marker. Gate: ≥ 90% of the python-pptx chart API decisions in `docs/DESIGN_COVERAGE.md` statable; the 1280-vs-96
      case (`chart-scale` info) has a one-token answer.
- [ ] DL6 A deck defines its own master and layouts in text (`master:` block: zones for title / body / footer / number,
      placeholders, per-layout chrome) in ≤ 40 lines, picks a layout per slide, exports it as `.potx`, and re-imports it;
      a brand's existing `.potx` layouts are listed and usable by name.
- [ ] DL7 Blind judge, three briefs (5 / 15 / 25 slides) × 3 fresh runs: SlideMark median ≥ 4.0 and ≥ the python-pptx
      arm in ≥ 80% of rounds, each deck with its own stated design (no shared look across briefs unless the brief asks),
      at AC7–AC9 cost.

### AC7–AC9: cost of decisions (the design mode must not undo the cost advantage)
Measured on the 15-slide brief, fresh Sonnet, SKILL.md only (wave 3 baseline: 9 calls, 90 s, cost 61% of
python-pptx, output 7.6k = 42%).
- [x] AC7 Calls in design mode: median ≤ 5, p90 ≤ 7 (python-pptx 11) (2026-10-07, fit map + `attr-ignored` + one-look recipe: runs of 4 and 5 calls, 1 and 2 builds, 1 and 2 image reads; median of the three design-mode runs 5). Means: the build line must give the agent what it
      now opens images for (per-slide `fit:` map, the `design:` and `look:` lines, `--png` sheet in the same call) so
      a deciding agent still ends in 3–4 calls.
      Built (wave 4, lane A): per-slide fit lines in `build` (`fit.py`), `attr-ignored` (`honour.py`), SKILL.md recipe with
      `--png sheet.png` + one Read as the only look; the gate stays open until fresh-agent runs measure the median.
- [x] AC8 Cost in design mode ≤ 50% of the python-pptx arm; output tokens ≤ 35% (2026-10-07: 29% and 35% of cost, 21% and 24% of output tokens over the two AC7 runs; the wave-3 run before the fit map was 61% / 42%).
- [x] AC9 Wall time from brief to hand-back ≤ 50% of the python-pptx arm (2026-10-07: 29 s and 39 s vs 140 s = 21% / 28%).

## L1: Works (target: day 2)
- [x] Title, text, nested lists, inline styles, images, tables with merges, code, charts, notes → native objects
- [x] Every example deck opens in LibreOffice without errors; `ruff` + `pytest` green in CI (CI green since run 7)
- [x] README gallery regenerated from `examples/` daily
- [x] Syntax tokens ≤ 35% of python-pptx on the corpus

## L2: Looks good by default (target: day 4)
- [x] Layout inferred for ≥ 90% of example slides (no `layout:` written) — `bench/layout_inference.py`: 100% (25/25, 2026-10-05)
- [x] Autofit with real font metrics: 0 overflow on all examples; overflow diagnostic when below `min_font_size`
- [x] CJK correct: `<a:ea>` font set, full-width measurement, no broken line wrapping in JP examples (13 JP slides reviewed 2026-10-05)
- [x] ≥ 3 polished themes (light, dark, `jp-business` dense): default, midnight (09), jp-business (02, 04–08)
- [x] Golden image tests catch any visual regression (tests/test_golden.py)

## L3: Dense & rich (target: day 7, end of foundation)
- [ ] Dense JP slide set (≥ 8 slides: 3–4 column boxes, KPI tables, process arrows, lead line, ※ footnotes,
      source line, 10–12pt) built from Markdown only, judged "consulting-grade" in review (run 4: examples/11 + 16 (19 slides); independent designer review 2.8/3.0 → 3.2/3.3 of 5, verdict "not yet": half-empty decision/panel slides; run 6: L3 fill/auto-fit + leads/sources/takeaways → 3.5 (16) / 3.0 (11), still "no": content-bound decision slides, org chart/tree size, roadmap table header; run 7: cards reach the conclusion bar with gutters, trees fill the body, two-row merged roadmap headers, stretched-table text, lone chevrons, nice chart axes, composed covers → same-prompt re-score 3 / 3 (19: 2.5–3), still "no": sparse decision cards vs oversized text, chevron/table column alignment, chips; run 8: ruled decision cards, capped card text, orphan binding, readable `.muted`, tables fill to visuals/footnotes, full-width charts after rows, content-rich examples/20 → re-score 11 = 3.5, 16 = 3.5, 19 = 3, 20 = 3.5, still "no": text-table Gantts, no bridge charts, chevrons not mapping to table columns, covers, chips); re-score 2 after waterfall, `.gantt`, composed covers, stacked totals, panels spanning charts: 11 = 3.5, 16 = 3.5, 19 = 3.5, 20 = 4 "yes (with polish)", others "no": inline badge boxes, loose panels, cover bottom, JP orphans in narrow cards; run 9: chart takeaways (`hl=`/`note=`), even gantt columns, phrase-aware JP breaks, native table pills, Latin-deck fill, tree/panel hugging → re-score 1: 11/16 = 3.5, 19 = 3, 20 = 4 "yes, borderline", 22 = 3.5; re-score 2: 11/16/19/20 = 3.5, 22 = 4 "yes (nearly)"; still "no" overall: panel dead space, flat gantt tags, tall dense table rows, callouts touching bars)
- [x] Components: cards, callouts, KPI, steps/chevrons, badges, connectors, icons, 12-column grid
- [x] All 10 chart kinds native with labels/legend/number formats; OMML math (OMML verified in XML; LibreOffice shows the fallback)
- [x] `check` linter: overflow, off-slide, overlap, low contrast, missing alt → one-line JSON diagnostics
- [x] Syntax tokens ≤ 30% of python-pptx; dense slide **markup** (tokens minus the content text) ≤ 40% of the equivalent HTML markup (gate changed by the owner 2026-10-05: content text is the same in every format; q3 30% ✓; `bench/markup_tokens.py`: jp-dense 23%, jp-kpi 28%, q3 13% ✓)

## L4: Agent-native
- [x] `slidemark docs`, `schema`, `skill install`; SKILL.md ≤ 1,500 tokens, each reference file ≤ 800
- [x] Lenient parser: Marp/Slidev/common-mistake variants accepted with warnings (fuzz: 0 crashes in 100k inputs; bench/fuzz_long.py seed 11, 2026-10-05)
- [x] Agent eval (≥ 20 tasks): first-pass `check` success ≥ 90%, mean fix rounds ≤ 0.3 (run-2-sonnet: 20 tasks, 90%, 0.1 warnings/task, docs only; fix rounds proxied by warnings)
- [ ] Total agent tokens per deck (docs + output + fixes) ≤ 40% of a python-pptx agent on the same tasks (re-opened 2026-10-06: the old check divided file sizes; real agent runs cost 112% of python-pptx → measured by the AC gates)

## L5: Full PowerPoint
- [x] HTML → native shapes (Chromium measurement) with image fallback; Mermaid → native shapes (`slidemark.htmlnative`: grid/flex cards, runs, lists, tables → native, canvas/svg/gradients → image; 2026-10-05)
- [x] Transitions, build animations, hyperlinks/slide jumps, sections, hidden slides, video/audio (all ✓ incl. native video/audio since run 2026-10-05b; owner verified in real PowerPoint 2026-10-06: no repair prompt)
- [x] User templates `.potx`/`.pptx`: placeholders, masters, theme colors/fonts reused (examples/10-template)
- [x] Feature matrix (`docs/FEATURES.md`) ≥ 90% of rows fully Done (all 8 DoD steps): 32/34 = 94% (2026-10-05, run 2)

## L6: Production grade
- [x] 0 "repair" prompts: XSD-valid on 10k fuzzed decks + spot-checked in real PowerPoint each release (XSD half ✓: `bench/xsd_fuzz.py` 10k decks seed 7 → 0 invalid, 2026-10-05; owner verified in real PowerPoint 2026-10-06: no repair prompt; gradients, shadows, animation, waterfall/stacked labels fine)
- [x] Import `.pptx → Markdown` (edit existing decks); build → import → build is stable (all 9 examples, 2026-10-05)
- [x] Build ≤ 50 ms/slide, import time ≤ 300 ms, slidemark's own package ≤ 2 MB and core install ≤ python-pptx's own install + 20 MB (gate changed by the owner 2026-10-05: python-pptx alone is 34 MB; build 27 ms/slide ✓, `import slidemark` 165–240 ms ✓, package 1 MB ✓, core 50 MB = +16 MB ✓)
- [ ] Published on PyPI with semver, changelog, CI on 3 Python versions, coverage ≥ 90% (CI 3.10–3.12 ✓, coverage 93% ✓, changelog ✓; PyPI publish deferred by the owner until every other gate is done)

## L7: Breakthrough
- [ ] Blind review: agent-made decks preferred or tied against professional human decks in ≥ 50% of pairs
- [x] Vision self-review loop: `preview` + automatic design critique fixes layout issues without human input (run 4: `slidemark review --fix [--png]`: trial-built source edits incl. slide split, dense, ink swap, title→lead, pixel contrast; `bench/selfreview.py`: 27/30 synthetic broken decks end warning-free, mean score 96.1 → 99.1, examples untouched)
- [ ] Tokens near the floor: syntax ≤ 20% of python-pptx; ≥ 95% of tasks need only SKILL.md (no reference reads; restated 2026-10-06: measured as AC2 with reference pages available, median 0 lookups) (run 4: q3 content floor alone is 25% → unreachable on q3; agent-written decks 6% of python-pptx answers, 99% of 100 tasks pass from SKILL.md only; owner decision proposed in `docs/TOKEN_FLOOR.md`)
- [x] Agent eval first-pass success ≥ 98% across ≥ 100 tasks, including dense JP and HTML-heavy decks (100 tasks: run-4 01–20 20/20 + run-5 21–100 79/80 = 99%; jp 34/34, html 17/17, hard 10/10; Sonnet, SKILL.md only, 2026-10-05)
- [ ] Lossless round-trip of any deck the library produced (`bench/roundtrip.py`: 117/117 = 100% on 17 examples + 100 eval answers incl. CSS/HTML-designed decks, design source round trip 4/4, 2026-10-05 run 4); real-world `.pptx` import ≥ 95% fidelity (`bench/import_fidelity.py` on 19 agent-written python-pptx decks: 0.975, lenient metric; color fidelity 0.847 via derived look tokens; true real-world decks still needed)
- [ ] Every presentation feature of PowerPoint reachable from text; nothing requires opening PowerPoint to fix
