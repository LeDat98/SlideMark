"""IR + Placed -> .pptx. Owner: renderer workstream."""

from __future__ import annotations

import re
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE, MSO_SHAPE_TYPE
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.oxml.ns import qn
from pptx.util import Emu, Pt

from ..ir import Chart, Code, Container, Deck, Image, Placed, Raw, Shape, Slide, Style, Table, Text
from ..layout.engine import CHEVRON_ADJ
from ..theme import Theme
from ..units import slide_size
from .math import add_math
from .objects import add_chart, add_image, add_table, code_paragraphs, resolve_image
from .text import fill_text, insert_rpr_child
from .util import RenderCtx, emu, rgb

__all__ = ["render"]

_SHAPES = {
    "rect": MSO_SHAPE.RECTANGLE,
    "rectangle": MSO_SHAPE.RECTANGLE,
    "rounded-rect": MSO_SHAPE.ROUNDED_RECTANGLE,
    "rounded-rectangle": MSO_SHAPE.ROUNDED_RECTANGLE,
    "ellipse": MSO_SHAPE.OVAL,
    "oval": MSO_SHAPE.OVAL,
    "circle": MSO_SHAPE.OVAL,
    "arrow-right": MSO_SHAPE.RIGHT_ARROW,
    "arrow-left": MSO_SHAPE.LEFT_ARROW,
    "arrow-up": MSO_SHAPE.UP_ARROW,
    "arrow-down": MSO_SHAPE.DOWN_ARROW,
    "chevron": MSO_SHAPE.CHEVRON,
    "pentagon": MSO_SHAPE.PENTAGON,
    "diamond": MSO_SHAPE.DIAMOND,
    "triangle": MSO_SHAPE.ISOSCELES_TRIANGLE,
    "hexagon": MSO_SHAPE.HEXAGON,
    "star": MSO_SHAPE.STAR_5_POINT,
    "cylinder": MSO_SHAPE.CAN,
    "parallelogram": MSO_SHAPE.PARALLELOGRAM,
    "trapezoid": MSO_SHAPE.TRAPEZOID,
    "cloud": MSO_SHAPE.CLOUD,
    "plus": MSO_SHAPE.MATH_PLUS,
    "callout": MSO_SHAPE.RECTANGULAR_CALLOUT,
}
_TRANSITIONS = {
    "fade": "<p:fade/>",
    "push": '<p:push dir="l"/>',
    "wipe": '<p:wipe dir="l"/>',
    "split": "<p:split/>",
}
_NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"


def render(deck: Deck, placed: list[list[Placed]], theme: Theme, out: str | Path) -> Path:
    """Write ``deck`` to ``out``. ``placed[i]`` is the layout result for ``deck.slides[i]``."""
    out = Path(out)
    prs = Presentation()
    try:
        prs.slide_width, prs.slide_height = (Emu(v) for v in slide_size(deck.size))
    except ValueError:
        prs.slide_width, prs.slide_height = (Emu(v) for v in slide_size("16:9"))
    rc = RenderCtx(deck=deck, theme=theme, base_dir=str(deck.attrs.get("base_dir", ".")))
    for i, slide in enumerate(deck.slides):
        rc.slide_index = i
        items = placed[i] if i < len(placed) else []
        try:
            rc.slides.append(_render_slide(rc, prs, slide, items))
        except Exception as e:  # never raise on bad input: keep an empty slide and say why
            rc.slides.append(prs.slides.add_slide(prs.slide_layouts[6]))
            rc.diag(
                "render-error",
                f"slide failed to render: {type(e).__name__}: {e}",
                "simplify this slide or report a bug",
                "error",
            )
    _resolve_links(rc)
    _core_properties(prs, deck)
    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out))
    return out


# --------------------------------------------------------------------------- slide


def _render_slide(rc: RenderCtx, prs, slide: Slide, items: list[Placed]):
    has_title = any(isinstance(p.element, Text) and p.element.role == "title" for p in items)
    s = prs.slides.add_slide(prs.slide_layouts[5 if has_title else 6])
    _background(rc, prs, s, slide)
    counters: dict[str, int] = {}
    used_title = False
    for pl in items:
        try:
            use_ph = (
                has_title and not used_title and isinstance(pl.element, Text) and pl.element.role == "title"
            )
            used_title = used_title or use_ph
            _render_item(rc, s, pl, counters, use_ph)
        except Exception as e:
            rc.diag(
                "render-error",
                f"{pl.element.type} failed to render: {type(e).__name__}: {e}",
                "simplify this element",
                "error",
            )
    if has_title and not used_title and s.shapes.title is not None:
        s.shapes.title._element.getparent().remove(s.shapes.title._element)
    if slide.notes:
        s.notes_slide.notes_text_frame.text = slide.notes
    if slide.hidden:
        s._element.set("show", "0")
    _transition(rc, s, slide)
    return s


def _background(rc: RenderCtx, prs, s, slide: Slide) -> None:
    bg = slide.background
    theme = rc.theme
    fill = s.background.fill
    if bg and bg.lower().startswith("linear-gradient"):
        cols = re.findall(r"#[0-9a-fA-F]{3,6}|\b[a-z]+\b(?=\s*[,)])", bg)
        ang = re.search(r"(-?\d+)deg", bg)
        cols = [c for c in cols if c.lower() not in ("linear", "gradient", "deg")]
        if len(cols) >= 2:
            fill.gradient()
            fill.gradient_angle = float(ang.group(1)) if ang else 90.0
            fill.gradient_stops[0].color.rgb = rgb(theme, cols[0])
            fill.gradient_stops[1].color.rgb = rgb(theme, cols[-1])
            return
    if bg and (resolve_image(rc, bg) is not None or re.search(r"\.(png|jpe?g|gif|bmp)$", bg, re.I)):
        fill.solid()
        fill.fore_color.rgb = rgb(theme, "bg")
        path = resolve_image(rc, bg)
        if path is None:
            rc.diag(
                "image-missing",
                f"background image not found: {bg}",
                "check the path, relative to the .md file",
            )
            return
        pic = s.shapes.add_picture(str(path), 0, 0, prs.slide_width, prs.slide_height)
        pic.name = "Background"
        tree = s.shapes._spTree
        tree.remove(pic._element)
        tree.insert(2, pic._element)
        return
    fill.solid()
    fill.fore_color.rgb = rgb(theme, bg or "bg", theme.colors.get("bg", "#FFFFFF"))


def _transition(rc: RenderCtx, s, slide: Slide) -> None:
    name = (slide.transition or "").strip().lower()
    if not name or name == "none":
        return
    inner = _TRANSITIONS.get(name)
    if inner is None:
        rc.diag(
            "transition", f"unknown transition {name!r}", f"use one of: {', '.join(_TRANSITIONS)}", "info"
        )
        return
    el = etree.fromstring(f'<p:transition xmlns:p="{_NS_P}" spd="med">{inner}</p:transition>')
    sld = s._element
    anchor = sld.find(qn("p:clrMapOvr"))
    if anchor is None:
        anchor = sld.find(qn("p:cSld"))
    anchor.addnext(el)


# --------------------------------------------------------------------------- items


def _name(pl: Placed, counters: dict[str, int]) -> str:
    el = pl.element
    if getattr(el, "id", None):
        return str(el.id)
    if isinstance(el, Text):
        field = el.attrs.get("field")
        if field == "footer":
            return "Footer"
        if field == "slide_number":
            return "Slide Number"
        base = {"title": "Title", "subtitle": "Subtitle", "lead": "Lead", "conclusion": "Conclusion"}.get(
            el.role
        )
        if base:
            return base
        base = {"heading": "Heading", "footnote": "Footnote"}.get(el.role, "Text")
    elif isinstance(el, Container):
        base = "Card"
    else:
        base = {
            "table": "Table",
            "chart": "Chart",
            "image": "Image",
            "code": "Code",
            "raw": "Raw",
            "shape": "Shape",
        }[el.type]
    counters[base] = counters.get(base, 0) + 1
    return f"{base} {counters[base]}"


def _style_shape(rc: RenderCtx, shp, st: Style) -> None:
    theme = rc.theme
    if st.fill:
        shp.fill.solid()
        shp.fill.fore_color.rgb = rgb(theme, st.fill)
        if st.opacity is not None and 0 <= st.opacity < 1:
            clr = shp._element.spPr.find(qn("a:solidFill")).find(qn("a:srgbClr"))
            etree.SubElement(clr, qn("a:alpha")).set("val", str(round(st.opacity * 100000)))
    else:
        shp.fill.background()
    if st.line:
        shp.line.color.rgb = rgb(theme, st.line)
        shp.line.width = Pt(st.line_width if st.line_width is not None else 0.75)
    else:
        shp.line.fill.background()
    if not st.shadow:
        shp.shadow.inherit = False


def _round(shp, st: Style, pl: Placed) -> None:
    if st.radius and shp.auto_shape_type == MSO_SHAPE.ROUNDED_RECTANGLE:
        short = max(min(pl.w, pl.h), 1)
        shp.adjustments[0] = min(emu(st.radius) / short, 0.5)


def _autoshape(rc: RenderCtx, slide, pl: Placed, kind, name: str):
    shp = slide.shapes.add_shape(kind, Emu(pl.x), Emu(pl.y), Emu(pl.w), Emu(pl.h))
    shp.name = name
    style_el = shp._element.find(qn("p:style"))
    if (
        style_el is not None
    ):  # drop theme style refs: LibreOffice/PowerPoint would add a shadow and white text
        shp._element.remove(style_el)
    _style_shape(rc, shp, pl.style)
    _round(shp, pl.style, pl)
    return shp


def _render_item(rc: RenderCtx, s, pl: Placed, counters: dict[str, int], use_placeholder: bool) -> None:
    el = pl.element
    st = pl.style
    name = _name(pl, counters)
    if isinstance(el, Container):
        if st.fill or st.line:
            kind = MSO_SHAPE.ROUNDED_RECTANGLE if st.radius else MSO_SHAPE.RECTANGLE
            _autoshape(rc, s, pl, kind, name)
    elif isinstance(el, Text):
        field = el.attrs.get("field")
        if use_placeholder:
            shp = s.shapes.title
            shp.left, shp.top, shp.width, shp.height = Emu(pl.x), Emu(pl.y), Emu(pl.w), Emu(pl.h)
            shp.name = name
            tree = shp._element.getparent()
            tree.remove(shp._element)
            tree.append(shp._element)  # keep layout z-order
            tf = shp.text_frame
        elif st.fill or st.line:
            kind = MSO_SHAPE.ROUNDED_RECTANGLE if st.radius else MSO_SHAPE.RECTANGLE
            shp = _autoshape(rc, s, pl, kind, name)
            tf = shp.text_frame
        else:
            shp = s.shapes.add_textbox(Emu(pl.x), Emu(pl.y), Emu(pl.w), Emu(pl.h))
            shp.name = name
            tf = shp.text_frame
        fill_text(rc, tf, el.paragraphs, st, pl.font_scale, field=field)
        if "callout" in el.classes and st.line and not use_placeholder:
            _accent_bar(rc, s, pl, name)
    elif isinstance(el, Shape) and el.shape == "line":
        _connector(rc, s, pl, name)
    elif isinstance(el, Shape):
        kind = _SHAPES.get(el.shape)
        if kind is None:
            rc.diag(
                "shape",
                f"unknown shape {el.shape!r}",
                f"use one of: {', '.join(sorted(_SHAPES))}",
                line=el.line,
            )
            kind = MSO_SHAPE.RECTANGLE
        shp = _autoshape(rc, s, pl, kind, name)
        if el.paragraphs:
            fill_text(rc, shp.text_frame, el.paragraphs, st, pl.font_scale)
        if el.shape == "chevron":
            shp.adjustments[0] = CHEVRON_ADJ
    elif isinstance(el, Table):
        add_table(rc, s, pl, name)
    elif isinstance(el, Chart):
        add_chart(rc, s, pl, name)
    elif isinstance(el, Image):
        if not add_image(rc, s, pl, name):
            _placeholder(rc, s, pl, name, f"[image: {el.alt or el.src}]")
    elif isinstance(el, Code):
        shp = _autoshape(rc, s, pl, MSO_SHAPE.RECTANGLE, name)
        fill_text(rc, shp.text_frame, code_paragraphs(el), st, pl.font_scale, para_gap=False)
    elif isinstance(el, Raw) and el.kind == "math" and add_math(rc, s, pl, name):
        pass
    elif isinstance(el, Raw):
        _placeholder(rc, s, pl, name, f"[{el.kind}]")
        rc.diag(
            "raw",
            f"{el.kind} content is not rendered yet",
            "replace it with an image or native elements",
            "info",
            line=el.line,
        )


def _accent_bar(rc: RenderCtx, slide, pl: Placed, name: str) -> None:
    """Callout cards get a thick accent bar on the left edge, in the border color."""
    bar = pl.model_copy(update={"w": min(emu(4), pl.w), "style": Style(fill=pl.style.line, line=None)})
    _autoshape(rc, slide, bar, MSO_SHAPE.RECTANGLE, f"{name} accent")


def _connector(rc: RenderCtx, slide, pl: Placed, name: str) -> None:
    """A connector: straight (corner to opposite corner, flips pick the diagonal) or an elbow.

    Elbows are ``bentConnector3``: horizontal-vertical-horizontal for ``route="h"``; for ``route="v"`` the
    shape is rotated by 90 degrees (vertical-horizontal-vertical). ``adj`` places the middle segment.
    """
    el = pl.element
    fh, fv = bool(el.attrs.get("flip_h")), bool(el.attrs.get("flip_v"))
    x0, x1 = (pl.x + pl.w, pl.x) if fh else (pl.x, pl.x + pl.w)
    y0, y1 = (pl.y + pl.h, pl.y) if fv else (pl.y, pl.y + pl.h)
    elbow = bool(el.attrs.get("elbow"))
    kind = MSO_CONNECTOR.ELBOW if elbow else MSO_CONNECTOR.STRAIGHT
    cx = slide.shapes.add_connector(kind, Emu(x0), Emu(y0), Emu(x1), Emu(y1))
    cx.name = name
    style_el = cx._element.find(qn("p:style"))
    if style_el is not None:
        cx._element.remove(style_el)
    if elbow:
        _elbow_geometry(cx, el.attrs, pl, fh, fv)
    _glue(slide, cx, el.attrs, fh, fv)
    st = pl.style
    cx.line.color.rgb = rgb(rc.theme, st.line or "primary")
    cx.line.width = Pt(st.line_width if st.line_width is not None else 1.5)
    if el.attrs.get("head") == "arrow":
        ln = cx.line._get_or_add_ln()
        tail = etree.SubElement(ln, qn("a:tailEnd"))
        tail.set("type", "triangle")
        tail.set("w", "med")
        tail.set("len", "med")


def _find_box(slide, box) -> object | None:
    """The first plain rectangle / rounded rectangle on ``slide`` with exactly this (x, y, w, h)."""
    if not box:
        return None
    for shp in slide.shapes:
        if shp.shape_type != MSO_SHAPE_TYPE.AUTO_SHAPE:
            continue
        if (shp.left, shp.top, shp.width, shp.height) == tuple(box):
            if shp.auto_shape_type in (MSO_SHAPE.RECTANGLE, MSO_SHAPE.ROUNDED_RECTANGLE):
                return shp
    return None


def _glue(slide, cx, attrs: dict, fh: bool, fv: bool) -> None:
    """Attach both ends to the connected boxes (connection sites 0 top, 1 left, 2 bottom, 3 right).

    Glued connectors follow their boxes when the slide is edited, and LibreOffice routes them by the sides.
    """
    route = attrs.get("route")
    src, dst = _find_box(slide, attrs.get("src_box")), _find_box(slide, attrs.get("dst_box"))
    if route not in ("v", "h") or src is None or dst is None:
        return
    if route == "v":
        s_idx, e_idx = (0, 2) if fv else (2, 0)
    else:
        s_idx, e_idx = (1, 3) if fh else (3, 1)
    c_nv = cx._element.find(qn("p:nvCxnSpPr")).find(qn("p:cNvCxnSpPr"))
    for tag, shp, idx in (("a:stCxn", src, s_idx), ("a:endCxn", dst, e_idx)):
        el = etree.SubElement(c_nv, qn(tag))
        el.set("id", str(shp.shape_id))
        el.set("idx", str(idx))


def _elbow_geometry(cx, attrs: dict, pl: Placed, fh: bool, fv: bool) -> None:
    """Set the bend position and, for vertical routes, the 90 degree rotation of a ``bentConnector3``."""
    adj = attrs.get("adj")
    geom = cx._element.spPr.find(qn("a:prstGeom"))
    if adj is not None and geom is not None and abs(adj - 0.5) > 1e-4:
        av = geom.find(qn("a:avLst"))
        if av is None:
            av = etree.SubElement(geom, qn("a:avLst"))
        gd = etree.SubElement(av, qn("a:gd"))
        gd.set("name", "adj1")
        gd.set("fmla", f"val {round(adj * 100000)}")
    if attrs.get("route") != "v":
        return
    # vertical route: rotate the unrotated (w=|dy|, h=|dx|) box by 90 degrees around the bounding box center.
    # With rot=90 the path starts top-right; flipV moves the start to the left, flipH to the bottom.
    xfrm = cx._element.spPr.find(qn("a:xfrm"))
    mx, my = pl.x + pl.w // 2, pl.y + pl.h // 2
    xfrm.set("rot", "5400000")
    for k in ("flipH", "flipV"):
        xfrm.attrib.pop(k, None)
    if fv:
        xfrm.set("flipH", "1")
    if not fh:
        xfrm.set("flipV", "1")
    xfrm.find(qn("a:off")).set("x", str(mx - pl.h // 2))
    xfrm.find(qn("a:off")).set("y", str(my - pl.w // 2))
    xfrm.find(qn("a:ext")).set("cx", str(pl.h))
    xfrm.find(qn("a:ext")).set("cy", str(pl.w))


def _placeholder(rc: RenderCtx, s, pl: Placed, name: str, label: str) -> None:
    st = Style(
        font_size=12,
        color="muted",
        fill="surface",
        line="border",
        line_width=1,
        align="center",
        valign="middle",
    ).merged(pl.style)
    shp = _autoshape(rc, s, pl.model_copy(update={"style": st}), MSO_SHAPE.RECTANGLE, name)
    shp.line.dash_style = 4  # dash
    from ..ir import Paragraph, Run

    fill_text(rc, shp.text_frame, [Paragraph(runs=[Run(text=label)])], st, 1.0)


# --------------------------------------------------------------------------- second pass


def _resolve_links(rc: RenderCtx) -> None:
    ids = {sl.id: i for i, sl in enumerate(rc.deck.slides) if sl.id}
    for _run_el, rpr, target, src_idx in rc.links:
        idx: int | None = None
        if target.isdigit():
            idx = int(target) - 1
        elif target in ids:
            idx = ids[target]
        rc.slide_index = src_idx
        if idx is None or not 0 <= idx < len(rc.slides):
            rc.diag(
                "link",
                f"slide link #{target} does not exist",
                "use #<n> with n from 1 to the slide count, or a slide id=",
            )
            continue
        src = rc.slides[src_idx]
        rid = src.part.relate_to(rc.slides[idx].part, RT.SLIDE)
        h = etree.Element(qn("a:hlinkClick"))
        h.set(qn("r:id"), rid)
        h.set("action", "ppaction://hlinksldjump")
        insert_rpr_child(rpr, h)


def _core_properties(prs, deck: Deck) -> None:
    cp = prs.core_properties
    title = deck.title
    if not title:
        for sl in deck.slides:
            if sl.title and sl.title.paragraphs:
                title = " ".join(p.plain for p in sl.title.paragraphs)
                break
    if title:
        cp.title = title
    if deck.author:
        cp.author = deck.author
    if deck.lang:
        cp.language = deck.lang
