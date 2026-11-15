# Rubric campaign 2026-11-15 (first use of the rubric)

Judge: Opus, blind (images only, 1280 x 720 renders of the current build), R = 3 independent runs, shuffled slide
order per run, one run grades all five decks. Decks: `t5` (the wave-3 fresh-agent deck of lengthbench-t5, default
look, rebuilt with today's code) and the editorial examples 27-30 (feature showcases, not storylines: read their slide
scores, their deck KPIs D-01 / D-04 are low by nature). Step 2 of the protocol (brief check) was not run; step 3
(measured facts) only for G-06 on 29 slides 3-4 (`measured-29-arch-venn.json`: smallest text 8 pt = the label floor,
the judge had estimated 7-8 pt from the image).

Files: `run<N>-<deck>.json` (judge output), `<deck>.md` (report per deck), `SUMMARY.md` (cross-deck summary),
regenerate with `python bench/rubric/campaign.py bench/rubric/runs/2026-11-15`.
