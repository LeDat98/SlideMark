"""L2 gate "layout inferred for >= 90% of example slides": share of slides that need no grid token.

A slide counts as inferred when it has no grid token (`@3`, `@2x2`, `@1:2`, `@aab/aac`), or when removing the
token gives the same layout. Semantic tokens (`flow`, `chevron`, connectors, `section`, `dense`) are content,
not layout, and never count against the gate.

Usage: python bench/layout_inference.py [--record]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path

from slidemark.layout import layout_slide
from slidemark.parser import parse
from slidemark.theme import get_theme

ROOT = Path(__file__).resolve().parent.parent


def boxes(slide, deck, theme, i):
    return [(p.x, p.y, p.w, p.h) for p in layout_slide(slide, deck, theme, i)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", action="store_true")
    args = ap.parse_args()
    total = inferred = 0
    for md in sorted((ROOT / "examples").glob("*.md")):
        deck = parse(md.read_text(encoding="utf-8"))
        theme = get_theme(deck.theme)
        for i, s in enumerate(deck.slides):
            total += 1
            if not s.grid:
                inferred += 1
                continue
            with_grid = boxes(s, deck, theme, i)
            grid, s.grid = s.grid, None
            same = boxes(s, deck, theme, i) == with_grid
            s.grid = grid
            inferred += same
            print(f"{md.stem} slide {i + 1}: @{grid} {'redundant' if same else 'needed'}")
    ratio = inferred / total if total else 0.0
    print(f"inferred {inferred}/{total} = {ratio:.0%}")
    if args.record:
        sha = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT
        )
        row = {
            "date": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "commit": sha.stdout.strip(),
            "metric": "layout_inferred",
            "value": round(ratio, 3),
            "slides": total,
        }
        with (ROOT / "bench" / "history.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
