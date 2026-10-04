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


def _class_styles(ctx: _Ctx, el) -> list[Style]:
    out: list[Style] = []
    for name in getattr(el, "classes", []):
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
    return st.merged(*_class_styles(ctx, el), el.style)


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
    return st.merged(*_class_styles(ctx, el), el.style)


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
    others = [s for n, s in zip(c.classes, _class_styles(ctx, c), strict=False) if n != "plain"]
    return Style().merged(base, *others, c.style)


def _place_container(ctx: _Ctx, c: Container, rect: Rect, inherit: Style) -> None:
    style = _card_style(ctx, c)
    pad = _pad(style, 10 * EMU_PER_PT)
    ctx.emit(c, rect, style)
    inner = rect.inset(pad)
    y = inner.y
    child_inherit = inherit.merged(_only_inheritable(style))
    if c.title is not None and c.title.paragraphs:
        h_el = c.title if c.title.role == "heading" else c.title.model_copy(update={"role": "heading"})
        hst = _text_style(ctx, h_el, Style())
        eff = measure.effective_scale(hst.font_size or 18, ctx.scale, ctx.theme.min_font_size)
        hh = round(_text_need(ctx, h_el, hst, inner.w, eff))
        if hh > inner.h * _TOL:
            ctx.over.append(_label(c))
        ctx.emit(h_el, Rect(inner.x, y, inner.w, min(hh, inner.h)), hst, eff)
        y += hh + round(pad * 0.5)
    area = Rect(inner.x, y, inner.w, max(inner.bottom - y, 0))
    if not c.children:
        return
    gap = _gap(ctx, c.gap, inner.w, small=True)
    if c.grid or any(n in ("flow", "chevron") for n in c.classes):
        _place_blocks(ctx, c.children, area, child_inherit, c.grid, c.classes, gap, c)
    else:
        _place_stack(ctx, c.children, area, child_inherit, gap, c)


def _gap(ctx: _Ctx, value, ref: int, small: bool = False) -> int:
    if value is not None:
        v = _len(ctx, value, ref)
        if v is not None:
            return v
    g = to_emu(ctx.theme.gap)
    return round(g * 0.5) if small else g


def _place_stack(ctx: _Ctx, children: list, area: Rect, inherit: Style, gap: int, owner) -> None:
    flow = [ch for ch in children if not _is_abs(ch)]
    for ch in children:
        if _is_abs(ch):
            _place_block(ctx, ch, _apply_box(ctx, ch, area, True), inherit)
    if not flow:
        return
    nat = [_natural_height(ctx, ch, area.w, inherit) for ch in flow]
    fixed = sum(n for n in nat if n is not None) + gap * (len(flow) - 1)
    nflex = sum(1 for n in nat if n is None)
    flex_h = 0
    if nflex:
        flex_h = max((area.h - fixed) // nflex, int(0.8 * EMU_PER_INCH))
    y = area.y
    used = 0
    for ch, n in zip(flow, nat, strict=True):
        h = n if n is not None else flex_h
        r = _apply_box(ctx, ch, Rect(area.x, y, area.w, h), False)
        _place_block(ctx, ch, r, inherit)
        y += h + gap
        used += h + gap
    used -= gap
    if used > area.h * _TOL:
        ctx.over.append(_label(owner) if owner is not None else "content")


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


def _place_blocks(
    ctx: _Ctx, blocks: list, area: Rect, inherit: Style, grid: str | None, classes: list[str], gap: int, owner
) -> None:
    flow = [b for b in blocks if not _is_abs(b)]
    for b in blocks:
        if _is_abs(b):
            _place_block(ctx, b, _apply_box(ctx, b, area, True), inherit)
    if not flow:
        return
    gs = parse_spec(grid, len(flow), classes)
    flags: set[str] = set()
    if gs is not None:
        for err in gs.errors:
            ctx.diag("grid", err, "use @N, @CxR, @1:2 or areas like @aab/aac; falling back to auto layout")
        flags = gs.flags
    if gs is None or not gs.cols:
        text_visual, short = _block_kind_hint(flow)
        if text_visual and not isinstance(flow[0], Text):
            flow = [flow[1], flow[0]]
        gs = auto_spec(len(flow), text_visual=text_visual, short=short)
    if "flow" in flags:
        gap = max(gap, round(0.45 * EMU_PER_INCH))
    elif "chevron" in flags:
        gap = max(round(gap / 4), 0)
    rects = cell_rects(gs, len(flow), area, gap)
    for blk, r in zip(flow, rects, strict=True):
        r = _apply_box(ctx, blk, r, False)
        if "chevron" in flags:
            _place_chevron(ctx, blk, r, inherit)
        else:
            _place_block(ctx, blk, r, inherit)
    if "flow" in flags:
        for a, b in zip(rects, rects[1:], strict=False):
            g = b.x - a.right
            overlap_y = min(a.bottom, b.bottom) - max(a.y, b.y)
            if g <= 0 or overlap_y <= 0:
                continue
            aw = min(round(g * 0.8), round(0.35 * EMU_PER_INCH))
            ah = min(round(aw * 1.2), overlap_y)
            cy = max(a.y, b.y) + overlap_y // 2
            st = Style(fill="muted", line=None)
            ctx.emit(Shape(shape="arrow-right"), Rect(a.right + (g - aw) // 2, cy - ah // 2, aw, ah), st)


def _place_chevron(ctx: _Ctx, blk, rect: Rect, inherit: Style) -> None:
    sh = _chevron_shape(blk)
    st = _text_style(ctx, sh, inherit)
    rect = Rect(rect.x, rect.y, rect.w, min(rect.h, max(round(rect.w * 0.45), round(0.9 * EMU_PER_INCH))))
    pad_pt = round(CHEVRON_ADJ * min(rect.w, rect.h) * 1.05 / EMU_PER_PT, 1)
    st = st.merged(Style(padding=f"{pad_pt}pt", align="center", valign="middle"))
    eff = measure.effective_scale(st.font_size or 18, ctx.scale, ctx.theme.min_font_size)
    need = _text_need(ctx, sh, st, rect.w, eff)
    if need > rect.h * _TOL:
        ctx.over.append(_label(blk))
    ctx.emit(sh, rect, st, eff)


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
                "split the slide or cut text",
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
            hs = [round(_text_need(ctx, f, st, inner_w, 1.0)) for f, st in zip(notes, sts, strict=True)]
            fy0 = bottom - sum(hs)
            for f, st, h in zip(notes, sts, hs, strict=True):
                put(tail, f, Rect(Mx, fy0, inner_w, h), st)
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
            c2 = _Ctx(deck, theme, slide, index, W, H, scale=s, dense_k=ctx.dense_k)
            _place_blocks(c2, elements, body, slide_inherit, slide.grid, slide.classes, sgap, None)
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
                    "split the slide or cut text",
                )
    elif body is not None and body.h <= 0 and elements:
        ctx.diag("overflow", "no room left for the body", "split the slide or cut text")

    deck.diagnostics.extend(ctx.diags)
    return head + (final_ctx.out if final_ctx else []) + tail
