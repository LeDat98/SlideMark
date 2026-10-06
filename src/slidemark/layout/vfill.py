"""Vertical policy of a finished body: distribute leftover height, then center the block.

Runs on the placed items of a slide body (after growth, the sparse step and row expansion):

1. rows = top-level blocks clustered by vertical overlap; connectors are not blocks and follow their rows;
2. when more than ``layout.body_free_max`` of the body is free: table rows and chevron rows grow, then the
   gaps between rows grow, each by at most ``layout.body_spread_max`` (cards keep hugging their content);
3. a block that fills less than ``layout.center_min_fill`` of the body is never centered (top-anchored);
   ``layout.body_valign``: ``top`` keeps the block at the top, ``center`` always centers it between the
   lead line and the footnote / conclusion area, ``auto`` centers only while the free height that is left
   is still above ``body_free_max``.

Never raises: anything unexpected returns the items unchanged.
"""

from __future__ import annotations

from ..ir import Container, Placed, Shape, Table, Text
from ..units import EMU_PER_PT
from . import measure
from .grid import Rect
from .tables import row_heights, table_grid


def _contains(a: Placed, b: Placed) -> bool:
    return b.x >= a.x - 2 and b.y >= a.y - 2 and b.x + b.w <= a.x + a.w + 2 and b.y + b.h <= a.y + a.h + 2


def _is_line(p: Placed) -> bool:
    return isinstance(p.element, Shape) and p.element.shape == "line"


def _row_cap(p: Placed, row_max_em: float) -> int | None:
    """Tallest a row of table ``p`` may get (EMU): ``row_max_em`` x its text size; None = no cap."""
    cap = p.element.attrs.get("_row_cap") if isinstance(p.element, Table) else None
    if row_max_em <= 0 or not cap:
        return None
    em = max(float(cap), row_max_em) if cap is not True else row_max_em  # a number: this table's own limit
    return round(em * (p.style.font_size or 14) * p.font_scale * EMU_PER_PT)


_VTEXT_STEP = 0.05  # table text grows in steps of this factor (see ``_grow_table``)


def _grow_table(p: Placed, peer_pt: float = 0.0) -> Placed:
    """A table whose rows are stretched beyond ``table_comfort_em`` grows its text (header and body alike).

    The factor is the largest one (<= ``table_vtext_max``, ``table_vtext_max_pt``) that keeps every row at its
    stretched height without a new wrapped line (CJK guard: natural height <= the old one x the factor). Rows
    keep their heights; the vertical fill may then stretch them again up to ``table_row_max_em``.
    ``peer_pt`` (> 0) caps the size: chevron text x ``table_peer_max``, box text x ``table_box_max``.
    """
    tk = measure.tokens()
    t = p.element
    if (
        tk.table_comfort_em <= 0
        or tk.table_vtext_max <= 1.0
        or tk.table_text_step <= 0
        or not isinstance(t, Table)
    ):
        return p
    rh, cw = t.attrs.get("_row_h"), t.attrs.get("_col_w")
    nrows, _ncols, anchors = table_grid(t)
    if (
        not rh
        or not cw
        or t.attrs.get("_row_cap")  # already grown by the layout's table text step
        or len(rh) != nrows
        or not tk.table_vtext_min_rows <= nrows <= tk.table_vtext_max_rows
        or any(c.style is not None and c.style.font_size is not None for row in t.rows for c in row)
    ):
        return p
    size = (p.style.font_size or 14) * p.font_scale
    avg = sum(rh) / nrows / (size * EMU_PER_PT)
    if avg <= tk.table_comfort_em:
        return p
    cap_pt = tk.table_vtext_max_pt
    if peer_pt > 0:
        cap_pt = min(cap_pt, peer_pt)
    top = min(tk.table_vtext_max, cap_pt / max(size, 1e-6), avg / tk.table_comfort_em)
    base = row_heights(t, anchors, cw, p.style, p.font_scale)
    n = int((top - 1.0) / _VTEXT_STEP + 1e-9)
    for i in range(n):
        f = round(top - _VTEXT_STEP * i, 3) if i else top
        if f <= 1.0 + 1e-6:
            break
        nat = row_heights(t, anchors, cw, p.style, p.font_scale * f)
        if all(a <= b * f * 1.02 and a <= h for a, b, h in zip(nat, base, rh, strict=True)):
            el = t.model_copy(update={"attrs": {**t.attrs, "_row_cap": True, "_vgrown": True}})
            return p.model_copy(update={"element": el, "font_scale": p.font_scale * f})
    if tk.table_vrow_max_em > 0:  # the text cannot grow: the rows may take a little more slack
        el = t.model_copy(update={"attrs": {**t.attrs, "_row_cap": tk.table_vrow_max_em, "_vgrown": True}})
        return p.model_copy(update={"element": el})
    return p


def _is_chevron(p: Placed) -> bool:
    return isinstance(p.element, Shape) and p.element.shape == "chevron"


def _owner(items: list[Placed], i: int) -> int | None:
    """Index of the smallest card (container / chevron) that contains item ``i``, else None."""
    p = items[i]
    best: int | None = None
    for j, q in enumerate(items):
        if j == i or not (isinstance(q.element, Container) or _is_chevron(q)):
            continue
        if not _contains(q, p) or (q.w == p.w and q.h == p.h and q.x == p.x and q.y == p.y and j > i):
            continue
        if best is None or q.w * q.h < items[best].w * items[best].h:
            best = j
    return best


def bottom_all(items: list[Placed], roots: list[int]) -> int:
    return max(items[i].y + items[i].h for i in roots)


def _header_bottom(items: list[Placed], o: int) -> int:
    """Bottom of the header bar of card ``o`` (a full-width shape at its top), else its top."""
    c = items[o]
    for q in items:
        if (
            isinstance(q.element, (Shape, Text))
            and (isinstance(q.element, Shape) or q.element.role == "heading")
            and q is not c
            and q.y <= c.y + 2
            and q.h < c.h * 0.5
            and q.w >= c.w * 0.9
            and _contains(c, q)
        ):
            return q.y + q.h
    return c.y


def free_height(items: list[Placed], body: Rect) -> int:
    """Body height not covered by the block (top gap above it counts as free)."""
    if not items:
        return 0
    top = min(p.y for p in items)
    bottom = max(p.y + p.h for p in items)
    return max(body.h - (bottom - top), 0)


def fill_body(
    items: list[Placed],
    body: Rect,
    free_max: float,
    valign: str,
    spread_max: float,
    reserve: int = 0,
    center_min: float = 0.0,
    pad_share: float = 0.0,
    card_stretch: bool = False,
    card_share: float = 0.5,
    row_max_em: float = 0.0,
) -> list[Placed]:
    try:
        tk = measure.tokens()
        caps = []  # the table never out-sizes the chevron / box text beside it (inverted hierarchy)
        for p in items:
            sz = (p.style.font_size or 14) * p.font_scale
            if _is_chevron(p) and tk.table_peer_max > 0:
                caps.append(sz * tk.table_peer_max)
            elif isinstance(p.element, Text) and p.element.role == "body" and tk.table_box_max > 0:
                caps.append(sz * tk.table_box_max)
        peer = min(caps, default=0.0)
        items = [
            _grow_table(p, peer) if isinstance(p.element, Table) and _owner(items, i) is None else p
            for i, p in enumerate(items)
        ]
        return _fill(
            items,
            body,
            free_max,
            valign,
            spread_max,
            reserve,
            center_min,
            pad_share,
            card_stretch,
            card_share,
            row_max_em,
        )
    except Exception:  # never raise on odd input
        return items


def _fill(
    items: list[Placed],
    body: Rect,
    free_max: float,
    valign: str,
    spread_max: float,
    reserve: int,
    center_min: float,
    pad_share: float,
    card_stretch: bool,
    card_share: float,
    row_max_em: float = 0.0,
) -> list[Placed]:
    if valign == "top" or not items or body.h <= 0:
        return items
    n = len(items)
    owner = [_owner(items, i) for i in range(n)]
    roots = [i for i in range(n) if owner[i] is None and not _is_line(items[i])]
    lines = [i for i in range(n) if owner[i] is None and _is_line(items[i])]
    if not roots or all(isinstance(items[i].element, Text) for i in roots):
        return items  # plain text stays top-anchored
    # --- rows
    order = sorted(roots, key=lambda i: (items[i].y, items[i].x))
    rows: list[list[int]] = []
    bottom = -1
    for i in order:
        p = items[i]
        if rows and p.y < bottom - 2:
            rows[-1].append(i)
            bottom = max(bottom, p.y + p.h)
        else:
            rows.append([i])
            bottom = p.y + p.h
    tops = [min(items[i].y for i in r) for r in rows]
    bots = [max(items[i].y + items[i].h for i in r) for r in rows]
    free = free_height(items, body)
    thr = round(free_max * body.h)
    # --- distribute
    grow = [0] * len(rows)
    gap_add = [0] * max(len(rows) - 1, 0)
    budget = max(free - reserve, 0)  # the block keeps ``reserve`` of air to the conclusion / footnote
    small = (bottom_all(items, roots) - min(items[i].y for i in roots)) < center_min * body.h
    # a table that grew its text takes the slack below it even under the threshold (its rows only)
    vgrown = free <= thr and not small
    vgrown = vgrown and any(
        items[i].element.attrs.get("_vgrown") for i in roots if isinstance(items[i].element, Table)
    )
    if free > thr or small or vgrown:
        want = []
        for r, row in enumerate(rows):
            kinds = {
                Table
                if isinstance(items[i].element, Table)
                else "chev"
                if _is_chevron(items[i])
                else "card"
                if small and card_stretch and isinstance(items[i].element, Container)
                else 0
                for i in row
            }
            ok = kinds <= {Table, "chev", "card"} and 0 not in kinds
            share = spread_max * (card_share if kinds == {"card"} else 1.0)
            if vgrown and kinds != {Table}:
                ok = False  # a table that grew its text takes the slack; chevrons keep their height
            w = round(share * (bots[r] - tops[r])) if ok else 0
            tabs = [items[i] for i in row if isinstance(items[i].element, Table)]
            caps = [_row_cap(tp, row_max_em) for tp in tabs]
            if w and tabs and len(tabs) == len(row) and all(caps):  # grown tables: rows stay <= row_max_em
                w = min(
                    w,
                    max(
                        sum(max(c - h, 0) for h in tp.element.attrs.get("_row_h", []))
                        for tp, c in zip(tabs, caps, strict=True)
                    ),
                )
            want.append(w)
        take = min(budget, sum(want))
        if sum(want) > 0 and take > 0:
            for r in range(len(rows)):
                grow[r] = round(want[r] * take / sum(want))
            budget -= sum(grow)
        gw = [round(spread_max * (tops[r + 1] - bots[r])) for r in range(len(rows) - 1)]
        if vgrown:
            gw = [0] * len(gw)
        take = min(budget, sum(gw))
        if sum(gw) > 0 and take > 0:
            for r in range(len(gw)):
                gap_add[r] = round(gw[r] * take / sum(gw))
            budget -= sum(gap_add)
    # --- new row tops
    new_top: list[int] = []
    shift = 0
    for r in range(len(rows)):
        if r > 0:
            shift += gap_add[r - 1]
        new_top.append(tops[r] + shift)
        shift += grow[r]
    block_top = new_top[0]
    block_bottom = bots[-1] + shift
    left = body.h - (block_bottom - block_top)
    center = valign == "center" or (valign == "auto" and left > thr)
    if small:
        center = False  # a small block is top-anchored, never floating mid-height
    off = (body.y + (body.h - (block_bottom - block_top)) // 2 - block_top) if center else 0
    if not center and not any(grow) and not any(gap_add):
        return items
    row_of = {}
    for r, row in enumerate(rows):
        for i in row:
            row_of[i] = r

    def f(y: int) -> int:
        """Map an old y to the new one (for connectors and glued boxes)."""
        for r in range(len(rows)):
            if y <= bots[r] + 1:
                if y >= tops[r] - 1 or r == 0:
                    span = max(bots[r] - tops[r], 1)
                    t = min(max((y - tops[r]) / span, 0.0), 1.0)
                    return round(y + (new_top[r] - tops[r]) + t * grow[r]) + off
                # in the gap before row r: interpolate between previous bottom and this top
                a, b = bots[r - 1], tops[r]
                pa = bots[r - 1] + (new_top[r - 1] - tops[r - 1]) + grow[r - 1]
                pb = new_top[r]
                t = (y - a) / max(b - a, 1)
                return round(pa + t * (pb - pa)) + off
        r = len(rows) - 1
        return round(y + (new_top[r] - tops[r]) + grow[r]) + off

    out = list(items)
    for i in range(n):
        p = items[i]
        o = owner[i]
        top_i = i
        while owner[top_i] is not None:
            top_i = owner[top_i]
        if top_i in row_of or o is not None:
            r = row_of.get(top_i)
            if r is None:
                continue
            dy = new_top[r] - tops[r] + off
            h = p.h
            if o is None and grow[r] > 0:
                ratio = (bots[r] - tops[r] + grow[r]) / max(bots[r] - tops[r], 1)
                if isinstance(p.element, Table):
                    rh = p.element.attrs.get("_row_h")
                    if rh:
                        cap = _row_cap(p, row_max_em)
                        new = [round(x * ratio) for x in rh]
                        new[-1] += round(sum(rh) * ratio) - sum(new)
                        if cap:  # a row that is already tall enough keeps its height
                            new = [min(n, max(x, cap)) for n, x in zip(new, rh, strict=True)]
                        el = p.element.model_copy(update={"attrs": {**p.element.attrs, "_row_h": new}})
                        out[i] = p.model_copy(update={"element": el, "y": p.y + dy, "h": sum(new)})
                        continue
                h = round(p.h * ratio)
            elif o is not None and grow[r] > 0 and _is_chevron(items[top_i]):
                dy += grow[r] // 2  # icon next to a chevron stays centered
            elif o is not None and grow[r] > 0 and isinstance(items[o].element, Container):
                hb = _header_bottom(items, o)
                if p.y >= hb - 2 and not (p.y == items[o].y and p.h == items[o].h):
                    dy += round(
                        grow[r] * pad_share
                    )  # body of a stretched card: part of the growth is padding
            out[i] = p.model_copy(update={"y": p.y + dy, "h": h})
    for i in lines:
        p = items[i]
        y0, y1 = f(p.y), f(p.y + p.h)
        attrs = dict(p.element.attrs)
        for k in ("src_box", "dst_box"):
            b = attrs.get(k)
            if b:
                bx, by, bw, bh = b
                ny0, ny1 = f(by), f(by + bh)
                attrs[k] = (bx, ny0, bw, ny1 - ny0)
        el = p.element.model_copy(update={"attrs": attrs})
        out[i] = p.model_copy(update={"element": el, "y": y0, "h": max(y1 - y0, 0)})
    return out
