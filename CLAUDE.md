# SlideMark: notes for coding sessions

Python library: token-efficient Markdown/HTML → native, editable .pptx for AI agents.
Design: `docs/PROPOSAL.md`. Plan: `docs/PLAN.md`. Syntax: `docs/SYNTAX.md`.

## Before you start
1. Read `docs/LESSONS.md` (known bugs, pitfalls, fixes). It is short on purpose.
2. Check today's tasks in `docs/PLAN.md`.
3. Read `docs/AGENT_COST.md`: what to optimize (model calls first, then output tokens, then input).

## Setup and commands
```bash
uv venv .venv && uv pip install -e ".[dev,html]" --python .venv   # html = Playwright; Chromium is pre-installed in the cloud env
.venv/bin/pytest -q                 # all tests
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/python bench/count_tokens.py --record   # token metrics, append to bench/history.jsonl
.venv/bin/python scripts/gallery.py               # rebuild examples -> docs/gallery PNGs + README section
```
Previews use the repo's `src/slidemark/fonts/fonts.conf` (Meiryo / Yu Gothic -> IPAPGothic, Arial / Inter -> Liberation
Sans, Georgia -> Liberation Serif) so renders and goldens are the same everywhere: `docs/RENDERING.md`. Optional:
`apt-get install fonts-noto-cjk` (~60 MB) gives a real bold CJK face, but goldens are made without it.

## Architecture (contract: `src/slidemark/ir.py`)
`parser/` Markdown → `Deck` · `layout/` `Slide` → `list[Placed]` (absolute EMU) · `render/` → .pptx ·
`theme.py` design tokens · `units.py` lengths. The renderer never decides positions; layout never touches pptx.
Changing `ir.py` affects every module: keep changes additive and update all users in the same commit.

## Definition of Done (every feature)
docs entry with shortest example → parser test → fuzz-safe (no crash, diagnostic instead) → render test
(reopen the .pptx and assert) → opens in LibreOffice → golden/gallery image looks right → lint rule if it can
break the visual → bench has no token regression. Mark progress in `docs/FEATURES.md`.

## Workflow
- **Language: everything in the repo is English** (code, comments, docs, commit messages, logs) **except
  `README.md`, which is Vietnamese.** `scripts/gallery.py` must keep the README text Vietnamese.
  Slide *content* in `examples/` and `bench/corpus/` may be Japanese/Vietnamese on purpose (test data).
- Push straight to `main` (allowed by the owner). No pull requests needed.
- GitHub Actions minutes are limited (private repo): CI runs once a day (08:00 JST) and on demand, not on push.
  Always run ruff + the full pytest suite locally before pushing; push once per wave, not per commit.
- Runs are led by an Opus orchestrator, last ≥ 2 hours, and use at most 2 Sonnet subagents at a time
  (lane A front, lane B back), in waves; see "Run routine" in `docs/PLAN.md`.

## Rules
- **Design freedom first (`docs/DESIGN_FREEDOM.md`).** Never hard-code a visual decision: colors, fonts, sizes,
  spacing, bands, card looks and layout constants are tokens an agent can override from the deck (tokens, CSS or
  HTML). Built-in themes are YAML presets in the public token schema, with no theme-specific code paths.
- Token cost is the main product metric, and it means the cost of the whole agent run to an accepted deck
  (`docs/AGENT_COST.md`): model calls first, then output tokens, then input. SKILL.md must be all an agent
  reads. New syntax must be the shortest unambiguous form that adds no lookup and no decision; measure it.
- Never raise on bad user input: append a `Diagnostic` with a one-line, actionable `hint`.
- Dense Japanese business slides (many boxes, 10–12pt text, tables, arrows, footnotes) are a first-class
  target. Always test CJK text (`<a:ea>` font, full-width width ≈ 1em).
- When you hit a bug, pitfall or non-obvious fix, add one line to `docs/LESSONS.md`.
- When you verify a usage pattern that saves agents tokens or retries, add it to `docs/AGENT_TIPS.md`.
- Every working day ends with: tests green, `scripts/gallery.py` run, README gallery updated, bench recorded.
