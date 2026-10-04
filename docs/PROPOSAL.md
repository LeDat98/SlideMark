# SlideMark: design proposal

> Goal: a Python library an agent installs in its sandbox, writes text (SlideMark syntax / HTML / JSON),
> and gets back a **native, editable** `.pptx` that can use every presentation feature of PowerPoint.
> The package name may change later.

## 1. Positioning: why another library?

| Tool | Editable PPTX? | Good layout | Agent-friendly |
|---|---|---|---|
| Marp / Slidev | No, every slide is exported as an image | Yes | Medium |
| Pandoc (md → pptx) | Yes | Weak, a few fixed layouts | Medium |
| python-pptx | Yes | You compute every coordinate | Poor, low-level API |
| pptxgenjs | Yes | You compute every coordinate | Poor, and needs Node |

No existing tool combines **native PPTX** (editable text, charts and tables), **good automatic layout**, and a
**design for agents** (predictable syntax, clear errors, a self-check and preview step). SlideMark targets that gap.

## 2. Design principles

1. **Agent-first.** Text is Markdown, which LLMs already know. Errors carry a line number and a fix hint.
   The syntax docs ship inside the package.
2. **Native first, images last.** Text, shapes, tables and charts are real PowerPoint objects. Only content that
   cannot be represented natively (arbitrary HTML, complex Mermaid) is rendered to an image.
3. **Easy by default, deep when needed.** A simple slide takes a few lines. Escape hatches exist for full control:
   attributes, absolute positions, HTML, the JSON IR, the Python API.
4. **A self-check loop.** `build → check → preview → fix`. The agent learns about overflowing text, elements off
   the slide or low contrast before a human opens the file.
5. **Valid OOXML.** Files must open in PowerPoint without a "repair" prompt. This is the biggest technical risk (§9).
6. **Token cost is the main value metric.** Every new piece of syntax gets a measured token count and must not
   raise the agent's total cost: docs read + deck generated + fix rounds (§4b, §8b).
7. **Every feature goes through the full test process** before it counts as done (§8).

## 3. Architecture

```
 SlideMark text ─┐
 HTML           ─┼─▶ Parser ─▶ IR (Pydantic) ─▶ Layout engine ─▶ Renderer ─▶ .pptx
 JSON/YAML      ─┤             Deck/Slide/       (arrangement,     (python-pptx + lxml
 Python API     ─┘             Element           measurement,      for missing OOXML)
                               (+ JSON Schema)   autofit, theme)
                                     │                                 │
                                     ▼                                 ▼
                             Validator / linter            Preview (LibreOffice → PDF → PNG)
```

- **IR (intermediate representation)** is the core contract (`src/slidemark/ir.py`). Every input becomes the same
  Pydantic model, which also gives a JSON Schema for tool calling or MCP. A new input format only needs a parser.
- **Layout engine** turns blocks and `@` grid specs into absolute EMU boxes. It measures text with real font
  metrics to shrink text and detect overflow.
- **Renderer** is built on python-pptx. Whatever python-pptx lacks (transitions, animations, sections, advanced
  actions, media) is written as OOXML with lxml.
- **Secondary backends** (later): HTML preview, PDF.

### Planned libraries

| Purpose | Library |
|---|---|
| Markdown inside slides | `markdown-it-py` + `mdit-py-plugins` |
| IR and validation | `pydantic` v2 |
| Writing PPTX | `python-pptx` + `lxml` |
| Code highlighting | `pygments` → colored text runs (native, editable) |
| Math | LaTeX → MathML (`latex2mathml`) → OMML (XSLT): native Office equations |
| Text measurement | `Pillow` / `fonttools` |
| HTML (extra) | `playwright` (headless Chromium) |
| Preview (extra) | headless LibreOffice → PDF → PNG (`pypdfium2`) |
| CLI | `argparse` (no extra dependency, small install) |

Extras: `pip install slidemark` (light core), `slidemark[html]`, `slidemark[preview]`, `slidemark[all]`.

## 4. Input syntax

The authoritative spec is **`docs/SYNTAX.md` (v1)**. It is SlideMark's own syntax, which borrows only Markdown for
text from tools like Slidev:

- **Headings are the structure.** `#` starts a slide (no separators), `##` makes a box, and boxes are arranged
  automatically.
- **One `@` line overrides the layout** with a tiny grid notation: `@3`, `@1:2`, `@aab/aac` (grid areas), `@4 chevron`.
- **Position gives meaning.** `>` under the title is the lead message, `>` at the end is a conclusion bar,
  `※` lines are footnotes.
- **Data is CSV** in fences named after the result (` ```column `, ` ```table `).

An earlier Slidev-style draft (`---` + YAML per slide + `:::` containers) was dropped. It cost more tokens, and its
closing markers were easy for agents to get wrong.

Besides the text syntax, an agent can send **JSON that follows the IR schema** for exact control, or use the
**Python API**.

## 4b. Designing for the fewest agent tokens

### Measurements (`bench/count_tokens.py`, `o200k_base` proxy tokenizer)

| Deck | SlideMark v1 | Comparison |
|---|---:|---|
| 3 slides: title + notes, bullets + chart, table | 155 | python-pptx 518 (SlideMark costs **30%** of it); HTML 321 |
| 2 dense Japanese business slides | 482 | HTML 828 (SlideMark costs **58%** of it) |

The python-pptx version has no theme or alignment at all. Matching the visual quality would make it much longer,
so the real gap is wider than the table shows.

### The cost to optimize is the whole loop

```
cost = tokens to read docs/skill (input, once)
     + tokens to generate the deck (output, about 5× the price of input)
     + fix rounds × (tokens to read diagnostics + tokens to regenerate)
```

Output tokens are the most expensive, so they come first. But syntax that is too terse and easy to get wrong
raises the number of fix rounds and the total. Always measure the **total**, not just syntax length.

### Design rules

1. **Smart defaults.** No declarations still gives a good slide. Layout is inferred from content (block count,
   text + visual, cover/section detection).
2. **Data as CSV, not YAML.**
3. **Short names, long aliases accepted.** `w`/`width`, `bg`/`background`. The docs teach only the short form.
4. **Define once, reuse.** Theme classes and components instead of repeated inline styles.
5. **Lenient parser.** It accepts variants agents commonly write (Markdown front-matter, Slidev/Marp habits,
   wrong case) and emits warnings instead of errors, because every fix round costs tokens.
6. **Short, actionable errors.** One line each: `slide 3 L42 overflow: ... -> use @2x2 or .dense`.
7. **Local fixes.** Diagnostics name the slide and line, so the agent edits one slide instead of regenerating
   the whole deck.
8. **Docs have token budgets.** For example, `SKILL.md` ≤ 1,500 tokens and each `reference/` file ≤ 800.
   CI fails when a budget is exceeded.

## 5. HTML support

Two modes, chosen with `render=native|image` (default `auto`):

1. **HTML → native shapes (default).** Headless Chromium (Playwright) renders the HTML/CSS at slide size.
   SlideMark reads each element's `getBoundingClientRect()` and computed style, then emits native shapes, text
   boxes, images and tables at those positions. The browser does the layout and the PPTX stays editable
   (the proven html2pptx idea).
2. **HTML → image (fallback).** What cannot become native (canvas, complex SVG, CSS filters, unusual web fonts)
   is captured as PNG/SVG and embedded.

The linter warns whenever content falls back to an image, so the agent knows that part is not editable.

## 6. PPTX feature matrix (long-term goal)

| Group | Features |
|---|---|
| Text | font, color, highlight, super/subscript, multi-level lists, numbering, alignment, line spacing, autofit, text columns, basic WordArt |
| Shapes | ~180 auto shapes, lines/connectors, freeform paths, gradient, shadow, glow, rotation, group, z-order |
| Images | crop, shape masks, native SVG, transparency, alt text |
| Tables | merged cells, styles, borders, banding, alignment |
| Charts | bar/column/line/area/pie/doughnut/scatter/bubble/radar/combo, with embedded Excel data so they stay editable |
| Diagrams | Mermaid → native shapes (simple) or image; SmartArt-like process/cycle/hierarchy built from shapes |
| Code / math | highlighting as native text runs; native OMML equations |
| Presenting | transitions (fade, push, wipe, morph...), animations (entrance/emphasis/exit/motion path, bullet builds), triggers |
| Navigation | hyperlinks, slide jumps, action buttons, table of contents, sections, custom shows, hidden slides |
| Media | video and audio (embedded or linked), poster frames |
| Structure | masters/layouts, placeholders, footer, slide number, date, theme colors/fonts, corporate `.potx` templates |
| Other | speaker notes, comments, metadata, accessibility (alt text, reading order), font embedding (hard, later) |

## 7. Agent tooling

```bash
slidemark build deck.md -o deck.pptx       # build
slidemark check deck.md                    # lint: overflow, off-slide, low contrast, too much text, missing alt
slidemark preview deck.md -o out/          # PNG per slide so a multimodal agent can look at the result
slidemark docs [topic]                     # syntax docs inside the sandbox, no internet needed
slidemark schema                           # JSON Schema of the IR
slidemark skill install                    # install SKILL.md for Claude / other agents
slidemark import deck.pptx -o deck.md      # (later) pptx → text so agents can edit existing decks
```

- `check --format json` gives one object per problem: `slide`, `line`, `element`, `rule`, `hint`.
- **Skill pack:** a short `SKILL.md` (core syntax and workflow) plus `reference/` split by topic (charts, layout,
  animation, html...), so an agent reads only what it needs. Every docs example runs in CI, so docs never drift
  from the code.
- Later: an MCP server (`slidemark mcp`).

## 8. Test process for every feature

### 8a. Definition of Done: 8 steps

| # | Step | Content | Tools |
|---|---|---|---|
| 1 | **Spec and docs first** | A docs entry with the shortest possible example and a token budget for it. | `docs/` |
| 2 | **Parser** | The example parses to the right IR; common agent mistakes are tested too. | pytest |
| 3 | **Parser fuzzing** | Random or broken input never crashes; it yields diagnostics with line numbers. | hypothesis |
| 4 | **Renderer** | Reopen the .pptx and assert properties: positions, fonts, colors, chart type, data... | python-pptx + lxml |
| 5 | **Valid OOXML** | XML passes the ECMA-376 XSD; LibreOffice opens it without errors. | xmlschema, soffice |
| 6 | **Golden snapshot** | Normalized XML and rendered image (perceptual diff with a threshold) match the golden copy. | pytest, image diff |
| 7 | **Lint** | If the feature can break the visual (overflow, overlap...), `check` has a rule for it, with tests. | pytest |
| 8 | **Bench** | No metric regresses beyond its threshold unless the commit explains why. | `bench/` |

Each feature has a row in `docs/FEATURES.md` with the status of all 8 steps, so half-finished features are visible.

### Test tiers

| Tier | When | Duration |
|---|---|---|
| Unit, parser, renderer, lint, docs examples, token budgets | every commit (CI) | < 1 min |
| XSD and golden XML | every commit (CI) | < 2 min |
| Golden images via LibreOffice | daily run | a few minutes |
| Agent eval (real model calls, costs money) | weekly, and by hand after syntax changes | depends on size |
| Real PowerPoint check | every milestone (manual) | — |

## 8b. Daily measurement and optimization

### Core metrics

| Group | Metric | Goal |
|---|---|---|
| **Tokens: syntax** | tokens per corpus deck vs the python-pptx/HTML baselines | down, never up |
| **Tokens: docs** | tokens of SKILL.md and each reference file | within budget |
| **Tokens: real agent** | input / output / total tokens to reach a deck that passes `check` | down |
| **Reliability** | first-pass success rate, mean fix rounds, parse error rate | up / down / down |
| **Quality** | `check` violations per deck, golden image drift | down |
| **Performance** | build time per slide, import time, install size, dependency count | small, since agents install it in every sandbox |
| **Coverage** | test coverage, finished cells in the feature matrix | up |

### Storage

```
bench/
  corpus/<deck>/            # one deck written several ways: slidemark, html, python-pptx
  tasks/<task>.md           # agent eval prompts (e.g. "make an 8-slide Q3 report from this data...")
  count_tokens.py           # syntax tokens (offline o200k_base proxy; exact Claude counts with an API key)
  history.jsonl             # append-only: date, commit, metric, deck/task, value, tokenizer
  BASELINE.json             # best current values; CI compares against it to catch regressions
  report.py                 # (later) trend charts from history.jsonl
```

- `history.jsonl` is committed and every row carries a commit, so any metric change can be traced to its cause.
- CI fails when a metric regresses past its threshold against `BASELINE.json` (e.g. tokens +2%). Accepting it
  means updating the baseline in the same commit, with a reason.
- Proxy token counts are for relative comparison (stable, offline). Exact counts come from the Claude
  `count_tokens` API and from usage in agent evals.

### Daily loop

The daily routine is described in `docs/PLAN.md`. Each day: build features through all 8 DoD steps, record the
bench, compare with the previous day, and fix or explain regressions. Weekly agent evals choose the next
optimization target (for example, the syntax agents get wrong most often becomes more lenient or shorter).

## 9. Risks and mitigations

| Risk | Mitigation |
|---|---|
| LibreOffice opens the file but PowerPoint wants to repair it | XSD validation; XML modeled on files saved by PowerPoint; periodic checks in real PowerPoint |
| Text measurement differs from PowerPoint, causing overflow | real font metrics, safety margins, `normAutofit` as a backstop |
| Animation/timing XML is very complex | build from presets instead of covering the whole spec |
| Scope is huge | daily milestones with small, tested tasks (`docs/PLAN.md`, `docs/TARGETS.md`) |
| Fonts missing in the sandbox | bundle open fonts (Inter, Noto incl. Vietnamese/CJK) for measurement and preview |

## 10. Roadmap and decisions

- Roadmap: `docs/PLAN.md` (7-day foundation, then daily routine) and `docs/TARGETS.md` (levels L1–L7).
- Decisions taken:
  - own syntax v1 (`docs/SYNTAX.md`);
  - everything in the repo in English except `README.md` (Vietnamese);
  - Python 3.10+;
  - MIT license;
  - at most 2 Sonnet subagents per day;
  - pushes go straight to `main`.
- Open: the PyPI package name. Check availability before the first release.
