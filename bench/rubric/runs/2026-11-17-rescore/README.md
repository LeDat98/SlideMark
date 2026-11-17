# Re-score 2026-11-17: the 2026-11-16 judge runs under the G-05 soft gate

No new judge calls: the run files are those of `../2026-11-16`. The measured files are the 2026-11-16 ones plus the
new empty-body fact (`bench/rubric/measure.py`, G-05 written only on a failure) read from builds of the same decks.
Rules changed: G-05 weight 4 -> 5 and `cap: 59` (level 2 caps the slide at 59, level 1 at 49; a measured failure
never raises the judge). A first cap of 69 changed nothing (the slides the judge saw as dead space were already 64-68
raw), so the cap is 59.

Result: example 27 slide 6 (four cards floating mid-slide) 67 -> 59 (G-05=2); slide 5 (lone table) stays 59 (it was
already capped by its 12 pt text, G-06). The venn slides of example 29 are judged 4 (side space around a figure that
fills the height is chosen space) and are no longer measured as dead space once side bands count half.
