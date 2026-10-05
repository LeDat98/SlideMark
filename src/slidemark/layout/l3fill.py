"""L3 fill: text cards and text panels use the height they have (token driven, geometry only).

Two cases, both applied to the finished placed items of a content slide body:

* ``fill_row``: a sparse slide (the completion ran) whose body is ONE row of text cards. The row stays
  top-anchored right under the lead; the cards share one height that reaches down to
  ``layout.sparse_row_bottom_band`` of the body above its bottom; inside each card the paragraphs spread with
  even gaps (at most ``layout.l3_gap_extra`` em more per gap, ``l3_gap_extra_numbered`` for numbered lists).
  When the cap is hit the rest stays at the bottom of the card (text is never centered).
* ``fill_panels``: a text card beside a chart / image whose content fills less than
  ``layout.panel_fill_min`` of its height: paragraphs spread the same way and a trailing note / callout
  anchors to the card bottom.

Explicit author input wins: a ``{h=}`` box, a vertical alignment, ``@free`` (never reaches here) and
``layout.body_valign=top`` leave everything as it is. Never raises: anything unexpected returns the items
unchanged.
"""

from __future__ import annotations

from ..ir import Chart, Container, Image, Media, Placed, Text
from ..theme import LayoutTokens
from ..units import EMU_PER_PT, to_emu
from . import measure
from .grid import Rect
from .vfill import _contains

_HEAD_ROLES = {"title", "subtitle", "lead", "conclusion", "caption", "footnote"}


def _pad(p: Placed, card: Placed) -> int:
    """Inner inset of a card: the horizontal gap between the card edge and its text."""
    return max(0, min(p.x - card.x, to_emu("0.15in")))


def _is_note(p: Placed) -> bool:
    return "callout" in p.element.classes or bool(p.style.fill or p.style.line)


def _explicit(p: Placed) -> bool:
    if p.element.box is not None:
        return True
    return p.style.valign not in (None, "top") and not _is_note(p)


def _inner_texts(card: Placed, out: list[Placed]) -> list[Placed] | None:
    """The placed texts inside ``card``; ``None`` when it holds anything else (nested cards, tables ...)."""
    inner = [p for p in out if p is not card and _contains(card, p)]
    if not inner or any(not isinstance(p.element, Text) for p in inner):
        return None
    return inner


def _spread(p: Placed, avail: int, lt: LayoutTokens, pad: int) -> Placed:
    """Paragraph gaps of ``p`` grow (capped) so its text spans ``avail`` EMU; ``p.h`` becomes ``avail``."""
    paras = p.element.paragraphs
    p = p.model_copy(update={"h": avail})
    n = len(paras)
    if n < 2:
        return p
    g0 = measure.element_gap(p.element)
    g0 = measure.para_gap() if g0 is None else g0
    width = p.w - 2 * pad
    need = measure.paragraphs_height(paras, width, p.style, p.font_scale, gap=g0)
    free = avail - 2 * pad - need
    size = (p.style.font_size or 18) * p.font_scale * EMU_PER_PT
    if free <= 0 or size <= 0:
        return p
    cap = lt.l3_gap_extra_numbered if paras[0].marker == "number" else lt.l3_gap_extra
    extra = min(max(cap, 0.0), free / ((n - 1) * size))
    for _ in range(10):  # the estimate carries a safety factor: shrink until it surely fits
        if extra <= 0.01 or measure.paragraphs_height(
            paras, width, p.style, p.font_scale, gap=g0 + extra
        ) <= (avail - 2 * pad):
            break
        extra *= 0.9
    if extra <= 0.01:
        return p
    return p.model_copy(
        update={
            "element": p.element.model_copy(
                update={"attrs": {**p.element.attrs, "para_gap": round(g0 + extra, 3)}}
            )
        }
    )


def _fill_card(
    card: Placed, inner: list[Placed], top: int, bottom: int, lt: LayoutTokens
) -> dict[int, Placed] | None:
    """New geometry of ``card`` and its texts for the box ``top..bottom``; ``None`` = leave it alone."""
    dy = top - card.y
    heads = [p for p in inner if p.element.role == "heading"]
    notes = [p for p in inner if p.element.role != "heading" and _is_note(p)]
    mains = [p for p in inner if p not in heads and p not in notes]
    kpi = "kpi" in card.element.classes  # a KPI value stays centred in its (taller) card, no spread
    if len(mains) != 1 or any(_explicit(p) and not (kpi and p is mains[0]) for p in (card, *inner)):
        return None
    main = mains[0]
    pad = _pad(main, card)
    res: dict[int, Placed] = {id(card): card.model_copy(update={"y": top, "h": bottom - top})}
    for p in heads:
        res[id(p)] = p.model_copy(update={"y": p.y + dy})
    floor = bottom - pad
    for p in sorted(notes, key=lambda q: -q.y):  # the last note sits on the bottom, the others stack above
        y = floor - p.h
        res[id(p)] = p.model_copy(update={"y": y})
        floor = y - pad
    m = main.model_copy(update={"y": main.y + dy})
    avail = floor - m.y
    if avail < main.h - 2:  # never squeeze the text
        return None
    res[id(main)] = m.model_copy(update={"h": avail}) if kpi else _spread(m, avail, lt, pad)
    return res


def _apply(out: list[Placed], res: dict[int, Placed]) -> list[Placed]:
    return [res.get(id(p), p) for p in out]


def _body_items(out: list[Placed], body: Rect) -> list[Placed]:
    return [
        p
        for p in out
        if p.y >= body.y - 2
        and p.y + p.h <= body.bottom + 2
        and getattr(p.element, "role", None) not in _HEAD_ROLES
    ]


def fill_row(out: list[Placed], body: Rect, lt: LayoutTokens, consulting: bool = True) -> list[Placed]:
    """A sparse slide of one row of text cards: top-anchored, equal tall cards, spread paragraphs."""
    try:
        return _fill_row(out, body, lt, consulting)
    except Exception:  # never raise on bad input
        return out


def _fill_row(out: list[Placed], body: Rect, lt: LayoutTokens, consulting: bool) -> list[Placed]:
    if not lt.l3_fill or lt.body_valign == "top" or body.h <= 0:
        return out
    items = _body_items(out, body)
    cards = [p for p in items if isinstance(p.element, Container)]
    if not cards or any(isinstance(p.element, (Chart, Image, Media)) for p in items):
        return out
    if not consulting and not all("kpi" in c.element.classes for c in cards):
        return out  # normal-density themes keep their hugging cards (only KPI rows are top-anchored)
    plan: dict[int, list[Placed]] = {}
    for c in cards:
        inner = _inner_texts(c, items)
        if inner is None:
            return out
        plan[id(c)] = inner
    covered = {id(p) for ps in plan.values() for p in ps} | set(plan)
    if any(id(p) not in covered for p in items):  # free text / tables / shapes next to the cards
        return out
    if min(c.y + c.h for c in cards) <= max(c.y for c in cards):  # not one row
        return out
    top = body.y
    bottom = body.bottom - round(lt.sparse_row_bottom_band * body.h)
    if bottom - top < max(c.h for c in cards) or any(c.y < top for c in cards):
        return out
    res: dict[int, Placed] = {}
    for c in cards:
        r = _fill_card(c, plan[id(c)], top, bottom, lt)
        if r is None:
            return out  # one card refuses: the row stays as it was
        res.update(r)
    return _apply(out, res)


def _fill_share(card: Placed, inner: list[Placed]) -> float:
    from .engine import _text_h

    return (max(p.y + _text_h(p) for p in inner) - card.y) / max(card.h, 1)


def fill_panels(out: list[Placed], body: Rect, lt: LayoutTokens) -> list[Placed]:
    """Text panels beside a chart / image: spread paragraphs, anchor the trailing note to the panel bottom."""
    try:
        return _fill_panels(out, body, lt)
    except Exception:  # never raise on bad input
        return out


def _fill_panels(out: list[Placed], body: Rect, lt: LayoutTokens) -> list[Placed]:
    if not lt.l3_fill or lt.body_valign == "top" or body.h <= 0:
        return out
    items = _body_items(out, body)
    if not any(isinstance(p.element, (Chart, Image, Media)) for p in items):
        return out
    res: dict[int, Placed] = {}
    visual_h = max(p.h for p in items if isinstance(p.element, (Chart, Image, Media)))
    for c in (p for p in items if isinstance(p.element, Container)):
        inner = _inner_texts(c, items)
        if inner is None or c.h < visual_h * 0.9 or _fill_share(c, inner) >= lt.panel_fill_min:
            continue
        r = _fill_card(c, inner, c.y, c.y + c.h, lt)
        if r is not None:
            res.update(r)
    return _apply(out, res) if res else out
