"""Vector icons as native custom-geometry shapes (editable, recolorable in PowerPoint)."""

from __future__ import annotations

from lxml import etree
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn
from pptx.util import Emu

from .. import icons
from ..ir import Placed
from .util import RenderCtx, rgb

_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_SCALE = 1000  # path units per grid unit (the path box is 24000 x 24000)


def _pt(x: float, y: float) -> str:
    return f'<a:pt x="{round(x * _SCALE)}" y="{round(y * _SCALE)}"/>'


def _cust_geom(layers) -> etree._Element:
    size = icons.GRID * _SCALE
    paths = []
    for layer in layers:
        body = []
        for op, pts in layer:
            if op == "M":
                body.append(f"<a:moveTo>{_pt(*pts[0])}</a:moveTo>")
            elif op == "L":
                body.append(f"<a:lnTo>{_pt(*pts[0])}</a:lnTo>")
            elif op == "C":
                body.append(f"<a:cubicBezTo>{''.join(_pt(*p) for p in pts)}</a:cubicBezTo>")
            elif op == "Q":
                body.append(f"<a:quadBezTo>{''.join(_pt(*p) for p in pts)}</a:quadBezTo>")
            else:
                body.append("<a:close/>")
        paths.append(f'<a:path w="{size}" h="{size}">{"".join(body)}</a:path>')
    xml = (
        f'<a:custGeom xmlns:a="{_A}"><a:avLst/><a:gdLst/><a:ahLst/><a:cxnLst/>'
        '<a:rect l="0" t="0" r="r" b="b"/>'
        f"<a:pathLst>{''.join(paths)}</a:pathLst></a:custGeom>"
    )
    return etree.fromstring(xml)


def add_icon(rc: RenderCtx, slide, pl: Placed, name: str) -> bool:
    """Draw ``pl.element.attrs["icon"]``; return False (nothing drawn) for an unknown icon name."""
    icon = str(pl.element.attrs.get("icon", "")).strip().lower()
    layers = icons.commands(icon)
    if not layers:
        return False
    shp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Emu(pl.x), Emu(pl.y), Emu(pl.w), Emu(pl.h))
    shp.name = f"icon {icon}"
    el = shp._element
    if (style_el := el.find(qn("p:style"))) is not None:
        el.remove(style_el)
    sp_pr = el.spPr
    prst = sp_pr.find(qn("a:prstGeom"))
    prst.addprevious(_cust_geom(layers))
    sp_pr.remove(prst)
    shp.fill.solid()
    shp.fill.fore_color.rgb = rgb(rc.theme, pl.style.fill or pl.style.color or "primary")
    shp.line.fill.background()
    shp.shadow.inherit = False
    return True
