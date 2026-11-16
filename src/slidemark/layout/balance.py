"""Card groups without dead space (``layout.card_balance``; rubric G-05).

A group of text cards alone on the slide ends up with one of two faults after the growth passes: the cards are
stretched and each is half empty, or the group is a modest block with bands above and below. This final pass:

* grows the text of the cards (one common factor, never past ``layout.grow_max`` or ``card_fill_text_max_pt``,
  explicit sizes stay) while the hugged group stays within ``card_group_aim`` of the body;
* shrinks every card to its content (all equal, rows keep their gap): as tall as its content plus its
  own top inset;
* centres the group in the body (``card_balance_top`` of the leftover above it).

It only acts when a card is hollow (its content ends before ``card_min_fill`` of its height) or the group is
shorter than ``card_group_min`` of the body; nothing else is on the slide (no bar, table, chart, loose text),
the cards form a regular grid (equal heights) and hold only texts and shapes. Never raises: anything
unexpected returns the items unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..ir import Container, Placed, Shape, Text
from ..theme import LayoutTokens
from ..units import to_emu
from . import measure
from .grid import Rect
from .l3fill import _body_items, _card_rows, _text_need, _text_pad
from .vfill import _contains

_SKIP_CLASSES = {"kpi", "steps-card", "diagram", "flow", "chevron", "tree"}
_FIXED_CLASSES = {"num", "kpi", "caption", "note", "callout", "eyebrow"}


@dataclass
class _Band:
    members: list[Placed]
    y0: int
    y1: int


def balance(out: list[Placed], body: Rect, lt: LayoutTokens, explicit=None) -> list[Placed]:
    """``explicit(text)`` says the author sized that text (pinned token, CSS, ``{size=}``): it never grows."""
    try:
        return _balance(out, body, lt, explicit)
    except Exception:
        return out


def _text_ink(p: Placed) -> int:
    """Visible height of a placed text (its lines, at most its box)."""
    pad = _text_pad(p)
    gap = measure.element_gap(p.element)
    need = measure.paragraphs_height(p.element.paragraphs, p.w - 2 * pad, p.style, p.font_scale, gap=gap)
    return min(p.h, round(need) + 2 * pad)


def _extent(p: Placed) -> tuple[int, int]:
    return (p.y, p.y + (_text_ink(p) if isinstance(p.element, Text) else p.h))


def _bands(inner: list[Placed]) -> list[_Band]:
    bands: list[_Band] = []
    for p in sorted(inner, key=lambda q: (q.y, q.x)):
        y0, y1 = _extent(p)
        if bands and y0 < bands[-1].y1 - 1:
            b = bands[-1]
            b.members.append(p)
            b.y1 = max(b.y1, y1)
        else:
            bands.append(_Band([p], y0, y1))
    return bands


class _Scale:
    """Growth of the texts of one card group: one factor ``s``, each text within its own ceiling.

    Headings never take a new wrapped line (and share their factor); a body text stays within
    ``card_balance_body_head`` x the grown heading; explicit sizes, numbers, captions, notes keep theirs."""

    def __init__(self, texts: list[Placed], lt: LayoutTokens, explicit) -> None:
        self.lt, self.explicit = lt, explicit
        self.heads = [p for p in texts if p.element.role == "heading" and not self._fixed(p)]
        self.head_pt = min(((p.style.font_size or 18) * p.font_scale for p in self.heads), default=0.0)
        self.hcap = 1.0
        if self.heads and lt.grow and lt.grow_max > 1.0:
            cap = min(self._ceiling(p) for p in self.heads)
            step = max(lt.l3_grow_step, 0.01)
            k = 1.0
            while k + step <= cap + 1e-9 and all(
                _text_need(p, k + step, lt, False) <= _text_need(p, 1.0, lt, False) for p in self.heads
            ):
                k += step
            self.hcap = k

    def _fixed(self, p: Placed) -> bool:
        el = p.element
        if getattr(getattr(el, "style", None), "font_size", None) or (self.explicit and self.explicit(el)):
            return True
        return bool(_FIXED_CLASSES & set(el.classes))

    def _ceiling(self, p: Placed) -> float:
        base = p.style.font_size or 18
        return measure.grow_cap(self.lt, base, base * p.font_scale, self.lt.card_fill_text_max_pt)

    def of(self, p: Placed, s: float) -> float:
        lt = self.lt
        if not lt.grow or lt.grow_max <= 1.0 or self._fixed(p) or p.element.role not in ("heading", "body"):
            return 1.0
        if p.element.role == "heading":
            return min(s, self.hcap, self._ceiling(p))
        k = min(s, self._ceiling(p))
        if self.head_pt:
            cur = (p.style.font_size or 18) * p.font_scale
            limit = lt.card_balance_body_head * self.head_pt * min(s, self.hcap) / max(cur, 1e-6)
            k = min(k, max(limit, 1.0))
        return max(k, 1.0)


def _band_h(band: _Band, s: float, g: _Scale) -> int:
    h = 0
    for p in band.members:
        if isinstance(p.element, Text):
            k = g.of(p, s)
            h = max(h, _text_need(p, k, g.lt, True) if k > 1.0 else _text_ink(p))
        else:
            h = max(h, p.h)
    return h


def _heights(plans: dict, cards: list[Placed], s: float, g: _Scale) -> dict[int, list[int]]:
    """Band heights per card at growth ``s``; cards with the same bands share them (headings line up)."""
    hs = {id(c): [_band_h(b, s, g) for b in plans[id(c)][0]] for c in cards}
    if len({len(v) for v in hs.values()}) == 1:
        top = [max(col) for col in zip(*hs.values(), strict=True)]
        hs = {k: list(top) for k in hs}
    return hs


def _need(plan: tuple, heights: list[int], s: float) -> int:
    _bands_, inset, gaps = plan
    return inset + sum(heights) + round(sum(gaps) * s) + inset


def _balance(out: list[Placed], body: Rect, lt: LayoutTokens, explicit=None) -> list[Placed]:
    if not lt.card_balance or body.h <= 0:
        return out
    items = _body_items(out, body)
    boxes = [p for p in items if isinstance(p.element, Container)]
    cards = [p for p in boxes if not any(q is not p and _contains(q, p) for q in boxes)]
    if len(cards) < 2 or len(cards) > 12:
        return out
    if any((_SKIP_CLASSES & set(c.element.classes)) or getattr(c.element, "box", None) for c in cards):
        return out
    tol = to_emu("0.03in")
    if max(c.h for c in cards) - min(c.h for c in cards) > tol:
        return out  # not a regular grid (a card spans rows, or the rows differ): the layout keeps its shape
    inner: dict[int, list[Placed]] = {}
    for c in cards:
        inn = [p for p in items if p is not c and _contains(c, p)]
        if not inn or any(not isinstance(p.element, (Text, Shape)) for p in inn):
            return out
        if any(getattr(p.element, "box", None) for p in inn):
            return out
        inner[id(c)] = inn
    owned = {id(p) for v in inner.values() for p in v} | {id(c) for c in cards}
    if any(id(p) not in owned for p in items):
        return out  # a table, chart, arrow or loose text shares the body
    rows = _card_rows(cards)
    if any(max(c.y for c in r) - min(c.y for c in r) > tol for r in rows):
        return out
    gaps_v = [min(q.y for q in rows[i + 1]) - max(q.y + q.h for q in rows[i]) for i in range(len(rows) - 1)]
    if any(gp < 0 for gp in gaps_v):
        return out
    gap = min(gaps_v, default=0)
    plans = {}
    for c in cards:
        bands = _bands(inner[id(c)])
        inset = max(bands[0].y0 - c.y, 0)
        gs = [max(b.y0 - a.y1, 0) for a, b in zip(bands, bands[1:], strict=False)]
        plans[id(c)] = (bands, inset, gs)
    g = _Scale([p for c in cards for p in inner[id(c)] if isinstance(p.element, Text)], lt, explicit)
    top0 = min(c.y for c in cards)
    group_h = max(c.y + c.h for c in cards) - top0
    h1 = _heights(plans, cards, 1.0, g)
    n1 = {id(c): _need(plans[id(c)], h1[id(c)], 1.0) for c in cards}
    hollow = min(n1[id(c)] / max(c.h, 1) for c in cards) < lt.card_min_fill
    sparse = group_h < lt.card_group_min * body.h
    if not hollow and not sparse:
        return out
    nrows = len(rows)
    aim = lt.card_group_aim * body.h

    def group_at(s: float) -> int:
        hs = _heights(plans, cards, s, g)
        return nrows * max(_need(plans[id(c)], hs[id(c)], s) for c in cards) + gap * (nrows - 1)

    s_top = max(
        (g.of(p, 10.0) for c in cards for p in inner[id(c)] if isinstance(p.element, Text)), default=1.0
    )
    step = max(lt.l3_grow_step, 0.01)
    best, k = 1.0, 1
    while group_at(1.0) <= aim:
        s = min(1.0 + k * step, s_top)
        if s <= best + 1e-9 or group_at(s) > aim:
            break
        best, k = s, k + 1
    hbest = _heights(plans, cards, best, g)
    h = max(_need(plans[id(c)], hbest[id(c)], best) for c in cards)
    total = nrows * h + gap * (nrows - 1)
    if total > body.h:
        return out
    top = body.y + round((body.h - total) * lt.card_balance_top)
    if best == 1.0 and abs(h - max(c.h for c in cards)) < 2 and abs(top - top0) < 2:
        return out
    res: dict[int, Placed] = {}
    for r, row in enumerate(rows):
        row_top = top + r * (h + gap)
        for c in row:
            bands, inset, gs = plans[id(c)]
            res[id(c)] = c.model_copy(update={"y": row_top, "h": h})
            y = row_top + inset
            for bi, band in enumerate(bands):
                bh = hbest[id(c)][bi]
                shapes = [p for p in band.members if not isinstance(p.element, Text)]
                anchor = max(shapes, key=lambda q: q.h) if shapes else None
                for p in band.members:
                    if isinstance(p.element, Text):
                        k = g.of(p, best)
                        res[id(p)] = p.model_copy(
                            update={
                                "y": y,
                                "h": bh if len(band.members) > 1 else _text_need(p, k, lt, False),
                                "font_scale": round(p.font_scale * k, 4),
                            }
                        )
                    elif anchor is not None:  # shapes keep their place relative to the band's largest shape
                        res[id(p)] = p.model_copy(update={"y": y + (bh - anchor.h) // 2 + (p.y - anchor.y)})
                y += bh + (round(gs[bi] * best) if bi < len(gs) else 0)
    # text boxes that stayed taller than their lines (the old stretch) end inside their card
    for c in cards:
        card = res[id(c)]
        for p in inner[id(c)]:
            q = res[id(p)]
            if q.y + q.h > card.y + card.h:
                res[id(p)] = q.model_copy(update={"h": max(card.y + card.h - q.y, 1)})
    return [res.get(id(p), p) for p in out]
