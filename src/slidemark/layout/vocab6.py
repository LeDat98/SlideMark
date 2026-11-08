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

import math
import re
from typing import Any

from .. import forms, forms6
from ..ir import Link, Paragraph, Run, Shape, Slide, Text, fast_style
from ..units import EMU_PER_PT
from . import measure
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
        "size",
        "w",
        "h",
        "rows",
        "per",
        "gn",
        "gt",
        "pad",
        "lw",
        "cap",
        "tier_h",
        "total",
        "ok",
        "capn",
    )

    def __init__(self, **kw: Any) -> None:
        for k in self.__slots__:
            setattr(self, k, kw.get(k))


def _arch(c, slide: Slide, body: Rect, sg: int, info: dict) -> bool:
    th, lt = c.theme, c.lt
    A = forms6.parse_arch(slide)
    if A is None or not A.nodes:
        return False
    cols = forms.words(slide.attrs, "arch", "dir") == "h"
    edges, _bad = forms6.parse_edges(forms6.edge_text(slide), A)
    n = len(A.tiers)
    base, _ratio, hi, lo, pinned = V._sizes(c, slide)
    gn = V._emu(th.arch_node_gap)
    pad = V._emu(th.arch_tier_pad)
    labelled = [e.label for e in edges if e.label]

    def node_paras(node, s: float) -> list[Paragraph]:
        out = [Paragraph(runs=[Run(text=node.name)])]
        if node.sub:
            st = fast_style(font_size=round(s * th.arch_sub_size, 2), color=th.arch_sub_color)
            out.append(Paragraph(runs=[Run(text=node.sub)], style=st))
        return out

    def node_style(s: float, classes: list[str] | None = None):
        st = V._text_style(c, s, align="center", valign="middle")
        st = st.merged(_class_style(th, ["node", *(classes or [])]))
        return st.merged(fast_style(font_size=s))

    def plan(s: float) -> _Plan:
        sub = s * th.arch_sub_size
        same = [e for e in edges if e.label and A.nodes[e.src].tier == A.nodes[e.dst].tier]
        gn_p = gn
        if same:  # a label on an arrow between neighbours of a tier needs its width between the nodes
            gn_p = max(gn, max(_tw(e.label or "", s * 0.75) for e in same) + round(0.3 * _IN))
        cap = th.arch_tier_label_size or max(round(s * 0.75, 1), 9.0)
        gt = V._emu(th.arch_gap) if th.arch_gap else 0
        if not gt:  # the arrows run in this gap: room for a label (rows) or its width (columns)
            if cols:
                lab = max((_tw(x, s * 0.75) for x in labelled), default=0)
                gt = max(round(0.45 * _IN), lab + round(0.3 * _IN)) if labelled else round(0.5 * _IN)
            else:
                gt = max(round(sg * 1.5), round((0.5 if labelled else 0.4) * _IN))
        st0 = node_style(s)
        pads = (
            V._emu(th.classes["node"].padding) if "node" in th.classes and th.classes["node"].padding else 0
        )
        nat = max(
            max(_tw(nd.name, s), _tw(nd.sub, sub) if nd.sub else 0) + 2 * pads + round(0.12 * _IN)
            for nd in A.nodes
        )
        w = (
            V._emu(th.arch_node_w)
            if th.arch_node_w
            else min(max(round(nat * 1.08), round(1.25 * _IN)), round(2.9 * _IN))
        )
        if cols:
            colw = (body.w - gt * (n - 1)) // n
            lw = 0
            w = min(w if th.arch_node_w else max(w, round(0.78 * colw)), colw - 2 * pad)
        else:
            cap_w = max((_tw(wd, cap, True) for t, _ in A.tiers for wd in t.split()), default=0)
            lw = (
                V._emu(th.arch_label_w)
                if th.arch_label_w
                else min(max(cap_w + round(0.12 * _IN), round(0.85 * _IN)), round(body.w * 0.2))
            )
            avail = body.w - 2 * pad - lw - round(0.1 * _IN)
            kmax = max(len(r) for _, r in A.tiers)
            wmin = round(1.1 * _IN)
            if not th.arch_node_w and kmax * (w + gn_p) - gn_p > avail:
                w = max(min(w, (avail - (kmax - 1) * gn_p) // kmax), wmin)
            w = min(w, avail)
        h = V._emu(th.arch_node_h) if th.arch_node_h else 0
        if not h:
            h = max(
                round(V._need(c, node_paras(nd, s), w, st0)) + round(0.1 * s * EMU_PER_PT) for nd in A.nodes
            )
            h = max(h, round(2.4 * s * EMU_PER_PT))
        per, rows, tier_h, capn = [], [], [], 0
        if cols:
            capn = max(
                (
                    V._need(
                        c,
                        [Paragraph(runs=[Run(text=t, bold=True)])],
                        w + 2 * pad,
                        V._text_style(c, cap, align="left"),
                    )
                    for t, _ in A.tiers
                ),
                default=0,
            )
            capn = round(capn + 0.3 * pad)
            avail = 0
            for _t, r in A.tiers:
                per.append(1)
                rows.append(len(r))
            tier_h = [capn + rows[i] * h + (rows[i] - 1) * gn_p + 2 * pad for i in range(n)]
            total = max(tier_h)
            ok = total <= body.h * lt.vocab_fill
            tier_h = [total] * n
        else:
            for _t, r in A.tiers:
                m = max(1, (avail + gn_p) // (w + gn_p))
                k = len(r)
                nrows = -(-k // m)
                rows.append(nrows)
                per.append(-(-k // nrows))
            tier_h = [rows[i] * h + (rows[i] - 1) * gn_p + 2 * pad for i in range(n)]
            total = sum(tier_h) + gt * (n - 1)
            ok = total <= body.h * lt.vocab_fill
        return _Plan(
            size=s,
            w=w,
            h=h,
            rows=rows,
            per=per,
            gn=gn_p,
            gt=gt,
            pad=pad,
            lw=lw,
            cap=cap,
            tier_h=tier_h,
            total=total,
            ok=ok,
            capn=capn,
        )

    best = plan(hi) if pinned else None
    if best is None:
        s = hi
        while True:
            best = plan(s)
            if best.ok or s - V._STEP < lo - 1e-9:
                break
            s -= V._STEP
    P: _Plan = best
    s = P.size
    cap = P.cap
    # spare height: tier bands grow a little, then the gaps, then the block is centred
    if cols:
        total = P.total
        extra = max(body.h - total, 0)
        grow = round(min(extra, 0.7 * total))
        tier_h = [P.tier_h[0] + grow] * n
        top = body.y + round(max(extra - grow, 0) * lt.vocab_top)
        gt = P.gt
        col_w = (body.w - gt * (n - 1)) // n
        bands = [Rect(body.x + i * (col_w + gt), top, col_w, tier_h[i]) for i in range(n)]
    else:
        extra = max(body.h - P.total, 0)
        e_t = round(min(extra / n, 0.5 * P.h))
        extra -= e_t * n
        e_g = round(min(extra / max(n - 1, 1), 0.8 * P.gt)) if n > 1 else 0
        extra -= e_g * (n - 1)
        top = body.y + round(max(extra, 0) * lt.vocab_top)
        gt = P.gt + e_g
        tier_h = [h + e_t for h in P.tier_h]
        bands, y = [], top
        for i in range(n):
            bands.append(Rect(body.x, y, body.w, tier_h[i]))
            y += tier_h[i] + gt
    # bands and captions
    band_fill = th.arch_tier_fill or V._eng()._tint(th, "muted", 0.07)
    radius = _radius(th)
    for i, (title, _row) in enumerate(A.tiers):
        own = V._own(slide.elements[i], "fill")
        fill = None if (own or band_fill) == "none" else (own or band_fill)
        if fill or th.arch_tier_line:  # `arch.tier.fill=none` and no outline: no band at all
            c.emit(
                Shape(shape="rect", attrs={"shape_name": f"Arch tier {i + 1}"}),
                bands[i],
                fast_style(
                    fill=fill, line=th.arch_tier_line, **({"radius": radius} if radius is not None else {})
                ),
            )
        if not title:
            continue
        paras = [Paragraph(runs=[Run(text=title, bold=True)])]
        lst = V._text_style(
            c, cap, color=th.arch_tier_label, align="left", valign="top" if cols else "middle"
        )
        if cols:
            rect = Rect(bands[i].x + P.pad, bands[i].y + P.pad // 2, bands[i].w - 2 * P.pad, bands[i].h)
        else:
            rect = Rect(bands[i].x + P.pad, bands[i].y, P.lw, bands[i].h)
        V._emit_text(c, f"Arch tier {i + 1} label", paras, rect, lst)
    # nodes
    rects: dict[int, Rect] = {}
    for i, (_title, row) in enumerate(A.tiers):
        b = bands[i]
        if cols:
            ncol = P.rows[i]
            stack = ncol * P.h + (ncol - 1) * P.gn
            top_y = b.y + P.pad + P.capn
            y0 = top_y + max((b.bottom - P.pad - top_y - stack) // 2, 0)
            x0 = b.x + (b.w - P.w) // 2
            pts = [(x0, y0 + k * (P.h + P.gn)) for k in range(ncol)]
        else:
            ax0 = b.x + P.pad + P.lw + round(0.05 * _IN)
            aw = b.w - 2 * P.pad - P.lw - round(0.1 * _IN)
            rows_n = P.rows[i]
            block_h = rows_n * P.h + (rows_n - 1) * P.gn
            y0 = b.y + (b.h - block_h) // 2
            pts = []
            for r in range(rows_n):
                chunk = row[r * P.per[i] : (r + 1) * P.per[i]]
                rw = len(chunk) * P.w + (len(chunk) - 1) * P.gn
                xr = ax0 + (aw - rw) // 2
                pts += [(xr + k * (P.w + P.gn), y0 + r * (P.h + P.gn)) for k in range(len(chunk))]
        for nd, (x, y) in zip(row, pts, strict=False):
            k = A.nodes.index(nd)
            rect = Rect(x, y, P.w, P.h)
            rects[k] = rect
            V._emit_text(
                c,
                f"Arch node {nd.name}",
                node_paras(nd, s),
                rect,
                node_style(s, nd.classes),
                [*nd.classes],
            )
    # arrows (over the nodes), then their labels
    E = V._eng()
    lab_size = th.arch_edge_size or max(round(s * 0.8, 1), 9.0)
    done = 0
    placed: list[tuple[Any, Any]] = []
    for e in edges:
        if e.src not in rects or e.dst not in rects:
            continue
        before = len(c.out)
        E._emit_links(c, [Link(src=e.src, dst=e.dst, arrow=True)], rects, "h" if cols else None)
        if len(c.out) == before:
            continue
        pl = c.out[-1]
        pl.element.attrs["shape_name"] = f"Arch edge {done + 1}"
        if e.focal:
            pl.style = pl.style.merged(
                fast_style(line="accent", line_width=max(th.render.connector_width, 1.5))
            )
        done += 1
        placed.append((e, pl))
    _stagger(placed)
    for e, pl in placed:
        if e.label:
            _edge_label(c, pl, pl.element.attrs["shape_name"] + " label", e.label, lab_size)
    info.update(n=len(A.nodes), tiers=n, edges=done, dir="h" if cols else "v", size=s, fit=P.ok)
    if not P.ok:
        c.over.append("@arch nodes")
    return True


def _stagger(placed: list[tuple[Any, Any]]) -> None:
    """Arrows of different sources and targets that would share one bend line get their own: the arrows of
    one gap whose spans overlap are bundled by shared end (one source or target = one bus) and the bundles
    take evenly spaced positions between the two tiers."""
    groups: dict[tuple[str, int, int], list[tuple[Any, Any]]] = {}
    for e, pl in placed:
        at = pl.element.attrs
        if not at.get("elbow"):
            continue
        if at.get("route") == "h":
            key = ("h", pl.x, pl.x + pl.w)
        else:
            key = ("v", pl.y, pl.y + pl.h)
        groups.setdefault(key, []).append((e, pl))
    for (route, _lo, _hi), items in groups.items():
        if len(items) < 2:
            continue
        parent = list(range(len(items)))

        def find(i: int, parent=parent) -> int:
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                if items[i][0].src == items[j][0].src or items[i][0].dst == items[j][0].dst:
                    parent[find(i)] = find(j)
        bundles: dict[int, list[int]] = {}
        for i in range(len(items)):
            bundles.setdefault(find(i), []).append(i)
        if len(bundles) < 2:
            continue

        def span(ix: list[int], route=route, items=items) -> tuple[int, int]:
            if route == "v":
                xs = [v for i in ix for v in (items[i][1].x, items[i][1].x + items[i][1].w)]
            else:
                xs = [v for i in ix for v in (items[i][1].y, items[i][1].y + items[i][1].h)]
            return min(xs), max(xs)

        order = sorted(bundles.values(), key=lambda ix: span(ix)[0])
        clusters: list[list[list[int]]] = []
        for ix in order:
            if clusters and span(ix)[0] < max(span(m)[1] for m in clusters[-1]):
                clusters[-1].append(ix)
            else:
                clusters.append([ix])
        for cl in clusters:
            if len(cl) < 2:
                continue
            for pos, ix in enumerate(cl):
                f = (pos + 1) / (len(cl) + 1)
                for i in ix:
                    pl = items[i][1]
                    at = pl.element.attrs
                    down = not (
                        pl.element.attrs.get("flip_v") if route == "v" else pl.element.attrs.get("flip_h")
                    )
                    at["adj"] = round(f if down else 1 - f, 4)


def _radius(th) -> Any:
    card = th.classes.get("node") or th.classes.get("card")
    return card.radius if card is not None and card.radius is not None else None


def _edge_label(c, pl, name: str, text: str, size: float) -> None:
    """The arrow label, centred on the middle segment of the connector, a knockout of the slide colour."""
    th = c.theme
    at = pl.element.attrs
    fh, fv = bool(at.get("flip_h")), bool(at.get("flip_v"))
    sx, ex = (pl.x + pl.w, pl.x) if fh else (pl.x, pl.x + pl.w)
    sy, ey = (pl.y + pl.h, pl.y) if fv else (pl.y, pl.y + pl.h)
    adj = float(at.get("adj", 0.5))
    if at.get("route") == "h":
        cx, cy = sx + adj * (ex - sx), (sy + ey) / 2
    else:
        cx, cy = (sx + ex) / 2, sy + adj * (ey - sy)
    pad = round(3 * EMU_PER_PT)
    w = _tw(text, size) + 2 * pad + round(0.04 * _IN)
    h = round(size * 1.35 * EMU_PER_PT)
    st = V._text_style(c, size, color=th.arch_edge_color, align="center", valign="middle", fill="bg")
    V._emit_text(
        c, name, [Paragraph(runs=[Run(text=text)])], Rect(round(cx - w / 2), round(cy - h / 2), w, h), st
    )


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


def _best_box(
    ins: list[tuple[float, float, float]], outs: list[tuple[float, float, float]], margin: float
) -> tuple[float, float, float, float]:
    """``(cx, cy, w, h)`` of the largest box of aspect ``_AR`` inside every circle of ``ins`` and outside
    every circle of ``outs`` (``margin`` from the outlines); ``w = 0`` when the region is empty."""
    x0, y0, r0 = ins[0]
    best = (x0, y0, 0.0, 0.0)
    steps = 26
    for iy in range(steps + 1):
        for ix in range(steps + 1):
            cx = x0 - r0 + 2 * r0 * ix / steps
            cy = y0 - r0 + 2 * r0 * iy / steps

            def ok(w: float, cx=cx, cy=cy) -> bool:
                h = w / _AR
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
            for _ in range(16):
                mid = (lo_w + hi_w) / 2
                lo_w, hi_w = (mid, hi_w) if ok(mid) else (lo_w, mid)
            if lo_w > best[2]:
                best = (cx, cy, lo_w, lo_w / _AR)
    return best


def _venn(c, slide: Slide, body: Rect, sg: int, info: dict) -> bool:
    th = c.theme
    bx = forms.boxes(slide) or []
    n = len(bx)
    if n not in (2, 3):
        return False
    base, ratio, hi, lo, pinned = V._sizes(c, slide)
    parts = [V._split_box(b) for b in bx]
    otext, ocls = forms6.split_trailing(forms6.edge_text(slide)) if forms6.edge_text(slide) else ("", [])
    o = th.venn_overlap or (0.36 if n == 2 else 0.42)
    fills = V._colors(slide, th.venn_fill)
    palette = [x for x in (th.palette or []) if x] or ["primary", "secondary", "muted"]
    focal_overlap = "focal" in ocls
    emu = V._emu

    def centres(r: float) -> list[tuple[float, float]]:
        d = 2 * r * (1 - o)
        if n == 2:
            return [(-d / 2, 0.0), (d / 2, 0.0)]
        return [(-d / 2, -d * 0.2887), (d / 2, -d * 0.2887), (0.0, d * 0.5774)]

    def extent(r: float) -> tuple[float, float]:
        d = 2 * r * (1 - o)
        return (2 * r + d, 2 * r) if n == 2 else (2 * r + d, 2 * r + 0.866 * d)

    def name_paras(i: int, s: float) -> list[Paragraph]:
        h = parts[i][0]
        if h is None:
            return []
        st = fast_style(font_size=round(s * ratio * 0.9, 2), bold=True)
        return [p.model_copy(update={"style": st.merged(p.style)}) for p in h.paragraphs]

    def solve(s: float, mode: str) -> dict[str, Any]:
        nst = V._text_style(c, s * ratio * 0.9, bold=True, align="center", valign="middle")
        # names: above the upper circles, below the lower one
        top_names = [i for i in range(n) if n == 2 or i < 2]
        bot_names = [i for i in range(n) if i not in top_names]
        band_top = max((round(V._need(c, name_paras(i, s), emu("2.4in"), nst)) for i in top_names), default=0)
        band_bot = max((round(V._need(c, name_paras(i, s), emu("2.4in"), nst)) for i in bot_names), default=0)
        air = round(0.08 * _IN)
        room_h = body.h - band_top - band_bot - air * (1 + (1 if bot_names else 0))
        # circle radius: from the height and the width, or the token
        r_h = room_h / (extent(1.0)[1])
        r_w = body.w * (0.96 if mode == "in" else 0.5) / extent(1.0)[0]
        r = min(r_h, r_w)
        if th.venn_size:
            r = min(r, emu(th.venn_size) / 2)
        cs = centres(r)
        w_, h_ = extent(r)
        ox = body.x + body.w / 2
        oy = body.y + band_top + air + (room_h - h_) / 2 + (r if n == 2 else r + 0.2887 * 2 * r * (1 - o))
        circ = [(ox + cx, oy + cy, r) for cx, cy in cs]
        margin = 0.04 * r + 3 * EMU_PER_PT
        boxes_: list[tuple[float, float, float, float]] = []
        aligns: list[str] = []
        fit = True
        for i in range(n):
            body_t = parts[i][1]
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
            if not body_t:
                continue
            if bxi[2] <= 0:
                fit = False
                continue
            st = V._text_style(c, s, align=al, valign="middle")
            need = V._need(c, V._paras(None, body_t, s, 1.0, None), round(bxi[2]), st)
            fit = fit and need <= bxi[3]
        ob = _best_box(list(circ), [], margin)
        osize = s
        ofits_ok = True
        if otext:
            op = [Paragraph(runs=[Run(text=otext, bold=True)])]

            def ofits(z: float) -> bool:
                st = V._text_style(c, z, bold=True, align="center", valign="middle")
                return ob[2] > 0 and V._need(c, op, round(ob[2]), st) <= ob[3]

            osize, ofit = V._largest(s, lo, ofits)
            ofits_ok = ofit
        return {
            "r": r,
            "circ": circ,
            "boxes": boxes_,
            "aligns": aligns,
            "ob": ob,
            "osize": osize,
            "fit": fit,
            "ofit": ofits_ok,
            "band_top": band_top,
            "air": air,
            "mode": mode,
        }

    want = th.venn_text if th.venn_text in ("in", "out") else "auto"
    best: dict[str, Any] | None = None
    size = hi
    plan_: list[tuple[str, float]] = []
    if pinned:
        plan_ = [("out" if want == "out" else "in", hi)]
    else:
        floor_in = max(lo, base * th.venn_in_min)
        if want in ("in", "auto"):
            plan_ += [("in", z) for z in _sizes_down(hi, floor_in if want == "auto" else lo)]
        if want in ("out", "auto"):
            plan_ += [("out", z) for z in _sizes_down(hi, lo)]
    for mode_, z in plan_:
        best = solve(z, mode_)
        size = z
        if best["fit"]:
            break
    if best is None:
        best = solve(hi, "in")
    S = best
    r, circ = S["r"], S["circ"]
    # circles (translucent, in the palette); a `.focal` set takes the accent
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
    # focal overlap: an accent tint ellipse inset in the lens, under the labels
    ob = S["ob"]
    if focal_overlap and ob[2] > 0:
        lw_ = (2 * r - (circ[1][0] - circ[0][0])) * 0.86 if n == 2 else r * 0.7
        lh_ = (
            2 * math.sqrt(max(r * r - ((circ[1][0] - circ[0][0]) / 2) ** 2, 0.0)) * 0.7 if n == 2 else r * 0.7
        )
        c.emit(
            Shape(shape="ellipse", attrs={"shape_name": "Venn overlap fill"}),
            Rect(round(ob[0] - lw_ / 2), round(ob[1] - lh_ / 2), round(lw_), round(lh_)),
            fast_style(fill="accent", opacity=max(th.venn_alpha, 0.35), line=None),
        )
    ncol = th.venn_name_color
    nst = V._text_style(c, size * ratio * 0.9, bold=True, color=ncol, align="center", valign="middle")
    for i in range(n):
        ps = name_paras(i, size)
        if not ps:
            continue
        cx, cy, rr = circ[i]
        up = n == 2 or i < 2
        w = round(min(2.4 * _IN, 0.96 * 2 * rr * (1 - o)) if up else min(2.4 * _IN, 1.9 * rr))
        hh = round(S["band_top"] if up else max(S["band_top"], size * ratio * 1.6 * EMU_PER_PT))
        y = round(cy - rr - S["air"] - hh) if up else round(cy + rr + S["air"])
        V._emit_text(
            c,
            f"Venn {i + 1} name",
            ps,
            Rect(round(cx - w / 2), y, w, hh),
            nst.merged(fast_style(valign="bottom" if up else "top")),
        )
    for i in range(n):
        bxi = S["boxes"][i]
        if not parts[i][1] or bxi[2] <= 0:
            continue
        w, h = round(bxi[2]), round(bxi[3])
        V._emit_text(
            c,
            f"Venn {i + 1} text",
            V._paras(None, parts[i][1], size, 1.0, None),
            Rect(round(bxi[0] - w / 2), round(bxi[1] - h / 2), w, h),
            V._text_style(c, size, align=S["aligns"][i], valign="middle"),
        )
    if otext and ob[2] > 0:
        w, h = round(ob[2]), round(ob[3])
        V._emit_text(
            c,
            "Venn overlap",
            [Paragraph(runs=[Run(text=otext, bold=True)])],
            Rect(round(ob[0] - w / 2), round(ob[1] - h / 2), w, h),
            V._text_style(c, S["osize"], bold=True, align="center", valign="middle"),
        )
    info.update(n=n, size=size, fit=S["fit"] and S["ofit"], overlap=bool(otext), text=S["mode"])
    if not (S["fit"] and S["ofit"]):
        c.over.append("@venn text")
    return True


FORMS = {"arch": _arch, "venn": _venn}

_ = (re, Text)
