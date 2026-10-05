"""Consulting-grade metric: how much of each card and each slide body is empty.

For every box card on every example slide, fill = (text height of the items inside the card) / (card height).
A card below 35% fill is "sparse" (the 01-basics slide 3 defect). Lower sparse counts are better.

Usage: python bench/whitespace.py [--verbose]
"""

from __future__ import annotations

import sys
from pathlib import Path

from slidemark.ir import Container, Placed
from slidemark.layout import layout_slide, measure
from slidemark.parser import parse
from slidemark.template import resolve_theme
from slidemark.units import to_emu

ROOT = Path(__file__).resolve().parent.parent
SPARSE = 0.35


def _content_height(p: Placed) -> float:
    paras = getattr(p.element, "paragraphs", None)
    if not paras:
        return p.h  # visuals (charts, tables, images) fill their box
    pad = 0
    if p.style.padding is not None:
        try:
            pad = to_emu(p.style.padding)
        except ValueError:
            pad = 0
    return min(p.h, measure.paragraphs_height(paras, p.w - 2 * pad, p.style, p.font_scale) + 2 * pad)


def _inside(a: Placed, b: Placed) -> bool:
    return a.x >= b.x - 2 and a.y >= b.y - 2 and a.x + a.w <= b.x + b.w + 2 and a.y + a.h <= b.y + b.h + 2


def card_fills(items: list[Placed]) -> list[tuple[str, float]]:
    out = []
    for c in items:
        if not isinstance(c.element, Container) or c.h <= 0 or "plain" in c.element.classes:
            continue
        inner = [p for p in items if p is not c and _inside(p, c) and not isinstance(p.element, Container)]
        if not inner:
            continue
        used = sum(_content_height(p) for p in inner)
        title = c.element.title.paragraphs[0].plain if c.element.title and c.element.title.paragraphs else "?"
        out.append((title, min(used / c.h, 1.0)))
    return out


def main() -> int:
    verbose = "--verbose" in sys.argv
    cards = sparse = 0
    fills: list[float] = []
    for md in sorted((ROOT / "examples").glob("*.md")):
        deck = parse(md.read_text(encoding="utf-8"))
        theme, _ = resolve_theme(deck.theme, md.parent)
        for i, s in enumerate(deck.slides):
            for title, fill in card_fills(layout_slide(s, deck, theme, i)):
                cards += 1
                fills.append(fill)
                if fill < SPARSE:
                    sparse += 1
                    if verbose:
                        print(f"  sparse {fill:4.0%}  {md.stem} slide {i + 1}: {title}")
    mean = sum(fills) / len(fills) if fills else 0
    print(f"cards {cards}, sparse (<{SPARSE:.0%} filled) {sparse}, mean fill {mean:.0%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
