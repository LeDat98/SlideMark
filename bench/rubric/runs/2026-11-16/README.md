# Rubric campaign 2026-11-16: after the fixes ranked by the 2026-11-15 campaign

Same protocol as `../2026-11-15` (Opus, blind, R = 3, shuffled, one run grades all five decks), on builds made after
fixes 1-8 (timeline time scale, card balance and arch growth, editorial label size and ink, chart series >= 3:1,
takeaway titles, cover metadata, example 27 text, pptx facts extractor). Measured facts (`measured-<deck>.json`) come
from `bench/rubric/measure.py`, run automatically by `campaign.py`.

Like-for-like comparison (the 2026-11-15 runs re-scored with the same extractor on their own .pptx builds):

| deck | before | after | slides before | slides after |
|---|---|---|---|---|
| t5 | 70 (66-75) | 69 (68-74) | 66 | 65 |
| 27-editorial | 58 (57-60) | 64 (61-67) | 62 | 64 |
| 28-swimlane-sequence | 60 (60-63) | 63 (62-68) | 66 | 71 |
| 29-arch-venn | 59 (55-59) | 66 (58-70) | 65 | 75 |
| 30-html-diagrams | 56 (56-57) | 65 (63-70) | 60 | 72 |

Targeted KPIs, mean level over all 35 slides: G-01 message 3.46 -> 3.83, G-09 contrast 3.20 -> 3.80, G-05 space
3.29 -> 3.46, G-06 type 3.34 -> 3.46; T-TIME-01 on t5 slide 4: 2 -> 5 (gate passes). The t5 deck text is the
agent's and unchanged, so its score moves only with the product fixes; its remaining cap is the agent's pale accent
dot on the timeline (2.5:1, measured). Remaining caps on example 27 slides 4 / 5: table and card text 12-13 pt
measured against the 14 pt body floor (the editorial type scale vs the rubric floor: owner decision).
