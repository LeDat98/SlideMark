"""Connectors -> ``@`` link tokens (``a>b``, ``a-b``) and mermaid flowcharts.

Pure geometry on EMU rectangles: no pptx objects, no layout decisions. Endpoints are resolved from glued
``a:stCxn``/``a:endCxn`` ids first, then from the box edge a connector end touches; pieces of a loop that the
renderer draws as several straight connectors are chained first.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .read import ConnT, Item
    from .structure import Block

TOUCH = 45720  # 0.05 in: an end this close to a box edge touches it
NEAR = 274320  # 0.3 in: last-resort tolerance for ends that touch nothing
JOIN = 30000  # two free ends this close belong to the same polyline
LABEL_NEAR = 228600  # 0.25 in: an unfilled text this close to a connector is its label
NODE_PRST = ("roundRect", "rect", "diamond", "flowChartDecision", "ellipse", "flowChartTerminator")
ROUND_PT = 8.5  # corner radius above which a node is written ``(text)``

Pt = tuple[float, float]
Rect = tuple[float, float, float, float]


@dataclass
class Edge:
    pts: list[Pt]
    s: int | None  # index of the rect at the start
    e: int | None  # index of the rect at the end
    arrow_start: bool
    arrow_end: bool
    order: int
    conns: list[ConnT] = field(default_factory=list)

    def flipped(self) -> Edge:
        return Edge(
            self.pts[::-1], self.e, self.s, self.arrow_end, self.arrow_start, self.order, list(self.conns)
        )

    @property
    def arrow(self) -> bool:
        return self.arrow_start or self.arrow_end


# --------------------------------------------------------------------------- geometry


def _dist(p: Pt, r: Rect) -> float:
    dx = max(r[0] - p[0], 0, p[0] - (r[0] + r[2]))
    dy = max(r[1] - p[1], 0, p[1] - (r[1] + r[3]))
    return math.hypot(dx, dy)


def _nearest(p: Pt, rects: list[Rect], tol: float) -> int | None:
    best: tuple[tuple[int, float], int] | None = None
    for i, r in enumerate(rects):
        d = _dist(p, r)
        if d <= tol:
            key = (round(d / 20000), r[2] * r[3])
            if best is None or key < best[0]:
                best = (key, i)
    return best[1] if best else None


def _close(a: Pt, b: Pt) -> bool:
    return math.hypot(a[0] - b[0], a[1] - b[1]) <= JOIN


def _seg_point(a: Pt, b: Pt, p: Pt) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    ln = dx * dx + dy * dy
    t = 0.0 if ln == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / ln))
    return math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy))


def _seg_rect(a: Pt, b: Pt, r: Rect) -> float:
    """Distance between a segment and a rectangle (0 when they cross)."""
    corners = [(r[0], r[1]), (r[0] + r[2], r[1]), (r[0] + r[2], r[1] + r[3]), (r[0], r[1] + r[3])]
    if _dist(a, r) == 0 or _dist(b, r) == 0:
        return 0.0
    for k in range(4):  # a segment crossing the rect with both ends outside
        c, d = corners[k], corners[(k + 1) % 4]
        if _cross(a, b, c, d):
            return 0.0
    return min(
        min(_dist(a, r), _dist(b, r)),
        *(_seg_point(a, b, c) for c in corners),
    )


def _cross(a: Pt, b: Pt, c: Pt, d: Pt) -> bool:
    def o(p: Pt, q: Pt, r: Pt) -> float:
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    return o(a, b, c) * o(a, b, d) < 0 and o(c, d, a) * o(c, d, b) < 0


def _poly_rect(pts: list[Pt], r: Rect) -> float:
    return min((_seg_rect(a, b, r) for a, b in zip(pts, pts[1:], strict=False)), default=math.inf)


# --------------------------------------------------------------------------- edges


def _sid_map(items: list[Item], rects: list[Rect]) -> dict[int, int]:
    """Shape id -> index of the smallest rect that fully contains the shape."""
    out: dict[int, int] = {}
    t = 20000
    for it in items:
        if not it.sid or it.area <= 0:
            continue
        best: int | None = None
        for i, r in enumerate(rects):
            if (
                r[0] - t <= it.x
                and r[1] - t <= it.y
                and it.x + it.w <= r[0] + r[2] + t
                and it.y + it.h <= r[1] + r[3] + t
                and (best is None or r[2] * r[3] < rects[best][2] * rects[best][3])
            ):
                best = i
        if best is not None:
            out[it.sid] = best
    return out


def _merge(edges: list[Edge]) -> list[Edge]:
    """Chain connectors whose free ends meet (a loop drawn as straight pieces)."""
    while True:
        for i in range(len(edges)):
            for j in range(i + 1, len(edges)):
                for fa in (False, True):
                    for fb in (False, True):
                        a = edges[i].flipped() if fa else edges[i]
                        b = edges[j].flipped() if fb else edges[j]
                        if a.e is None and b.s is None and _close(a.pts[-1], b.pts[0]):
                            m = Edge(
                                a.pts + b.pts,
                                a.s,
                                b.e,
                                a.arrow_start,
                                b.arrow_end,
                                min(a.order, b.order),
                                a.conns + b.conns,
                            )
                            edges = [x for k, x in enumerate(edges) if k not in (i, j)] + [m]
                            break
                    else:
                        continue
                    break
                else:
                    continue
                break
            else:
                continue
            break
        else:
            return edges


def network_edges(conns: list[ConnT], rects: list[Rect]) -> tuple[list[Edge], list[ConnT]]:
    """Tree networks (a bus line with branches, as in an org chart): one edge from the topmost rect the
    network touches to each other rect it touches. Returns the edges and the connectors left for the rest."""
    n = len(conns)
    segs = [((c.x0, c.y0), (c.x1, c.y1)) for c in conns]
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    tee = [False] * n
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            for p in segs[i]:
                if _seg_point(segs[j][0], segs[j][1], p) <= 3 * JOIN:
                    parent[find(i)] = find(j)
                    if min(math.hypot(p[0] - q[0], p[1] - q[1]) for q in segs[j]) > 6 * JOIN:
                        tee[j] = True  # an end lands in the middle of j: a branching bus
    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    edges: list[Edge] = []
    used: set[int] = set()
    for members in groups.values():
        if len(members) < 3 or not any(tee[i] for i in members):
            continue
        touched = sorted(
            {k for k, r in enumerate(rects) for i in members if _seg_rect(*segs[i], r) <= TOUCH * 2}
        )
        if len(touched) < 3:
            continue
        root = min(touched, key=lambda k: (rects[k][1] + rects[k][3] / 2, rects[k][0]))
        arrow = any(conns[i].arrow_end or conns[i].arrow_start for i in members)
        cs = [conns[i] for i in members]
        order = min(c.order for c in cs)
        for k in touched:
            if k != root:
                edges.append(
                    Edge([segs[members[0]][0], segs[members[0]][1]], root, k, False, arrow, order, cs)
                )
        used.update(members)
    return edges, [c for i, c in enumerate(conns) if i not in used]


def build_edges(conns: list[ConnT], rects: list[Rect], sid: dict[int, int]) -> list[Edge]:
    """Edges with both ends on a rect (start and end may be the same rect), in drawing order."""
    edges: list[Edge] = []
    for c in conns:
        s = sid.get(c.st) if c.st else None
        e = sid.get(c.en) if c.en else None
        p0, p1 = (c.x0, c.y0), (c.x1, c.y1)
        s = s if s is not None else _nearest(p0, rects, TOUCH)
        e = e if e is not None else _nearest(p1, rects, TOUCH)
        edges.append(Edge([p0, p1], s, e, c.arrow_start, c.arrow_end, c.order, [c]))
    edges = _merge(edges)
    for ed in edges:
        if ed.s is None:
            ed.s = _nearest(ed.pts[0], rects, NEAR)
        if ed.e is None:
            ed.e = _nearest(ed.pts[-1], rects, NEAR)
    out = []
    for ed in edges:
        if ed.s is None or ed.e is None:
            continue
        out.append(ed.flipped() if ed.arrow_start and not ed.arrow_end else ed)
    return sorted(out, key=lambda x: x.order)


# --------------------------------------------------------------------------- link tokens


def letter(i: int) -> str:
    return chr(97 + i) if i < 26 else str(i + 1)


def _box(b: Block) -> Rect:
    return (b.x, b.y, b.w, b.h)


def find_links(
    blocks: list[Block], conns: list[ConnT], items: list[Item]
) -> tuple[list[tuple[Block, Block, bool]], dict[int, list[tuple[Block, Block, bool]]], int]:
    """Slide-level links between ``blocks``, per box (keyed by ``id(block)``) links between its children,
    and how many connectors ended up in neither."""
    if not conns or not blocks:
        return [], {}, len(conns)
    kept: set[int] = set()
    rects = [_box(b) for b in blocks]
    net, rest = network_edges(conns, rects)
    edges = sorted([*build_edges(rest, rects, _sid_map(items, rects)), *net], key=lambda x: x.order)
    top: list[tuple[Block, Block, bool]] = []
    inner_conns: dict[int, list[ConnT]] = {}
    seen: set[tuple] = set()
    for ed in edges:
        if ed.s == ed.e:
            inner_conns.setdefault(ed.s, []).extend(ed.conns)
        else:
            kept.update(id(c) for c in ed.conns)
            if _fresh(seen, ed):
                top.append((blocks[ed.s], blocks[ed.e], ed.arrow))
    inner: dict[int, list[tuple[Block, Block, bool]]] = {}
    for bi, cs in inner_conns.items():
        b = blocks[bi]
        if b.kind != "box" or len(b.children) < 2:
            continue
        crects = [_box(c) for c in b.children]
        seen = set()
        refs = []
        for ed in build_edges(cs, crects, _sid_map(items, crects)):
            if ed.s != ed.e:
                kept.update(id(c) for c in ed.conns)
                if _fresh(seen, ed):
                    refs.append((b.children[ed.s], b.children[ed.e], ed.arrow))
        if refs:
            inner[id(b)] = refs
    return top, inner, len(conns) - len(kept)


def _fresh(seen: set[tuple], ed: Edge) -> bool:
    """True the first time a link (directed for arrows, undirected for lines) is seen."""
    key = (">", ed.s, ed.e) if ed.arrow else ("-", *sorted((ed.s or 0, ed.e or 0)))
    if key in seen:
        return False
    seen.add(key)
    return True


def tokens(links: list[tuple[Block, Block, bool]], order: list[Block], drop_next: bool = False) -> list[str]:
    """``a>b`` tokens; ``drop_next`` skips links between neighbours (``flow`` draws those already)."""
    idx = {id(b): i for i, b in enumerate(order)}
    out: list[str] = []
    for a, b, arrow in links:
        if id(a) not in idx or id(b) not in idx:
            continue
        i, j = idx[id(a)], idx[id(b)]
        if drop_next and arrow and j == i + 1:
            continue
        out.append(f"{letter(i)}{'>' if arrow else '-'}{letter(j)}")
    return out


# --------------------------------------------------------------------------- mermaid


@dataclass
class Diagram:
    lines: list[str]
    used: list[Block]  # nodes and labels the fence replaces
    box: Rect


def _node_text(text: str) -> str:
    text = text.replace("%%", "%").replace(";", ",").replace('"', "'")
    quoted = bool(re.search(r"[\[\](){}|<>]", text))
    text = "<br/>".join(x.strip() for x in text.split("\n") if x.strip())
    return f'"{text}"' if quoted else text


def _node(b: Block, nid: str) -> str:
    text = _node_text(b.item.text if b.item else "") or nid
    prst = b.item.prst if b.item else None
    if prst in ("diamond", "flowChartDecision"):
        return f"{nid}{{{text}}}"
    if prst in ("ellipse", "flowChartTerminator") or (
        b.item and b.item.radius is not None and b.item.radius > ROUND_PT
    ):
        return f"{nid}({text})"
    return f"{nid}[{text}]"


def recover_diagram(blocks: list[Block], conns: list[ConnT], items: list[Item]) -> Diagram | None:
    """A drawn flowchart: >= 3 filled node shapes joined by >= 2 connectors, and no ``##`` boxes."""
    if len(conns) < 2 or any(b.kind == "box" for b in blocks):
        return None
    nodes = [
        b
        for b in blocks
        if b.kind == "text"
        and b.item is not None
        and (b.item.fill or b.item.line)
        and b.item.prst in NODE_PRST
        and b.item.text
    ]
    if len(nodes) < 3:
        return None
    rects = [_box(b) for b in nodes]
    edges = [e for e in build_edges(conns, rects, _sid_map(items, rects)) if e.s != e.e]
    used = sorted({i for e in edges for i in (e.s, e.e) if i is not None})
    if len(edges) < 2 or len(used) < 3 or len(used) > 26:
        return None
    ids = {i: chr(65 + n) for n, i in enumerate(_appearance(edges, nodes, used))}
    # edge labels: unfilled short texts lying next to a connector
    labels: dict[int, str] = {}
    consumed: list[Block] = []
    for b in blocks:
        it = b.item
        if b.kind != "text" or it is None or it.fill or it.line or b in nodes or not it.text:
            continue
        if len(it.paras) != 1 or len(it.text) > 40:
            continue
        near = [(_poly_rect(e.pts, _box(b)), k) for k, e in enumerate(edges)]
        d, k = min(near)
        if d <= LABEL_NEAR and k not in labels:
            labels[k] = it.text.replace("|", "/")
            consumed.append(b)
    ends = [(nodes[e.s], nodes[e.e]) for e in edges if e.s is not None and e.e is not None]
    sx = sum(b.x + b.w / 2 - a.x - a.w / 2 for a, b in ends)
    sy = sum(b.y + b.h / 2 - a.y - a.h / 2 for a, b in ends)
    out = ["flowchart " + ("LR" if abs(sx) > abs(sy) else "TD")]
    declared: set[int] = set()

    def ref(i: int) -> str:
        if i in declared:
            return ids[i]
        declared.add(i)
        return _node(nodes[i], ids[i])

    seen: set[tuple] = set()
    for k, e in enumerate(edges):
        if e.s is None or e.e is None:
            continue
        key = (e.s, e.e, e.arrow, labels.get(k))
        if key in seen:
            continue
        seen.add(key)
        op = "-->" if e.arrow else "---"
        op += f"|{labels[k]}|" if k in labels else ""
        out.append(f"{ref(e.s)} {op} {ref(e.e)}")
    for i in used:
        if i not in declared:
            out.append(ref(i))
    members = [nodes[i] for i in used] + consumed
    x0, y0 = min(b.x for b in members), min(b.y for b in members)
    x1, y1 = max(b.x + b.w for b in members), max(b.y + b.h for b in members)
    return Diagram(out, members, (x0, y0, x1 - x0, y1 - y0))


def _appearance(edges: list[Edge], nodes: list[Block], used: list[int]) -> list[int]:
    order: list[int] = []
    for e in edges:
        for i in (e.s, e.e):
            if i is not None and i not in order:
                order.append(i)
    return order + [i for i in used if i not in order]
