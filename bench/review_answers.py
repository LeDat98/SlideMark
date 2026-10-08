"""Run the design critic over the eval answers and list the decks that score below a threshold.

Usage: python bench/review_answers.py [--answers DIR] [--below 95] [--verbose]

Prints the mean review score, the decks under the threshold with their ``design-*`` / layout warnings and a
tally of the rules that cost the most points. Layout work uses it to find the most common layout causes.
"""

from __future__ import annotations

import argparse
import collections
import statistics
import sys
from pathlib import Path

from slidemark.critique import critique, review_score
from slidemark.layout import layout_slide
from slidemark.lint import lint
from slidemark.parser import parse
from slidemark.template import deck_theme

ROOT = Path(__file__).resolve().parent.parent


def review(path: Path) -> tuple[int, list]:
    deck = parse(path.read_text(encoding="utf-8"))
    diags = list(deck.diagnostics)
    deck.attrs.setdefault("base_dir", str(path.resolve().parent))
    theme, tdiags = deck_theme(deck, deck.attrs["base_dir"])
    diags.extend(tdiags)
    placed = [layout_slide(s, deck, theme, i) for i, s in enumerate(deck.slides)]
    seen = {(d.rule, d.slide) for d in diags}
    diags.extend(d for d in lint(deck, placed, theme) if (d.rule, d.slide) not in seen)
    diags.extend(critique(deck, placed, theme))
    return review_score(diags, len(deck.slides)), diags


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--answers", default=str(ROOT / "bench/answers/run-5-sonnet"))
    ap.add_argument("--below", type=int, default=95)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    scores: list[int] = []
    tally: collections.Counter[str] = collections.Counter()
    for md in sorted(Path(args.answers).glob("*.md")):
        score, diags = review(md)
        scores.append(score)
        warn = [d for d in diags if d.level != "info" or args.verbose]
        for d in warn:
            tally[d.rule] += 1
        if score < args.below:
            print(f"{md.name}: {score}")
            for d in warn:
                print(f"    {d}")
    if not scores:
        print("no answers found", file=sys.stderr)
        return 1
    print(f"decks: {len(scores)}  mean review score: {statistics.fmean(scores):.2f}  min: {min(scores)}")
    print("rules:", ", ".join(f"{r} x{n}" for r, n in tally.most_common()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
