"""Sparse slides use the body (design wave 2): a short bullet list, a lone table with its conclusion bar.

Two passes over the finished placed items of a content slide body (token driven, geometry only):

* ``fill_text_list``: body text alone under the lead (a few bullets, one or two paragraphs) that leaves
  more than ``layout.list_fill_free`` of the body empty grows its text (up to ``list_text_max_pt``, never
  onto a new wrapped line), then its paragraph gaps (up to ``list_gap_max`` em) until it covers
  ``list_fill_share`` of the body; the block sits with ``list_top_share`` of what is left above it.
* ``fill_table_free``: a table alone in the body (at most ``table_free_max_rows`` rows) grows its text (up to
  ``table_free_text_max_pt``, no new wrapped line, CJK safe) and its rows (up to ``table_free_row_em`` x the
  text) toward the free height; what is still free is split around it (``table_free_top`` above). The caller
  attaches a conclusion bar to the result (``bar_attach``).

Explicit author input wins: a ``{x y w h}`` box, an own font size, a class, a vertical alignment or
``layout.body_valign=top`` leave everything as it is. Never raises: anything unexpected returns the items.
"""

from __future__ import annotations

import math

from ..ir import Placed, Table, Text
from ..theme import LayoutTokens
from ..units import EMU_PER_PT
from . import measure
from .grid import Rect
from .l3fill import _body_items, _spread, _text_pad
from .tables import row_heights, table_grid
from .vfill import _contains


def _own_size(el) -> bool:
    """The author fixed a font size on the element or on one of its paragraphs (``{size=14}``)."""
    return bool(getattr(el, "style", None) and el.style.font_size) or any(
        q.style is not None and q.style.font_size for q in getattr(el, "paragraphs", [])
    )


def _empty(items: list[Placed], body: Rect, bottom: int) -> int:
    top = min(p.y for p in items)
    return (top - body.y) + (body.bottom - bottom)


def fill_text_list(out: list[Placed], body: Rect, lt: LayoutTokens) -> list[Placed]:
    """Body text alone under the lead grows with the free height (see the module docstring)."""
    try:
        return _fill_text_list(out, body, lt)
    except Exception:  # never raise on bad input
        return out


def _fill_text_list(out: list[Placed], body: Rect, lt: LayoutTokens) -> list[Placed]:
    if not lt.list_fill or not lt.grow or lt.body_valign == "top" or body.h <= 0:
        return out
    items = _body_items(out, body)
    texts = sorted(items, key=lambda p: (p.y, p.x))
    if not texts or len(texts) > 3:
        return out
    for p in texts:
        el = p.element
        if (
            not isinstance(el, Text)
            or el.role != "body"
            or not el.paragraphs
            or el.classes
            or el.box is not None
            or _own_size(el)
            or p.style.valign not in (None, "top")
            or p.style.fill
            or p.style.line
        ):
            return out
    if not any(len(p.element.paragraphs) > 1 for p in texts):
        return out  # a lone paragraph is prose, not a list
    from .engine import _text_h

    bottom = max(p.y + _text_h(p) for p in texts)
    if _empty(texts, body, bottom) <= lt.list_fill_free * body.h:
        return out
    target = round(lt.list_fill_share * body.h)
    g_def = measure.para_gap()
    gaps = [b.y - (a.y + _text_h(a)) for a, b in zip(texts, texts[1:], strict=False)]
    cur_pt = max((p.style.font_size or 18) * p.font_scale for p in texts)

    def height(s: float, g: float) -> int:
        h = 0
        for p in texts:
            pad = _text_pad(p)
            w = p.w - 2 * pad
            h += round(measure.paragraphs_height(p.element.paragraphs, w, p.style, p.font_scale * s, gap=g))
            h += 2 * pad
        return h + round(sum(max(x, 0) for x in gaps) * s)

    def wraps_ok(s: float) -> bool:
        return s <= 1.0 or all(_spread(p, 10**9, lt, _text_pad(p), s) is not None for p in texts)

    s_top = max(lt.list_text_max_pt / max(cur_pt, 1.0), 1.0)
    step = max(lt.l3_grow_step, 0.01)
    n = int((s_top - 1.0) / step + 1e-9)
    best = 1.0
    for i in range(n + 2):
        s = math.floor((s_top - i * step) * 10000 + 1e-6) / 10000 if i <= n else 1.0
        if s < 1.0:
            s = 1.0
        if wraps_ok(s) and height(s, g_def) <= target:
            best = s
            break
        if s <= 1.0:
            break
    g = g_def
    cap = max(lt.list_gap_max, g_def)
    while g + 0.05 <= cap + 1e-9 and height(best, g + 0.05) <= target:
        g = round(g + 0.05, 3)
    if best <= 1.0 and g <= g_def + 1e-9:
        return out
    # place: the block sits with list_top_share of the leftover above it
    gap_s = [round(max(x, 0) * best) for x in gaps]
    total = height(best, g)
    top = body.y + round((body.h - total) * min(max(lt.list_top_share, 0.0), 1.0))
    before = max(texts[0].y - body.y, body.bottom - bottom)
    if max(top - body.y, body.bottom - (top + total)) >= before:
        return out  # the band the slide had is not made smaller: keep it
    res: dict[int, Placed] = {}
    y = top
    for k, p in enumerate(texts):
        pad = _text_pad(p)
        w = p.w - 2 * pad
        fs = p.font_scale * best
        h = round(measure.paragraphs_height(p.element.paragraphs, w, p.style, fs, gap=g)) + 2 * pad
        el = p.element.model_copy(update={"attrs": {**p.element.attrs, "para_gap": round(g, 3)}})
        res[id(p)] = p.model_copy(update={"y": y, "h": h, "font_scale": round(fs, 4), "element": el})
        y += h + (gap_s[k] if k < len(gap_s) else 0)
    return [res.get(id(p), p) for p in out]


def lone_table(items: list[Placed]) -> Placed | None:
    """The one table of a body that holds nothing else (items inside it count as the table), else ``None``."""
    tabs = [p for p in items if isinstance(p.element, Table)]
    if len(tabs) != 1 or any(q is not tabs[0] and not _contains(tabs[0], q) for q in items):
        return None
    return tabs[0]


def fill_table_free(out: list[Placed], body: Rect, lt: LayoutTokens, bar: bool = False) -> list[Placed]:
    """A table alone in the body grows its text and rows toward the free height (see the module docstring).

    ``bar``: a conclusion bar sits under the body; the table then stays at the top and, with
    ``bar_attach=move``, keeps its natural rows (the caller moves the bar up to it)."""
    try:
        return _fill_table_free(out, body, lt, bar)
    except Exception:  # never raise on bad input
        return out


def _fill_table_free(out: list[Placed], body: Rect, lt: LayoutTokens, bar: bool) -> list[Placed]:
    if not lt.table_free or lt.table_text_step <= 0 or lt.body_valign == "top" or body.h <= 0:
        return out
    p = lone_table(_body_items(out, body))
    if p is None:
        return out
    t = p.element
    if t.classes or t.box is not None:
        return out
    rh, cw = t.attrs.get("_row_h"), t.attrs.get("_col_w")
    nrows, _ncols, anchors = table_grid(t)
    if (
        not rh
        or not cw
        or len(rh) != nrows
        or nrows > lt.table_free_max_rows
        or any(c.style is not None and c.style.font_size is not None for row in t.rows for c in row)
        or _own_size(t)
    ):
        return out
    free = _empty([p], body, p.y + p.h)
    if free <= lt.table_free_min * body.h:
        return out
    size = (p.style.font_size or 14) * p.font_scale
    avail = body.bottom - body.y
    # 1. text: the largest factor (<= table_free_text_max_pt) that adds no wrapped line and fits the body
    top_f = max(lt.table_free_text_max_pt / max(size, 1e-6), 1.0)
    step = lt.table_text_step
    narrow = [max(1, round(w * (1.0 - lt.l3_wrap_margin))) for w in cw]
    old = row_heights(t, anchors, narrow, p.style, p.font_scale)
    best, nat = 1.0, row_heights(t, anchors, cw, p.style, p.font_scale)
    n = int((top_f - 1.0) / step + 1e-9)
    for i in range(n + 1):
        f = math.floor((top_f - i * step) * 1000 + 1e-6) / 1000  # never past the cap
        if f < 1.0 + step / 2:
            break  # a sliver of growth is not worth a moved table
        cand = row_heights(t, anchors, cw, p.style, p.font_scale * f)
        if sum(cand) > avail:
            continue
        new = row_heights(t, anchors, narrow, p.style, p.font_scale * f)
        if any(b > a * f * 1.02 for a, b in zip(old, new, strict=True)):
            continue  # a cell would wrap earlier than before
        best, nat = f, cand
        break
    # 2. rows: stretch toward the free height, each at most table_free_row_em x the text
    cap = round(lt.table_free_row_em * size * best * EMU_PER_PT) if lt.table_free_row_em > 0 else 0
    rows = [max(a, b) for a, b in zip(nat, rh, strict=True)]  # rows never get shorter than they were
    if sum(rows) > avail:
        rows = list(nat)
    want = avail - sum(rows)
    if want > 0 and cap > 0 and not (bar and lt.bar_attach == "move"):
        room = [max(cap - h, 0) for h in rows]
        total = sum(room)
        if total > 0:
            take = min(want, total)
            rows = [h + round(take * r / total) for h, r in zip(rows, room, strict=True)]
    if best == 1.0 and sum(rows) <= sum(rh) + 2:
        return out
    block = sum(rows)
    left = avail - block
    y = body.y if bar else body.y + round(max(left, 0) * min(max(lt.table_free_top, 0.0), 1.0))
    el = t.model_copy(update={"attrs": {**t.attrs, "_row_h": rows, "_row_cap": True, "_vgrown": True}})
    grown = p.model_copy(update={"element": el, "font_scale": p.font_scale * best, "h": block, "y": y})
    return [grown if q is p else q for q in out]
