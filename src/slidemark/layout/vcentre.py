"""Vertical rhythm of a content slide (``layout.vcentre``): hug the content, centre it, keep air below.

A token-driven final pass over the placed body items (no theme-specific code; editorial turns it on):

* a lone table keeps its columns as wide as their content (centred), rows at most ``vcentre_row_em`` x text;
* a row of text cards takes the height of its tallest content, never a stretched one (all cards equal);
* the block never reaches nearer than ``vcentre_gap`` to what sits under the body (footnote, footer):
  a chart / table / card that touched the bottom gives that much back;
* the block is centred in the free body: no empty band under the title while the bottom is crowded.

Never raises: anything unexpected returns the items unchanged.
"""

from __future__ import annotations

from ..ir import Chart, Container, Image, Media, Placed, Raw, Shape, Table, Text
from ..theme import LayoutTokens
from ..units import EMU_PER_PT, to_emu
from . import measure, tables
from .grid import Rect
from .l3fill import _body_items
from .vfill import _contains

_SKIP_CLASSES = {"diagram", "flow", "chevron", "kpi"}


def vcentre(out: list[Placed], body: Rect, lt: LayoutTokens) -> list[Placed]:
    try:
        return _vcentre(out, body, lt)
    except Exception:
        return out


def _roots(items: list[Placed]) -> list[Placed]:
    return [p for p in items if not any(q is not p and _contains(q, p) for q in items)]


def _vcentre(out: list[Placed], body: Rect, lt: LayoutTokens) -> list[Placed]:
    if not lt.vcentre or body.h <= 0:
        return out
    items = _body_items(out, body)
    roots = _roots(items)
    if not roots:
        return out
    for p in roots:
        el = p.element
        if isinstance(el, (Image, Media)) or not isinstance(el, (Container, Table, Chart, Text, Shape, Raw)):
            return out
        if isinstance(el, Shape) and p.h > to_emu("0.05in"):
            return out  # a loose shape is a figure the passes before this one placed
        if isinstance(el, Container) and (_SKIP_CLASSES & set(el.classes)):
            return out
        if getattr(el, "box", None) is not None:
            return out  # the author placed it
    res: dict[int, Placed] = {}
    gap = to_emu(lt.vcentre_gap)
    # --- a lone table: columns hug their text, rows stay moderate
    tabs = [p for p in roots if isinstance(p.element, Table)]
    if len(tabs) == 1 and len(roots) == 1:
        res[id(tabs[0])] = _hug_table(tabs[0], lt)
    # --- a row of text cards: the tallest content decides the height
    cards = [p for p in roots if isinstance(p.element, Container)]
    if cards and len({c.y for c in cards}) == 1:
        res.update(_hug_cards(cards, items, lt))
    now = [res.get(id(p), p) for p in items]
    top = min(p.y for p in now)
    bottom = max(p.y + p.h for p in now)
    # --- air under the block: what reached the bottom gives the gap back
    limit = body.bottom - gap
    if bottom > limit:
        for p in roots:
            q = res.get(id(p), p)
            if q.y + q.h > limit and isinstance(q.element, (Chart, Table, Raw)):
                res[id(p)] = _cut(q, limit - q.y)
            elif q.y + q.h > limit and isinstance(q.element, Container):
                inner = [c for c in now if c is not q and _contains(q, c)]
                if all(c.y + c.h <= limit for c in inner):
                    res[id(p)] = q.model_copy(update={"h": limit - q.y})
        now = [res.get(id(p), p) for p in items]
        bottom = max(p.y + p.h for p in now)
    # --- centred in the free body
    free = limit - body.y
    dy = body.y + (free - (bottom - top)) // 2 - top if bottom - top < free else 0
    if not dy and not res:
        return out
    ids = {id(p) for p in items}
    return [
        (res.get(id(p), p).model_copy(update={"y": res.get(id(p), p).y + dy}) if dy else res.get(id(p), p))
        if id(p) in ids
        else p
        for p in out
    ]


def _cut(p: Placed, h: int) -> Placed:
    h = max(h, 1)
    if isinstance(p.element, Table):
        rh = p.element.attrs.get("_row_h")
        if rh and sum(rh) > h:
            k = h / sum(rh)
            new = [round(x * k) for x in rh]
            el = p.element.model_copy(update={"attrs": {**p.element.attrs, "_row_h": new}})
            return p.model_copy(update={"element": el, "h": sum(new)})
    return p.model_copy(update={"h": h})


def _hug_table(p: Placed, lt: LayoutTokens) -> Placed:
    t = p.element
    rh, cw = t.attrs.get("_row_h"), t.attrs.get("_col_w")
    if not rh or not cw:
        return p
    size = (p.style.font_size or 14) * p.font_scale
    nrows, ncols, anchors = tables.table_grid(t)
    attrs = dict(t.attrs)
    w, x = p.w, p.x
    if lt.vcentre_hug_cols and not t.col_widths and len(cw) == ncols:
        weights, min_w = tables._measured_em(t, ncols, anchors, size)
        nat = sum(max(a, b) for a, b in zip(weights, min_w, strict=True))
        want = round((nat + ncols * lt.vcentre_col_pad_em) * size * EMU_PER_PT)
        if want < p.w:
            w = want
            x = p.x + (p.w - w) // 2
            pad_em = lt.vcentre_col_pad_em * size * EMU_PER_PT
            nat_w = [max(a, b) * size * EMU_PER_PT + pad_em for a, b in zip(weights, min_w, strict=True)]
            new = [round(v) for v in nat_w]
            new[-1] += w - sum(new)
            attrs["_col_w"] = new
    cap = round(lt.vcentre_row_em * size * EMU_PER_PT) if lt.vcentre_row_em > 0 else 0
    h = p.h
    if cap and any(r > cap for r in rh):
        new = [min(r, cap) for r in rh]
        attrs["_row_h"] = new
        h = sum(new)
    if w == p.w and h == p.h:
        return p
    return p.model_copy(update={"element": t.model_copy(update={"attrs": attrs}), "w": w, "x": x, "h": h})


def _hug_cards(cards: list[Placed], items: list[Placed], lt: LayoutTokens) -> dict[int, Placed]:
    from .engine import _text_h

    need = 0
    inner_of: dict[int, list[Placed]] = {}
    for c in cards:
        inner = [p for p in items if p is not c and _contains(c, p)]
        if not inner or any(not isinstance(p.element, Text) for p in inner):
            return {}
        inner_of[id(c)] = inner
        inset = min(p.y for p in inner) - c.y
        need = max(need, max(p.y + _text_h(p) for p in inner) - c.y + inset)
    if need >= max(c.h for c in cards) or need <= 0:
        return {}
    res: dict[int, Placed] = {}
    for c in cards:
        res[id(c)] = c.model_copy(update={"h": need})
        for p in inner_of[id(c)]:
            res[id(p)] = p.model_copy(update={"h": max(min(p.h, c.y + need - p.y), 1)})
    return res


__all__ = ["vcentre"]
_ = measure  # (kept for the callers that import the module for its side tokens)
