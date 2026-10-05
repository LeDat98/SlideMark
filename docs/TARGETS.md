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
- [ ] Syntax tokens ≤ 30% of python-pptx; dense slide ≤ 40% of the equivalent HTML (30% ✓; dense 58–60% ✗: content text dominates)

## L4: Agent-native
- [x] `slidemark docs`, `schema`, `skill install`; SKILL.md ≤ 1,500 tokens, each reference file ≤ 800
- [x] Lenient parser: Marp/Slidev/common-mistake variants accepted with warnings (fuzz: 0 crashes in 100k inputs; bench/fuzz_long.py seed 11, 2026-10-05)
- [x] Agent eval (≥ 20 tasks): first-pass `check` success ≥ 90%, mean fix rounds ≤ 0.3 (run-2-sonnet: 20 tasks, 90%, 0.1 warnings/task, docs only; fix rounds proxied by warnings)
- [x] Total agent tokens per deck (docs + output + fixes) ≤ 40% of a python-pptx agent on the same tasks (run-4: (SKILL.md 909 + deck 152) / python-pptx 2,704 = 0.39, 20/20 first pass, no reference pages read)

## L5: Full PowerPoint
- [ ] HTML → native shapes (Chromium measurement) with image fallback; Mermaid → native shapes (HTML subset parser + Chromium image fallback ✓, Mermaid flowcharts ✓; no Chromium measurement yet)
- [ ] Transitions, build animations, hyperlinks/slide jumps, sections, hidden slides, video/audio (all but video/audio ✓; PowerPoint repair check pending)
- [x] User templates `.potx`/`.pptx`: placeholders, masters, theme colors/fonts reused (examples/10-template)
- [x] Feature matrix (`docs/FEATURES.md`) ≥ 90% of rows fully Done (all 8 DoD steps): 27/29 = 93% (2026-10-05)

## L6: Production grade
- [ ] 0 "repair" prompts: XSD-valid on 10k fuzzed decks + spot-checked in real PowerPoint each release
- [x] Import `.pptx → Markdown` (edit existing decks); build → import → build is stable (all 9 examples, 2026-10-05)
- [ ] Build ≤ 50 ms/slide, import time ≤ 300 ms, core install ≤ 15 MB (build 27 ms/slide ✓; `import slidemark` 165–240 ms ✓ with lazy python-pptx; install 50 MB ✗: python-pptx alone pulls lxml + Pillow ≈ 31 MB, slidemark wheel ≈ 0.2 MB)
- [ ] Published on PyPI with semver, changelog, CI on 3 Python versions, coverage ≥ 90%

## L7: Breakthrough
- [ ] Blind review: agent-made decks preferred or tied against professional human decks in ≥ 50% of pairs
- [ ] Vision self-review loop: `preview` + automatic design critique fixes layout issues without human input
- [ ] Tokens near the floor: syntax ≤ 20% of python-pptx; ≥ 95% of tasks need only SKILL.md (no reference reads)
- [ ] Agent eval first-pass success ≥ 98% across ≥ 100 tasks, including dense JP and HTML-heavy decks
- [ ] Lossless round-trip of any deck the library produced; real-world `.pptx` import ≥ 95% fidelity
- [ ] Every presentation feature of PowerPoint reachable from text; nothing requires opening PowerPoint to fix
