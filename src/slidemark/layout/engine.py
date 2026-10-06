"""Layout engine: ``Slide`` -> ``list[Placed]`` in absolute EMU. Never touches python-pptx."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field, replace

from .. import icons
from ..ir import (
    Box,
    Cell,
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
    fast_style,
)
from ..template import footer_top
from ..theme import DEFAULT_SIZES, LayoutTokens, Theme, _base_classes
from ..units import EMU_PER_INCH, EMU_PER_PT, slide_size, to_emu
from . import css, measure
from .chartnote import expand_notes, scale_warning
from .diagram import fill_tree
from .gantt import expand_gantt
from .grid import GridSpec, Rect, auto_spec, cell_rects, parse_spec, tree_areas
from .grid import row_heights as grid_row_heights
from .l3fill import (
    _body_items,
    align_chevron_table,
    center_band,
    fill_cards_to_bar,
    fill_chevron_row,
    fill_panels,
    fill_row,
    fill_steps,
    fit_lone_kpi,
    grow_chevron_table,
    scale_kpi_values,
)
from .pills import expand_pills, has_pills
from .score import score as score_layout
from .search import alternatives
from .sparsefill import fill_table_free, fill_text_list, lone_table
from .tables import capped_width, column_widths, right_align_numbers, row_heights, table_grid
from .vfill import fill_body

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
_SPAN_BLOCKS = (Image, Media, Chart, Code, Raw)  # a lone one after a full box row spans the width
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
    tgrow: float = 1.0  # extra table text growth of a table that has room (``_table_text``)
    twrap: bool = False  # ``_table_text`` wrap pass: the extra table growth may wrap cells at a space
    step: float = 1.0  # sparse step: padding, table / chevron text and paragraph gaps scale with it
    chev_adj: float | None = None  # point depth / shorter side of the chevron row being placed (None = token)
    chev_grow: float = 1.0  # a chevron row alone on the slide: its text grows with ``grow``
    steps_row: bool = False  # the chevron row being placed is the arrow row of an ``@steps`` slide
    fill: float | None = None  # natural content height / grid height of the slide-level grid, if known
    expand: int = 0  # extra height (EMU) the capped rows of the slide-level grid may take
    arrange: str | None = None  # layout search: a grid token that replaces the rule-based arrangement
    alts: list[str] = field(default_factory=list)  # layout search: alternative tokens for this slide
    cap_tables: bool = True  # False when another block (box row, chart, ...) spans the body: no narrow table
    lone_air: float = (
        0.0  # normal-density balance: a lone box row may reach this multiple of its natural height
    )
    roomy: bool = False  # sparse dense slide with a large empty band: tables / trees may take more height
    grow_base: float = (
        1.0  # roomy pass: the growth before it; text that would wrap more at ``grow`` is refused
    )
    air: float = 0.0  # sparse completion: paragraph gap (em) of plain body text, KPI cards grow with ``grow``
    kpi_air: float = 1.0  # sparse completion: KPI rows may be this many times their natural height
    chev_air: bool = False  # sparse completion: a chevron row alone may be taller
    completed: bool = False  # the sparse completion laid this slide out: the vertical fill keeps it as is
    band_h: dict[tuple[int, int], int] = field(
        default_factory=dict
    )  # (box id, box width) -> heading height shared by the boxes of one row
    gaps: dict[int, float] = field(default_factory=dict)  # text id -> paragraph gap (em) of a roomy card
    text_out: dict[int, int] = field(default_factory=dict)  # text id -> index of its Placed in ``out``
    boxes: dict[int, list[int]] = field(default_factory=dict)  # box id -> ids of its spreadable texts
    centered: set[int] = field(
        default_factory=set
    )  # card ids whose content is centered (row pinned by a visual)
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


_ROLE_CACHE: dict = {}


def _role_style(ctx: _Ctx, role: str, cover: bool = False) -> Style:
    """Theme style of a text role (memoised per theme: Styles are never mutated, only merged into copies)."""
    key = (id(ctx.theme), role, cover, ctx.dense_k)
    hit = _ROLE_CACHE.get(key)
    if hit is None or hit[0] is not ctx.theme:
        if len(_ROLE_CACHE) > 512:
            _ROLE_CACHE.clear()
        hit = _ROLE_CACHE[key] = (ctx.theme, _role_style0(ctx, role, cover))
    return hit[1]


def _role_style0(ctx: _Ctx, role: str, cover: bool = False) -> Style:
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
    st = fast_style(
        font=t.fonts.heading if heading_font else t.fonts.body,
        font_ea=t.fonts.ea,
        font_size=size,
        color="fg",
        align="left",
        valign="top",
    )
    if role == "title":
        st = st.merged(fast_style(bold=True, color=t.title_color, valign="middle"))
    elif role == "heading":
        st = st.merged(fast_style(bold=True, color=t.heading_color))
    elif role == "subtitle":
        st = st.merged(fast_style(color="muted"))
    elif role == "lead":
        st = st.merged(fast_style(color=t.lead_color))
    elif role == "quote":
        st = st.merged(fast_style(italic=True, color="muted"))
    elif role in ("footnote", "caption"):
        st = st.merged(fast_style(color="muted"))
    elif role == "conclusion":
        st = st.merged(
            fast_style(
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
        if name in skip or (
            name == "gantt" and isinstance(el, Table)
        ):  # the bars carry the look, not the grid
            continue
        if name == "muted" and isinstance(el, Container):  # a muted box: border + band, body keeps its ink
            out.append(ctx.theme.classes.get("muted-box") or ctx.theme.classes["muted"])
        elif name in ctx.theme.classes:
            out.append(ctx.theme.classes[name])
        elif name in ctx.theme.colors and name not in ("bg", "fg", "surface", "border"):
            if isinstance(el, Container):
                out.append(fast_style(line=name))
            elif isinstance(el, Shape):
                out.append(fast_style(fill=name))
            else:
                out.append(
                    fast_style(color=ctx.theme.legible(name))
                )  # `.primary` text: readable shade if needed
    return out


def _styled(ctx: _Ctx, el, st: Style, classes: bool = True) -> Style:
    """``st`` (theme role) -> inherited CSS -> theme classes -> CSS rules -> inline style."""
    own = ctx.css.own(el)
    out = st.merged(
        ctx.css.inherited(el), *(_class_styles(ctx, el) if classes else ()), own, getattr(el, "style", None)
    )
    if own.line_width and not out.line:  # `border: 2px` without a color: the border color token
        out = out.merged(fast_style(line="border"))
    return out


def _cstyle(ctx: _Ctx, el) -> Style:
    """Classes + CSS + inline of ``el`` only (margin, gap, grid, rotation lookups)."""
    return fast_style().merged(*_class_styles(ctx, el), ctx.css.own(el), getattr(el, "style", None))


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
    return _scale_pad(st, ctx.tight)


def _scale_pad(st: Style, k: float) -> Style:
    """``st`` with every padding multiplied by ``k``."""
    if k == 1.0:
        return st
    upd = {}
    for f in ("padding", "padding_top", "padding_right", "padding_bottom", "padding_left"):
        v = getattr(st, f)
        if v is None:
            continue
        try:
            upd[f] = f"{round(to_emu(v) / EMU_PER_PT * k, 2)}pt"
        except ValueError:
            continue
    return st.merged(fast_style(**upd)) if upd else st


def _text_style(ctx: _Ctx, el: Text | Shape, inherit: Style) -> Style:
    role = el.role if isinstance(el, Text) else "shape"
    if role == "shape":
        t = ctx.theme
        st = fast_style(
            font=t.fonts.body,
            font_ea=t.fonts.ea,
            font_size=t.sizes.get("body", DEFAULT_SIZES["body"]) * ctx.dense_k,
            color=None,  # auto ink on the fill below, unless the deck sets a color
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
    if role == "shape" and st.color is None:
        st = st.merged(fast_style(color=ctx.theme.ink_on(st.fill, "bg")))  # `bg` unless it fails on the fill
    if (
        isinstance(el, Text)
        and "callout" in el.classes
        and not (el.style and el.style.fill)
        and not ctx.css.own(el).fill
    ):
        kind = next((k for k in _CALLOUT_KINDS if k in el.classes), None)
        if kind and (tint := _tint(ctx.theme, st.line)):
            st = st.merged(fast_style(fill=tint))
    st = _tighten(ctx, st)
    if isinstance(el, Text) and "callout" in el.classes:
        st = _callout_floor(ctx, st)
    return st


def _callout_floor(ctx: _Ctx, st: Style) -> Style:
    """A callout keeps ``callout_pad_min`` padding on every side and text at least as large as a footnote."""
    floor = to_emu(ctx.lt.callout_pad_min) / EMU_PER_PT
    upd: dict = {}
    for f in ("padding", "padding_top", "padding_right", "padding_bottom", "padding_left"):
        v = getattr(st, f)
        if v is None:
            continue
        try:
            if to_emu(v) / EMU_PER_PT < floor:
                upd[f] = f"{floor}pt"
        except ValueError:
            continue
    if all(
        getattr(st, f) is None
        for f in ("padding", "padding_top", "padding_right", "padding_bottom", "padding_left")
    ):
        upd["padding"] = f"{floor}pt"
    small = ctx.theme.sizes.get("footnote", DEFAULT_SIZES["footnote"])
    if st.font_size is not None and st.font_size < small:
        upd["font_size"] = small
    st = st.merged(fast_style(**upd)) if upd else st
    if ctx.depth > 0:  # inside a box: roomier, and the text clears the accent bar
        box = max(to_emu(ctx.lt.callout_box_pad), to_emu(ctx.lt.callout_pad_min))
        bar = to_emu(ctx.lt.callout_bar_w)
        left, top, right, bottom = css.insets(st)
        st = st.merged(
            fast_style(
                padding_left=f"{max(left, box + bar) / EMU_PER_PT}pt",
                padding_top=f"{max(top, box) / EMU_PER_PT}pt",
                padding_right=f"{max(right, box) / EMU_PER_PT}pt",
                padding_bottom=f"{max(bottom, box) / EMU_PER_PT}pt",
            )
        )
    return st


def _only_inheritable(s: Style) -> Style:
    d = s.__dict__
    return fast_style(**{k: v for k, v in d.items() if k in _INHERIT_FIELDS and v is not None})


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


def _css_width(ctx: _Ctx, el, r: Rect, inherit: Style) -> Rect:
    """CSS ``width`` of a block in the flow: fixed (``40%``, ``3in``) or ``fit-content`` (a text hugs its
    longest line + padding). The block keeps the cell's left edge, or moves per ``text-align``."""
    if not ctx.css.active:
        return r
    st = ctx.css.own(el)
    if not st.width or st.width == "auto" or (getattr(el, "box", None) is not None and el.box.w is not None):
        return r
    if st.width == "fit-content":
        if not isinstance(el, Text) or not el.paragraphs:
            return r
        ts = _text_style(ctx, el, inherit)
        size = (ts.font_size or 18) * ctx.scale
        em = max(measure.text_em(p.plain, bold=bool(ts.bold)) for p in el.paragraphs)
        pl, _, pr, _ = css.insets(ts, 0)
        w = round(em * size * 1.08 * EMU_PER_PT) + pl + pr
    else:
        w = _len(ctx, st.width, r.w, el)
        if w is None:
            return r
    w = max(min(w, r.w), 1)
    dx = {"center": (r.w - w) // 2, "right": r.w - w}.get(_text_style(ctx, el, inherit).align or "left", 0)
    return Rect(r.x + dx, r.y, w, r.h)


def _cover_explicit(ctx: _Ctx, *els) -> bool:
    """The author styled the cover text (``{size=}``, CSS rule): the automatic cover composition stays off."""
    for el in els:
        if el is None:
            continue
        if _explicit_size(ctx, el) or (ctx.css.active and ctx.css.own(el) != fast_style()):
            return True
    return False


def _grow_cover_title(ctx: _Ctx, el: Text, st: Style, rect: Rect, eff: float) -> float:
    """Largest scale (up to the ``cover_title_max_pt`` token) at which the title keeps its line count, breaks
    no word and fits its area: the title fills the band width instead of sitting small in a corner."""
    size = st.font_size or 44
    top = ctx.lt.cover_title_max_pt / size
    if top <= eff + 1e-6 or eff < 1.0 - 1e-6:  # autofit already shrank it: leave it
        return eff
    huge = 10**9
    ph, _pv = css.inset_hv(st)
    avail = rect.w - ph

    def lines(scale: float, width: int) -> float:
        return _text_need(ctx, el, st, width, scale) / max(_text_need(ctx, el, st, huge, scale), 1)

    def breaks_word(scale: float) -> bool:
        pt = size * scale
        for par in el.paragraphs:
            for run in par.runs:
                for w in run.text.split():
                    if not measure.has_cjk(w) and measure.text_em(w, bold=True) * pt > avail / EMU_PER_PT:
                        return True
        return False

    base = lines(eff, rect.w)
    s = top
    while s > eff + 1e-6:
        if (
            lines(s, rect.w) <= base + 0.05
            and _text_need(ctx, el, st, rect.w, s) <= rect.h * _TOL
            and not breaks_word(s)
        ):
            return s
        s -= 0.05
    return eff


def _fit(ctx: _Ctx, need_fn, avail: int, base_size: float) -> float:
    """Smallest-effort local autofit scale for a standalone element (title, lead, ...)."""
    for s in _SCALES:
        eff = measure.effective_scale(base_size, s, ctx.theme.min_font_size)
        if need_fn(eff) <= avail * _TOL:
            return eff
    return measure.effective_scale(base_size, 0.0, ctx.theme.min_font_size)


# --------------------------------------------------------------------------- element placement


def _explicit_size(ctx: _Ctx, el) -> bool:
    """The author set the font size of ``el`` (CSS rule, ``{size=}``, element style): it never grows."""
    if getattr(getattr(el, "style", None), "font_size", None) is not None:
        return True
    return bool(ctx.css.active and ctx.css.own(el).font_size is not None)


def _grown(ctx: _Ctx, el, eff: float) -> float:
    """Autofit scale ``eff`` times the sparse-grid growth for body text inside boxes.

    A CSS ``font-size`` is explicit: it is never grown (autofit may still shrink it)."""
    if _explicit_size(ctx, el):
        return eff
    if ctx.grow > 1.0 and (ctx.depth > 0 or ctx.text_only) and ctx.scale >= 1.0 and isinstance(el, Text):
        if el.role == "body" and "callout" not in el.classes:
            ctx.grew = True
            return eff * ctx.grow
        if "callout" in el.classes and ctx.depth > 0 and ctx.lt.callout_text_step > 0:
            # a note inside a box follows the box text: at most one step smaller
            base = max(_text_style(ctx, el, fast_style()).font_size or 18, 1.0)
            box_pt = ctx.theme.sizes.get("body", DEFAULT_SIZES["body"]) * ctx.dense_k * ctx.grow
            f = min(max(box_pt / ctx.lt.callout_text_step / base, 1.0), ctx.grow)
            if f > 1.0:
                ctx.grew = True
                return eff * f
    elif (
        ctx.grow > 1.0
        and ctx.depth == 0
        and ctx.scale >= 1.0
        and isinstance(el, Text)
        and el.role == "body"
        and "callout" not in el.classes
        and (_has_box_text(ctx) or _has_kpi_row(ctx))
    ):  # slide-level text beside grown boxes: at most one step smaller than their body text
        base = max(_text_style(ctx, el, fast_style()).font_size or 18, 1.0)
        box_pt = ctx.theme.sizes.get("body", DEFAULT_SIZES["body"]) * ctx.dense_k * ctx.grow
        peer = 1.0 if _has_kpi_row(ctx) and not _has_box_text(ctx) else ctx.lt.slide_peer_step
        f = min(max(box_pt / peer / base, 1.0), ctx.grow)
        if f > 1.0:
            ctx.grew = True
            return eff * f
    return eff


def _base_gap(ctx: _Ctx) -> float:
    """Paragraph gap (em) of a card paragraph before any spreading: wider at the sparse step."""
    return max(measure.para_gap(), ctx.lt.sparse_para_gap) if ctx.step > 1.0 else measure.para_gap()


def _para_gap(ctx: _Ctx, el) -> float | None:
    """The paragraph gap (em) chosen for ``el`` (spread or sparse step), ``None`` = the default gap."""
    g = ctx.gaps.get(id(el))
    if ctx.air > 0 and ctx.depth == 0 and ctx.scale >= 1.0 and _spreadable(el):
        return max(g or 0.0, _base_gap(ctx), ctx.air)
    if g is None and ctx.step > 1.0 and ctx.depth > 0 and ctx.scale >= 1.0 and _spreadable(el):
        return _base_gap(ctx)
    return g


def _text_need(ctx: _Ctx, el: Text | Shape, style: Style, width: int, scale: float) -> float:
    ph, pv = css.inset_hv(style)
    gap = _para_gap(ctx, el)
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
    st = fast_style(
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


def _gantt_style(ctx: _Ctx, table: Placed) -> Style:
    """Style of the bars of a placed ``.gantt`` table: the table text (font, size), the ``gantt`` theme class
    (tokens ``style: gantt.*``) and the deck CSS rules that match ``.gantt``; the ink is chosen for contrast
    on the bar fill unless one is set."""
    t = table.style
    st = fast_style(font=t.font, font_ea=t.font_ea, font_size=t.font_size, bold=t.bold)
    st = st.merged(ctx.theme.classes.get("gantt") or fast_style(fill="primary"))
    tn = ctx.css.node(table.element)
    if tn is not None:
        bar = css.Node(frozenset({"shape"}), frozenset({"gantt"}), "other", None, tn)
        ctx.css._compute(bar)
        st = st.merged(bar._own or fast_style())
    if st.color is None:
        st = st.merged(fast_style(color=ctx.theme.ink_on(st.fill, "bg")))
    return st


def _pill_style(ctx: _Ctx, table: Placed, cell: Cell) -> Style:
    """Style of the pill that replaces the badge of a table cell: the cell text (font, size), the ``pill``
    theme class (tokens ``style: pill.*``) and the deck CSS rules that match ``.pill``. Fill and ink follow
    the badge unless a rule sets them."""
    t = table.style.merged(cell.style) if cell.style else table.style
    st = fast_style(font=t.font, font_ea=t.font_ea, font_size=t.font_size)
    st = st.merged(ctx.theme.classes.get("pill") or fast_style())
    tn = ctx.css.node(table.element)
    if tn is not None:
        pill = css.Node(frozenset({"shape"}), frozenset({"pill"}), "other", None, tn)
        ctx.css._compute(pill)
        st = st.merged(pill._own or fast_style())
    return st


def _table_style(ctx: _Ctx, el: Table) -> Style:
    t = ctx.theme
    st = fast_style(
        font=t.fonts.body,
        font_ea=t.fonts.ea,
        font_size=t.sizes.get("table", DEFAULT_SIZES["table"]) * ctx.dense_k,
        color="fg",
        align="left",
        valign="middle",
    )
    return _styled(ctx, el, st)


def _cells_sized(el: Table) -> bool:
    return any(c.style is not None and c.style.font_size is not None for row in el.rows for c in row)


def _table_size_explicit(ctx: _Ctx, el: Table) -> bool:
    """The author fixed the table text size (``sizes: table=``, CSS, ``{size=}``): it never grows further."""
    if "sizes.table" in (ctx.deck.tokens or {}) or _explicit_size(ctx, el):
        return True
    return _cells_sized(ctx.css.table(el))  # CSS td / th font-size and {size=} on a cell


def _tables_alone(ctx: _Ctx) -> bool:
    """Roomy pass of a normal-density slide that holds nothing but tables: they may grow more."""
    return ctx.roomy and not _consulting(ctx) and all(isinstance(e, Table) for e in ctx.slide.elements)


def _table_grow(ctx: _Ctx) -> float:
    if _tables_alone(ctx):
        return ctx.lt.table_alone_grow
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


def _kpi_grow(ctx: _Ctx, grow: float, box: Container | None = None, width: int | None = None) -> float:
    """Growth of the text inside a ``.kpi`` card: none, except next to free body text on a sparse slide.

    The sparse completion (``ctx.air``) also grows a KPI row that stands alone, unless the author set the
    size (``{size=}`` on the card, a CSS rule on ``.kpi``). Growth never makes a number wrap: it is capped
    so the widest number of the row still fits one line with a safety margin."""
    if ctx.lt.kpi_grow_max <= 1.0:
        return 1.0
    g = min(max(grow, 1.0), ctx.lt.kpi_grow_max)
    if not _has_kpi_text(ctx) and (ctx.air <= 0 or _kpi_explicit(ctx, box)):
        return 1.0
    return max(min(g, _kpi_fit(ctx, box, width)), 1.0) if width else g


def _kpi_row_em(ctx: _Ctx, box: Container | None, own: float) -> float:
    """Em width of the widest number among the KPI cards of the slide (one size per row)."""
    best = own
    for e in ctx.slide.elements:
        if isinstance(e, Container) and "kpi" in e.classes:
            t = next((c for c in e.children if isinstance(c, Text) and c.paragraphs), None)
            if t is not None:
                best = max(best, measure.text_em(t.paragraphs[0].plain, bold=True))
    return best


def _kpi_fit(ctx: _Ctx, box: Container | None, width: int) -> float:
    """How many times larger the numbers of the row may get and still fit one line of ``width``."""
    if box is None:
        return 1.0
    text = next((c for c in box.children if isinstance(c, Text) and c.paragraphs), None)
    if text is None:
        return 1.0
    big = (ctx.theme.classes.get("kpi") or _base_classes()["kpi"]).merged(ctx.css.kpi_styles(box)[0])
    em = _kpi_row_em(ctx, box, measure.text_em(text.paragraphs[0].plain, bold=True))
    avail = width / EMU_PER_PT * 0.72
    size = min(big.font_size or 36, avail / max(em, 1e-6))  # the size the number has after its own shrink
    return avail * ctx.lt.kpi_fit_margin / max(em * size, 1e-6)


def _kpi_explicit(ctx: _Ctx, box: Container | None) -> bool:
    if box is None:
        return False
    if _explicit_size(ctx, box):
        return True
    return ctx.css.active and any(st.font_size is not None for st in ctx.css.kpi_styles(box))


def _has_kpi_text(ctx: _Ctx) -> bool:
    return _has_kpi_row(ctx) and any(
        isinstance(e, Text) and e.role == "body" and "callout" not in e.classes for e in ctx.slide.elements
    )


def _has_kpi_row(ctx: _Ctx) -> bool:
    """The slide holds a ``.kpi`` box: free text under it follows the sparse-slide growth (never smaller)."""
    return ctx.lt.kpi_text_grow and any(
        isinstance(e, Container) and "kpi" in e.classes for e in ctx.slide.elements
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
        ctx.grow > 1.0
        and ctx.scale >= 1.0
        and not (ctx.css.active and ctx.css.own(el).font_size is not None)
        and not _cells_sized(el)
    ):  # sparse slide: table text grows too (less than box text)
        t = min(
            ctx.grow,
            (ctx.lt.table_alone_font_grow if _tables_alone(ctx) else ctx.lt.table_font_grow) * ctx.step,
        )
        if _has_box_text(ctx):  # ... but stays within one step of the box text on the same slide
            body = ctx.theme.sizes.get("body", DEFAULT_SIZES["body"]) * ctx.dense_k * ctx.grow
            peer = 1.0 if ctx.lt.body_size_unify else ctx.lt.peer_step  # unify: never below the box text
            want = body / peer / max(st.font_size or 14, 1) / max(eff, 1e-6)
            t = max(t, min(want, ctx.grow * 1.1))
        eff *= t
        ctx.grew = True
    elif ctx.lt.body_size_unify and ctx.scale >= 1.0 and _has_box_text(ctx) and not _tables_alone(ctx):
        box = ctx.theme.sizes.get("body", DEFAULT_SIZES["body"]) * ctx.dense_k * ctx.grow
        have = (st.font_size or 14) * eff
        if (
            box > have
            and not (ctx.css.active and ctx.css.own(el).font_size is not None)
            and box / have <= ctx.lt.unify_max
        ):  # a table smaller than the card text beside it inverts the hierarchy: lift it to the same size
            eff *= box / have
    eff0 = measure.effective_scale(st.font_size or 14, ctx.scale, ctx.theme.min_font_size)
    nrows, ncols, anchors = table_grid(el)
    if ctx.tgrow > 1.0 and ctx.scale >= 1.0 and not _table_size_explicit(ctx, el):
        if ctx.twrap:  # tall free body: the extra growth may wrap a cell at a space (never mid-word)
            if eff > eff0 * 1.001:
                eff = _no_new_wraps(ctx, el, ncols, anchors, width, st, eff0, eff)
            eff *= ctx.tgrow
        else:
            eff *= ctx.tgrow
            if eff > eff0 * 1.001:
                eff = _no_new_wraps(ctx, el, ncols, anchors, width, st, eff0, eff)
    elif eff > eff0 * 1.001:
        eff = _no_new_wraps(ctx, el, ncols, anchors, width, st, eff0, eff)
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


def _no_new_wraps(ctx: _Ctx, el: Table, ncols: int, anchors, width: int, st: Style, eff0: float, eff: float):
    """The largest table text scale <= ``eff`` at which no cell that fits one line at ``eff0`` on a column
    ``l3_wrap_margin`` narrower (renders wrap earlier than the model: fonts, diacritics) wraps there."""
    pad = 2 * measure.cell_pad()[0]
    k = 1.0 - ctx.lt.l3_wrap_margin
    cells = []
    for r, c, cell in anchors:
        if len(cell.paragraphs) != 1:
            continue
        text = "".join(run.text for run in cell.paragraphs[0].runs)
        if " " not in text.strip():  # a single word cannot gain a break; CJK guards live elsewhere
            continue
        bold = r < el.header_rows or any(run.bold for run in cell.paragraphs[0].runs)
        cells.append((c, cell.colspan, measure.text_em(text, bold=bold, font=st.font)))
    if not cells:
        return eff

    def inner(cw, c, span):
        return sum(cw[c : c + span]) / EMU_PER_PT - pad / EMU_PER_PT

    base = st.font_size or 14
    cw0 = column_widths(el, ncols, anchors, width, base * eff0)
    one = [(c, n, em) for c, n, em in cells if em * base * eff0 <= inner(cw0, c, n) * k]
    if not one:
        return eff
    f = eff
    while f > eff0 * 1.001:
        cw = column_widths(el, ncols, anchors, width, base * f)
        if all(em * base * f <= inner(cw, c, n) * k for c, n, em in one):
            return f
        f = max(eff0, f - 0.05 * eff0)
    return eff0


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
        elif (
            (
                ctx.roomy
                or (ctx.lone_air > 0 and measure.has_cjk(_plain(getattr(el, "paragraphs", None) or [])))
            )
            and ctx.grow > ctx.grow_base >= 1.0
            and eff > 0
        ):
            small = (
                eff * ctx.grow_base / ctx.grow
            )  # growing must not add wrapped lines (orphan CJK characters)
            if need > _text_need(ctx, el, st, rect.w, small) * (ctx.grow / ctx.grow_base) * 1.04:
                ctx.over.append(_label(el))
        if isinstance(el, Text) and "callout" in el.classes:
            rect = Rect(rect.x, rect.y, rect.w, min(rect.h, round(need)))  # callouts never stretch
        orig = id(el)
        if (pg := _para_gap(ctx, el)) is not None:  # spread paragraphs: the renderer writes spcBef
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
            if ctx.lt.table_row_max_em > 0:  # rows stretch, but a row is never more than N text heights
                row_cap = round(ctx.lt.table_row_max_em * (st.font_size or 14) * eff * EMU_PER_PT)
                target = min(target, sum(max(h, row_cap) for h in rh))
            rh = [round(h * target / total) for h in rh]
            rh[-1] += target - sum(rh)
            total = sum(rh)
        attrs = {**el.attrs, "_col_w": cw, "_row_h": rh}
        if ctx.tgrow > 1.0:
            attrs["_row_cap"] = (
                True  # text grown by ``_table_text``: the vertical fill keeps rows <= row_max_em
            )
            if ctx.twrap:
                attrs["_twrap"] = True  # wrap pass: the vertical fill may still fit it to the gutter
        ctx.emit(
            (el if "gantt" in el.classes else right_align_numbers(el)).model_copy(update={"attrs": attrs}),
            Rect(rect.x, rect.y, min(rect.w, sum(cw)), min(total, rect.h) if total > rect.h else total),
            st,
            eff,
        )
    elif isinstance(el, Chart):
        t = ctx.theme
        st = fast_style(
            font=t.fonts.body,
            font_ea=t.fonts.ea,
            font_size=t.sizes.get("table", DEFAULT_SIZES["table"]),
            color="fg",
        )
        ctx.emit(el, rect, _styled(ctx, el, st, classes=False))
    elif isinstance(el, (Image, Media)):
        ctx.emit(el, rect, _styled(ctx, el, fast_style()))
    elif isinstance(el, Raw):
        t = ctx.theme
        st = fast_style(
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
        if (
            el.kind == "html"
            and ctx.depth == 0
            and ctx.lt.html_fit
            and len(ctx.slide.elements) == 1
            and str(el.attrs.get("fit", "")).lower() != "off"
        ):  # alone on the slide: Chromium lays it out at the full box height (stretch, else center)
            el = el.model_copy(update={"source": HTML_FIT_OPEN + el.source + "</div>"})
        ctx.emit(el, rect, st, fs)
    elif isinstance(el, Container):
        _place_container(ctx, el, rect, inherit)


HTML_FIT_OPEN = (
    "<style>.sm-fit{display:flex;flex-direction:column;justify-content:center;height:100vh}"
    '.sm-fit>:only-child{flex:1 1 auto}</style><div class="sm-fit">'
)  # a lone single-root HTML block stretches over the box; several roots / fixed content center vertically


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
        base = fast_style(padding="0pt")
    else:
        base = _scale_pad(ctx.theme.classes.get("card", fast_style(padding=ctx.lt.box_pad)), ctx.step)
    others = _class_styles(ctx, c, skip=("plain", "kpi"))
    own = ctx.css.own(c)
    st = fast_style().merged(ctx.css.inherited(c), base, *others, own, c.style)
    if own.line_width and not st.line:
        st = st.merged(fast_style(line="border"))
    return _tighten(ctx, st)


def _cpads(ctx: _Ctx, c: Container) -> tuple[Style, int, tuple[int, int, int, int]]:
    """(card style, scalar padding, (left, top, right, bottom) insets) of a box."""
    style = _card_style(ctx, c)
    dflt = _emu(ctx.lt.box_pad) * ctx.tight * ctx.step
    return style, _pad(style, dflt), css.insets(style, dflt)


def _heading_parts(ctx: _Ctx, c: Container, pad: int, kpi: bool):
    """(heading element, merged style, autofit scale, band fill) of a box, or ``None`` without a heading."""
    if c.title is None or not c.title.paragraphs:
        return None
    band, band_ink = (None, "bg") if kpi else ctx.theme.heading_band_for(c.classes)
    h_el = c.title if c.title.role == "heading" else c.title.model_copy(update={"role": "heading"})
    hst = _text_style(ctx, h_el, fast_style())
    if kpi:
        body_size = ctx.theme.sizes.get("body", DEFAULT_SIZES["body"]) * ctx.dense_k
        hst = hst.merged(
            fast_style(align="center", color="muted", bold=False, font_size=body_size), ctx.css.own(h_el)
        )  # `.kpi h2 {..}` still wins over the label defaults
    if band:
        hst = hst.merged(
            fast_style(
                fill=band,
                color=band_ink,
                bold=True,
                valign="middle",
                padding=f"{round(pad / EMU_PER_PT, 2)}pt",
            )
        )
    eff = measure.effective_scale(hst.font_size or 18, ctx.scale, ctx.theme.min_font_size)
    fixed = _explicit_size(ctx, h_el) or _explicit_size(ctx, c.title)
    if ctx.head_grow and ctx.grow > 1.0 and ctx.scale >= 1.0 and not kpi and not fixed:
        eff *= min(ctx.grow, ctx.lt.grow_head)
    if ctx.grow > 1.0 and ctx.scale >= 1.0 and not kpi and not fixed and (body := _box_body_pt(ctx, c)):
        size = max(hst.font_size or 18, 1.0)
        if size * eff < body * HEAD_TOL:  # never smaller than its own body
            eff = body * ctx.lt.head_body / size
    return h_el, hst, eff, band


def _box_body_pt(ctx: _Ctx, c: Container) -> float:
    """Largest body text size (pt) inside box ``c`` after the sparse-slide growth; 0 without body text."""
    best = 0.0
    for ch in c.children:
        if isinstance(ch, Text) and ch.role == "body" and "callout" not in ch.classes:
            st = _text_style(ctx, ch, fast_style())
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
    name = str(name).strip() if name else ""
    if icons.is_file(name):  # `icon=file.svg`: case-sensitive path, read by the renderer
        return name
    name = name.lower()
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
    if "steps" in c.classes and _place_steps(ctx, c, rect, inherit):
        return
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
                _icon_item(icon),
                Rect(inner.x + (inner.w - isz) // 2, y, isz, isz),
                fast_style(fill="primary"),
            )
            y += isz + round(pad * 0.4)
        if band:
            if hh > rect.h * _TOL:
                ctx.over.append(_label(c))
            band_rect = Rect(rect.x, rect.y, rect.w, min(hh, rect.h))
            if icon:  # the band is a plain shape behind the icon and the shifted heading text
                ctx.emit(Shape(shape="rect"), band_rect, fast_style(fill=band))
                ctx.emit(
                    _icon_item(icon),
                    Rect(rect.x + pad, rect.y + (band_rect.h - isz) // 2, isz, isz),
                    fast_style(fill=hst.color),
                )
                text_rect = Rect(rect.x + shift, rect.y, rect.w - shift, band_rect.h)
                ctx.emit(h_el, text_rect, hst.model_copy(update={"fill": None}), eff)
            else:
                ctx.emit(h_el, band_rect, hst, eff)
            y = band_rect.bottom + round(pad * 0.5)
        else:
            if icon and not kpi:
                ctx.emit(
                    _icon_item(icon), Rect(inner.x, y, isz, isz), fast_style(fill=hst.color or "primary")
                )
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
        children = _kpi_children(ctx, children, area.w, c)
    saved = (ctx.depth, ctx.grow)
    ctx.depth += 1
    if kpi:
        ctx.grow = _kpi_grow(ctx, saved[1], c, area.w)
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


def _steps_parts(c: Container) -> tuple[list[Container], list[Container | None]]:
    """The arrow (heading only) and the card (the rest) of every ``##`` step of an ``@steps`` group.

    Both keep the step's classes and CSS identity (``_css_src``); a step without content has no card."""
    arrows: list[Container] = []
    cards: list[Container | None] = []
    for i, b in enumerate(b for b in c.children if isinstance(b, Container) and b.title is not None):
        src = b.attrs.get("_css_src", id(b))
        keep = {k: v for k, v in b.attrs.items() if k == "icon"}
        arrows.append(
            Container(
                title=b.title,
                id=b.id,
                line=b.line,
                classes=[*(k for k in b.classes if k not in ("kpi", "plain", "card")), "steps-arrow"],
                attrs={**keep, "_css_src": src, "shape_name": f"Step {i + 1} arrow"},
            )
        )
        if b.children:
            cards.append(
                Container(
                    line=b.line,
                    grid=b.grid,
                    gap=b.gap,
                    links=b.links,
                    style=b.style,
                    children=b.children,
                    classes=[*b.classes, "steps-card"],
                    attrs={
                        **{k: v for k, v in b.attrs.items() if k != "icon"},
                        "_css_src": src,
                        "shape_name": f"Step {i + 1} card",
                    },
                )
            )
        else:
            cards.append(None)
    return arrows, cards


def _place_steps(ctx: _Ctx, c: Container, rect: Rect, inherit: Style) -> bool:
    """``@steps``: a chevron row of the step headings, and under every arrow its card (same columns).

    The cards start ``steps_gap`` under the arrows and are as tall as their content here; the slide's
    growth passes then enlarge their text and ``fill_steps`` stretches them to the conclusion bar /
    footnote. ``False`` = not a steps group (fewer than two headed boxes): placed like any other box."""
    arrows, cards = _steps_parts(c)
    n = len(arrows)
    if n < 2 or n != len(c.children):  # other blocks in the group: a plain row of boxes
        return False
    gap = _gap(ctx, _cgap(ctx, c), rect.w)
    grid = _cgrid(ctx, c) or str(n)
    present = [k for k in cards if k is not None]
    letters, nxt = [], 0
    for k in cards:  # areas grid: the present cards keep their column, a step without content leaves a gap
        letters.append(chr(97 + nxt) if k is not None else ".")
        nxt += k is not None
    card_grid = grid if len(present) == n else "".join(letters)
    saved = (ctx.depth, ctx.steps_row)
    ctx.depth += 1
    try:
        start = len(ctx.out)
        ctx.steps_row = True
        _place_blocks(ctx, arrows, rect, inherit, grid, ["chevron", "steps"], gap, c)
        ctx.steps_row = False
        bottom = max((p.y + p.h for p in ctx.out[start:]), default=rect.y)
        if not present:
            return True
        top = bottom + _emu(ctx.lt.steps_gap)
        area = Rect(rect.x, top, rect.w, max(rect.bottom - top, 0))
        gs = parse_spec(card_grid, len(present), [])
        h = area.h
        if gs is not None and gs.cols:
            cells = cell_rects(gs, len(present), area, gap, ctx.theme.columns)
            nat = [_box_nat(ctx, k, r.w, inherit) for k, r in zip(present, cells, strict=True)]
            if all(v is not None for v in nat):
                h = min(h, max(nat))  # type: ignore[type-var]
        if area.h <= 0:
            ctx.over.append(_label(c))
            return True
        _place_blocks(ctx, present, Rect(area.x, area.y, area.w, h), inherit, card_grid, [], gap, c)
    finally:
        ctx.depth, ctx.steps_row = saved
    return True


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
        children = _kpi_children(ctx, children, inner_w, c)
    saved = (ctx.depth, ctx.grow)
    ctx.depth += 1
    if kpi:
        ctx.grow = _kpi_grow(ctx, saved[1], c, inner_w)
    try:
        child_inherit = inherit.merged(_only_inheritable(style))
        nat = [_natural_height(ctx, ch, inner_w, child_inherit) for ch in children]
    finally:
        ctx.depth, ctx.grow = saved
    if any(n is None for n in nat):
        return None
    return total + sum(nat) + _gap(ctx, _cgap(ctx, c), inner_w, small=True) * (len(nat) - 1)


def _hero_cols(ctx: _Ctx, gs: GridSpec, blocks: list) -> None:
    """A row of ``.kpi`` cards where some carry ``.hero`` (no ``@`` column token): hero columns weigh
    ``layout.kpi_hero_w`` times a normal one, so ``{.kpi .hero}`` reads like ``@2:1:1``."""
    if ctx.lt.kpi_hero_w <= 1.0 or len(blocks) < 2 or len(gs.rows) != 1 or gs.areas is not None:
        return
    if len(gs.cols) != len(blocks) or not all(
        isinstance(b, Container) and "kpi" in b.classes for b in blocks
    ):
        return
    heroes = ["hero" in b.classes for b in blocks]
    if any(heroes) and not all(heroes):
        gs.cols = [ctx.lt.kpi_hero_w if h else 1.0 for h in heroes]
        gs.snap = True


def _kpi_children(ctx: _Ctx, children: list, width: int, box: Container | None = None) -> list:
    """The first text child of a ``.kpi`` box: paragraph 0 = big number, the rest = muted caption."""
    i = next((k for k, c in enumerate(children) if isinstance(c, Text) and c.paragraphs), None)
    if i is None:
        return children
    ch = children[i]
    th = ctx.theme
    big = th.classes.get("kpi") or _base_classes()["kpi"]
    cap = fast_style(
        font_size=th.sizes.get("caption", DEFAULT_SIZES["caption"]), color="muted", align="center", bold=False
    )
    vcss, ccss = ctx.css.kpi_styles(box) if box is not None else (fast_style(), fast_style())
    big, cap = big.merged(vcss), cap.merged(ccss)
    paras: list[Paragraph] = []
    for j, p in enumerate(ch.paragraphs):
        if j == 0:
            st = big
            size = big.font_size or 36
            em = _kpi_row_em(ctx, box, measure.text_em(p.plain, bold=True))  # one size per row
            avail = width / EMU_PER_PT * 0.72  # headroom: fallback fonts are wider than the estimate
            if em * size > avail:  # one line: shrink the number to the card width
                st = st.merged(fast_style(font_size=max(round(avail / em, 1), 10)))
        else:
            st = cap
        paras.append(p.model_copy(update={"style": st.merged(p.style)}))
    new = ch.model_copy(
        update={"paragraphs": paras, "style": fast_style(align="center", valign="middle").merged(ch.style)}
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
    floor = min(ctx.gaps.get(i, _base_gap(ctx)) for ids in members for i in ids)
    for ids in members:
        for i in ids:
            if ctx.gaps.get(i, _base_gap(ctx)) <= floor + 1e-9:
                continue
            p = ctx.out[ctx.text_out[i]]
            attrs = {k: v for k, v in p.element.attrs.items() if k != "para_gap"}
            if floor > _base_gap(ctx) + 1e-9:
                attrs["para_gap"] = floor
                ctx.gaps[i] = floor
            else:
                ctx.gaps.pop(i, None)
                if ctx.step > 1.0:
                    attrs["para_gap"] = _base_gap(ctx)
            p.element = p.element.model_copy(update={"attrs": attrs})


def _consulting(ctx: _Ctx) -> bool:
    """Dense slide or small-body (consulting) theme: sparse cards may take more air than normal themes."""
    return ctx.dense_k < 1.0 or ctx.theme.sizes.get("body", DEFAULT_SIZES["body"]) <= ctx.lt.grow_small_pt


def _hugging(ctx: _Ctx) -> bool:
    """Cards are as tall as their content (``row_slack_hug``) instead of ``row_slack``."""
    return ctx.lt.hug_cards


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
    base = _base_gap(ctx)
    slots = sum(c[2] for c in cands)
    if not slots:
        return
    gmax = ctx.lt.room_gap_max_dense if _consulting(ctx) else ctx.lt.room_gap_max
    g = min(gmax, base + free * ctx.lt.room_use / EMU_PER_PT / slots)
    while g > base + 0.02:
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
    if (
        not nflex and owner is not None and id(owner) in ctx.centered
    ):  # a card as tall as the visual beside it
        y += max((area.h - sum(n or 0 for n in nat) - gap * (len(flow) - 1)) // 2, 0)
    used = 0
    for (i, ch), n in zip(flow, nat, strict=True):
        h = n if n is not None else flex_h
        r = _css_width(ctx, ch, _apply_box(ctx, ch, Rect(area.x, y, area.w, h), False), inherit)
        rects[i] = r
        _place_block(ctx, ch, r, inherit)
        y += h + gap
        used += h + gap
    used -= gap
    _share_gaps(ctx, [ch for _, ch in flow])
    limit = (
        ctx.lt.grow_box_fill
        if ctx.grow > 1.0 and ctx.depth > 0 and not (isinstance(owner, Container) and "kpi" in owner.classes)
        else _TOL
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
        attrs={
            "_css_src": blk.attrs.get("_css_src", id(blk)),  # css matching: this shape is the box ``blk``
            **({"shape_name": blk.attrs["shape_name"]} if blk.attrs.get("shape_name") else {}),
        },
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
            fast_style(line="primary", line_width=ctx.theme.render.connector_width),
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
    if isinstance(blk, Container) and "steps" in blk.classes:
        return None, "other"  # arrows over cards: takes the body, the cards hug their content inside
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
    tail_text: bool = False,
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
    singles: list[tuple[int, object]] = []
    rowtable = [False] * nr  # rows with a table inside a card: its rows grow, so the card keeps some slack
    stacked: set[int] = set()  # rows beside a flexible block that spans them (a column of stacked boxes)
    for k, ((_i, blk), r) in enumerate(zip(flow, cells, strict=True)):
        if gs.areas is not None:
            if k not in gs.areas:
                continue
            r0, r1 = gs.areas[k][0], gs.areas[k][2]
        else:
            r0 = r1 = min(k // len(gs.cols), nr - 1)
        n, kind = _cell_nat(ctx, blk, r.w, inherit)
        if isinstance(blk, Container) and any(isinstance(ch, Table) for ch in blk.children):
            rowtable[r0] = True
        if r1 > r0:
            spans.append((r0, r1, n))
            if isinstance(blk, Container) and ctx.lt.center_beside:
                ctx.centered.add(id(blk))  # a card spanning several rows may be taller than its content
            continue
        singles.append((r0, blk))
        covered[r0] = True
        kinds[r0].add(kind)
        if not isinstance(blk, (Text, Code)):
            rowtext[r0] = False
        nat[r0] = None if n is None or nat[r0] is None else max(nat[r0] or 0, n)
    caps: list[int | None] = []
    ref_h = grid_area.h if has_tail else body.h  # a tail (callout, table) below keeps its own room
    for row in range(nr):
        n = nat[row]
        if not covered[row] or n is None or n <= 0:
            caps.append(None)
        elif kinds[row] == {"kpi"}:
            caps.append(max(round(n * ctx.kpi_air), _emu(ctx.lt.kpi_min_h)))
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
            if ctx.roomy and nr == 1 and (tail_text or not has_tail) and ctx.grow > ctx.grow_base:
                floor = max(
                    floor,
                    min(
                        ctx.lt.roomy_row * ref_h,
                        (ctx.lt.roomy_row_air_dense if _consulting(ctx) else ctx.lt.roomy_row_air) * n,
                    )
                    / body.h,
                )  # fill stays >= ~50%
            if ctx.lone_air > 0 and nr == 1 and (tail_text or not has_tail):
                floor = max(floor, min(ctx.lt.balance_row * ref_h, ctx.lone_air * n) / body.h)
            if _consulting(ctx) and not has_tail:
                floor = min(floor, ctx.lt.row_min_hug)  # consulting cards hug their text instead
            slack = ctx.lt.row_slack_hug if _hugging(ctx) and not rowtable[row] else ctx.lt.row_slack
            caps.append(max(round(n * min(slack, ctx.lt.row_slack)), round(floor * body.h)))
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
    if stacked and ctx.lt.center_beside:
        ctx.centered.update(id(b) for r0, b in singles if r0 in stacked and isinstance(b, Container))
    if stacked and all(n for n in nat):  # boxes stacked beside a tall block share its height by content
        tot = sum(nat)  # type: ignore[arg-type]
        w = [max(n or 0, ctx.lt.stack_min * tot) for n in nat]
        return grid_row_heights(replace(gs, rows=[float(x) for x in w]), grid_area.h, gap, caps)
    if (
        ctx.expand > 0 and nr >= 2 and not tree
    ):  # sparse slide: spread extra height over the capped rows (not kpi / table)
        rows = [r for r in range(nr) if caps[r] is not None and "other" in kinds[r]]
        tot = sum(caps[r] or 0 for r in rows)
        airy = (ctx.roomy and ctx.grow > ctx.grow_base) or _hugging(
            ctx
        )  # grown text / consulting cards: rows keep a card fill of about 50-70%
        for r in rows:
            grown = (caps[r] or 0) + round(ctx.expand * (caps[r] or 0) / max(tot, 1))
            if airy and nat[r]:
                grown = min(
                    grown,
                    max(
                        caps[r] or 0,
                        round(
                            (ctx.lt.roomy_row_air_dense if _consulting(ctx) else ctx.lt.roomy_row_air)
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
        if ctx.lt.table_fill_width and len(flow) == 1 and isinstance(flow[0][1], Table):
            ctx.cap_tables = False  # the only body block: aligns with the lead / conclusion bar
    # slide level: callouts are never grid cells, they close the slide body as full-width rows
    callouts: list[tuple[int, object]] = []
    if ctx.depth == 0 and len(flow) > 1:
        callouts = [(i, b) for i, b in flow if isinstance(b, Text) and "callout" in b.classes]
        if len(callouts) == len(flow):
            callouts = []
        flow = [(i, b) for i, b in flow if (i, b) not in callouts]
    gs = parse_spec(grid, len(flow), classes)
    auto_cols = gs is None or not gs.cols  # no explicit column token: `.hero` KPI cards may weigh the columns
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
        if k == len(flow) and len(flow) - 1 >= len(gs.cols) and isinstance(flow[-1][1], _SPAN_BLOCKS):
            k = len(flow) - 1  # a lone chart / image / code / diagram after a full box row spans the width
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
    if auto_cols and not gs.flags:
        _hero_cols(ctx, gs, [b for _, b in flow])
    # blocks beyond the grid's cells are stacked full width below it
    extra: list[tuple[int, object]] = []
    if gs.capacity is not None and len(flow) > gs.capacity:
        extra = flow[gs.capacity :]
        flow = flow[: gs.capacity]
    extra = sorted(extra + tables, key=lambda t: t[0]) + callouts
    if "flow" in flags:
        gap = max(gap, round(0.45 * EMU_PER_INCH))
    elif "chevron" in flags and "steps" not in flags:  # step arrows share the card columns: the same gap
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
        tail_text = all(
            isinstance(b, Text) for _, b in extra
        )  # a callout / lead below keeps only its own line
        row_h = _row_heights(
            ctx, gs, flow, cells, grid_area, area, gap, inherit, tail_area is not None, tree, tail_text
        )
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
        elif ctx.step > 1.0 and ctx.scale >= 1.0:
            ctx.chev_grow = ctx.step
            ctx.grew = True
        ctx.chev_adj = None
        ladder = _chevron_ladder(ctx)
        word_cap: float | None = None
        for k, adj in enumerate(ladder):  # pointiest shape first; flatter points widen the text area
            ctx.chev_adj = adj if adj != ctx.lt.chevron_adj else None
            chev_h = _chevron_row_h(
                ctx,
                [b for _, b in flow],
                min((r.w for r in cells), default=area.w),
                inherit,
                area.h if alone else None,
            )
            word_cap = _chevron_word_cap(ctx, flow, cells, chev_h, inherit, last=k == len(ladder) - 1)
            head_cap = _chevron_head_cap(ctx, flow, cells, chev_h, inherit)
            nominal = _chevron_nominal(ctx, flow, inherit)
            head_ok = head_cap is None or head_cap >= min(nominal, 1.0)
            cjk_cap = _chevron_cjk_cap(ctx, flow, cells, chev_h, inherit)
            head_ok = head_ok and (cjk_cap is None or cjk_cap >= min(nominal, 1.0))
            roomy = all(
                _chevron_text_w(r, fast_style(), None, _cadj(ctx)) >= ctx.lt.chevron_text_share * r.w
                for r in cells
                if r.w > 0
            )
            if (roomy and head_ok and (word_cap is None or word_cap >= nominal)) or k == len(ladder) - 1:
                break
        chev_eff = min(
            (
                _chevron_eff(ctx, blk, _apply_box(ctx, blk, r, False), inherit, chev_h)
                for (_i, blk), r in zip(flow, cells, strict=True)
                if isinstance(blk, (Text, Shape, Container))
            ),
            default=None,
        )
        if word_cap is not None:  # shrink the text (down to the deck minimum) before a word would break
            chev_eff = word_cap if chev_eff is None else min(chev_eff, word_cap)
        if head_cap is not None and chev_eff is not None:  # ... and a bit more before a heading wraps
            chev_eff = min(chev_eff, head_cap)
        if cjk_cap is not None and chev_eff is not None:  # CJK lines never break (fallback fonts run wider)
            chev_eff = min(chev_eff, cjk_cap)
    for (i, blk), r in zip(flow, cells, strict=True):
        r = _css_width(ctx, blk, _apply_box(ctx, blk, r, False), inherit)
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
            st = fast_style(fill="muted", line=None)
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
        p.style = p.style.merged(fast_style(valign="top"))


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
            isinstance(o, (Chart, Image, Media, Raw))
            for j, (_n, o) in enumerate(flow)
            if j // ncol == row and j != k
        ):
            continue
        n = _box_nat(ctx, blk, r.w, inherit)
        if n is None:
            continue
        floor = round(ctx.lt.beside_min * r.h)
        h = round(n * ctx.lt.beside_slack)
        if (
            h >= ctx.lt.beside_align * r.h
        ):  # content fills enough of the visual's height: share top and bottom
            out[k] = r
            if ctx.lt.center_beside:
                ctx.centered.add(id(blk))
            continue
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
    return st.merged(fast_style(font_size=max(st.font_size or 18, floor)))


def _chevron_geom(
    ctx: _Ctx, blk, rect: Rect, inherit: Style, hcap: int | None = None
) -> tuple[Shape, Style, Rect]:
    sh = _chevron_shape(blk)
    st = _chevron_font(ctx, sh, _text_style(ctx, sh, inherit))
    if hcap is not None:
        rect = Rect(rect.x, rect.y, rect.w, min(rect.h, hcap))
    # the preset text rectangle already starts a point depth inside both ends: add only a small padding
    st = st.merged(fast_style(padding=ctx.lt.chevron_pad, align="center", valign="middle"))
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


def _cadj(ctx: _Ctx) -> float:
    """Point depth of the chevron row being placed (shorter side = 1)."""
    return ctx.lt.chevron_adj if ctx.chev_adj is None else ctx.chev_adj


def _chevron_ladder(ctx: _Ctx) -> list[float]:
    """Point depths to try, pointiest first: ``chevron_adj`` down to ``chevron_adj_min``."""
    top, low = ctx.lt.chevron_adj, min(ctx.lt.chevron_adj_min, ctx.lt.chevron_adj)
    step = max(ctx.lt.chevron_adj_step, 0.005)
    out = [top]
    while out[-1] - step > low + 1e-9:
        out.append(round(out[-1] - step, 4))
    if out[-1] > low + 1e-9:
        out.append(low)
    return out


_KATAKANA = re.compile(r"[\u30a0-\u30ff\u31f0-\u31ff\uff66-\uff9f]+")


def _longest_word_em(paragraphs: list[Paragraph]) -> float:
    """Width (em) of the longest unbreakable word (space-separated or a katakana run), bold where bold."""
    best = 0.0
    for p in paragraphs:
        for run in p.runs:
            bold = bool(run.bold or run.highlight)
            for chunk in run.text.split():
                if measure.has_cjk(chunk):
                    best = max(best, *(measure.text_em(r, bold=bold) for r in _KATAKANA.findall(chunk)), 0.0)
                else:
                    best = max(best, measure.text_em(chunk, bold=bold))
    return best


def _chevron_nominal(ctx: _Ctx, flow: list, inherit: Style) -> float:
    """Text scale a chevron row would use without any word constraint (the smallest of its blocks)."""
    effs = []
    for _i, blk in flow:
        if not isinstance(blk, (Text, Shape, Container)):
            continue
        sh = _chevron_shape(blk)
        st = _chevron_font(ctx, sh, _text_style(ctx, sh, inherit))
        effs.append(
            measure.effective_scale(st.font_size or 18, ctx.scale, ctx.theme.min_font_size) * ctx.chev_grow
        )
    return min(effs, default=1.0)


def _chevron_word_cap(
    ctx: _Ctx, flow: list, cells: list[Rect], h: int, inherit: Style, last: bool = True
) -> float | None:
    """Largest text scale at which the longest word of every chevron fits one line (floor: deck minimum).

    ``None`` when nothing constrains. Emits ``chevron-word-break`` (only when ``last``: the flattest point
    depth was tried) when even the minimum size cannot fit.
    """
    cap: float | None = None
    for (_i, blk), r in zip(flow, cells, strict=True):
        if not isinstance(blk, (Text, Shape, Container)):
            continue
        sh, st, rect = _chevron_geom(ctx, blk, _apply_box(ctx, blk, r, False), inherit, h)
        em = _longest_word_em(sh.paragraphs)
        if em <= 0:
            continue
        size = max(st.font_size or 18, 1.0)
        avail = _chevron_text_w(rect, st, sh, _cadj(ctx)) / EMU_PER_PT
        fit = avail / (em * size * ctx.lt.chevron_word_slack)  # slack: fallback fonts run wider
        floor = ctx.theme.min_font_size / size
        if fit < floor:
            if last:
                ctx.diag(
                    "chevron-word-break",
                    f"a word in {_label(blk)} is wider than the chevron text area even at the minimum size",
                    "use `flow` boxes or shorter step labels",
                    line=getattr(blk, "line", None),
                )
            fit = floor
        cap = fit if cap is None else min(cap, fit)
    return cap


def _chevron_head_cap(ctx: _Ctx, flow: list, cells: list[Rect], h: int, inherit: Style) -> float | None:
    """Text scale at which every bold heading ("Tháng 11") fits ``chevron_head_lines`` lines, or ``None``.

    Rows of >= ``chevron_head_min_steps`` chevrons only. A heading stays on one line when that costs at
    most ``1 - chevron_head_keep`` of the size; otherwise it wraps at a space (never inside a word) and the
    text shrinks only when the allowed lines still do not fit (down to ``chevron_head_min_scale``; below
    that shrinking would not save it and the heading is left to wrap).
    """
    lt = ctx.lt
    if len(flow) < lt.chevron_head_min_steps:
        return None
    lines_max = max(int(lt.chevron_head_lines), 1)
    top = max(ctx.chev_grow, 1.0)
    cap: float | None = None
    for (_i, blk), r in zip(flow, cells, strict=True):
        if not isinstance(blk, (Text, Shape, Container)):
            continue
        sh, st, rect = _chevron_geom(ctx, blk, _apply_box(ctx, blk, r, False), inherit, h)
        paras = sh.paragraphs
        if len(paras) < 2 or not paras[0].runs or not all(run.bold for run in paras[0].runs):
            continue
        size = max(st.font_size or 18, 1.0)
        avail = _chevron_text_w(rect, st, sh, _cadj(ctx)) / EMU_PER_PT / lt.chevron_head_slack
        segs = measure.para_segments(paras[0], True)

        def largest(limit: int, floor: float, segs=segs, avail=avail, size=size, st=st) -> float | None:
            s_ = top
            while s_ >= floor - 1e-9:
                if measure.count_lines(segs, avail, size * s_, st.font) <= limit:
                    return s_
                s_ = round(s_ - 0.05 * top, 3)
            return None

        keep = lt.chevron_head_keep if lines_max > 1 else lt.chevron_head_min_scale
        fit = largest(1, keep * top)
        if fit is None and lines_max > 1:
            fit = largest(lines_max, lt.chevron_head_min_scale * top)
        if fit is None:
            continue
        cap = fit if cap is None else min(cap, fit)
    return cap


def _chevron_cjk_cap(ctx: _Ctx, flow: list, cells: list[Rect], h: int, inherit: Style) -> float | None:
    """Text scale at which every CJK line of a chevron row stays on ONE line in a fallback font.

    A Japanese label has no spaces, so it breaks anywhere ("受取拠点の開 / 設") and leaves a one-character
    orphan. Every paragraph with CJK text is measured ``chevron_cjk_slack`` x wider; the text shrinks (down to
    ``chevron_head_min_scale`` of its size) until all of them fit. ``None`` = nothing to do.
    """
    lt = ctx.lt
    top = max(ctx.chev_grow, 1.0)
    cap: float | None = None
    for (_i, blk), r in zip(flow, cells, strict=True):
        if not isinstance(blk, (Text, Shape, Container)):
            continue
        sh, st, rect = _chevron_geom(ctx, blk, _apply_box(ctx, blk, r, False), inherit, h)
        size = max(st.font_size or 18, 1.0)
        avail = _chevron_text_w(rect, st, sh, _cadj(ctx)) / EMU_PER_PT / max(lt.chevron_cjk_slack, 1.0)
        for i, para in enumerate(sh.paragraphs):
            if not measure.has_cjk(para.plain):
                continue
            segs = measure.para_segments(
                para, i == 0 and bool(para.runs) and all(run.bold for run in para.runs)
            )
            s_ = top
            floor = lt.chevron_head_min_scale
            while s_ > floor + 1e-9 and measure.count_lines(segs, avail, size * s_, st.font) > 1:
                s_ = round(s_ - 0.025 * top, 3)
            if measure.count_lines(segs, avail, size * s_, st.font) > 1:
                continue  # even the smallest size would wrap: leave it to the usual wrap rules
            cap = s_ if cap is None else min(cap, s_)
    return cap


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
    if ctx.steps_row:  # step arrows: tall enough to read as the head of a column of cards
        s_hi = _emu(ctx.lt.steps_arrow_max_h)
        lo = min(max(round(ctx.lt.steps_arrow_aspect * width), _emu(ctx.lt.steps_arrow_min_h)), s_hi)
        hi = max(hi, s_hi)
    elif alone_h is not None:
        many = len(blocks) >= ctx.lt.chevron_head_min_steps  # narrow chevrons wrap into many lines: go tall
        hi = _emu(ctx.lt.chevron_max_alone_sparse if ctx.chev_air or many else ctx.lt.chevron_max_alone)
        share = ctx.lt.chevron_alone_share_sparse if ctx.chev_air else ctx.lt.chevron_alone_share
        lo = max(lo, min(hi, round(share * alone_h)))
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
                    sh.paragraphs, _chevron_text_w(rect, st, sh, _cadj(ctx)), st, eff, squeeze=False
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
    width = _chevron_text_w(rect, st, sh, _cadj(ctx))
    base = st.font_size or 18
    first = measure.effective_scale(base, ctx.scale, ctx.theme.min_font_size) * ctx.chev_grow
    for m in (1.0, 0.95, 0.9, 0.85, 0.8):
        eff = measure.effective_scale(base, ctx.scale * m, ctx.theme.min_font_size) * ctx.chev_grow
        wide = measure.paragraphs_height(sh.paragraphs, width, st, eff, squeeze=False)
        narrow = measure.paragraphs_height(sh.paragraphs, round(width * 0.88), st, eff, squeeze=False)
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
        sh.paragraphs, _chevron_text_w(rect, st, sh, _cadj(ctx)), st, eff, squeeze=False
    )
    if need > rect.h * 0.8:
        ctx.over.append(_label(blk))
    if ctx.chev_adj is not None:  # the renderer draws this point depth (default: the token)
        sh = sh.model_copy(update={"attrs": {**sh.attrs, "adj": ctx.chev_adj}})
    ctx.emit(sh, rect, st, eff)
    if "icon_side" in sh.attrs:  # icon just before the (centered) text block, vertically centered
        side = sh.attrs["icon_side"]
        left = rect.x + round(_cadj(ctx) * min(rect.w, rect.h)) + _pad(st)
        avail = _chevron_text_w(rect, st, sh, _cadj(ctx))
        size = (st.font_size or 18) * eff
        line = max(
            (measure.text_em(p.plain, bold=True) * size * EMU_PER_PT for p in sh.paragraphs), default=0
        )
        off = max(round((avail - min(line, avail)) / 2), 0)
        ctx.emit(
            _icon_item(sh.attrs["icon"]),
            Rect(left + off, rect.y + (rect.h - side) // 2, side, side),
            fast_style(fill=st.color or "primary"),
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


def _reserve_lead(deck: Deck, mode: str) -> bool:
    """``reserve_lead``: on, off, or auto = at least half of the deck's content slides carry a lead line."""
    if mode == "on":
        return True
    if mode == "off":
        return False
    body = [s for s in deck.slides if s.title and s.elements and s.layout in (None, "content")]
    return bool(body) and sum(s.lead is not None for s in body) * 2 >= len(body)


def _has_chart(elements: list) -> bool:
    """True when a chart sits anywhere in ``elements`` (its legend needs air above the footnote band)."""
    for e in elements:
        if isinstance(e, Chart) or (isinstance(e, Container) and _has_chart(e.children)):
            return True
    return False


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
    if (
        all(isinstance(e, Table) for e in elements)
        and left >= ctx.lt.roomy_left * body.h
        and not (fin.dense_k < 1.0 or small_theme)
    ):  # tables alone: rows grow up to ``table_grow_roomy`` x (text a little more), then the usual shift
        for g in (ctx.lt.table_alone_font_grow, fin.grow):
            c = run(body, grow=round(g, 2), expand=fin.expand, roomy=True, grow_base=fin.grow)
            if not c.over and c.out and _bottom(c) > _bottom(fin):
                fin = c
                left = body.bottom - _bottom(fin)
                break
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
            if f > 1.0 and (not ctx.lt.grow or fin.step > 1.0):  # growth off / sparse step is the last step
                continue
            g = round(fin.grow * f, 2)
            if (
                fin.dense_k < 1.0 and g * fin.dense_k > ctx.lt.dense_roomy_body * fin.step
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
    if (
        ctx.lt.balance_air > 0
        and fin.dense_k >= 1.0
        and not small_theme
        and not fin.roomy
        and body.bottom - _bottom(fin) > ctx.lt.balance_left * body.h
    ):  # normal density: a lone row of boxes gets taller cards instead of a 40% empty band
        body_pt0 = ctx.theme.sizes.get("body", DEFAULT_SIZES["body"])
        has_diagram = any(isinstance(e, Container) and "diagram" in e.classes for e in elements)
        steps = max(0, round((ctx.lt.balance_grow - 1.0) / 0.05)) if ctx.lt.grow and not has_diagram else 0
        # text first: grow it (cards follow at most ``balance_text_air`` x their natural height) until the
        # empty band is small enough; only then stretch the cards. The wrap guard refuses new wrapped CJK
        # lines; Latin text may wrap more.
        best_g = fin.grow
        for f in [1.0] + [round(1.0 + 0.05 * i, 2) for i in range(1, steps + 1)]:
            g = round(fin.grow * f, 2)
            if g > fin.grow and (g * body_pt0 > ctx.lt.balance_max_pt or g > max(ctx.lt.grow_max, fin.grow)):
                break
            c = run(body, grow=g, expand=fin.expand, lone_air=ctx.lt.balance_text_air, grow_base=fin.grow)
            if c.over or not c.out:
                if f > 1.0:
                    break  # bigger text only overflows more
                continue
            best_g = g
            if _bottom(c) > _bottom(fin):
                fin = c
                left = body.bottom - _bottom(fin)
            if left <= ctx.lt.balance_left * body.h:
                break
        if left > ctx.lt.balance_left * body.h:  # text cannot grow any more: stretch the cards
            c = run(body, grow=best_g, expand=fin.expand, lone_air=ctx.lt.balance_air, grow_base=fin.grow)
            if not c.over and c.out and _bottom(c) > _bottom(fin):
                fin = c
                left = body.bottom - _bottom(fin)
        dy = round((left - ctx.lt.balance_left * body.h) * ctx.lt.balance_shift)
        if dy > 0:  # what is still empty is split: part above the block, the rest below
            c = run(
                Rect(body.x, body.y + dy, body.w, body.h - dy),
                grow=fin.grow,
                expand=fin.expand,
                lone_air=fin.lone_air,
            )
            if not c.over and c.out:
                fin = c
                left = body.bottom - _bottom(fin)
    top = min((p.y for p in fin.out), default=body.y)
    cards = (
        (fin.dense_k < 1.0 or small_theme)
        and any(isinstance(e, Container) for e in elements)
        and all(
            isinstance(e, Text) or (isinstance(e, Container) and not {"kpi", "diagram"} & set(e.classes))
            for e in elements
        )  # only card blocks: tables, charts and chevron rows keep their top anchor
        and "chevron" not in (_slide_grid(ctx) or "")
        and "chevron" not in ctx.slide.classes
    )
    # consulting cards hug their text: the leftover stays ONE band. It sits below the block (top-anchored,
    # same title gap on every slide) unless ``hug_shift`` moves part of it above.
    hug = cards and ctx.lt.hug_shift > 0 and left > keep
    if hug or (not cards and _bottom(fin) - top < ctx.lt.very_sparse_fill * body.h):
        share = (
            ctx.lt.left_shift if any(isinstance(e, Container) for e in elements) else ctx.lt.left_shift_table
        )
        dy = round(left * share)
        if hug:
            dy = max(dy, round((left - keep) * ctx.lt.hug_shift))
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


def _text_h(p: Placed) -> int:
    """Height of the lines of a placed text (at most its box)."""
    pad = 0
    if p.style.padding is not None:
        try:
            pad = to_emu(p.style.padding)
        except ValueError:
            pad = 0
    gap = measure.element_gap(p.element)
    need = measure.paragraphs_height(p.element.paragraphs, p.w - 2 * pad, p.style, p.font_scale, gap=gap)
    return min(p.h, round(need) + 2 * pad)


def _content_bottom(out: list[Placed]) -> int:
    """Bottom of the visible content: a text box ends with its last line, not with the (taller) box."""
    best = 0
    for p in out:
        paras = getattr(p.element, "paragraphs", None)
        best = max(best, p.y + (_text_h(p) if paras and isinstance(p.element, Text) else p.h))
    return best


def _block_h(out: list[Placed]) -> int:
    return _content_bottom(out) - min((p.y for p in out), default=0)


def _spread_rows(out: list[Placed], gap_max: int, body: Rect, limit: int) -> list[Placed]:
    """Rows of top-level blocks move apart (each gap by at most ``gap_max``) while a band is over it."""
    cards = [p for p in out if isinstance(p.element, Container)]
    roots: list[tuple[int, int]] = []  # (top, bottom) of the top-level blocks, as rows
    for p in sorted(out, key=lambda p: p.y):
        if any(
            c is not p
            and c.x - 2 <= p.x
            and c.y - 2 <= p.y
            and p.x + p.w <= c.x + c.w + 2
            and p.y + p.h <= c.y + c.h + 2
            for c in cards
        ):
            continue
        h = _text_h(p) if isinstance(p.element, Text) and p.element.paragraphs else p.h
        if roots and p.y < roots[-1][1] - 2:
            roots[-1] = (roots[-1][0], max(roots[-1][1], p.y + h))
        else:
            roots.append((p.y, p.y + h))
    if len(roots) < 2:
        return out
    free = body.bottom - max(b for _t, b in roots)
    add = min(gap_max, max(free - limit, 0) // (len(roots) - 1) + 1 if free > limit else 0)
    if add <= 0:
        return out
    res = []
    for p in out:
        k = sum(1 for t, _b in roots[1:] if p.y >= t - 2)  # how many row gaps lie above this item
        res.append(p.model_copy(update={"y": p.y + k * add}) if k else p)
    return res


def _hug_text(out: list[Placed]) -> list[Placed]:
    """Top-anchored body text outside any card ends with its last line (the empty rest is not a box)."""
    cards = [p for p in out if isinstance(p.element, Container)]
    res = []
    for p in out:
        el = p.element
        if (
            isinstance(el, Text)
            and el.role == "body"
            and el.paragraphs
            and p.style.valign in (None, "top")
            and not any(
                c.x - 2 <= p.x
                and c.y - 2 <= p.y
                and p.x + p.w <= c.x + c.w + 2
                and p.y + p.h <= c.y + c.h + 2
                for c in cards
            )
        ):
            p = p.model_copy(update={"h": _text_h(p)})
        res.append(p)
    return res


def _needs_complete(ctx: _Ctx, fin: _Ctx, body: Rect, elements: list) -> bool:
    """A candidate for ``_complete``: boxes / text only, and an empty band over ``sparse_left_max``."""
    lt = ctx.lt
    if lt.sparse_left_max <= 0 or not lt.grow or fin.scale < 1.0 or fin.over or not fin.out:
        return False
    if not all(isinstance(e, (Text, Container)) for e in elements):
        return False
    bg = ctx.slide.background or ""
    if "." in bg or "(" in bg:  # a picture / gradient behind the text: the author placed it, do not move it
        return False
    if ctx.slide.links or any(
        isinstance(e, Container) and ("diagram" in e.classes or e.links) for e in elements
    ):
        return False
    top = min((p.y for p in fin.out), default=body.y)
    return max(body.bottom - _content_bottom(fin.out), top - body.y) > round(lt.sparse_left_max * body.h)


def _complete(ctx: _Ctx, fin: _Ctx, run, body: Rect, elements: list) -> _Ctx:
    """Last stage of a sparse slide: no empty band over ``sparse_left_max`` of the body.

    Only boxes / text / chevron rows (tables, charts and pictures fill their own space). The slide is laid
    out again with larger text (up to ``sparse_text_max_pt`` and ``sparse_step_max`` x the theme body size;
    explicit sizes never change, the CJK wrap guard stays on), air between paragraphs, taller KPI cards, cards
    up to ``sparse_card_air`` x their content and taller chevrons. What is still empty then moves above the
    block until the band below it is ``sparse_left_target`` of the body. A slide that already fits is kept.
    """
    lt = ctx.lt
    if not _needs_complete(ctx, fin, body, elements):
        return fin
    limit = round(lt.sparse_left_max * body.h)

    def empty(c: _Ctx) -> int:
        top = min((p.y for p in c.out), default=body.y)
        return max(body.bottom - _content_bottom(c.out), top - body.y)

    base_pt = ctx.theme.sizes.get("body", DEFAULT_SIZES["body"])
    cap_pt = min(lt.sparse_text_max_pt, base_pt * max(lt.sparse_step_max, 1.0))
    base = base_pt * ctx.dense_k
    top_g = math.floor(cap_pt / base * 100 + 1e-6) / 100  # never past the cap
    extra = {"air": lt.sparse_air, "kpi_air": lt.sparse_kpi_air, "chev_air": True}
    if fin.step > 1.0:
        extra["step"] = fin.step
    if fin.roomy:
        extra["roomy"] = True
    grow_base = fin.grow if fin.step <= 1.0 else max(fin.grow / fin.step, 1.0)
    top_g = max(top_g, fin.grow)
    n = max(round((top_g - fin.grow) / 0.05), 0)
    for g in [round(top_g - 0.05 * i, 2) for i in range(n + 1)] + [fin.grow]:
        if g < fin.grow - 1e-9:
            continue
        c = run(
            body,
            grow=g,
            expand=fin.expand,
            lone_air=lt.sparse_card_air,
            grow_base=grow_base,
            **extra,
        )
        if c.over or not c.out or _block_h(c.out) <= _block_h(fin.out):
            continue  # nothing gained (or something would overflow): try a smaller step
        fin = c
        break
    fin.out = _hug_text(fin.out)
    fin.completed = True
    if empty(fin) > limit:
        fin.out = _spread_rows(fin.out, _emu(lt.sparse_row_gap_max), body, limit)
    left = body.bottom - _content_bottom(fin.out)
    above = min((p.y for p in fin.out), default=body.y) - body.y
    dy = left - max(
        round(lt.sparse_left_target * body.h), (left + above) // 2
    )  # too little content: halve it
    if (
        dy > 0 and empty(fin) > limit and lt.body_valign != "top"
    ):  # a plain translation: re-running in a smaller area would shrink the block
        fin.out = [p.model_copy(update={"y": p.y + dy}) for p in fin.out]
    return fin


def _panel_fill(out: list[Placed]) -> float:
    """Lowest content share of a text panel (card) that sits beside a chart / image; 1.0 without one."""
    if not any(isinstance(p.element, (Chart, Image, Media)) for p in out):
        return 1.0
    worst = 1.0
    for c in out:
        if not isinstance(c.element, Container) or c.h <= 0:
            continue
        inner = [
            p
            for p in out
            if p is not c
            and isinstance(p.element, Text)
            and p.x >= c.x - 2
            and p.y >= c.y - 2
            and p.x + p.w <= c.x + c.w + 2
            and p.y + p.h <= c.y + c.h + 2
        ]
        if inner:
            worst = min(worst, (max(p.y + p.h for p in inner) - c.y) / c.h)
    return worst


def _sparse_step(ctx: _Ctx, fc: _Ctx, run, body: Rect, stepped: list[float]) -> _Ctx:
    """A slide whose content fills less than ``sparse_fill_soft`` of the body is laid out one step up.

    Text, paddings, paragraph gaps, chevron and table text scale by ``sparse_step`` (else ``sparse_step_min``)
    on top of the growth already chosen. A step is refused when something overflows, a wrapped line is
    added (CJK guard of the roomy pass), nothing gets bigger, or the body text would pass ``sparse_max_pt``.
    Explicit font sizes never change (``_explicit_size``). The first accepted step wins.
    """
    fill = (_bottom(fc) - body.y) / max(body.h, 1)
    panel = _panel_fill(fc.out)
    if fill >= ctx.lt.sparse_fill_soft and panel >= ctx.lt.center_min_fill:
        return fc
    if (
        fill >= ctx.lt.sparse_fill_soft
    ):  # full-height block, but a text panel beside a chart stays mostly empty
        return _panel_step(ctx, fc, run, body, stepped, panel)
    # a marginal slide only tries the full step; a really sparse one may fall back to the smaller one
    steps = (
        (ctx.lt.sparse_step, ctx.lt.sparse_step_min) if fill < ctx.lt.sparse_fill else (ctx.lt.sparse_step,)
    )
    max_pt = ctx.lt.sparse_max_pt
    if (
        fill < ctx.lt.center_min_fill
        and ctx.lt.sparse_step_max > ctx.lt.sparse_step
        and not any(isinstance(p.element, Table) for p in fc.out)  # table text keeps the regular step
    ):
        # a block that would float: try bigger steps first (largest that fits), then the usual ones
        top = ctx.lt.sparse_step_max
        n = round((top - ctx.lt.sparse_step) / 0.05)
        steps = tuple(round(top - 0.05 * i, 2) for i in range(n)) + steps
        max_pt = max(max_pt, ctx.lt.sparse_low_max_pt)
    for st in steps:
        if st <= 1.0:
            continue
        g = round(fc.grow * st, 2)
        c = run(body, grow=g, step=st, roomy=True, grow_base=fc.grow, expand=fc.expand)
        if c.over or not c.out or _bottom(c) <= _bottom(fc):
            continue
        big = max(
            (
                (p.style.font_size or 0) * p.font_scale
                for p in c.out
                if isinstance(p.element, Text)
                and p.element.role == "body"
                and not _explicit_size(c, p.element)
            ),
            default=0,
        )
        if big > max_pt + 1e-6:  # body text of a stepped slide stays below ``sparse_max_pt``
            continue
        if c.fill is not None and c.fill > ctx.lt.grow_fill:
            continue
        stepped[0], stepped[1] = st, fc.grow
        return c
    return fc


def _grow_head(
    ctx: _Ctx,
    fin: _Ctx,
    head: list[Placed],
    tail: list[Placed],
    body: Rect,
    inner_w: int,
    reserved: tuple[Style, int] | None = None,
) -> None:
    """A sparse slide's lead and footnotes follow its grown body text (no extra layout pass).

    The body is already placed; the lead / footnotes are re-measured at the larger size and the body moves
    down (footnotes move up) by the extra height, only when the content still ends above the footnotes.
    The lead stays below ``sparse_lead_title_max`` x the title size; explicit sizes never change.
    """
    lt = ctx.lt
    g = fin.grow
    if g <= 1.0 or not fin.out or (lt.sparse_lead_grow <= 1.0 and lt.sparse_footnote_grow <= 1.0):
        return
    H = ctx.H
    title_pt = ctx.theme.sizes.get("title", DEFAULT_SIZES["title"])
    lead_pt = ctx.theme.sizes.get("lead", DEFAULT_SIZES["lead"])
    lead_k = min(g, lt.sparse_lead_grow, lt.sparse_lead_title_max * title_pt / max(lead_pt, 1.0))
    foot_k = min(g, lt.sparse_footnote_grow)
    li = next(
        (
            i
            for i, p in enumerate(head)
            if isinstance(p.element, Text)
            and p.element.role == "lead"
            and p.element.paragraphs
            and p.font_scale >= 1.0
            and p.style.font_size
            and not _explicit_size(ctx, p.element)
        ),
        None,
    )
    fis = [
        i
        for i, p in enumerate(tail)
        if isinstance(p.element, Text)
        and p.element.role == "footnote"
        and p.font_scale >= 1.0
        and p.style.font_size
        and not _explicit_size(ctx, p.element)
    ]
    if li is not None:
        reserved = None  # a real lead: no empty slot
    if li is None and reserved is None and not fis:
        return
    content_bottom = _content_bottom(fin.out)
    for t in (1.0, 0.6, 0.3):
        lk, fk = 1 + (lead_k - 1) * t, 1 + (foot_k - 1) * t
        new_lead = None
        dlead = 0
        if li is not None and lk > 1.0:
            p = head[li]
            st = p.style.merged(fast_style(font_size=p.style.font_size * lk))
            h = round(_text_need(ctx, p.element, st, inner_w, 1.0))
            if h <= round(H * 0.18):
                new_lead, dlead = (st, h), max(h - p.h, 0)
        elif reserved is not None and lk > 1.0 and reserved[0].font_size:
            st = reserved[0].merged(fast_style(font_size=reserved[0].font_size * lk))
            dlead = max(round(_text_need(ctx, _text_el("lead", "x"), st, inner_w, 1.0)) - reserved[1], 0)
        new_foot: dict[int, tuple[Style, int]] = {}
        dfoot = 0
        if fis and fk > 1.0:
            for i in fis:
                p = tail[i]
                st = p.style.merged(fast_style(font_size=p.style.font_size * fk))
                new_foot[i] = (st, round(_text_need(ctx, p.element, st, inner_w, 1.0)))
            dfoot = sum(h for _st, h in new_foot.values()) - sum(tail[i].h for i in fis)
            if sum(h for _st, h in new_foot.values()) > round(H * lt.footnote_max):
                new_foot, dfoot = {}, 0
        if new_lead is None and not dlead and not new_foot:
            continue
        if content_bottom + dlead + max(dfoot, 0) > body.bottom:
            continue
        if new_lead is not None:
            p = head[li]
            head[li] = p.model_copy(update={"style": new_lead[0], "h": new_lead[1]})
        if dlead:
            fin.out = [q.model_copy(update={"y": q.y + dlead}) for q in fin.out]
        if new_foot:
            end = max(tail[i].y + tail[i].h for i in fis)
            y = end - sum(h for _st, h in new_foot.values())
            for i in fis:
                st, h = new_foot[i]
                tail[i] = tail[i].model_copy(update={"style": st, "y": y, "h": h})
                y += h
            for i, q in enumerate(tail):
                if isinstance(q.element, Text) and q.element.role == "conclusion":
                    tail[i] = q.model_copy(update={"y": q.y - dfoot})
        return


def _edges(out: list[Placed], tail: list[Placed]) -> tuple[int, int]:
    """(top of the body block, top of the conclusion / footnote zone): the lead growth moves them."""
    top = min((p.y for p in out), default=0)
    zone = min(
        (p.y for p in tail if isinstance(p.element, Text) and p.element.role in ("conclusion", "footnote")),
        default=0,
    )
    return top, zone


def _shifted(body: Rect, now: tuple[int, int], before: tuple[int, int]) -> Rect:
    """``body`` after the lead grew (top moves down) and the footnotes grew (bottom moves up)."""
    dtop = max(now[0] - before[0], 0)
    dbot = min(now[1] - before[1], 0)
    return Rect(body.x, body.y + dtop, body.w, body.h - dtop + dbot)


def _table_text(ctx: _Ctx, fc: _Ctx, run, body: Rect, elements: list) -> _Ctx:
    """A table that leaves the body mostly empty grows its text first, then its rows (``table_row_max_em``).

    Only slides of tables and text (no cards): the largest factor that fits wins, up to ``table_text_max`` x
    the theme body size and ``sparse_text_max_pt``. A candidate is refused when something overflows or rows
    wrap more than before. Explicit sizes (``sizes: table=``, CSS, ``{size=}``) never change.
    """
    lt = ctx.lt
    tabs = [p for p in fc.out if isinstance(p.element, Table)]
    if (
        lt.table_text_step <= 0
        or ctx.dense_k < 1.0  # dense decks keep their capped type
        or not tabs
        or any(isinstance(e, Container) for e in elements)
        or any(_table_size_explicit(fc, e) for e in elements if isinstance(e, Table))
    ):
        return fc
    free = body.bottom - _bottom(fc)
    if free <= lt.body_free_max * body.h:
        return fc
    body_pt = ctx.theme.sizes.get("body", DEFAULT_SIZES["body"]) * ctx.dense_k
    cap_pt = min(lt.sparse_text_max_pt, body_pt * lt.table_text_max)

    def size(p) -> float:
        return (p.style.font_size or 14) * p.font_scale

    def tall(c: _Ctx) -> int:  # rows above the cap: they wrapped
        n = 0
        for p in c.out:
            if isinstance(p.element, Table):
                lim = lt.table_row_max_em * size(p) * EMU_PER_PT * 1.02 if lt.table_row_max_em > 0 else 0
                n += sum(1 for h in p.element.attrs.get("_row_h", []) if lim and h > lim)
        return n

    s0 = max(size(p) for p in tabs)
    h0 = sum(p.h for p in tabs)
    top = min(cap_pt / max(s0, 1e-6), (h0 + free) / max(h0, 1))
    n = round((top - 1.0) / lt.table_text_step)
    base_tall = tall(fc)
    first: _Ctx | None = None
    for i in range(n):
        f = round(top - lt.table_text_step * i, 3)
        if f <= 1.0 + 1e-6:
            break
        c = run(
            body,
            grow=fc.grow,
            step=fc.step,
            roomy=fc.roomy,
            grow_base=fc.grow_base,
            expand=fc.expand,
            tgrow=f,
        )
        if c.over or not c.out or tall(c) > base_tall or _bottom(c) > body.bottom or _rewraps(c, fc, lt):
            continue
        first = c
        break
    got = max((size(p) for p in first.out if isinstance(p.element, Table)), default=0.0) if first else s0
    want = body_pt * lt.table_wrap_ratio
    if lt.table_wrap_ratio <= 0 or got >= want - 0.05 or s0 >= want:
        return first or fc
    # the table text is still below the body text of the deck: a tall free body lets cells wrap at a space
    top = min(want / max(s0, 1e-6), cap_pt / max(s0, 1e-6))
    for i in range(round((top - got / s0) / lt.table_text_step) + 1):
        f = round(top - lt.table_text_step * i, 3)
        if f * s0 <= got + 0.05:
            break
        c = run(
            body,
            grow=fc.grow,
            step=fc.step,
            roomy=fc.roomy,
            grow_base=fc.grow_base,
            expand=fc.expand,
            tgrow=f,
            twrap=True,
        )
        if c.over or not c.out or _bottom(c) > body.bottom:
            continue
        return c
    return first or fc


def _rewraps(c: _Ctx, fc: _Ctx, lt) -> bool:
    """A grown table whose rows would wrap more lines on columns ``l3_wrap_margin`` narrower (renders wrap
    earlier than the model: fallback fonts, Vietnamese diacritics) than the same table before growing."""
    olds = [p for p in fc.out if isinstance(p.element, Table)]
    news = [p for p in c.out if isinstance(p.element, Table)]
    if len(olds) != len(news):
        return False
    k = 1.0 - lt.l3_wrap_margin
    for a, b in zip(olds, news, strict=True):
        cw = b.element.attrs.get("_col_w")
        if not cw:
            continue
        _n, _m, anchors = table_grid(b.element)
        narrow = [max(1, round(w * k)) for w in cw]
        f = b.font_scale / max(a.font_scale, 1e-6)
        old = row_heights(b.element, anchors, narrow, a.style, a.font_scale)
        new = row_heights(b.element, anchors, narrow, b.style, b.font_scale)
        if any(y > x * f * 1.02 for x, y in zip(old, new, strict=False)):
            return True
    return False


def _panel_step(ctx: _Ctx, fc: _Ctx, run, body: Rect, stepped: list[float], panel: float) -> _Ctx:
    """Text of a panel beside a chart / image grows (largest step that fits) to use the panel height."""
    top = ctx.lt.sparse_step_max
    n = round((top - ctx.lt.sparse_step_min) / 0.05)
    for i in range(n + 1):
        st = round(top - 0.05 * i, 2)
        c = run(body, grow=round(fc.grow * st, 2), step=st, roomy=True, grow_base=fc.grow, expand=fc.expand)
        if c.over or not c.out or _panel_fill(c.out) <= panel + 0.02:
            continue
        big = max(
            (
                (p.style.font_size or 0) * p.font_scale
                for p in c.out
                if isinstance(p.element, Text)
                and p.element.role == "body"
                and not _explicit_size(c, p.element)
            ),
            default=0,
        )
        if big > ctx.lt.sparse_low_max_pt + 1e-6:
            continue
        stepped[0], stepped[1] = st, fc.grow
        return c
    return fc


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


def _layout_free(ctx: _Ctx, elements: list, body: Rect, slide: Slide, theme: Theme, sg: int) -> _Ctx:
    """`@free`: blocks with a box sit exactly there (no growth, balance or search); the rest stack on top."""
    c = _Ctx(
        ctx.deck,
        theme,
        slide,
        ctx.index,
        ctx.W,
        ctx.H,
        dense_k=ctx.dense_k,
        tight=ctx.tight,
        css=ctx.css,
    )
    inherit = fast_style()
    for n in slide.classes:
        if n in theme.classes:
            inherit = inherit.merged(_only_inheritable(theme.classes[n]))
    inherit = inherit.merged(_only_inheritable(ctx.css.own(slide)))
    loose = []
    for b in elements:
        bx = getattr(b, "box", None)
        if bx is not None and any(v is not None for v in (bx.x, bx.y, bx.w, bx.h)):
            _place_block(c, b, _apply_box(c, b, body, True), inherit)
        else:
            loose.append(b)
    y = body.y
    for b in loose:
        h = _natural_height(c, b, body.w, inherit)
        if h is None:
            h = round(min(body.bottom - y, body.h * 0.4))
        h = max(min(h, body.bottom - y), 0)
        _place_block(c, b, Rect(body.x, y, body.w, h), inherit)
        y += h + sg
        c.diag(
            "free-unplaced",
            f"{_label(b)} has no position on a @free slide",
            "add {x= y= w= h=} (e.g. {x=10% y=30% w=40% h=20%}) to place it",
            level="info",
            line=getattr(b, "line", None),
        )
    return c


_CONC_TRIAL: list[bool] = []  # non-empty while a trial layout (bar at its theme size) is measuring the body


def _conclusion_style(ctx: _Ctx, slide: Slide, st: Style, index: int) -> Style:
    """The conclusion bar is never smaller than the largest card / box body text of its slide.

    A trial layout with the bar at its theme size measures that text (after sparse growth); the bar then takes
    ``conclusion_min_ratio`` x that size, clamped to [theme size, ``conclusion_max_pt``]. Explicit sizes
    (``sizes: conclusion=``, CSS, ``{size=}``) win.
    """
    lt = ctx.lt
    base = _role_style(ctx, "conclusion").font_size
    if "conclusion" in ctx.theme.sizes and st.font_size == base:  # `sizes: conclusion=N`
        return st.merged(fast_style(font_size=ctx.theme.sizes["conclusion"]))
    if _CONC_TRIAL or st.font_size != base:
        return st
    if slide.layout in ("free", "cover", "section", "blank") or not slide.elements:
        return st
    lines = ["".join(r.text for r in p.runs) for p in slide.conclusion.paragraphs] if slide.conclusion else []
    em = max((measure.text_em(t, bold=True, font=st.font) for t in lines if t.strip()), default=0.0)
    pad = 4 * measure.cell_pad()[0]  # text insets of the bar, generously
    room = (ctx.W - 2 * to_emu(ctx.theme.margin_x) - pad) / EMU_PER_PT * (1.0 - lt.l3_wrap_margin)
    if not lt.conclusion_min_ratio:
        return _bar_shrink(st, base, em, room, base, lt)
    trial = ctx.deck.model_copy(update={"diagnostics": []})
    _CONC_TRIAL.append(True)
    try:
        placed = _layout(slide, trial, ctx.theme, index)
    finally:
        _CONC_TRIAL.pop()
    sizes = [
        p.style.font_size * p.font_scale
        for p in placed
        if isinstance(p.element, Text) and p.element.role == "body" and p.style.font_size
    ]
    if not sizes:
        return _bar_shrink(st, base, em, room, base, lt)
    want = min(max(base, max(sizes) * lt.conclusion_min_ratio), max(lt.conclusion_max_pt, base))
    return _bar_shrink(st, base, em, room, want, lt)


def _bar_shrink(st: Style, base: float, em: float, room: float, want: float, lt: LayoutTokens) -> Style:
    """The bar text (``want`` pt, at least ``base``) stays on one line: it shrinks step by step to the floor
    (``conclusion_min_scale`` x ``base``, never below 12pt) before the bar may wrap; a text that does not fit
    even there wraps at the theme size."""
    if em > 0 and em * want > room:
        if room / em >= base:
            want = room / em  # grown text shrinks to the line
        else:  # even the theme size wraps: step down to the floor, else wrap at the theme size
            floor = min(base, max(base * lt.conclusion_min_scale, 12.0))
            size = base
            while em * size > room and size > floor + 1e-6:
                size = max(size - 0.5, floor)
            want = size if em * size <= room else base
    return st if abs(want - base) < 1e-6 else st.merged(fast_style(font_size=want))


def _anchored_cover(ctx: _Ctx, slide: Slide, sub, head: list, tail: list, put, fit_text, dims) -> Rect | None:
    """Cover composed from tokens: a band (``cover.band_h`` of the height, filled when ``title.band`` is set)
    anchored to the top, the title (+ subtitle) bottom-aligned in it ``cover.pad`` above its edge, a thin
    ``cover.rule`` along that edge and the deck footer as a quiet caption at the bottom (``cover.footer``)."""
    W, H, Mx, My, sg, inner_w = dims
    theme, deck = ctx.theme, ctx.deck
    bh = round(H * theme.cover_band_h)
    rh = _emu(theme.cover_rule_h) if theme.cover_rule else 0
    if theme.title_band:
        put(
            head,
            Shape(shape="rect", id="band"),
            Rect(0, 0, W, bh),
            fast_style(fill=theme.title_band, line=None),
        )
    bottom = bh - _emu(theme.cover_pad)
    air = _emu(theme.cover_gap)
    s_r = None
    sh = 0
    if sub:
        s_st = _role_style(ctx, "subtitle", cover=True)
        if theme.title_band:
            s_st = s_st.merged(fast_style(color=theme.title_band_color))
        s_st = _styled(ctx, sub, s_st.merged(fast_style(valign="top")), classes=False)
        s_fs = fit_text(sub, Rect(Mx, 0, inner_w, round(bh * 0.25)), s_st)
        sh = round(_text_need(ctx, sub, s_st, inner_w, s_fs))
        s_r = Rect(Mx, bottom - sh, inner_w, sh)
    if slide.title:
        t_st = _role_style(ctx, "title", cover=True).merged(fast_style(valign="bottom"))
        if theme.title_band:
            t_st = t_st.merged(fast_style(color=theme.title_band_color))
        t_st = _styled(ctx, slide.title, t_st, classes=False)
        room = max(bottom - sh - (air if sh else 0) - My, 1)
        t_r = Rect(Mx, bottom - sh - (air if sh else 0) - room, inner_w, room)
        t_fs = fit_text(slide.title, t_r, t_st)
        t_fs = _grow_cover_title(ctx, slide.title, t_st, t_r, t_fs)
        th = round(_text_need(ctx, slide.title, t_st, inner_w, t_fs))
        put(head, slide.title, Rect(Mx, t_r.bottom - th, inner_w, th), t_st, t_fs)
    if s_r is not None:
        put(head, sub, s_r, s_st, s_fs)
    if rh:
        full = theme.title_band is not None
        put(
            head,
            Shape(shape="rect", id="rule"),
            Rect(0 if full else Mx, bh, W if full else inner_w, rh),
            fast_style(fill=theme.cover_rule, line=None),
        )
    foot_h = round(0.26 * EMU_PER_INCH)
    foot_y = H - foot_h - round(0.1 * EMU_PER_INCH)
    if theme.cover_footer and deck.footer:
        put(
            tail,
            _text_el("caption", deck.footer, {"field": "footer"}),
            Rect(Mx, foot_y, round(inner_w * 0.7), foot_h),
            _role_style(ctx, "caption").merged(fast_style(valign="middle")),
        )
    if not slide.elements:
        return None
    top = bh + rh + sg
    return Rect(Mx, top, inner_w, max(foot_y - top - sg, 0))


def _chevron_steps(slide: Slide, lt: LayoutTokens) -> Slide:
    """A chevron row alone on the slide whose steps all carry short bodies is built as ``@steps``.

    ``@chevron`` with one or two bullets per heading otherwise renders as a thin strip; ``@steps`` (arrows
    with a card under each) fills the body, so an agent gets the full-slide form with either spelling.
    Plain chevrons (no bodies), longer bodies (``chevron_steps_items``), other blocks on the slide,
    connectors and explicit boxes keep the chevron row."""
    els = slide.elements
    if (
        not lt.chevron_steps
        or lt.body_valign == "top"
        or "chevron" not in slide.classes
        or "steps" in slide.classes
        or slide.links
        or len(els) < 2
        or any(
            not (isinstance(e, Container) and e.title is not None and e.children and not e.links) for e in els
        )
        or any(
            not isinstance(ch, Text) or ch.box is not None or ch.role != "body"
            for e in els
            for ch in e.children
        )
        or any(sum(len(ch.paragraphs) for ch in e.children) > lt.chevron_steps_items for e in els)
    ):
        return slide
    from ..parser.core import group_steps, steps_grid_ok

    grid = (slide.grid or "").strip()
    new = slide.model_copy(deep=False)
    new.classes = [c for c in slide.classes if c not in ("steps", "chevron")]
    group_steps(new, list(els), grid if steps_grid_ok(grid, len(els)) else str(len(els)))
    return new


def _attach_bar(
    out: list[Placed], body: Rect, tail: list[Placed], bar: Text | None, lt: LayoutTokens
) -> list[Placed]:
    """The conclusion bar moves up to ``bar_attach_gap`` under the lone table above it (never down)."""
    if bar is None or lt.bar_attach == "off":
        return tail
    tab = lone_table(_body_items(out, body))
    if tab is None:
        return tail
    y = tab.y + tab.h + to_emu(lt.bar_attach_gap)
    return [p.model_copy(update={"y": y}) if p.element is bar and y < p.y else p for p in tail]


def _layout(slide: Slide, deck: Deck, theme: Theme, index: int) -> list[Placed]:
    slide = _chevron_steps(slide, theme.layout)
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
    if kind not in ("cover", "section", "blank", "center", "content", "free"):
        if kind:
            ctx.diag(
                "layout",
                f"unknown layout {kind!r}",
                "use cover, section, blank, center or free; using automatic",
            )
        kind = None
    if kind is None:
        kind = "content"
        if slide.title and not slide.elements and not slide.conclusion:
            kind = "cover" if index == 0 else "section"
    if deck.css or slide.css:
        ctx.css = css.CssIndex(deck, slide, index, kind)
        for n in {id(n): n for n in ctx.css.nodes.values()}.values():
            if n.kind == "table" and "gantt" in n.classes:  # `.gantt` rules style the bars, not the grid
                n.classes = n.classes - {"gantt"}

    Mx, My = to_emu(theme.margin_x), to_emu(theme.margin_y)
    gap = to_emu(theme.gap)
    sg = round(gap * 0.5)
    inner_w = W - 2 * Mx

    head: list[Placed] = []
    tail: list[Placed] = []
    reserved: tuple[Style, int] | None = None  # style and height of the empty lead slot kept for the body y

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
        sub = slide.subtitle or slide.lead
        if kind == "cover" and theme.cover_band_h > 0 and not _cover_explicit(ctx, slide.title, sub):
            body = _anchored_cover(ctx, slide, sub, head, tail, put, fit_text, (W, H, Mx, My, sg, inner_w))
            y_top = 0
        else:
            band_h = round(H * 0.34)
            by = round(H * 0.24)
            composed = (
                kind == "cover" and ctx.lt.cover_title_y > 0 and not _cover_explicit(ctx, slide.title, sub)
            )
            if composed:
                by = (
                    round(H * ctx.lt.cover_title_y) - band_h // 2
                )  # the band (or its title block) is centred here
            if theme.title_band:
                put(
                    head,
                    Shape(shape="rect", id="band"),
                    Rect(0, by, W, band_h),
                    fast_style(fill=theme.title_band, line=None),
                )
            t_st = s_st = None
            t_r = s_r = None
            t_fs = s_fs = 1.0
            if slide.title:
                t_st = _role_style(ctx, "title", cover=True)
                t_st = t_st.merged(fast_style(valign="bottom"))
                if theme.title_band:
                    t_st = t_st.merged(fast_style(color=theme.title_band_color))
                t_r = Rect(Mx, by, inner_w, round(band_h * 0.65))
                t_st = _styled(ctx, slide.title, t_st, classes=False)
                t_fs = fit_text(slide.title, t_r, t_st)
                if composed:
                    t_fs = _grow_cover_title(ctx, slide.title, t_st, t_r, t_fs)
            if sub:
                s_st = _role_style(ctx, "subtitle", cover=True)
                if theme.title_band:
                    s_st = s_st.merged(fast_style(color=theme.title_band_color))
                s_r = Rect(Mx, by + round(band_h * 0.68), inner_w, round(band_h * 0.3))
                s_st = _styled(ctx, sub, s_st.merged(fast_style(valign="top")), classes=False)
                s_fs = fit_text(sub, s_r, s_st)
            if composed and t_r is not None:  # title + subtitle: one block, centred on the token line
                th = round(_text_need(ctx, slide.title, t_st, t_r.w, t_fs))
                sh = round(_text_need(ctx, sub, s_st, s_r.w, s_fs)) if s_r is not None else 0
                sp = sg if sh else 0
                top = round(H * ctx.lt.cover_title_y) - (th + sp + sh) // 2
                t_r = Rect(Mx, top, inner_w, th)
                if s_r is not None:
                    s_r = Rect(Mx, top + th + sp, inner_w, sh)
            if t_r is not None:
                put(head, slide.title, t_r, t_st, t_fs)
            if s_r is not None:
                put(head, sub, s_r, s_st, s_fs)
            body = (
                Rect(Mx, by + band_h + sg, inner_w, H - (by + band_h + sg) - My) if slide.elements else None
            )
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
                st = st.merged(fast_style(color=theme.title_band_color))
                put(
                    head,
                    Shape(shape="rect", id="band"),
                    Rect(0, 0, W, tr_h + My // 2),
                    fast_style(fill=theme.title_band, line=None),
                )
                r = Rect(Mx, 0, inner_w, tr_h + My // 2)
                y = tr_h + My // 2 + sg
                head_bottom = r.bottom
            else:
                r = Rect(Mx, My, inner_w, tr_h)
                y = My + tr_h
                head_bottom = y
            if kind == "free" and getattr(slide.title, "box", None) is not None:
                r = _apply_box(ctx, slide.title, Rect(0, 0, W, H), True)  # an explicit title box wins
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
        if (
            kind == "content"
            and slide.title
            and slide.lead is None
            and slide.subtitle is None
            and head_bottom is not None
            and _reserve_lead(deck, ctx.lt.reserve_lead)
        ):  # most slides of the deck have a lead line: keep its slot so the body starts at the same y
            st = _styled(ctx, _text_el("lead", "x"), _role_style(ctx, "lead"))
            h = round(_text_need(ctx, _text_el("lead", "x"), st, inner_w, 1.0))
            reserved = (st, h)
            head_bottom = y + (sg // 2 if y == My else 0) + h
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
                cst.merged(fast_style(valign="middle")),
            )
        if deck.slide_number:
            put(
                tail,
                _text_el("caption", str(index + 1), {"field": "slide_number"}),
                Rect(W - Mx - round(0.9 * EMU_PER_INCH), fy, round(0.9 * EMU_PER_INCH), fh),
                cst.merged(fast_style(align="right", valign="middle")),
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
            foot_air = max(sg // 2, _emu(ctx.lt.footnote_gap)) if _has_chart(slide.elements) else sg // 2
            if slide.conclusion is not None and slide.conclusion.paragraphs:
                foot_air = max(foot_air, _emu(ctx.lt.conclusion_foot_gap), round(gap * ctx.lt.conclusion_gap))
            bottom = bottom - sum(hs) - foot_air
        if slide.conclusion is not None and slide.conclusion.paragraphs:
            c = slide.conclusion
            if show_row and not notes:  # no footnote between them: one card gutter above the footer line
                bottom -= max(0, max(sg, round(gap * ctx.lt.conclusion_gap)) - sg // 2)
            st = _styled(ctx, c, _role_style(ctx, "conclusion"))
            st = _conclusion_style(ctx, slide, st, index)
            h = max(round(_text_need(ctx, c, st, inner_w, 1.0)), round(0.4 * EMU_PER_INCH))
            h = min(h, round(H * ctx.lt.footnote_max))
            eff = fit_text(c, Rect(0, 0, inner_w, h), st)
            put(tail, c, Rect(Mx, bottom - h, inner_w, h), st, eff)
            bottom = bottom - h - max(sg, round(gap * ctx.lt.conclusion_gap))  # one card gutter above the bar
        body = Rect(Mx, y_top, inner_w, bottom - y_top)
        if kind == "blank":
            body = Rect(Mx, My, inner_w, bottom - My)

    # ---- body with global autofit
    elements = list(slide.elements)
    final_ctx: _Ctx | None = None
    if kind == "free" and body is not None and elements and body.h > 0:
        final_ctx = _layout_free(ctx, elements, body, slide, theme, sg)
        ctx.diags += final_ctx.diags
        for lab in dict.fromkeys(final_ctx.over):
            ctx.diag("overflow", f"{lab} overflows its box", "enlarge its {x= y= w= h=} or shorten the text")
    elif body is not None and elements and body.h > 0:
        slide_inherit = fast_style()
        for n in slide.classes:
            if n in theme.classes:
                slide_inherit = slide_inherit.merged(_only_inheritable(theme.classes[n]))
        slide_inherit = slide_inherit.merged(_only_inheritable(ctx.css.own(slide)))
        if kind == "center":
            slide_inherit = slide_inherit.merged(fast_style(align="center", valign="middle"))
        sgap = _gap(ctx, slide.attrs.get("gap") or ctx.css.own(slide).gap, body.w)

        body_pt = theme.sizes.get("body", DEFAULT_SIZES["body"]) * ctx.dense_k
        very = body_pt >= ctx.lt.grow_very_sparse_pt and _very_sparse(elements)
        text_only = kind != "center" and all(
            isinstance(e, Text) and e.role == "body" and "callout" not in e.classes for e in elements
        )

        def solve(arrange: str | None = None, complete: bool = False) -> _Ctx:
            stepped: list[float] = [1.0, 1.0]  # sparse step, growth before it

            def run(area: Rect, **kw) -> _Ctx:
                if stepped[0] > 1.0:  # every later run keeps the slide's sparse step
                    kw.setdefault("step", stepped[0])
                    kw.setdefault("roomy", True)
                    kw.setdefault("grow_base", stepped[1])
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
                if ctx.dense_k >= 1.0:
                    top = min(top, max(ctx.lt.grow_max, 1.0))
                n = round((top - 1.05) / 0.05)
                for g in [round(top - 0.05 * i, 2) for i in range(n + 1)]:
                    c3 = run(body, grow=g)
                    if c3.grew and not c3.over and (c3.fill is None or c3.fill <= ctx.lt.grow_fill):
                        fc = c3
                        break
            if fc.scale >= 1.0 and not fc.over and ctx.lt.grow and ctx.lt.sparse_step > 1.0:
                fc = _sparse_step(ctx, fc, run, body, stepped)
            if fc.scale >= 1.0 and not fc.over:
                fc = _spread(ctx, fc, run, body, elements)
                fc = _table_text(ctx, fc, run, body, elements)
                if complete:
                    fc = _complete(ctx, fc, run, body, elements)
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
        if _needs_complete(ctx, final_ctx, body, elements):  # the search judged the plain arrangements
            done = solve(chosen, complete=True)
            if done.out and not done.over:
                final_ctx = done
        if kind == "content" and not final_ctx.over and final_ctx.out:
            if slide.links:  # org chart / issue tree: grow it down the body (diagram.fill_tree)
                final_ctx.out = fill_tree(
                    final_ctx.out,
                    body,
                    ctx.lt,
                    _emu(ctx.lt.top_gap) if (slide.conclusion or slide.footnotes) else 0,
                )
            final_ctx.out = fill_steps(final_ctx.out, body, ctx.lt)
            final_ctx.out = align_chevron_table(final_ctx.out, body, ctx.lt)
            final_ctx.out = grow_chevron_table(final_ctx.out, body, ctx.lt)
            final_ctx.out = fill_body(
                final_ctx.out,
                body,
                ctx.lt.body_free_max,
                "top" if final_ctx.completed else ctx.lt.body_valign,
                ctx.lt.body_spread_max,
                _emu(ctx.lt.top_gap) if (slide.conclusion or slide.footnotes) else 0,
                ctx.lt.center_min_fill,
                ctx.lt.card_pad_share,
                ctx.lt.card_stretch,
                ctx.lt.card_stretch_share,
                ctx.lt.table_row_max_em,
            )
        to_bar: tuple[bool, bool, bool] | None = None
        if kind == "content" and not final_ctx.over and final_ctx.out:
            linked_sparse = bool(slide.links) and (
                body.bottom - _content_bottom(final_ctx.out) > round(ctx.lt.sparse_left_max * body.h)
            )  # a flow row: the sparse completion skips linked slides, the row fill does not
            # a sparse row of text cards: top-anchored, tall, spread; above a table it only shrinks to content
            small = theme.sizes.get("body", DEFAULT_SIZES["body"]) <= ctx.lt.grow_small_pt
            has_bar = slide.conclusion is not None and bool(slide.conclusion.paragraphs)
            to_bar_args = (
                has_bar,
                bool(final_ctx.completed) or _block_h(final_ctx.out) < ctx.lt.center_min_fill * body.h,
                bool(slide.footnotes),
            )
            if fill_cards_to_bar(final_ctx.out, body, ctx.lt, *to_bar_args, small) is not None:
                to_bar = to_bar_args  # applied after the lead / footnote growth (it moves the body edges)
            else:
                final_ctx.out = fill_row(
                    final_ctx.out,
                    body,
                    ctx.lt,
                    consulting=final_ctx.dense_k < 1.0 or small,
                    sparse=bool(final_ctx.completed or linked_sparse),
                )
            small_body = theme.sizes.get("body", DEFAULT_SIZES["body"]) <= ctx.lt.grow_small_pt
            final_ctx.out = fill_panels(
                final_ctx.out,
                body,
                ctx.lt,
                consulting=final_ctx.dense_k < 1.0 or small_body,
                title_scale=theme.render.chart_title_scale,
            )
            final_ctx.out = fill_chevron_row(final_ctx.out, body, ctx.lt)
        edge0 = _edges(final_ctx.out, tail)
        if (
            ctx.dense_k >= 1.0
            and ctx.lt.grow
            and not final_ctx.over
            and (final_ctx.completed or final_ctx.step > 1.0)
        ):
            _grow_head(
                ctx, final_ctx, head, tail, body, inner_w, reserved
            )  # dense decks keep their size ratios
        if to_bar is not None:  # cards reach the conclusion bar (replaces the sparse row fill)
            edge = _edges(final_ctx.out, tail)
            fin = fill_cards_to_bar(final_ctx.out, _shifted(body, edge, edge0), ctx.lt, *to_bar, small)
            if fin is not None:
                final_ctx.out = fin
        body_now = _shifted(
            body, _edges(final_ctx.out, tail), edge0
        )  # the body after the lead / footnote growth
        if kind == "content" and not final_ctx.over and final_ctx.out:  # a lone KPI row: content-sized cards
            fixed = any(
                isinstance(e, Container) and "kpi" in e.classes and _kpi_explicit(final_ctx, e)
                for e in slide.elements
            )
            lone = fit_lone_kpi(final_ctx.out, body_now, ctx.lt, has_bar, fixed)
            final_ctx.out = (
                scale_kpi_values(final_ctx.out, body_now, ctx.lt, fixed) if lone is final_ctx.out else lone
            )
        if (
            kind == "content"
            and not final_ctx.over
            and final_ctx.out
            and not slide.links
            and theme.sizes.get("body", DEFAULT_SIZES["body"]) <= ctx.lt.grow_small_pt
            and not any(
                _table_size_explicit(final_ctx, e) if isinstance(e, Table) else _explicit_size(final_ctx, e)
                for e in slide.elements
                if isinstance(e, (Table, Text))
            )
        ):  # small-body (consulting) themes: a short list / a lone table use the body (pinned sizes stay)
            final_ctx.out = fill_text_list(final_ctx.out, body_now, ctx.lt)
            lone = fill_table_free(
                final_ctx.out,
                body_now,
                ctx.lt,
                slide.conclusion is not None and bool(slide.conclusion.paragraphs),
            )
            final_ctx.out = lone
            tail = _attach_bar(final_ctx.out, body_now, tail, slide.conclusion, ctx.lt)
        if (
            kind == "content"
            and not final_ctx.over
            and final_ctx.out
            and not slide.links
            and not has_bar  # a conclusion bar anchors the block (fill_cards_to_bar owns that case)
            and final_ctx.dense_k >= 1.0
            and theme.sizes.get("body", DEFAULT_SIZES["body"]) > ctx.lt.grow_small_pt
        ):  # normal density: a block that still leaves a band under it sits at the optical center
            final_ctx.out = center_band(final_ctx.out, body_now, ctx.lt)
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
    if final_ctx:
        final_ctx.out = expand_notes(
            final_ctx.out,
            theme,
            lambda msg, hint: deck.diagnostics.append(
                Diagnostic(level="warning", message=msg, slide=index + 1, rule="chart-note", hint=hint)
            ),
        )
    if final_ctx:
        for p in final_ctx.out:
            if isinstance(p.element, Chart) and (warn := scale_warning(p.element, theme)):
                deck.diagnostics.append(
                    Diagnostic(
                        level="info", message=warn[0], slide=index + 1, rule="chart-scale", hint=warn[1]
                    )
                )
    if final_ctx and any(
        isinstance(p.element, Table) and "gantt" in p.element.classes for p in final_ctx.out
    ):
        final_ctx.out = expand_gantt(
            final_ctx.out,
            theme,
            lambda pl: _gantt_style(ctx, pl),
            ctx.lt.gantt_pad,
            ctx.lt.gantt_bar,
            lambda msg, hint: deck.diagnostics.append(
                Diagnostic(level="warning", message=msg, slide=index + 1, rule="gantt-text", hint=hint)
            ),
            (lambda pl, cell: _pill_style(ctx, pl, cell)) if ctx.lt.table_pills else None,
        )
    if (
        final_ctx
        and ctx.lt.table_pills
        and any(isinstance(p.element, Table) and has_pills(p.element) for p in final_ctx.out)
    ):
        final_ctx.out = expand_pills(
            final_ctx.out, theme, lambda pl, cell: _pill_style(ctx, pl, cell), ctx.lt.pill_h
        )
    return head + (final_ctx.out if final_ctx else []) + tail
