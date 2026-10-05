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
      source line, 10–12pt) built from Markdown only, judged "consulting-grade" in review
- [x] Components: cards, callouts, KPI, steps/chevrons, badges, connectors, icons, 12-column grid
- [x] All 10 chart kinds native with labels/legend/number formats; OMML math (OMML verified in XML; LibreOffice shows the fallback)
- [x] `check` linter: overflow, off-slide, overlap, low contrast, missing alt → one-line JSON diagnostics
- [x] Syntax tokens ≤ 30% of python-pptx; dense slide **markup** (tokens minus the content text) ≤ 40% of the equivalent HTML markup (gate changed by the owner 2026-10-05: content text is the same in every format; q3 30% ✓; `bench/markup_tokens.py`: jp-dense 23%, jp-kpi 28%, q3 13% ✓)

## L4: Agent-native
- [x] `slidemark docs`, `schema`, `skill install`; SKILL.md ≤ 1,500 tokens, each reference file ≤ 800
- [x] Lenient parser: Marp/Slidev/common-mistake variants accepted with warnings (fuzz: 0 crashes in 100k inputs; bench/fuzz_long.py seed 11, 2026-10-05)
- [x] Agent eval (≥ 20 tasks): first-pass `check` success ≥ 90%, mean fix rounds ≤ 0.3 (run-2-sonnet: 20 tasks, 90%, 0.1 warnings/task, docs only; fix rounds proxied by warnings)
- [x] Total agent tokens per deck (docs + output + fixes) ≤ 40% of a python-pptx agent on the same tasks (run-4: (SKILL.md 909 + deck 152) / python-pptx 2,704 = 0.39, 20/20 first pass, no reference pages read)

## L5: Full PowerPoint
- [x] HTML → native shapes (Chromium measurement) with image fallback; Mermaid → native shapes (`slidemark.htmlnative`: grid/flex cards, runs, lists, tables → native, canvas/svg/gradients → image; 2026-10-05)
- [ ] Transitions, build animations, hyperlinks/slide jumps, sections, hidden slides, video/audio (all ✓ incl. native video/audio since run 2026-10-05b; PowerPoint repair check of the timing XML pending, owner)
- [x] User templates `.potx`/`.pptx`: placeholders, masters, theme colors/fonts reused (examples/10-template)
- [x] Feature matrix (`docs/FEATURES.md`) ≥ 90% of rows fully Done (all 8 DoD steps): 32/34 = 94% (2026-10-05, run 2)

## L6: Production grade
- [ ] 0 "repair" prompts: XSD-valid on 10k fuzzed decks + spot-checked in real PowerPoint each release (XSD half ✓: `bench/xsd_fuzz.py` 10k decks seed 7 → 0 invalid, 2026-10-05; real-PowerPoint spot check pending, owner)
- [x] Import `.pptx → Markdown` (edit existing decks); build → import → build is stable (all 9 examples, 2026-10-05)
- [x] Build ≤ 50 ms/slide, import time ≤ 300 ms, slidemark's own package ≤ 2 MB and core install ≤ python-pptx's own install + 20 MB (gate changed by the owner 2026-10-05: python-pptx alone is 34 MB; build 27 ms/slide ✓, `import slidemark` 165–240 ms ✓, package 1 MB ✓, core 50 MB = +16 MB ✓)
- [ ] Published on PyPI with semver, changelog, CI on 3 Python versions, coverage ≥ 90% (CI 3.10–3.12 ✓, coverage 93% ✓, changelog ✓; PyPI publish needs the owner's token)

## L7: Breakthrough
- [ ] Blind review: agent-made decks preferred or tied against professional human decks in ≥ 50% of pairs
- [x] Vision self-review loop: `preview` + automatic design critique fixes layout issues without human input (run 4: `slidemark review --fix [--png]`: trial-built source edits incl. slide split, dense, ink swap, title→lead, pixel contrast; `bench/selfreview.py`: 27/30 synthetic broken decks end warning-free, mean score 96.1 → 99.1, examples untouched)
- [ ] Tokens near the floor: syntax ≤ 20% of python-pptx; ≥ 95% of tasks need only SKILL.md (no reference reads) (run 4: q3 content floor alone is 25% → unreachable on q3; agent-written decks 6% of python-pptx answers, 99% of 100 tasks pass from SKILL.md only; owner decision proposed in `docs/TOKEN_FLOOR.md`)
- [x] Agent eval first-pass success ≥ 98% across ≥ 100 tasks, including dense JP and HTML-heavy decks (100 tasks: run-4 01–20 20/20 + run-5 21–100 79/80 = 99%; jp 34/34, html 17/17, hard 10/10; Sonnet, SKILL.md only, 2026-10-05)
- [ ] Lossless round-trip of any deck the library produced (`bench/roundtrip.py`: 117/117 = 100% on 17 examples + 100 eval answers incl. CSS/HTML-designed decks, design source round trip 4/4, 2026-10-05 run 4); real-world `.pptx` import ≥ 95% fidelity (`bench/import_fidelity.py` on 19 agent-written python-pptx decks: 0.975, lenient metric; color fidelity 0.847 via derived look tokens; true real-world decks still needed)
- [ ] Every presentation feature of PowerPoint reachable from text; nothing requires opening PowerPoint to fix
