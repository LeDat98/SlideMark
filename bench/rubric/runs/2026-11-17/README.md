# Rubric campaign 2026-11-17: example 27 after the dead-space fixes

Same protocol as `../2026-11-16` (Opus, blind, R = 3, shuffled slide order per run), example 27 only, built after
the G-05 soft gate and the `dead-space` fixes (slide 5: table + chart of its Change column + takeaway bar; slide 6:
four cards + the target table). Measured facts from `bench/rubric/measure.py` via `campaign.py`.

| slide | 2026-11-16 (re-scored, `../2026-11-17-rescore`) | 2026-11-17 | what changed |
|---|---|---|---|
| 5 table | 59 (raw 68; G-05 = 2 "small table floats") | **81** (Good; G-05 4, G-02 5) | table + chart + takeaway |
| 6 cards | 59 (raw 64; G-05 = 2 "dead bands above and below") | **67** (G-05 3-4) | cards + target table |
| 4 chart | 59 (G-06 = 2, 12 pt text) | 59 (G-05 = 2) | text now 14 pt; the judge now names the empty block under the Reading card |

Deck 64 (63-66), Acceptable; slide mean 66. New finding: on slide 4 all three runs saw a dead block of about 40%
of the body below the small `Reading` card beside the chart. It is a corner, not a full-width band, so the
empty-body measure (bands) reads 0%: the measure and the `dead-space` warning do not see a dead quadrant yet.
