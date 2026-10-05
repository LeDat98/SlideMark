# Agent cost: what SlideMark must optimize (owner review, 2026-10-06)

Direction set by the owner on 2026-10-06 after an A/B pilot with real agents. Read it before picking work.
It changes what "token cost" means in this repo. Design freedom (`docs/DESIGN_FREEDOM.md`) still applies:
nothing below may hard-code a look.

## Verdict

SlideMark promises that an agent makes a deck for about 30% of what it costs with python-pptx. The pilot found:

- the **source file** is 10–19% of the python-pptx script (the promise holds for the file), but
- the **whole agent run** cost 112% of the python-pptx run (58–177% per brief).

The file is small and the run is not cheaper. Cost follows the number of model calls, because every call
re-reads the whole context, and the SlideMark agent made more calls: it fetched reference pages, ran `check`,
`build` and a render as separate steps, and looped on a warning it could not clear in one edit.

**From now on the product metric is the cost of the agent run that ends with an accepted deck. The first lever
is the number of model calls, the second is output tokens (thinking included), the third is input tokens.**
Source-size ratios stay as a regression guard and are no longer reported as "agent cost".

## Owner requirements

1. **Fewer model calls.** Target path: 3 calls (read brief + SKILL.md, write + build, report).
2. **No docs reading.** A normal deck must never need `slidemark docs` or a reference page. Everything an agent
   needs is in SKILL.md.
3. **Tests with dedicated subagents** that may read SKILL.md and nothing else, scored on model calls and run
   cost against a python-pptx agent on the same briefs.
4. **Reach the 30% for real** on that test (defined under "Metric and gates").

## Evidence

### Pilot (2026-10-06, SlideMark 73b25cc)

Three new briefs with the content given word for word, the same acceptance requirements, two arms. Each run was
a fresh Sonnet 5 subagent in Claude Code that did not know another arm existed. The SlideMark arm was told to
read SKILL.md first; `slidemark docs` was available. The python-pptx arm had a venv with python-pptx only. Both
could render PNGs with the same tool. One run per cell, so the numbers show direction, not a final ratio.

| Brief | Model calls SM / pptx | Source, o200k tokens SM / pptx | Output tokens SM / pptx | Run cost SM vs pptx: all-in, above common start |
|---|---|---|---|---|
| T1: 3 slides, EN, default look | 11 / 8 | 278 / 2,893 (10%) | 4.1k / 7.1k (57%) | 108%, 113% |
| T2: 5 slides, JA dense | 10 / 19 | 826 / 5,762 (14%) | 4.9k / 16.3k (30%) | 58%, 46% |
| T3: 10 slides, VI, brand colours | 29 / 13 | 1,343 / 7,119 (19%) | 22.2k / 16.0k (139%) | 177%, 203% |
| All | 50 / 40 | 2,447 / 15,774 (16%) | 31.2k / 39.4k (79%) | 112%, 117% |

Output tokens are Claude tokens including thinking, reconstructed from context growth (Appendix B). All six
decks contained every required string (30/30, 68/68, 136/136) with native charts and tables.

### Where the SlideMark runs spent their calls

| Step | T1 | T2 | T3 |
|---|---|---|---|
| Read brief, SKILL.md, list folder | 1 | 1 | 2 |
| `slidemark docs` (pages fetched) | 2 (4) | 2 (5) | 2 (6) |
| Write deck.md | 1 | 1 | 1 |
| Check, build, render (and list the output) | 3 | 3 | 3 |
| Fix loop: contrast warning | 0 | 0 | 5 |
| Look at slide images (images) | 1 (3) | 1 (5) | 2 (8) |
| Fix loop: 5-step chevron text (2 `slidemark tokens`, 3 edits, 2 rebuilds, 3 looks) | 0 | 0 | 10 |
| Re-open the .pptx with own python-pptx script | 1 | 0 | 2 |
| Hand back, final message | 2 | 2 | 2 |
| Total | 11 | 10 | 29 |

- **Docs.** Every run made 4–6 reference page fetches before writing a line: `charts-tables`, `design`, `syntax`,
  `components` in all three, plus `jp-dense` (T2) and `diagnostics` (T3). SKILL.md line 14 ("More: `slidemark
  docs …`") reads as an instruction to do so.
- **Three commands.** SKILL.md lists `check`, `review`, `build`, so agents run them one call at a time. `build`
  already prints the diagnostics.
- **Contrast loop (T3).** `check` printed four identical lines "low contrast 2.9:1 -> use a darker text color or
  a lighter fill (need >= 3:1)" for the brand accent on KPI values. The first edit did not clear it, the agent
  wrote its own contrast calculator, then edited again: 5 calls. The hint names no token and no passing colour.
- **Thinking.** Before writing the 10-slide deck the SlideMark agent spent about 8k thinking tokens and then
  wrote a 2.2k-token deck. The python-pptx agent wrote 12k tokens of code with no thinking. Unfamiliar syntax
  and open design decisions are paid for in thinking tokens, at output price.
- **Distrust.** In 2 of 3 runs the agent re-opened the .pptx with its own script to confirm slide size, chart
  type and notes. `build` prints only "wrote deck.pptx (N slides)".

The cheapest python-pptx run (T1, 8 calls) was: read, list, write script, run, render, look, hand back, final.

### Why calls dominate

Measured in Claude Code with prompt caching. Price weights are Claude list-price ratios: fresh input 1, cache
write 1.25, cache read 0.10, output 5 (units = fresh-input-token equivalents).

- Context at the first call is about 60k tokens (system prompt and tools) and grows to 80–117k.
- **One extra model call costs 6–12k units even if it does nothing**: the price of 1,200–2,300 output tokens,
  more than the whole source of the 10-slide SlideMark deck (about 2,050 Claude tokens).
- **Text in SKILL.md is cheap by comparison.** 1,000 more o200k tokens there cost about 1,800 units once and
  145 per later call. One reference lookup costs at least 6,500 units of re-reading plus the page. SKILL.md
  could carry all eight reference pages (4,520 tokens) for less than the two lookup calls agents make today.
- **Images.** A 1280×720 PNG is 1,229 tokens (width × height / 750). Looking at 10 slides adds about 12k
  tokens and 2–3 calls.
- **Tokenizer.** Claude counts about 1.53× `o200k_base` for model-written text and 1.45× for tool results (fit
  on 42 calls, R² > 0.999). Every number in `bench/` is the o200k proxy: ratios hold, absolute costs are about
  one third too low. `tokens_claude` is null in all 53 rows of `bench/history.jsonl`.
- Without prompt caching each call re-reads at weight 1 instead of 0.10, so calls matter ten times more.

### Defects that passed `check` with no warning

Agents look at images because zero warnings does not yet mean a clean deck. Seen in the rendered pilot decks:

1. **Cover with `## subtitle`** (T1 default theme, T3 `theme: none`). `# Title` + `## Subtitle` is laid out as a
   content slide with one empty card. `check` prints "ok". With `@cover` it is a cover plus an info hint, and a
   plain subtitle line also works. SKILL.md says "`##` there is a subtitle line", which is what agents followed.
2. **List after a KPI row** (T2). `@4` KPI cards, `@end`, then three bullets: the bullets are set in very small
   text in the top-left and half the slide stays empty.
3. **Table narrower than the conclusion bar** (T1): the table ends at about 80% of the content width, the bar
   spans all of it.
4. **Five chevrons with Vietnamese labels** (T3): a word broke in the middle of a syllable; the agent switched
   to `flow` after three rebuilds.

The python-pptx arm had one miss of its own (a doughnut without data labels).

### Earlier measurements to correct

- **"6% of python-pptx" (TOKEN_FLOOR.md, eval tasks 01–20).** All 20 files in `bench/answers/run-2-python-pptx`
  contain the same 12 helper functions, byte for byte: 2,159 tokens, 80% of each file. Counted once the ratio is
  24%; with helpers treated as a library 29% (9–53% per task); with equal visible text 30.5%. The python-pptx
  decks carry 32% more visible text. `20-speaker.py` raises `TypeError` and is still in the total.
- **L4 "total agent tokens ≤ 40%"** was checked as (SKILL.md + deck) / python file = 0.39. Those are file
  sizes. With today's SKILL.md (1,037 tokens) the same formula gives 0.44; real runs are in the pilot table.
- **L7 "≥ 95% of tasks need only SKILL.md"** was measured where reference pages were not offered. When they
  are offered, 3 of 3 agents read them first.
- **q3 corpus:** `slidemark.md` uses `bar` (horizontal bars), `python-pptx.py` builds a column chart.

## Design direction

1. **Count calls first.** Any change is judged by what it does to model calls per accepted deck. A feature that
   saves 50 source tokens and adds one lookup or one decision is a loss.
2. **SKILL.md is the only document an agent reads.** Fold in what agents fetched (chart and table options, the
   component list, `@` tokens, the brand header recipe, the classes). Remove the "More: `slidemark docs …`"
   line. Keep reference pages for humans. Raise the size budget to what the eval needs (start at ≤ 3,000 o200k
   tokens) and change `tests/test_skill.py` to match. Do not move content out of SKILL.md to meet a size gate.
3. **One command, and its output is enough to stop.** `slidemark build deck.md -o deck.pptx` parses, lints,
   applies safe mechanical fixes, builds and prints: grouped diagnostics, then one line of facts an agent would
   otherwise verify itself, for example `wrote deck.pptx: 10 slides 16:9, 2 charts, 4 tables, notes on 1 slide,
   0 warnings`. SKILL.md shows only `build`. `check` and `review` stay for people.
4. **Write and build in one tool call.** Accept the deck on stdin (`slidemark build - -o deck.pptx --save
   deck.md`) so a heredoc both saves and builds. Where a shell has no heredoc, SKILL.md tells the agent to send
   the write and the build in the same turn.
5. **Zero warnings must mean no need to look.** Every defect class a reviewer can see becomes a lint rule or a
   layout fix. A visible defect in a zero-warning deck is a bug in SlideMark; start with the four above. When a
   look is still wanted, give one contact sheet image (`--png sheet.png`), not one image per slide.
6. **A warning is fixed in one edit, without thinking.** The hint names the token or selector to change and a
   value that passes (contrast: the nearest passing shade of the declared colour). Identical warnings print once
   with a count.
7. **Defaults remove decisions.** A brand deck should need `colors:` and `fonts:` only: title band, table
   header, chart palette and KPI colour derive from those tokens, with contrast-safe adjustment, and stay
   overridable. Cover inference must match what SKILL.md tells agents to write.
8. **Teach by pattern.** SKILL.md gives one complete example per common deck shape (default business, dense JA,
   brand colours), so an agent copies and adapts instead of reasoning out the syntax.

### What the target path costs

Budget arithmetic from the measured constants, for a 3-call run plus the hand-back call:

| Deck | SlideMark target, cost above common start | python-pptx measured | Ratio |
|---|---|---|---|
| 3 slides | about 40k units | 106k | about 38% |
| 5 slides | about 45k units | 268k (one run, with detours) | about 17% |
| 10 slides | 54–66k units | 224k | 24–29% |

Assumptions: SKILL.md at 3,000 o200k tokens, at most 2k thinking tokens, no image views, no fix loop. The 30%
is within reach from 5 slides up and only on this path. On the same path the all-in ratio would be about
35–65%, because both arms pay the same 75k units for the first call.

## Metric and gates

- **Model call:** one API request (unique `requestId`) in the subagent transcript.
- **Cost units:** fresh input + 1.25 × cache write + 0.10 × cache read + 5 × output (thinking included).
- **Cost above common start:** cost minus the first call's context, which both arms pay.
- **Accepted:** the acceptance script passes and a blind reviewer finds no defect in the rendered slides.

Add these as a gate group "AC" in `docs/TARGETS.md`, re-open the L4 "total agent tokens" gate, and restate the
L7 "only SKILL.md" gate in these terms:

- [ ] **AC1 Harness.** `bench/agent_cost.py` reads subagent transcripts and prints the pilot table columns
  (calls, output, cost, cost above start, images viewed, docs attempts). Method in Appendix B.
- [ ] **AC2 SKILL only.** With reference pages unavailable: ≥ 90% accepted over ≥ 27 runs (9 briefs × 3).
  With them available: median 0 lookups per run.
- [ ] **AC3 Calls.** Median ≤ 4 model calls from brief to hand-back, 90th percentile ≤ 6.
- [ ] **AC4 Cost.** Median cost above common start ≤ 35% of the python-pptx arm over the brief set, and ≤ 30%
  on briefs of 5 slides or more.
- [ ] **AC5 Output.** Median output tokens (thinking included) ≤ 30% of the python-pptx arm.
- [ ] **AC6 Trust.** Median 0 images viewed per run; reviewer-found defects in zero-warning decks ≤ 0.02 per
  slide.

Public wording until AC4 passes: "the deck source is 15–30% of the equivalent python-pptx script". Do not write
"agent cost" or "tokens per deck" for a file-size ratio.

## Test protocol

**Arms**

- `skill-only`: SlideMark. The agent may read its brief and SKILL.md. `slidemark docs` is disabled (an env
  switch that prints one line and exits non-zero) and each attempt is counted.
- `skill-open`: the same with `slidemark docs` available. It measures how many lookups SKILL.md still causes.
- `python-pptx`: the baseline, in a venv without slidemark. Its cost changes only with the brief set and the
  model, so run it once per brief set and reuse the numbers.

**Subagents.** Fresh context per run, the same model in every arm, no mention of another arm or of the
comparison. Each works in its own folder **outside the repo checkout**: a worktree shows the agent the docs,
examples and bench answers and invalidates the run. Prompts are in Appendix A. After the run, read the
transcript and discard any run that read a file outside its folder other than SKILL.md.

**Briefs.** Write new ones for every full run; never reuse `bench/tasks` (SKILL.md was tuned on them). Give the
content word for word (titles, bullets, table cells, chart data, notes) so both arms present the same text,
and list the acceptance requirements. Cover 3, 5 and 10 slides; EN, dense JA and VI; default look and required
brand colours. Nine briefs, three runs per cell; report the median and the range.

**Acceptance script.** From the .pptx: every required string from the brief (text frames, table cells, notes,
chart XML), slide count, 16:9, native chart and table counts, notes where asked. Then a reviewer subagent that
sees only one contact sheet per deck, not the arm, and reports from a fixed list: overflow, overlap, cut-off
text, tiny text beside a large empty area, a cover that is not a cover, missing data labels.

**Size.** The six pilot runs cost 1.75M units. Per run day: a smoke test of 3 briefs × `skill-only` × 1.
Full matrix (9 briefs × 2 SlideMark arms × 3) when SKILL.md, the CLI output or the lint rules change. Keep to
two subagents at a time.

## Work packages, in order

| # | Lane | Work | Expected effect per run |
|---|---|---|---|
| 1 | Orchestrator | `bench/agent_cost.py`, acceptance script, first brief set, AC gates in TARGETS.md, corrected numbers in TOKEN_FLOOR.md and AGENT_TIPS.md | makes the rest measurable |
| 2 | Orchestrator | SKILL.md as the single document: fold in the fetched pages, drop the docs pointer, lead with the one-command recipe, one example per deck shape; new size budget in `tests/test_skill.py` | −2 calls, −6k input tokens |
| 3 | A (CLI) | `build` = lint + safe fixes + build + facts line; stdin and `--save`; grouped warnings; `--png` contact sheet; `docs` switch for the eval | −2 to −3 calls |
| 4 | B (layout, lint) | The four silent defects: cover with `##`, list after a KPI row, table width, chevron word wrap. A rule or a fix for each, with a golden test | removes the reason to look: −1 to −2 calls, −4k to −12k tokens |
| 5 | A + B | One-edit warnings: contrast hint with the token and a passing colour, or a contrast-safe derived default | −4 calls on brand decks |
| 6 | B | Brand deck from `colors:` and `fonts:` alone | fewer thinking tokens |

Re-run the smoke test after each package and record calls, cost above start and accepted rate in
`bench/history.jsonl`.

## Do not

- Do not shrink SKILL.md to pass a size gate if agents then look things up.
- Do not report a file-size ratio as agent cost.
- Do not add shorter syntax that adds a decision: a thinking token costs five input tokens.
- Do not send agents to images for anything a rule can state.
- Do not tune only on the fixed 140 tasks, and do not run eval agents inside the repo.
- Do not hard-code a look to get a default: derive it from tokens.

## Appendix A: prompts used in the pilot

Shortened. Both arms received the same text except step 2. `<folder>` held only `brief.md`.

```text
Build a PowerPoint deck from a written brief.

Your working folder is <folder>. Run every command from that folder, and do not read, list, search or write
anything outside it except the paths named below.

1. Read brief.md in your folder. It gives the slides, the exact content, and the acceptance requirements.
2. <arm-specific step>
3. You are finished when deck.pptx meets every requirement in the brief. How you verify that is up to you; a
   reviewer will inspect the rendered slides afterwards.

Leave <source file> and deck.pptx in your folder. Reply in one or two sentences: what you delivered, and
anything that does not meet the brief.
```

SlideMark step 2: "Build the deck with SlideMark: write the deck as SlideMark text in deck.md and build it with
the `slidemark` command line tool, which is installed and on PATH. Read its guide first: `<path>/SKILL.md`. Do
not make the file any other way, and do not use the Skill tool." The pilot also allowed `slidemark docs
<topic>`; leave that sentence out for `skill-only`.

python-pptx step 2: "Build the deck with python-pptx: write a Python script build.py that creates deck.pptx, and
run it with `<venv python> build.py`. Do not make the file any other way, and do not use the Skill tool."

Both: "To look at the slides, run `<render tool> deck.pptx previews`; it writes previews/slide-NN.png."

## Appendix B: reading cost from a transcript

Observed in Claude Code, October 2026; verify the paths and fields in the harness the run uses.

- One file per subagent: `~/.claude/projects/<project>/<session-id>/subagents/agent-<id>.jsonl`. Lines with
  `type: assistant` carry `requestId` and `message.usage`. One request spans several lines: group by
  `requestId`.
- Exact per request: `input_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`. Their sum is the
  context of that call.
- **`output_tokens` is a snapshot taken when the stream starts (2, 3, 4…). Do not use it.**
- Output of call k, thinking included, is what the next call's context gained minus what the tools returned:
  `out_k = ctx_(k+1) − ctx_k − 1.45 × tool_text_k − image_px_k / 750 − 29`, with tool text counted in
  `o200k_base`. For a call without a thinking block use `1.53 × visible_k` (text plus tool-call JSON).
- The harness adds about 5.2k tokens once, between calls 1 and 2: take `out_1` from visible content only.
- The last call has no successor: use `1.53 × visible`.
- `subagent_tokens` in the completion notice is the final context size, not the total cost.
- Count from tool inputs: `slidemark docs` attempts, builds, PNG reads, and any path outside the run folder.
