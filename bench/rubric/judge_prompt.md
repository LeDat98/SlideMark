# Judge prompt: design rubric, step 1 (blind)

Reuse verbatim so scores stay comparable. Fill `{RUBRIC}` with the contents of `bench/rubric/general.yaml` and
`bench/rubric/topics.yaml`, `{SLIDES}` with the image paths (full-size renders, one per slide, in a shuffled order
for each run), `{DECK}` with a short neutral deck label. The judge returns JSON only; `bench/rubric/score.py`
computes every number. Run it R = 3 times in fresh contexts (method: `docs/DESIGN_RUBRIC.md`, section 9). Step 2
(brief check of G-01 and content-dependent topic KPIs) and step 3 (measured facts) are separate.

---

You are a senior presentation designer grading slides with a fixed rubric. You do not know how the slides were made
and must not guess. Judge only what you can see in each image.

The rubric (YAML) follows. Each KPI has a question, levels 1 to 5 that describe what you see at each level (1-2 bad
signs, 3 acceptable, 4-5 good signs), good and bad signals, and checks.

{RUBRIC}

Slides (read every image with the Read tool, in this order): {SLIDES}

For each slide:
1. Decide its topic: one id from `topics` (the communication job of the slide). Add `+dense-ja-business` when the
   slide is a dense Japanese business slide (many boxes, 10-12 pt Japanese text, tables, footnotes).
2. Write the message a viewer would state after a three-second look, in one sentence.
3. For every KPI in `general` and in the slide's topic(s): first the evidence (what you see and where, each line with
   a sign: `+` a good signal, `-` a bad signal), then the level whose description matches best. A level of 4 or 5
   needs at least one `+` line, a level of 1 or 2 at least one `-` line, a 3 one of each or a reason. Use `"na": true`
   only for things an image cannot show (G-14 accessible structure). Never leave a KPI out.
Then score the deck KPIs (`deck`) once for the whole set of slides, in the same way.

Return only this JSON (no prose before or after):

```json
{"deck": "{DECK}", "judge": "<your model name>", "date": "<yyyy-mm-dd>",
 "slides": [
  {"slide": 1, "topic": "data-chart", "message": "...",
   "kpis": [
    {"id": "G-01", "level": 4, "evidence": [{"sign": "+", "text": "title states the takeaway; the bar for Q3 proves it"}]},
    {"id": "G-14", "na": true, "evidence": []}
   ]}
 ],
 "deck_kpis": [{"id": "D-01", "level": 3, "evidence": [{"sign": "-", "text": "titles 2, 5 are topic labels"}]}]}
```
