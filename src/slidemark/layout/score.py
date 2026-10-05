"""Cheap scorer for the automatic layout search: lower is better, ``HARD`` terms reject a candidate.

It judges the final ``Placed`` items of one candidate arrangement with the same measurement lint uses:

- hard penalties: an overflowing block (``over``) or text below the theme minimum size (critique's
  ``design-too-many-blocks`` threshold);
- soft penalties (same thresholds as ``critique.py``, kept here so layout never imports it): the smallest
  font scale, sparse cards (< ``SPARSE_FILL`` filled), uneven or low card fill, a card row whose tallest
  content is >= ``UNBALANCED`` x the shortest, an empty band at the bottom, a chart / picture squashed far
  from a sensible aspect.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass

from ..ir import Chart, Container, Image, Media, Placed, Text
from ..theme import DEFAULT_SIZES, Theme
from ..units import EMU_PER_PT
from . import css, measure
from .grid import Rect

HARD_OVER = 1000.0  # per overflowing block
HARD_TINY = 500.0  # per text block below the theme minimum font size
SPARSE_FILL = 0.30  # a card filled less than this is "sparse" (critique)
UNBALANCED = 3.0  # tallest / shortest natural content of a card row (critique)
EMPTY_OK = 0.35  # share of the body that may stay empty at the bottom for free (critique: info from 30%)
WIDTH_TARGET = 0.45  # a card's longest text line should span this share of its inner width
FILL_TARGET = 0.55  # mean card fill below this costs
ASPECT_OK = (1.0, 2.8)  # chart width / height that looks right; beyond it the chart is squashed
ASPECT_OK_PICTURE = (0.6, 3.4)

W_SCALE = 25.0  # x (1 - smallest font scale)
W_SPARSE = 3.0  # per sparse card
W_SPREAD = 6.0  # x std-dev of the card fills
W_MEAN = 6.0  # x shortfall of the mean card fill
W_WIDTH = 12.0  # x shortfall of the mean horizontal fill (short lines in wide cards)
W_UNBALANCED = 3.0  # per unbalanced row
W_EMPTY = 14.0  # x empty share above EMPTY_OK
W_ASPECT = 6.0  # x log2 distance from the OK aspect range


@dataclass
class Score:
    total: float
    hard: float
    parts: dict[str, float]

    def __lt__(self, other: Score) -> bool:
        return self.total < other.total


def _pad(p: Placed) -> tuple[int, int]:
    """(horizontal, vertical) total insets of a placed item, CSS per-side padding and borders included."""
    return css.inset_hv(p.style)


def _natural(p: Placed, scale: float | None = None) -> float:
    paras = getattr(p.element, "paragraphs", None)
    if not paras:
        return p.h
    ph, pv = _pad(p)
    s = p.font_scale if scale is None else scale
    return measure.paragraphs_height(paras, p.w - ph, p.style, s, gap=measure.element_gap(p.element)) + pv


def _inside(a: Placed, b: Placed) -> bool:
    t = 2
    return a.x >= b.x - t and a.y >= b.y - t and a.x + a.w <= b.x + b.w + t and a.y + a.h <= b.y + b.h + t


def _cards(items: list[Placed]) -> list[tuple[Placed, list[Placed]]]:
    out = []
    for c in items:
        el = c.element
        if not isinstance(el, Container) or c.h <= 0 or "plain" in el.classes or "diagram" in el.classes:
            continue
        inner = [p for p in items if p is not c and _inside(p, c) and not isinstance(p.element, Container)]
        inner = [
            p
            for p in inner
            if getattr(p.element, "paragraphs", None) or isinstance(p.element, (Chart, Image, Media))
        ]
        if inner:
            out.append((c, inner))
    return out


def _width_fill(c: Placed, inner: list[Placed]) -> float | None:
    """Share of the card's inner width its longest (unwrapped) text line would take, at most 1."""
    best = None
    for p in inner:
        paras = getattr(p.element, "paragraphs", None)
        if not paras:
            continue
        size = (p.style.font_size or 18) * p.font_scale
        avail_em = max(p.w - _pad(p)[0], 1) / EMU_PER_PT / max(size, 1)
        longest = max(measure.text_em(q.plain) for q in paras)
        best = max(best or 0.0, min(1.0, longest / avail_em))
    return best


def _rows(cards: list[tuple[Placed, list[Placed]]]) -> list[list[tuple[Placed, list[Placed]]]]:
    tol = 4 * int(EMU_PER_PT)
    rows: list[list[tuple[Placed, list[Placed]]]] = []
    for card in sorted(cards, key=lambda c: (c[0].y, c[0].x)):
        for row in rows:
            if abs(row[0][0].y - card[0].y) <= tol:
                row.append(card)
                break
        else:
            rows.append([card])
    return [r for r in rows if len(r) >= 2]


def _aspect_penalty(p: Placed) -> float:
    if p.h <= 0 or p.w <= 0:
        return 0.0
    lo, hi = ASPECT_OK if isinstance(p.element, Chart) else ASPECT_OK_PICTURE
    a = p.w / p.h
    if a < lo:
        return W_ASPECT * math.log2(lo / a)
    if a > hi:
        return W_ASPECT * math.log2(a / hi)
    return 0.0


def score(items: list[Placed], body: Rect, theme: Theme, *, over: int = 0) -> Score:
    """Score the body items of one candidate layout (``over`` = number of overflowing blocks)."""
    parts: dict[str, float] = {}
    hard = HARD_OVER * over
    body_pt = theme.sizes.get("body", DEFAULT_SIZES["body"])
    texts = [p for p in items if isinstance(p.element, Text) and getattr(p.element, "paragraphs", None)]
    tiny = [p for p in texts if (p.style.font_size or body_pt) * p.font_scale < theme.min_font_size - 0.05]
    hard += HARD_TINY * len(tiny)
    scaled = [p.font_scale for p in items if getattr(p.element, "paragraphs", None) and p.font_scale > 0]
    if scaled:
        parts["scale"] = W_SCALE * max(0.0, 1.0 - min(scaled))
    cards = _cards(items)
    fills = [min(1.0, sum(min(c.h, _natural(p)) for p in inner) / c.h) for c, inner in cards]
    if fills:
        parts["sparse"] = W_SPARSE * sum(f < SPARSE_FILL for f in fills)
        if len(fills) > 1:
            parts["spread"] = W_SPREAD * statistics.pstdev(fills)
        parts["mean"] = W_MEAN * max(0.0, FILL_TARGET - statistics.fmean(fills))
    wf = [w for w in (_width_fill(c, inner) for c, inner in cards) if w is not None]
    if wf:
        parts["width"] = W_WIDTH * max(0.0, WIDTH_TARGET - statistics.fmean(wf))
    unbalanced = 0
    for row in _rows(cards):
        if any(
            "kpi" in c.element.classes or any(not getattr(p.element, "paragraphs", None) for p in inner)
            for c, inner in row
        ):
            continue
        nat = [sum(_natural(p, 1.0) for p in inner) for _c, inner in row]
        if min(nat) > 0 and max(nat) / min(nat) >= UNBALANCED:
            unbalanced += 1
    parts["unbalanced"] = W_UNBALANCED * unbalanced
    if items and body.h > 0:
        bottom = max(p.y + p.h for p in items)
        parts["empty"] = W_EMPTY * max(0.0, (body.bottom - bottom) / body.h - EMPTY_OK)
    parts["aspect"] = sum(_aspect_penalty(p) for p in items if isinstance(p.element, (Chart, Image, Media)))
    soft = sum(parts.values())
    return Score(total=hard + soft, hard=hard, parts=parts)
