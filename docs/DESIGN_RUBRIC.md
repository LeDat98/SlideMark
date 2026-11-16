# SlideMark design rubric: method, formula and protocol

Owner request (2026-11-15): a KPI rubric with a clear description for every level 1 to 5, general KPIs for every slide,
specialised KPIs per slide topic, both directions (good and bad signs), weights, mandatory criteria, a scoring formula,
a report and a methodology. Built by two research agents (topics and topic KPIs; general KPIs and method) from published
design guidance, then merged here.

## 0. Why a new rubric

The earlier judging prompts (`bench/design_review_prompt.md`, `bench/ui_review_prompt.md`) score 1-5 with no
description per level: only "5 = a strong designer would ship it unchanged" and "3 = competent but undesigned" for the
overall score. They have no weights and no mandatory criteria, so a fatal flaw (text cut off) can hide in a good
average, and the same deck scored 3.0 and 3.5 in two rounds (judge noise about +-0.5).

## Files

| File | What it holds |
|---|---|
| `bench/rubric/general.yaml` | 14 general KPIs (every slide) and 5 deck KPIs, each with question, gate, weight, good / bad signals, levels 1-5, checks, sources |
| `bench/rubric/topics.yaml` | 12 topics: how to recognise a slide of the topic, how often it appears, and 4-6 specialised KPIs each |
| `docs/DESIGN_RUBRIC_KPIS.md` | the readable catalogue, generated from the YAML (`python bench/rubric/render.py`) |
| `bench/rubric/score.py` | judge runs (JSON) -> slide and deck scores, caps, bands, ranges and the Markdown report |
| `bench/rubric/judge_prompt.md` | the judge prompt (step 1, blind) and the JSON it must return |

## Topics

A slide is scored with the general set plus the KPIs of its topic. `dense-ja-business` is an overlay: a dense
Japanese business slide is scored with its primary topic plus the overlay (`"topic": "data-table+dense-ja-business"`).

| id | name | KPIs | gates | note |
|---|---|---|---|---|
| `data-chart` | Data chart | 6 | 2 |
| `data-table` | Data table | 5 | 1 |
| `key-numbers` | KPI cards / key numbers | 5 | 1 |
| `process-flow` | Process, flow and steps | 5 | 1 |
| `system-diagram` | System, architecture and concept diagram | 5 | 2 |
| `comparison` | Comparison and options | 5 | 1 |
| `timeline-roadmap` | Timeline and roadmap | 5 | 2 |
| `hierarchy-org` | Hierarchy, org chart and tree | 5 | 1 |
| `framing` | Framing slides (cover, agenda, section, closing, decision) | 4 | 0 |
| `text-message` | Text argument / message slide | 5 | 0 |
| `matrix-quadrant` | Matrix, quadrant and prioritisation | 4 | 2 |
| `dense-ja-business` | Dense Japanese business slide (overlay) | 6 | 2 | overlay: scored on top of the primary topic

## 1. Why this design (short)

- **Analytic rubric with anchored levels.** Each KPI has five levels written as observable signs on the image
  (behaviourally anchored in the sense of Smith and Kendall's retranslation idea: anchors are behaviours or signs, not
  adjectives). The existing prompts give a number with no description per level, which is why two rounds of the same
  deck gave 3.0 and 3.5.
- **Gates for "wrong or unusable", weights for "better or worse".** A slide with cut-off content or unreadable text
  is not rescued by a nice palette. A weighted mean alone lets a high score on many KPIs hide one fatal flaw.
- **Evidence before score.** The judge writes what it sees, with a sign (+ or -), then the level. This is the
  form-filling and reasoning-first structure of G-Eval, and rubric-conditioned judging as in Prometheus.
- **Repeat and aggregate.** LLM judges are not stable run to run, so the protocol takes the median of several runs and
  reports the spread.

## 2. Definitions

| Symbol | Meaning |
|---|---|
| s | KPI score in one run, integer 1..5 (level number) |
| s_med | median of s over the R runs (R = 3 default), may be x.5 only if R is even |
| n | normalised score, n = (s_med - 1) / 4, so 1 -> 0, 3 -> 0.5, 5 -> 1 |
| w | weight 1..5 (from the yaml) |
| gate | true/false flag (from the yaml) |
| N/A | KPI cannot be judged (for example G-14 from an image only, or a topic KPI that does not apply). It is removed from both sums, so the remaining weights are renormalised. A gate KPI may not be N/A. |

## 3. Slide score

### 3.1 Set score (general set G, topic set T)

S_set = sum(w_i * n_i) / sum(w_i), over applicable KPIs in the set. Range 0..1.

### 3.2 Combine the two sets

Slide_raw = 100 * ( a * S_G + (1 - a) * S_T ), with **a = 0.6**.

Why 0.6 / 0.4:
- The general set has 14 KPIs and carries the readability and polish gates that every slide must pass; the topic set
  has fewer KPIs (about 5 to 8) and each one is noisier, so it should not outweigh the broad set.
- The topic set carries "is this the right content for this form" (the owner's "dung noi dung"), so it must not be a
  minor part either. 40% makes a slide with a perfect general score but a poor topic score (for example a beautiful
  chart that shows no takeaway) lose up to 40 points.
- G-02 (form fits content) overlaps with topic KPIs. The topic author must not repeat G-02; the topic set refines it.
- This is a starting value, not a measured one. Re-fit a by comparing against human ranks of about 20 slides (the
  existing 20 slides in `bench/ui_review.jsonl` can serve) and keep a at 0.5..0.7.

If a slide has no topic set (unclassifiable), use Slide_raw = 100 * S_G and add the flag `no-topic`.

### 3.3 Gates and caps

A gate KPI is any KPI with gate=true, in either set. Let g_min be the lowest s_med over the gate KPIs of the slide.

| g_min | Rule | Meaning |
|---|---|---|
| 3 or more | no cap | gates pass |
| 2 | Slide = min(Slide_raw, **59**) | weak but usable; cannot reach Good |
| 1 | Slide = min(Slide_raw, **39**) | wrong, misleading or unusable; always Fail |

Gate stability rule (to stop one noisy run from failing a good slide): a gate counts as failed only if the median over
runs is below 3 AND, where the KPI has a measurable check (font size, contrast ratio, bounds), the measurement agrees.
If the judge says 1 for text size but the pptx says 10.5 pt in a dense JA slide, the measurement wins and the KPI is
re-scored from the measurement. A gate with a disagreement between runs of 2 levels or more is flagged `gate-unstable`
and needs a human look; it is capped as if failed until it is resolved.

Each cap and its trigger is printed in the report, so a capped slide always has a visible reason.

### 3.4 Score bands

The 0-100 scale is linear in the 1..5 scale: 3.0 -> 50, 4.0 -> 75, 5.0 -> 100.

| Band | Slide / deck score | Average level | Reading |
|---|---|---|---|
| Excellent | 85 - 100 | 4.4 and above | a strong designer would ship it unchanged |
| Good | 70 - 84 | 3.8 - 4.4 | ship after small fixes |
| Acceptable | 50 - 69 | 3.0 - 3.8 | competent but undesigned or one real weakness |
| Fail | 0 - 49 | below 3.0 | do not ship; rebuild the weak parts |

"Acceptable" starts at all-3s, which matches the existing prompt's definition of 3 ("competent but undesigned").
Because of the gate caps, a gate failure at level 2 lands in Acceptable (top 59) and at level 1 in Fail.

## 4. Deck score

1. **Slide aggregate.** With P_k the slide scores (after caps):
   Deck_slides = 0.75 * mean(P_k) + 0.25 * mean of the lowest ceil(K/4) slides (bottom quartile, at least one slide).
   The bottom-quartile term stops a deck from hiding weak slides in a good average.
2. **Deck KPIs.** D = 100 * sum(w * n) / sum(w) over the deck KPIs D-01..D-05 (same n and N/A rules).
3. **Final.** Deck = 0.7 * Deck_slides + 0.3 * D.
4. **Deck caps.**
   - Any slide with a gate at level 1 or 2: the deck is capped at 84 (cannot be Excellent).
   - 20% or more of the slides have a gate at level 1: the deck is capped at 49 (Fail).
   - 40% or more of the slides are in the Fail band for any reason: the deck is capped at 59.

Why 0.7 / 0.3: a deck is mostly its slides, but narrative, consistency and pacing decide whether the slides are a deck
at all; 30% lets a deck with fine slides but no story or system fall by up to about 30 points.

Deck KPIs are judged once per deck (from the title list and the contact sheet or all slides), with the same R runs.

## 5. Worked example 1: one chart slide

General set (14 KPIs, G-14 is N/A because only an image was given, so sum of weights = 55 - 2 = 53).

| KPI | w | s_med | n | w*n |
|---|---|---|---|---|
| G-01 message (gate) | 5 | 4 | 0.75 | 3.75 |
| G-02 form | 4 | 4 | 0.75 | 3.00 |
| G-03 hierarchy | 5 | 3 | 0.50 | 2.50 |
| G-04 grid | 4 | 4 | 0.75 | 3.00 |
| G-05 space | 4 | 3 | 0.50 | 2.00 |
| G-06 type (gate) | 5 | 4 | 0.75 | 3.75 |
| G-07 text economy | 3 | 4 | 0.75 | 2.25 |
| G-08 colour | 3 | 3 | 0.50 | 1.50 |
| G-09 contrast (gate) | 5 | 5 | 1.00 | 5.00 |
| G-10 emphasis | 3 | 3 | 0.50 | 1.50 |
| G-11 glance | 4 | 3 | 0.50 | 2.00 |
| G-12 fidelity (gate) | 5 | 4 | 0.75 | 3.75 |
| G-13 deliberate | 3 | 4 | 0.75 | 2.25 |
| total | 53 | | | 36.25 |

S_G = 36.25 / 53 = 0.684.

Topic set `data-chart` (illustrative KPIs and weights; the real ones are in `topics.yaml`):

| KPI | w | s_med | n | w*n |
|---|---|---|---|---|
| T1 chart type right | 5 | 4 | 0.75 | 3.75 |
| T2 takeaway annotated | 5 | 2 | 0.25 | 1.25 |
| T3 direct labels, no legend lookup | 4 | 4 | 0.75 | 3.00 |
| T4 no chartjunk | 3 | 3 | 0.50 | 1.50 |
| T5 honest scale (gate) | 5 | 5 | 1.00 | 5.00 |
| T6 colour encodes series | 3 | 4 | 0.75 | 2.25 |
| total | 25 | | | 16.75 |

S_T = 16.75 / 25 = 0.670.

Slide_raw = 100 * (0.6 * 0.684 + 0.4 * 0.670) = 100 * (0.4104 + 0.268) = **67.8**. Gates (G-01, G-06, G-09, G-12, T5)
all at 4, 4, 5, 4, 5, so g_min = 4 and no cap. Band: **Acceptable**. The report's top fix comes from the largest
weighted loss: T2 (loss 5 * 0.75 = 3.75 weight points), then G-03 (2.5), G-05 and G-11 (2.0 each).

Same slide, but the judge median for G-06 is 2 (body text on the edge of the floor, sizes inconsistent): g_min = 2, so
Slide = min(67.8, 59) = **59**, still Acceptable but cannot reach Good. With G-06 = 1 (body at 9 pt on a presented
slide), Slide = min(raw, 39) = **39** (raw would be about 64 after the G-06 drop), Fail, because the cap applies whatever the raw score is.

## 6. Worked example 2: a 10-slide deck

Slide scores after caps: 72, 68, 39 (gate 1 on slide 3), 81, 74, 66, 78, 70, 85, 63.
- mean = 696 / 10 = 69.6
- bottom quartile = lowest ceil(10/4) = 3 slides: 39, 63, 66 -> mean 56.0
- Deck_slides = 0.75 * 69.6 + 0.25 * 56.0 = 52.2 + 14.0 = 66.2

Deck KPIs: D-01 s=4 (w5), D-02 s=3 (w4), D-03 s=3 (w3), D-04 s=2 (w3), D-05 s=4 (w3).
w*n = 5*0.75 + 4*0.5 + 3*0.5 + 3*0.25 + 3*0.75 = 3.75 + 2.0 + 1.5 + 0.75 + 2.25 = 10.25; sum of weights 18;
D = 100 * 10.25 / 18 = 56.9.

Deck = 0.7 * 66.2 + 0.3 * 56.9 = 46.34 + 17.08 = **63.4**.
Caps: one slide in 10 (10%) has a gate at level 1, so only the "cannot be Excellent" cap (84) applies, which is not
binding. Band: **Acceptable**. Top fixes: slide 3 (gate), then D-04 (no agenda or dividers in a long deck), then the
weakest recurring slide types.

## 7. Uncertainty

The known noise is about +-0.5 on the 1-5 overall from the owner's rounds (the same deck scored 3.0 and 3.5). That is
+-12.5 points on the 0-100 scale for a single-run overall. Aggregating 14 KPIs with medians over three runs shrinks it
but errors in one judge are correlated, so do not assume it falls by 1/sqrt(N). Rules:

1. **Always report a range**: score = median over runs, with (min - max) over runs. Example: "Deck 63 (58-66, R=3)".
2. **Measure the noise once**: run one fixed deck at least 5 times with the final prompt and record the standard
   deviation SD_slide (per slide) and SD_deck. Until measured, assume SD_deck = 4 points and SD_slide = 6 points
   (an assumption derived from the +-0.5 observation; label it "assumed").
3. **Comparing two decks or two versions**: call the difference real only if |difference| > 2 * sqrt(SD_a^2 + SD_b^2)
   (about 11 points with the assumed SD_deck = 4), and the ranges do not overlap. Otherwise report "tie within noise".
   A paired design (same brief, same slides re-judged in random order) cuts the noise: judge both versions in the same
   run, shuffled, and compare per KPI.
4. **Band edge**: if the range crosses a band boundary, print the band as "Acceptable / Good (borderline)".
5. **KPI-level flag**: if s differs by 2 or more levels between runs for a KPI, mark it `unstable`, take the median,
   and request two more runs of that KPI only (cheap: one short prompt with the slide and that KPI).
6. **Never** quote one decimal place beyond the range's resolution: round slide and deck scores to whole points.

## 8. Report template

```
# Design report: <deck name>  (rubric vX, judge <model>, R=3 runs, date)

## Summary
Deck 63 (58-66)  Acceptable        Slides 66 (bottom quartile 56)   Deck KPIs 57
Gates: 1 slide capped (slide 3, G-12 = 1: text cut off). Unstable KPIs: G-03 (slide 5), D-04.

## Deck KPIs
| id | name | w | s (runs) | evidence (+/-) |
| D-01 | Narrative | 5 | 4 (4,4,3) | + titles 4,6,7 are claims; - slide 9 title 'Summary' |

## Slides
| # | topic | general | topic | raw | cap | score | band | weakest KPIs (loss) |
| 1 | cover | 74 | 71 | 73 | - | 73 | Good | G-05 |
| 3 | table | 61 | 55 | 58 | G-12=1 -> 39 | 39 | Fail | G-12, G-06 |

## Top fixes (ordered by weighted loss, then by gate)
1. Slide 3 (G-12, gate): the third column overflows its card and is cut at the right edge. Fix: reduce text, widen card.
2. ...
(maximum 5 fixes; each names slide, KPI, observed sign, and one action)

## Evidence lines (full)
S3 | G-12 | s=1 (1,1,2) | - | right column text cut at "Q4 forec" in the third card | fix: widen or wrap
S3 | G-06 | s=3 | - | footnote ~8 pt but readable | +- | body 12 pt
S5 | G-03 | s=4 (4,3,5) unstable | + | the 38% figure is the largest object, top left
```

Each evidence line is: slide | KPI | final s (run values) | sign | what is seen, with where | optional fix.
No score may be printed without at least one evidence line. A score of 4 or 5 needs a "+" sign; a score of 1 or 2 needs
a "-" sign; a 3 needs one of each or a reason for neutrality.

Also print the measured facts used (min font size in pt, min contrast ratios, longest run of one layout) so a reader can
check the gates without opening the deck.

## 9. Judging protocol

**Inputs.** Rendered PNGs at full size (1920 x 1080 or higher), one per slide, rendered with the repo font config so
the rendering is the same everywhere. Contact sheets are good for deck-level KPIs and for ranking, but too small for
G-06, G-09 and G-12; give full-size images for the slide KPIs and add a zoomed crop for dense areas. The brief (intended
message and purpose of each slide, and the intended use of the deck) is given only in step 2.

**Step 1 - blind pass (images only).**
- The judge is told nothing about the tool, the generator or any other version, and sees only the image(s).
- It first writes, per slide: the topic type (from the topic list), a one-sentence message as a viewer would state it
  after a three-second look, and the content type.
- Then, for every applicable KPI in the general set and the topic set: evidence line (what is seen, where, + or -),
  then the level. The level must match the level text in the yaml; the judge quotes the level number only.
- It marks N/A where the image cannot show the thing (accessibility structure).

**Step 2 - brief check (separate call).** Give the intended message and the content brief. The judge re-scores only
G-01 (message matches intent, nothing missing from the brief, nothing contradicts the data) and the topic KPIs that
depend on the content. This keeps the aesthetic scoring blind and still checks "right for its content".

**Step 3 - measured facts.** Tooling, not the judge, extracts from the pptx: minimum and body font sizes per slide,
contrast ratios, shape bounds versus slide and card bounds, overlap list, alt text, title and reading order. These
override the judge for the gates (section 3.3) and supply G-14.

`bench/rubric/measure.py deck.pptx --deck <id> [--dense-ja] -o measured-<id>.json` is that tooling. Per slide it reads
the smallest text size per role (body, node, label, footnote, chart), the contrast of every run against the fill behind
it, the non-text contrast of chart series, arrows and legend swatches (>= 3:1), text that overflows its frame,
shapes past the slide edge and overlapping text shapes, and writes `{"slides": {"3": {"G-06": 2}}, "facts": {"3":
"min body 12 pt (floor 14); ..."}}`. Floors are those of the KPI checks (body 14 pt, dense JA 10 pt, labels,
footnotes and chart text 8 pt); a clear failure is level 1, a borderline one level 2, a pass level 3. G-12 is written
only for a measured defect. `score.py` applies a measured failure over the judge, and lets a measured pass lift only a
judge level below 3. `campaign.py` runs the extractor itself when `<deck>.pptx` sits in the campaign folder and no
`measured-<deck>.json` exists.

**Step 4 - repeat.** R = 3 independent runs with fresh context. Shuffle the slide order and the KPI order in each run to
reduce position and order bias, and never show two versions in the same image unlabeled in a fixed order. Use a
judge model that is not the model that generated the deck when possible (self-enhancement bias). Take the median per KPI;
flag unstable KPIs and re-run only those twice more.

**Step 5 - calibration rule.** Keep an anchor set of at least 12 frozen slides with human consensus scores (at least two
per gate KPI at levels 1, 2 and 3 and a few at 5; include dense JA business slides). Before each campaign, or after any
change of judge model or prompt, the judge scores the anchor set. Accept the setup only if (a) mean absolute error
against the human scores is 0.4 level or lower, (b) no gate disagrees with the human by two levels, and (c) the
standard deviation across R runs on the anchors is at most 0.4 level. If not, fix the level wording or add anchors,
and do not compare numbers across setups. Store the SD in `bench` next to the scores so the uncertainty rule in
section 7 uses the measured value.

**Output format.** One JSON object per slide with `slide`, `topic`, `message`, `kpis: [{id, na, evidence: [{sign, text}],
level}]`, then the report is computed by script from these objects, never by the judge. This keeps the arithmetic
exact and cheaper than prose.

**Cost note.** One call per deck for all slides (JSON out) times R = 3 is the baseline; step 2 and the re-runs add a
small number of short calls. Do not spend more calls to get a decimal of precision that the noise does not allow.

## 10. Known limits

- 14 general KPIs and about 6 topic KPIs per slide is a long form; the judge may skim. Mitigation: the JSON form per
  KPI with required evidence, and a deck of at most about 20 slides per call.
- LLM judges prefer text-heavy or LLM-looking output and are inconsistent run to run; the score is a design signal, not
  a verdict. Human review of gates and the top fixes remains.
- The numeric thresholds marked "heuristic" or "SlideMark heuristic" in the yaml are working values from the owner's
  context, not figures from the cited sources.
- Weights, the 0.6/0.4 split, the 0.75/0.25 deck mix and the caps are proposals to be tuned on the anchor set.

## 11. Sources and verification status

Verified this session (page fetched or found by search):
- WCAG 2.2 SC 1.4.3 Contrast (Minimum): 4.5:1 normal text, 3:1 large text (18 pt, or 14 pt bold), CJK equivalent sizes
  apply. https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html
- WCAG 2.2 SC 1.4.11 Non-text Contrast: 3:1 for graphical objects and UI components needed to understand content.
  https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html
- Microsoft, Make your PowerPoint presentations accessible: alt text, reading order, unique slide titles, contrast and
  colour, readable fonts (it suggests 18 pt or larger), simple tables, descriptive links.
  https://support.microsoft.com/en-us/office/make-your-powerpoint-presentations-accessible-to-people-with-disabilities-6f7772b2-2f33-4bd2-8ca7-dae3b2b3ef25
- Zheng et al., Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena (NeurIPS 2023 Datasets and Benchmarks):
  position, verbosity and self-enhancement bias; strong judges reach over 80% agreement with human preference.
  https://arxiv.org/abs/2306.05685
- Liu et al., G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment (2023): chain-of-thought and form-filling;
  Spearman 0.514 with humans on summarisation; notes bias toward LLM-generated text. https://arxiv.org/abs/2303.16634
- Kim et al., Prometheus: Inducing Fine-grained Evaluation Capability in Language Models (ICLR 2024): evaluation with a
  user-supplied score rubric and reference answer. https://arxiv.org/abs/2310.08491
- Haldar and Hockenmaier, Rating Roulette: Self-Inconsistency in LLM-As-A-Judge Frameworks (Findings of EMNLP 2025):
  low intra-rater reliability across runs. https://aclanthology.org/2025.findings-emnlp.1361 (found via search; abstract
  level only)
- Smith and Kendall, Retranslation of expectations (Journal of Applied Psychology 47(2), 1963, 149-155, DOI
  10.1037/h0047060): origin of behaviourally anchored scales (citation confirmed through search results; paper text not read).
- Duarte, The Glance Test: main point in 3 seconds or less; signal-to-noise per slide.
  https://www.duarte.com/resources/guides-tools/the-glance-test/ and https://www.duarte.com/resources/slide-glance-test/
  (search-result summaries; the scoring sheet itself was not read)
- Knaflic, Storytelling with Data: chapter list (declutter, focus attention, action titles) via the O'Reilly
  tables of contents and secondary summaries, https://oreilly.com/library/view/storytelling-with-data/9781119002253
  (paraphrase only; the book was not read)
- Minto, The Pyramid Principle (1st ed. 1987): governing thought, MECE grouping, action titles; only via secondary
  summaries (e.g. https://www.think-cell.com/en/resources/content-hub/using-the-pyramid-principle-to-build-better-powerpoint-presentations).
  Sources disagree on the origin dates and the MECE attribution; the primary book was not checked.
- Müller-Brockmann, Grid Systems in Graphic Design (Niggli, 1981): publication existence confirmed by publisher listings
  only (https://www.slanted.de/?p=792761).

Not verified (known works, claims paraphrased from general knowledge, no search hit or not read):
- Williams, The Non-Designer's Design Book (contrast, repetition, alignment, proximity): the search returned nothing for it.
- Reynolds, Presentation Zen; Duarte, slide:ology and Resonate (book contents); Tufte, The Visual Display of Quantitative
  Information and Envisioning Information; Lupton, Thinking with Type.
- Consulting practice (McKinsey, BCG) and Japanese 資料作成 guides: no specific title was identified, so no citation is given.
- WCAG 1.4.1 (use of colour): referenced by name only; page not fetched.
- Quantitative thresholds marked "heuristic" in `general.yaml` (margins, word counts, hue counts, run lengths, 25% emphasis
  share) are working values, not published figures. The 10 pt floor for dense JA business slides and the 8 pt footnote
  floor come from the SlideMark owner's targets, not from a source.
- The assumed noise values SD_deck = 4 and SD_slide = 6 points are assumptions derived from the +-0.5 observation in
  `bench/design_review.jsonl`, to be replaced by a measured value.
