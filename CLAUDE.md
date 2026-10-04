# SlideMark: notes for coding sessions

Python library: token-efficient Markdown/HTML → native, editable .pptx for AI agents.
Design: `docs/PROPOSAL.md` (Vietnamese). Plan: `docs/PLAN.md`. Syntax: `docs/SYNTAX.md`.

## Before you start
1. Read `docs/LESSONS.md` (known bugs, pitfalls, fixes). It is short on purpose.
2. Check today's tasks in `docs/PLAN.md`.

## Setup and commands
```bash
uv venv .venv && uv pip install -e ".[dev]" --python .venv
.venv/bin/pytest -q                 # all tests
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/python bench/count_tokens.py --record   # token metrics, append to bench/history.jsonl
.venv/bin/python scripts/gallery.py               # rebuild examples -> docs/gallery PNGs + README section
```

## Architecture (contract: `src/slidemark/ir.py`)
`parser/` Markdown → `Deck` · `layout/` `Slide` → `list[Placed]` (absolute EMU) · `render/` → .pptx ·
`theme.py` design tokens · `units.py` lengths. The renderer never decides positions; layout never touches pptx.
Changing `ir.py` affects every module: keep changes additive and update all users in the same commit.

## Definition of Done (every feature)
docs entry with shortest example → parser test → fuzz-safe (no crash, diagnostic instead) → render test
(reopen the .pptx and assert) → opens in LibreOffice → golden/gallery image looks right → lint rule if it can
break the visual → bench has no token regression. Mark progress in `docs/FEATURES.md`.

## Rules
- Token cost is the main product metric. New syntax must be the shortest unambiguous form; measure it.
- Never raise on bad user input: append a `Diagnostic` with a one-line, actionable `hint`.
- Dense Japanese business slides (many boxes, 10–12pt text, tables, arrows, footnotes) are a first-class
  target. Always test CJK text (`<a:ea>` font, full-width width ≈ 1em).
- When you hit a bug, pitfall or non-obvious fix, add one line to `docs/LESSONS.md`.
- When you verify a usage pattern that saves agents tokens or retries, add it to `docs/AGENT_TIPS.md`.
- Every working day ends with: tests green, `scripts/gallery.py` run, README gallery updated, bench recorded.
