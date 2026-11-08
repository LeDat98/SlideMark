"""Mermaid flowcharts: text-sized nodes, rank-aware connectors and edge labels.

``place_diagram`` is called by the engine for a ``Container(classes=["diagram"])`` whose children are ``node``
texts. Nodes keep one shared size (diamonds another), are centered in their grid cell and joined edge to edge.
Everything is computed in a *frame* where the rank axis points down (TD); LR / BT / RL diagrams are the same
picture transposed or mirrored, so one routing code serves all four directions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..ir import Container, Shape, Style, Text, fast_style
from ..theme import DEFAULT_SIZES
from ..units import EMU_PER_INCH as IN
from ..units import EMU_PER_PT
from . import measure
from . import ports as PO
from .grid import Rect, parse_spec

MIN_W, MIN_H = 1.4, 0.55  # inches: smallest node
MAX_W = 3.4  # inches: node text wraps beyond this width
DIAMOND_MIN_W, DIAMOND_MIN_H = 1.9, 0.95
RANK_GAP, RANK_GAP_MAX = 0.45, 1.0  # inches between ranks (arrows must stay visible)
CROSS_GAP, CROSS_GAP_MAX = 0.3, 0.8  # inches between nodes of one rank
SIDE_STEP = 0.24  # inches between nested side routes (back edges)
CLR = round(0.125 * IN)  # 12 px: the least distance of a connector from a node it passes
MINSEG = round(0.22 * IN)  # the least straight run before an arrowhead and after leaving a node
SEP = round(0.125 * IN)  # the least distance of two parallel connectors
TOL = 1.01
RANK_GK_MIN = 0.75  # arrows between ranks keep at least this share of the base gap
STEP = round(0.04 * IN)  # node width search step
LABEL_MIN_PT = 10  # edge labels never shrink below this (or their own base size when that is smaller)
_SQUEEZE = [round(0.95 - 0.05 * i, 2) for i in range(14)]  # own fit: 0.95 .. 0.3
_GROW_STEPS_H = [1.5, 1.4, 1.3, 1.2, 1.1]  # height-only growth of the nodes
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
    side: bool = False  # a loop around the nodes: drawn as straight legs
    legs: bool = False  # an L-shaped connector: drawn as straight legs (a native elbow has two bends)


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


def _gaps(total: int, avail: int, mins: list[int], hi: int) -> list[int]:
    """Gaps between tracks: equal (at most ``hi``) when there is room, each at least its own minimum."""
    if not mins:
        return []
    room = avail - total
    lo_t, hi_t = 0, max(hi, max(mins))
    if sum(max(m, hi_t) for m in mins) <= room:
        return [max(m, hi_t) for m in mins]
    while lo_t < hi_t:  # largest common target whose gaps still fit
        mid = (lo_t + hi_t + 1) // 2
        if sum(max(m, mid) for m in mins) <= room:
            lo_t = mid
        else:
            hi_t = mid - 1
    return [max(m, lo_t) for m in mins]


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
        _place(ctx, E, c, area, inherit, pos, nr, nc, saved == 0)
    finally:
        ctx.depth = saved
    return True


@dataclass
class _Built:
    """One complete diagram layout (real coordinates, before it is shifted into its area)."""

    nodes: list[_Node]
    rects: dict[int, Rect]
    routes: list[tuple[int, _Route, bool]]
    labels: dict[int, Rect]  # link index -> real rect
    K: object  # the diagram kit look (label size) the labels were measured with
    bad: list[tuple[int, int]]  # links that refer to a missing node
    bx0: int
    by0: int
    bw: int
    bh: int


def _place(ctx, E, c: Container, area: Rect, inherit: Style, pos, nr: int, nc: int, top_level: bool) -> None:
    kids: list[Text] = c.children  # type: ignore[assignment]
    vertical, sgn = _orientation(c.links, pos)
    frame = _Frame(vertical, sgn)
    cap_style = E._role_style(ctx, "caption").merged(
        fast_style(align="center", valign="middle", padding="2pt")
    )

    def fits(b: _Built, tol: float = TOL) -> bool:
        return b.bw <= area.w * tol and b.bh <= area.h * tol

    # 1. natural size; on a slide that still fits at full size the diagram squeezes itself (font and node
    #    size together) instead of shrinking the whole slide: the text under it keeps its size
    def build(q: float = 1.0, sz: float = 1.0, body_pt: float = 1.0, szh: float = 1.0) -> _Built:
        return _build(ctx, E, c, area, inherit, pos, nr, nc, frame, cap_style, kids, q, sz, body_pt, szh)

    best = build()
    qf = 1.0
    if not fits(best):
        for q in _SQUEEZE if ctx.scale >= 1.0 and ctx.grow <= 1.0 else ():
            best, qf = build(q), q
            if fits(best, 1.0):
                break
    if fits(best) and top_level and ctx.scale >= 1.0 and ctx.dense_k >= 1.0 and ctx.lt.grow:
        # 2. sparse slide: grow the nodes (and their text, up to the theme body size) while the diagram fits
        body_pt = ctx.theme.sizes.get("body", DEFAULT_SIZES["body"])
        done = False
        grow_steps = [round(ctx.lt.diagram_grow - 0.1 * i, 2) for i in range(6)]  # 1.6 .. 1.1
        for sz in grow_steps if qf >= 1.0 else ():
            cand = build(sz=sz, body_pt=body_pt)
            if fits(cand, 1.0) and cand.bh <= area.h * ctx.lt.diagram_fill:
                best, done = cand, True
                break
        if not done:  # the width is the limit: taller nodes at the same text size
            for szh in _GROW_STEPS_H:
                cand = build(qf, szh=szh)
                if fits(cand, 1.0) and cand.bh <= area.h * ctx.lt.diagram_fill:
                    best = cand
                    break
    if not fits(best):
        ctx.over.append("diagram")
    for a, b in best.bad:
        ctx.diag(
            "link",
            f"connector {a}>{b} refers to a node that does not exist",
            "use node indices that exist in this diagram",
        )
    _emit(ctx, E, c, area, frame, cap_style, best)


def _build(
    ctx,
    E,
    c: Container,
    area: Rect,
    inherit: Style,
    pos,
    nr: int,
    nc: int,
    frame: _Frame,
    cap_style: Style,
    kids: list[Text],
    q: float,
    sz: float,
    body_pt: float,
    szh: float = 1.0,
) -> _Built:
    """Lay the flowchart out at squeeze ``q`` (<= 1) or node growth ``sz`` (>= 1; text up to body_pt)."""
    from . import diagramkit as DK  # (lazy: diagramkit imports the vocabulary, which imports this module)

    n = len(kids)
    vertical = not frame.t
    sgn = -1 if frame.m else 1
    # ---- node styles
    nodes: list[_Node] = []
    ks: list[float] = []
    scale = ctx.scale * q
    for el in kids:
        st = E._text_style(ctx, el, inherit)
        if (
            dn := ctx.theme.classes.get("diagram-node")
        ) is not None:  # `diagram-node.bold=on`: flowchart nodes only
            st = st.merged(dn)
        base = st.font_size or 18
        eff = measure.effective_scale(base, scale, ctx.theme.min_font_size)
        if q >= 1.0:
            eff = E._grown(ctx, el, eff)
        ks.append(eff if eff > 1.0 else max(min(scale, 1.0), 0.3))
        if sz > 1.0:  # bigger nodes: the text follows, but never beyond the theme body size
            eff *= max(1.0, min(sz, body_pt / max(base * eff, 1.0)))
        diamond = "decision" in el.classes
        pad = E._pad(st)
        if diamond:
            pad = round(2 * EMU_PER_PT * ctx.tight)
            st = st.merged(fast_style(padding=f"{round(pad / EMU_PER_PT, 2)}pt"))
        elif st.radius is None:
            st = st.merged(fast_style(radius=5))
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
    kb = max(ks)
    k = kb * max(sz, 1.0)
    gk = max(min(kb, 1.0), 0.5) * max(sz, 1.0)
    # ---- edge labels (sizes first: they widen the gaps between ranks): mono capitals of the diagram kit
    K = DK.look(ctx).scaled(min(scale, 1.0))
    lab_dims: dict[int, tuple[int, int]] = {}
    for i, ln in enumerate(c.links):
        text = " ".join((ln.label or "").split())
        if not text or ln.src not in pos or ln.dst not in pos or ln.src == ln.dst:
            continue
        lab_dims[i] = (
            DK.small_w(K, text, K.label, ctx.theme.diagram_label_track) + round(8 * EMU_PER_PT),
            round(K.label * 1.6 * EMU_PER_PT),
        )

    def rank_cross(i: int) -> tuple[int, int]:
        r, cc = pos[i]
        return (r, cc) if vertical else (cc, r)

    gap0 = round(RANK_GAP * IN * max(gk, RANK_GK_MIN))
    rank_min = [gap0] * max((nr if vertical else nc) - 1, 0)  # per gap between rank tracks (real index)
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
            need = ext + round(0.2 * IN) if straight else 2 * ext + round(0.1 * IN)
            for t in range(min(rs, rd), max(rs, rd)):  # only the gaps this connector crosses widen
                rank_min[t] = max(rank_min[t], need)
    gap_cross = round(CROSS_GAP * IN * gk)
    reserve = (round(n_side * SIDE_STEP * IN * gk) + round(0.15 * IN) + side_label) if n_side else 0
    x_min = [gap_cross] * (nc - 1) if vertical else rank_min
    y_min = rank_min if vertical else [gap_cross] * (nr - 1)
    res_x, res_y = (reserve, 0) if vertical else (0, reserve)
    # ---- node sizes
    min_w, min_h = round(MIN_W * IN * k), round(MIN_H * IN * k * szh)
    cap_w = max(round(0.6 * IN), (area.w - res_x - sum(x_min)) // max(nc, 1))
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
        floor = max(min_w, max(round(nd.ww) + 2 * nd.pad + round(0.1 * IN) for nd in rect_nodes))
        if w >= cap_w and w > floor:  # wrapped at the cap: the narrowest width with the same wrapping
            text_need = max(text_h(nd, w - 2 * nd.pad) for nd in rect_nodes)
            while w - STEP >= floor and (
                max(text_h(nd, round((w - STEP - 2 * nd.pad) * 0.9)) for nd in rect_nodes) <= text_need
            ):  # ... also when the renderer sets the text 10% wider than measured
                w -= STEP
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
            round(DIAMOND_MIN_H * IN * k * szh),
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

    gx = _gaps(sum(cw), area.w - res_x, x_min, round((CROSS_GAP_MAX if vertical else RANK_GAP_MAX) * IN * gk))
    gy = _gaps(sum(rh), area.h - res_y, y_min, round((RANK_GAP_MAX if vertical else CROSS_GAP_MAX) * IN * gk))
    xs, ys = [], []
    x = y = 0
    for j, wv in enumerate(cw):
        xs.append(x)
        x += wv + (gx[j] if j < len(gx) else 0)
    for j, hv in enumerate(rh):
        ys.append(y)
        y += hv + (gy[j] if j < len(gy) else 0)
    rects: dict[int, Rect] = {}
    for i, nd in enumerate(nodes):
        r, cc = pos[i]
        rects[i] = Rect(xs[cc] + (cw[cc] - nd.w) // 2, ys[r] + (rh[r] - nd.h) // 2, nd.w, nd.h)
    # ---- connectors and labels in the frame
    frects = {i: frame.rect(r) for i, r in rects.items()}
    bad: list[tuple[int, int]] = [
        (ln.src, ln.dst) for ln in c.links if ln.src not in frects or ln.dst not in frects or ln.src == ln.dst
    ]
    ok_links = [i for i, ln in enumerate(c.links) if (ln.src, ln.dst) not in bad]
    by_link = _route_all(c.links, ok_links, frects, round(SIDE_STEP * IN * gk))
    routes: list[tuple[int, _Route, bool]] = [(i, by_link[i], not by_link[i].side) for i in ok_links]
    real_polys = {i: [frame.unpt(p) for p in rt.pts] for i, rt, _g in routes}
    obstacles = list(rects.values())
    for pts in real_polys.values():
        obstacles += PO.segment_rects(pts)
    label_real: dict[int, Rect] = {}
    for i, _rt, _g in routes:
        if i not in lab_dims:
            continue
        lw, lh = lab_dims[i]
        r_, _clear = DK.place_label(real_polys[i], lw, lh, obstacles)
        label_real[i] = r_
        obstacles.append(r_)
    # ---- bounding box
    all_real: list[Rect] = list(rects.values())
    for _i, rt, _g in routes:
        for p in rt.pts:
            q_ = frame.unpt(p)
            all_real.append(Rect(q_[0], q_[1], 0, 0))
    all_real += list(label_real.values())
    bx0, by0 = min(r.x for r in all_real), min(r.y for r in all_real)
    bx1, by1 = max(r.right for r in all_real), max(r.bottom for r in all_real)
    return _Built(nodes, rects, routes, label_real, K, bad, bx0, by0, bx1 - bx0, by1 - by0)


def _emit(ctx, E, c: Container, area: Rect, frame: _Frame, cap_style: Style, b: _Built) -> None:
    """Shift the layout into ``area`` (centered across, top-anchored along the page) and emit it."""
    from . import diagramkit as DK  # (lazy: diagramkit imports the vocabulary, which imports this module)
    from . import vocab as V

    dx = area.x + max(area.w - b.bw, 0) // 2 - b.bx0
    dy = area.y - b.by0  # top-anchored: the leftover stays below (the slide policy moves very sparse slides)

    def shift(r: Rect) -> Rect:
        return Rect(r.x + dx, r.y + dy, r.w, r.h)

    rects, routes, label_real, nodes = b.rects, b.routes, b.labels, b.nodes
    # ---- emit: card, nodes, connectors, labels
    pad = (
        2 * 9525
    )  # the legs of a loop overlap at their corners: the card holds them (rows move blocks, not parts)
    card = Rect(b.bx0 + dx - pad, b.by0 + dy - pad, b.bw + 2 * pad, b.bh + 2 * pad)
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
        if rt.side or rt.legs:  # a loop or an L: straight segments render the same everywhere
            pts = [frame.unpt(p) for p in rt.pts]
            pts = [(x + dx, y + dy) for x, y in pts]
            last = len(pts) - 2
            for s_i, (u, v) in enumerate(zip(pts, pts[1:], strict=False)):
                ex = (v[0] > u[0]) - (v[0] < u[0])
                ey = (v[1] > u[1]) - (v[1] < u[1])
                if s_i > 0:  # legs overlap at the corners so they stay closed
                    u = (u[0] - ex * 9525, u[1] - ey * 9525)
                if s_i < last:
                    v = (v[0] + ex * 9525, v[1] + ey * 9525)
                attrs = {
                    "head": head if s_i == last else "none",
                    "flip_h": v[0] < u[0],
                    "flip_v": v[1] < u[1],
                    "side": True,
                }
                box = Rect(min(u[0], v[0]), min(u[1], v[1]), abs(v[0] - u[0]), abs(v[1] - u[1]))
                ctx.emit(
                    Shape(shape="line", attrs=attrs),
                    box,
                    fast_style(
                        line=ctx.theme.render.connector_color, line_width=ctx.theme.render.connector_width
                    ),
                )
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
        ctx.emit(
            Shape(shape="line", attrs=attrs),
            box,
            fast_style(line=ctx.theme.render.connector_color, line_width=ctx.theme.render.connector_width),
        )
    K = b.K
    size, tr = K.label, ctx.theme.diagram_label_track
    st = V._text_style(ctx, size, align="center", valign="middle", padding="0pt", fill="bg")
    for i, r in label_real.items():
        text = " ".join((c.links[i].label or "").split())
        el = Text(
            role="caption",
            paragraphs=[DK.small_para(ctx, K, text, size, tr)],
            attrs={"shape_name": f"Flow edge {i + 1} label", "nowrap": True},
        )
        ctx.emit(el, shift(r), st)


# --------------------------------------------------------------------------- routing (frame coordinates)


def _infl(r: Rect, m: int) -> Rect:
    return Rect(r.x - m, r.y - m, r.w + 2 * m, r.h + 2 * m)


def _segs(pts: list[tuple[int, int]]) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    return [(u, v) for u, v in zip(pts, pts[1:], strict=False) if u != v]


def _clear(pts: list[tuple[int, int]], a: Rect, b: Rect, others: list[Rect]) -> bool:
    """No segment passes within ``CLR`` of another node; none but the first / last grazes ``a`` / ``b``."""
    segs = _segs(pts)
    if not segs:
        return False
    if any(_hits(u, v, _infl(r, CLR)) for r in others for u, v in segs):
        return False
    ia, ib = _infl(a, CLR), _infl(b, CLR)
    last = len(segs) - 1
    for k, (u, v) in enumerate(segs):
        if k > 0 and _hits(u, v, ia):
            return False
        if k < last and _hits(u, v, ib):
            return False
    if last > 0 and (_hits(*segs[0], ib) or _hits(*segs[-1], ia)):
        return False
    return True


def _min_run(pts: list[tuple[int, int]], minseg: int) -> bool:
    """The first and the last straight run (before the arrowhead) are at least ``minseg`` long."""
    segs = _segs(pts)
    if len(segs) < 2:
        return True
    ln = [abs(v[0] - u[0]) + abs(v[1] - u[1]) for u, v in segs]
    return ln[0] >= minseg and ln[-1] >= minseg


def _clash(p: list[tuple[int, int]], q: list[tuple[int, int]]) -> bool:
    """Two connectors run side by side closer than ``SEP`` (or on top of each other) over some length."""
    for u, v in _segs(p):
        for s, t in _segs(q):
            if u[1] == v[1] and s[1] == t[1]:
                if abs(u[1] - s[1]) < SEP and min(max(u[0], v[0]), max(s[0], t[0])) > max(
                    min(u[0], v[0]), min(s[0], t[0])
                ):
                    return True
            elif u[0] == v[0] and s[0] == t[0]:
                if abs(u[0] - s[0]) < SEP and min(max(u[1], v[1]), max(s[1], t[1])) > max(
                    min(u[1], v[1]), min(s[1], t[1])
                ):
                    return True
    return False


def _levels(lo: int, hi: int, others: list[Rect], minseg: int) -> list[int]:
    """Candidate levels (frame y) for the bend of a connector from ``lo`` to ``hi``: the middle of every free
    band first, then positions on either side of it; each keeps ``minseg`` from both ends."""
    out: list[int] = []
    for u, v in _channel_bands(others, lo, hi):
        top = max(u + (CLR if u != lo else 0), lo + minseg)
        bot = min(v - (CLR if v != hi else 0), hi - minseg)
        if top > bot:
            continue
        mid = (top + bot) // 2
        out.append(mid)
        for k in range(1, 6):
            d = round(1.5 * SEP * k)
            out += [y for y in (mid + d, mid - d) if top <= y <= bot]
    return out


def _candidates(
    a: Rect, b: Rect, others: list[Rect], prefer_l: bool, prefer_in: bool, minseg: int
) -> list[_Route]:
    """Routes of a forward connector (``b`` below ``a``), best first; every end is the middle of a side."""
    acx, bcx, acy, bcy = _cx(a), _cx(b), _cy(a), _cy(b)
    p0, p1 = (acx, a.bottom), (bcx, b.y)
    straight: list[_Route] = []
    if abs(bcx - acx) <= round(0.03 * IN):
        straight.append(_Route([p0, (acx, b.y)], "v", False, 0.5, p0, (acx, b.y)))
    elbows = [
        _Route([p0, (acx, y), (bcx, y), p1], "v", True, (y - p0[1]) / max(p1[1] - p0[1], 1), p0, p1)
        for y in _levels(a.bottom, b.y, others, minseg)
    ]
    legs: list[_Route] = []
    if bcx != acx:
        sx = a.right if bcx > acx else a.x  # leave through the side that faces the target
        q0 = (sx, acy)
        legs.append(_Route([q0, (bcx, acy), p1], "v", False, 0.5, q0, p1, legs=True))
        ex = (
            b.x if acx < b.x else b.right if acx > b.right else None
        )  # arrive through the side facing the source
        if ex is not None:
            r1 = (ex, bcy)
            legs.append(_Route([p0, (acx, bcy), r1], "v", False, 0.5, p0, r1, legs=True))
    if prefer_l:
        return straight + legs[:1] + elbows + legs[1:]
    if prefer_in:
        return straight + legs[1:] + elbows + legs[:1]
    return straight + elbows + legs


def _route_all(links: list, idx: list[int], frects: dict[int, Rect], step: int) -> dict[int, _Route]:
    """Route every link (frame coordinates, rank axis down). Connectors never pass closer than ``CLR`` to a
    node, never run along one, keep a straight run of ``MINSEG`` before the head, leave a node that fans out
    through different sides (no shared trunk) and arrive at the middle of a side."""
    out: dict[int, _Route] = {}
    fan_out: dict[int, int] = {}
    fan_in: dict[int, int] = {}
    fwd: dict[int, bool] = {}
    for i in idx:
        ln = links[i]
        a, b = frects[ln.src], frects[ln.dst]
        fwd[i] = b.y >= a.bottom
        if fwd[i]:
            fan_out[ln.src] = fan_out.get(ln.src, 0) + 1
            fan_in[ln.dst] = fan_in.get(ln.dst, 0) + 1

    def rank(i: int) -> tuple[int, int]:
        ln = links[i]
        a, b = frects[ln.src], frects[ln.dst]
        if not fwd[i]:
            return (3, i)
        if abs(_cx(b) - _cx(a)) <= round(0.03 * IN):
            return (0, i)  # a straight connector keeps the middle of its sides
        if fan_out[ln.src] > 1 or fan_in[ln.dst] > 1:
            return (1, i)
        return (2, i)

    taken: list[list[tuple[int, int]]] = []
    side_k = 0
    for i in sorted(idx, key=rank):
        ln = links[i]
        a, b = frects[ln.src], frects[ln.dst]
        others = [r for j, r in frects.items() if j not in (ln.src, ln.dst)]
        everyone = list(frects.values())
        rt: _Route | None = None
        if fwd[i]:
            minseg = min(MINSEG, max(round(0.1 * IN), round((b.y - a.bottom) * 0.4)))
            cands = _candidates(
                a, b, others, fan_out[ln.src] > 1, fan_in[ln.dst] > 1 and fan_out[ln.src] <= 1, minseg
            )
            for strict in (3, 2, 1):  # relax: no clash, then no minimum run, then clearance only
                for cand in cands:
                    if not _clear(cand.pts, a, b, others):
                        continue
                    if strict >= 2 and not _min_run(cand.pts, minseg):
                        continue
                    if strict >= 3 and any(_clash(cand.pts, t) for t in taken):
                        continue
                    rt = cand
                    break
                if rt is not None:
                    break
        elif a.y < b.bottom:  # same rank: side by side
            right = b.x >= a.right
            p0 = (a.right if right else a.x, _cy(a))
            p1 = (b.x if right else b.right, _cy(b))
            if p0[1] == p1[1] and not _poly_hits([p0, p1], others):
                rt = _Route([p0, p1], "h", False, 0.5, p0, p1)
        if rt is None:
            rt = _side_route(a, b, everyone, side_k, step, taken)
            side_k += 1
        taken.append(rt.pts)
        out[i] = rt
    return out


def _channel_bands(others: list[Rect], lo: int, hi: int) -> list[tuple[int, int]]:
    """The free bands between ``lo`` and ``hi`` (frame y), nearest to ``lo`` first."""
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
    return [(u, v) for u, v in free if v > u]


def _side_route(
    a: Rect, b: Rect, everyone: list[Rect], side_k: int, step: int, taken: list[list[tuple[int, int]]]
) -> _Route:
    """A loop around the nodes (a back edge, or a connector that would cross a node): out of the right side of
    ``a`` into the right side of ``b``; else around the left; else down below the nodes and up the left."""
    ya, yb = _cy(a), _cy(b)
    lo, hi = min(ya, yb), max(ya, yb)
    near = [r for r in everyone if r.y <= hi and r.bottom >= lo]
    others = [r for r in everyone if r is not a and r is not b]
    k = step * (side_k + 1)
    right_bend = max(r.right for r in near) + k
    left_bend = min(r.x for r in near) - k
    low = max(r.bottom for r in everyone) + k
    cands = [
        [(a.right, ya), (right_bend, ya), (right_bend, yb), (b.right, yb)],
        [(a.x, ya), (left_bend, ya), (left_bend, yb), (b.x, yb)],
        [(_cx(a), a.bottom), (_cx(a), low), (left_bend, low), (left_bend, yb), (b.x, yb)],
    ]
    for strict in (True, False):
        for pts in cands:
            if _clear(pts, a, b, others) and not (strict and any(_clash(pts, t) for t in taken)):
                return _Route(pts, "h", False, 0.5, pts[0], pts[-1], side=True)
    pts = cands[0]
    return _Route(pts, "h", False, 0.5, pts[0], pts[-1], side=True)


# --------------------------------------------------------------------------- slide-level trees (a>b links)

_CHROME_ROLES = ("title", "subtitle", "lead", "conclusion", "footnote", "caption")


def fill_tree(items: list, body: Rect, lt, reserve: int = 0) -> list:
    """Org chart / issue tree (``@a>b b>c`` boxes) on a slide with room: grow it down the body, top-anchored.

    Box heights, the gaps between levels, the box text (heading + body) and a lone root box grow, each capped
    by a ``layout.tree_*`` token; connectors are re-attached (bottom-middle to top-middle). Anything unusual
    (side-by-side links, icons, other blocks on the slide, a slide that is already full) returns ``items``
    unchanged. Never raises.
    """
    try:
        return _fill_tree(items, body, lt, reserve)
    except Exception:
        return items


def _rect4(p) -> tuple[int, int, int, int]:
    return (p.x, p.y, p.w, p.h)


def _tree_text_h(p, width: int, scale: float) -> float:
    from . import css

    ph, pv = css.inset_hv(p.style)
    return measure.paragraphs_height(p.element.paragraphs, max(width - ph, 1), p.style, scale) + pv


def _one_line_width(q, w0: int, cap: int, tf: float) -> int:
    """Smallest box width in [w0, cap] that keeps heading ``q`` on one line at scale ``tf``."""
    sc = q.font_scale * tf
    one = _tree_text_h(q, 10**9, sc)
    if _tree_text_h(q, w0, sc) <= one * 1.01:
        return w0
    if _tree_text_h(q, cap, sc) > one * 1.01:
        return cap
    lo, hi = w0, cap
    while hi - lo > 20000:
        mid = (lo + hi) // 2
        if _tree_text_h(q, mid, sc) <= one * 1.01:
            hi = mid
        else:
            lo = mid
    return hi


def _tree_stack(
    items: list, b: int, ms: list[int], dw: int, tf: float, shrink: bool = False, hug: bool = False
) -> tuple[list[tuple[int, int, int]], int]:
    """Text of box ``b`` at factor ``tf`` and ``dw`` more width: ([(item, y offset, height)], used height).

    The heading band grows with its text; the gaps between paragraphs and the padding scale with ``tf``.
    """
    box = items[b]
    res: list[tuple[int, int, int]] = []
    cursor = 0
    prev = box.y  # bottom of the previous member in the old geometry
    lead_pad = 0  # air between the heading band and the first body paragraph (old geometry)
    for n, j in enumerate(ms):
        q = items[j]
        w = q.w + dw
        grow = 0
        if tf > 1.0 or (dw and shrink):  # a box widened to fit its heading unwraps: the shrink counts
            grow = round(_tree_text_h(q, w, q.font_scale * tf) - _tree_text_h(q, q.w, q.font_scale))
        head = n == 0 and getattr(q.element, "role", "") == "heading" and q.y - box.y <= 2
        if not head:
            cursor += round(max(q.y - prev, 0) * tf)
            if not lead_pad and n > 0:
                lead_pad = round(max(q.y - prev, 0) * tf)
        res.append((j, cursor, q.h + grow))
        cursor += q.h + grow
        prev = q.y + q.h
    last = items[ms[-1]] if ms else None
    tail = max(box.y + box.h - (last.y + last.h), 0) if last is not None else 0
    if shrink and dw and last is not None:  # stretched before: keep only its real bottom padding
        from . import css

        tail = min(tail, css.insets(box.style)[3] * 2)
    if hug and last is not None and lead_pad:  # even air above and below the body text
        return res, cursor + min(round(tail * tf), lead_pad)
    return res, cursor + round(tail * tf)


def _fill_tree(items: list, body: Rect, lt, reserve: int) -> list:
    from ..ir import Container as C
    from .vfill import _contains, _is_line

    if lt.tree_fill <= 0 or body.h <= 0:
        return items
    lines = [i for i, p in enumerate(items) if _is_line(p) and p.element.attrs.get("src_box")]
    if not lines:
        return items
    for i in lines:
        a = items[i].element.attrs
        sb, db = a["src_box"], a["dst_box"]
        if a.get("route") != "v" or db[1] < sb[1] + sb[3]:
            return items  # only downward links
    by_rect = {_rect4(p): i for i, p in enumerate(items) if isinstance(p.element, C)}
    boxes: dict[tuple, int] = {}
    for i in lines:
        for k in ("src_box", "dst_box"):
            r = tuple(items[i].element.attrs[k])
            if r not in by_rect:
                return items
            boxes[r] = by_rect[r]
    members: dict[int, list[int]] = {b: [] for b in boxes.values()}
    owned = set(lines) | set(boxes.values())
    for j, p in enumerate(items):
        if j in owned:
            continue
        for b in members:
            if _contains(items[b], p):
                if not isinstance(p.element, Text) or not p.element.paragraphs:
                    return items  # icons, nested boxes, pictures: leave the tree alone
                members[b].append(j)
                break
        else:
            el = p.element
            chrome = p.y < body.y - 2 or (
                isinstance(el, Text) and (el.role in _CHROME_ROLES or el.attrs.get("field"))
            )
            if not chrome:
                return items  # another block shares the slide: the tree does not own the body
    for b in members:
        members[b].sort(key=lambda j: items[j].y)
    # ---- levels
    order = sorted(boxes.values(), key=lambda i: (items[i].y, items[i].x))
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
    top0 = min(items[i].y for i in order)
    row_h = [max(items[i].h for i in r) for r in rows]
    row_y = [min(items[i].y for i in r) for r in rows]
    gaps = [row_y[k + 1] - (row_y[k] + row_h[k]) for k in range(len(rows) - 1)]
    if any(g < 0 for g in gaps):
        return items
    cur = row_y[-1] + row_h[-1] - top0
    target = min(round(lt.tree_fill * body.h), body.bottom - reserve - top0)
    if target <= cur * 1.03:
        return items  # no slack: dense trees stay as they are
    hb, gs = sum(row_h), sum(gaps)
    sb = min(target / cur, lt.tree_box_grow)
    sg = 1.0
    if gs > 0:
        sg = max(1.0, min((target - hb * sb) / gs, lt.tree_gap_grow))
    sb = max(1.0, min((target - gs * sg) / hb, lt.tree_box_grow))
    # ---- widths: a lone box of a level (the root) may be wider, until its heading fits one line
    row_of = {b: k for k, r in enumerate(rows) for b in r}
    lone = [r[0] for r in rows if len(r) == 1 and len(rows) > 1 and lt.tree_wide > 1.0]

    kids: dict[int, list[int]] = {}
    for i in lines:
        a = items[i].element.attrs
        kids.setdefault(by_rect[tuple(a["src_box"])], [])
        if by_rect[tuple(a["dst_box"])] not in kids[by_rect[tuple(a["src_box"])]]:
            kids[by_rect[tuple(a["src_box"])]].append(by_rect[tuple(a["dst_box"])])

    def _balance(res: dict[int, tuple[int, int]]) -> dict[int, tuple[int, int]]:
        """Siblings of one parent get the widest sibling's width (when the row stays clear);
        parents are centered over their children, as wide as ``tree_parent_span`` of the children's span
        but never wider than that span (nor narrower than they already are)."""
        if lt.tree_parent_span <= 0:
            return res
        orig = dict(res)
        for ks in kids.values():
            if len(ks) > 1:
                w = max(res[k][1] for k in ks)
                eq = {k: (res[k][0] + res[k][1] // 2 - w // 2, w) for k in ks}
                rest = [(res[k][0], res[k][1]) for k in order if k not in eq and row_of[k] == row_of[ks[0]]]
                xs = sorted([*eq.values(), *rest])
                ok = xs[0][0] >= body.x and xs[-1][0] + xs[-1][1] <= body.right
                ok = ok and all(xs[n][0] + xs[n][1] <= xs[n + 1][0] for n in range(len(xs) - 1))
                if ok:
                    res.update(eq)
        for k in range(len(rows) - 2, -1, -1):  # bottom-up: a parent follows its (final) children
            for b in rows[k]:
                ks = kids.get(b)
                if not ks:
                    continue
                left = min(res[c][0] for c in ks)
                right = max(res[c][0] + res[c][1] for c in ks)
                span = right - left
                w = res[b][1]
                if w < span:
                    w = min(max(w, round(lt.tree_parent_span * span)), span) if len(ks) > 1 else span
                res[b] = (min(max((left + right) // 2 - w // 2, body.x), max(body.right - w, body.x)), w)
        for r in rows:  # a row that now overlaps keeps its old widths
            xs = sorted(res[b] for b in r)
            if any(xs[n][0] + xs[n][1] > xs[n + 1][0] for n in range(len(xs) - 1)):
                return orig
        return res

    fitted: set[int] = set()  # lone boxes widened beyond the usual factor to keep their heading on one line

    def widths(tf: float) -> dict[int, tuple[int, int]]:
        fitted.clear()
        res: dict[int, tuple[int, int]] = {i: (items[i].x, items[i].w) for i in order}
        for b in lone:
            p = items[b]
            cap = max(round(lt.tree_wide_max * body.w), p.w)
            w = min(round(p.w * lt.tree_wide), cap) if p.w < cap else p.w
            heads = [items[j] for j in members[b] if getattr(items[j].element, "role", "") == "heading"]
            if heads and lt.tree_head_fit > 0:
                cap = max(cap, round(lt.tree_head_fit * body.w))
                fit = _one_line_width(heads[0], p.w, cap, tf)
                if fit > w:
                    w = fit
                    fitted.add(b)
            w = min(w, cap)
            res[b] = (min(max(p.x + p.w // 2 - w // 2, body.x), max(body.right - w, body.x)), w)
        return _balance(res)

    new_x = widths(1.0)

    def pt(p, tf: float) -> float:
        return (p.style.font_size or 14) * p.font_scale * tf

    def fits(tf: float) -> bool:
        wx = widths(tf)
        for b, ms in members.items():
            dw = wx[b][1] - items[b].w
            stack, used = _tree_stack(items, b, ms, dw, tf, b in fitted, lt.tree_hug)
            if used > round(row_h[row_of[b]] * sb):
                return False
            for j in ms:
                p = items[j]
                cap = lt.sparse_text_max_pt if p.element.role == "heading" else lt.l3_text_max_pt
                if pt(p, tf) > max(cap, pt(p, 1.0)):
                    return False
                w = p.w + dw
                m0, m1 = _tree_text_h(p, w, p.font_scale), _tree_text_h(p, w, p.font_scale * tf)
                if m1 > m0 * tf * 1.06:
                    return False  # growing would add a wrapped line
        return True

    tf = 1.0
    for k in range(max(round((min(lt.tree_text_max, measure.ceiling(lt)) - 1.0) / 0.05), 0), 0, -1):
        if fits(round(1.0 + 0.05 * k, 2)):
            tf = round(1.0 + 0.05 * k, 2)
            break
    new_x = widths(tf)
    # ---- row heights: boxes keep an airy fit around their text, the rest of the growth goes to the gaps
    nhs: list[int] = []
    for k, r in enumerate(rows):
        need = max(
            _tree_stack(items, b, members[b], new_x[b][1] - items[b].w, tf, b in fitted, lt.tree_hug)[1]
            for b in r
        )
        floor, air = (0 if lt.tree_hug else row_h[k]), lt.tree_box_air
        if r[0] in fitted and len(r) == 1:
            floor, air = min(floor, round(need)), 1.0  # a widened lone box gives back the height it unwrapped
        nhs.append(min(round(row_h[k] * sb), max(floor, round(need * air))))
    if gs > 0:
        sg = max(1.0, min((target - sum(nhs)) / gs, lt.tree_gap_grow))
    left = target - sum(nhs) - round(gs * sg)
    if left > 0 and lt.tree_box_air_max > lt.tree_box_air:  # gaps are capped: the boxes take the rest
        caps = []
        for k, r in enumerate(rows):
            need = max(
                _tree_stack(items, b, members[b], new_x[b][1] - items[b].w, tf, b in fitted)[1] for b in r
            )
            caps.append(max(nhs[k], min(round(row_h[k] * sb), round(need * lt.tree_box_air_max))) - nhs[k])
        tot = sum(caps)
        if tot > 0:
            take = min(left, tot) / tot
            nhs = [h + round(c * take) for h, c in zip(nhs, caps, strict=True)]
    # ---- new geometry
    out = list(items)
    new_rect: dict[tuple, tuple[int, int, int, int]] = {}
    y = top0
    for k, r in enumerate(rows):
        nh = nhs[k]
        for b in r:
            p = items[b]
            bx, bw = new_x[b]
            out[b] = p.model_copy(update={"x": bx, "y": y, "w": bw, "h": nh})
            new_rect[_rect4(p)] = (bx, y, bw, nh)
            stack, used = _tree_stack(items, b, members[b], bw - p.w, tf, b in fitted, lt.tree_hug)
            spare = max(nh - used, 0)
            shift = round(spare * lt.tree_pad_share)  # part of the growth is padding above the body text
            for n, (j, off, h) in enumerate(stack):
                q = items[j]
                head = n == 0 and q.element.role == "heading" and q.y - p.y <= 2
                out[j] = q.model_copy(
                    update={
                        "x": q.x + (bx - p.x),
                        "y": y + off + (0 if head else shift),
                        "w": q.w + (bw - p.w),
                        "h": h,
                        "font_scale": q.font_scale * tf,
                    }
                )
        y += nh + (round(gaps[k] * sg) if k < len(gaps) else 0)
    # ---- connectors: bottom-middle of the parent to top-middle of the child
    tol = round(0.03 * IN)
    all_new = list(new_rect.values())
    for i in lines:
        p = items[i]
        a = p.element.attrs
        ra, rb = new_rect[tuple(a["src_box"])], new_rect[tuple(a["dst_box"])]
        p0 = (ra[0] + ra[2] // 2, ra[1] + ra[3])
        p1 = (rb[0] + rb[2] // 2, rb[1])
        elbow = abs(p1[0] - p0[0]) > tol
        if not elbow:
            p1 = (p0[0], p1[1])
        else:  # the bend must stay clear of every other box
            cy = p0[1] + round((p1[1] - p0[1]) * a.get("adj", 0.5))
            pts = [p0, (p0[0], cy), (p1[0], cy), p1]
            if _poly_hits(pts, [Rect(*bx) for bx in all_new if bx not in (ra, rb)]):
                return items
        attrs = {
            **a,
            "flip_h": p1[0] < p0[0],
            "flip_v": False,
            "elbow": elbow,
            "src_box": list(ra),
            "dst_box": list(rb),
        }
        out[i] = p.model_copy(
            update={
                "element": p.element.model_copy(update={"attrs": attrs}),
                "x": min(p0[0], p1[0]),
                "y": p0[1],
                "w": abs(p1[0] - p0[0]),
                "h": p1[1] - p0[1],
            }
        )
    return out
