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

## 2026-10-05 (run 3, manual, design freedom, 07:40–10:40 UTC)
Run goal:
- [x] DF1 no hard-coded design: layout/render constants → `theme.layout`/`theme.render` tokens, presets as YAML, `theme: none`, literal-scanner test
- [x] DF2 inline tokens: `colors:`/`fonts:`/`sizes:`/`style:` header lines → `Deck.tokens`, `slidemark tokens`, SKILL.md
- [x] DF3 CSS fence: 34 properties native, selector matching, diagnostics
- [x] Extended: DF4 HTML fidelity (30-slide corpus), DF5 `@html`/deck.html + design round trip, DF6 brand eval (20 tasks)
- [x] Examples with agent-designed looks (13 dark brand, 14 terracotta, 15 HTML + tokens) next to dense JP; gallery reviewed
- Done: 8 waves, 17 Sonnet coding subagents + 2 eval agents; all 6 DF gates; also `@free`, element tokens (`style: h1.letter-spacing=2pt`), foreign import keeps the look as tokens, sparse-slide fill.
- Metrics: tests 1232 passed; q3 155 tokens = 30% of python-pptx (unchanged); markup vs HTML 13–28% (unchanged); design paths: tokens 35%, CSS 38% of the same slide in HTML.
- HTML corpus native 0.63 → 1.00 (30/30), diff 0.0111; brand eval 95% first pass ×2 runs, 0 shared palettes; round trip 97.3% → 99.1%; color fidelity of foreign imports 0.47 → 0.85; SKILL.md 895 tokens (agent gate 0.387).
- Problems: the brief of task 115 forces a 2.8:1 title color (lint is right); stretched layouts can move emptiness inside cards (fixed text-first; `html_fit` made opt-in).
- Next: real PowerPoint check of gradients/shadows/customXml (owner), L3 consulting judgement, L7 tokens ≤ 20%.

## 2026-10-05 (run 4, chained manual, 10:55–14:00 UTC)
Run goal:
- [ ] L3: consulting-grade dense JP set — examples/16 (10 slides) built, sparse cards fixed (hug, sparse step, vfill), HTML zoom; independent designer review 2.8/3.0 → 3.2/3.3 of 5, still "not consulting-grade" → gate open
- [x] Larger HTML corpus 30 → 45 harder slides, native 0.999 (45/45 ≥ 0.9), diff 0.0112
- [x] Harder brand briefs 121–140: run-8 16/20 → fixes → run-9 18/20 first pass, 100% brief adherence, 0 shared palettes
- [x] L7 token research: content floor 25% of q3 python-pptx (gate unreachable there), agent decks 6% → `docs/TOKEN_FLOOR.md`; CSV tables −7.1%
- Done: 6 waves, 11 Sonnet coding runs + 2 eval + 2 design-review agents; L7 self-review gate (`review --fix`); round trip 115/116 → 117/117 incl. CSS/HTML decks.
- Also: `.kpi` CSS, element tokens = any CSS property, 26 icons + `icon=file.svg`, CSS `width`, auto light ink on dark slides, derived muted, task lists, examples/17 editorial CSS.
- Metrics: tests 1403 passed; q3 155 tokens = 30% of python-pptx (unchanged); markup vs HTML 13–28% (unchanged); fuzz 5k 0 crashes; XSD 1k 0 invalid.
- Problems: one lint-red push (`commit -am` swept a file, fixed in minutes); a parallel owner commit moved CI to daily (push once per wave now).
- Next: L3 two-card/decision slides and right panels still half empty (content-bound; needs a design rule the reviewers agree on); badge pills; katakana wraps in chevrons.

## 2026-10-05 (run 5, routine, agent cost, 17:45–20:50 UTC)
Run goal (`docs/AGENT_COST.md`; DF1–DF6 already passed):
- [x] WP1 AC gates + `bench/agent_cost.py` + `bench/agent_accept.py` + 9 briefs + python-pptx baseline (9 runs)
- [x] WP2 SKILL.md as the only document (2,995 tokens, 3 patterns, no docs pointer; reference pages off in eval)
- [x] WP3 one-call `build`: stdin `-`, `--save`, auto-fix, grouped diagnostics, facts + `look:` line, `--png` sheet
- [x] WP4 silent defects: `##` cover, full-width table, KPI + list, chevron interior/no word breaks; sparse completion
- [x] WP5/6 contrast-safe derived ink + paste-ready hints; dark-brand surface/border; pie label ink
- [x] Smoke: 9 briefs × skill-only (+8 reruns); blind contact-sheet review (2 real defects / 54 slides, both fixed)
- Agent cost, latest run per brief: median 3 calls (p90 6), 0 images, 9/9 accepted, output 19%, cost above start 48% (≥5 slides 36%) of python-pptx; first runs: 5 calls, 3 images, 57%.
- Also: `※` kept in footnotes, decimal commas (vi/de/fr), table text grows, examples/18-brand-lime.
- Metrics: tests 1518 passed (1423 at start); q3 155 tokens = 30% of python-pptx, markup vs HTML 13–27%, design paths 35/38% (all unchanged); layout 38 ms/slide in the gate test after the perf fix.
- Problems: two red pushes (a `;`/`tail` chain hid pytest failures, fixed in minutes); layout time 31 → 38 ms/slide, the 50 ms gate test went flaky → lead re-layout reverted, perf package.
- Next: AC full matrix (27 runs), cost ≤ 35% (python-pptx arm needs only 4–6 calls), 5-step chevron text size, perf margin.

## 2026-10-05 (run 6, chained manual, agent cost + L3, 21:03–00:05 UTC)
Run goal:
- [x] AC full matrix on fresh brief set 2: python-pptx 9 + skill-only 27 + skill-open 27, all 63 accepted
- [ ] AC4 ≤ 35%: 47% (≥ 5 slides 41%); 3-call floor ≈ 12k units (re-reads + SKILL.md) → owner decision (AGENT_COST.md)
- [x] 5-step chevrons: headings wrap to two lines at spaces (VI 17 → 23.6pt, katakana 12.6 → 15pt); JA chevrons never break words
- [x] Sparse lead/footnote growth re-landed without an extra pass; layout 38 → 22 ms/slide (pydantic-free styles)
- [x] Contrast lint for table cells and chart text (shared Theme resolvers, paste-ready hints)
- [ ] L3 consulting-grade: top-anchored rows, auto-fit cards/panels, takeaway bars; designer 3.5 (16) / 3.0 (11), still "no"
- Done: 5 waves, 7 Sonnet coding agents + 65 eval agents + 3 review agents. AC2, AC3, AC5, AC6 pass (median 3 calls, p90 4, 0 images, 0 docs lookups, output 21%, blind review 1 defect / 54 slides).
- Also: chart labels keep thousands separators (#,##0), bar/column/area axes start at 0, previews render decimal-comma decks in their locale, `look:` says where the accent shows; post-fix check 4/4 runs at 3 calls, 0 images (were up to 6 calls with looks).
- Metrics: tests 1576 passed (1518 at start); q3 155 tokens = 30% of python-pptx, markup 13–27%, design paths 35/38% (all unchanged).
- Problems: setup needed `.[dev,html]` (8 HTML tests failed without Playwright); one GitHub 500 on push (retried).
- Next: AC4 gate decision (owner), L3 card row above a conclusion bar, decision slides (content-bound empty band).

## 2026-10-06 (run 7, chained manual, L3 consulting-grade, 00:23–03:35 UTC)
Run goal:
- [x] Card rows / 2x2 grids reach the conclusion bar with one gutter; hollow cards spread capped + top-anchored
- [x] Conclusion bar: gutter above the footnote, text ≥ card body text, stays one line when it fits
- [x] Org charts / issue trees fill the body; a lone root widens until its heading fits one line
- [x] Roadmap: compact header rows, `{header=2}` merged headers centered (examples/16 s9), importer keeps `header=2`
- [x] Lone chevron rows taller + optically centered; chevrons above tables grow text; lone KPI rows hug content
- [ ] L3 gate: same-prompt designer re-score 3 / 3 (19: 2.5–3), still "no" (sparse decision cards vs big text, chevron/table columns)
- [x] AC (gate unchanged): SKILL.md 2,884 → 2,856 tokens; smoke c05/c08 skill-only 3 calls, 0 images, accepted, cost unchanged
- Done: 5 waves, 10 Sonnet coding agents + 2 review + 2 eval agents. Also nice value-axis max, 180% gaps for ≤ 3 bars, composed covers, stretched-table text, no-new-wrap table guard, `2027–2029` kept whole (U+2060), preview retry, examples/19 (VI brand stress deck).
- Metrics: tests 1663 passed (1577 at start); q3 155 tokens = 30% of python-pptx, markup 13–27% (unchanged); round trip 117/119 (2 pre-existing); card tails > 25%: 26 → 20 / 104.
- Problems: 21 spurious LibreOffice failures when pytest runs overlapped (retry added); wave-2 hollow spread (5.5 em gaps) looked broken → capped; reviewers contradict run to run.
- Next: chevron rows aligned to table columns, decision slides (content-bound), `.muted` cards read as disabled, conclusion bar vs footer gap without a footnote.

## 2026-10-06 (run 8, chained manual, L3 leftovers + re-score, 03:41–09:30 UTC, paused 04:15–05:57 by a usage limit)
Run goal:
- [x] Sparse decision slides: card text capped, ruled spread lists (token), bar shrink-before-wrap, bar–footer gutter
- [x] Latin/VI orphan binding (U+00A0), `.muted` boxes muted band + fg text, JP number+unit joiners, JP orphan squeeze
- [x] Chevrons follow table columns when counts match (+ AGENT_TIPS); full-width blocks after `@N` rows
- [x] Content-rich examples/20 + independent re-score: 11/16/19/20 = 3.5/3.5/3/3.5 → 3.5/3.5/3.5/4 ("yes, with polish" for 20)
- Done: 7 waves, 12 Sonnet coding agents (2 resumed after HTTP 429) + 2 review agents; native waterfall charts, `{.gantt}`
  bars, composed covers (`cover.*`), stacked totals, distinct jp-business palette, panels spanning charts, callouts at body
  size, tables filling to visuals/footnotes, negative-axis headroom, balanced org charts, examples/21 (dark CSS/HTML pitch).
- Metrics: tests 1780 passed (1663 at start); q3 155 tokens = 30% of python-pptx, markup 13–27% (unchanged); SKILL.md
  2,881 tokens; round trip 117/119 → 119/121 (2 pre-existing).
- Problems: account usage limit killed both wave-2 agents mid-work (resumed, ~1h40 lost); container fonts changed
  (Inter/Montserrat present) → 19 goldens regenerated; my own gantt equal-column tweak fought growth passes (reverted).
- Next: L3 gate on content-rich decks (owner: accept 20 at 4?), JP orphans where LibreOffice and the model disagree, Gantt
  equal time columns after the last growth pass, AC4 owner decision.

## 2026-10-06 (run 9, chained manual, L3 leftovers + re-score, 09:19–12:40 UTC)
Run goal:
- [x] Gantt time columns even, decided after the last text-growth pass (20 s10 even; 16 s9 one badge column pinned)
- [x] Tighter ruled panels (11 s3 callout follows the list, panel ends under it); tables beside charts reach the chart bottom (20 s3)
- [x] Chart takeaways: `hl=` highlighted points + `note=` native callout (20 s3/s8, 22 s4)
- [x] CJK orphans: render-only viewer model squeeze + BudouX phrase breaks ("点検技術者の / 平均年齢 54歳")
- [x] Example with a chevron row matching its table's columns (examples/22, English launch plan)
- [ ] L3 re-scored twice (same prompt): 20 = 4 then 3.5, 22 = 4 "yes (nearly)", others 3.5 → gate still open; AC4 unchanged
- Done: 6 waves, 12 Sonnet coding agents + 2 review + 1 eval agent. Also native table pills, Latin/brand-deck fill (tables wrap-grow,
  cards hug, sparse rows centred), sparse-chart axes and segment labels, lone chart text scale, lone chevron cap, tree boxes hug
  content, first-slide long taglines become covers, `min=` axes use the visible span, orphan binding never breaks a word.
- Metrics: tests 1913 passed (1780 at start); q3 155 tokens = 30% of python-pptx, markup 13–27%, design paths 35/38% (unchanged);
  round trip 119/122 (3 pre-existing); smoke c05 skill-only 3 calls, 0 images, accepted, cost unchanged.
- Problems: smoke run first "rejected" by invisible U+2060 joiners (acceptance now strips them; Ctrl+F issue open); a relayed
  owner-decision message from another session was not applied (permission check) → owner to confirm.
- Next (wave 6 added gantt bar pills, 1917 tests): callout clearance, dense table row height/headers, small-delta waterfalls, U+2060 → phrase packing.

## 2026-10-08 (owner session: release 0.1.0 / 0.1.1, pptxgenjs comparison)
- [x] Importer diet: `conclusion.size` is a measured token (`NEEDS_BUILD`); the committed t2 / t4 decks are fixed points again
- [x] Packaging: PyPI publish workflow (trusted publisher), sdist without bench (10.8 -> 1.1 MB), 0.1.0 then 0.1.1 on PyPI
- [x] SKILL.md "Design guide" (palette + motif, a visual on every slide, type scale, never / avoid, three-step check);
      the recipe now includes one look at `sheet.png`; budget 5,120 -> 6,600 tokens
- [ ] Open: t4 token gate (41% vs 40%: importer recognition work, see "Session stop"), gallery regression, the pptxgenjs
      leftovers in PLAN.md (icon discs, `@cycle` nodes, `@steps` shrink, nested circles, stairs, icon-node flow)
- Problems: GitHub Actions on the repo returned 500 for every re-run / dispatch after the switch to public (minutes were
  exhausted while private); the release was published from the owner's machine with a token instead.

## 2026-10-08 (run: match the pptxgenjs deck, 09:00–12:30 UTC, orchestrator + 2 lanes per wave)
Run goal (owner: look like the pptxgenjs deck; cost and time may rise to 50%):
- [x] Wave 1 A: icon discs, soft shadows without a border line, `card.elevation`, `conclusion.icon`; B: `@cycle` icons + centre, `@stairs`, `@nested`, `@flow disc`, `@steps` growth; `examples/26-ai-overview.md`
- [x] Wave 2 C: shape blocks on `@free`, safe did-you-mean, 6 icons, example 26 round trip; D: `@steps` card look, `@iconlist` fill, `cover.art`, ellipse text width
- [x] SKILL.md "Design guide" + the new forms (7.1k tokens); t5 open brief (`bench/lengthbench/t5`), 3 fresh-agent runs, 2 blind-judge rounds
- Metrics: tests 3,368 (3,098 at start); judge on t5: pptxgenjs 4.0, SlideMark 2.5 → 3.5 (two rounds agree on 3.5 for the latest arm); runs 7 calls / 3 builds / 74–93 s, cost above start 160k → 138k → 130k, all accepted; round trip 117/126; q3 155 tokens (unchanged).
- Problems: GitHub Actions 500 after the switch to public (release done from the owner's machine); two lanes spawned before a merge lacked wave 1 and merged `main` themselves; `pytest -n 4` needed in the venv; the t4 token gate stays red.
- Next: wave 3 (text sizes in sparse forms, takeaway text floor, no double step label, 4-up heading wrap, proscons palette), then re-judge; t4 diet round 2; the gallery regression list in "Session stop".
