"""Layout engine: ``Slide`` -> ``list[Placed]`` in absolute EMU. Never touches python-pptx."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..ir import (
    Box,
    Chart,
    Code,
    Container,
    Deck,
    Diagnostic,
    Image,
    Link,
    Paragraph,
    Placed,
    Raw,
    Shape,
    Slide,
    Style,
    Table,
    Text,
)
from ..theme import Theme
from ..units import EMU_PER_INCH, EMU_PER_PT, slide_size, to_emu
from . import measure
from .grid import Rect, auto_spec, cell_rects, parse_spec
from .tables import column_widths, row_heights, table_grid

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
_VISUALS = (Image, Chart, Table, Code)
_TOL = 1.01
CHEVRON_ADJ = 0.3  # chevron point depth / shorter side; the renderer sets the same adjustment
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


def _text_need(ctx: _Ctx, el: Text | Shape, style: Style, width: int, scale: float) -> float:
    pad = _pad(style)
    return measure.paragraphs_height(el.paragraphs, width - 2 * pad, style, scale) + 2 * pad


def _natural_height(ctx: _Ctx, el, width: int, inherit: Style) -> int | None:
    """Natural height for stackable elements, ``None`` for flexible ones."""
    if isinstance(el, Text):
        st = _text_style(ctx, el, inherit)
        eff = measure.effective_scale(st.font_size or 18, ctx.scale, ctx.theme.min_font_size)
        return round(_text_need(ctx, el, st, width, eff))
    if isinstance(el, Code):
        st = _code_style(ctx, el)
        eff = measure.effective_scale(st.font_size or 14, ctx.scale, ctx.theme.min_font_size)
        pad = _pad(st)
        return round(measure.code_height(el.text, width - 2 * pad, (st.font_size or 14) * eff) + 2 * pad)
    if isinstance(el, Table):
        _, _, _, _, rh = _table_geom(ctx, el, width)
        return sum(rh)
    return None


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


def _table_geom(ctx: _Ctx, el: Table, width: int):
    st = _table_style(ctx, el)
    eff = measure.effective_scale(st.font_size or 14, ctx.scale, ctx.theme.min_font_size)
    nrows, ncols, anchors = table_grid(el)
    cw = column_widths(el, ncols, anchors, width)
    rh = row_heights(el, anchors, cw, st, eff)
    return st, eff, anchors, cw, rh


def _place_block(ctx: _Ctx, el, rect: Rect, inherit: Style) -> None:
    if rect.w <= 0 or rect.h <= 0:
        return
    if isinstance(el, (Text, Shape)):
        st = _text_style(ctx, el, inherit)
        eff = measure.effective_scale(st.font_size or 18, ctx.scale, ctx.theme.min_font_size)
        need = _text_need(ctx, el, st, rect.w, eff)
        if need > rect.h * _TOL:
            ctx.over.append(_label(el))
        ctx.emit(el, rect, st, eff)
    elif isinstance(el, Code):
        st = _code_style(ctx, el)
        eff = measure.effective_scale(st.font_size or 14, ctx.scale, ctx.theme.min_font_size)
        pad = _pad(st)
        need = measure.code_height(el.text, rect.w - 2 * pad, (st.font_size or 14) * eff) + 2 * pad
        if need > rect.h * _TOL:
            ctx.over.append(_label(el))
        ctx.emit(el, Rect(rect.x, rect.y, rect.w, min(round(need), rect.h)), st, eff)
    elif isinstance(el, Table):
        st, eff, _anchors, cw, rh = _table_geom(ctx, el, rect.w)
        total = sum(rh)
        if total > rect.h * _TOL:
            ctx.over.append(_label(el))
        attrs = {**el.attrs, "_col_w": cw, "_row_h": rh}
        ctx.emit(
            el.model_copy(update={"attrs": attrs}),
            Rect(rect.x, rect.y, rect.w, min(total, rect.h) if total > rect.h else total),
            st,
            eff,
        )
    elif isinstance(el, Chart):
        t = ctx.theme
        st = Style(
            font=t.fonts.body, font_ea=t.fonts.ea, font_size=t.sizes.get("table", 14), color="fg"
        ).merged(el.style)
        ctx.emit(el, rect, st)
    elif isinstance(el, Image):
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
        ctx.emit(el, rect, st)
    elif isinstance(el, Container):
        _place_container(ctx, el, rect, inherit)


def _card_style(ctx: _Ctx, c: Container) -> Style:
    if "plain" in c.classes:
        base = Style(padding="0pt")
    else:
        base = ctx.theme.classes.get(
            "card", Style(fill="surface", line="border", line_width=0.75, radius=6, padding="10pt")
        )
    others = _class_styles(ctx, c, skip=("plain", "kpi"))
    return _tighten(ctx, Style().merged(base, *others, c.style))


def _place_container(ctx: _Ctx, c: Container, rect: Rect, inherit: Style) -> None:
    style = _card_style(ctx, c)
    pad = _pad(style, 10 * EMU_PER_PT * ctx.tight)
    ctx.emit(c, rect, style)
    inner = rect.inset(pad)
    y = inner.y
    child_inherit = inherit.merged(_only_inheritable(style))
    kpi = "kpi" in c.classes
    band = None if kpi else ctx.theme.heading_band
    if c.title is not None and c.title.paragraphs:
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
        if band:
            hh = round(_text_need(ctx, h_el, hst, rect.w, eff))
            if hh > rect.h * _TOL:
                ctx.over.append(_label(c))
            band_rect = Rect(rect.x, rect.y, rect.w, min(hh, rect.h))
            ctx.emit(h_el, band_rect, hst, eff)
            y = band_rect.bottom + round(pad * 0.5)
        else:
            hh = round(_text_need(ctx, h_el, hst, inner.w, eff))
            if hh > inner.h * _TOL:
                ctx.over.append(_label(c))
            ctx.emit(h_el, Rect(inner.x, y, inner.w, min(hh, inner.h)), hst, eff)
            y += hh + round(pad * 0.5)
    area = Rect(inner.x, y, inner.w, max(inner.bottom - y, 0))
    if not c.children:
        return
    gap = _gap(ctx, c.gap, inner.w, small=True)
    children = c.children
    if kpi:
        children = _kpi_children(ctx, children, area.w)
    if c.grid or any(n in ("flow", "chevron") for n in c.classes):
        _place_blocks(ctx, children, area, child_inherit, c.grid, c.classes, gap, c, c.links)
    else:
        rects = _place_stack(ctx, children, area, child_inherit, gap, c, center=kpi and len(children) == 1)
        _emit_links(ctx, c.links, rects)


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
    if used > area.h * _TOL:
        ctx.over.append(_label(owner) if owner is not None else "content")
    return rects


def _chevron_shape(blk) -> Shape:
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


def _block_kind_hint(blocks: list) -> tuple[bool, bool]:
    """(text_visual, short) hints for the automatic arrangement."""
    text_visual = (
        len(blocks) == 2
        and sum(isinstance(b, Text) for b in blocks) == 1
        and sum(isinstance(b, _VISUALS) for b in blocks) == 1
    )

    def size(b) -> int:
        if isinstance(b, Text):
            return len(_plain(b.paragraphs))
        if isinstance(b, Container):
            return sum(size(c) for c in b.children) + (len(_plain(b.title.paragraphs)) if b.title else 0)
        return 10_000

    return text_visual, all(size(b) <= 80 for b in blocks)


def _cx(r: Rect) -> int:
    return r.x + r.w // 2


def _cy(r: Rect) -> int:
    return r.y + r.h // 2


def _emit_links(ctx: _Ctx, links: list[Link], rects: dict[int, Rect]) -> None:
    """Connectors between block rects, emitted after the blocks so they sit on top."""
    for ln in links:
        a, b = rects.get(ln.src), rects.get(ln.dst)
        if a is None or b is None or ln.src == ln.dst:
            ctx.diag(
                "link",
                f"connector {ln.src}>{ln.dst} refers to a block that does not exist",
                "use block letters/numbers that exist in this grid, e.g. @abc a>b>c",
            )
            continue
        v_overlap = min(a.bottom, b.bottom) - max(a.y, b.y)
        h_overlap = min(a.right, b.right) - max(a.x, b.x)
        if h_overlap > 0 and v_overlap > 0:
            continue  # overlapping blocks (area spans): nothing sensible to draw
        if v_overlap > 0:
            horizontal = True
        elif h_overlap > 0:
            horizontal = False
        else:
            horizontal = abs(_cx(b) - _cx(a)) >= abs(_cy(b) - _cy(a))
        if horizontal:
            if _cx(b) >= _cx(a):
                p0, p1 = (a.right, _cy(a)), (b.x, _cy(b))
            else:
                p0, p1 = (a.x, _cy(a)), (b.right, _cy(b))
        elif _cy(b) >= _cy(a):
            p0, p1 = (_cx(a), a.bottom), (_cx(b), b.y)
        else:
            p0, p1 = (_cx(a), a.y), (_cx(b), b.bottom)
        attrs = {"head": "arrow" if ln.arrow else "none", "flip_h": p1[0] < p0[0], "flip_v": p1[1] < p0[1]}
        rect = Rect(min(p0[0], p1[0]), min(p0[1], p1[1]), abs(p1[0] - p0[0]), abs(p1[1] - p0[1]))
        ctx.emit(Shape(shape="line", attrs=attrs), rect, Style(line="primary", line_width=1.5))


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
        gs = auto_spec(len(flow), text_visual=text_visual, short=short)
    # blocks beyond the grid's cells are stacked full width below it
    extra: list[tuple[int, object]] = []
    if gs.capacity is not None and len(flow) > gs.capacity:
        extra = flow[gs.capacity :]
        flow = flow[: gs.capacity]
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
    for (i, blk), r in zip(flow, cells, strict=True):
        r = _apply_box(ctx, blk, r, False)
        rects[i] = r
        if "chevron" in flags and isinstance(blk, (Text, Shape, Container)):
            rects[i] = _place_chevron(ctx, blk, r, inherit)
        else:
            _place_block(ctx, blk, r, inherit)
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
    _emit_links(ctx, links or [], rects)


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
        cw = (area.w - gap * (len(gs.cols) - 1)) / max(len(gs.cols), 1)
        compact = max(round(cw * 0.45), round(0.9 * EMU_PER_INCH))
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


def _place_chevron(ctx: _Ctx, blk, rect: Rect, inherit: Style) -> Rect:
    sh = _chevron_shape(blk)
    st = _text_style(ctx, sh, inherit)
    full = rect
    rect = Rect(rect.x, rect.y, rect.w, min(rect.h, max(round(rect.w * 0.45), round(0.9 * EMU_PER_INCH))))
    pad_pt = round(CHEVRON_ADJ * min(rect.w, rect.h) * 1.05 / EMU_PER_PT, 1)
    st = st.merged(Style(padding=f"{pad_pt}pt", align="center", valign="middle"))
    eff = measure.effective_scale(st.font_size or 18, ctx.scale, ctx.theme.min_font_size)
    need = _text_need(ctx, sh, st, rect.w, eff)
    if need > rect.h * _TOL:
        ctx.over.append(_label(blk))
    ctx.emit(sh, rect, st, eff)
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
            else:
                r = Rect(Mx, My, inner_w, tr_h)
                y = My + tr_h
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
        y_top = y
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
        for s in _SCALES:
            c2 = _Ctx(deck, theme, slide, index, W, H, scale=s, dense_k=ctx.dense_k, tight=ctx.tight)
            _place_blocks(
                c2, elements, body, slide_inherit, slide.grid, slide.classes, sgap, None, slide.links
            )
            final_ctx = c2
            if not c2.over:
                break
        assert final_ctx is not None
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
