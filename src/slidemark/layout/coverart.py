"""Cover art: a decorative motif of native shapes on the right part of a cover (``cover.art=network``).

Tokens (``theme.py``): ``cover.art`` = ``network`` | ``dots`` | ``rings`` | ``none`` (the default),
``cover.art.color`` (default ``secondary``), ``cover.art.opacity``, ``cover.art.seed`` (the same seed draws
the same motif), ``cover.art.split`` (the title keeps this share of the slide width, the motif the rest).
Sizes: ``layout.cover_art_*``. One node is drawn in ``accent``.

* ``network``  8..12 dots (``layout.cover_art_nodes``) joined by thin lines, like a graph: a jittered grid,
  the lines are the shortest spanning tree plus a few short extra edges;
* ``dots``     a grid of small discs that fades out towards the title;
* ``rings``    three concentric thin circles with one dot on a ring.

Every shape is named ``Cover art N`` (the importer drops them and writes the token back). A pure function of
the theme and the slide size: it returns ``(shape, rect, style)`` triples, the engine places them behind the
title. Never raises: an unusable colour falls back to ``primary``.
"""

from __future__ import annotations

import math
import random

from ..ir import Shape, Style
from ..theme import LayoutTokens, Theme
from .grid import Rect

KINDS = ("network", "dots", "rings")
_PT = 12700  # EMU per pt


def wanted(theme: Theme) -> bool:
    """Is a motif asked for (``cover.art`` is not ``none``)?"""
    return theme.cover_art in KINDS


def _color(theme: Theme, name: str | None, fallback: str) -> str:
    """A colour word of the palette (or ``#hex``); an unknown theme name falls back."""
    if not name:
        return fallback
    return name if name.startswith("#") or name in theme.colors else fallback


def art(theme: Theme, lt: LayoutTokens, W: int, H: int, x0: int) -> list[tuple[Shape, Rect, Style]]:
    """The shapes of the motif in the area right of ``x0`` (EMU), top to bottom behind the title."""
    kind = theme.cover_art
    if kind not in KINDS:
        return []
    mx = round(W * lt.cover_art_margin)
    my = round(H * 0.08)
    area = Rect(x0 + mx // 2, my, max(W - mx - (x0 + mx // 2), 1), max(H - 2 * my, 1))
    if area.w < W * 0.12:  # no room beside the title
        return []
    col = _color(theme, theme.cover_art_color, _color(theme, "secondary", "primary"))
    acc = _color(theme, "accent", col)
    rng = random.Random(theme.cover_art_seed)
    opacity = min(max(theme.cover_art_opacity, 0.05), 1.0)
    maker = {"network": _network, "dots": _dots, "rings": _rings}[kind]
    out: list[tuple[Shape, Rect, Style]] = []
    maker(out, area, col, acc, opacity, rng, lt)
    for n, (shape, _r, _s) in enumerate(out, 1):
        shape.attrs["shape_name"] = f"Cover art {n}"
    return out


def _disc(out, cx: float, cy: float, d: float, fill: str, opacity: float) -> None:
    d = max(round(d), 1)
    out.append(
        (
            Shape(shape="ellipse", attrs={}),
            Rect(round(cx - d / 2), round(cy - d / 2), d, d),
            Style(fill=fill, line=None, opacity=opacity if opacity < 1 else None),
        )
    )


def _line(out, p: tuple[float, float], q: tuple[float, float], color: str, opacity: float, pt: float) -> None:
    (x0, y0), (x1, y1) = (p, q) if p[1] <= q[1] else (q, p)  # drawn from the upper end down
    attrs: dict = {"line_alpha": opacity}
    if x1 < x0:
        attrs["flip_h"] = True
    out.append(
        (
            Shape(shape="line", attrs=attrs),
            Rect(round(min(x0, x1)), round(y0), round(abs(x1 - x0)), round(y1 - y0)),
            Style(line=color, line_width=pt),
        )
    )


def _network(
    out, area: Rect, col: str, acc: str, opacity: float, rng: random.Random, lt: LayoutTokens
) -> None:
    n = min(max(int(lt.cover_art_nodes), 8), 12)
    cols, rows = (3, 4) if area.h >= area.w else (4, 3)
    cells = [(c, r) for r in range(rows) for c in range(cols)]
    rng.shuffle(cells)
    cells = sorted(cells[:n])
    cw, ch = area.w / cols, area.h / rows
    pts = [
        (area.x + (c + rng.uniform(0.22, 0.78)) * cw, area.y + (r + rng.uniform(0.22, 0.78)) * ch)
        for c, r in cells
    ]
    side = min(area.w, area.h)
    base = lt.cover_art_node_ratio * side
    sizes = [base * rng.uniform(0.55, 1.2) for _ in pts]
    # the accent node: the one nearest the middle of the motif
    mid = (area.x + area.w * 0.5, area.y + area.h * 0.45)
    hub = min(range(n), key=lambda i: math.dist(pts[i], mid))
    sizes[hub] = base * 1.7
    # shortest spanning tree (Prim) + the few shortest remaining edges
    edges: set[tuple[int, int]] = set()
    seen = {hub}
    while len(seen) < n:
        i, j = min(
            ((a, b) for a in seen for b in range(n) if b not in seen),
            key=lambda e: math.dist(pts[e[0]], pts[e[1]]),
        )
        edges.add((min(i, j), max(i, j)))
        seen.add(j)
    rest = sorted(
        ((a, b) for a in range(n) for b in range(a + 1, n) if (a, b) not in edges),
        key=lambda e: math.dist(pts[e[0]], pts[e[1]]),
    )
    edges.update(rest[: max(n // 3, 1)])
    pt = lt.cover_art_line_pt
    for a, b in sorted(edges):
        _line(out, pts[a], pts[b], col, opacity, pt)
    for i, (x, y) in enumerate(pts):
        if i != hub:
            _disc(out, x, y, sizes[i], col, min(opacity * 1.6, 1.0))
    _disc(out, pts[hub][0], pts[hub][1], sizes[hub], acc, 1.0)


def _dots(out, area: Rect, col: str, acc: str, opacity: float, rng: random.Random, lt: LayoutTokens) -> None:
    cols = 8
    cell = area.w / cols
    rows = max(int(area.h // cell), 2)
    oy = area.y + (area.h - rows * cell) / 2
    d = cell * 0.34
    pick = (rng.randrange(cols // 2, cols), rng.randrange(rows))
    for r in range(rows):
        for c in range(cols):
            t = (c + 1) / cols  # 1 at the right edge, fading towards the title
            op = opacity * t**1.4
            x, y = area.x + (c + 0.5) * cell, oy + (r + 0.5) * cell
            if (c, r) == pick:
                _disc(out, x, y, d * 1.9, acc, 1.0)
            elif op >= 0.06:
                _disc(out, x, y, d * (0.55 + 0.45 * t), col, op)


def _rings(out, area: Rect, col: str, acc: str, opacity: float, rng: random.Random, lt: LayoutTokens) -> None:
    side = min(area.w, area.h)
    cx, cy = area.x + area.w * 0.55, area.y + area.h * 0.5
    radii = [side * 0.5, side * 0.35, side * 0.2]
    pt = lt.cover_art_line_pt
    for r in radii:
        d = round(2 * r)
        out.append(
            (
                Shape(shape="ellipse", attrs={"line_alpha": opacity}),
                Rect(round(cx - r), round(cy - r), d, d),
                Style(fill=None, line=col, line_width=pt * 1.2),
            )
        )
    ang = rng.uniform(-math.pi / 3, math.pi / 3)
    r = radii[1]
    _disc(out, cx + r * math.cos(ang), cy + r * math.sin(ang), lt.cover_art_node_ratio * side * 1.7, acc, 1.0)
