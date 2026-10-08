"""``h=`` / ``y=`` / ``w=`` on the ``.kpi`` cards of one row: the row takes them (design wave 3, DL2).

``## 売上高 {.kpi .hero h=55% y=24% w=40%}``: the cards keep their columns; the row is as tall as the largest
``h=`` given (a share of the body), starts at ``y=`` (a share of the body, measured from its top), and a card
with ``w=`` takes that width (the others share what is left). An ``x=`` on a card still makes it absolute.
Pure geometry: lengths are resolved by the caller (``to_len`` returns EMU or None for a bad value).
"""

from __future__ import annotations

from collections.abc import Callable

from ..ir import Container
from .grid import Rect


def is_kpi(el) -> bool:
    return isinstance(el, Container) and "kpi" in el.classes


def pinned(el) -> bool:
    """A KPI card carrying ``h`` / ``y`` / ``w`` (and no ``x``: that one is positioned absolutely)."""
    b = getattr(el, "box", None)
    return is_kpi(el) and b is not None and b.x is None and any(v is not None for v in (b.y, b.w, b.h))


def any_pinned(elements) -> bool:
    """A pinned KPI card in a body whose boxes are all KPI cards (a row the author can place).

    A card beside other boxes is not a row: its ``y`` has no effect there and the sparse passes stay on."""
    boxes = [e for e in elements if isinstance(e, Container)]
    return any(pinned(e) for e in boxes) and all(is_kpi(e) for e in boxes)


def pin_row(
    cells: list[Rect],
    blocks: list,
    area: Rect,
    gap: int,
    to_len: Callable[[object, int, object], int | None],
    min_share: float,
) -> list[Rect] | None:
    """The row's cells with the cards' ``w`` / ``h`` / ``y`` applied; ``None`` = nothing pinned.

    ``area`` is the body: ``h`` and ``y`` are shares of its height, ``w`` of its width."""
    n = len(blocks)
    if n == 0 or len(cells) != n or not all(is_kpi(b) for b in blocks) or not any(pinned(b) for b in blocks):
        return None
    boxes = [b.box for b in blocks]

    def lens(key: str, ref: int, floor: int) -> list[int | None]:
        vals = [
            to_len(getattr(bx, key), ref, b) if bx is not None and getattr(bx, key) is not None else None
            for bx, b in zip(boxes, blocks, strict=True)
        ]
        return [v if v is not None and v >= floor else None for v in vals]

    ws, hs, ys = (
        lens("w", area.w, 1),
        lens("h", area.h, 1),
        lens("y", area.h, 0),
    )  # y = 0: the top of the body
    out = list(cells)
    if any(w is not None for w in ws):
        avail = max(area.w - gap * (n - 1), n)
        given = sum(w for w in ws if w is not None)
        free = [i for i, w in enumerate(ws) if w is None]
        floor = round(min_share * avail / n)
        each = max(round((avail - given) / len(free)), floor) if free else 0
        widths = [w if w is not None else each for w in ws]
        total = sum(widths)
        if total > avail:  # more than the row holds: every card shrinks alike
            widths = [max(round(w * avail / total), 1) for w in widths]
        x = cells[0].x
        for i, w in enumerate(widths):
            out[i] = Rect(x, out[i].y, w, out[i].h)
            x += w + gap
    h_given = [h for h in hs if h is not None]
    y_given = next((y for y in ys if y is not None), None)
    top = area.y + y_given if y_given is not None else cells[0].y
    top = min(max(top, area.y), area.bottom - 1)
    height = max(h_given) if h_given else cells[0].h
    height = max(min(height, area.bottom - top), 1)
    return [Rect(r.x, top, r.w, height) for r in out]
