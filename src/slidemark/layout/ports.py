"""Connector ports and bend levels of the diagram forms: no two arrows ever share a segment.

``engine._emit_links`` joins the middle of one box side to the middle of another, so two arrows that enter or
leave the same box side run on top of each other. :func:`plan` routes a list of box-to-box arrows instead:

- every box side that carries N arrows gives each its own **port**: the port follows where the arrow comes
  from / goes to, kept inside ``L/(N+1) .. L*N/(N+1)`` of the side and at least ``sep`` apart (a lone arrow
  keeps the middle, so aligned boxes stay joined by a straight line); a jog shorter than ``sep`` is snapped
  straight;
- the middle segments (bends) of the elbows between the same two rows (columns for ``route="h"``) take
  separate levels at least ``sep`` apart, ordered by brute force for the fewest crossings.

Pure geometry on :class:`Rect`; :func:`emit` draws the native connector. A connector whose end is off the
middle of its side is not glued to the box (a connection site is the middle of a side).
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Any

from ..ir import Shape, fast_style
from ..units import EMU_PER_PT
from .grid import Rect

PX = 9525  # EMU per pixel at 96 dpi
SEP = round(9 * EMU_PER_PT)  # 12 px: the least distance of two parallel arrows / ports


@dataclass
class Route:
    src: int
    dst: int
    route: str  # "v" (leaves through a top / bottom side) | "h"
    fwd: bool  # towards larger y (v) / larger x (h)
    p0: tuple[int, int] = (0, 0)
    p1: tuple[int, int] = (0, 0)
    adj: float = 0.5
    free: list[str] = field(default_factory=list)  # ends off the middle of their side: "s" / "e"
    label: bool = False

    @property
    def elbow(self) -> bool:
        return (self.route == "v" and self.p0[0] != self.p1[0]) or (
            self.route == "h" and self.p0[1] != self.p1[1]
        )

    def poly(self) -> list[tuple[int, int]]:
        (x0, y0), (x1, y1) = self.p0, self.p1
        if not self.elbow:
            return [self.p0, self.p1]
        if self.route == "h":
            mx = round(x0 + self.adj * (x1 - x0))
            return [self.p0, (mx, y0), (mx, y1), self.p1]
        my = round(y0 + self.adj * (y1 - y0))
        return [self.p0, (x0, my), (x1, my), self.p1]


def _spread(desired: list[float], lo_edge: float, length: float, sep: float) -> list[float]:
    """Port positions (absolute) of ``len(desired)`` arrows on one side that starts at ``lo_edge``."""
    n = len(desired)
    lo, hi = length / (n + 1), length - length / (n + 1)
    pos = [min(max(d - lo_edge, lo), hi) for d in desired]
    for i in range(1, n):
        pos[i] = max(pos[i], pos[i - 1] + sep)
    for i in range(n - 2, -1, -1):
        pos[i] = min(pos[i], pos[i + 1] - sep)
    if n > 1 and (pos[0] < sep / 2 or pos[-1] > length - sep / 2):  # no room: even spacing
        pos = [length * (i + 1) / (n + 1) for i in range(n)]
    return [lo_edge + p for p in pos]


def _seg_cross(a: tuple, b: tuple, c: tuple, d: tuple) -> bool:
    """Interior crossing of two axis-parallel segments a-b and c-d (perpendicular ones)."""
    ah, ch = a[1] == b[1], c[1] == d[1]
    if ah == ch:
        return False
    (h0, h1), (v0, v1) = ((a, b), (c, d)) if ah else ((c, d), (a, b))
    hx0, hx1 = sorted((h0[0], h1[0]))
    vy0, vy1 = sorted((v0[1], v1[1]))
    return hx0 < v0[0] < hx1 and vy0 < h0[1] < vy1


def crossings(polys: list[list[tuple[int, int]]]) -> int:
    n = 0
    for i, pa in enumerate(polys):
        for pb in polys[i + 1 :]:
            for s in zip(pa, pa[1:], strict=False):
                for t in zip(pb, pb[1:], strict=False):
                    n += _seg_cross(s[0], s[1], t[0], t[1])
    return n


def _hits(p0: tuple[int, int], p1: tuple[int, int], r: Rect) -> bool:
    x0, x1 = sorted((p0[0], p1[0]))
    y0, y1 = sorted((p0[1], p1[1]))
    return x1 > r.x and x0 < r.right and y1 > r.y and y0 < r.bottom


def plan(
    edges: list[tuple[int, int]],
    rects: dict[int, Rect],
    prefer: str | None = None,
    sep: int = SEP,
    labelled: set[int] | None = None,
) -> list[Route | None]:
    """One :class:`Route` per ``(src, dst)`` pair (``None`` for a pair that cannot be drawn)."""
    out: list[Route | None] = []
    for s, d in edges:
        a, b = rects.get(s), rects.get(d)
        if a is None or b is None or s == d:
            out.append(None)
            continue
        side = b.x >= a.right or a.x >= b.right
        if (b.y >= a.bottom or a.y >= b.bottom) and not (prefer == "h" and side):
            out.append(Route(s, d, "v", b.y >= a.bottom))
        elif side:
            out.append(Route(s, d, "h", b.x >= a.right))
        else:
            out.append(None)
    for i, r in enumerate(out):
        if r is not None and labelled and i in labelled:
            r.label = True
    # --- ports
    sides: dict[tuple[int, str], list[tuple[int, str]]] = {}
    for i, r in enumerate(out):
        if r is None:
            continue
        if r.route == "v":
            ss, ds = ("b", "t") if r.fwd else ("t", "b")
        else:
            ss, ds = ("r", "l") if r.fwd else ("l", "r")
        sides.setdefault((r.src, ss), []).append((i, "s"))
        sides.setdefault((r.dst, ds), []).append((i, "e"))
    pos: dict[tuple[int, str], float] = {}  # (edge, end) -> absolute coordinate along the side

    def desired(i: int, end: str) -> float:
        r = out[i]
        assert r is not None
        other = rects[r.dst if end == "s" else r.src]
        return other.x + other.w / 2 if r.route == "v" else other.y + other.h / 2

    def span(node: int, side: str) -> tuple[float, float]:
        rc = rects[node]
        return (rc.x, rc.w) if side in "tb" else (rc.y, rc.h)

    for (node, side), items in sides.items():
        items.sort(key=lambda it: (desired(*it), it[0]))
        lo_edge, length = span(node, side)
        for it, p in zip(items, _spread([desired(*it) for it in items], lo_edge, length, sep), strict=True):
            pos[it] = p
    # snap short jogs straight (move the end that stays clear of its neighbours)
    for i, r in enumerate(out):
        if r is None:
            continue
        ds_ = pos[(i, "s")] - pos[(i, "e")]
        if 0 < abs(ds_) < sep:
            for end, other in (("e", "s"), ("s", "e")):
                node = r.dst if end == "e" else r.src
                side = next(sd for (nd, sd), its in sides.items() if nd == node and (i, end) in its)
                lo_edge, length = span(node, side)
                new = pos[(i, other)]
                near = [
                    pos[it] for it in sides[(node, side)] if it != (i, end)
                ]  # the other ports of this side
                if lo_edge + 0.15 * length <= new <= lo_edge + 0.85 * length and all(
                    abs(new - q) >= sep for q in near
                ):
                    pos[(i, end)] = new
                    break
    for i, r in enumerate(out):
        if r is None:
            continue
        a, b = rects[r.src], rects[r.dst]
        if r.route == "v":
            y0, y1 = (a.bottom, b.y) if r.fwd else (a.y, b.bottom)
            r.p0, r.p1 = (round(pos[(i, "s")]), y0), (round(pos[(i, "e")]), y1)
            mids = (a.x + a.w // 2, b.x + b.w // 2)
        else:
            x0, x1 = (a.right, b.x) if r.fwd else (a.x, b.right)
            r.p0, r.p1 = (x0, round(pos[(i, "s")])), (x1, round(pos[(i, "e")]))
            mids = (a.y + a.h // 2, b.y + b.h // 2)
        k = 0 if r.route == "v" else 1
        tol = round(2 * PX)
        if abs(r.p0[k] - mids[0]) > tol:
            r.free.append("s")
        if abs(r.p1[k] - mids[1]) > tol:
            r.free.append("e")
        if r.route == "v" and abs(r.p0[0] - r.p1[0]) <= tol:
            r.p1 = (r.p0[0], r.p1[1])
        if r.route == "h" and abs(r.p0[1] - r.p1[1]) <= tol:
            r.p1 = (r.p1[0], r.p0[1])
    _bends(out, rects, sep)
    return out


def _pt(route: str, main: float, cross: float) -> tuple[int, int]:
    return (round(cross), round(main)) if route == "v" else (round(main), round(cross))


def _bends(out: list[Route | None], rects: dict[int, Rect], sep: int) -> None:
    """Free level of every elbow's middle segment, then separate levels inside one gap."""
    base: dict[int, tuple[float, float]] = {}  # edge -> free interval (main axis) around its first choice
    for i, r in enumerate(out):
        if r is None or not r.elbow:
            continue
        k = 1 if r.route == "v" else 0  # index of the main axis in a point
        m0, m1 = r.p0[k], r.p1[k]
        lo, hi = min(m0, m1), max(m0, m1)
        c0, c1 = r.p0[1 - k], r.p1[1 - k]
        others = [rc for n, rc in rects.items() if n not in (r.src, r.dst)]

        def free(c: float, r=r, c0=c0, c1=c1, m0=m0, m1=m1, others=others) -> bool:
            pts = [_pt(r.route, m0, c0), _pt(r.route, c, c0), _pt(r.route, c, c1), _pt(r.route, m1, c1)]
            return not any(_hits(u, v, rc) for rc in others for u, v in zip(pts, pts[1:], strict=False))

        mid = (lo + hi) / 2
        step = max(round(2 * PX), 1)
        cands = sorted(range(int(lo) + step, int(hi), step), key=lambda c, mid=mid: abs(c - mid))
        first = next((c for c in cands if free(c)), mid)
        a = b = first
        while a - step > lo and free(a - step):
            a -= step
        while b + step < hi and free(b + step):
            b += step
        base[i] = (a, b)
    groups: dict[tuple, list[int]] = {}
    for i in base:
        r = out[i]
        assert r is not None
        k = 1 if r.route == "v" else 0
        groups.setdefault((r.route, round(r.p0[k] / PX), round(r.p1[k] / PX)), []).append(i)
    for (_route, _a, _b), ids in groups.items():
        route = out[ids[0]].route  # type: ignore[union-attr]
        ax = 0 if route == "v" else 1  # the cross axis of a point
        # clusters of edges whose cross spans (with the sep margin) overlap
        ids.sort(key=lambda i: min(out[i].p0[ax], out[i].p1[ax]))  # type: ignore[union-attr]
        clusters: list[list[int]] = []
        reach = -1e18
        for i in ids:
            r = out[i]
            assert r is not None
            lo_c, hi_c = min(r.p0[ax], r.p1[ax]), max(r.p0[ax], r.p1[ax])
            if clusters and lo_c < reach + sep:
                clusters[-1].append(i)
                reach = max(reach, hi_c)
            else:
                clusters.append([i])
                reach = hi_c
        for cl in clusters:
            _levels(out, cl, base, sep)


def _levels(out: list[Route | None], cl: list[int], base: dict[int, tuple[float, float]], sep: int) -> None:
    rs = [out[i] for i in cl]
    r0 = rs[0]
    assert r0 is not None
    k = 1 if r0.route == "v" else 0
    a = max(base[i][0] for i in cl)
    b = min(base[i][1] for i in cl)
    if a > b:  # no shared free interval: each keeps its own middle
        for i in cl:
            lo_, hi_ = base[i]
            _set(out[i], (lo_ + hi_) / 2)  # type: ignore[arg-type]
        return
    n = len(cl)
    near_dst = r0.route == "h" and any(r.label for r in rs if r)  # labelled: a long stub for the label
    slots: list[float] = []
    for j in range(n):
        if near_dst:
            d = 1.2 * sep * (j + 1)
            slots.append(b - d if r0.fwd else a + d)
        else:
            slots.append(a + (b - a) * (j + 1) / (n + 1))
    slots = [min(max(s, a), b) for s in slots]
    best, best_n = None, 10**9
    perms = itertools.permutations(range(n)) if n <= 6 else [tuple(range(n))]
    for perm in perms:
        trial = []
        for idx, slot in zip(cl, perm, strict=True):
            r = out[idx]
            assert r is not None
            c = slots[slot]
            m0, m1 = r.p0[k], r.p1[k]
            r.adj = (c - m0) / (m1 - m0) if m1 != m0 else 0.5
            trial.append(r.poly())
        nx = crossings(trial)
        if nx < best_n:
            best, best_n = perm, nx
            if nx == 0:
                break
    for idx, slot in zip(cl, best or range(n), strict=True):
        _set(out[idx], slots[slot])  # type: ignore[arg-type]


def _set(r: Route, level: float) -> None:
    k = 1 if r.route == "v" else 0
    m0, m1 = r.p0[k], r.p1[k]
    r.adj = round((level - m0) / (m1 - m0), 4) if m1 != m0 else 0.5


def emit(c, r: Route, rects: dict[int, Rect], name: str) -> Any:
    """Draw ``r`` as a native connector (under its boxes, glued where its ends are on a site)."""
    (x0, y0), (x1, y1) = r.p0, r.p1
    attrs: dict[str, Any] = {
        "head": "arrow",
        "flip_h": x1 < x0,
        "flip_v": y1 < y0,
        "elbow": r.elbow,
        "route": r.route,
        "adj": round(r.adj, 4),
        "shape_name": name,
        "src_box": [rects[r.src].x, rects[r.src].y, rects[r.src].w, rects[r.src].h],
        "dst_box": [rects[r.dst].x, rects[r.dst].y, rects[r.dst].w, rects[r.dst].h],
        "under": True,
    }
    if r.free:
        attrs["free_ends"] = list(r.free)
    return c.emit(
        Shape(shape="line", attrs=attrs),
        Rect(min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0)),
        fast_style(),
    )


def segment_rects(poly: list[tuple[int, int]], w: int = PX) -> list[Rect]:
    """The segments of ``poly`` as thin rectangles (obstacles for labels)."""
    out = []
    for (x0, y0), (x1, y1) in zip(poly, poly[1:], strict=False):
        out.append(Rect(min(x0, x1) - w // 2, min(y0, y1) - w // 2, abs(x1 - x0) + w, abs(y1 - y0) + w))
    return out
