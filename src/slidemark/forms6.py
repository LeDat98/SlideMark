"""Wave 2026-11-08 lane D: ``@arch`` (layered architecture) and ``@venn`` (2-3 overlapping circles).

Source syntax (shortest unambiguous form, no lookup):

``@arch``  each ``## Tier`` box is a tier (rows top to bottom; ``dir=h`` = columns), each list item a node:
``- [API] API gateway {.focal}``, ``- Postgres: orders, users {.store}`` (a leading ``[TAG]`` is the type tag;
text after the first colon is a mono sublabel; the role classes ``.focal .store .external .input
.optional .security`` restyle the node).
The connections are the final ``>`` line of the slide, edges by node name: ``> Web > API, API > Postgres,
API > Stripe: charge`` (a chain ``A > B > C`` is two arrows, the text after ``:`` labels the last arrow of the
item, a trailing ``{.focal}`` draws that arrow in the accent). Why a ``>`` line: it is the slide's last
block, so it reads as a caption of the diagram, needs no ids and no grid letters, and an agent that forgets
it still gets a valid diagram without arrows.

``@venn``  2-3 ``## Set`` boxes (heading = set name, body = the set's own text); an optional final
``> overlap text`` is written at the centre where the circles meet (``{.focal}`` fills it in the accent
tint, and ``## Set {.focal}`` the circle). One centre label, not one per intersection: the diagram-design
rule is "label what the diagram is about"; named pairwise intersections would need a second syntax.

The parser lifts the final ``>`` line out of ``Slide.conclusion`` into ``Slide.attrs["form_text"]`` (so no
conclusion bar is drawn for it) and warns about what cannot be drawn (``arch-edge``, ``arch-node``).

======================  ===========================================================================
token                   meaning
======================  ===========================================================================
``arch.gap``            air between tiers, where the arrows run (a length; default from the labels)
``arch.node.w``         node width (a length; default from the longest label, shared by all nodes)
``arch.node.h``         node height (a length; default from the tallest node text)
``arch.node.gap``       air between nodes of a tier (a length; default 0.2in)
``arch.tier.look``      ``auto`` (rows: a caption; columns: a dashed container for 2+ nodes) ``caption``
                        ``box`` ``band``; a set ``arch.tier.fill`` / ``.line`` means ``band``
``arch.tier.fill``      fill of a tier band (``band`` look; default: a faint ``muted`` tint; ``none``)
``arch.tier.line``      outline of a tier band (default: none)
``arch.tier.label``     colour of the tier caption (default ``muted``)
``arch.tier.label.size``  caption size in pt (default 0.75 x the node text, at least 9)
``arch.tier.pad``       padding inside a tier band (a length; default 0.12in)
``arch.label.w``        width of the caption column of a row tier (a length; default from the captions)
``arch.sub.size``       sublabel size / node text size (default 0.8)
``arch.sub.color``      sublabel colour (default ``muted``)
``arch.edge.size``      arrow label size in pt (default 0.8 x the node text, at least 9)
``arch.edge.color``     arrow label colour (default ``muted``)
``venn.fill``           circle fills ``a,b,c`` (default: the first palette colours)
``venn.alpha``          fill opacity 0-1 of a circle (default 0.3)
``venn.line``           circle outline colour (default: the circle's own colour) and ``venn.line.w`` width
``venn.size``           circle diameter (a length; default from the room)
``venn.overlap``        share of a diameter two neighbouring circles share (default 0.36, three sets 0.42)
``venn.name.color``     colour of the set names (default ``fg``)
``venn.max``            largest circle diameter (a length; default 3.6in: circles are never grown to fill)
``venn.core``           fill of the overlap of all sets, an exact lens (default ``primary``)
``venn.text``           where a set's text goes: ``in`` the circle, ``out`` beside it, ``auto`` (default:
                        inside while it reads at ``venn.in.min`` x the body size, else beside the circle)
``venn.in.min``         smallest inside text, share of the body size (default 0.75)
======================  ===========================================================================
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from typing import Any

from pydantic import Field

from .forms4 import Forms4Tokens
from .forms5 import Forms5Tokens, kind_of, split_tag
from .ir import Link, Slide

Length = str | float | int


class Forms6Tokens(Forms5Tokens):
    """Theme fields of wave 2026-11-08 lane D (``None`` = derive: the layout decides)."""

    arch_gap: Length | None = None
    arch_node_w: Length | None = None
    arch_node_h: Length | None = None
    arch_node_gap: Length = "0.2in"
    arch_tier_fill: str | None = None
    arch_tier_line: str | None = None
    arch_tier_label: str = "muted"
    arch_tier_label_size: float | None = None
    arch_tier_pad: Length = "0.12in"
    arch_label_w: Length | None = None
    arch_sub_size: float = Field(0.8, ge=0.4, le=1.0)
    arch_sub_color: str = "muted"
    arch_edge_size: float | None = None
    arch_edge_color: str = "muted"
    venn_fill: str | None = None
    venn_alpha: float = Field(0.3, ge=0.05, le=1.0)
    venn_line: str | None = None
    venn_line_w: Length = "1pt"
    venn_size: Length | None = None
    venn_overlap: float | None = Field(None, ge=0.1, le=0.6)
    venn_name_color: str = "fg"
    venn_text: str = "auto"
    venn_in_min: float = Field(0.75, ge=0.3, le=1.0)
    venn_max: Length = "3.6in"
    venn_core: str = "primary"
    arch_tier_look: str = "auto"
    # diagram kit (docs/SYNTAX.md "Diagram tokens"): shared by @arch @swimlane @sequence @venn
    diagram_legend: str = "auto"
    diagram_legend_text: str | None = None
    diagram_name_size: float = Field(13.0, ge=6, le=40)
    diagram_name_min: float = Field(11.0, ge=6, le=40)
    diagram_sub_size: float = Field(9.0, ge=6, le=30)
    diagram_tag_size: float = Field(8.0, ge=6, le=20)
    diagram_label_size: float = Field(8.0, ge=6, le=20)
    diagram_legend_size: float = Field(9.0, ge=6, le=20)
    diagram_tag_track: float = Field(0.18, ge=0, le=0.6)
    diagram_label_track: float = Field(0.08, ge=0, le=0.6)
    diagram_font: str | None = None
    diagram_muted: str = "muted"
    diagram_tag_line: str = "border"
    diagram_arrow: str | None = None
    diagram_arrow_primary: str = "accent"
    diagram_arrow_http: str = "link"
    diagram_arrow_return: str | None = None
    diagram_arrow_w: Length | None = None
    diagram_return_dash: str = "dash"
    diagram_node_pad: Length = "8pt"
    diagram_act_fill: str = "surface"
    diagram_act_line: str = "muted"
    diagram_act_w: Length = "9pt"
    diagram_hairline: Length = "0.75pt"
    diagram_tag_radius: Length = "1pt"
    diagram_group_radius: Length = "6pt"


_COLOR_LISTS = {"venn_fill"}
_COLORS = {"arch_tier_fill", "arch_tier_line", "arch_tier_label", "arch_sub_color", "arch_edge_color"}
_COLORS |= {"venn_line", "venn_name_color", "venn_core"}
_COLORS |= {"diagram_muted", "diagram_tag_line", "diagram_arrow", "diagram_arrow_primary"}
_COLORS |= {"diagram_arrow_http", "diagram_arrow_return", "diagram_act_fill", "diagram_act_line"}
_LENGTHS = {"arch_gap", "arch_node_w", "arch_node_h", "arch_node_gap", "arch_tier_pad", "arch_label_w"}
_LENGTHS |= {"venn_line_w", "venn_size", "venn_max", "diagram_arrow_w", "diagram_node_pad", "diagram_act_w"}
_LENGTHS |= {"diagram_hairline", "diagram_tag_radius", "diagram_group_radius"}
_PTS = {"arch_tier_label_size", "arch_edge_size"}
_NONE = ("none", "null", "off")
_NOT_NONE = {"arch_node_gap", "arch_tier_pad", "venn_line_w", "arch_tier_label", "arch_sub_color"}
_NOT_NONE |= {
    "arch_edge_color",
    "venn_name_color",
    "venn_core",
    "venn_max",
    "diagram_node_pad",
    "diagram_act_w",
}
_NOT_NONE |= {"diagram_muted", "diagram_tag_line", "diagram_arrow_primary", "diagram_arrow_http"}
_NOT_NONE |= {"diagram_act_fill", "diagram_act_line", "diagram_hairline", "diagram_tag_radius"}
_NOT_NONE |= {"diagram_group_radius"}
_WORDS = {
    "venn_text": ("in", "out", "auto"),
    "arch_tier_look": ("auto", "caption", "box", "band"),
    "diagram_legend": ("auto", "on", "off"),
    "diagram_return_dash": ("solid", "dash", "dot"),
}


def normalize(path: str, raw: str, names: set[str] | None) -> list[tuple[str, Any]] | None:
    """Validate one of this module's tokens (``None`` = not one of them). Raises ``theme.TokenValueError``."""
    if path not in Forms6Tokens.model_fields or path in Forms4Tokens.model_fields:
        return None
    from .theme import TokenValueError, _color_value, _length_value, _pt_value, _unquote

    v = _unquote(raw)
    key = path.replace("_", ".")
    if path in _WORDS:
        if v.lower() in _WORDS[path]:
            return [(path, v.lower())]
        raise TokenValueError(f"{key} is {', '.join(_WORDS[path])}", f"write {key}={_WORDS[path][0]}")
    if path in ("diagram_font", "diagram_legend_text"):
        return [(path, None if v.lower() in _NONE else v)]
    key = path.replace("_", ".")
    if path in _COLOR_LISTS:
        if v.lower() in _NONE:
            return [(path, None)]
        items = [p.strip() for p in v.split(",") if p.strip()]
        if not items:
            raise TokenValueError(f"{key} needs a color", f"write {key}=primary,secondary")
        return [(path, ",".join(_color_value(p, names) for p in items))]
    if path == "arch_tier_fill" and v.lower() in _NONE:
        return [(path, "none")]  # no band (``None`` would mean the derived tint)
    if path in _COLORS:
        if v.lower() in _NONE and path not in _NOT_NONE:
            return [(path, None)]
        return [(path, _color_value(raw, names))]
    if path in _PTS:
        if v.lower() in _NONE:
            return [(path, None)]
        return [(path, _pt_value(raw))]
    if path in _LENGTHS:
        if v.lower() in _NONE and path not in _NOT_NONE:
            return [(path, None)]
        return [(path, _length_value(raw))]
    return None


FIT_NAMES = {"arch": "architecture", "venn": "venn"}

# --------------------------------------------------------------------------- source model

_TRAIL = re.compile(r"\s*\{([^{}]*)\}\s*$")
_COLON = re.compile(r"[:：]")
_ARROW = re.compile(r"\s*(-->|~>|=>|->|→|>)\s*")  # `>` flow, `=>` primary, `~>` HTTP, `-->` return
_SPLIT = re.compile(r"[,;，；、\n]")
FORM_TEXT = "form_text"  # Slide.attrs key that holds the lifted final `>` line


@dataclass
class Node:
    name: str
    sub: str = ""
    classes: list[str] = field(default_factory=list)
    tier: int = 0
    tag: str = ""  # `[EXT] Reader`: the type tag drawn at the top-left of the card

    @property
    def key(self) -> str:
        return self.name.strip().lower()


@dataclass
class Arch:
    tiers: list[tuple[str, list[Node]]]
    nodes: list[Node]
    index: dict[str, int]  # lower-cased node name -> index in ``nodes`` (the first of equal names)


@dataclass
class Edge:
    src: int
    dst: int
    label: str | None = None
    focal: bool = False
    kind: str = "flow"  # flow | primary | http | return (the arrow symbol: `>` `=>` `~>` `-->`)


def split_trailing(text: str) -> tuple[str, list[str]]:
    """``text {.focal .store}`` -> (``text``, [``focal``, ``store``]); other ``{...}`` stay text."""
    m = _TRAIL.search(text)
    if not m:
        return text.strip(), []
    words = m.group(1).split()
    if not words or not all(w.startswith(".") and len(w) > 1 for w in words):
        return text.strip(), []
    return text[: m.start()].strip(), [w[1:] for w in words]


def parse_arch(slide: Slide) -> Arch | None:
    """The tiers and nodes of an ``@arch`` slide (``None`` = it is not one: no ``##`` boxes)."""
    from .forms import boxes

    bx = boxes(slide)
    if not bx:
        return None
    tiers: list[tuple[str, list[Node]]] = []
    nodes: list[Node] = []
    index: dict[str, int] = {}
    for ti, box in enumerate(bx):
        title = " ".join(p.plain.strip() for p in box.title.paragraphs) if box.title is not None else ""
        row: list[Node] = []
        for ch in box.children:
            for p in getattr(ch, "paragraphs", ()):
                if p.level > 0 or not p.plain.strip():
                    continue
                body, classes = split_trailing(p.plain)
                body, tag = split_tag(body)
                parts = _COLON.split(body, maxsplit=1)
                name = parts[0].strip()
                if not name:
                    continue
                n = Node(name, parts[1].strip() if len(parts) > 1 else "", classes, ti, tag)
                index.setdefault(n.key, len(nodes))
                nodes.append(n)
                row.append(n)
        tiers.append((title, row))
    return Arch(tiers, nodes, index)


def parse_edges(text: str, arch: Arch) -> tuple[list[Edge], list[tuple[str, str, str]]]:
    """``(edges, problems)`` of the ``>`` line; a problem is ``(rule, message, hint)``. Never raises."""
    edges: list[Edge] = []
    problems: list[tuple[str, str, str]] = []
    names = [n.name for n in arch.nodes]
    seen: set[tuple[int, int]] = set()
    for raw in _SPLIT.split(text or ""):
        item = raw.strip()
        if not item:
            continue
        item, classes = split_trailing(item)
        cut = _COLON.split(item, maxsplit=1)
        head = cut[0]
        label = cut[1].strip() or None if len(cut) > 1 else None
        pieces = _ARROW.split(head)  # name, arrow, name, arrow, name ...
        parts = [x.strip() for x in pieces[0::2]]
        syms = [kind_of(x) for x in pieces[1::2]]
        if len(parts) < 2 or any(not x for x in parts):
            problems.append(
                ("arch-edge", f"edge '{item[:30]}' is not 'A > B'", "write `> Web > API, API > Postgres`")
            )
            continue
        ids: list[int] = []
        for x in parts:
            k = arch.index.get(x.lower())
            if k is None:
                near = difflib.get_close_matches(x.lower(), list(arch.index), n=1, cutoff=0.5)
                dym = f"did you mean '{arch.nodes[arch.index[near[0]]].name}'?" if near else "no close name"
                problems.append(
                    (
                        "arch-edge",
                        f"edge '{item[:30]}': no node named '{x}'",
                        f"{dym} (nodes: {', '.join(names[:8])}{' ...' if len(names) > 8 else ''})",
                    )
                )
                ids = []
                break
            ids.append(k)
        for i, (a, b) in enumerate(zip(ids, ids[1:], strict=False)):
            if a == b:
                problems.append(("arch-edge", f"edge '{item[:30]}' joins a node to itself", "drop it"))
                continue
            if (a, b) in seen:
                continue
            seen.add((a, b))
            last = i == len(ids) - 2
            kind = syms[i] if i < len(syms) else "flow"
            edges.append(Edge(a, b, label if last else None, "focal" in classes, kind))
    return edges, problems


def edge_text(slide: Slide) -> str:
    """The lifted final ``>`` line of an ``@arch`` / ``@venn`` slide (``""`` when there is none)."""
    return str(slide.attrs.get(FORM_TEXT) or "")


# --------------------------------------------------------------------------- parser / build feedback


def fits_extra(form: str, slide: Slide) -> str | None:
    """What an ``@arch`` slide lacks beyond its ``##`` boxes (one sentence), else ``None``."""
    if form != "arch":
        return None
    arch = parse_arch(slide)
    if arch is None:
        return None
    empty = [t or f"#{i + 1}" for i, (t, row) in enumerate(arch.tiers) if not row]
    if empty:
        return f"@arch tier '{empty[0]}' has no nodes (one list item per node)"
    return None


def lift(slide: Slide, form: str | None) -> None:
    """Move the final ``>`` line of a composed ``@arch`` / ``@venn`` slide into ``attrs['form_text']``: it
    holds the edges / the overlap text, not a conclusion bar. Call only when ``forms.fits`` is satisfied."""
    if form not in ("arch", "venn") or slide.conclusion is None:
        return
    text = "\n".join(p.plain for p in slide.conclusion.paragraphs).strip()
    slide.conclusion = None
    if text:
        slide.attrs[FORM_TEXT] = text


def check(form: str | None, slide: Slide) -> list[tuple[str, str, str]]:
    """``(rule, message, hint)`` warnings for an ``@arch`` slide (edges that cannot be drawn, nodes that
    cannot be told apart). Pure."""
    if form != "arch":
        return []
    arch = parse_arch(slide)
    if arch is None:
        return []
    out: list[tuple[str, str, str]] = []
    seen: dict[str, int] = {}
    for n in arch.nodes:
        seen[n.key] = seen.get(n.key, 0) + 1
    dup = [k for k, v in seen.items() if v > 1]
    if dup:
        out.append(
            (
                "arch-node",
                f"node name '{dup[0]}' appears twice",
                "edges address a node by name: give every node its own name",
            )
        )
    edges, problems = parse_edges(edge_text(slide), arch)
    out += problems
    for e in edges:
        a, b = arch.nodes[e.src], arch.nodes[e.dst]
        row = arch.tiers[a.tier][1]
        if a.tier == b.tier and abs(row.index(a) - row.index(b)) > 1:
            out.append(
                (
                    "arch-edge",
                    f"arrow '{a.name} > {b.name}' crosses the nodes between them",
                    "join neighbours, or route through a node of another tier",
                )
            )
    return out


def graph(slide: Slide) -> tuple[int, list[Link]] | None:
    """``(node count, arrows)`` of an ``@arch`` slide for the ``diagram-budget`` rule, else ``None``."""
    from . import forms

    if forms.form_of(slide) != "arch" or forms.fits("arch", slide) is not None:
        return None
    arch = parse_arch(slide)
    if arch is None:
        return None
    edges, _ = parse_edges(edge_text(slide), arch)
    return len(arch.nodes), [Link(src=e.src, dst=e.dst, label=e.label) for e in edges]
