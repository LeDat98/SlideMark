"""Composition vocabulary, wave 2026-11-08 lane D: ``@arch`` (layered architecture) and ``@venn``.

Same contract as ``vocab.py`` / ``vocab4.py`` (``vocab.py`` dispatches here): a composer works on the body
rectangle with its own context, names every shape (``Arch tier 1`` / ``Arch tier 1 label`` /
``Arch node API gateway`` / ``Arch edge 2`` / ``Arch edge 2 label``; ``Venn 1 set`` / ``Venn 1 name`` /
``Venn 1 text`` / ``Venn overlap`` / ``Venn overlap fill``) so ``importer/vocab.py`` can fold them back,
reads every number from a token (``forms6.py``) and never raises on bad input (a slide that lacks what the
form needs is laid out as ordinary blocks; the parser warned).

Arrows reuse the connector router of ``@ a>b`` (``engine._emit_links``): orthogonal elbows glued to the node
rectangles, bends in a free channel; the arrow colour is ``render.connector_color``.
"""

from __future__ import annotations

import itertools
import math
import re
from typing import Any

from .. import forms, forms6
from ..ir import Paragraph, Run, Shape, Slide, Text, fast_style
from ..units import EMU_PER_PT
from . import diagramkit as DK
from . import measure
from . import ports as PO
from . import vocab as V
from .grid import Rect

_IN = 914400


def _tw(text: str, size_pt: float, bold: bool = False) -> int:
    """Width (EMU) of ``text`` on one line at ``size_pt``."""
    if measure.has_cjk(text):
        em = sum(1.0 if ord(ch) > 0x2E80 else measure.text_em(ch, bold) for ch in text)
    else:
        em = measure.text_em(text, bold)
    return round(em * size_pt * EMU_PER_PT)


def _class_style(th, classes: list[str]):
    out = fast_style()
    for n in classes:
        if n in th.classes:
            out = out.merged(th.classes[n])
    return out


# --------------------------------------------------------------------------- @arch


class _Plan:
    __slots__ = (
        "k",
        "w",
        "h",
        "rows",
        "per",
        "gn",
        "gt",
        "pad",
        "lw",
        "tier_h",
        "tier_w",
        "total_w",
        "total_h",
        "ok",
        "capn",
        "labw",
    )

    def __init__(self, **kw: Any) -> None:
        for k in self.__slots__:
            setattr(self, k, kw.get(k))


def _arch(c, slide: Slide, body: Rect, sg: int, info: dict) -> bool:
    th = c.theme
    A = forms6.parse_arch(slide)
    if A is None or not A.nodes:
        return False
    cols = forms.words(slide.attrs, "arch", "dir") == "h"
    edges, _bad = forms6.parse_edges(forms6.edge_text(slide), A)
    n = len(A.tiers)
    K0 = DK.look(c, slide)
    pinned = bool(forms.num(slide.attrs, "size"))
    pad = V._emu(th.arch_tier_pad)
    labelled = [e for e in edges if e.label]
    own_band = bool(th.arch_tier_fill and th.arch_tier_fill != "none") or bool(th.arch_tier_line)
    want = th.arch_tier_look
    if want == "auto" and own_band:
        want = "band"

    def look_of(i: int) -> str:  # how tier i is drawn: caption | box | band
        if want != "auto":
            return want
        return "box" if cols and len(A.tiers[i][1]) >= 2 else "caption"

    looks = [look_of(i) for i in range(n)]
    has_title = [bool(A.tiers[i][0]) for i in range(n)]
    tag_h = [0]

    # the most elbows (arrows that change column) any two neighbouring tiers share: each needs a level
    tier_of = {id(nd): ti for ti, (_t, r_) in enumerate(A.tiers) for nd in r_}
    stacked = 1
    for g in range(max(n - 1, 0)):
        m_ = sum(
            1
            for e in edges
            if min(tier_of[id(A.nodes[e.src])], tier_of[id(A.nodes[e.dst])])
            <= g
            < max(tier_of[id(A.nodes[e.src])], tier_of[id(A.nodes[e.dst])])
        )
        stacked = max(stacked, m_)
    if cols:
        stacked = 1

    def plan(k: float) -> _Plan:
        K = K0.scaled(k)
        tag_h[0] = DK.tag_size(K, "X")[1]
        cap_h = round(K.label * 1.6 * DK.PT)
        gn = V._emu(th.arch_node_gap)
        same = [e for e in labelled if A.nodes[e.src].tier == A.nodes[e.dst].tier]
        labw = max(
            (DK.small_w(K, e.label or "", K.label, th.diagram_label_track) for e in labelled), default=0
        )
        if same:  # a label on an arrow between neighbours of a tier needs its width between the nodes
            gn = max(
                gn,
                max(DK.small_w(K, e.label or "", K.label, th.diagram_label_track) for e in same)
                + round(0.3 * _IN),
            )
        gt = V._emu(th.arch_gap) if th.arch_gap else 0
        if not gt:
            if cols:
                gt = max(round(0.55 * _IN), labw + round(0.6 * _IN)) if labelled else round(0.55 * _IN)
                gt = min(gt, round(2.2 * _IN))
            else:
                gt = round((0.55 if labelled else 0.45) * _IN)
                gt = max(gt, round((0.2 + 0.3 * stacked) * _IN))
        nat = max(DK.node_width(c, K, nd.name, nd.sub, nd.tag) for nd in A.nodes)
        w = V._emu(th.arch_node_w) if th.arch_node_w else min(max(nat, round(1.3 * _IN)), round(2.6 * _IN))
        lw = 0
        boxed = [lk != "caption" for lk in looks]
        if cols:
            avail = body.w - (n - 1) * gt - 2 * n * pad
            if not th.arch_node_w:
                w = max(min(w, avail // n), round(1.1 * _IN))
        else:
            cap_w = max(
                (DK.small_w(K, t, K.label, th.diagram_label_track) for t, _ in A.tiers if t), default=0
            )
            lw = 0 if all(boxed) else (cap_w + round(0.2 * _IN) if cap_w else 0)
            avail = body.w - lw - 2 * pad
            kmax = max(len(r) for _, r in A.tiers)
            if not th.arch_node_w and kmax * (w + gn) - gn > avail:
                w = max(min(w, (avail - (kmax - 1) * gn) // kmax), round(1.1 * _IN))
            w = min(w, avail)
        h = V._emu(th.arch_node_h) if th.arch_node_h else 0
        if not h:
            h = max(
                DK.node_need(
                    c, K, DK.node_paras(c, K, nd.name, nd.sub), w, bool(nd.tag), tag_h[0], nd.classes
                )
                for nd in A.nodes
            )
            h = max(h, round(2.9 * K.name * DK.PT))
        per, rows, tier_h, tier_w = [], [], [], []
        if cols:
            for i, (_t, r) in enumerate(A.tiers):
                per.append(1)
                rows.append(len(r))
                inner = len(r) * h + (len(r) - 1) * gn
                head = cap_h + round(0.5 * pad) if has_title[i] else 0
                tier_h.append(inner + head + (2 * pad if boxed[i] else 0))
                tier_w.append(w + (2 * pad if boxed[i] else 0))
            total_h = max(tier_h)
            total_w = sum(tier_w) + gt * (n - 1)
        else:
            for i, (_t, r) in enumerate(A.tiers):
                m = max(1, (avail + gn) // (w + gn))
                kk = len(r)
                nrows = -(-kk // m)
                rows.append(nrows)
                per.append(-(-kk // nrows))
                inner = nrows * h + (nrows - 1) * gn
                head = cap_h + round(0.5 * pad) if boxed[i] and has_title[i] else 0
                tier_h.append(inner + head + (2 * pad if boxed[i] else 0))
            widest = max(per[i] * w + (per[i] - 1) * gn + (2 * pad if boxed[i] else 0) for i in range(n))
            tier_w = [lw + widest] * n
            total_w = lw + widest
            total_h = sum(tier_h) + gt * (n - 1)
        return _Plan(
            k=k, w=w, h=h, rows=rows, per=per, gn=gn, gt=gt, pad=pad, lw=lw, tier_h=tier_h, tier_w=tier_w,
            total_w=total_w, total_h=total_h, ok=True, capn=cap_h, labw=labw,
        )  # fmt: skip

    # the legend strip is reserved first; the diagram is centred in what is left
    used_kinds = sorted({("primary" if e.focal else e.kind) for e in edges}, key=DK.KINDS.index)
    roles = [r for r in DK.ROLES if any(r in nd.classes for nd in A.nodes)]
    plain = any(not (set(nd.classes) & set(DK.ROLES)) for nd in A.nodes)
    legend_on = DK.wants_legend(c, roles, used_kinds, slide)
    area = Rect(body.x, body.y, body.w, body.h)
    leg_h = DK.legend_height(K0) if legend_on else 0
    if legend_on:
        area = Rect(body.x, body.y, body.w, body.h - leg_h)
    k = 1.0
    best = plan(k)
    while not pinned and (best.total_h > area.h or best.total_w > area.w) and k > 0.6:
        k = round(k - 0.05, 2)
        best = plan(k)
    P: _Plan = best
    K = K0.scaled(P.k)
    ok = P.total_h <= area.h * 1.02 and P.total_w <= area.w * 1.02
    x0, y0 = DK.centred(area, P.total_w, P.total_h)
    cap_h = P.capn
    cap_st = V._text_style(c, K.label, align="left", valign="middle", padding="0pt")
    radius = _radius(th)
    # tier regions
    zones: list[Rect] = []
    if cols:
        x = x0
        for i in range(n):
            zones.append(Rect(x, y0 + (P.total_h - P.tier_h[i]) // 2, P.tier_w[i], P.tier_h[i]))
            x += P.tier_w[i] + P.gt
    else:
        y = y0
        for i in range(n):
            zones.append(Rect(x0 + P.lw, y, P.tier_w[i] - P.lw, P.tier_h[i]))
            y += P.tier_h[i] + P.gt
    band_fill = th.arch_tier_fill or V._eng()._tint(th, "muted", 0.07)
    group_fill = th.diagram_group_fill or V._eng()._tint(th, "muted", 0.07)
    caps: list[Rect] = []

    def own_fill(i: int) -> str | None:
        return V._own(slide.elements[i], "fill")

    for i, (title, _row) in enumerate(A.tiers):
        z = zones[i]
        lk = looks[i]
        if lk != "caption":
            own = V._own(slide.elements[i], "fill")
            if lk == "band":
                fill = None if (own or band_fill) == "none" else (own or band_fill)
                st = fast_style(
                    fill=fill, line=th.arch_tier_line, **({"radius": radius} if radius is not None else {})
                )
            else:  # a light solid container: paper-2 fill, hairline border, caption on a knockout
                st = fast_style(
                    fill=own or group_fill,
                    line=th.diagram_tag_line,
                    line_width=DK.hairline(c),
                    radius=V._pt(V._emu(th.diagram_group_radius)),
                )
            if fill_ok(st):
                c.emit(Shape(shape="rect", attrs={"shape_name": f"Arch tier {i + 1}"}), z, st)
        if not title:
            continue
        tw = DK.small_w(K, title, K.label, th.diagram_label_track) + round(10 * DK.PT)
        if lk == "caption":
            if cols:
                r = Rect(z.x, z.y, max(z.w, tw), cap_h)
            else:
                r = Rect(z.x - P.lw, z.y, P.lw, z.h)
        else:
            r = Rect(
                z.x + round(0.4 * pad), z.y - cap_h // 2 if lk == "box" else z.y + round(0.3 * pad), tw, cap_h
            )
        cst = cap_st
        if lk == "box":
            cst = V._text_style(
                c, K.label, align="center", valign="middle", padding="0pt", fill=own_fill(i) or group_fill
            )
        DK.emit_text(
            c,
            f"Arch tier {i + 1} label",
            [DK.small_para(c, K, title, K.label, th.diagram_label_track, th.arch_tier_label)],
            r,
            cst,
            nowrap=True,
        )
        caps.append(r)
    # node positions (drawn after the arrows, which run under them)
    rects: dict[int, Rect] = {}
    node_draws: list[tuple[Any, Rect]] = []
    for i, (_title, row) in enumerate(A.tiers):
        z = zones[i]
        boxed = looks[i] != "caption"
        head = (cap_h + round(0.5 * pad)) if has_title[i] and (cols or boxed) else 0
        if cols:
            ncol = P.rows[i]
            stack = ncol * P.h + (ncol - 1) * P.gn
            ytop = z.y + (pad if boxed else 0) + head
            yy = ytop + max((z.bottom - (pad if boxed else 0) - ytop - stack) // 2, 0)
            xx = z.x + (z.w - P.w) // 2
            pts = [(xx, yy + kk * (P.h + P.gn)) for kk in range(ncol)]
        else:
            ax0 = z.x + (pad if boxed else 0)
            aw = z.w - (2 * pad if boxed else 0)
            rows_n = P.rows[i]
            block_h = rows_n * P.h + (rows_n - 1) * P.gn
            ytop = z.y + (pad + head if boxed else 0)
            yy = ytop + max((z.bottom - (pad if boxed else 0) - ytop - block_h) // 2, 0)
            pts = []
            for r_ in range(rows_n):
                chunk = row[r_ * P.per[i] : (r_ + 1) * P.per[i]]
                rw = len(chunk) * P.w + (len(chunk) - 1) * P.gn
                xr = ax0 + (aw - rw) // 2
                pts += [(xr + kk * (P.w + P.gn), yy + r_ * (P.h + P.gn)) for kk in range(len(chunk))]
        for nd, (x, y) in zip(row, pts, strict=False):
            kidx = A.nodes.index(nd)
            rect = Rect(x, y, P.w, P.h)
            rects[kidx] = rect
            node_draws.append((nd, rect))
    # arrows (own ports and bend levels, drawn under the nodes), then the nodes, then the labels
    pairs = [(e.src, e.dst) for e in edges]
    routes = PO.plan(
        pairs, rects, "h" if cols else None, labelled={i for i, e in enumerate(edges) if e.label}
    )
    done = 0
    placed: list[tuple[Any, Any]] = []
    for e, rt in zip(edges, routes, strict=True):
        if rt is None:
            continue
        pl = PO.emit(c, rt, rects, f"Arch edge {done + 1}")
        kind = "primary" if e.focal and e.kind == "flow" else e.kind
        col, dash, wd = DK.style_of(K, kind, e.focal)
        DK.restyle(pl, col, dash, wd)
        pl.element.attrs["kind"] = kind
        done += 1
        placed.append((e, pl))
    for nd, rect in node_draws:
        DK.node(
            c, K, f"Arch node {nd.name}", f"Arch tag {nd.name}", rect,
            DK.node_paras(c, K, nd.name, nd.sub), nd.tag, nd.classes,
        )  # fmt: skip
    obstacles = [*rects.values(), *caps]
    for _e, pl in placed:
        obstacles += PO.segment_rects(DK.polyline(pl))
    for e, pl in placed:
        if e.label:
            kind = "primary" if e.focal and e.kind == "flow" else e.kind
            col = DK.style_of(K, kind, e.focal)[0] if (kind != "flow" or e.focal) else None
            r = DK.edge_label(
                c,
                K,
                pl.element.attrs["shape_name"] + " label",
                DK.polyline(pl),
                e.label,
                col,
                obstacles,
                area,
            )
            obstacles.append(r)
    if legend_on:
        entries = DK.legend_entries(
            c,
            roles,
            used_kinds,
            plain and bool(roles),
            "ja" if any(DK.has_wide(nd.name) for nd in A.nodes) else None,
        )
        lw_ = min(max(P.total_w, DK.legend_width(K, entries)), body.w)
        lx = min(max(x0, body.x), body.right - lw_)
        DK.legend(c, K, lx, body.bottom - leg_h + round(6 * DK.PT), lw_, entries)
    info.update(n=len(A.nodes), tiers=n, edges=done, dir="h" if cols else "v", size=K.name, fit=ok)
    if not ok:
        c.over.append("@arch nodes")
    return True


def fill_ok(st) -> bool:
    return bool(st.fill or st.line)


def _radius(th) -> Any:
    card = th.classes.get("node") or th.classes.get("card")
    return card.radius if card is not None and card.radius is not None else None


# --------------------------------------------------------------------------- @venn


def _sizes_down(hi: float, lo: float) -> list[float]:
    out, s = [], hi
    while s >= lo - 1e-9:
        out.append(s)
        s -= V._STEP
    return out or [lo]


_AR = 1.5  # width / height of the text boxes searched inside a region


def _inside(px: float, py: float, circ: tuple[float, float, float], grow: float = 0.0) -> bool:
    return math.hypot(px - circ[0], py - circ[1]) <= circ[2] + grow


_BOX_CACHE: dict[tuple, tuple[float, float, float, float]] = {}


def _best_box(
    ins: list[tuple[float, float, float]],
    outs: list[tuple[float, float, float]],
    margin: float,
    ar: float = _AR,
) -> tuple[float, float, float, float]:
    """Memoised ``_best_box0``: the geometry is the same at every text size the layout tries."""
    key = (
        tuple(map(round, (v for c in ins for v in c))),
        tuple(map(round, (v for c in outs for v in c))),
        round(margin),
        ar,
    )
    got = _BOX_CACHE.get(key)
    if got is None:
        if len(_BOX_CACHE) > 512:
            _BOX_CACHE.clear()
        got = _BOX_CACHE[key] = _best_box0(ins, outs, margin, ar)
    return got


def _best_box0(
    ins: list[tuple[float, float, float]],
    outs: list[tuple[float, float, float]],
    margin: float,
    ar: float = _AR,
) -> tuple[float, float, float, float]:
    """``(cx, cy, w, h)`` of the largest box of aspect ``ar`` inside every circle of ``ins`` and outside
    every circle of ``outs`` (``margin`` from the outlines); ``w = 0`` when the region is empty."""
    x0, y0, r0 = ins[0]
    best = (x0, y0, 0.0, 0.0)
    steps = 16
    for iy in range(steps + 1):
        for ix in range(steps + 1):
            cx = x0 - r0 + 2 * r0 * ix / steps
            cy = y0 - r0 + 2 * r0 * iy / steps

            def ok(w: float, cx=cx, cy=cy) -> bool:
                h = w / ar
                pts = []
                for fx in (-1, -0.5, 0, 0.5, 1):
                    for fy in (-1, 0, 1):
                        pts.append((cx + fx * w / 2, cy + fy * h / 2))
                return all(
                    all(_inside(px, py, ci, -margin) for ci in ins)
                    and not any(_inside(px, py, co, margin) for co in outs)
                    for px, py in pts
                )

            if not ok(1.0):
                continue
            lo_w, hi_w = 1.0, 2 * r0
            for _ in range(12):
                mid = (lo_w + hi_w) / 2
                lo_w, hi_w = (mid, hi_w) if ok(mid) else (lo_w, mid)
            if lo_w > best[2]:
                best = (cx, cy, lo_w, lo_w / ar)
    return best


def _box_free(
    cx: float,
    cy: float,
    w: float,
    h: float,
    ins: list[tuple[float, float, float]],
    outs: list[tuple[float, float, float]],
    margin: float,
) -> bool:
    for fx in (-1, -0.5, 0, 0.5, 1):
        for fy in (-1, 0, 1):
            px, py = cx + fx * w / 2, cy + fy * h / 2
            if not all(_inside(px, py, ci, -margin) for ci in ins):
                return False
            if any(_inside(px, py, co, margin) for co in outs):
                return False
    return True


def _outward(
    circ: tuple[float, float, float],
    outs: list[tuple[float, float, float]],
    w: float,
    h: float,
    direction: tuple[float, float],
    margin: float,
) -> tuple[float, float] | None:
    """Centre of a ``w`` x ``h`` box inside ``circ`` and outside ``outs`` that lies furthest along
    ``direction`` (the name of an outer set sits towards the outside of its circle), or ``None``."""
    cx0, cy0, r = circ
    best, best_s = None, -1e18
    steps = 28
    for iy in range(steps + 1):
        for ix in range(steps + 1):
            cx = cx0 - r + 2 * r * ix / steps
            cy = cy0 - r + 2 * r * iy / steps
            if not _box_free(cx, cy, w, h, [circ], outs, margin):
                continue
            dx, dy = cx - cx0, cy - cy0
            sc = dx * direction[0] + dy * direction[1] - 0.3 * abs(dx * direction[1] - dy * direction[0])
            if sc > best_s:
                best, best_s = (cx, cy), sc
    return best


_WEAK = {"a", "an", "the", "of", "to", "and", "for", "in", "on", "or", "by", "at", "with", "is", "are"}


def _balanced(text: str, size: float, w: float, c, K) -> list[str]:
    """``text`` as one line when it fits ``w`` (EMU), else the fewest lines (up to 3) that fit, split where
    the widths are most even and no line ends on a function word ("A PLAN THE / TEAM")."""
    words = text.split()
    tr = c.theme.diagram_label_track

    def wid(ws: list[str]) -> float:
        return DK.small_w(K, " ".join(ws), size, tr)

    if len(words) < 2 or wid(words) <= w:
        return [text]
    best: list[str] = [text]
    for n in (2, 3):
        if len(words) < n:
            break
        top: tuple[float, list[str]] | None = None
        for cuts in itertools.combinations(range(1, len(words)), n - 1):
            parts = [words[a:b] for a, b in zip((0, *cuts), (*cuts, len(words)), strict=True)]
            cost = max(
                wid(pt) * (1.8 if pt[-1].lower().strip(".,") in _WEAK and pt is not parts[-1] else 1.0)
                for pt in parts
            )
            if top is None or cost < top[0]:
                top = (cost, [" ".join(pt) for pt in parts])
        assert top is not None
        best = top[1]
        if max(wid(ln.split()) for ln in best) <= w:
            return best
    return best


def _lens(circ: list[tuple[float, float, float]], steps: int = 720) -> list[tuple[int, int]]:
    """The polygon of the region inside every circle: arc samples that lie in all the other circles plus the
    exact crossing points of the circles, sorted around the (convex) region's centre. ``[]`` when empty."""
    tol = 1.0 + 1e-6
    pts: list[tuple[float, float]] = []
    for i, (cx, cy, r) in enumerate(circ):
        others = [o for j, o in enumerate(circ) if j != i]
        for k in range(steps):
            a = 2 * math.pi * k / steps
            x, y = cx + r * math.cos(a), cy + r * math.sin(a)
            if all(math.hypot(x - ox, y - oy) <= orr * tol for ox, oy, orr in others):
                pts.append((x, y))
    for i in range(len(circ)):
        for j in range(i + 1, len(circ)):
            (x0, y0, r0), (x1, y1, r1) = circ[i], circ[j]
            d = math.hypot(x1 - x0, y1 - y0)
            if d == 0 or d > r0 + r1 or d < abs(r0 - r1):
                continue
            a = (r0 * r0 - r1 * r1 + d * d) / (2 * d)
            h = math.sqrt(max(r0 * r0 - a * a, 0.0))
            mx, my = x0 + a * (x1 - x0) / d, y0 + a * (y1 - y0) / d
            for sgn in (1, -1):
                px, py = mx + sgn * h * (y1 - y0) / d, my - sgn * h * (x1 - x0) / d
                if all(math.hypot(px - ox, py - oy) <= orr * (1 + 1e-4) for ox, oy, orr in circ):
                    pts.append((px, py))
    if len(pts) < 3:
        return []
    gx, gy = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
    pts.sort(key=lambda p: math.atan2(p[1] - gy, p[0] - gx))
    out: list[tuple[int, int]] = []
    for x, y in pts:
        q = (round(x), round(y))
        if not out or q != out[-1]:
            out.append(q)
    return out


def _set_paras(c, K, head: str, body: list, wide: float, name_pt: float) -> list[Paragraph]:
    """The label of a set: the bold name, then its body line as a mono capitals sublabel (short Latin text)
    or, for anything longer or CJK, as plain muted text."""
    out = [Paragraph(runs=[Run(text=head)], style=fast_style(font_size=name_pt, bold=True))] if head else []
    paras = [p for t in body for p in t.paragraphs if p.plain.strip()]
    text = " ".join(p.plain.strip() for p in paras)
    if not text:
        return out
    if len(paras) == 1 and len(text) <= 34 and not DK.has_wide(text) and not paras[0].marker:
        out.append(DK.small_para(c, K, text, K.sub, c.theme.diagram_label_track))
    else:
        for p in paras:
            st = fast_style(font_size=round(K.sub + 2, 1), color=K.muted)
            out.append(p.model_copy(update={"style": st.merged(p.style), "marker": None, "level": 0}))
    return out


def _venn(c, slide: Slide, body: Rect, sg: int, info: dict) -> bool:
    th = c.theme
    bx = forms.boxes(slide) or []
    n = len(bx)
    if n not in (2, 3):
        return False
    K0 = DK.look(c, slide)
    pinned = bool(forms.num(slide.attrs, "size"))
    parts = [V._split_box(b) for b in bx]
    heads = [
        " ".join(p.plain.strip() for p in h.paragraphs).strip() if h is not None else "" for h, _ in parts
    ]
    otext, ocls = forms6.split_trailing(forms6.edge_text(slide)) if forms6.edge_text(slide) else ("", [])
    oname, osub = DK.split_sub(otext) if otext else ("", "")
    o = th.venn_overlap or (0.36 if n == 2 else 0.42)
    fills = V._colors(slide, th.venn_fill)
    palette = [x for x in (th.palette or []) if x] or ["primary", "secondary", "muted"]
    focal_overlap = "focal" in ocls
    emu = V._emu
    air = round(0.08 * _IN)
    rmax = emu(th.venn_size) / 2 if th.venn_size else emu(th.venn_max) / 2

    def centres(r: float) -> list[tuple[float, float]]:
        d = 2 * r * (1 - o)
        if n == 2:
            return [(-d / 2, 0.0), (d / 2, 0.0)]
        return [(0.0, -d * 0.5774), (-d / 2, d * 0.2887), (d / 2, d * 0.2887)]

    def extent(r: float) -> tuple[float, float]:
        d = 2 * r * (1 - o)
        return (2 * r + d, 2 * r) if n == 2 else (2 * r + d, 2 * r + 0.866 * d)

    def solve(k: float, mode: str) -> dict[str, Any]:
        K = K0.scaled(k)
        K.sub = max(K.sub, min(9.0, th.diagram_sub_size))  # a venn sublabel never drops below 9 pt
        name_pt = round(K.name + 3, 1)
        r_h = (body.h - 2 * air) / extent(1.0)[1]
        r_w = body.w * (0.96 if mode == "in" else 0.5) / extent(1.0)[0]
        r = min(r_h, r_w, rmax)
        cs = centres(r)
        w_, h_ = extent(r)
        ox = body.x + body.w / 2
        oy = body.y + (body.h - h_) / 2 + (r if n == 2 else r + 0.5774 * 2 * r * (1 - o))
        circ = [(ox + cx, oy + cy, r) for cx, cy in cs]
        margin = 0.04 * r + 3 * EMU_PER_PT
        boxes_: list[tuple[float, float, float, float]] = []
        aligns: list[str] = []
        fit = True
        for i in range(n):
            if mode == "in":
                bxi = _best_box([circ[i]], [circ[j] for j in range(n) if j != i], margin)
                al = "center"
            else:
                left = circ[i][0] < ox - 0.25 * r
                gap = 2 * air
                x0, x1 = (body.x, ox - w_ / 2 - gap) if left else (ox + w_ / 2 + gap, body.right)
                same = [
                    abs(circ[j][1] - circ[i][1])
                    for j in range(n)
                    if j != i and (circ[j][0] < ox - 0.25 * r) == left
                ]
                hh = min(2 * r, body.h, *same) if same else min(2 * r, body.h)
                cy = min(max(circ[i][1], body.y + hh / 2), body.bottom - hh / 2)
                bxi = ((x0 + x1) / 2, cy, max(x1 - x0, 1.0), hh)
                al = "right" if left else "left"
            boxes_.append(bxi)
            aligns.append(al)
            if bxi[2] <= 0:
                fit = False
                continue
            st = V._text_style(c, name_pt, align=al, valign="middle")
            need = V._need(c, _set_paras(c, K, heads[i], parts[i][1], bxi[2], name_pt), round(bxi[2]), st)
            fit = fit and need <= bxi[3]
        ob, ocore, ofit = (0.0, 0.0, 0.0, 0.0), None, True
        if otext:
            ob, ocore, ofit = _core_label(c, K, list(circ), margin, oname, osub)
        else:
            ob = _best_box(list(circ), [], margin)
        return {
            "r": r, "circ": circ, "boxes": boxes_, "aligns": aligns, "ob": ob, "fit": fit, "ofit": ofit,
            "mode": mode, "K": K, "name_pt": name_pt, "ox": ox, "core": ocore, "margin": margin,
        }  # fmt: skip

    want = th.venn_text if th.venn_text in ("in", "out") else "auto"
    plan_: list[tuple[str, float]] = []
    ks = [1.0] if pinned else [1.0, 0.95, 0.9, 0.85, 0.8, 0.75]
    if want in ("in", "auto"):
        plan_ += [("in", k) for k in ks]
    if want in ("out", "auto"):
        plan_ += [("out", k) for k in ks]
    S = None
    for mode_, k in plan_:
        S = solve(k, mode_)
        if S["fit"] and S["ofit"]:
            break
    if S is None:
        S = solve(1.0, "in")
    circ, K, name_pt = S["circ"], S["K"], S["name_pt"]
    # circles: translucent, neutral by token (editorial: ink at a few percent, hairline strokes)
    line_w = V._pt(emu(th.venn_line_w))
    for i in range(n):
        focal = "focal" in bx[i].classes
        col = (
            V._own(bx[i], "fill")
            or ("accent" if focal else None)
            or V._pick(fills, i)
            or palette[i % len(palette)]
        )
        lc = th.venn_line or ("accent" if focal else col)
        cx, cy, rr = circ[i]
        d = round(2 * rr)
        c.emit(
            Shape(shape="ellipse", attrs={"shape_name": f"Venn {i + 1} set"}),
            Rect(round(cx - rr), round(cy - rr), d, d),
            fast_style(fill=col, opacity=th.venn_alpha, line=lc, line_width=line_w),
        )
    # the overlap of all sets: an exact lens (a freeform), solid
    core_fill = "accent" if focal_overlap else th.venn_core
    if otext:
        poly = _lens(circ)
        if len(poly) >= 3:
            xs, ys = [p[0] for p in poly], [p[1] for p in poly]
            c.emit(
                Shape(shape="freeform", attrs={"shape_name": "Venn overlap fill", "points": poly}),
                Rect(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)),
                fast_style(fill=core_fill, line=None),
            )
    gx = sum(ci[0] for ci in circ) / n
    gy = sum(ci[1] for ci in circ) / n
    for i in range(n):
        bxi = S["boxes"][i]
        paras = _set_paras(c, K, heads[i], parts[i][1], bxi[2], name_pt)
        if not paras or bxi[2] <= 0:
            continue
        w, h = round(bxi[2]), round(bxi[3])
        cx_, cy_ = bxi[0], bxi[1]
        if S["mode"] == "in":
            # a name sits towards the outside of its circle: a box of the text's own size, pushed outwards
            st_ = V._text_style(c, name_pt, color=th.venn_name_color, align="center", valign="middle")
            nat = max(
                (
                    max(
                        DK.small_w(K, r.text, p.style.font_size or K.sub, th.diagram_label_track)
                        if p.style.text_transform == "caps"
                        else _tw(r.text, p.style.font_size or name_pt, bool(p.style.bold))
                        for r in p.runs
                    )
                    for p in paras
                ),
                default=w,
            )
            tw_ = min(w, round(nat + 6 * EMU_PER_PT))
            th_ = round(V._need(c, paras, tw_, st_))
            vx, vy = circ[i][0] - gx, circ[i][1] - gy
            vn = math.hypot(vx, vy) or 1.0
            outs = [circ[j] for j in range(n) if j != i]
            got = _outward(circ[i], outs, tw_, th_, (vx / vn, vy / vn), S["margin"] + 0.05 * circ[i][2])
            if got is not None and th_ <= h * 1.05:
                cx_, cy_, w, h = got[0], got[1], tw_, th_
        V._emit_text(
            c,
            f"Venn {i + 1} name",
            paras,
            Rect(round(cx_ - w / 2), round(cy_ - h / 2), w, h),
            V._text_style(c, name_pt, color=th.venn_name_color, align=S["aligns"][i], valign="middle"),
        )
    if otext and S["core"] is not None:
        (ocx, ocy, ow, oh), oparas_fn = S["core"]
        ink = th.ink_on(core_fill, "bg")
        w, h = round(ow), round(oh)
        V._emit_text(
            c,
            "Venn overlap",
            oparas_fn(ink),
            Rect(round(ocx - w / 2), round(ocy - h / 2), w, h),
            V._text_style(c, K.name, color=ink, align="center", valign="middle"),
        )
    info.update(n=n, size=name_pt, fit=S["fit"] and S["ofit"], overlap=bool(otext), text=S["mode"])
    if not (S["fit"] and S["ofit"]):
        c.over.append("@venn text")
    return True


def _core_paras(
    c, K, name: str, sub: list[str] | str, name_pt: float, sub_pt: float, ink: str | None = None
) -> list[Paragraph]:
    """The label of the overlap: the bold name and the mono capitals sublabel (one or two lines)."""
    st = fast_style(font_size=name_pt, bold=True, **({"color": ink} if ink else {}))
    out = [Paragraph(runs=[Run(text=name)], style=st)]
    for ln in [sub] if isinstance(sub, str) else sub:
        if ln:
            out.append(DK.small_para(c, K, ln, sub_pt, c.theme.diagram_label_track, ink))
    return out


_CORE_AR = (1.5, 2.0, 1.0, 2.6, 0.7, 3.4)


def _core_label(c, K, circ, margin: float, oname: str, osub: str):
    """``(box, (box, paras of an ink), fits)`` of the label of the overlap: the largest sizes (name down to
    9 pt, sublabel down to 8 pt) and the box shape (aspect 1.5 .. 3.4) that fit the lens, the sublabel on one
    line or two balanced ones, never a word split."""
    th = c.theme
    best = _best_box(circ, [], margin)
    names = [round(K.name - 0.5 * i, 1) for i in range(int((K.name - 9) / 0.5) + 1)] or [K.name]
    for wrap in (False, True):  # first shrink the sublabel to 8 pt on one line, then break it
        for nm in names:
            for sub_pt in (K.sub, max(K.sub - 0.5, 8.0), 8.0):
                for ar in _CORE_AR:
                    box = _best_box(circ, [], margin, ar)
                    if box[2] <= 0:
                        continue
                    w = round(box[2])
                    lines = _balanced(osub, sub_pt, w - 2 * EMU_PER_PT, c, K) if (osub and wrap) else [osub]
                    paras = _core_paras(c, K, oname, lines, nm, sub_pt)
                    st = V._text_style(c, nm, bold=True, align="center", valign="middle")
                    wide = max(
                        [_tw(wd, nm, True) for wd in oname.split() or [oname]]
                        + [DK.small_w(K, ln, sub_pt, th.diagram_label_track) for ln in lines if ln]
                    )
                    if wide <= w and V._need(c, paras, w, st) <= box[3]:
                        return box, (box, _CoreInk(c, K, oname, lines, nm, sub_pt)), True
    nm = names[-1]
    lines = _balanced(osub, 8.0, round(best[2]), c, K) if osub else []
    return best, (best, _CoreInk(c, K, oname, lines, nm, 8.0)), False


class _CoreInk:
    """The paragraphs of the overlap label, drawn once the ink colour is known."""

    def __init__(self, c, K, name: str, lines: list[str], name_pt: float, sub_pt: float) -> None:
        self.a = (c, K, name, lines, name_pt, sub_pt)

    def __call__(self, ink: str | None) -> list[Paragraph]:
        c, K, name, lines, name_pt, sub_pt = self.a
        return _core_paras(c, K, name, lines, name_pt, sub_pt, ink)


FORMS = {"arch": _arch, "venn": _venn}

_ = (re, Text)
