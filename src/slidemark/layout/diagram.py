"""Mermaid flowcharts: text-sized nodes, rank-aware connectors and edge labels.

``place_diagram`` is called by the engine for a ``Container(classes=["diagram"])`` whose children are ``node``
texts. Nodes keep one shared size (diamonds another), are centered in their grid cell and joined edge to edge.
Everything is computed in a *frame* where the rank axis points down (TD); LR / BT / RL diagrams are the same
picture transposed or mirrored, so one routing code serves all four directions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..ir import Container, Paragraph, Run, Shape, Style, Text
from ..units import EMU_PER_INCH as IN
from ..units import EMU_PER_PT
from . import measure
from .grid import Rect, parse_spec

MIN_W, MIN_H = 1.4, 0.55  # inches: smallest node
MAX_W = 3.4  # inches: node text wraps beyond this width
DIAMOND_MIN_W, DIAMOND_MIN_H = 1.9, 0.95
RANK_GAP, RANK_GAP_MAX = 0.45, 1.0  # inches between ranks (arrows must stay visible)
CROSS_GAP, CROSS_GAP_MAX = 0.3, 0.8  # inches between nodes of one rank
SIDE_STEP = 0.24  # inches between nested side routes (back edges)
LABEL_OFF = 0.05  # inches between an edge and its label
TOL = 1.01
_WORD = re.compile(r"[^\s\u3000-\u9fff\uff00-\uffef]+|[\u3000-\u9fff\uff00-\uffef]")


@dataclass
class _Node:
    el: Text
    style: Style
    eff: float
    diamond: bool
    tw: float  # natural single-line text width, EMU
    pad: int
    ww: float = 0.0  # width of the longest unbreakable word, EMU
    w: int = 0
    h: int = 0


@dataclass
class _Route:
    pts: list[tuple[int, int]]  # polyline in frame coordinates
    route: str  # "v" | "h" in frame coordinates
    elbow: bool
    adj: float
    p0: tuple[int, int]
    p1: tuple[int, int]
    side: bool = False


class _Frame:
    """Real slide coordinates <-> frame (rank axis down). ``t`` transposes, ``m`` mirrors the rank axis."""

    def __init__(self, vertical: bool, sgn: int):
        self.t = not vertical
        self.m = sgn < 0

    def pt(self, p: tuple[int, int]) -> tuple[int, int]:
        x, y = p
        if self.t:
            x, y = y, x
        return (x, -y if self.m else y)

    def unpt(self, p: tuple[int, int]) -> tuple[int, int]:
        x, y = p
        if self.m:
            y = -y
        return (y, x) if self.t else (x, y)

    def rect(self, r: Rect) -> Rect:
        x, y, w, h = r.x, r.y, r.w, r.h
        if self.t:
            x, y, w, h = y, x, h, w
        if self.m:
            y = -(y + h)
        return Rect(x, y, w, h)

    def unrect(self, r: Rect) -> Rect:
        x, y, w, h = r.x, r.y, r.w, r.h
        if self.m:
            y = -(y + h)
        if self.t:
            x, y, w, h = y, x, h, w
        return Rect(x, y, w, h)

    def dims(self, w: int, h: int) -> tuple[int, int]:
        return (h, w) if self.t else (w, h)


def _cx(r: Rect) -> int:
    return r.x + r.w // 2


def _cy(r: Rect) -> int:
    return r.y + r.h // 2


def _hits(p0: tuple[int, int], p1: tuple[int, int], r: Rect) -> bool:
    x0, x1 = sorted((p0[0], p1[0]))
    y0, y1 = sorted((p0[1], p1[1]))
    return x1 > r.x and x0 < r.right and y1 > r.y and y0 < r.bottom


def _poly_hits(pts: list[tuple[int, int]], rects: list[Rect]) -> bool:
    return any(_hits(u, v, r) for r in rects for u, v in zip(pts, pts[1:], strict=False))


def _poly_hits_any(lines: list[list[tuple[int, int]]], r: Rect) -> bool:
    return any(_hits(u, v, r) for pts in lines for u, v in zip(pts, pts[1:], strict=False))


def _overlap(a: Rect, b: Rect, margin: int = 0) -> bool:
    return (
        a.x < b.right + margin
        and b.x < a.right + margin
        and a.y < b.bottom + margin
        and b.y < a.bottom + margin
    )


def _positions(c: Container, n: int) -> tuple[dict[int, tuple[int, int]], int, int] | None:
    """Node index -> (row, col) from the container grid; ``None`` when the grid is unusable."""
    if not c.grid:
        return ({0: (0, 0)}, 1, 1) if n == 1 else None
    gs = parse_spec(c.grid, n, c.classes)
    if gs is None or gs.errors or not gs.cols or not gs.rows:
        return None
    nc, nr = len(gs.cols), len(gs.rows)
    if gs.areas is not None:
        if set(gs.areas) != set(range(n)):
            return None
        return {i: (a[0], a[1]) for i, a in gs.areas.items()}, nr, nc
    return {i: (min(i // nc, nr - 1), i % nc) for i in range(n)}, nr, nc


def _orientation(links, pos) -> tuple[bool, int]:
    """(vertical, sign): the axis along which most links point the same way is the rank axis."""
    stats = {True: [0, 0], False: [0, 0]}  # vertical? -> [forward, backward] counts
    for ln in links:
        if ln.src in pos and ln.dst in pos:
            (r0, c0), (r1, c1) = pos[ln.src], pos[ln.dst]
            for vertical, d in ((True, r1 - r0), (False, c1 - c0)):
                if d > 0:
                    stats[vertical][0] += 1
                elif d < 0:
                    stats[vertical][1] += 1
    vertical = max(stats[True]) >= max(stats[False])
    fwd, back = stats[vertical]
    return vertical, 1 if fwd >= back else -1


def place_diagram(ctx, c: Container, area: Rect, inherit: Style) -> bool:
    """Place a flowchart inside ``area``; ``False`` (nothing emitted) when it is not a plain flowchart."""
    from . import engine as E

    kids = c.children
    if not kids or not all(isinstance(k, Text) and "node" in k.classes for k in kids):
        return False
    got = _positions(c, len(kids))
    if got is None or area.w <= 0 or area.h <= 0:
        return False
    pos, nr, nc = got
    saved = ctx.depth
    ctx.depth += 1  # children of a box: sparse-slide growth applies to the node text
    try:
        _place(ctx, E, c, area, inherit, pos, nr, nc)
    finally:
        ctx.depth = saved
    return True


def _place(ctx, E, c: Container, area: Rect, inherit: Style, pos, nr: int, nc: int) -> None:
    kids: list[Text] = c.children  # type: ignore[assignment]
    n = len(kids)
    vertical, sgn = _orientation(c.links, pos)
    frame = _Frame(vertical, sgn)
    # ---- node styles
    nodes: list[_Node] = []
    ks: list[float] = []
    for el in kids:
        st = E._text_style(ctx, el, inherit)
        base = st.font_size or 18
        eff = E._grown(ctx, el, measure.effective_scale(base, ctx.scale, ctx.theme.min_font_size))
        diamond = "decision" in el.classes
        pad = E._pad(st)
        if diamond:
            pad = round(2 * EMU_PER_PT * ctx.tight)
            st = st.merged(Style(padding=f"{round(pad / EMU_PER_PT, 2)}pt"))
        elif st.radius is None:
            st = st.merged(Style(radius=5))
        bold = bool(st.bold)
        em = max(
            (measure.text_em(p.plain, bold=bold or any(r.bold for r in p.runs)) for p in el.paragraphs),
            default=1.0,
        )
        unit = (
            base
            * eff
            * EMU_PER_PT
            * (1.06 if any(measure.is_cjk(ch) for p in el.paragraphs for ch in p.plain) else 1.16)
        )
        word_em = max(
            (
                measure.text_em(w, bold=bold or any(r.bold for r in p.runs))
                for p in el.paragraphs
                for w in _WORD.findall(p.plain)
            ),
            default=0.0,
        )
        nodes.append(_Node(el, st, eff, diamond, em * unit, pad, ww=max(word_em, 1.0) * unit))
        ks.append(eff if eff > 1.0 else max(min(ctx.scale, 1.0), 0.3))
    k = max(ks)
    gk = max(min(k, 1.0), 0.5)
    # ---- edge labels (sizes first: they widen the gaps between ranks)
    cap_style = E._role_style(ctx, "caption").merged(Style(align="center", valign="middle", padding="2pt"))
    cap_base = cap_style.font_size or 12
    cap_eff = measure.effective_scale(cap_base, ctx.scale, ctx.theme.min_font_size)
    cap_pad = E._pad(cap_style)
    lab_dims: dict[int, tuple[int, int]] = {}
    for i, ln in enumerate(c.links):
        text = " ".join((ln.label or "").split())
        if not text or ln.src not in pos or ln.dst not in pos or ln.src == ln.dst:
            continue
        lw = (
            round(measure.text_em(text) * cap_base * cap_eff * EMU_PER_PT * 1.1)
            + 2 * cap_pad
            + round(0.04 * IN)
        )
        para = Paragraph(runs=[Run(text=text)])
        lh = round(measure.paragraphs_height([para], 10**9, cap_style, cap_eff)) + 2 * cap_pad
        lab_dims[i] = (lw, lh)

    def rank_cross(i: int) -> tuple[int, int]:
        r, cc = pos[i]
        return (r, cc) if vertical else (cc, r)

    gap_rank = round(RANK_GAP * IN * gk)
    n_side = 0
    side_label = 0
    for i, ln in enumerate(c.links):
        if ln.src not in pos or ln.dst not in pos or ln.src == ln.dst:
            continue
        (rs, cs), (rd, cd) = rank_cross(ln.src), rank_cross(ln.dst)
        d = (rd - rs) * sgn
        straight = cs == cd
        between = [
            j
            for j in range(n)
            if j not in (ln.src, ln.dst) and rank_cross(j)[1] == cs and rs < rank_cross(j)[0] < rd
        ]
        if d <= 0 or (straight and d > 1 and between):
            n_side += 1
            if i in lab_dims:
                side_label = max(side_label, lab_dims[i][0] if vertical else lab_dims[i][1])
            continue
        if i in lab_dims:
            ext = lab_dims[i][1] if vertical else lab_dims[i][0]
            gap_rank = max(gap_rank, ext + round(0.2 * IN) if straight else 2 * ext + round(0.1 * IN))
    gap_cross = round(CROSS_GAP * IN * gk)
    reserve = (round(n_side * SIDE_STEP * IN * gk) + round(0.15 * IN) + side_label) if n_side else 0
    gx_min, gy_min = (gap_cross, gap_rank) if vertical else (gap_rank, gap_cross)
    res_x, res_y = (reserve, 0) if vertical else (0, reserve)
    # ---- node sizes
    min_w, min_h = round(MIN_W * IN * k), round(MIN_H * IN * k)
    cap_w = max(round(0.6 * IN), (area.w - res_x - (nc - 1) * gx_min) // max(nc, 1))
    cap_w = min(cap_w, round(MAX_W * IN * k))

    def text_h(nd: _Node, width: int) -> float:
        return measure.paragraphs_height(nd.el.paragraphs, max(width, 1), nd.style, nd.eff)

    rect_nodes = [nd for nd in nodes if not nd.diamond]
    dia_nodes = [nd for nd in nodes if nd.diamond]
    if rect_nodes:
        w = max(min_w, min(cap_w, max(round(nd.tw) + 2 * nd.pad + round(0.1 * IN) for nd in rect_nodes)))
        w = max(
            w, max(round(nd.ww) + 2 * nd.pad + round(0.1 * IN) for nd in rect_nodes)
        )  # never break a word
        h = max(
            min_h, max(round(text_h(nd, w - 2 * nd.pad)) + 2 * nd.pad + round(0.08 * IN) for nd in rect_nodes)
        )
        for nd in rect_nodes:
            nd.w, nd.h = w, h
    if dia_nodes:
        cap_d = min(cap_w, round(3.0 * IN * k))
        w = max(
            round(DIAMOND_MIN_W * IN * k),
            min(cap_d, max(2 * round(nd.tw) + 4 * nd.pad + round(0.2 * IN) for nd in dia_nodes)),
        )
        # the text area of a diamond is half its width: the longest word must fit there on one line
        w = max(w, max(2 * round(nd.ww * 1.1) + 4 * nd.pad + round(0.1 * IN) for nd in dia_nodes))
        h = max(
            round(DIAMOND_MIN_H * IN * k),
            max(
                2 * round(text_h(nd, w // 2 - 2 * nd.pad)) + 4 * nd.pad + round(0.1 * IN) for nd in dia_nodes
            ),
        )
        for nd in dia_nodes:
            nd.w, nd.h = w, h
    # ---- tracks and gaps (real coordinates)
    cw = [0] * nc
    rh = [0] * nr
    for i, nd in enumerate(nodes):
        r, cc = pos[i]
        cw[cc] = max(cw[cc], nd.w)
        rh[r] = max(rh[r], nd.h)

    def spread(total: int, avail: int, count: int, lo: int, hi: int) -> int:
        if count <= 1:
            return 0
        return max(lo, min(hi, (avail - total) // (count - 1)))

    gx = spread(
        sum(cw),
        area.w - res_x,
        nc,
        gx_min,
        round((RANK_GAP_MAX if not vertical else CROSS_GAP_MAX) * IN * gk),
    )
    gy = spread(
        sum(rh), area.h - res_y, nr, gy_min, round((RANK_GAP_MAX if vertical else CROSS_GAP_MAX) * IN * gk)
    )
    xs, ys = [], []
    x = y = 0
    for wv in cw:
        xs.append(x)
        x += wv + gx
    for hv in rh:
        ys.append(y)
        y += hv + gy
    rects: dict[int, Rect] = {}
    for i, nd in enumerate(nodes):
        r, cc = pos[i]
        rects[i] = Rect(xs[cc] + (cw[cc] - nd.w) // 2, ys[r] + (rh[r] - nd.h) // 2, nd.w, nd.h)
    # ---- connectors and labels in the frame
    frects = {i: frame.rect(r) for i, r in rects.items()}
    routes: list[tuple[int, _Route, bool]] = []  # (link index, route, glue boxes?)
    side_k = 0
    for i, ln in enumerate(c.links):
        if ln.src not in frects or ln.dst not in frects or ln.src == ln.dst:
            ctx.diag(
                "link",
                f"connector {ln.src}>{ln.dst} refers to a node that does not exist",
                "use node indices that exist in this diagram",
            )
            continue
        a, b = frects[ln.src], frects[ln.dst]
        others = [r for j, r in frects.items() if j not in (ln.src, ln.dst)]
        rt = _route(a, b, others, list(frects.values()), side_k, round(SIDE_STEP * IN * gk))
        if rt.side:
            side_k += 1
        routes.append((i, rt, not rt.side))
    fnodes = list(frects.values())
    placed_labels: list[tuple[int, Rect]] = []  # (link index, frame rect)
    for i, rt, _g in routes:
        if i not in lab_dims:
            continue
        lw, lh = frame.dims(*lab_dims[i])
        lines = [o.pts for j, o, _g in routes if j != i]
        taken = [r for _, r in placed_labels]
        placed_labels.append((i, _label_rect(rt, lw, lh, fnodes, taken, round(LABEL_OFF * IN), lines)))
    # ---- bounding box, fit check, centering
    all_real: list[Rect] = list(rects.values())
    for _i, rt, _g in routes:
        for p in rt.pts:
            q = frame.unpt(p)
            all_real.append(Rect(q[0], q[1], 0, 0))
    label_real = {i: frame.unrect(r) for i, r in placed_labels}
    all_real += list(label_real.values())
    bx0, by0 = min(r.x for r in all_real), min(r.y for r in all_real)
    bx1, by1 = max(r.right for r in all_real), max(r.bottom for r in all_real)
    bw, bh = bx1 - bx0, by1 - by0
    if bw > area.w * TOL or bh > area.h * TOL:
        ctx.over.append("diagram")
    dx = area.x + max(area.w - bw, 0) // 2 - bx0
    dy = area.y + max(area.h - bh, 0) // 2 - by0  # centered in the space it has

    def shift(r: Rect) -> Rect:
        return Rect(r.x + dx, r.y + dy, r.w, r.h)

    # ---- emit: card, nodes, connectors, labels
    card = Rect(bx0 + dx, by0 + dy, bw, bh)
    ctx.emit(c, card, E._card_style(ctx, c))
    for i, nd in enumerate(nodes):
        el = nd.el
        shape = Shape(
            shape="diamond" if nd.diamond else "rounded-rect",
            paragraphs=el.paragraphs,
            id=el.id,
            classes=el.classes,
            line=el.line,
        )
        ctx.emit(shape, shift(rects[i]), nd.style, nd.eff)
    for i, rt, _glue in routes:
        ln = c.links[i]
        head = "arrow" if ln.arrow else "none"
        if rt.side:  # a loop around the nodes: straight segments render the same everywhere
            pts = [frame.unpt(p) for p in rt.pts]
            pts = [(x + dx, y + dy) for x, y in pts]
            for s_i, (u, v) in enumerate(zip(pts, pts[1:], strict=False)):
                if s_i == 1:  # the middle leg overlaps its neighbours so the corners stay closed
                    ex = (v[0] > u[0]) - (v[0] < u[0])
                    ey = (v[1] > u[1]) - (v[1] < u[1])
                    u, v = (u[0] - ex * 9525, u[1] - ey * 9525), (v[0] + ex * 9525, v[1] + ey * 9525)
                attrs = {
                    "head": head if s_i == 2 else "none",
                    "flip_h": v[0] < u[0],
                    "flip_v": v[1] < u[1],
                    "side": True,
                }
                box = Rect(min(u[0], v[0]), min(u[1], v[1]), abs(v[0] - u[0]), abs(v[1] - u[1]))
                ctx.emit(Shape(shape="line", attrs=attrs), box, Style(line="primary", line_width=1.5))
            continue
        p0, p1 = frame.unpt(rt.p0), frame.unpt(rt.p1)
        p0, p1 = (p0[0] + dx, p0[1] + dy), (p1[0] + dx, p1[1] + dy)
        route = rt.route
        if frame.t:
            route = "h" if route == "v" else "v"
        sa, sb = shift(rects[ln.src]), shift(rects[ln.dst])
        attrs: dict = {
            "head": head,
            "flip_h": p1[0] < p0[0],
            "flip_v": p1[1] < p0[1],
            "elbow": rt.elbow,
            "route": route,
            "adj": round(rt.adj, 4),
            "src_box": [sa.x, sa.y, sa.w, sa.h],
            "dst_box": [sb.x, sb.y, sb.w, sb.h],
        }
        box = Rect(min(p0[0], p1[0]), min(p0[1], p1[1]), abs(p1[0] - p0[0]), abs(p1[1] - p0[1]))
        ctx.emit(Shape(shape="line", attrs=attrs), box, Style(line="primary", line_width=1.5))
    for i, r in label_real.items():
        text = " ".join((c.links[i].label or "").split())
        el = Text(role="caption", paragraphs=[Paragraph(runs=[Run(text=text)])])
        ctx.emit(el, shift(r), cap_style, cap_eff)


# --------------------------------------------------------------------------- routing (frame coordinates)


def _route(a: Rect, b: Rect, others: list[Rect], everyone: list[Rect], side_k: int, step: int) -> _Route:
    """Connector from node ``a`` to node ``b``; the rank axis points down."""
    if b.y >= a.bottom:  # forward: bottom-middle -> top-middle
        p0, p1 = (_cx(a), a.bottom), (_cx(b), b.y)
        if abs(p1[0] - p0[0]) <= 2:
            p1 = (p0[0], p1[1])
            if not _poly_hits([p0, p1], others):
                return _Route([p0, p1], "v", False, 0.5, p0, p1)
        else:
            lo, hi = p0[1], p1[1]
            for cy in _channel_centers(others, lo, hi):
                pts = [p0, (p0[0], cy), (p1[0], cy), p1]
                if not _poly_hits(pts, others):
                    return _Route(pts, "v", True, (cy - lo) / (hi - lo), p0, p1)
    elif a.y < b.bottom:  # same rank: side by side
        right = b.x >= a.right
        p0 = (a.right if right else a.x, _cy(a))
        p1 = (b.x if right else b.right, _cy(a))
        if not _poly_hits([p0, p1], others):
            return _Route([p0, p1], "h", False, 0.5, p0, p1)
    return _side_route(a, b, everyone, side_k, step)


def _channel_centers(others: list[Rect], lo: int, hi: int) -> list[int]:
    """Centers of the free bands between ``lo`` and ``hi`` (frame y), nearest to ``lo`` first."""
    cur = lo
    free: list[tuple[int, int]] = []
    for r in sorted(others, key=lambda r: r.y):
        if r.bottom <= lo or r.y >= hi:
            continue
        if r.y > cur:
            free.append((cur, min(r.y, hi)))
        cur = max(cur, r.bottom)
    if cur < hi:
        free.append((cur, hi))
    return [(u + v) // 2 for u, v in free if v > u]


def _side_route(a: Rect, b: Rect, everyone: list[Rect], side_k: int, step: int) -> _Route:
    """Out of the right side of ``a``, around the nodes, into the right side of ``b`` (route ``h``)."""
    ya, yb = _cy(a), _cy(b)
    lo, hi = min(ya, yb), max(ya, yb)
    ext = max(r.right for r in everyone if r.y <= hi and r.bottom >= lo)
    bend = ext + step * (side_k + 1)
    p0 = (a.right, ya)
    p1 = (b.right, yb)
    return _Route([p0, (bend, ya), (bend, yb), p1], "h", False, 0.5, p0, p1, side=True)


def _label_rect(
    rt: _Route,
    lw: int,
    lh: int,
    nodes: list[Rect],
    taken: list[Rect],
    off: int,
    lines: list[list[tuple[int, int]]],
) -> Rect:
    """Rect of an edge label next to its connector: never on the line, never over a node or another label."""
    segs = [(u, v) for u, v in zip(rt.pts, rt.pts[1:], strict=False) if u != v]
    if rt.side:
        order = [segs[1]] if len(segs) > 1 else segs
    elif rt.elbow:
        order = [segs[1], segs[0], segs[-1]] if len(segs) >= 3 else segs
    else:
        order = segs[:1]
    order = order + [s for s in segs if s not in order]
    toward = 1 if rt.p1[0] >= rt.p0[0] else -1
    if rt.side:
        toward = 1  # outer side of the loop
    cands: list[Rect] = []
    for u, v in order:
        fracs = (0.8, 0.6, 0.4) if rt.elbow and (u, v) == order[0] else (0.5, 0.75, 0.25)
        if u[0] == v[0]:  # vertical segment
            for frac in fracs:
                my = round(u[1] + (v[1] - u[1]) * frac)
                for s in (toward, -toward):
                    x = u[0] + off if s > 0 else u[0] - off - lw
                    cands.append(Rect(x, my - lh // 2, lw, lh))
        else:  # horizontal segment
            for frac in fracs:
                mx = round(u[0] + (v[0] - u[0]) * frac)
                for y in (u[1] - off - lh, u[1] + off):
                    cands.append(Rect(mx - lw // 2, y, lw, lh))
    margin = round(0.02 * IN)
    for r in cands:
        if (
            not any(_overlap(r, n, margin) for n in nodes)
            and not any(_overlap(r, t, margin) for t in taken)
            and not _poly_hits_any(lines, r)
        ):
            return r
    return cands[0]
