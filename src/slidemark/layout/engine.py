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
from ..theme import Theme
from ..units import EMU_PER_INCH, EMU_PER_PT, slide_size, to_emu
from . import measure
from .grid import GridSpec, Rect, auto_spec, cell_rects, parse_spec, tree_areas
from .grid import row_heights as grid_row_heights
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
ICON_HEAD = 1.2  # icon side / heading font size (icon left of the heading text)
ICON_KPI = 2.0  # icon side / label font size (icon above a kpi number)
ICON_GAP = 0.4  # gap between icon and text, in icon sides
CHEVRON_ADJ = 0.3  # chevron point depth / shorter side; the renderer sets the same adjustment
CHEVRON_PAD_PT = 4  # text padding inside a chevron (the preset's text rectangle already clears the points)
CHEVRON_MIN_H = 0.7  # inches: a chevron row is its text height + padding, at least this tall ...
CHEVRON_MAX_H = 1.3  # ... and at most this tall
CHEVRON_VPAD = 0.17  # inches above and below the text of a chevron
CODE_GROW = 1.25  # code text grows with the sparse-slide growth, up to this factor
TABLE_GROW = 1.4  # rows of a table with spare room grow up to this factor (a row stays near its text)
TABLE_FONT_GROW = 1.2  # table text grows with the sparse-slide growth, up to this factor
TABLE_GROW_ROOMY = 2.0  # ... and rows up to this factor when a quarter of the body would stay empty
TREE_SLACK_ROOMY = 1.3  # org-tree boxes may be this much taller than their content on such slides
ROOMY_LEFT = 0.25  # share of the body left empty (top-anchored) that triggers the roomy pass
ROOMY_GROW = 1.2  # ... which also grows box / tree text by up to this factor on top of the sparse growth
BESIDE_MIN = 0.5  # a box beside a chart / image takes its natural height, at least this share of the visual
BESIDE_FILL = 0.6  # ... a shorter one grows by this share of the way to that minimum
BESIDE_SLACK = 1.12  # ... headroom over the natural height (grown text keeps some air)
FULL_WIDTH = 0.6  # a table wider than this share of the slide width counts as a full-width table
ROW_SLACK = 1.35  # a grid row is at most this much taller than its tallest content ...
TREE_SLACK = 1.15  # org-tree boxes are at most this much taller than their content
ROW_MIN_TAIL = 0.12  # ... when blocks (a chart, a table) follow the grid: the row hugs its content
STACK_MIN = 0.4  # stacked boxes beside a tall block: each gets at least this share of the natural total
ROW_MIN_DENSE = 0.42  # dense slides: a lone row of boxes is at least this share of the body (fuller boxes)
ROW_MIN = 0.3  # ... but never shorter than this share of the body height (0.12 when blocks follow the grid)
GROW_SMALL = (
    1.35  # sparse slides: text grows up to this factor when the theme body size is <= GROW_SMALL_PT ...
)
GROW_SMALL_PT = 14
GROW_BIG = 1.15  # ... and up to this factor for larger themes
GROW_VERY_SPARSE = (
    1.4  # very sparse boxes (<= SPARSE_LINES short lines each) of a theme with body >= ..._PT ...
)
GROW_VERY_SPARSE_PT = 16
GROW_VERY_SPARSE_MAX_PT = 26  # ... grow up to this factor, but never beyond this body size
GROW_HEAD = 1.25  # box headings grow along with the body text, up to this factor
SPARSE_LINES = 2
SPARSE_LINE_EM = 22  # a "short" line
GROW_FILL = 0.85  # growth stops when the content would fill more than this share of the grid
GROW_BOX_FILL = 0.92  # ... or more than this share of a box
LEFT_KEEP = 0.12  # rows of a sparse slide expand until at most this share of the body is left over ...
VERY_SPARSE_FILL = 0.4  # content below this share of the body (after growth) is "very sparse" ...
LEFT_SHIFT = 1 / 3  # ... and only then moves down, by at most this share of the leftover (boxes) ...
LEFT_SHIFT_TABLE = 0.2  # ... or this share (slides without boxes: a lone table, a chart)
DENSE_GROW_BODY = 1.25  # dense slides: text may grow up to this multiple of the theme body size
MATH_GROW = 1.6  # an equation alone in its cell is this much larger than body text
TOP_GAP = 0.25  # inches between the title band (or lead) and the body, the same on every slide
KPI_MIN_H = 1.1  # inches
SHORT_EM = 30  # boxes with at most this much text (in em) are "short": four of them stay in one row
DENSE_TIGHT = 0.7  # gap / padding factor on dense slides
_SCALES = [round(1.0 - 0.05 * i, 2) for i in range(15)]  # 1.0 .. 0.3


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
    head_grow: bool = False  # very sparse boxes: box headings grow with ``grow`` (up to ``GROW_HEAD``)
    grew: bool = False  # set when ``grow`` actually scaled some text
    fill: float | None = None  # natural content height / grid height of the slide-level grid, if known
    expand: int = 0  # extra height (EMU) the capped rows of the slide-level grid may take
    roomy: bool = False  # sparse dense slide with a large empty band: tables / trees may take more height
    grow_base: float = (
        1.0  # roomy pass: the growth before it; text that would wrap more at ``grow`` is refused
    )
    out: list[Placed] = field(default_factory=list)
    over: list[str] = field(default_factory=list)
    diags: list[Diagnostic] = field(default_factory=list)

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
    size = t.sizes.get(key, t.sizes.get("body", 18))
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
    if ctx.tight >= 1.0 or st.padding is None:
        return st
    try:
        pt = to_emu(st.padding) / EMU_PER_PT
    except ValueError:
        return st
    return st.merged(Style(padding=f"{round(pt * ctx.tight, 2)}pt"))


def _text_style(ctx: _Ctx, el: Text | Shape, inherit: Style) -> Style:
    role = el.role if isinstance(el, Text) else "shape"
    if role == "shape":
        t = ctx.theme
        st = Style(
            font=t.fonts.body,
            font_ea=t.fonts.ea,
            font_size=t.sizes.get("body", 18) * ctx.dense_k,
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
    st = st.merged(*_class_styles(ctx, el), el.style)
    if isinstance(el, Text) and "callout" in el.classes and not (el.style and el.style.fill):
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
    """Autofit scale ``eff`` times the sparse-grid growth for body text inside boxes."""
    if ctx.grow > 1.0 and ctx.depth > 0 and ctx.scale >= 1.0 and isinstance(el, Text):
        if el.role == "body" and "callout" not in el.classes:
            ctx.grew = True
            return eff * ctx.grow
    return eff


def _text_need(ctx: _Ctx, el: Text | Shape, style: Style, width: int, scale: float) -> float:
    pad = _pad(style)
    return measure.paragraphs_height(el.paragraphs, width - 2 * pad, style, scale) + 2 * pad


def _natural_height(ctx: _Ctx, el, width: int, inherit: Style) -> int | None:
    """Natural height for stackable elements, ``None`` for flexible ones."""
    if isinstance(el, Text):
        st = _text_style(ctx, el, inherit)
        eff = _grown(ctx, el, measure.effective_scale(st.font_size or 18, ctx.scale, ctx.theme.min_font_size))
        return round(_text_need(ctx, el, st, width, eff))
    if isinstance(el, Code):
        st = _code_style(ctx, el)
        eff = _code_eff(ctx, st)
        pad = _pad(st)
        return round(measure.code_height(el.text, width - 2 * pad, (st.font_size or 14) * eff) + 2 * pad)
    if isinstance(el, Table):
        _, _, _, _, rh = _table_geom(ctx, el, width)
        return sum(rh)
    return None


def _code_eff(ctx: _Ctx, st: Style) -> float:
    """Code font scale: the autofit scale, times the sparse-slide growth (at most ``CODE_GROW``)."""
    eff = measure.effective_scale(st.font_size or 14, ctx.scale, ctx.theme.min_font_size)
    if ctx.grow > 1.0 and ctx.scale >= 1.0:
        ctx.grew = True
        eff *= min(ctx.grow, CODE_GROW)
    return eff


def _code_style(ctx: _Ctx, el: Code) -> Style:
    t = ctx.theme
    st = Style(
        font=t.fonts.mono,
        font_ea=t.fonts.ea,
        font_size=t.sizes.get("code", 14) * ctx.dense_k,
        color="fg",
        fill="surface",
        padding="8pt",
        valign="top",
        align="left",
    )
    return _tighten(ctx, st.merged(*_class_styles(ctx, el), el.style))


def _table_style(ctx: _Ctx, el: Table) -> Style:
    t = ctx.theme
    st = Style(
        font=t.fonts.body,
        font_ea=t.fonts.ea,
        font_size=t.sizes.get("table", 14) * ctx.dense_k,
        color="fg",
        align="left",
        valign="middle",
    )
    return st.merged(*_class_styles(ctx, el), el.style)


def _table_grow(ctx: _Ctx) -> float:
    return TABLE_GROW_ROOMY if ctx.roomy else TABLE_GROW


def _table_geom(ctx: _Ctx, el: Table, width: int):
    st = _table_style(ctx, el)
    eff = measure.effective_scale(st.font_size or 14, ctx.scale, ctx.theme.min_font_size)
    if ctx.grow > 1.0 and ctx.scale >= 1.0:  # sparse slide: table text grows too (less than box text)
        eff *= min(ctx.grow, TABLE_FONT_GROW)
        ctx.grew = True
    nrows, ncols, anchors = table_grid(el)
    size = (st.font_size or 14) * eff
    b = getattr(el, "box", None)
    if ctx.depth == 0 and width > FULL_WIDTH * ctx.W and not (b is not None and b.w is not None):
        width = capped_width(el, ncols, anchors, width, size)  # a few short columns: numbers stay near labels
    cw = column_widths(el, ncols, anchors, width, size)
    rh = row_heights(el, anchors, cw, st, eff)
    return st, eff, anchors, cw, rh


def _place_block(ctx: _Ctx, el, rect: Rect, inherit: Style) -> None:
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
        ctx.emit(el, rect, st, eff)
    elif isinstance(el, Code):
        st = _code_style(ctx, el)
        eff = _code_eff(ctx, st)
        pad = _pad(st)
        need = measure.code_height(el.text, rect.w - 2 * pad, (st.font_size or 14) * eff) + 2 * pad
        if need > rect.h * _TOL:
            ctx.over.append(_label(el))
        ctx.emit(el, Rect(rect.x, rect.y, rect.w, min(round(need), rect.h)), st, eff)
    elif isinstance(el, Table):
        st, eff, _anchors, cw, rh = _table_geom(ctx, el, rect.w)
        if not rh or not cw:  # an empty table places nothing
            return
        total = sum(rh)
        if total > rect.h * _TOL:
            ctx.over.append(_label(el))
        elif rect.h > total:  # spare room: rows grow up to TABLE_GROW, cell text stays centered
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
            font=t.fonts.body, font_ea=t.fonts.ea, font_size=t.sizes.get("table", 14), color="fg"
        ).merged(el.style)
        ctx.emit(el, rect, st)
    elif isinstance(el, (Image, Media)):
        ctx.emit(el, rect, Style().merged(*_class_styles(ctx, el), el.style))
    elif isinstance(el, Raw):
        t = ctx.theme
        st = Style(
            font=t.fonts.body,
            font_size=t.sizes.get("caption", 12),
            color="muted",
            fill="surface",
            line="border",
            align="center",
            valign="middle",
        ).merged(el.style)
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
    body = ctx.theme.sizes.get("body", 18) * ctx.dense_k
    size = body * MATH_GROW * ctx.scale
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
        base = ctx.theme.classes.get(
            "card", Style(fill="surface", line="border", line_width=0.75, radius=6, padding="10pt")
        )
    others = _class_styles(ctx, c, skip=("plain", "kpi"))
    return _tighten(ctx, Style().merged(base, *others, c.style))


def _heading_parts(ctx: _Ctx, c: Container, pad: int, kpi: bool):
    """(heading element, merged style, autofit scale, band fill) of a box, or ``None`` without a heading."""
    if c.title is None or not c.title.paragraphs:
        return None
    band = None if kpi else ctx.theme.heading_band
    h_el = c.title if c.title.role == "heading" else c.title.model_copy(update={"role": "heading"})
    hst = _text_style(ctx, h_el, Style())
    if kpi:
        body_size = ctx.theme.sizes.get("body", 18) * ctx.dense_k
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
        eff *= min(ctx.grow, GROW_HEAD)
    return h_el, hst, eff, band


def _icon_name(el) -> str | None:
    """The valid icon name of ``icon=name`` on a box / chevron (unknown names are ignored here)."""
    name = getattr(el, "attrs", {}).get("icon")
    name = str(name).strip().lower() if name else ""
    return name if name and icons.path(name) else None


def _icon_item(name: str) -> Shape:
    return Shape(shape="icon", attrs={"icon": name})


def _icon_side(hst: Style, eff: float, kpi: bool) -> tuple[int, int]:
    """(icon side, space the icon takes left of the heading text) in EMU."""
    side = round((ICON_KPI if kpi else ICON_HEAD) * (hst.font_size or 18) * eff * EMU_PER_PT)
    return side, side + round(ICON_GAP * side)


def _place_container(ctx: _Ctx, c: Container, rect: Rect, inherit: Style) -> None:
    style = _card_style(ctx, c)
    pad = _pad(style, 10 * EMU_PER_PT * ctx.tight)
    if "diagram" in c.classes and c.title is None:
        from .diagram import place_diagram  # flowcharts size and route their own nodes

        if place_diagram(ctx, c, rect.inset(pad), inherit.merged(_only_inheritable(style))):
            return
    ctx.emit(c, rect, style)
    inner = rect.inset(pad)
    y = inner.y
    child_inherit = inherit.merged(_only_inheritable(style))
    kpi = "kpi" in c.classes
    if parts := _heading_parts(ctx, c, pad, kpi):
        h_el, hst, eff, band = parts
        icon = _icon_name(c)
        isz, shift = _icon_side(hst, eff, kpi) if icon else (0, 0)
        if icon and kpi:  # icon centered above the label and the number
            isz = min(isz, inner.w)
            ctx.emit(
                _icon_item(icon), Rect(inner.x + (inner.w - isz) // 2, y, isz, isz), Style(fill="primary")
            )
            y += isz + round(pad * 0.4)
            shift = 0
        if icon and band:
            shift = pad + isz  # the text's own padding supplies the gap after the icon
        if band:
            hh = round(_text_need(ctx, h_el, hst, rect.w - shift, eff))
            if icon:
                hh = max(hh, isz + 2 * pad)
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
            hh = round(_text_need(ctx, h_el, hst, inner.w - shift, eff))
            if icon and not kpi:
                hh = max(hh, isz)
                ctx.emit(_icon_item(icon), Rect(inner.x, y, isz, isz), Style(fill=hst.color or "primary"))
            if hh > inner.h * _TOL:
                ctx.over.append(_label(c))
            ctx.emit(h_el, Rect(inner.x + shift, y, inner.w - shift, min(hh, inner.h)), hst, eff)
            y += hh + round(pad * 0.5)
    area = Rect(inner.x, y, inner.w, max(inner.bottom - y, 0))
    if not c.children:
        return
    gap = _gap(ctx, c.gap, inner.w, small=True)
    children = c.children
    if kpi:
        children = _kpi_children(ctx, children, area.w)
    saved = (ctx.depth, ctx.grow)
    ctx.depth += 1
    if kpi:
        ctx.grow = 1.0
    try:
        if c.grid or any(n in ("flow", "chevron") for n in c.classes):
            _place_blocks(ctx, children, area, child_inherit, c.grid, c.classes, gap, c, c.links)
        else:
            rects = _place_stack(
                ctx, children, area, child_inherit, gap, c, center=kpi and len(children) == 1
            )
            _emit_links(ctx, c.links, rects)
    finally:
        ctx.depth, ctx.grow = saved


def _box_nat(ctx: _Ctx, c: Container, width: int, inherit: Style) -> int | None:
    """Natural height of a ``##`` box (heading, children, padding); ``None`` if content is flexible."""
    if c.grid or c.links or any(n in ("flow", "chevron") for n in c.classes):
        return None
    style = _card_style(ctx, c)
    pad = _pad(style, 10 * EMU_PER_PT * ctx.tight)
    kpi = "kpi" in c.classes
    total = 2 * pad if c.children or c.title else 0
    if parts := _heading_parts(ctx, c, pad, kpi):
        h_el, hst, eff, band = parts
        icon = _icon_name(c)
        isz, shift = _icon_side(hst, eff, kpi) if icon else (0, 0)
        if icon and kpi:
            isz = min(isz, max(width - 2 * pad, 1))
            total += isz + round(pad * 0.4)
            shift = 0
        if icon and band:
            shift = pad + isz
        if band:
            hh = round(_text_need(ctx, h_el, hst, width - shift, eff))
            total = (max(hh, isz + 2 * pad) if icon else hh) + round(pad * 0.5) + pad
        else:
            hh = round(_text_need(ctx, h_el, hst, width - 2 * pad - shift, eff))
            total += (max(hh, isz) if icon and not kpi else hh) + round(pad * 0.5)
    children = c.children
    if not children:
        return total
    if any(_is_abs(ch) for ch in children):
        return None
    inner_w = max(width - 2 * pad, 1)
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
    return total + sum(nat) + _gap(ctx, c.gap, inner_w, small=True) * (len(nat) - 1)


def _kpi_children(ctx: _Ctx, children: list, width: int) -> list:
    """The first text child of a ``.kpi`` box: paragraph 0 = big number, the rest = muted caption."""
    i = next((k for k, c in enumerate(children) if isinstance(c, Text) and c.paragraphs), None)
    if i is None:
        return children
    ch = children[i]
    th = ctx.theme
    big = th.classes.get("kpi", Style(font_size=36, bold=True, color="primary", align="center"))
    cap = Style(font_size=th.sizes.get("caption", 12), color="muted", align="center", bold=False)
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
    else:  # spare room goes to tables (rows grow up to TABLE_GROW), everything else stays natural and on top
        tabs = [k for k, (_i, ch) in enumerate(flow) if isinstance(ch, Table)]
        spare = area.h - fixed
        if tabs and spare > 0:
            share = spare / len(tabs)
            for k in tabs:
                nat[k] = round((nat[k] or 0) + min(share, (nat[k] or 0) * (_table_grow(ctx) - 1)))
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
    limit = GROW_BOX_FILL if ctx.grow > 1.0 and ctx.depth > 0 else _TOL  # grown text keeps some headroom
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
        ctx.emit(Shape(shape="line", attrs=attrs), rect, Style(line="primary", line_width=1.5))


def _group_nat(ctx: _Ctx, g: Container, width: int, inherit: Style) -> tuple[int | None, str]:
    """Natural height of a row group (one row of boxes): its tallest box; kind kpi if all boxes are KPIs."""
    kids = [c for c in g.children if isinstance(c, Container)]
    m = re.match(r"\d+", g.grid or "")
    if not kids or len(kids) != len(g.children) or not m or len(kids) > int(m.group()):
        return None, "other"
    gap = _gap(ctx, g.gap, width, small=True)
    w = max((width - gap * (len(kids) - 1)) // len(kids), 1)
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
        nat[r0] = None if n is None or nat[r0] is None else max(nat[r0] or 0, n)
    caps: list[int | None] = []
    for row in range(nr):
        n = nat[row]
        if not covered[row] or n is None or n <= 0:
            caps.append(None)
        elif kinds[row] == {"kpi"}:
            caps.append(max(n, round(KPI_MIN_H * EMU_PER_INCH)))
        elif kinds[row] == {"table"}:
            caps.append(n)
        elif tree:  # org-tree levels hug their boxes (+ modest slack): the connectors fill the gaps
            caps.append(round(n * (TREE_SLACK_ROOMY if ctx.roomy else TREE_SLACK)))
        else:
            lone = nr == 1 and not has_tail and ctx.dense_k < 1.0
            floor = ROW_MIN_TAIL if has_tail else (ROW_MIN_DENSE if lone else ROW_MIN)
            caps.append(max(round(n * ROW_SLACK), round(floor * body.h)))
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
        w = [max(n or 0, STACK_MIN * tot) for n in nat]
        return grid_row_heights(replace(gs, rows=[float(x) for x in w]), grid_area.h, gap, caps)
    if (
        ctx.expand > 0 and nr >= 2 and not tree
    ):  # sparse slide: spread extra height over the capped rows (not kpi / table)
        rows = [r for r in range(nr) if caps[r] is not None and "other" in kinds[r]]
        tot = sum(caps[r] or 0 for r in rows)
        for r in rows:
            caps[r] = (caps[r] or 0) + round(ctx.expand * (caps[r] or 0) / max(tot, 1))
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
    # slide level: callouts are never grid cells, they close the slide body as full-width rows
    callouts: list[tuple[int, object]] = []
    if ctx.depth == 0 and len(flow) > 1:
        callouts = [(i, b) for i, b in flow if isinstance(b, Text) and "callout" in b.classes]
        if len(callouts) == len(flow):
            callouts = []
        flow = [(i, b) for i, b in flow if (i, b) not in callouts]
    gs = parse_spec(grid, len(flow), classes)
    tables: list[tuple[int, object]] = []
    if gs is None or not gs.cols:  # no explicit grid token: infer the arrangement from the blocks
        gs, flow, tables = _auto_plan(flow, gs, classes, links or [])
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
        if text_visual and not isinstance(flow[0][1], Text):
            flow = [flow[1], flow[0]]
        wide = any(isinstance(b, Code) and max(map(len, b.text.split("\n")), default=0) > 45 for _, b in flow)
        gs = auto_spec(len(flow), text_visual=text_visual, short=short, wide_visual=wide)
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
        chev_h = _chevron_row_h(ctx, [b for _, b in flow], min((r.w for r in cells), default=area.w), inherit)
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
        floor = round(BESIDE_MIN * r.h)
        h = round(n * BESIDE_SLACK)
        if h < floor:
            h = round(h + BESIDE_FILL * (floor - h))
        out[k] = Rect(r.x, r.y, r.w, min(h, r.h))
    return out


def _is_diagram(b) -> bool:
    return isinstance(b, Container) and "diagram" in b.classes and b.title is None


def _hug_tail(ctx: _Ctx, start: int, area: Rect, gap: int) -> None:
    """A lone diagram followed by blocks (a callout): the blocks sit right below it, the pair is centered."""
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
    rbot = max(p.y + p.h for p in rest)
    pair = (dbot - top) + gap + (rbot - rtop)
    new_top = area.y + max(area.h - pair, 0) // 2
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
    floor = max(t.sizes.get("body", 18), t.sizes.get("table", 14) * ctx.dense_k * TABLE_FONT_GROW)
    return st.merged(Style(font_size=max(st.font_size or 18, floor)))


def _chevron_geom(
    ctx: _Ctx, blk, rect: Rect, inherit: Style, hcap: int | None = None
) -> tuple[Shape, Style, Rect]:
    sh = _chevron_shape(blk)
    st = _chevron_font(ctx, sh, _text_style(ctx, sh, inherit))
    if hcap is not None:
        rect = Rect(rect.x, rect.y, rect.w, min(rect.h, hcap))
    # the preset text rectangle already starts a point depth inside both ends: add only a small padding
    st = st.merged(Style(padding=f"{CHEVRON_PAD_PT}pt", align="center", valign="middle"))
    if icon := _icon_name(blk):  # the icon sits left of the text: reserve its room as a left inset
        side = min(round(ICON_HEAD * (st.font_size or 18) * EMU_PER_PT), round(0.4 * rect.h))
        sh = sh.model_copy(
            update={
                "attrs": {
                    **sh.attrs,
                    "icon": icon,
                    "icon_side": side,
                    "icon_inset": side + round(ICON_GAP * side),
                }
            }
        )
    return sh, st, rect


def _chevron_text_w(rect: Rect, st: Style, sh: Shape | None = None) -> int:
    """Width of a chevron's text area: the shape minus both point depths, the padding and the icon."""
    inset = sh.attrs.get("icon_inset", 0) if sh is not None else 0
    return rect.w - 2 * round(CHEVRON_ADJ * min(rect.w, rect.h)) - 2 * _pad(st) - inset


def _chevron_row_h(ctx: _Ctx, blocks: list, width: int, inherit: Style) -> int:
    """Height of a chevron row: tallest text + padding, clamped to ``CHEVRON_MIN_H`` .. ``CHEVRON_MAX_H``."""
    lo, hi = round(CHEVRON_MIN_H * EMU_PER_INCH), round(CHEVRON_MAX_H * EMU_PER_INCH)
    h = round(EMU_PER_INCH)
    for _ in range(3):  # the point depth depends on the height, the height on the wrapped text
        need = 0
        for blk in blocks:
            if not isinstance(blk, (Text, Shape, Container)):
                continue
            sh, st, rect = _chevron_geom(ctx, blk, Rect(0, 0, width, h), inherit)
            eff = measure.effective_scale(st.font_size or 18, ctx.scale, ctx.theme.min_font_size)
            need = max(need, measure.paragraphs_height(sh.paragraphs, _chevron_text_w(rect, st, sh), st, eff))
        h = min(max(round(need / 0.8), round(need + 2 * CHEVRON_VPAD * EMU_PER_INCH), lo), hi)
    return h


def _chevron_eff(ctx: _Ctx, blk, rect: Rect, inherit: Style, hcap: int | None = None) -> float:
    """Font scale of a chevron whose wrapping survives a renderer that is ~12% narrower than the estimate.

    A label that just fits would leave a lone character on its last line when the real font is wider (e.g.
    "KPI モニタリン / グ"): shrink until the line count no longer changes in a 12% narrower area (>= 80%).
    """
    sh, st, rect = _chevron_geom(ctx, blk, rect, inherit, hcap)
    width = _chevron_text_w(rect, st, sh)
    base = st.font_size or 18
    first = measure.effective_scale(base, ctx.scale, ctx.theme.min_font_size)
    for m in (1.0, 0.95, 0.9, 0.85, 0.8):
        eff = measure.effective_scale(base, ctx.scale * m, ctx.theme.min_font_size)
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
    eff = measure.effective_scale(st.font_size or 18, ctx.scale, ctx.theme.min_font_size)
    if eff_cap is not None:
        eff = min(eff, eff_cap)
    # centered text may use the middle 80% of the height
    need = measure.paragraphs_height(sh.paragraphs, _chevron_text_w(rect, st, sh), st, eff)
    if need > rect.h * 0.8:
        ctx.over.append(_label(blk))
    ctx.emit(sh, rect, st, eff)
    if "icon_side" in sh.attrs:  # icon just before the (centered) text block, vertically centered
        side = sh.attrs["icon_side"]
        left = rect.x + round(CHEVRON_ADJ * min(rect.w, rect.h)) + _pad(st)
        avail = _chevron_text_w(rect, st, sh)
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
    keep = round(LEFT_KEEP * body.h)
    if left > keep:
        c = run(body, grow=fin.grow, expand=left - keep)
        if not c.over and c.out:
            fin = c
            left = body.bottom - _bottom(fin)
    small_theme = ctx.theme.sizes.get("body", 18) <= GROW_SMALL_PT  # consulting themes (jp-business: 11pt)
    if left >= ROOMY_LEFT * body.h and (
        fin.dense_k < 1.0 or small_theme
    ):  # a quarter of the body stays empty
        for f in (ROOMY_GROW, 1.15, 1.1, 1.05, 1.0):  # tables / trees take more height, text grows a little
            c = run(body, grow=round(fin.grow * f, 2), expand=fin.expand, roomy=True, grow_base=fin.grow)
            if not c.over and c.out and _bottom(c) > _bottom(fin):
                fin = c
                left = body.bottom - _bottom(fin)
                break
    top = min((p.y for p in fin.out), default=body.y)
    if _bottom(fin) - top < VERY_SPARSE_FILL * body.h:
        dy = round(
            left * (LEFT_SHIFT if any(isinstance(e, Container) for e in elements) else LEFT_SHIFT_TABLE)
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


def layout_slide(slide: Slide, deck: Deck, theme: Theme, index: int) -> list[Placed]:
    """Return every visible item of ``slide`` (title included) in z-order, with final boxes and merged styles.

    ``index`` is the 0-based slide index (used for footer / slide number items).
    Problems (overflow, unknown layout, ...) are appended to ``deck.diagnostics``.
    """
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
    ctx = _Ctx(deck, theme, slide, index, W, H)
    dense = deck.density == "dense" or "dense" in slide.classes
    ctx.dense_k = theme.dense_scale if dense else 1.0
    ctx.tight = DENSE_TIGHT if dense else 1.0

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
            put(head, slide.title, r, st.merged(slide.title.style), fit_text(slide.title, r, st))
        sub = slide.subtitle or slide.lead
        if sub:
            st = _role_style(ctx, "subtitle", cover=True)
            if theme.title_band:
                st = st.merged(Style(color=theme.title_band_color))
            r = Rect(Mx, by + round(band_h * 0.68), inner_w, round(band_h * 0.3))
            st = st.merged(Style(valign="top"), sub.style)
            put(head, sub, r, st, fit_text(sub, r, st))
        body = Rect(Mx, by + band_h + sg, inner_w, H - (by + band_h + sg) - My) if slide.elements else None
        y_top = 0
    else:
        y = My
        head_bottom: int | None = (
            None  # bottom of the title band / title / lead: the body starts TOP_GAP below
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
            st = st.merged(slide.title.style)
            put(head, slide.title, r, st, fit_text(slide.title, r, st))
        for role, el in (("subtitle", slide.subtitle), ("lead", slide.lead)):
            if kind == "blank" or el is None or not el.paragraphs:
                continue
            st = _role_style(ctx, role).merged(*_class_styles(ctx, el), el.style)
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
        y_top = y if head_bottom is None else head_bottom + round(TOP_GAP * EMU_PER_INCH)
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
            sts = [_role_style(ctx, "footnote").merged(f.style) for f in notes]
            max_h = round(H * 0.2)
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
            st = _role_style(ctx, "conclusion").merged(*_class_styles(ctx, c), c.style)
            h = max(round(_text_need(ctx, c, st, inner_w, 1.0)), round(0.4 * EMU_PER_INCH))
            h = min(h, round(H * 0.2))
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
        if kind == "center":
            slide_inherit = slide_inherit.merged(Style(align="center", valign="middle"))
        sgap = _gap(ctx, slide.attrs.get("gap"), body.w)

        body_pt = theme.sizes.get("body", 18) * ctx.dense_k
        very = body_pt >= GROW_VERY_SPARSE_PT and _very_sparse(elements)

        def run(area: Rect, **kw) -> _Ctx:
            c = _Ctx(
                deck, theme, slide, index, W, H, dense_k=ctx.dense_k, tight=ctx.tight, head_grow=very, **kw
            )
            _place_blocks(
                c, elements, area, slide_inherit, slide.grid, slide.classes, sgap, None, slide.links
            )
            return c

        for s in _SCALES:
            final_ctx = run(body, scale=s)
            if not final_ctx.over:
                break
        assert final_ctx is not None
        if final_ctx.scale >= 1.0 and not final_ctx.over:
            # sparse slide: grow text uniformly (siblings share one factor), more for small themes
            top = GROW_SMALL if (body_pt <= GROW_SMALL_PT) else GROW_BIG
            if ctx.dense_k < 1.0:  # dense slides: up to DENSE_GROW_BODY x the theme body size
                top = max(top, DENSE_GROW_BODY / ctx.dense_k)
            if very:
                top = max(top, min(GROW_VERY_SPARSE, GROW_VERY_SPARSE_MAX_PT / body_pt))
            n = round((top - 1.05) / 0.05)
            for g in [round(top - 0.05 * i, 2) for i in range(n + 1)]:
                c3 = run(body, grow=g)
                if c3.grew and not c3.over and (c3.fill is None or c3.fill <= GROW_FILL):
                    final_ctx = c3
                    break
            final_ctx = _spread(ctx, final_ctx, run, body, elements)
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

    deck.diagnostics.extend(ctx.diags)
    return head + (final_ctx.out if final_ctx else []) + tail
