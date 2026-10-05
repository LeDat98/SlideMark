"""Mermaid flowcharts -> a ``Container(classes=["diagram"])`` of node texts with ``links`` and an areas grid.

Only ``graph``/``flowchart`` diagrams are understood. Anything else (sequenceDiagram, gantt, ...) or a
flowchart this module cannot read stays ``Raw(kind="mermaid")`` with an info diagnostic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..ir import Container, Link, Paragraph, Raw, Run, Text
from .ctx import Ctx

MAX_NODES = 26
HEADER_RE = re.compile(r"^(?:graph|flowchart)(?:[ \t]+(TD|TB|LR|RL|BT))?[ \t]*$", re.I)
IGNORED_RE = re.compile(
    r"^(subgraph|end|classDef|class|style|linkStyle|click|direction|accTitle|accDescr|title)\b", re.I
)
ID_RE = re.compile(r"[\w\u0080-\U0010ffff]+")
OPENERS = [
    ("((", "))", "round"),
    ("([", "])", "round"),
    ("[[", "]]", ""),
    ("[(", ")]", ""),
    ("{{", "}}", ""),
    ("(", ")", "round"),
    ("[", "]", ""),
    ("{", "}", "decision"),
]
END_TOKEN = r"(?:-{2,}>|-{3,}|\.+->|-\.+-|={2,}>|={3,})"
TEXT_EDGE_RE = re.compile(rf"(?:--|-\.|==)[ \t]+(.+?)[ \t]+({END_TOKEN})")
PLAIN_EDGE_RE = re.compile(r"<?(?:-{2,}[>xo]?|={2,}[>xo]?|-\.+-?>?|~{3,})")
LABEL_RE = re.compile(r"\|([^|]*)\|")
TAG_RE = re.compile(r"<[^>]*>")
BR_RE = re.compile(r"<br[ \t]*/?>", re.I)


class _Unsupported(Exception):
    pass


@dataclass
class _Graph:
    direction: str = "TD"
    order: list[str] = field(default_factory=list)
    text: dict[str, str] = field(default_factory=dict)
    kind: dict[str, str] = field(default_factory=dict)
    edges: list[tuple[str, str, bool, str | None]] = field(default_factory=list)

    def node(self, nid: str, text: str | None, kind: str) -> None:
        if nid not in self.text:
            self.order.append(nid)
            self.text[nid] = nid
            self.kind[nid] = ""
        if text is not None:
            self.text[nid] = text
            self.kind[nid] = kind


def _statements(source: str) -> list[str]:
    """Split on newlines and on ``;`` outside quotes and brackets."""
    out: list[str] = []
    buf: list[str] = []
    quote = False
    depth = 0
    for ch in source:
        if ch == '"':
            quote = not quote
        elif not quote:
            if ch in "[({":
                depth += 1
            elif ch in "])}" and depth:
                depth -= 1
        if ch == "\n" or (ch == ";" and not quote and depth == 0):
            out.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    out.append("".join(buf))
    return [s.strip() for s in out if s.strip()]


def _strip_comment(line: str) -> str:
    i = line.find("%%")
    return line if i < 0 else line[:i]


def _clean(text: str) -> str:
    return TAG_RE.sub("", BR_RE.sub("\n", text)).strip()


class _Stmt:
    def __init__(self, s: str, g: _Graph):
        self.s, self.i, self.g = s, 0, g

    def ws(self) -> None:
        while self.i < len(self.s) and self.s[self.i] in " \t":
            self.i += 1

    def node(self) -> str:
        m = ID_RE.match(self.s, self.i)
        if not m:
            raise _Unsupported(f"node id expected near {self.s[self.i : self.i + 12]!r}")
        nid = m.group(0)
        self.i = m.end()
        text: str | None = None
        kind = ""
        for op, cl, k in OPENERS:
            if self.s.startswith(op, self.i):
                j = self.i + len(op)
                while j < len(self.s) and self.s[j] in " \t":
                    j += 1
                if self.s.startswith('"', j):
                    q = self.s.find('"', j + 1)
                    if q < 0:
                        raise _Unsupported("unclosed quote")
                    text, j = self.s[j + 1 : q], q + 1
                    while j < len(self.s) and self.s[j] in " \t":
                        j += 1
                    if not self.s.startswith(cl, j):
                        raise _Unsupported("closing bracket expected")
                    self.i = j + len(cl)
                else:
                    e = self.s.find(cl, j)
                    if e < 0:
                        raise _Unsupported("unclosed bracket")
                    text, self.i = self.s[j:e], e + len(cl)
                kind = k
                break
        if self.s.startswith(":::", self.i):
            m2 = ID_RE.match(self.s, self.i + 3)
            self.i = m2.end() if m2 else self.i + 3
        self.g.node(nid, _clean(text) or nid if text is not None else None, kind)
        return nid

    def group(self) -> list[str]:
        ids = [self.node()]
        while True:
            self.ws()
            if self.s.startswith("&", self.i):
                self.i += 1
                self.ws()
                ids.append(self.node())
            else:
                return ids

    def edge(self) -> tuple[bool, str | None, bool] | None:
        """Returns (arrow, label, visible) or None when no edge operator follows."""
        m = TEXT_EDGE_RE.match(self.s, self.i)
        if m:
            self.i = m.end()
            return m.group(2).endswith(">"), _clean(m.group(1)) or None, True
        m = PLAIN_EDGE_RE.match(self.s, self.i)
        if not m:
            return None
        op = m.group(0)
        self.i = m.end()
        label = None
        lm = LABEL_RE.match(self.s, self.i)
        if lm:
            label = lm.group(1).strip().strip('"').strip() or None
            self.i = lm.end()
        arrow = op.endswith((">", "x", "o")) or op.startswith("<")
        return arrow, label, not op.startswith("~")

    def run(self) -> None:
        prev = self.group()
        while True:
            self.ws()
            if self.i >= len(self.s):
                return
            e = self.edge()
            if e is None:
                raise _Unsupported(f"unreadable text near {self.s[self.i : self.i + 12]!r}")
            arrow, label, visible = e
            self.ws()
            nxt = self.group()
            if visible:
                for a in prev:
                    for b in nxt:
                        self.g.edges.append((a, b, arrow, label))
            prev = nxt


def _parse(source: str) -> tuple[_Graph, bool]:
    """Read the flowchart; second value: whether lines were ignored (subgraph, classDef, ...)."""
    text = "\n".join(_strip_comment(ln) for ln in source.replace("\r", "").split("\n"))
    lines = text.split("\n")
    if lines and lines[0].strip() == "---":  # front matter
        for k in range(1, len(lines)):
            if lines[k].strip() == "---":
                lines = lines[k + 1 :]
                break
    stmts = _statements("\n".join(lines))
    if not stmts:
        raise _Unsupported("empty")
    m = HEADER_RE.match(stmts[0])
    if not m:
        raise _Unsupported("not a flowchart")
    g = _Graph(direction=(m.group(1) or "TD").upper().replace("TB", "TD"))
    ignored = False
    for s in stmts[1:]:
        if IGNORED_RE.match(s):
            ignored = True
            continue
        _Stmt(s, g).run()
    if not g.order:
        raise _Unsupported("no nodes")
    return g, ignored


# --------------------------------------------------------------------------- layout


def _ranks(g: _Graph) -> tuple[dict[str, int], dict[str, list[str]]]:
    """Longest path from the sources; back edges of cycles are dropped."""
    succ: dict[str, list[str]] = {n: [] for n in g.order}
    for a, b, _, _ in g.edges:
        if a != b and b not in succ[a]:
            succ[a].append(b)
    state: dict[str, int] = {}
    back: set[tuple[str, str]] = set()

    def dfs(u: str) -> None:
        state[u] = 1
        for v in succ[u]:
            if state.get(v) == 1:
                back.add((u, v))
            elif v not in state:
                dfs(v)
        state[u] = 2

    for n in g.order:
        if n not in state:
            dfs(n)
    pred: dict[str, list[str]] = {n: [] for n in g.order}
    for u in g.order:
        for v in succ[u]:
            if (u, v) not in back:
                pred[v].append(u)
    rank: dict[str, int] = {}

    def rk(n: str) -> int:
        if n not in rank:
            rank[n] = 0 if not pred[n] else 1 + max(rk(p) for p in pred[n])
        return rank[n]

    for n in g.order:
        rk(n)
    return rank, pred


def _layout(g: _Graph) -> tuple[list[str], str | None]:
    """Returns (node ids in output order, areas grid string or None for a single node)."""
    rank, pred = _ranks(g)
    top = max(rank.values())
    layers: list[list[str]] = [[n for n in g.order if rank[n] == r] for r in range(top + 1)]
    width = max(len(layer) for layer in layers)
    pos: dict[str, float] = {}
    cell: dict[str, tuple[int, int]] = {}  # node -> (rank, slot)
    appear = {n: i for i, n in enumerate(g.order)}
    for r, layer in enumerate(layers):
        if r:

            def median(n: str) -> float:
                xs = sorted(pos[p] for p in pred[n])
                m = len(xs) // 2
                return xs[m] if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2

            layer.sort(key=lambda n: (median(n), appear[n]))
        off = (width - len(layer)) // 2
        for k, n in enumerate(layer):
            pos[n] = off + k
            cell[n] = (r, off + k)
    reverse = g.direction in ("BT", "RL")
    vertical = g.direction in ("TD", "BT")
    nrank = top + 1
    rows, cols = (nrank, width) if vertical else (width, nrank)
    coord: dict[str, tuple[int, int]] = {}
    for n, (r, s) in cell.items():
        rr = nrank - 1 - r if reverse else r
        coord[n] = (rr, s) if vertical else (s, rr)
    order = list(g.order)
    if rows == 1:  # a single row needs ascending letters to be a valid areas grid
        order.sort(key=lambda n: coord[n][1])
    if len(order) == 1:
        return order, None
    letter = {n: chr(97 + i) for i, n in enumerate(order)}
    grid = [["."] * cols for _ in range(rows)]
    for n, (r, c) in coord.items():
        grid[r][c] = letter[n]
    return order, "/".join("".join(row) for row in grid)


def build_mermaid(source: str, ctx: Ctx, line: int | None) -> Container | Raw:
    """Convert a mermaid fence body. Never raises; falls back to ``Raw(kind="mermaid")``."""
    try:
        g, ignored = _parse(source)
    except (_Unsupported, RecursionError) as e:
        ctx.add(
            "info",
            f"mermaid diagram not converted ({e})",
            line,
            "mermaid-unsupported",
            "only 'graph TD|LR' / 'flowchart' diagrams become editable shapes; this one stays raw",
        )
        return Raw(kind="mermaid", source=source, line=line)
    if len(g.order) > MAX_NODES:
        ctx.warn(
            f"diagram has {len(g.order)} nodes (max {MAX_NODES})",
            line,
            "diagram-too-big",
            f"split it into diagrams of at most {MAX_NODES} nodes; kept as raw mermaid",
        )
        return Raw(kind="mermaid", source=source, line=line)
    if ignored:
        ctx.add(
            "info",
            "subgraph/classDef/style/click lines ignored",
            line,
            "mermaid-ignored",
            "styling and grouping are not converted; nodes and edges are",
        )
    order, grid = _layout(g)
    index = {n: i for i, n in enumerate(order)}
    children = []
    for n in order:
        classes = ["node"]
        if g.kind[n] in ("decision", "round"):
            classes.append(g.kind[n])
        paras = [Paragraph(runs=[Run(text=t)]) for t in g.text[n].split("\n") if t.strip()]
        children.append(
            Text(role="body", paragraphs=paras or [Paragraph(runs=[Run(text=n)])], classes=classes)
        )
    links: list[Link] = []
    seen: set[tuple[int, int, str | None]] = set()
    for a, b, arrow, label in g.edges:
        if a == b:
            continue
        key = (index[a], index[b], label)
        if key in seen:
            continue
        seen.add(key)
        links.append(Link(src=index[a], dst=index[b], arrow=arrow, label=label))
    return Container(classes=["diagram", "plain"], grid=grid, children=children, links=links, line=line)
