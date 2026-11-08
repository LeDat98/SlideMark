"""Diagram complexity budget: the info rule ``diagram-budget`` (never a warning).

Editorial diagram rules (diagram-design): "above 9 nodes it is probably two diagrams", at most 12 arrows,
arrow labels of at most 14 characters, 1-2 accent elements. One ``Diagnostic`` per slide at most, with every
reason combined:

- nodes > ``layout.diagram_nodes`` or edges > ``layout.diagram_edges``, in a ```mermaid fence (a ``Container``
  with class ``diagram``: nodes = its children) or in blocks joined by ``@ a>b`` connectors (nodes = the
  distinct blocks the links join);
- an edge label longer than ``layout.diagram_label``;
- more than ``layout.diagram_accents`` shapes drawn in the theme accent colour (fill or line) on a slide that
  holds a diagram; charts, tables, images, connector lines and text runs are not counted.

The thresholds are layout tokens: ``style: lint.diagram_nodes=12`` (or ``layout.diagram_nodes=12``); 0 = off.
Never raises.
"""

from __future__ import annotations

from collections.abc import Iterator

from .ir import Chart, Container, Diagnostic, Image, Media, Placed, Shape, Slide, Table
from .theme import Theme

RULE = "diagram-budget"


def _containers(slide: Slide) -> Iterator[Container]:
    def rec(el) -> Iterator[Container]:
        if isinstance(el, Container):
            yield el
            for c in el.children:
                yield from rec(c)

    for el in slide.elements:
        yield from rec(el)


def _graphs(slide: Slide) -> list[tuple[int, list]]:
    """(node count, links) of every diagram on the slide: mermaid containers and connector-joined blocks."""
    out: list[tuple[int, list]] = []
    if slide.links:
        out.append((len({i for lk in slide.links for i in (lk.src, lk.dst)}), list(slide.links)))
    for c in _containers(slide):
        if not c.links:
            continue
        if "diagram" in c.classes:
            out.append((len(c.children), list(c.links)))
        else:
            out.append((len({i for lk in c.links for i in (lk.src, lk.dst)}), list(c.links)))
    return out


def _accent(color: str | None, theme: Theme, accent: str) -> bool:
    return bool(color) and (theme.color(color) or "").strip().lower() == accent


def accent_shapes(items: list[Placed], theme: Theme) -> int:
    """Shapes drawn in the accent colour (fill or line); decoration without text and connectors excluded."""
    accent = (theme.color("accent") or "").strip().lower()
    if not accent:
        return 0
    n = 0
    for p in items:
        el = p.element
        if isinstance(el, (Chart, Table, Image, Media)):
            continue
        if isinstance(el, Shape) and el.shape in ("line", "arrow-right", "connector", "arc"):
            continue
        if getattr(el, "role", None) in ("title", "subtitle", "lead", "caption") or el.attrs.get("field"):
            continue
        if _accent(p.style.fill, theme, accent) or _accent(p.style.line, theme, accent):
            n += 1
    return n


def budget_diagnostic(
    slide: Slide | None, items: list[Placed], theme: Theme, index: int
) -> Diagnostic | None:
    """The ``diagram-budget`` info of one slide, or ``None`` when the diagram is within budget."""
    if slide is None:
        return None
    try:
        lt = theme.layout
        graphs = _graphs(slide)
        if not graphs:
            return None
        why: list[str] = []
        hints: list[str] = []
        nodes = max(n for n, _ in graphs)
        edges = max(len(lk) for _, lk in graphs)
        if lt.diagram_nodes and nodes > lt.diagram_nodes:
            why.append(f"{nodes} nodes (keep <= {lt.diagram_nodes}: split into two diagrams)")
            hints.append("split it into two diagrams")
        if lt.diagram_edges and edges > lt.diagram_edges:
            why.append(f"{edges} arrows (keep <= {lt.diagram_edges})")
            hints.append("drop the arrows that restate the layout")
        labels = [lk.label for _, links in graphs for lk in links if lk.label]
        long = [x for x in labels if lt.diagram_label and len(x) > lt.diagram_label]
        if long:
            why.append(
                f"arrow label '{long[0][:20]}' has {len(long[0])} characters (keep <= {lt.diagram_label})"
            )
            hints.append("shorten edge labels to a word or two")
        accents = accent_shapes(items, theme)
        if lt.diagram_accents and accents > lt.diagram_accents:
            why.append(f"{accents} accent shapes (keep <= {lt.diagram_accents})")
            hints.append("accent only the 1-2 nodes that matter")
        if not why:
            return None
        hint = "; ".join(hints[:2]) + " (thresholds: style: lint.diagram_nodes=N)"
        return Diagnostic(level="info", message="; ".join(why), slide=index + 1, rule=RULE, hint=hint)
    except Exception:  # feedback must never break a build
        return None
