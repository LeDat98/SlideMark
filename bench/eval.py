"""Agent eval harness v0.

Each task in ``bench/tasks/*.md`` is a natural-language request. An answer is a SlideMark deck written by an
agent that only saw the skill docs (``src/slidemark/skill``). The harness scores answers offline:

- ``first_pass``: the answer parses, lays out and lints with no warning or error (info is fine);
- ``warnings``: count of warnings + errors (fix rounds an agent would need, roughly);
- ``tokens``: answer size (o200k proxy).

Usage:
    python bench/eval.py --answers bench/answers/<run>         # score saved answers
    python bench/eval.py --answers bench/answers/<run> --live  # ask a model first (ANTHROPIC_API_KEY)
    python bench/eval.py ... --record                          # append a summary to bench/eval_history.jsonl
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
from pathlib import Path

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parent
TASKS = BENCH / "tasks"
HISTORY = BENCH / "eval_history.jsonl"


def skill_text() -> str:
    skill = ROOT / "src" / "slidemark" / "skill"
    parts = [(skill / "SKILL.md").read_text(encoding="utf-8")]
    return "\n\n".join(parts)


def ask_model(task: str) -> str:  # pragma: no cover - needs network and a key
    import anthropic

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=os.environ.get("SLIDEMARK_EVAL_MODEL", "claude-sonnet-5-5"),
        max_tokens=4000,
        system=skill_text() + "\n\nAnswer with the SlideMark source only: no explanation, no wrapping fence.",
        messages=[{"role": "user", "content": task}],
    )
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


def score(text: str) -> dict:
    from slidemark.layout import layout_slide
    from slidemark.lint import lint
    from slidemark.parser import parse
    from slidemark.theme import get_theme

    deck = parse(text)
    builtin = deck.theme in ("default", "midnight", "jp-business")
    theme = get_theme(deck.theme if builtin else "default")
    placed = [layout_slide(s, deck, theme, i) for i, s in enumerate(deck.slides)]
    seen = {(d.rule, d.slide) for d in deck.diagnostics}
    diags = deck.diagnostics + [d for d in lint(deck, placed, theme) if (d.rule, d.slide) not in seen]
    bad = [d for d in diags if d.level in ("warning", "error")]
    try:
        import tiktoken

        tokens = len(tiktoken.get_encoding("o200k_base").encode(text))
    except ImportError:  # pragma: no cover
        tokens = len(text) // 3
    return {
        "slides": len(deck.slides),
        "first_pass": not bad and len(deck.slides) > 0,
        "warnings": len(bad),
        "rules": sorted({d.rule or "" for d in bad}),
        "tokens": tokens,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--answers", required=True, type=Path)
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--record", action="store_true")
    args = ap.parse_args()
    args.answers.mkdir(parents=True, exist_ok=True)
    rows = []
    for task in sorted(TASKS.glob("*.md")):
        ans = args.answers / task.name
        if args.live:
            ans.write_text(ask_model(task.read_text(encoding="utf-8")), encoding="utf-8")
        if not ans.exists():
            print(f"{task.stem}: no answer")
            continue
        r = {"task": task.stem, **score(ans.read_text(encoding="utf-8"))}
        rows.append(r)
        mark = "ok " if r["first_pass"] else "FIX"
        print(f"{mark} {task.stem:16} n={r['slides']} warn={r['warnings']} tok={r['tokens']} {r['rules']}")
    if not rows:
        return 1
    summary = {
        "date": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "commit": subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT
        ).stdout.strip(),
        "answers": args.answers.resolve().name,
        "tasks": len(rows),
        "first_pass_rate": round(sum(r["first_pass"] for r in rows) / len(rows), 3),
        "mean_warnings": round(sum(r["warnings"] for r in rows) / len(rows), 3),
        "mean_tokens": round(sum(r["tokens"] for r in rows) / len(rows), 1),
    }
    print(json.dumps(summary, ensure_ascii=False))
    if args.record:
        with HISTORY.open("a", encoding="utf-8") as f:
            f.write(json.dumps(summary, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
