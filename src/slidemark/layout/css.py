"""CSS selector matching: ``Deck.css`` / ``Slide.css`` rules applied to the IR during layout (DF3).

Grammar (see ``ir.CssRule``): ``compound ((" " | " > ") compound)*`` with
``compound = [type] [.class]* [#id] [:nth-child(even|odd|N)] [:first-child] [:last-child]``.

``CssIndex`` is built once per slide. It walks the slide to make a node tree (slide, ``h1``, ``.lead``, boxes,
``h2`` box headings, ``p``/``li`` text, tables with ``tr``/``th``/``td``, ``code``, ``img``, ``.chart``) and
answers ``own(el)``: the merged ``Style`` of every rule that matches, ordered by specificity then source order
(deck css before slide css). Text-like fields (color, fonts, letter spacing, text transform) are inherited
down the node tree: ``inherited(el)``. Merge order used by the engine: theme role -> inherited CSS -> theme
classes -> CSS rules -> inline ``{}`` style.

Also here: helpers shared by layout, lint and the renderer (per-side insets, borders, text transform,
margins, rotation of a placed subtree). Nothing here raises.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from functools import lru_cache

from ..ir import (
    Chart,
    Code,
    Container,
    CssRule,
    Deck,
    Diagnostic,
    Image,
    Media,
    Placed,
    Raw,
    Shape,
    Slide,
    Style,
    Table,
    Text,
    fast_style,
)
from ..units import EMU_PER_PT, to_emu
from .tablehl import hl_rows

INHERITED = ("color", "font", "font_ea", "letter_spacing", "text_transform")
_CSS_FIELDS = tuple(Style.model_fields)
_ROLE_CLASS = {"subtitle", "lead", "conclusion", "footnote", "caption", "quote"}
_ROLE_TYPE = {"title": "h1", "heading": "h2", "body": "p", "quote": "p", "caption": "p"}

# Style fields each element kind can draw natively; a CSS rule that sets another one gets a diagnostic.
_TEXTUAL = {
    "color",
    "font",
    "font_ea",
    "font_size",
    "bold",
    "italic",
    "align",
    "valign",
    "line_spacing",
    "letter_spacing",
    "text_transform",
    "underline",
    "strike",
}
_BOX = {
    "fill",
    "line",
    "line_width",
    "line_dash",
    "radius",
    "shadow",
    "opacity",
    "rotation",
    "margin",
    "padding",
    "padding_top",
    "padding_right",
    "padding_bottom",
    "padding_left",
    "border_top",
    "border_right",
    "border_bottom",
    "border_left",
}
_HONORED: dict[str, set[str]] = {
    "text": _TEXTUAL | _BOX | {"width"},
    "code": _TEXTUAL | _BOX | {"width"},
    "shape": _TEXTUAL | _BOX,
    "container": _TEXTUAL | _BOX | {"gap", "grid", "width"},
    "slide": {"fill", "gap", "grid", "color", "font", "font_ea", "font_size", "bold", "italic", "align"}
    | {"valign", "line_spacing", "letter_spacing", "text_transform"},
    "image": {
        "line",
        "line_width",
        "line_dash",
        "radius",
        "shadow",
        "opacity",
        "rotation",
        "margin",
        "width",
    },
    "chart": {"color", "font", "font_ea", "font_size", "margin", "width"},
    "table": _TEXTUAL | {"fill", "line", "line_width", "line_dash", "margin", "width"},
    "cell": _TEXTUAL
    | {
        "fill",
        "line",
        "line_width",
        "line_dash",
        "opacity",
        "padding",
        "padding_top",
        "padding_right",
        "padding_bottom",
        "padding_left",
        "border_top",
        "border_right",
        "border_bottom",
        "border_left",
    },
    "other": {"margin"},
}
_HONORED["row"] = _HONORED["cell"]
_PROP = {
    "fill": "background",
    "line": "border-color",
    "line_width": "border-width",
    "line_dash": "border-style",
    "radius": "border-radius",
    "shadow": "box-shadow",
    "font": "font-family",
    "font_size": "font-size",
    "bold": "font-weight",
    "italic": "font-style",
    "align": "text-align",
    "valign": "vertical-align",
    "line_spacing": "line-height",
    "rotation": "transform",
    "grid": "grid-template-*",
}


# --------------------------------------------------------------------------- selectors


@dataclass(frozen=True)
class Compound:
    type: str | None = None
    classes: tuple[str, ...] = ()
    id: str | None = None
    nth: str | None = None  # "even" | "odd" | "<N>"
    first: bool = False
    last: bool = False


@dataclass(frozen=True)
class Selector:
    parts: tuple[tuple[str, Compound], ...]  # (combinator to the previous compound, compound)
    spec: tuple[int, int, int]


_PART = re.compile(
    r"\.([A-Za-z_][\w-]*)|#([A-Za-z_][\w-]*)|:nth-child\((even|odd|\d+)\)|:(first-child|last-child)"
)
_TYPE = re.compile(r"[A-Za-z][A-Za-z0-9]*")


def _compound(text: str) -> Compound | None:
    pos, typ = 0, None
    m = _TYPE.match(text)
    if m:
        typ, pos = m.group(0).lower(), m.end()
    classes: list[str] = []
    cid = nth = None
    first = last = False
    while pos < len(text):
        pm = _PART.match(text, pos)
        if not pm:
            return None
        pos = pm.end()
        if pm.group(1):
            classes.append(pm.group(1))
        elif pm.group(2):
            cid = pm.group(2)
        elif pm.group(3):
            nth = pm.group(3)
        elif pm.group(4) == "first-child":
            first = True
        else:
            last = True
    return Compound(typ, tuple(classes), cid, nth, first, last)


@lru_cache(maxsize=512)
def compile_selector(text: str) -> Selector | None:
    """Parse one normalized selector (``a > b c``); ``None`` when it cannot be read."""
    parts: list[tuple[str, Compound]] = []
    comb = " "
    for tok in text.replace(">", " > ").split():
        if tok == ">":
            comb = ">"
            continue
        c = _compound(tok)
        if c is None:
            return None
        parts.append((comb, c))
        comb = " "
    if not parts:
        return None
    ids = sum(1 for _, c in parts if c.id)
    cls = sum(len(c.classes) + (1 if c.nth else 0) + int(c.first) + int(c.last) for _, c in parts)
    types = sum(1 for _, c in parts if c.type)
    return Selector(tuple(parts), (ids, cls, types))


# --------------------------------------------------------------------------- nodes


@dataclass(eq=False)
class Node:
    types: frozenset[str]
    classes: frozenset[str]
    kind: str  # slide | text | container | table | row | cell | code | image | chart | other
    id: str | None = None
    parent: Node | None = None
    nth: int = 1
    nth_last: int = 1
    el: object = None
    _own: Style | None = None
    _inh: Style | None = None
    _lines: dict[str, int | None] = field(default_factory=dict)


def _compound_match(c: Compound, n: Node) -> bool:
    if c.type and c.type not in n.types:
        return False
    if c.id and c.id != n.id:
        return False
    if any(k not in n.classes for k in c.classes):
        return False
    if c.first and n.nth != 1:
        return False
    if c.last and n.nth_last != 1:
        return False
    if c.nth:
        if c.nth == "even":
            return n.nth % 2 == 0
        if c.nth == "odd":
            return n.nth % 2 == 1
        return n.nth == int(c.nth)
    return True


def _match(parts: tuple[tuple[str, Compound], ...], i: int, n: Node | None) -> bool:
    """Does node ``n`` match ``parts[i]`` with the earlier parts matching its ancestors?"""
    if n is None or not _compound_match(parts[i][1], n):
        return False
    if i == 0:
        return True
    comb = parts[i][0]
    anc = n.parent
    if comb == ">":
        return _match(parts, i - 1, anc)
    while anc is not None:
        if _match(parts, i - 1, anc):
            return True
        anc = anc.parent
    return False


def slide_kind(slide: Slide, index: int) -> str:
    """Layout kind of a slide, as the engine infers it: cover | section | blank | center | content."""
    if slide.layout in ("cover", "section", "blank", "center", "content", "free"):
        return slide.layout
    if slide.layout is None and slide.title and not slide.elements and not slide.conclusion:
        return "cover" if index == 0 else "section"
    return "content"


# --------------------------------------------------------------------------- the index


class CssIndex:
    """Selector matching for one slide. ``active`` is False without any rule (every lookup is free)."""

    def __init__(self, deck: Deck, slide: Slide, index: int = 0, kind: str | None = None):
        self.slide = slide
        self.slide_no = index + 1
        self.kind = kind or slide_kind(slide, index)
        self.rules: list[tuple[Selector, CssRule, int]] = []
        for order, rule in enumerate([*deck.css, *slide.css]):
            sel = compile_selector(rule.selector)
            if sel is not None:
                self.rules.append((sel, rule, order))
        self.rules.sort(key=lambda t: (t[0].spec, t[2]))
        self.active = bool(self.rules)
        self.nodes: dict[int, Node] = {}
        self.kpi_nodes: dict[int, tuple[Node, Node]] = {}
        self.diags: list[Diagnostic] = []
        self._tcache: dict[int, Table] = {}
        self._done: set[int] = set()
        self._reported: set[tuple[str, str]] = set()
        self.root: Node | None = None
        if self.active:
            try:
                self._build()
            except Exception:  # never raise: no css for this slide
                self.active = False

    # ---- node tree
    def _reg(self, el, node: Node) -> Node:
        self.nodes[id(el)] = node
        cl = getattr(el, "classes", None)
        if cl is not None:
            self.nodes[id(cl)] = node  # survives model_copy (the classes list is shared)
        node.el = el
        return node

    def _make(self, parent: Node, type_: str, classes, kind: str, el=None, eid=None) -> Node:
        n = Node(frozenset(type_.split()), frozenset(classes), kind, eid, parent)
        if el is not None:
            self._reg(el, n)
        return n

    @staticmethod
    def _number(nodes: list[Node]) -> None:
        for i, n in enumerate(nodes):
            n.nth, n.nth_last = i + 1, len(nodes) - i

    def _text_node(self, parent: Node, el: Text, as_type: str | None = None) -> Node:
        role = el.role
        classes = set(el.classes)
        if role in _ROLE_CLASS:
            classes.add(role)
        typ = as_type or _ROLE_TYPE.get(role, "div")
        if typ == "p" and any(p.marker for p in el.paragraphs):
            typ = "p li"
        return self._make(parent, typ, classes, "text", el, el.id)

    def _block(self, parent: Node, el) -> Node | None:
        if isinstance(el, Container):
            classes = set(el.classes)
            if "plain" not in classes:
                classes.add("box")
            n = self._make(parent, "div", classes, "container", el, el.id)
            kids: list[Node] = []
            if el.title is not None and el.title.paragraphs:
                kids.append(self._text_node(n, el.title, "h2"))
            for ch in el.children:
                if (k := self._block(n, ch)) is not None:
                    kids.append(k)
            self._number(kids)
            if "kpi" in classes:  # virtual nodes: `.kpi .value` (the big number), `.kpi .caption`
                self.kpi_nodes[id(el)] = (
                    Node(frozenset({"p"}), frozenset({"value"}), "text", None, n),
                    Node(frozenset({"p"}), frozenset({"caption"}), "text", None, n),
                )
            return n
        if isinstance(el, Text):
            return self._text_node(parent, el)
        if isinstance(el, Table):
            n = self._make(parent, "table", el.classes, "table", el, el.id)
            return n
        if isinstance(el, Code):
            return self._make(parent, "code", el.classes, "code", el, el.id)
        if isinstance(el, (Image, Media)):
            return self._make(parent, "img", el.classes, "image", el, el.id)
        if isinstance(el, Chart):
            return self._make(parent, "div", {*el.classes, "chart"}, "chart", el, el.id)
        if isinstance(el, Shape):
            return self._make(parent, "div", el.classes, "shape", el, el.id)
        if isinstance(el, Raw):
            return self._make(parent, "div", {*el.classes, el.kind}, "other", el, el.id)
        return None

    def _build(self) -> None:
        s = self.slide
        classes = set(s.classes)
        if self.kind in ("cover", "section", "blank", "center"):
            classes.add(self.kind)
        root = Node(frozenset({"slide"}), frozenset(classes), "slide", s.id, None)
        self.root = root
        self.nodes[id(s)] = root
        kids: list[Node] = []
        if s.title is not None:
            kids.append(self._text_node(root, s.title, "h1"))
        for el in (s.subtitle, s.lead):
            if el is not None and el.paragraphs:
                kids.append(self._text_node(root, el))
        for el in s.elements:
            if (k := self._block(root, el)) is not None:
                kids.append(k)
        if s.conclusion is not None:
            kids.append(self._text_node(root, s.conclusion))
        for f in s.footnotes:
            kids.append(self._text_node(root, f))
        self._number(kids)

    # ---- aliases / lookups
    def alias(self, new, old) -> None:
        """Make ``new`` (a copy the layout made of ``old``) match the same node."""
        if (n := self.node(old)) is not None:
            self.nodes[id(new)] = n

    def node(self, el) -> Node | None:
        if not self.active or el is None:
            return None
        n = self.nodes.get(id(el))
        if n is None:
            cl = getattr(el, "classes", None)
            if cl is not None:
                n = self.nodes.get(id(cl))
        if n is None:
            src = getattr(el, "attrs", {}).get("_css_src")
            if src is not None:
                n = self.nodes.get(src)
        return n

    def slide_node(self) -> Node | None:
        return self.root

    # ---- styles
    def _matched(self, n: Node) -> Style:
        merged: dict[str, object] = {}
        lines: dict[str, int | None] = {}
        for sel, rule, _ in self.rules:
            if _match(sel.parts, len(sel.parts) - 1, n):
                for k, v in rule.style.model_dump().items():
                    if v is not None:
                        merged[k] = v
                        lines[k] = rule.line
        n._lines = lines
        try:
            return Style(**merged)  # type: ignore[arg-type]
        except Exception:
            return fast_style()

    def _compute(self, n: Node) -> None:
        if n._own is not None:
            return
        own = self._matched(n)
        n._own = own
        inh: dict[str, object] = {}
        if n.parent is not None and n.kind not in ("row", "cell"):
            self._compute(n.parent)
            assert n.parent._own is not None and n.parent._inh is not None
            for k in INHERITED:
                v = getattr(n.parent._own, k)
                if v is None:
                    v = getattr(n.parent._inh, k)
                if v is not None:
                    inh[k] = v
        n._inh = Style(**inh)  # type: ignore[arg-type]
        self._check(n, own)

    def _check(self, n: Node, own: Style) -> None:
        """One ``css-unsupported`` warning per element kind listing the properties it cannot draw."""
        honored = _HONORED.get(n.kind, set())
        bad: list[str] = []
        line = None
        for f in _CSS_FIELDS:
            if getattr(own, f) is None or f in honored or (n.kind, f) in self._reported:
                continue
            self._reported.add((n.kind, f))
            prop = _PROP.get(f, f.replace("_", "-"))
            if prop not in bad:
                bad.append(prop)
            line = line or n._lines.get(f)
        if bad:
            what = {"image": "images", "chart": "charts", "slide": "the slide", "table": "tables"}.get(
                n.kind, "this element"
            )
            self.diags.append(
                Diagnostic(
                    level="warning",
                    message=f"css {', '.join(bad)} not drawn on {what}",
                    slide=self.slide_no,
                    line=line,
                    rule="css-unsupported",
                    hint="move it to a box (.box) or remove it",
                )
            )

    def own(self, el) -> Style:
        """Style of the rules that match ``el`` (empty when none)."""
        n = self.node(el)
        if n is None:
            return fast_style()
        self._compute(n)
        return n._own or fast_style()

    def kpi_styles(self, box) -> tuple[Style, Style]:
        """``(value, caption)`` CSS of a ``.kpi`` box.

        The box's own text properties (``.kpi { color; font-size; font-family; font-weight }``) style the big
        number; ``.kpi .value`` / ``.kpi p`` refine it, ``.kpi .caption`` / ``.kpi p`` style the caption.
        """
        pair = self.kpi_nodes.get(id(box)) if self.active else None
        if pair is None:
            return fast_style(), fast_style()
        box_own = self.own(box)
        keep = {
            k: getattr(box_own, k) for k in ("font_size", "bold", "italic") if getattr(box_own, k) is not None
        }
        out = []
        for i, n in enumerate(pair):
            self._compute(n)
            own = n._own or fast_style()
            st = (n._inh or fast_style()).merged(own)
            out.append(Style(**keep).merged(st) if i == 0 else own)
        return out[0], out[1]

    def inherited(self, el) -> Style:
        n = self.node(el)
        if n is None:
            return fast_style()
        self._compute(n)
        return n._inh or fast_style()

    # ---- tables
    def table(self, t: Table) -> Table:
        """Copy of ``t`` whose cells carry the th/td/tr rules (their ``style`` = css, then inline)."""
        if id(t) in self._done:
            return t
        if (hit := self._tcache.get(id(t))) is not None:
            return hit
        tn = self.node(t)
        if tn is None or not t.rows:
            return t
        tbl_own = self.own(t)
        tbl_text = fast_style(letter_spacing=tbl_own.letter_spacing, text_transform=tbl_own.text_transform)
        hl = hl_rows(t)  # `tr.hl` styles the rows an `hl=` emphasises
        row_nodes = [
            Node(frozenset({"tr"}), frozenset({"hl"}) if ri in hl else frozenset(), "row", None, tn)
            for ri in range(len(t.rows))
        ]
        self._number(row_nodes)
        rows = []
        for ri, row in enumerate(t.rows):
            rn = row_nodes[ri]
            cells = []
            for ci, cell in enumerate(row):
                hdr = ri < t.header_rows or ci < t.header_cols
                cn = Node(frozenset({"th" if hdr else "td"}), frozenset(), "cell", None, rn)
                cn.nth, cn.nth_last = ci + 1, len(row) - ci
                own = tbl_text.merged(self._cell_style(rn, cn))
                if any(v is not None for v in own.model_dump().values()):
                    cell = cell.model_copy(update={"style": own.merged(cell.style)})
                cells.append(cell)
            rows.append(cells)
        out = t.model_copy(update={"rows": rows})
        self.nodes[id(out)] = tn
        self._tcache[id(t)] = out
        self._done.add(id(out))
        return out

    def _cell_style(self, rn: Node, cn: Node) -> Style:
        """tr rules first, then th/td rules (a cell paints over its row)."""
        if rn._own is None:
            rn._own = self._matched(rn)
            rn._inh = fast_style()
            self._check(rn, rn._own)
        cell_own = self._matched(cn)
        self._check(cn, cell_own)
        return rn._own.merged(cell_own)

    def diagnostics(self) -> list[Diagnostic]:
        return list(self.diags)


_EMPTY: Style = fast_style()


def slide_style(deck: Deck, slide: Slide, index: int = 0) -> Style:
    """The CSS rules that match the slide itself (``slide``, ``slide.cover``, ...): background, color, ..."""
    try:
        ix = CssIndex(deck, slide, index)
        if not ix.active or ix.root is None:
            return _EMPTY
        return ix.own(slide)
    except Exception:
        return _EMPTY


# --------------------------------------------------------------------------- shared helpers


def _emu(v) -> int | None:
    if v is None:
        return None
    try:
        return to_emu(v)
    except (ValueError, TypeError):
        return None


def border_spec(value: str | None) -> tuple[float, str, str] | None:
    """``(width pt, dash, color)`` of ``"<w>pt <solid|dash|dot> <color>"``; None for none / bad."""
    if not value or value.strip().lower() == "none":
        return None
    parts = value.split(None, 2)
    try:
        width = float(parts[0].removesuffix("pt"))
    except (ValueError, IndexError):
        return None
    if width <= 0:
        return None
    dash = parts[1] if len(parts) > 1 and parts[1] in ("solid", "dash", "dot") else "solid"
    color = parts[2].strip() if len(parts) > 2 else "fg"
    return width, dash, color


def side_borders(st: Style, default_width: float = 0.75) -> dict[str, tuple[float, str, str] | None]:
    """Per side: the border to draw, or None. A side without its own ``border_*`` uses the uniform line."""
    uniform = None
    if st.line and (st.line_width is None or st.line_width > 0):
        uniform = (
            st.line_width if st.line_width is not None else default_width,
            st.line_dash or "solid",
            st.line,
        )
    out: dict[str, tuple[float, str, str] | None] = {}
    for side in ("top", "right", "bottom", "left"):
        v = getattr(st, f"border_{side}")
        out[side] = border_spec(v) if v is not None else uniform
    return out


def has_side_borders(st: Style) -> bool:
    return any(getattr(st, f"border_{s}") is not None for s in ("top", "right", "bottom", "left"))


def insets(st: Style, default: float = 0.0) -> tuple[int, int, int, int]:
    """(left, top, right, bottom) text-frame insets in EMU: ``padding`` (``default`` when unset), per-side
    ``padding_*`` over it, plus the width of each per-side ``border_*`` (CSS box model)."""
    base = _emu(st.padding)
    base = round(default) if base is None else base
    d = st.__dict__
    if (
        d["padding_top"] is None
        and d["padding_right"] is None
        and d["padding_bottom"] is None
        and d["padding_left"] is None
        and d["border_top"] is None
        and d["border_right"] is None
        and d["border_bottom"] is None
        and d["border_left"] is None
    ):  # the common case: one padding on every side
        base = max(base, 0)
        return base, base, base, base
    vals = []
    for side in ("left", "top", "right", "bottom"):
        v = _emu(getattr(st, f"padding_{side}"))
        pad = base if v is None else v
        b = getattr(st, f"border_{side}")
        spec = border_spec(b) if b is not None else None
        vals.append(max(pad, 0) + (round(spec[0] * EMU_PER_PT) if spec else 0))
    return vals[0], vals[1], vals[2], vals[3]


def cell_insets(st: Style | None, dx: int, dy: int) -> tuple[int, int, int, int]:
    """(left, top, right, bottom) EMU margins of a table cell: ``dx`` / ``dy`` unless the cell style sets
    ``padding`` / ``padding_*`` (borders do not add to a cell)."""
    if st is None:
        return dx, dy, dx, dy
    base = _emu(st.padding)
    out = []
    for side, d in (("left", dx), ("top", dy), ("right", dx), ("bottom", dy)):
        v = _emu(getattr(st, f"padding_{side}"))
        out.append(max(v if v is not None else (base if base is not None else d), 0))
    return out[0], out[1], out[2], out[3]


def inset_hv(st: Style, default: float = 0.0) -> tuple[int, int]:
    """(horizontal, vertical) total insets in EMU."""
    left, top, right, bottom = insets(st, default)
    return left + right, top + bottom


def margin_emu(st: Style) -> int:
    v = _emu(st.margin)
    return max(v, 0) if v else 0


def transform_text(text: str, mode: str | None) -> str:
    if mode == "upper":
        return text.upper()
    if mode == "lower":
        return text.lower()
    if mode == "capitalize":
        return re.sub(r"(?<![\w'])(\w)", lambda m: m.group(1).upper(), text)
    return text


def rotate_placed(items: list[Placed], cx: float, cy: float, deg: float) -> bool:
    """Rotate placed items about (cx, cy) by ``deg`` clockwise: centers move, each item gets ``rotation``.

    Returns False when a connector was among them (its geometry is left alone)."""
    rad = math.radians(deg)
    cos, sin = math.cos(rad), math.sin(rad)
    ok = True
    for p in items:
        if isinstance(p.element, Shape) and p.element.shape == "line":
            ok = False
            continue
        mx, my = p.x + p.w / 2 - cx, p.y + p.h / 2 - cy
        nx, ny = cx + mx * cos - my * sin, cy + mx * sin + my * cos
        p.x, p.y = round(nx - p.w / 2), round(ny - p.h / 2)
        p.style = p.style.merged(fast_style(rotation=round(((p.style.rotation or 0) + deg) % 360, 3)))
    return ok
