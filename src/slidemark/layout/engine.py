"""Layout engine: ``Slide`` -> ``list[Placed]`` in absolute EMU. Never touches python-pptx."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field, replace

from .. import icons
from ..ir import (
    Box,
    Chart,
    Code,
    Container,
    Deck,
    Diagnostic,
    Image,
    Link,
    Media,
    Paragraph,
    Placed,
    Raw,
    Shape,
    Slide,
    Style,
    Table,
    Text,
)
from ..template import footer_top
from ..theme import DEFAULT_SIZES, LayoutTokens, Theme, _base_classes
from ..units import EMU_PER_INCH, EMU_PER_PT, slide_size, to_emu
from . import css, measure
from .grid import GridSpec, Rect, auto_spec, cell_rects, parse_spec, tree_areas
from .grid import row_heights as grid_row_heights
from .score import score as score_layout
from .search import alternatives
from .tables import capped_width, column_widths, right_align_numbers, row_heights, table_grid

_SIZE_KEY = {
    "title": "title",
    "subtitle": "subtitle",
    "heading": "heading",
    "body": "body",
    "lead": "lead",
    "quote": "quote",
    "caption": "caption",
    "footnote": "footnote",
    "conclusion": "lead",
}
_INHERIT_ROLES = {"body", "quote"}
_INHERIT_FIELDS = (
    "font_size",
    "color",
    "bold",
    "italic",
    "align",
    "valign",
    "line_spacing",
    "font",
    "font_ea",
)
_VISUALS = (Image, Media, Chart, Table, Code)
_TOL = 1.01
SPARSE_LINES = 2
SPARSE_LINE_EM = 22  # a "short" line
SHORT_EM = 30  # boxes with at most this much text (in em) are "short": four of them stay in one row
HEAD_TOL = 0.98  # a box heading is raised to ctx.lt.head_body x its body only when it is more than 2% smaller
MAX_CANDIDATES = 6  # layout search: the rule's choice + at most this many - 1 alternatives per slide
SEARCH_SKIP = 1.5  # ... and no search at all when the rule's choice scores below this (it is fine)
SEARCH_MARGIN = 3.0  # ... an alternative must beat the rule's score by this much (the rule wins ties)
_SCALES = [round(1.0 - 0.05 * i, 2) for i in range(15)]  # 1.0 .. 0.3


TABLE_GROW_ROOMY = LayoutTokens().table_grow_roomy  # alias of the token default (tests, docs)


def _emu(value) -> int:
    """A length token (``0.7in``, ``4pt``) in EMU; a malformed value counts as 0."""
    try:
        return to_emu(value)
    except (ValueError, TypeError):
        return 0


_NOCSS = css.CssIndex(Deck(), Slide())


@dataclass
class _Ctx:
    deck: Deck
    theme: Theme
    slide: Slide
    index: int
    W: int
    H: int
    scale: float = 1.0
    dense_k: float = 1.0
    tight: float = 1.0  # gap / padding factor (dense slides)
    grow: float = 1.0  # body text growth inside boxes (sparse grids), shared by all sibling boxes
    depth: int = 0  # 0 = slide level, > 0 inside a box
    text_only: bool = False  # the slide body is plain text only: its body text grows like box text
    head_grow: bool = False  # very sparse boxes: box headings grow with ``grow`` (up to ``GROW_HEAD``)
    grew: bool = False  # set when ``grow`` actually scaled some text
    chev_grow: float = 1.0  # a chevron row alone on the slide: its text grows with ``grow``
    fill: float | None = None  # natural content height / grid height of the slide-level grid, if known
    expand: int = 0  # extra height (EMU) the capped rows of the slide-level grid may take
    arrange: str | None = None  # layout search: a grid token that replaces the rule-based arrangement
    alts: list[str] = field(default_factory=list)  # layout search: alternative tokens for this slide
    cap_tables: bool = True  # False when another block (box row, chart, ...) spans the body: no narrow table
    roomy: bool = False  # sparse dense slide with a large empty band: tables / trees may take more height
    grow_base: float = (
        1.0  # roomy pass: the growth before it; text that would wrap more at ``grow`` is refused
    )
    band_h: dict[tuple[int, int], int] = field(
        default_factory=dict
    )  # (box id, box width) -> heading height shared by the boxes of one row
    gaps: dict[int, float] = field(default_factory=dict)  # text id -> paragraph gap (em) of a roomy card
    text_out: dict[int, int] = field(default_factory=dict)  # text id -> index of its Placed in ``out``
    boxes: dict[int, list[int]] = field(default_factory=dict)  # box id -> ids of its spreadable texts
    out: list[Placed] = field(default_factory=list)
    over: list[str] = field(default_factory=list)
    diags: list[Diagnostic] = field(default_factory=list)
    css: css.CssIndex = field(default_factory=lambda: _NOCSS)  # selector matching of the slide's css rules

    @property
    def lt(self) -> LayoutTokens:
        return self.theme.layout

    def diag(self, rule: str, message: str, hint: str, level: str = "warning", line: int | None = None):
        self.diags.append(
            Diagnostic(level=level, message=message, slide=self.index + 1, rule=rule, hint=hint, line=line)  # type: ignore[arg-type]
        )

    def emit(self, el, rect: Rect, style: Style, font_scale: float = 1.0) -> Placed:
        p = Placed(
            element=el,
            x=rect.x,
            y=rect.y,
            w=max(rect.w, 0),
            h=max(rect.h, 0),
            style=style,
            font_scale=font_scale,
        )
        self.out.append(p)
        return p


# --------------------------------------------------------------------------- styles


def _label(el) -> str:
    if getattr(el, "id", None):
        return f"#{el.id}"
    if isinstance(el, Container) and el.title:
        return f"box '{_plain(el.title.paragraphs)[:24]}'"
    if isinstance(el, (Text, Shape)):
        return f"{el.type} '{_plain(el.paragraphs)[:24]}'"
    return el.type


def _plain(paragraphs: list[Paragraph]) -> str:
    return " ".join(p.plain for p in paragraphs)


def _role_style(ctx: _Ctx, role: str, cover: bool = False) -> Style:
    t = ctx.theme
    key = (
        "cover-title"
        if cover and role == "title"
        else "cover-subtitle"
        if cover and role == "subtitle"
        else _SIZE_KEY.get(role, "body")
    )
    size = t.sizes.get(key, t.sizes.get("body", DEFAULT_SIZES["body"]))
    if role in ("body", "quote"):
        size *= ctx.dense_k
    heading_font = role in ("title", "heading", "subtitle")
    st = Style(
        font=t.fonts.heading if heading_font else t.fonts.body,
        font_ea=t.fonts.ea,
        font_size=size,
        color="fg",
        align="left",
        valign="top",
    )
    if role == "title":
        st = st.merged(Style(bold=True, color=t.title_color, valign="middle"))
    elif role == "heading":
        st = st.merged(Style(bold=True, color=t.heading_color))
    elif role == "subtitle":
        st = st.merged(Style(color="muted"))
    elif role == "lead":
        st = st.merged(Style(color=t.lead_color))
    elif role == "quote":
        st = st.merged(Style(italic=True, color="muted"))
    elif role in ("footnote", "caption"):
        st = st.merged(Style(color="muted"))
    elif role == "conclusion":
        st = st.merged(
            Style(
                bold=True,
                color=t.conclusion_color,
                fill=t.conclusion_fill,
                align="center",
                valign="middle",
                padding="6pt",
            )
        )
    return st


def _class_styles(ctx: _Ctx, el, skip: tuple[str, ...] = ()) -> list[Style]:
    out: list[Style] = []
    for name in getattr(el, "classes", []):
        if name in skip:
            continue
        if name in ctx.theme.classes:
            out.append(ctx.theme.classes[name])
        elif name in ctx.theme.colors and name not in ("bg", "fg", "surface", "border"):
            if isinstance(el, Container):
                out.append(Style(line=name))
            elif isinstance(el, Shape):
                out.append(Style(fill=name))
            else:
                out.append(Style(color=name))
    return out


def _styled(ctx: _Ctx, el, st: Style, classes: bool = True) -> Style:
    """``st`` (theme role) -> inherited CSS -> theme classes -> CSS rules -> inline style."""
    own = ctx.css.own(el)
    out = st.merged(
        ctx.css.inherited(el), *(_class_styles(ctx, el) if classes else ()), own, getattr(el, "style", None)
    )
    if own.line_width and not out.line:  # `border: 2px` without a color: the border color token
        out = out.merged(Style(line="border"))
    return out


def _cstyle(ctx: _Ctx, el) -> Style:
    """Classes + CSS + inline of ``el`` only (margin, gap, grid, rotation lookups)."""
    return Style().merged(*_class_styles(ctx, el), ctx.css.own(el), getattr(el, "style", None))


def _cgrid(ctx: _Ctx, c) -> str | None:
    """The ``@`` spec of a container: its own, else the CSS ``grid-template-*`` of its rules."""
    if getattr(c, "grid", None):
        return c.grid
    return _cstyle(ctx, c).grid if ctx.css.active else None


def _cgap(ctx: _Ctx, c):
    if getattr(c, "gap", None) is not None:
        return c.gap
    return _cstyle(ctx, c).gap if ctx.css.active else None


def _margin(ctx: _Ctx, el) -> int:
    return css.margin_emu(_cstyle(ctx, el)) if isinstance(el, _MARGIN_TYPES) else 0


_MARGIN_TYPES = (Text, Shape, Container, Table, Code, Chart, Image, Media, Raw)
_CALLOUT_KINDS = ("note", "tip", "warn", "caution")


def _hex(theme: Theme, value: str | None) -> tuple[int, int, int] | None:
    v = theme.color(value) if value else None
    if v and len(v) == 7 and v[0] == "#":
        try:
            return int(v[1:3], 16), int(v[3:5], 16), int(v[5:7], 16)
        except ValueError:
            return None
    return None


def _tint(theme: Theme, color: str | None, amount: float = 0.12) -> str | None:
    """``color`` mixed into the slide background (``amount`` = share of ``color``)."""
    c, bg = _hex(theme, color), _hex(theme, "bg") or (255, 255, 255)
    if c is None:
        return None
    mixed = [round(b + (x - b) * amount) for x, b in zip(c, bg, strict=True)]
    return "#{:02X}{:02X}{:02X}".format(*mixed)


def _tighten(ctx: _Ctx, st: Style) -> Style:
    """Dense slides shrink paddings as well as fonts."""
    if ctx.tight >= 1.0:
        return st
    upd = {}
    for f in ("padding", "padding_top", "padding_right", "padding_bottom", "padding_left"):
        v = getattr(st, f)
        if v is None:
            continue
        try:
            upd[f] = f"{round(to_emu(v) / EMU_PER_PT * ctx.tight, 2)}pt"
        except ValueError:
            continue
    return st.merged(Style(**upd)) if upd else st


def _text_style(ctx: _Ctx, el: Text | Shape, inherit: Style) -> Style:
    role = el.role if isinstance(el, Text) else "shape"
    if role == "shape":
        t = ctx.theme
        st = Style(
            font=t.fonts.body,
            font_ea=t.fonts.ea,
            font_size=t.sizes.get("body", DEFAULT_SIZES["body"]) * ctx.dense_k,
            color="bg",
            fill="primary",
            align="center",
            valign="middle",
            padding="6pt",
        )
    else:
        st = _role_style(ctx, role)
    if role in _INHERIT_ROLES or role == "shape":
        st = st.merged(_only_inheritable(inherit))
    st = _styled(ctx, el, st)
    if (
        isinstance(el, Text)
        and "callout" in el.classes
        and not (el.style and el.style.fill)
        and not ctx.css.own(el).fill
    ):
        kind = next((k for k in _CALLOUT_KINDS if k in el.classes), None)
        if kind and (tint := _tint(ctx.theme, st.line)):
            st = st.merged(Style(fill=tint))
    return _tighten(ctx, st)


def _only_inheritable(s: Style) -> Style:
    d = s.model_dump()
    return Style(**{k: v for k, v in d.items() if k in _INHERIT_FIELDS and v is not None})


def _pad(style: Style, default: float = 0.0) -> int:
    if style.padding is None:
        return round(default)
    try:
        return to_emu(style.padding)
    except ValueError:
        return round(default)


def _len(ctx: _Ctx, value, ref: int, el=None) -> int | None:
    try:
        return to_emu(value, ref)
    except (ValueError, TypeError):
        ctx.diag(
            "bad-length",
            f"invalid length {value!r}",
            "use e.g. 50%, 2in, 36pt, 3cm, 120px",
            line=getattr(el, "line", None),
        )
        return None


# --------------------------------------------------------------------------- geometry helpers


def _is_abs(el) -> bool:
    b: Box | None = getattr(el, "box", None)
    return b is not None and (b.x is not None or b.y is not None)


def _apply_box(ctx: _Ctx, el, rect: Rect, absolute: bool) -> Rect:
    """Resolve ``el.box`` against ``rect`` (the parent area). Non-absolute boxes only resize."""
    b: Box | None = getattr(el, "box", None)
    if b is None:
        return rect
    x, y, w, h = rect.x, rect.y, rect.w, rect.h
    if absolute:
        if b.x is not None and (v := _len(ctx, b.x, rect.w, el)) is not None:
            x = rect.x + v
        if b.y is not None and (v := _len(ctx, b.y, rect.h, el)) is not None:
            y = rect.y + v
        w, h = max(rect.right - x, 0), max(rect.bottom - y, 0)
    if b.w is not None and (v := _len(ctx, b.w, rect.w, el)) is not None:
        w = v
    if b.h is not None and (v := _len(ctx, b.h, rect.h, el)) is not None:
        h = v
    return Rect(x, y, w, h)


def _fit(ctx: _Ctx, need_fn, avail: int, base_size: float) -> float:
    """Smallest-effort local autofit scale for a standalone element (title, lead, ...)."""
    for s in _SCALES:
        eff = measure.effective_scale(base_size, s, ctx.theme.min_font_size)
        if need_fn(eff) <= avail * _TOL:
            return eff
    return measure.effective_scale(base_size, 0.0, ctx.theme.min_font_size)


# --------------------------------------------------------------------------- element placement


def _grown(ctx: _Ctx, el, eff: float) -> float:
    """Autofit scale ``eff`` times the sparse-grid growth for body text inside boxes.

    A CSS ``font-size`` is explicit: it is never grown (autofit may still shrink it)."""
    if ctx.css.active and ctx.css.own(el).font_size is not None:
        return eff
    if ctx.grow > 1.0 and (ctx.depth > 0 or ctx.text_only) and ctx.scale >= 1.0 and isinstance(el, Text):
        if el.role == "body" and "callout" not in el.classes:
            ctx.grew = True
            return eff * ctx.grow
    elif (
        ctx.grow > 1.0
        and ctx.depth == 0
        and ctx.scale >= 1.0
        and isinstance(el, Text)
        and el.role == "body"
        and "callout" not in el.classes
        and _has_box_text(ctx)
    ):  # slide-level text beside grown boxes: at most one step smaller than their body text
        base = max(_text_style(ctx, el, Style()).font_size or 18, 1.0)
        box_pt = ctx.theme.sizes.get("body", DEFAULT_SIZES["body"]) * ctx.dense_k * ctx.grow
        f = min(max(box_pt / ctx.lt.slide_peer_step / base, 1.0), ctx.grow)
        if f > 1.0:
            ctx.grew = True
            return eff * f
    return eff


def _text_need(ctx: _Ctx, el: Text | Shape, style: Style, width: int, scale: float) -> float:
    ph, pv = css.inset_hv(style)
    gap = ctx.gaps.get(id(el))
    return measure.paragraphs_height(el.paragraphs, width - ph, style, scale, gap=gap) + pv


def _natural_height(ctx: _Ctx, el, width: int, inherit: Style) -> int | None:
    """Natural height for stackable elements, ``None`` for flexible ones (CSS margin included)."""
    m = _margin(ctx, el)
    if not m:
        return _natural_height0(ctx, el, width, inherit)
    h = _natural_height0(ctx, el, max(width - 2 * m, 1), inherit)
    return None if h is None else h + 2 * m


def _natural_height0(ctx: _Ctx, el, width: int, inherit: Style) -> int | None:
    if isinstance(el, Text):
        st = _text_style(ctx, el, inherit)
        eff = _grown(ctx, el, measure.effective_scale(st.font_size or 18, ctx.scale, ctx.theme.min_font_size))
        return round(_text_need(ctx, el, st, width, eff))
    if isinstance(el, Code):
        st = _code_style(ctx, el)
        eff = _code_eff(ctx, st)
        ph, pv = css.inset_hv(st)
        return round(measure.code_height(el.text, width - ph, (st.font_size or 14) * eff) + pv)
    if isinstance(el, Table):
        _, _, _, _, rh = _table_geom(ctx, el, width)
        return sum(rh)
    return None


def _code_eff(ctx: _Ctx, st: Style) -> float:
    """Code font scale: the autofit scale, times the sparse-slide growth (at most ``CODE_GROW``)."""
    eff = measure.effective_scale(st.font_size or 14, ctx.scale, ctx.theme.min_font_size)
    if ctx.grow > 1.0 and ctx.scale >= 1.0:
        ctx.grew = True
        eff *= min(ctx.grow, ctx.lt.code_grow)
    return eff


def _code_style(ctx: _Ctx, el: Code) -> Style:
    t = ctx.theme
    st = Style(
        font=t.fonts.mono,
        font_ea=t.fonts.ea,
        font_size=t.sizes.get("code", DEFAULT_SIZES["code"]) * ctx.dense_k,
        color="fg",
        fill="surface",
        padding="8pt",
        valign="top",
        align="left",
    )
    return _tighten(ctx, _styled(ctx, el, st))


def _table_style(ctx: _Ctx, el: Table) -> Style:
    t = ctx.theme
    st = Style(
        font=t.fonts.body,
        font_ea=t.fonts.ea,
        font_size=t.sizes.get("table", DEFAULT_SIZES["table"]) * ctx.dense_k,
        color="fg",
        align="left",
        valign="middle",
    )
    return _styled(ctx, el, st)


def _table_grow(ctx: _Ctx) -> float:
    return ctx.lt.table_grow_roomy if ctx.roomy else ctx.lt.table_grow


def _has_box_text(ctx: _Ctx) -> bool:
    """The slide holds a box with body text (it grows with the sparse-slide growth)."""
    if "chevron" in (_slide_grid(ctx) or "") or "chevron" in ctx.slide.classes:  # chevron text: own size
        return False
    return any(
        isinstance(e, Container)
        and not {"kpi", "chevron", "diagram"} & set(e.classes)
        and "chevron" not in (_cgrid(ctx, e) or "")
        and any(isinstance(ch, Text) and ch.role == "body" for ch in e.children)
        for e in ctx.slide.elements
    )


def _slide_grid(ctx: _Ctx) -> str | None:
    if ctx.slide.grid:
        return ctx.slide.grid
    return ctx.css.own(ctx.slide).grid if ctx.css.active else None


def _table_geom(ctx: _Ctx, el: Table, width: int):
    el = ctx.css.table(el)
    st = _table_style(ctx, el)
    eff = measure.effective_scale(st.font_size or 14, ctx.scale, ctx.theme.min_font_size)
    if (
        ctx.grow > 1.0 and ctx.scale >= 1.0 and not (ctx.css.active and ctx.css.own(el).font_size is not None)
    ):  # sparse slide: table text grows too (less than box text)
        t = min(ctx.grow, ctx.lt.table_font_grow)
        if _has_box_text(ctx):  # ... but stays within one step of the box text on the same slide
            body = ctx.theme.sizes.get("body", DEFAULT_SIZES["body"]) * ctx.dense_k * ctx.grow
            want = body / ctx.lt.peer_step / max(st.font_size or 14, 1) / max(eff, 1e-6)
            t = max(t, min(want, ctx.grow * 1.1))
        eff *= t
        ctx.grew = True
    nrows, ncols, anchors = table_grid(el)
    size = (st.font_size or 14) * eff
    b = getattr(el, "box", None)
    if (
        ctx.depth == 0
        and ctx.cap_tables
        and width > ctx.lt.full_width * ctx.W
        and not (b is not None and b.w is not None)
    ):
        width = capped_width(el, ncols, anchors, width, size)  # a few short columns: numbers stay near labels
    cw = column_widths(el, ncols, anchors, width, size)
    rh = row_heights(el, anchors, cw, st, eff)
    return st, eff, anchors, cw, rh


def _place_block(ctx: _Ctx, el, rect: Rect, inherit: Style) -> None:
    if rect.w <= 0 or rect.h <= 0:
        return
    if m := _margin(ctx, el):  # CSS margin: the element shrinks inside its cell
        rect = rect.inset(m)
        if rect.w <= 0 or rect.h <= 0:
            return
    if isinstance(el, (Text, Shape)):
        st = _text_style(ctx, el, inherit)
        eff = _grown(ctx, el, measure.effective_scale(st.font_size or 18, ctx.scale, ctx.theme.min_font_size))
        need = _text_need(ctx, el, st, rect.w, eff)
        if need > rect.h * _TOL:
            ctx.over.append(_label(el))
        elif ctx.roomy and ctx.grow > ctx.grow_base >= 1.0 and eff > 0:
            small = (
                eff * ctx.grow_base / ctx.grow
            )  # growing must not add wrapped lines (orphan CJK characters)
            if need > _text_need(ctx, el, st, rect.w, small) * (ctx.grow / ctx.grow_base) * 1.04:
                ctx.over.append(_label(el))
        if isinstance(el, Text) and "callout" in el.classes:
            rect = Rect(rect.x, rect.y, rect.w, min(rect.h, round(need)))  # callouts never stretch
        orig = id(el)
        if (pg := ctx.gaps.get(orig)) is not None:  # spread paragraphs: the renderer writes spcBef
            el = el.model_copy(update={"attrs": {**el.attrs, "para_gap": pg}})
        ctx.emit(el, rect, st, eff)
        ctx.text_out[orig] = len(ctx.out) - 1
    elif isinstance(el, Code):
        st = _code_style(ctx, el)
        eff = _code_eff(ctx, st)
        ph, pv = css.inset_hv(st)
        need = measure.code_height(el.text, rect.w - ph, (st.font_size or 14) * eff) + pv
        if need > rect.h * _TOL:
            ctx.over.append(_label(el))
        ctx.emit(el, Rect(rect.x, rect.y, rect.w, min(round(need), rect.h)), st, eff)
    elif isinstance(el, Table):
        el = ctx.css.table(el)
        st, eff, _anchors, cw, rh = _table_geom(ctx, el, rect.w)
        if not rh or not cw:  # an empty table places nothing
            return
        total = sum(rh)
        if total > rect.h * _TOL:
            ctx.over.append(_label(el))
        elif rect.h > total:  # spare room: rows grow up to ctx.lt.table_grow, cell text stays centered
            target = min(rect.h, round(total * _table_grow(ctx)))
            rh = [round(h * target / total) for h in rh]
            rh[-1] += target - sum(rh)
            total = sum(rh)
        attrs = {**el.attrs, "_col_w": cw, "_row_h": rh}
        ctx.emit(
            right_align_numbers(el).model_copy(update={"attrs": attrs}),
            Rect(rect.x, rect.y, min(rect.w, sum(cw)), min(total, rect.h) if total > rect.h else total),
            st,
            eff,
        )
    elif isinstance(el, Chart):
        t = ctx.theme
        st = Style(
            font=t.fonts.body,
            font_ea=t.fonts.ea,
            font_size=t.sizes.get("table", DEFAULT_SIZES["table"]),
            color="fg",
        )
        ctx.emit(el, rect, _styled(ctx, el, st, classes=False))
    elif isinstance(el, (Image, Media)):
        ctx.emit(el, rect, _styled(ctx, el, Style()))
    elif isinstance(el, Raw):
        t = ctx.theme
        st = Style(
            font=t.fonts.body,
            font_size=t.sizes.get("caption", DEFAULT_SIZES["caption"]),
            color="muted",
            fill="surface",
            line="border",
            align="center",
            valign="middle",
        )
        st = _styled(ctx, el, st, classes=False)
        fs = 1.0
        if el.kind == "math" and ctx.depth == 0:
            fs = _math_scale(
                ctx, el, rect
            )  # alone in its cell: the equation grows (the renderer scales the body size)
        ctx.emit(el, rect, st, fs)
    elif isinstance(el, Container):
        _place_container(ctx, el, rect, inherit)


def _math_scale(ctx: _Ctx, el: Raw, rect: Rect) -> float:
    """Font scale of an equation alone in a cell: ``MATH_GROW`` x body, less when it would not fit."""
    body = ctx.theme.sizes.get("body", DEFAULT_SIZES["body"]) * ctx.dense_k
    size = body * ctx.lt.math_grow * ctx.scale
    flat = re.sub(r"\\[A-Za-z]+|[{}\s]", "", el.source)
    lines = max(el.source.count("\\\\") + 1, 1)
    width = max(len(flat) / lines, 1) * 0.6  # em, rough
    size = min(size, rect.w / EMU_PER_PT * 0.9 / width, rect.h / EMU_PER_PT * 0.8 / (1.6 * lines))
    return max(size, body * ctx.scale * 0.6) / ctx.theme.sizes.get(
        "body", 18
    )  # the renderer divides by the theme body


def _card_style(ctx: _Ctx, c: Container) -> Style:
    if "plain" in c.classes:
        base = Style(padding="0pt")
    else:
        base = ctx.theme.classes.get("card", Style(padding=ctx.lt.box_pad))
    others = _class_styles(ctx, c, skip=("plain", "kpi"))
    own = ctx.css.own(c)
    st = Style().merged(ctx.css.inherited(c), base, *others, own, c.style)
    if own.line_width and not st.line:
        st = st.merged(Style(line="border"))
    return _tighten(ctx, st)


def _cpads(ctx: _Ctx, c: Container) -> tuple[Style, int, tuple[int, int, int, int]]:
    """(card style, scalar padding, (left, top, right, bottom) insets) of a box."""
    style = _card_style(ctx, c)
    dflt = _emu(ctx.lt.box_pad) * ctx.tight
    return style, _pad(style, dflt), css.insets(style, dflt)


def _heading_parts(ctx: _Ctx, c: Container, pad: int, kpi: bool):
    """(heading element, merged style, autofit scale, band fill) of a box, or ``None`` without a heading."""
    if c.title is None or not c.title.paragraphs:
        return None
    band = None if kpi else ctx.theme.heading_band
    h_el = c.title if c.title.role == "heading" else c.title.model_copy(update={"role": "heading"})
    hst = _text_style(ctx, h_el, Style())
    if kpi:
        body_size = ctx.theme.sizes.get("body", DEFAULT_SIZES["body"]) * ctx.dense_k
        hst = hst.merged(Style(align="center", color="muted", bold=False, font_size=body_size))
    if band:
        hst = hst.merged(
            Style(
                fill=band,
                color=ctx.theme.heading_band_color,
                bold=True,
                valign="middle",
                padding=f"{round(pad / EMU_PER_PT, 2)}pt",
            )
        )
    eff = measure.effective_scale(hst.font_size or 18, ctx.scale, ctx.theme.min_font_size)
    if ctx.head_grow and ctx.grow > 1.0 and ctx.scale >= 1.0 and not kpi:
        eff *= min(ctx.grow, ctx.lt.grow_head)
    if ctx.grow > 1.0 and ctx.scale >= 1.0 and not kpi and (body := _box_body_pt(ctx, c)):
        size = max(hst.font_size or 18, 1.0)
        if size * eff < body * HEAD_TOL:  # never smaller than its own body
            eff = body * ctx.lt.head_body / size
    return h_el, hst, eff, band


def _box_body_pt(ctx: _Ctx, c: Container) -> float:
    """Largest body text size (pt) inside box ``c`` after the sparse-slide growth; 0 without body text."""
    best = 0.0
    for ch in c.children:
        if isinstance(ch, Text) and ch.role == "body" and "callout" not in ch.classes:
            st = _text_style(ctx, ch, Style())
            size = st.font_size or 18
            best = max(
                best, size * measure.effective_scale(size, ctx.scale, ctx.theme.min_font_size) * ctx.grow
            )
    return best


def _head_metrics(
    ctx: _Ctx, c: Container, rect_w: int, pad: int, kpi: bool, row: bool = True, hpad: int | None = None
):
    """(parts, icon side, text shift, heading height) of a box ``rect_w`` wide, or ``None`` without heading.

    The height is the heading band (or the plain heading text); with ``row`` it is raised to the tallest
    heading among the boxes of the same row (``ctx.band_h``) so that bands and bodies line up.
    """
    parts = _heading_parts(ctx, c, pad, kpi)
    if parts is None:
        return None
    h_el, hst, eff, band = parts
    icon = _icon_name(c)
    isz, shift = _icon_side(ctx, hst, eff, kpi) if icon else (0, 0)
    if icon and kpi:
        isz = min(isz, max(rect_w - 2 * pad, 1))
        shift = 0
    if icon and band:
        shift = pad + isz  # the text's own padding supplies the gap after the icon
    if band:
        hh = round(_text_need(ctx, h_el, hst, rect_w - shift, eff))
        if icon:
            hh = max(hh, isz + 2 * pad)
    else:
        hh = round(_text_need(ctx, h_el, hst, rect_w - (2 * pad if hpad is None else hpad) - shift, eff))
        if icon and not kpi:
            hh = max(hh, isz)
    if row:
        hh = max(hh, ctx.band_h.get((id(c), rect_w), 0))
    return parts, isz, shift, hh


def _equalize_heads(ctx: _Ctx, boxes: list[tuple[Container, int, int]]) -> None:
    """Boxes of one row share the tallest heading height: ``boxes`` are (box, width, row key)."""
    rows: dict[int, list[tuple[Container, int, int]]] = {}
    for c, w, key in boxes:
        if isinstance(c, Container) and "kpi" not in c.classes and c.title is not None:
            _st, pad, (pl, _pt, pr, _pb) = _cpads(ctx, c)
            m = _head_metrics(ctx, c, w, pad, False, row=False, hpad=pl + pr)
            if m is not None:
                rows.setdefault(key, []).append((c, w, m[3]))
    for items in rows.values():
        top = max(h for _, _, h in items)
        for c, w, _ in items:
            ctx.band_h[(id(c), w)] = top


def _icon_name(el) -> str | None:
    """The valid icon name of ``icon=name`` on a box / chevron (unknown names are ignored here)."""
    name = getattr(el, "attrs", {}).get("icon")
    name = str(name).strip().lower() if name else ""
    return name if name and icons.path(name) else None


def _icon_item(name: str) -> Shape:
    return Shape(shape="icon", attrs={"icon": name})


def _icon_side(ctx: _Ctx, hst: Style, eff: float, kpi: bool) -> tuple[int, int]:
    """(icon side, space the icon takes left of the heading text) in EMU."""
    side = round((ctx.lt.icon_kpi if kpi else ctx.lt.icon_head) * (hst.font_size or 18) * eff * EMU_PER_PT)
    return side, side + round(ctx.lt.icon_gap * side)


def _inset4(rect: Rect, pl: int, pt: int, pr: int, pb: int) -> Rect:
    """``rect`` shrunk by per-side insets (never below zero size)."""
    w, h = max(rect.w - pl - pr, 0), max(rect.h - pt - pb, 0)
    return Rect(rect.x + min(pl, rect.w // 2), rect.y + min(pt, rect.h // 2), w, h)


def _place_container(ctx: _Ctx, c: Container, rect: Rect, inherit: Style) -> None:
    """Place a box and its children; CSS ``rotate()`` turns the whole subtree about the box center."""
    start = len(ctx.out)
    _place_container0(ctx, c, rect, inherit)
    deg = _cstyle(ctx, c).rotation if ctx.css.active else None
    if deg and len(ctx.out) > start:
        subtree = ctx.out[start + 1 :]  # the card (first item) already carries the rotation in its style
        if not css.rotate_placed(subtree, rect.x + rect.w / 2, rect.y + rect.h / 2, deg):
            ctx.diag(
                "css-unsupported",
                "rotate() on a box with connectors: the connectors are not rotated",
                "rotate boxes without a>b links, or remove the transform",
            )


def _place_container0(ctx: _Ctx, c: Container, rect: Rect, inherit: Style) -> None:
    style, pad, (pl, pt, pr, pb) = _cpads(ctx, c)
    if "diagram" in c.classes and c.title is None:
        from .diagram import place_diagram  # flowcharts size and route their own nodes

        if place_diagram(ctx, c, _inset4(rect, pl, pt, pr, pb), inherit.merged(_only_inheritable(style))):
            return
    ctx.emit(c, rect, style)
    inner = _inset4(rect, pl, pt, pr, pb)
    y = inner.y
    child_inherit = inherit.merged(_only_inheritable(style))
    kpi = "kpi" in c.classes
    if metrics := _head_metrics(ctx, c, rect.w, pad, kpi, hpad=pl + pr):
        (h_el, hst, eff, band), isz, shift, hh = metrics
        icon = _icon_name(c)
        if icon and kpi:  # icon centered above the label and the number
            ctx.emit(
                _icon_item(icon), Rect(inner.x + (inner.w - isz) // 2, y, isz, isz), Style(fill="primary")
            )
            y += isz + round(pad * 0.4)
        if band:
            if hh > rect.h * _TOL:
                ctx.over.append(_label(c))
            band_rect = Rect(rect.x, rect.y, rect.w, min(hh, rect.h))
            if icon:  # the band is a plain shape behind the icon and the shifted heading text
                ctx.emit(Shape(shape="rect"), band_rect, Style(fill=band))
                ctx.emit(
                    _icon_item(icon),
                    Rect(rect.x + pad, rect.y + (band_rect.h - isz) // 2, isz, isz),
                    Style(fill=hst.color),
                )
                text_rect = Rect(rect.x + shift, rect.y, rect.w - shift, band_rect.h)
                ctx.emit(h_el, text_rect, hst.model_copy(update={"fill": None}), eff)
            else:
                ctx.emit(h_el, band_rect, hst, eff)
            y = band_rect.bottom + round(pad * 0.5)
        else:
            if icon and not kpi:
                ctx.emit(_icon_item(icon), Rect(inner.x, y, isz, isz), Style(fill=hst.color or "primary"))
            if hh > inner.h * _TOL:
                ctx.over.append(_label(c))
            ctx.emit(h_el, Rect(inner.x + shift, y, inner.w - shift, min(hh, inner.h)), hst, eff)
            y += hh + round(pad * 0.5)
    area = Rect(inner.x, y, inner.w, max(inner.bottom - y, 0))
    if not c.children:
        return
    gap = _gap(ctx, _cgap(ctx, c), inner.w, small=True)
    children = c.children
    grid = _cgrid(ctx, c)
    if kpi:
        children = _kpi_children(ctx, children, area.w)
    saved = (ctx.depth, ctx.grow)
    ctx.depth += 1
    if kpi:
        ctx.grow = 1.0
    try:
        if grid or any(n in ("flow", "chevron") for n in c.classes):
            _place_blocks(ctx, children, area, child_inherit, grid, c.classes, gap, c, c.links)
        else:
            rects = _place_stack(
                ctx, children, area, child_inherit, gap, c, center=kpi and len(children) == 1
            )
            _emit_links(ctx, c.links, rects)
    finally:
        ctx.depth, ctx.grow = saved
    if not kpi:
        ids = [id(ch) for ch in children if _spreadable(ch) and id(ch) in ctx.text_out]
        if ids:
            ctx.boxes[id(c)] = ids


def _box_nat(ctx: _Ctx, c: Container, width: int, inherit: Style) -> int | None:
    """Natural height of a ``##`` box (heading, children, padding, CSS margin); ``None`` if flexible."""
    m = _margin(ctx, c)
    if not m:
        return _box_nat0(ctx, c, width, inherit)
    h = _box_nat0(ctx, c, max(width - 2 * m, 1), inherit)
    return None if h is None else h + 2 * m


def _box_nat0(ctx: _Ctx, c: Container, width: int, inherit: Style) -> int | None:
    if _cgrid(ctx, c) or c.links or any(n in ("flow", "chevron") for n in c.classes):
        return None
    style, pad, (pl, pt, pr, pb) = _cpads(ctx, c)
    kpi = "kpi" in c.classes
    total = pt + pb if c.children or c.title else 0
    if metrics := _head_metrics(ctx, c, width, pad, kpi, hpad=pl + pr):
        (_h_el, _hst, _eff, band), isz, _shift, hh = metrics
        if kpi and _icon_name(c):
            total += isz + round(pad * 0.4)
        if band:
            total = hh + round(pad * 0.5) + pb
        else:
            total += hh + round(pad * 0.5)
    children = c.children
    if not children:
        return total
    if any(_is_abs(ch) for ch in children):
        return None
    inner_w = max(width - pl - pr, 1)
    if kpi:
        children = _kpi_children(ctx, children, inner_w)
    saved = (ctx.depth, ctx.grow)
    ctx.depth += 1
    if kpi:
        ctx.grow = 1.0
    try:
        child_inherit = inherit.merged(_only_inheritable(style))
        nat = [_natural_height(ctx, ch, inner_w, child_inherit) for ch in children]
    finally:
        ctx.depth, ctx.grow = saved
    if any(n is None for n in nat):
        return None
    return total + sum(nat) + _gap(ctx, _cgap(ctx, c), inner_w, small=True) * (len(nat) - 1)


def _kpi_children(ctx: _Ctx, children: list, width: int) -> list:
    """The first text child of a ``.kpi`` box: paragraph 0 = big number, the rest = muted caption."""
    i = next((k for k, c in enumerate(children) if isinstance(c, Text) and c.paragraphs), None)
    if i is None:
        return children
    ch = children[i]
    th = ctx.theme
    big = th.classes.get("kpi") or _base_classes()["kpi"]
    cap = Style(
        font_size=th.sizes.get("caption", DEFAULT_SIZES["caption"]), color="muted", align="center", bold=False
    )
    paras: list[Paragraph] = []
    for j, p in enumerate(ch.paragraphs):
        if j == 0:
            st = big
            size = big.font_size or 36
            em = measure.text_em(p.plain, bold=True)
            avail = width / EMU_PER_PT * 0.72  # headroom: fallback fonts are wider than the estimate
            if em * size > avail:  # one line: shrink the number to the card width
                st = st.merged(Style(font_size=max(round(avail / em, 1), 10)))
        else:
            st = cap
        paras.append(p.model_copy(update={"style": st.merged(p.style)}))
    new = ch.model_copy(
        update={"paragraphs": paras, "style": Style(align="center", valign="middle").merged(ch.style)}
    )
    return children[:i] + [new] + children[i + 1 :]


def _gap(ctx: _Ctx, value, ref: int, small: bool = False) -> int:
    if value is not None:
        v = _len(ctx, value, ref)
        if v is not None:
            return v
    g = to_emu(ctx.theme.gap) * ctx.tight
    return round(g * 0.5) if small else round(g)


def _spreadable(ch) -> bool:
    """A body text with several paragraphs: the only text whose paragraph spacing the layout varies."""
    return (
        isinstance(ch, Text) and ch.role == "body" and "callout" not in ch.classes and len(ch.paragraphs) > 1
    )


def _share_gaps(ctx: _Ctx, boxes: list) -> None:
    """Sibling boxes (one grid row / stacked column) share ONE paragraph gap: the smallest any of them got.

    A sibling without a multi-paragraph body text does not take part. Lowering a gap only shrinks text.
    """
    members = [ids for b in boxes if isinstance(b, Container) and (ids := ctx.boxes.get(id(b)))]
    if len(members) < 2:
        return
    floor = min(ctx.gaps.get(i, measure.para_gap()) for ids in members for i in ids)
    for ids in members:
        for i in ids:
            if ctx.gaps.get(i, measure.para_gap()) <= floor + 1e-9:
                continue
            p = ctx.out[ctx.text_out[i]]
            attrs = {k: v for k, v in p.element.attrs.items() if k != "para_gap"}
            if floor > measure.para_gap() + 1e-9:
                attrs["para_gap"] = floor
                ctx.gaps[i] = floor
            else:
                ctx.gaps.pop(i, None)
            p.element = p.element.model_copy(update={"attrs": attrs})


def _roomy_paragraphs(ctx: _Ctx, flow: list, nat: list, area: Rect, inherit: Style, owner, gap: int) -> None:
    """A card with plenty of free height spreads its paragraphs (space-before up to about half a line).

    Only inside boxes, not on shrunk (dense full) slides, and only when more than ``ROOM_FREE`` of the inner
    height stays free. Sets ``ctx.gaps`` (read by ``_text_need`` and written by the renderer as ``spcBef``)
    and updates the natural heights in ``nat``.
    """
    if ctx.depth == 0 or ctx.scale < 1.0 or not isinstance(owner, Container) or "kpi" in owner.classes:
        return
    fixed = sum(n or 0 for n in nat) + gap * (len(flow) - 1)
    free = area.h - fixed
    if area.h <= 0 or free <= ctx.lt.room_free * area.h:
        return
    cands: list[tuple[int, Text, float]] = []  # (index, text, sum of font sizes over its paragraph gaps)
    for k, (_i, ch) in enumerate(flow):
        if (
            isinstance(ch, Text)
            and ch.role == "body"
            and "callout" not in ch.classes
            and len(ch.paragraphs) > 1
        ):
            st = _text_style(ctx, ch, inherit)
            size = (st.font_size or 18) * _grown(
                ctx, ch, measure.effective_scale(st.font_size or 18, ctx.scale, ctx.theme.min_font_size)
            )
            cands.append((k, ch, size * (len(ch.paragraphs) - 1)))
    slots = sum(c[2] for c in cands)
    if not slots:
        return
    gmax = ctx.lt.room_gap_max_dense if ctx.dense_k < 1.0 else ctx.lt.room_gap_max
    g = min(gmax, measure.para_gap() + free * ctx.lt.room_use / EMU_PER_PT / slots)
    while g > measure.para_gap() + 0.02:
        for k, ch, _ in cands:
            ctx.gaps[id(ch)] = g
            nat[k] = round(_natural_height(ctx, ch, area.w, inherit) or 0)
        if sum(n or 0 for n in nat) + gap * (len(flow) - 1) <= area.h * (1 - ctx.lt.room_free * 0.5):
            return
        g -= 0.05
    for k, ch, _ in cands:  # no room for more than the default gap after all
        ctx.gaps.pop(id(ch), None)
        nat[k] = round(_natural_height(ctx, ch, area.w, inherit) or 0)


def _place_stack(
    ctx: _Ctx, children: list, area: Rect, inherit: Style, gap: int, owner, *, center: bool = False
) -> dict[int, Rect]:
    """Stack blocks full width, one per row. Returns the rect of every child by index."""
    rects: dict[int, Rect] = {}
    for i, ch in enumerate(children):
        if _is_abs(ch):
            rects[i] = _apply_box(ctx, ch, area, True)
            _place_block(ctx, ch, rects[i], inherit)
    flow = [(i, ch) for i, ch in enumerate(children) if not _is_abs(ch)]
    if not flow:
        return rects
    nat = [_natural_height(ctx, ch, area.w, inherit) for _, ch in flow]
    fixed = sum(n for n in nat if n is not None) + gap * (len(flow) - 1)
    nflex = sum(1 for n in nat if n is None)
    flex_h = 0
    if nflex:
        flex_h = max((area.h - fixed) // nflex, int(0.8 * EMU_PER_INCH))
    elif center and len(flow) == 1:
        nat = [max(nat[0] or 0, area.h)]  # a lone block fills the area (its text is centered by its style)
    else:  # spare room goes to tables (up to table_grow), everything else stays natural and on top
        tabs = [k for k, (_i, ch) in enumerate(flow) if isinstance(ch, Table)]
        spare = area.h - fixed
        if tabs and spare > 0:
            share = spare / len(tabs)
            for k in tabs:
                nat[k] = round((nat[k] or 0) + min(share, (nat[k] or 0) * (_table_grow(ctx) - 1)))
        elif not tabs:
            _roomy_paragraphs(ctx, flow, nat, area, inherit, owner, gap)
    y = area.y
    used = 0
    for (i, ch), n in zip(flow, nat, strict=True):
        h = n if n is not None else flex_h
        r = _apply_box(ctx, ch, Rect(area.x, y, area.w, h), False)
        rects[i] = r
        _place_block(ctx, ch, r, inherit)
        y += h + gap
        used += h + gap
    used -= gap
    _share_gaps(ctx, [ch for _, ch in flow])
    limit = (
        ctx.lt.grow_box_fill if ctx.grow > 1.0 and ctx.depth > 0 else _TOL
    )  # grown text keeps some headroom
    if used > area.h * limit:
        ctx.over.append(_label(owner) if owner is not None else "content")
    return rects


def _chevron_shape(blk) -> Shape:
    """A chevron carries centered lines: list markers would hang off centered text, so they are dropped."""
    shape = _chevron_shape_raw(blk)
    plain = [p.model_copy(update={"marker": None, "level": 0}) if p.marker else p for p in shape.paragraphs]
    return shape.model_copy(update={"paragraphs": plain})


def _chevron_shape_raw(blk) -> Shape:
    paras: list[Paragraph] = []
    if isinstance(blk, Container):
        if blk.title is not None:
            for p in blk.title.paragraphs:
                paras.append(
                    p.model_copy(update={"runs": [r.model_copy(update={"bold": True}) for r in p.runs]})
                )
        for ch in blk.children:
            if isinstance(ch, (Text, Shape)):
                paras += ch.paragraphs
    elif isinstance(blk, (Text, Shape)):
        paras = list(blk.paragraphs)
    return Shape(
        shape="chevron",
        paragraphs=paras,
        attrs={"_css_src": id(blk)},  # css matching: this shape is the box ``blk``
        id=getattr(blk, "id", None),
        classes=[c for c in blk.classes if c not in ("card", "plain")],
        style=getattr(blk, "style", None),
        line=getattr(blk, "line", None),
    )


def _weight(b) -> int:
    """Text length of a block (visuals count as huge)."""
    if isinstance(b, Text):
        return len(_plain(b.paragraphs))
    if isinstance(b, Container):
        return sum(_weight(c) for c in b.children) + (len(_plain(b.title.paragraphs)) if b.title else 0)
    return 10_000


def _has_visual(b) -> bool:
    if isinstance(b, (Chart, Table, Image, Media)):
        return True
    return isinstance(b, Container) and any(_has_visual(c) for c in b.children)


def _auto_plan(flow: list, gs: GridSpec | None, classes: list[str], links: list[Link]):
    """Arrangement without a grid token (docs/SYNTAX.md): returns (spec or None, flow, tail blocks).

    1. a run of >= 2 boxes followed only by non-box blocks = the boxes in one row (<= 5, else two rows) and
       the rest full width below (``tail``); ``flow`` / ``chevron`` take one column per box;
    2. slide links forming a tree = layered areas; 3. three boxes, the first with a visual or >= 2x the text
       of each other box = ``aab/aac``.
    """
    flags = set(gs.flags) if gs else set()
    errors = list(gs.errors) if gs else []
    k = 0
    while k < len(flow) and isinstance(flow[k][1], Container):
        k += 1
    tail: list[tuple[int, object]] = []
    if k >= 2 and k < len(flow) and all(not isinstance(b, Container) for _, b in flow[k:]):
        tail, flow = flow[k:], flow[:k]
    n = len(flow)

    def spec(cols: int, rows: int, cap: int | None) -> GridSpec:
        return GridSpec([1.0] * cols, [1.0] * rows, flags=flags, errors=errors, capacity=cap)

    if flags:
        if n < 2:
            return gs, flow, tail
        cols = n if n <= 6 else math.ceil(n / 2)
        return spec(cols, math.ceil(n / cols), n), flow, tail
    if n == 3 and all(isinstance(b, Container) and "kpi" not in b.classes for _, b in flow):
        w = [_weight(b) for _, b in flow]
        if _has_visual(flow[0][1]) or w[0] >= 2 * max(w[1], w[2]):
            return parse_spec("aab/aac", n, classes), flow, tail
    ids = [i for i, _ in flow]
    if links and (areas := tree_areas(ids, [(ln.src, ln.dst) for ln in links])):
        return parse_spec(areas, n, classes), flow, tail
    if tail:
        cols = n if n <= 5 else math.ceil(n / 2)
        return spec(cols, math.ceil(n / cols), n), flow, tail
    return gs, flow, tail


def _block_kind_hint(blocks: list) -> tuple[bool, bool]:
    """(text_visual, short) hints for the automatic arrangement."""
    text_visual = (
        len(blocks) == 2
        and sum(isinstance(b, Text) for b in blocks) == 1
        and sum(isinstance(b, _VISUALS) for b in blocks) == 1
    )

    def size(b) -> float:
        if isinstance(b, Text):
            return measure.text_em(_plain(b.paragraphs))
        if isinstance(b, Container):
            return sum(size(c) for c in b.children) + (
                measure.text_em(_plain(b.title.paragraphs)) if b.title else 0
            )
        return 10_000

    return text_visual, all(size(b) <= SHORT_EM for b in blocks)


def _cx(r: Rect) -> int:
    return r.x + r.w // 2


def _cy(r: Rect) -> int:
    return r.y + r.h // 2


def _hits(p0: tuple[int, int], p1: tuple[int, int], r: Rect) -> bool:
    """True when the axis-aligned segment p0-p1 passes through the interior of ``r``."""
    x0, x1 = sorted((p0[0], p1[0]))
    y0, y1 = sorted((p0[1], p1[1]))
    return x1 > r.x and x0 < r.right and y1 > r.y and y0 < r.bottom


def _bus(lo: int, hi: int, spans: list[tuple[int, int]], crosses) -> float:
    """Position (as a fraction of lo..hi) of the middle segment of an elbow that avoids every obstacle.

    ``spans`` are the free channels between obstacles (lo/hi coordinates along the main axis); ``crosses(c)``
    tells whether a bus at coordinate ``c`` touches a third box. Falls back to the middle of lo..hi.
    """
    mid = (lo + hi) / 2
    cands = [mid] + sorted(
        ((a + b) / 2 for a, b in spans if lo < (a + b) / 2 < hi), key=lambda c: abs(c - mid)
    )
    for c in cands:
        if not crosses(c):
            return (c - lo) / (hi - lo) if hi != lo else 0.5
    return 0.5


def _channels(rects: list[Rect], axis: str, lo: int, hi: int) -> list[tuple[int, int]]:
    """Free intervals along ``axis`` ("y" or "x") between the obstacle rects, clipped to lo..hi."""
    iv = sorted((r.y, r.bottom) if axis == "y" else (r.x, r.right) for r in rects)
    out: list[tuple[int, int]] = []
    cur = lo
    for a, b in iv:
        if a > cur:
            out.append((cur, min(a, hi)))
        cur = max(cur, b)
    if cur < hi:
        out.append((cur, hi))
    return [(a, b) for a, b in out if b > a]


def _emit_links(ctx: _Ctx, links: list[Link], rects: dict[int, Rect]) -> None:
    """Connectors between block rects, emitted after the blocks so they sit on top.

    Routing by relative position: a destination clearly below (or above) the source is reached from the
    bottom-middle (top-middle) to the top-middle (bottom-middle); side by side blocks connect right-middle to
    left-middle. Offset ends get an elbow (``bentConnector3``) whose middle segment runs in a free channel.
    """
    tol = round(0.03 * EMU_PER_INCH)
    for ln in links:
        a, b = rects.get(ln.src), rects.get(ln.dst)
        if a is None or b is None or ln.src == ln.dst:
            ctx.diag(
                "link",
                f"connector {ln.src}>{ln.dst} refers to a block that does not exist",
                "use block letters/numbers that exist in this grid, e.g. @abc a>b>c",
            )
            continue
        others = [r for k, r in rects.items() if k not in (ln.src, ln.dst)]
        route, adj = "", 0.5
        if b.y >= a.bottom or a.y >= b.bottom:  # clearly below / above: vertical route
            down = b.y >= a.bottom
            p0 = (_cx(a), a.bottom if down else a.y)
            p1 = (_cx(b), b.y if down else b.bottom)
            route = "v"
            if abs(p1[0] - p0[0]) > tol:
                lo, hi = min(p0[1], p1[1]), max(p0[1], p1[1])

                def crosses(c, p0=p0, p1=p1, others=others):
                    pts = [p0, (p0[0], c), (p1[0], c), p1]
                    return any(_hits(u, v, r) for r in others for u, v in zip(pts, pts[1:], strict=False))

                f = _bus(lo, hi, _channels(others, "y", lo, hi), crosses)
                adj = f if down else 1 - f
            else:
                p1 = (p0[0], p1[1])
        elif b.x >= a.right or a.x >= b.right:  # side by side: horizontal route
            right = b.x >= a.right
            p0 = (a.right if right else a.x, _cy(a))
            p1 = (b.x if right else b.right, _cy(b))
            route = "h"
            if abs(p1[1] - p0[1]) > tol:
                lo, hi = min(p0[0], p1[0]), max(p0[0], p1[0])

                def crosses(c, p0=p0, p1=p1, others=others):
                    pts = [p0, (c, p0[1]), (c, p1[1]), p1]
                    return any(_hits(u, v, r) for r in others for u, v in zip(pts, pts[1:], strict=False))

                f = _bus(lo, hi, _channels(others, "x", lo, hi), crosses)
                adj = f if right else 1 - f
            else:
                p1 = (p1[0], p0[1])
        else:
            continue  # overlapping blocks (area spans): nothing sensible to draw
        elbow = (route == "v" and p0[0] != p1[0]) or (route == "h" and p0[1] != p1[1])
        attrs = {
            "head": "arrow" if ln.arrow else "none",
            "flip_h": p1[0] < p0[0],
            "flip_v": p1[1] < p0[1],
            "elbow": elbow,
            "route": route,
            "adj": round(adj, 4),
            "src_box": [a.x, a.y, a.w, a.h],
            "dst_box": [b.x, b.y, b.w, b.h],
        }
        rect = Rect(min(p0[0], p1[0]), min(p0[1], p1[1]), abs(p1[0] - p0[0]), abs(p1[1] - p0[1]))
        ctx.emit(
            Shape(shape="line", attrs=attrs),
            rect,
            Style(line="primary", line_width=ctx.theme.render.connector_width),
        )


def _group_nat(ctx: _Ctx, g: Container, width: int, inherit: Style) -> tuple[int | None, str]:
    """Natural height of a row group (one row of boxes): its tallest box; kind kpi if all boxes are KPIs."""
    kids = [c for c in g.children if isinstance(c, Container)]
    m = re.match(r"\d+", _cgrid(ctx, g) or "")
    if not kids or len(kids) != len(g.children) or not m or len(kids) > int(m.group()):
        return None, "other"
    gap = _gap(ctx, _cgap(ctx, g), width, small=True)
    w = max((width - gap * (len(kids) - 1)) // len(kids), 1)
    _equalize_heads(ctx, [(k, w, 0) for k in kids])
    nats = [_box_nat(ctx, k, w, inherit) for k in kids]
    if any(n is None for n in nats):
        return None, "other"
    kind = "kpi" if all("kpi" in k.classes for k in kids) else "other"
    return max(nats), kind


def _cell_nat(ctx: _Ctx, blk, width: int, inherit: Style) -> tuple[int | None, str]:
    """(natural height, kind) of a grid cell; kind is ``kpi``, ``table`` or ``other``."""
    if isinstance(blk, Container) and "group" in blk.classes:
        return _group_nat(ctx, blk, width, inherit)
    if isinstance(blk, Container):
        return _box_nat(ctx, blk, width, inherit), "kpi" if "kpi" in blk.classes else "other"
    if isinstance(blk, Table):
        n = _natural_height(ctx, blk, width, inherit)
        return (None if n is None else round(n * _table_grow(ctx))), "table"
    if isinstance(blk, (Text, Code)):
        return _natural_height(ctx, blk, width, inherit), "other"
    return None, "other"


def _row_heights(
    ctx: _Ctx,
    gs,
    flow: list,
    cells: list[Rect],
    grid_area: Rect,
    body: Rect,
    gap: int,
    inherit: Style,
    has_tail: bool = False,
    tree: bool = False,
) -> list[int] | None:
    """Row heights of a slide-level grid: sparse rows do not stretch over the whole body.

    A row is at most ``ROW_SLACK`` x its tallest natural content (at least ``ROW_MIN`` of the body height);
    ``.kpi`` rows are exactly as tall as their cards, table rows as tall as the table grown by ``TABLE_GROW``.
    Rows holding flexible content (charts, images, ...) keep their weighted share. Also records ``ctx.fill``.
    """
    nr = len(gs.rows)
    nat: list[int | None] = [0] * nr
    kinds: list[set[str]] = [set() for _ in range(nr)]
    covered = [False] * nr
    onecol = len(gs.cols) == 1 and nr >= 2 and not tree
    rowtext = [True] * nr  # rows holding only text / code blocks (a vertical stack)
    spans: list[tuple[int, int, int | None]] = []  # blocks spanning several rows: (first, last, natural)
    stacked: set[int] = set()  # rows beside a flexible block that spans them (a column of stacked boxes)
    for k, ((_i, blk), r) in enumerate(zip(flow, cells, strict=True)):
        if gs.areas is not None:
            if k not in gs.areas:
                continue
            r0, r1 = gs.areas[k][0], gs.areas[k][2]
        else:
            r0 = r1 = min(k // len(gs.cols), nr - 1)
        n, kind = _cell_nat(ctx, blk, r.w, inherit)
        if r1 > r0:
            spans.append((r0, r1, n))
            continue
        covered[r0] = True
        kinds[r0].add(kind)
        if not isinstance(blk, (Text, Code)):
            rowtext[r0] = False
        nat[r0] = None if n is None or nat[r0] is None else max(nat[r0] or 0, n)
    caps: list[int | None] = []
    for row in range(nr):
        n = nat[row]
        if not covered[row] or n is None or n <= 0:
            caps.append(None)
        elif kinds[row] == {"kpi"}:
            caps.append(max(n, _emu(ctx.lt.kpi_min_h)))
        elif kinds[row] == {"table"}:
            caps.append(n)
        elif tree:  # org-tree levels hug their boxes (+ modest slack): the connectors fill the gaps
            caps.append(round(n * (ctx.lt.tree_slack_roomy if ctx.roomy else ctx.lt.tree_slack)))
        elif onecol and rowtext[row]:  # a stack of text / code: each row is its natural height, no gap
            caps.append(n)
            kinds[row] = {"stack"}
        else:
            lone = nr == 1 and not has_tail and ctx.dense_k < 1.0
            floor = ctx.lt.row_min_tail if has_tail else (ctx.lt.row_min_dense if lone else ctx.lt.row_min)
            if ctx.roomy and nr == 1 and not has_tail and ctx.grow > ctx.grow_base:
                floor = max(
                    floor,
                    min(
                        ctx.lt.roomy_row * body.h,
                        (ctx.lt.roomy_row_air_dense if ctx.dense_k < 1.0 else ctx.lt.roomy_row_air) * n,
                    )
                    / body.h,
                )  # fill stays >= ~50%
            caps.append(max(round(n * ctx.lt.row_slack), round(floor * body.h)))
    extra_h = 0  # natural height that spanning blocks need beyond their rows
    for r0, r1, n in spans:
        rows = range(r0, r1 + 1)
        if n is None or any(caps[r] is None for r in rows):
            if n is None and all(caps[r] is not None for r in rows):
                stacked.update(rows)  # keep the natural heights: they set the rows' shares below
                for r in rows:
                    caps[r] = None
                continue
            for r in rows:
                caps[r] = None
            nat = [None if r in rows else v for r, v in enumerate(nat)]
            continue
        have = sum(caps[r] or 0 for r in rows) + gap * (r1 - r0)
        if have < n:  # the spanning block needs more room than its rows allow: leave them uncapped
            for r in rows:
                caps[r] = None
            nat = [None if r in rows else v for r, v in enumerate(nat)]
        else:
            extra_h = max(extra_h, n - (sum(nat[r] or 0 for r in rows) + gap * (r1 - r0)))
    if all(n is not None and n > 0 for n in nat) and not stacked:
        total = sum(n for n in nat if n) + gap * (nr - 1) + max(extra_h, 0)
        ctx.fill = total / max(grid_area.h, 1)
    if all(c is None for c in caps) and not stacked:
        return None
    if stacked and all(n for n in nat):  # boxes stacked beside a tall block share its height by content
        tot = sum(nat)  # type: ignore[arg-type]
        w = [max(n or 0, ctx.lt.stack_min * tot) for n in nat]
        return grid_row_heights(replace(gs, rows=[float(x) for x in w]), grid_area.h, gap, caps)
    if (
        ctx.expand > 0 and nr >= 2 and not tree
    ):  # sparse slide: spread extra height over the capped rows (not kpi / table)
        rows = [r for r in range(nr) if caps[r] is not None and "other" in kinds[r]]
        tot = sum(caps[r] or 0 for r in rows)
        airy = ctx.roomy and ctx.grow > ctx.grow_base  # grown text: rows keep a card fill of about 50%
        for r in rows:
            grown = (caps[r] or 0) + round(ctx.expand * (caps[r] or 0) / max(tot, 1))
            if airy and nat[r]:
                grown = min(
                    grown,
                    max(
                        caps[r] or 0,
                        round(
                            (ctx.lt.roomy_row_air_dense if ctx.dense_k < 1.0 else ctx.lt.roomy_row_air)
                            * (nat[r] or 0)
                        ),
                    ),
                )
            caps[r] = grown
    return grid_row_heights(gs, grid_area.h, gap, caps)


def _place_blocks(
    ctx: _Ctx,
    blocks: list,
    area: Rect,
    inherit: Style,
    grid: str | None,
    classes: list[str],
    gap: int,
    owner,
    links: list[Link] | None = None,
) -> None:
    rects: dict[int, Rect] = {}
    for i, b in enumerate(blocks):
        if _is_abs(b):
            rects[i] = _apply_box(ctx, b, area, True)
            _place_block(ctx, b, rects[i], inherit)
    flow = [(i, b) for i, b in enumerate(blocks) if not _is_abs(b)]
    if not flow:
        _emit_links(ctx, links or [], rects)
        return
    if (
        ctx.depth == 0
    ):  # a table next to a full-width box row / chart / image keeps the full width (no ragged edge)
        ctx.cap_tables = not any(isinstance(b, (Container, Chart, Image, Media, Code)) for _, b in flow)
    # slide level: callouts are never grid cells, they close the slide body as full-width rows
    callouts: list[tuple[int, object]] = []
    if ctx.depth == 0 and len(flow) > 1:
        callouts = [(i, b) for i, b in flow if isinstance(b, Text) and "callout" in b.classes]
        if len(callouts) == len(flow):
            callouts = []
        flow = [(i, b) for i, b in flow if (i, b) not in callouts]
    gs = parse_spec(grid, len(flow), classes)
    tables: list[tuple[int, object]] = []
    searchable = False
    if gs is None or not gs.cols:  # no explicit grid token: infer the arrangement from the blocks
        searchable = gs is None and not links and ctx.depth == 0 and len(flow) > 1
        gs, flow, tables = _auto_plan(flow, gs, classes, links or [])
        searchable = searchable and not (gs and gs.flags)
        if searchable and ctx.arrange:  # layout search: lay out this candidate instead of the rule's choice
            alt = parse_spec(ctx.arrange, len(flow), classes)
            if alt is not None and alt.cols and not alt.errors:
                gs = alt
    elif gs.capacity is None and gs.areas is None and not gs.flags and len(flow) > 2:
        k = len(flow)  # `@4` / `@1:2`: tables closing a row of boxes (a `.kpi` row) are not grid cells
        while k > 0 and isinstance(flow[k - 1][1], Table):
            k -= 1
        if k >= 2 and all(isinstance(b, Container) for _, b in flow[:k]):
            tables, flow = flow[k:], flow[:k]
            gs = parse_spec(grid, len(flow), classes)
    flags: set[str] = set()
    if gs is not None:
        for err in gs.errors:
            ctx.diag("grid", err, "use @N, @CxR, @1:2 or areas like @aab/aac; falling back to auto layout")
        flags = gs.flags
    if gs is None or not gs.cols:
        text_visual, short = _block_kind_hint([b for _, b in flow])
        swapped = text_visual and not isinstance(flow[0][1], Text)
        if swapped:
            flow = [flow[1], flow[0]]
        wide = any(isinstance(b, Code) and max(map(len, b.text.split("\n")), default=0) > 45 for _, b in flow)
        if len(flow) > 1 and any(_wide_diagram(b) for _, b in flow):
            # a wide flowchart takes the full width; what follows it sits right below (the tail)
            first = _wide_diagram(flow[0][1])
            gs = GridSpec([1.0], [1.0] if first else [1.0] * len(flow), capacity=1 if first else None)
        else:
            gs = auto_spec(len(flow), text_visual=text_visual, short=short, wide_visual=wide)
        if searchable and not ctx.arrange:
            ctx.alts = _search_tokens(flow, gs, classes, bool(tables), swapped)
    elif searchable and not ctx.arrange:
        ctx.alts = _search_tokens(flow, gs, classes, bool(tables), False)
    # blocks beyond the grid's cells are stacked full width below it
    extra: list[tuple[int, object]] = []
    if gs.capacity is not None and len(flow) > gs.capacity:
        extra = flow[gs.capacity :]
        flow = flow[: gs.capacity]
    extra = sorted(extra + tables, key=lambda t: t[0]) + callouts
    if "flow" in flags:
        gap = max(gap, round(0.45 * EMU_PER_INCH))
    elif "chevron" in flags:
        gap = max(round(gap / 4), 0)
    elif links and len(gs.cols) > 1:
        gap = max(gap, round(0.4 * EMU_PER_INCH))
    grid_area = area
    tail_area: Rect | None = None
    if extra:
        grid_area, tail_area = _split_grid_tail(ctx, area, gap, gs, flow, extra, inherit, flags)
    cells = cell_rects(gs, len(flow), grid_area, gap, ctx.theme.columns)
    if "chevron" not in flags:  # boxes of one row share the tallest heading (band) height
        _equalize_heads(ctx, [(blk, r.w, r.y) for (_i, blk), r in zip(flow, cells, strict=True)])
    if "chevron" not in flags and ctx.depth == 0:
        tree = bool(links) and gs.areas is not None and len(gs.rows) >= 2
        row_h = _row_heights(ctx, gs, flow, cells, grid_area, area, gap, inherit, tail_area is not None, tree)
        if row_h is not None:
            cells = cell_rects(gs, len(flow), grid_area, gap, ctx.theme.columns, row_h)
            used = sum(row_h) + gap * (len(row_h) - 1)
            if tail_area is not None:  # the tail follows the (shortened) grid directly
                tgap = tail_area.y - grid_area.bottom
                ty = grid_area.y + used + tgap
                tail_area = Rect(area.x, ty, area.w, max(area.bottom - ty, 0))
    if "chevron" not in flags and ctx.depth == 0:
        cells = _hug_beside_visual(ctx, gs, flow, cells, inherit)
    start = len(ctx.out)
    chev_eff: float | None = None  # one text size for the whole chevron row
    chev_h: int | None = None
    if "chevron" in flags:
        alone = _chevron_alone(ctx, flow, extra, links)
        ctx.chev_grow = 1.0
        if alone and ctx.grow > 1.0 and ctx.scale >= 1.0:
            ctx.chev_grow = ctx.grow
            ctx.grew = True
        chev_h = _chevron_row_h(
            ctx,
            [b for _, b in flow],
            min((r.w for r in cells), default=area.w),
            inherit,
            area.h if alone else None,
        )
        chev_eff = min(
            (
                _chevron_eff(ctx, blk, _apply_box(ctx, blk, r, False), inherit, chev_h)
                for (_i, blk), r in zip(flow, cells, strict=True)
                if isinstance(blk, (Text, Shape, Container))
            ),
            default=None,
        )
    for (i, blk), r in zip(flow, cells, strict=True):
        r = _apply_box(ctx, blk, r, False)
        rects[i] = r
        if "chevron" in flags and isinstance(blk, (Text, Shape, Container)):
            rects[i] = _place_chevron(ctx, blk, r, inherit, chev_eff, chev_h)
        else:
            _place_block(ctx, blk, r, inherit)
            if isinstance(blk, (Image, Media)) and _text_mate(flow):
                _top_align(ctx.out[-1])
    if "chevron" not in flags:
        parent = list(range(len(flow)))

        def find(k: int) -> int:
            while parent[k] != k:
                k = parent[k]
            return k

        seen: dict[tuple, int] = {}
        for k, r in enumerate(cells[: len(flow)]):
            for key in (("row", r.y), ("col", r.x, r.w)):  # cells in one row / stacked column are linked
                if key in seen:
                    parent[find(k)] = find(seen[key])
                else:
                    seen[key] = k
        comps: dict[int, list] = {}
        for k, (_i, blk) in enumerate(flow):
            comps.setdefault(find(k), []).append(blk)
        for group in comps.values():
            _share_gaps(ctx, group)
    if "flow" in flags:
        for a, b in zip(cells, cells[1:], strict=False):
            g = b.x - a.right
            overlap_y = min(a.bottom, b.bottom) - max(a.y, b.y)
            if g <= 0 or overlap_y <= 0:
                continue
            aw = min(round(g * 0.8), round(0.35 * EMU_PER_INCH))
            ah = min(round(aw * 1.2), overlap_y)
            cy = max(a.y, b.y) + overlap_y // 2
            st = Style(fill="muted", line=None)
            ctx.emit(Shape(shape="arrow-right"), Rect(a.right + (g - aw) // 2, cy - ah // 2, aw, ah), st)
    if extra and tail_area is not None:
        sub = _place_stack(ctx, [b for _, b in extra], tail_area, inherit, gap, owner)
        for k, (i, _b) in enumerate(extra):
            if k in sub:
                rects[i] = sub[k]
    if ctx.depth == 0 and extra and len(flow) == 1 and _is_diagram(flow[0][1]):
        _hug_tail(ctx, start, area, gap)
    _emit_links(ctx, links or [], rects)


def _same_grid(a: GridSpec | None, b: GridSpec | None) -> bool:
    return a is not None and b is not None and (a.cols, a.rows, a.areas) == (b.cols, b.rows, b.areas)


def _search_tokens(flow: list, rule: GridSpec, classes: list[str], tail: bool, swapped: bool) -> list[str]:
    """Alternative arrangements (grid tokens) of the slide-level blocks, minus the rule's own choice."""
    if (
        swapped
    ):  # the rule put the text first; as written (visual first) the only token that reorders is `b/a`
        return ["b/a"]
    n = len(flow)
    toks = alternatives([b for _, b in flow], [_weight(b) for _, b in flow], tail=tail)
    return [t for t in toks if not _same_grid(parse_spec(t, n, classes), rule)]


def _text_mate(flow: list) -> bool:
    """True when a visual shares the grid with text or boxes (their tops line up)."""
    return any(isinstance(b, (Text, Container)) for _, b in flow)


def _top_align(p: Placed) -> None:
    """A picture / video beside text sits at the top of its cell (the renderer honors ``valign``)."""
    if p.style.valign is None:
        p.style = p.style.merged(Style(valign="top"))


def _hug_beside_visual(ctx: _Ctx, gs, flow: list, cells: list[Rect], inherit: Style) -> list[Rect]:
    """A box beside a chart / image takes its natural height, top-aligned with the visual.

    Text-only boxes next to a visual used to stretch over the visual's whole height and stayed mostly empty.
    A box that would end up under ``BESIDE_MIN`` of the visual height grows part of the way to that minimum.
    """
    if gs.areas is not None or not gs.cols:
        return cells
    ncol = len(gs.cols)
    out = list(cells)
    for k, ((_i, blk), r) in enumerate(zip(flow, cells, strict=True)):
        if not isinstance(blk, Container) or {"kpi", "group"} & set(blk.classes):
            continue
        b = blk.box
        if b is not None and (b.h is not None or b.y is not None):
            continue
        row = k // ncol
        if not any(
            isinstance(o, (Chart, Image, Media))
            for j, (_n, o) in enumerate(flow)
            if j // ncol == row and j != k
        ):
            continue
        n = _box_nat(ctx, blk, r.w, inherit)
        if n is None:
            continue
        floor = round(ctx.lt.beside_min * r.h)
        h = round(n * ctx.lt.beside_slack)
        if h < floor:
            h = round(h + ctx.lt.beside_fill * (floor - h))
        out[k] = Rect(r.x, r.y, r.w, min(h, r.h))
    return out


def _is_diagram(b) -> bool:
    return isinstance(b, Container) and "diagram" in b.classes and b.title is None


def _wide_diagram(b) -> bool:
    """A flowchart whose grid is much wider than tall (>= 4 columns, or a single row of 3+): full width."""
    if not _is_diagram(b) or not b.grid:
        return False
    gs = parse_spec(b.grid, len(b.children), b.classes)
    if gs is None or gs.errors or not gs.cols or not gs.rows:
        return False
    nc, nr = len(gs.cols), len(gs.rows)
    return nc >= 4 or (nc >= 3 and nc / nr >= 2.5)


def _hug_tail(ctx: _Ctx, start: int, area: Rect, gap: int) -> None:
    """A lone diagram followed by blocks (a callout): the blocks sit right below it, both top-anchored."""
    items = ctx.out[start:]
    if len(items) < 2:
        return
    diag = items[0]  # the diagram card is emitted first and spans the diagram
    inside = [p for p in items if p.y < diag.y + diag.h and p.y + p.h > diag.y and p is not diag]
    members = [diag, *inside]
    rest = [p for p in items if all(p is not m for m in members)]
    if not rest:
        return
    top = min(p.y for p in members)
    dbot = max(p.y + p.h for p in members)
    rtop = min(p.y for p in rest)
    new_top = area.y
    for p in members:
        p.y += new_top - top
    for p in rest:
        p.y += new_top + (dbot - top) + gap - rtop


def _split_grid_tail(
    ctx: _Ctx, area: Rect, gap: int, gs, flow: list, extra: list, inherit: Style, flags: set[str]
) -> tuple[Rect, Rect]:
    """Split ``area`` into the grid part (top) and the full-width stack of leftover blocks (bottom)."""
    tgap = max(gap, round(0.1 * EMU_PER_INCH)) if "chevron" in flags else gap
    avail = max(area.h - tgap, 0)
    nat = [_natural_height(ctx, b, area.w, inherit) for _, b in extra]
    tail_nat = sum(n for n in nat if n is not None) + gap * (len(extra) - 1)
    has_flex = any(n is None for n in nat)
    if "chevron" in flags:
        cw = round((area.w - gap * (len(gs.cols) - 1)) / max(len(gs.cols), 1))
        compact = _chevron_row_h(ctx, [b for _, b in flow], cw, inherit)
        has_extras = any(
            isinstance(b, Container) and any(not isinstance(ch, (Text, Shape)) for ch in b.children)
            for _, b in flow
        )
        grid_h = round(avail * 0.5) if has_extras else min(compact, round(avail * 0.5))
    elif has_flex:
        grid_h = round(avail * 0.5)
    else:
        grid_h = max(avail - tail_nat, round(avail * 0.4))
    grid_h = min(grid_h, avail)
    return Rect(area.x, area.y, area.w, grid_h), Rect(
        area.x, area.y + grid_h + tgap, area.w, max(avail - grid_h, 0)
    )


def _chevron_font(ctx: _Ctx, sh: Shape, st: Style) -> Style:
    """Chevron text is at least the theme body size and never smaller than the table text beside it."""
    if sh.style and sh.style.font_size:
        return st
    t = ctx.theme
    floor = max(
        t.sizes.get("body", DEFAULT_SIZES["body"]),
        t.sizes.get("table", DEFAULT_SIZES["table"]) * ctx.dense_k * ctx.lt.table_font_grow,
    )
    return st.merged(Style(font_size=max(st.font_size or 18, floor)))


def _chevron_geom(
    ctx: _Ctx, blk, rect: Rect, inherit: Style, hcap: int | None = None
) -> tuple[Shape, Style, Rect]:
    sh = _chevron_shape(blk)
    st = _chevron_font(ctx, sh, _text_style(ctx, sh, inherit))
    if hcap is not None:
        rect = Rect(rect.x, rect.y, rect.w, min(rect.h, hcap))
    # the preset text rectangle already starts a point depth inside both ends: add only a small padding
    st = st.merged(Style(padding=ctx.lt.chevron_pad, align="center", valign="middle"))
    if icon := _icon_name(blk):  # the icon sits left of the text: reserve its room as a left inset
        side = min(round(ctx.lt.icon_head * (st.font_size or 18) * EMU_PER_PT), round(0.4 * rect.h))
        sh = sh.model_copy(
            update={
                "attrs": {
                    **sh.attrs,
                    "icon": icon,
                    "icon_side": side,
                    "icon_inset": side + round(ctx.lt.icon_gap * side),
                }
            }
        )
    return sh, st, rect


def _chevron_text_w(rect: Rect, st: Style, sh: Shape | None = None, adj: float | None = None) -> int:
    """Width of a chevron's text area: the shape minus both point depths, the padding and the icon."""
    inset = sh.attrs.get("icon_inset", 0) if sh is not None else 0
    adj = LayoutTokens().chevron_adj if adj is None else adj
    return rect.w - 2 * round(adj * min(rect.w, rect.h)) - 2 * _pad(st) - inset


def _chevron_alone(ctx: _Ctx, flow: list, extra: list, links) -> bool:
    """A single chevron row is everything the slide holds (plain text boxes only, no tail, no connectors)."""
    if ctx.depth != 0 or extra or links:
        return False
    return all(
        isinstance(b, (Text, Shape))
        or (isinstance(b, Container) and all(isinstance(ch, (Text, Shape)) for ch in b.children))
        for _, b in flow
    )


def _chevron_row_h(ctx: _Ctx, blocks: list, width: int, inherit: Style, alone_h: int | None = None) -> int:
    """Height of a chevron row: tallest text + padding, clamped to ``CHEVRON_MIN_H`` .. ``CHEVRON_MAX_H``.

    A row alone on the slide (``alone_h`` = the body height) aims at ``CHEVRON_ALONE_SHARE`` of it, up to
    ``CHEVRON_MAX_ALONE``.
    """
    lo, hi = _emu(ctx.lt.chevron_min_h), _emu(ctx.lt.chevron_max_h)
    if alone_h is not None:
        hi = _emu(ctx.lt.chevron_max_alone)
        lo = max(lo, min(hi, round(ctx.lt.chevron_alone_share * alone_h)))
    h = round(EMU_PER_INCH)
    for _ in range(3):  # the point depth depends on the height, the height on the wrapped text
        need = 0
        for blk in blocks:
            if not isinstance(blk, (Text, Shape, Container)):
                continue
            sh, st, rect = _chevron_geom(ctx, blk, Rect(0, 0, width, h), inherit)
            eff = (
                measure.effective_scale(st.font_size or 18, ctx.scale, ctx.theme.min_font_size)
                * ctx.chev_grow
            )
            need = max(
                need,
                measure.paragraphs_height(
                    sh.paragraphs, _chevron_text_w(rect, st, sh, ctx.lt.chevron_adj), st, eff
                ),
            )
        h = min(max(round(need / 0.8), round(need + 2 * _emu(ctx.lt.chevron_vpad)), lo), hi)
    return h


def _chevron_eff(ctx: _Ctx, blk, rect: Rect, inherit: Style, hcap: int | None = None) -> float:
    """Font scale of a chevron whose wrapping survives a renderer that is ~12% narrower than the estimate.

    A label that just fits would leave a lone character on its last line when the real font is wider (e.g.
    "KPI モニタリン / グ"): shrink until the line count no longer changes in a 12% narrower area (>= 80%).
    """
    sh, st, rect = _chevron_geom(ctx, blk, rect, inherit, hcap)
    width = _chevron_text_w(rect, st, sh, ctx.lt.chevron_adj)
    base = st.font_size or 18
    first = measure.effective_scale(base, ctx.scale, ctx.theme.min_font_size) * ctx.chev_grow
    for m in (1.0, 0.95, 0.9, 0.85, 0.8):
        eff = measure.effective_scale(base, ctx.scale * m, ctx.theme.min_font_size) * ctx.chev_grow
        wide = measure.paragraphs_height(sh.paragraphs, width, st, eff)
        narrow = measure.paragraphs_height(sh.paragraphs, round(width * 0.88), st, eff)
        if narrow <= wide * 1.001:
            return eff
    return first


def _place_chevron(
    ctx: _Ctx, blk, rect: Rect, inherit: Style, eff_cap: float | None = None, hcap: int | None = None
) -> Rect:
    full = rect
    sh, st, rect = _chevron_geom(ctx, blk, rect, inherit, hcap)
    eff = measure.effective_scale(st.font_size or 18, ctx.scale, ctx.theme.min_font_size) * ctx.chev_grow
    if eff_cap is not None:
        eff = min(eff, eff_cap)
    # centered text may use the middle 80% of the height
    need = measure.paragraphs_height(
        sh.paragraphs, _chevron_text_w(rect, st, sh, ctx.lt.chevron_adj), st, eff
    )
    if need > rect.h * 0.8:
        ctx.over.append(_label(blk))
    ctx.emit(sh, rect, st, eff)
    if "icon_side" in sh.attrs:  # icon just before the (centered) text block, vertically centered
        side = sh.attrs["icon_side"]
        left = rect.x + round(ctx.lt.chevron_adj * min(rect.w, rect.h)) + _pad(st)
        avail = _chevron_text_w(rect, st, sh, ctx.lt.chevron_adj)
        size = (st.font_size or 18) * eff
        line = max(
            (measure.text_em(p.plain, bold=True) * size * EMU_PER_PT for p in sh.paragraphs), default=0
        )
        off = max(round((avail - min(line, avail)) / 2), 0)
        ctx.emit(
            _icon_item(sh.attrs["icon"]),
            Rect(left + off, rect.y + (rect.h - side) // 2, side, side),
            Style(fill=st.color or "primary"),
        )
    # a chevron shape only carries text: place the other children (table, chart, ...) under it
    extra = (
        [ch for ch in blk.children if not isinstance(ch, (Text, Shape))] if isinstance(blk, Container) else []
    )
    if not extra:
        return rect
    gap = _gap(ctx, getattr(blk, "gap", None), full.w, small=True)
    area = Rect(full.x, rect.bottom + gap, full.w, full.bottom - rect.bottom - gap)
    if area.h < round(0.4 * EMU_PER_INCH):
        ctx.diag(
            "dropped-content",
            f"{len(extra)} non-text item(s) in {_label(blk)} have no room next to the chevron",
            "end the box with `@end` or move the visual out of the chevron box",
            line=getattr(blk, "line", None),
        )
        return rect
    _place_stack(ctx, extra, area, _only_inheritable(st), gap, blk)
    return rect


# --------------------------------------------------------------------------- slide frame


def _text_el(role: str, text: str, attrs: dict | None = None) -> Text:
    return Text(role=role, paragraphs=[Paragraph(runs=[_run(text)])], attrs=attrs or {})  # type: ignore[arg-type]


def _run(text: str):
    from ..ir import Run

    return Run(text=text)


def _bottom(c: _Ctx) -> int:
    return max((p.y + p.h for p in c.out), default=0)


def _very_sparse(elements: list) -> bool:
    """Boxes only (callouts aside), each with at most ``SPARSE_LINES`` short text lines and nothing else."""
    boxes = [e for e in elements if isinstance(e, Container)]
    if not boxes or any(
        not isinstance(e, Container) and not (isinstance(e, Text) and "callout" in e.classes)
        for e in elements
    ):
        return False

    def ok(c: Container) -> bool:
        if (
            c.grid
            or c.links
            or c.classes
            and any(n in ("kpi", "flow", "chevron", "diagram") for n in c.classes)
        ):
            return False
        lines = 0
        for ch in c.children:
            if isinstance(ch, Container):
                return False
            if not isinstance(ch, Text):
                return False
            lines += len(ch.paragraphs)
            if any(measure.text_em(p.plain) > SPARSE_LINE_EM for p in ch.paragraphs):
                return False
        return lines <= SPARSE_LINES

    return all(ok(b) for b in boxes)


def _spread(ctx: _Ctx, fin: _Ctx, run, body: Rect, elements: list) -> _Ctx:
    """Vertical policy of a sparse slide body: top-anchored, the leftover stays at the bottom.

    1. capped rows of multi-row content expand until the leftover is at most ``LEFT_KEEP`` of the body;
    2. only a very sparse slide (content < ``VERY_SPARSE_FILL`` of the body) moves down, by at most
       ``LEFT_SHIFT`` of what is left. Anything else keeps its body top at ``head_bottom + TOP_GAP``.
    """
    if fin.scale < 1.0 or fin.over or not any(isinstance(e, (Container, Table)) for e in elements):
        return fin
    left = body.bottom - _bottom(fin)
    left0 = left
    keep = round(ctx.lt.left_keep * body.h)
    if left > keep:
        c = run(body, grow=fin.grow, expand=left - keep)
        if not c.over and c.out:
            fin = c
            left = body.bottom - _bottom(fin)
    small_theme = (
        ctx.theme.sizes.get("body", DEFAULT_SIZES["body"]) <= ctx.lt.grow_small_pt
    )  # consulting themes (jp-business: 11pt)
    if max(left, left0) >= ctx.lt.roomy_left * body.h and (
        fin.dense_k < 1.0 or small_theme
    ):  # a quarter of the body stays empty (before the rows expanded)
        expanded = fin.expand > 0
        steps = (ctx.lt.roomy_grow_dense, 1.35, 1.3, 1.25) if fin.dense_k < 1.0 else ()
        for f in (
            *steps,
            ctx.lt.roomy_grow,
            1.15,
            1.1,
            1.05,
            1.0,
        ):  # tables / trees take more height, text grows a little
            if f > 1.0 and not ctx.lt.grow:  # growth is off: text keeps its nominal size
                continue
            g = round(fin.grow * f, 2)
            if (
                fin.dense_k < 1.0 and g * fin.dense_k > ctx.lt.dense_roomy_body
            ):  # consulting body text stays below ~1.6x the theme size
                continue
            if expanded:  # text first: grow it, then spread what is left over the rows
                c = run(body, grow=g, expand=0, roomy=True, grow_base=fin.grow)
                if c.over or not c.out:
                    continue
                rest = body.bottom - _bottom(c) - keep
                if rest > 0:
                    c2 = run(body, grow=g, expand=rest, roomy=True, grow_base=fin.grow)
                    if not c2.over and c2.out:
                        c = c2
                if g > fin.grow or _bottom(c) > _bottom(fin):
                    fin = c
                    left = body.bottom - _bottom(fin)
                    break
                continue
            c = run(body, grow=g, expand=fin.expand, roomy=True, grow_base=fin.grow)
            if not c.over and c.out and _bottom(c) > _bottom(fin):
                fin = c
                left = body.bottom - _bottom(fin)
                break
    top = min((p.y for p in fin.out), default=body.y)
    if _bottom(fin) - top < ctx.lt.very_sparse_fill * body.h:
        dy = round(
            left
            * (
                ctx.lt.left_shift
                if any(isinstance(e, Container) for e in elements)
                else ctx.lt.left_shift_table
            )
        )
        if dy > 0:
            c = run(
                Rect(body.x, body.y + dy, body.w, body.h - dy),
                grow=fin.grow,
                expand=fin.expand,
                roomy=fin.roomy,
            )
            if not c.over and c.out:
                fin = c
    return fin


def _search(first: _Ctx, solve, theme: Theme, body: Rect) -> tuple[_Ctx, str | None]:
    """Layout search: try the alternative arrangements of ``first`` (the rule's choice) and keep the best.

    The rule's choice wins unless it is already good (``SEARCH_SKIP``) or another candidate beats it by at
    least ``SEARCH_MARGIN``. Returns the winning context and its token (``None``: the rule's choice stays).
    """
    if not first.alts or not first.out:
        return first, None
    base = score_layout(first.out, body, theme, over=len(first.over))
    if base.total < SEARCH_SKIP:
        return first, None
    best: tuple[float, _Ctx, str] | None = None
    for tok in first.alts[: MAX_CANDIDATES - 1]:
        c = solve(tok)
        if not c.out:
            continue
        sc = score_layout(c.out, body, theme, over=len(c.over)).total
        if best is None or sc < best[0] - 1e-9:
            best = (sc, c, tok)
    if best is not None and base.total - best[0] >= SEARCH_MARGIN:
        return best[1], best[2]
    return first, None


def layout_slide(slide: Slide, deck: Deck, theme: Theme, index: int) -> list[Placed]:
    """Return every visible item of ``slide`` (title included) in z-order, with final boxes and merged styles.

    ``index`` is the 0-based slide index (used for footer / slide number items).
    Problems (overflow, unknown layout, ...) are appended to ``deck.diagnostics``.
    """
    if slide.html is not None:  # whole-slide HTML: Chromium decides the layout
        from .htmlslide import layout_html_slide

        return layout_html_slide(slide, deck, theme, index)
    try:
        return _layout(slide, deck, theme, index)
    except Exception as e:  # never raise on bad input
        deck.diagnostics.append(
            Diagnostic(
                level="error",
                message=f"layout failed: {type(e).__name__}: {e}",
                slide=index + 1,
                rule="layout-error",
                hint="simplify this slide or report a bug",
            )
        )
        return []


def _layout(slide: Slide, deck: Deck, theme: Theme, index: int) -> list[Placed]:
    try:
        W, H = slide_size(deck.size)
    except ValueError:
        W, H = slide_size("16:9")
    measure.set_default_font(theme.fonts.body)
    measure.set_tokens(theme.layout)
    ctx = _Ctx(deck, theme, slide, index, W, H)
    dense = deck.density == "dense" or "dense" in slide.classes
    ctx.dense_k = theme.dense_scale if dense else 1.0
    ctx.tight = ctx.lt.dense_tight if dense else 1.0

    kind = slide.layout
    if kind not in ("cover", "section", "blank", "center", "content"):
        if kind:
            ctx.diag(
                "layout", f"unknown layout {kind!r}", "use cover, section, blank or center; using automatic"
            )
        kind = None
    if kind is None:
        kind = "content"
        if slide.title and not slide.elements and not slide.conclusion:
            kind = "cover" if index == 0 else "section"
    if deck.css or slide.css:
        ctx.css = css.CssIndex(deck, slide, index, kind)

    Mx, My = to_emu(theme.margin_x), to_emu(theme.margin_y)
    gap = to_emu(theme.gap)
    sg = round(gap * 0.5)
    inner_w = W - 2 * Mx

    head: list[Placed] = []
    tail: list[Placed] = []

    def put(dst: list[Placed], el, rect: Rect, style: Style, fs: float = 1.0):
        dst.append(
            Placed(
                element=el, x=rect.x, y=rect.y, w=max(rect.w, 0), h=max(rect.h, 0), style=style, font_scale=fs
            )
        )

    def fit_text(el: Text, rect: Rect, st: Style) -> float:
        size = st.font_size or 18
        eff = _fit(ctx, lambda s: _text_need(ctx, el, st, rect.w, s), rect.h, size)
        if _text_need(ctx, el, st, rect.w, eff) > rect.h * _TOL:
            ctx.diag(
                "overflow",
                f"{el.role} text does not fit its area",
                "shorten text or split the slide",
                line=el.line,
            )
        return eff

    body: Rect | None
    if kind in ("cover", "section"):
        band_h = round(H * 0.34)
        by = round(H * 0.24)
        if theme.title_band:
            put(
                head,
                Shape(shape="rect", id="band"),
                Rect(0, by, W, band_h),
                Style(fill=theme.title_band, line=None),
            )
        if slide.title:
            st = _role_style(ctx, "title", cover=True)
            st = st.merged(Style(valign="bottom"))
            if theme.title_band:
                st = st.merged(Style(color=theme.title_band_color))
            r = Rect(Mx, by, inner_w, round(band_h * 0.65))
            st = _styled(ctx, slide.title, st, classes=False)
            put(head, slide.title, r, st, fit_text(slide.title, r, st))
        sub = slide.subtitle or slide.lead
        if sub:
            st = _role_style(ctx, "subtitle", cover=True)
            if theme.title_band:
                st = st.merged(Style(color=theme.title_band_color))
            r = Rect(Mx, by + round(band_h * 0.68), inner_w, round(band_h * 0.3))
            st = _styled(ctx, sub, st.merged(Style(valign="top")), classes=False)
            put(head, sub, r, st, fit_text(sub, r, st))
        body = Rect(Mx, by + band_h + sg, inner_w, H - (by + band_h + sg) - My) if slide.elements else None
        y_top = 0
    else:
        y = My
        head_bottom: int | None = (
            None  # bottom of the title band / title / lead: the body starts ctx.lt.top_gap below
        )
        if kind != "blank" and slide.title:
            tr_h = to_emu(theme.title_height)
            st = _role_style(ctx, "title")
            if theme.title_band:
                st = st.merged(Style(color=theme.title_band_color))
                put(
                    head,
                    Shape(shape="rect", id="band"),
                    Rect(0, 0, W, tr_h + My // 2),
                    Style(fill=theme.title_band, line=None),
                )
                r = Rect(Mx, 0, inner_w, tr_h + My // 2)
                y = tr_h + My // 2 + sg
                head_bottom = r.bottom
            else:
                r = Rect(Mx, My, inner_w, tr_h)
                y = My + tr_h
                head_bottom = y
            st = _styled(ctx, slide.title, st, classes=False)
            put(head, slide.title, r, st, fit_text(slide.title, r, st))
        for role, el in (("subtitle", slide.subtitle), ("lead", slide.lead)):
            if kind == "blank" or el is None or not el.paragraphs:
                continue
            st = _styled(ctx, el, _role_style(ctx, role))
            size = st.font_size or 18
            h = round(_text_need(ctx, el, st, inner_w, 1.0))
            max_h = round(H * 0.18)
            eff = 1.0
            if h > max_h:
                eff = _fit(ctx, lambda s, el=el, st=st: _text_need(ctx, el, st, inner_w, s), max_h, size)
                h = round(_text_need(ctx, el, st, inner_w, eff))
            r = Rect(Mx, y + (sg // 2 if y == My else 0), inner_w, h)
            put(head, el, r, st, eff)
            y = r.bottom + sg // 2
            head_bottom = r.bottom
        y_top = y if head_bottom is None else head_bottom + _emu(ctx.lt.top_gap)
        body = None

    # bottom stack (cover/blank get no footer row)
    bottom = H - My
    show_row = kind not in ("cover", "blank") and bool(deck.footer or deck.slide_number)
    if show_row:
        fh = round(0.26 * EMU_PER_INCH)
        fy = H - fh - round(0.1 * EMU_PER_INCH)
        cst = _role_style(ctx, "caption")
        if deck.footer:
            put(
                tail,
                _text_el("caption", deck.footer, {"field": "footer"}),
                Rect(Mx, fy, round(inner_w * 0.7), fh),
                cst.merged(Style(valign="middle")),
            )
        if deck.slide_number:
            put(
                tail,
                _text_el("caption", str(index + 1), {"field": "slide_number"}),
                Rect(W - Mx - round(0.9 * EMU_PER_INCH), fy, round(0.9 * EMU_PER_INCH), fh),
                cst.merged(Style(align="right", valign="middle")),
            )
        bottom = fy - sg // 2
        if (ft := footer_top(theme)) is not None:  # template: its own footer zone replaces the built-in row
            bottom = min(ft - sg // 2, H - My)
    elif kind not in ("cover", "section"):
        bottom = H - My

    if kind not in ("cover", "section"):
        notes = [f for f in slide.footnotes if f.paragraphs]
        if notes:
            sts = [_styled(ctx, f, _role_style(ctx, "footnote"), classes=False) for f in notes]
            max_h = round(H * ctx.lt.footnote_max)
            effs = [1.0] * len(notes)
            hs = [round(_text_need(ctx, f, st, inner_w, 1.0)) for f, st in zip(notes, sts, strict=True)]
            if sum(hs) > max_h:
                base = min(st.font_size or 10 for st in sts)

                def total(s_: float) -> float:
                    return sum(
                        _text_need(
                            ctx,
                            f,
                            st,
                            inner_w,
                            measure.effective_scale(st.font_size or 10, s_, theme.min_font_size),
                        )
                        for f, st in zip(notes, sts, strict=True)
                    )

                eff0 = _fit(ctx, total, max_h, base)
                effs = [measure.effective_scale(st.font_size or 10, eff0, theme.min_font_size) for st in sts]
                hs = [
                    round(_text_need(ctx, f, st, inner_w, e))
                    for f, st, e in zip(notes, sts, effs, strict=True)
                ]
                if sum(hs) > max_h * _TOL:
                    ctx.diag(
                        "overflow",
                        "footnotes overflow their area at the minimum font size",
                        "shorten text or split the slide",
                        line=notes[0].line,
                    )
            fy0 = bottom - sum(hs)
            for f, st, h, e in zip(notes, sts, hs, effs, strict=True):
                put(tail, f, Rect(Mx, fy0, inner_w, h), st, e)
                fy0 += h
            bottom = bottom - sum(hs) - sg // 2
        if slide.conclusion is not None and slide.conclusion.paragraphs:
            c = slide.conclusion
            st = _styled(ctx, c, _role_style(ctx, "conclusion"))
            h = max(round(_text_need(ctx, c, st, inner_w, 1.0)), round(0.4 * EMU_PER_INCH))
            h = min(h, round(H * ctx.lt.footnote_max))
            eff = fit_text(c, Rect(0, 0, inner_w, h), st)
            put(tail, c, Rect(Mx, bottom - h, inner_w, h), st, eff)
            bottom = bottom - h - sg
        body = Rect(Mx, y_top, inner_w, bottom - y_top)
        if kind == "blank":
            body = Rect(Mx, My, inner_w, bottom - My)

    # ---- body with global autofit
    elements = list(slide.elements)
    final_ctx: _Ctx | None = None
    if body is not None and elements and body.h > 0:
        slide_inherit = Style()
        for n in slide.classes:
            if n in theme.classes:
                slide_inherit = slide_inherit.merged(_only_inheritable(theme.classes[n]))
        slide_inherit = slide_inherit.merged(_only_inheritable(ctx.css.own(slide)))
        if kind == "center":
            slide_inherit = slide_inherit.merged(Style(align="center", valign="middle"))
        sgap = _gap(ctx, slide.attrs.get("gap") or ctx.css.own(slide).gap, body.w)

        body_pt = theme.sizes.get("body", DEFAULT_SIZES["body"]) * ctx.dense_k
        very = body_pt >= ctx.lt.grow_very_sparse_pt and _very_sparse(elements)
        text_only = kind != "center" and all(
            isinstance(e, Text) and e.role == "body" and "callout" not in e.classes for e in elements
        )

        def solve(arrange: str | None = None) -> _Ctx:
            def run(area: Rect, **kw) -> _Ctx:
                c = _Ctx(
                    deck,
                    theme,
                    slide,
                    index,
                    W,
                    H,
                    dense_k=ctx.dense_k,
                    tight=ctx.tight,
                    head_grow=very,
                    css=ctx.css,
                    arrange=arrange,
                    text_only=text_only,
                    **kw,
                )
                _place_blocks(
                    c, elements, area, slide_inherit, _slide_grid(ctx), slide.classes, sgap, None, slide.links
                )
                return c

            for s in _SCALES:
                fc = run(body, scale=s)
                if not fc.over:
                    break
            if fc.scale >= 1.0 and not fc.over and ctx.lt.grow:
                # sparse slide: grow text uniformly (siblings share one factor), more for small themes
                top = ctx.lt.grow_small if (body_pt <= ctx.lt.grow_small_pt) else ctx.lt.grow_big
                if ctx.dense_k < 1.0:  # dense slides: up to ctx.lt.dense_grow_body x the theme body size
                    top = max(top, ctx.lt.dense_grow_body / ctx.dense_k)
                if very:
                    top = max(top, min(ctx.lt.grow_very_sparse, ctx.lt.grow_very_sparse_max_pt / body_pt))
                n = round((top - 1.05) / 0.05)
                for g in [round(top - 0.05 * i, 2) for i in range(n + 1)]:
                    c3 = run(body, grow=g)
                    if c3.grew and not c3.over and (c3.fill is None or c3.fill <= ctx.lt.grow_fill):
                        fc = c3
                        break
            if fc.scale >= 1.0 and not fc.over:
                fc = _spread(ctx, fc, run, body, elements)
            return fc

        final_ctx = solve()
        final_ctx, chosen = _search(final_ctx, solve, theme, body)
        if chosen:
            ctx.diag(
                "auto-layout",
                f"arranged as `@{chosen}` (the default arrangement scored worse)",
                f"write `@{chosen}` to pin it",
                level="info",
            )
        ctx.diags += final_ctx.diags
        seen: set[str] = set()
        for lab in final_ctx.over:
            if lab not in seen:
                seen.add(lab)
                ctx.diag(
                    "overflow",
                    f"{lab} overflows its area at the minimum font size",
                    "shorten text or split the slide",
                )
    elif body is not None and body.h <= 0 and elements:
        ctx.diag("overflow", "no room left for the body", "shorten text or split the slide")

    ctx.diags += ctx.css.diagnostics()
    deck.diagnostics.extend(ctx.diags)
    return head + (final_ctx.out if final_ctx else []) + tail
