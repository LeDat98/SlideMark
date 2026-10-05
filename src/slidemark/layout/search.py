"""Candidate arrangements for the automatic layout search (L7): grid tokens an author could write.

``alternatives`` lists, for the blocks of a slide without a grid token, a few other arrangements than the
rule-based one (<= ``MAX_ALTERNATIVES``). Each is a plain `@` token (``2x2``, ``1:2``, ``aab/aac``) so
the engine can lay it out with the normal grid code and the author can pin it by writing the same token.
Pure and deterministic: no layout, no measuring.
"""

from __future__ import annotations

import math

from ..ir import Chart, Code, Image, Media, Table, Text

MAX_ALTERNATIVES = 5  # plus the rule-based choice = at most 6 candidates per slide
HEAVY = 2.0  # a block is "heavy" when it carries at least this many times the text of every other block
_VISUALS = (Image, Media, Chart, Table, Code)
_SKIP_CLASSES = {"kpi", "group", "diagram", "flow", "chevron"}


def _letter(i: int) -> str:
    return chr(97 + i)


def alternatives(blocks: list, weights: list[float], *, tail: bool) -> list[str]:
    """Grid tokens to try besides the rule's choice for ``blocks`` (the grid cells, source order).

    ``weights`` are the text lengths (visuals huge). ``tail`` means more blocks follow the grid full width,
    so equal grids are written ``CxR`` (the leftovers then stack below instead of becoming cells).
    """
    n = len(blocks)
    if n < 2 or n > 12 or len(weights) != n:
        return []
    if any(_SKIP_CLASSES & set(getattr(b, "classes", [])) for b in blocks):
        return []
    out: list[str] = []

    def add(tok: str) -> None:
        if tok not in out:
            out.append(tok)

    def grid(cols: int) -> str:
        cols = max(1, min(cols, n))
        rows = math.ceil(n / cols)
        return f"{cols}x{rows}" if tail or (cols > 1 and rows > 1) else str(cols)

    heavy = max(range(n), key=lambda i: weights[i])
    others = [i for i in range(n) if i != heavy]
    is_heavy = all(weights[heavy] >= HEAVY * weights[i] for i in others)
    if n == 2:
        text_visual = (
            sum(isinstance(b, Text) for b in blocks) == 1
            and sum(isinstance(b, _VISUALS) for b in blocks) == 1
        )
        if text_visual and isinstance(blocks[0], Text):
            for tok in ("1:1", "1:2", "2:1"):
                add(tok)
            add("1")  # the visual below the text
        elif text_visual:
            add("b/a")  # the text above the visual (source order is visual first)
        else:
            for tok in ("1:2", "2:1"):
                add(tok)
            add("1")
    elif n == 3:
        h, (o0, o1) = _letter(heavy), (_letter(i) for i in others)
        add(grid(3))
        add(f"{h}{h}{o0}/{h}{h}{o1}")  # the heavy block left, two stacked right
        add(f"{h}{h}/{o0}{o1}")  # the heavy block on top, two below
        add(f"{o0}{o1}/{h}{h}")  # two on top, the heavy block below
        add("1")
    elif n == 4:
        add(grid(4))
        add(grid(2))
        if is_heavy:
            h = _letter(heavy)
            o = [_letter(i) for i in others]
            add("/".join(f"{h}{h}{x}" for x in o))
        add(grid(1) if tail else "1")
    else:
        for cols in (math.ceil(n / 2), 3, 2, n if n <= 6 else 4, 4):
            add(grid(cols))
    return out[:MAX_ALTERNATIVES]
