# Daily log

Newest at the bottom. ≤ 10 lines per day: done · metrics · problems · next.

## 2026-10-04 (day 0, manual session)
- Done: proposal, 7-day plan, targets L1–L7, IR contract, theme/units, syntax v0, bench v0, project notes.
- Metrics: syntax tokens compact 158 / python-pptx 528 (30%), o200k proxy.
- Changed: own syntax v1 (headings = structure, `@` grid line); max 2 subagents (A front, B back); push to `main`.
- Metrics: q3 deck 155 tokens (30% of python-pptx 518); dense JP deck 482 vs HTML 828 (58%).
- Next: day 1 work packages by the 02:45 JST routine.

## 2026-10-04 (day 1, routine)
- Done: parser v1 + CLI (A), layout + renderer + 3 themes (B), preview, gallery, CI, examples, FEATURES (orchestrator); merged, 150 tests.
- Metrics: tests 150 passed / 1 skipped; q3 deck 155 tokens = 30% of python-pptx (518), 48% of HTML (321); jp-dense 482 vs HTML 828 (58%); unchanged vs day 0.
- Problems: sandbox lacked libreoffice-impress (installed via apt); parser/layout disagreed on merged-cell shape (fixed in layout); a table after the last `##` is swallowed into that box (jp-dense slide 2 table missing from render).
- Next: finish day 1 leftover (box terminator), then day 2 (lenient parsing, real font metrics, golden images, CI token gate).

## 2026-10-05 (day 2, manual run)
- Done: `@end` box terminator (day 1 leftover); lenient parsing (Marp/Slidev/Note:) with difflib hints + fuzz (A); chevron non-text children, footnote autofit, kinsoku, zebra tables (B); golden image test, BASELINE.json token gate (orchestrator).
- Metrics: tests 196 passed / 1 skipped; q3 deck 155 tokens = 30% of python-pptx, 48% of HTML; jp-dense 482 vs HTML 828 (58%); unchanged vs day 1.
- Problems: libreoffice-impress had to be apt-installed again; jp-dense slide 2 table now renders but is squeezed into one grid cell.
- Next: slide-level visuals below a chevron/grid row, day 3 (components, dense JP, connectors).

## 2026-10-05 (days 3–7 + gates, Opus-led run, 01:34–03:35 UTC)
Run goal:
- [x] Day 2 leftover: slide-level visual under a chevron/grid row gets its own full-width row
- [x] Day 3: components (kpi, callouts, badges, connectors, heading band, dense), ≥ 5 dense JP decks
- [x] Day 4: chart/table options, all chart kinds, OMML math, `check` linter v1 + JSON
- [x] Extended: days 5–7 (docs/schema/skill, templates, mermaid/HTML, animations/sections), icons, .pptx import, row groups, font metrics
- Done: 9 waves, 18 Sonnet coding subagents + 5 eval agents; L2 reached, all L4 gates pass; L3 3/5, L5 2/4, L6 1/4.
- Metrics: tests 602 passed (1 skipped); q3 155 tokens = 30% of python-pptx, 48% of HTML; jp-dense 482 vs HTML 828 (58%); unchanged.
- Agent eval (Sonnet, SKILL.md only, 20 tasks): 100% first pass, (skill 909 + deck 152) / python-pptx 2,704 = 0.39.
- Layout inference 100% (28/28 slides); fuzz 100k inputs 0 crashes; build 27 ms/slide; import ~200 ms; install 50 MB (python-pptx deps).
- Problems: preview fonts (DejaVu for Calibri) faked wraps → Carlito + aliases; I pushed two red commits (fixed within minutes).
- Open: dense ≤ 40% of HTML gate is content-bound (markup overhead is ~16% of HTML's); PowerPoint repair check for animations/morph/sections/OMML not possible here.
- Next: L3 consulting-grade review pass, video/audio, Chromium HTML measurement, XSD validation, PyPI packaging.

## 2026-10-05 (run 2, manual, 04:10–07:20 UTC)
Run goal:
- [x] Leftover: sparse box slides + consulting-grade layout pass (top anchoring, content-sized cards/chevrons/trees/tables, growth, layout search)
- [x] Leftover: importer reconstructs connectors (`a>b`) and mermaid diagrams; round trip 59.5% → 97–98% lossless (112 decks)
- [x] L5: video/audio natively embedded; HTML → native via Chromium; SVG pictures
- [ ] L3: dense JP consulting deck (examples/11, 9 slides) reviewed: much better, slide 9 still half empty → gate stays open
- [x] L6: XSD validation (10k fuzzed decks, 0 invalid); CI on 3.10–3.12 with Chromium; coverage 93%
- Done: 10 waves, 17 Sonnet coding subagents + 2 eval agents; also `slidemark review`, `check --fix`, eval to 100 tasks.
- Metrics: tests 866 passed (1 skipped, 1 xfail); q3 155 tokens = 30% of python-pptx (unchanged); markup ratio vs HTML 13–28%.
- Eval (Sonnet, SKILL.md only): tasks 21–100 80/80 after fixes (79/80 first run) → 100 tasks 100%; review mean 97.25.
- Whitespace: sparse cards 12 → 0, mean card fill 56% → 70%; layout inference 100% (40 slides); foreign import 0.975.
- Bugs found by new tooling: title > 255 chars crashed, negative chart axIds, empty media timing sequence (XSD), image line swallowed under a list (eval).
- Problems: a parallel owner session pushed to main (merged); I pushed one red commit (pipe hid pytest's exit code), fixed in minutes.
- Next: L3 consulting judgement (slide 9 fill), PowerPoint spot check of media/SVG/animation XML (owner), PyPI token (owner).

## 2026-10-05 (run 3, manual, design freedom, 07:40 UTC–)
Run goal:
- [ ] DF1 no hard-coded design: layout/render constants → `theme.layout`/`theme.render` tokens, presets as YAML, `theme: none`, literal-scanner test
- [ ] DF2 inline tokens: `colors:`/`fonts:`/`sizes:`/`style:` header lines → `Deck.tokens`, `slidemark tokens`, SKILL.md
- [ ] DF3 CSS fence (if time): selectors + native mappings (gradients, shadows, per-side borders, letter-spacing …)
- [ ] Examples with agent-designed looks (brand colors, gradients, dark/light) next to dense JP; gallery reviewed
