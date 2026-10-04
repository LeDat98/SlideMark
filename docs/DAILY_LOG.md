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
