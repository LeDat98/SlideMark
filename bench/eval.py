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
    python bench/eval.py ... --tasks "2*,*-jp-*"               # only tasks whose name matches a glob
    python bench/eval.py ... --tag jp                          # only tasks carrying a tag
    python bench/eval.py ... --summary-by tag                  # first-pass rate per tag (jp html vi en hard)

A task file may start with ``<!-- tags: jp dense html -->``; the line is stripped before a model sees it.
Answers may reference media, images and templates that do not exist on disk: those diagnostics
(``image-missing``, ``missing-media``, ``bad-theme`` "file not found") are counted as ``assets`` and never
fail the first pass.
"""

from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parent
TASKS = BENCH / "tasks"
HISTORY = BENCH / "eval_history.jsonl"


def skill_text() -> str:
    skill = ROOT / "src" / "slidemark" / "skill"
    parts = [(skill / "SKILL.md").read_text(encoding="utf-8")]
    return "\n\n".join(parts)


_TAGS = re.compile(r"\A\s*<!--\s*tags:(.*?)-->[ \t]*\r?\n?", re.S)
ASSET_RULES = frozenset({"image-missing", "missing-media"})  # a file the answer points at does not exist here


def parse_task(text: str) -> tuple[list[str], str]:
    """Split a task file into (tags, prompt); the ``<!-- tags: a b -->`` first line is not in the prompt."""
    m = _TAGS.match(text)
    if not m:
        return [], text
    return m.group(1).split(), text[m.end() :].lstrip("\n")


def is_asset_missing(d) -> bool:
    """True for the diagnostics caused only by absent media / images / template files (acceptable in eval)."""
    if d.rule in ASSET_RULES:
        return True
    return d.rule == "bad-theme" and "file not found" in d.message


def select_tasks(tasks: list[Path], pattern: str | None = None, tag: str | None = None) -> list[Path]:
    """Filter task files by name glob(s) (comma separated; matched on stem and file name) and/or tag."""
    out = []
    pats = [p.strip() for p in pattern.split(",") if p.strip()] if pattern else []
    for t in tasks:
        if pats and not any(fnmatch.fnmatch(t.stem, p) or fnmatch.fnmatch(t.name, p) for p in pats):
            continue
        if tag and tag not in parse_task(t.read_text(encoding="utf-8"))[0]:
            continue
        out.append(t)
    return out


def ask_model(task: str) -> str:  # pragma: no cover - needs network and a key
    import anthropic

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=os.environ.get("SLIDEMARK_EVAL_MODEL", "claude-sonnet-5-5"),
        max_tokens=8000,
        system=skill_text() + "\n\nAnswer with the SlideMark source only: no explanation, no wrapping fence.",
        messages=[{"role": "user", "content": task}],
    )
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


def score(text: str) -> dict:
    """Parse, lay out, lint and render ``text``; missing assets only show up at render and are tolerated."""
    from slidemark.build import build_deck
    from slidemark.parser import parse

    deck = parse(text)
    with tempfile.TemporaryDirectory() as tmp:  # empty base dir: every referenced asset is "missing"
        try:
            build_deck(deck, Path(tmp) / "out.pptx", tmp)
        except Exception as e:  # a crash is a real failure, never an exception for the harness
            from slidemark.ir import Diagnostic

            deck.diagnostics.append(
                Diagnostic(level="error", message=f"{type(e).__name__}: {e}"[:200], rule="crash")
            )
    diags = deck.diagnostics
    assets = [d for d in diags if is_asset_missing(d)]
    bad = [d for d in diags if d.level in ("warning", "error") and not is_asset_missing(d)]
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
        "assets": len(assets),
        "tokens": tokens,
    }


def summarize_by_tag(rows: list[dict]) -> dict[str, dict]:
    """Per-tag task count and first-pass rate (a task with several tags counts in each)."""
    out: dict[str, dict] = {}
    for r in rows:
        for t in r.get("tags") or ["untagged"]:
            o = out.setdefault(t, {"tasks": 0, "passed": 0})
            o["tasks"] += 1
            o["passed"] += bool(r["first_pass"])
    for o in out.values():
        o["first_pass_rate"] = round(o["passed"] / o["tasks"], 3)
    return dict(sorted(out.items()))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--answers", required=True, type=Path)
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--record", action="store_true")
    ap.add_argument("--baseline", type=Path, help="dir of python-pptx answers (<task>.py)")
    ap.add_argument("--tasks", metavar="GLOB", help='score a subset, e.g. "2*" or "*-jp-*,05-*" (comma list)')
    ap.add_argument("--tag", help="score only tasks with this tag (from the <!-- tags: ... --> line)")
    ap.add_argument("--summary-by", choices=["tag"], help="also print first-pass rate split by tag")
    args = ap.parse_args(argv)
    args.answers.mkdir(parents=True, exist_ok=True)
    rows = []
    for task in select_tasks(sorted(TASKS.glob("*.md")), args.tasks, args.tag):
        tags, prompt = parse_task(task.read_text(encoding="utf-8"))
        ans = args.answers / task.name
        if args.live:
            ans.write_text(ask_model(prompt), encoding="utf-8")
        if not ans.exists():
            print(f"{task.stem}: no answer")
            continue
        r = {"task": task.stem, "tags": tags, **score(ans.read_text(encoding="utf-8"))}
        rows.append(r)
        mark = "ok " if r["first_pass"] else "FIX"
        extra = f" assets-missing={r['assets']}" if r["assets"] else ""
        head = f"{mark} {task.stem:28} n={r['slides']} warn={r['warnings']} tok={r['tokens']}"
        print(f"{head} {r['rules']}{extra}")
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
    if args.summary_by == "tag":
        summary["by_tag"] = summarize_by_tag(rows)
    if args.baseline:
        import tiktoken

        enc = tiktoken.get_encoding("o200k_base")
        skill = len(enc.encode(skill_text()))
        base = [args.baseline / f"{r['task']}.py" for r in rows]
        if all(b.exists() for b in base):
            pptx = sum(len(enc.encode(b.read_text(encoding="utf-8"))) for b in base) / len(rows)
            summary["skill_tokens"] = skill
            summary["python_pptx_tokens"] = round(pptx, 1)
            # one task = read SKILL.md once + write the deck (+ fixes, ~0 when first_pass is high)
            summary["agent_token_ratio"] = round((skill + summary["mean_tokens"]) / pptx, 3)
    print(json.dumps(summary, ensure_ascii=False))
    if args.record:
        with HISTORY.open("a", encoding="utf-8") as f:
            f.write(json.dumps(summary, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
