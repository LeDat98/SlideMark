"""``hl=`` points and the pinned plot area of a chart takeaway (``note=``), written into the chart XML."""

from __future__ import annotations

from lxml import etree
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_MARKER_STYLE
from pptx.oxml.ns import qn
from pptx.util import Pt

from ..ir import Chart
from ..layout import chartnote
from ..theme import Theme
from . import waterfall as wfall
from .util import hex6

_BAR_LIKE = ("bar", "column", "stacked-bar", "stacked-column")


def hl_color(theme: Theme) -> RGBColor:
    return RGBColor.from_string(hex6(theme, theme.render.chart_hl))


def apply_hl(ch: Chart, chart, cats: list[str], real_series: int, wf: dict | None, theme: Theme) -> list[str]:
    """Emphasise the ``hl=`` categories; returns their names. Never raises: a missing point is skipped."""
    idx = chartnote.resolve_hl(ch, cats)
    if not idx:
        return []
    color, rt = hl_color(theme), theme.render
    kind = ch.kind
    for plot in chart.plots:
        for si, ser in enumerate(plot.series):
            for i in idx:
                try:
                    if wf is not None:
                        if si in (wfall.BASE, wfall.PAD) or wf["series"][si].values[i] is None:
                            continue
                        pt = ser.points[i]
                        pt.format.fill.solid()
                        pt.format.fill.fore_color.rgb = color
                    elif kind in ("pie", "doughnut"):
                        pt = ser.points[i]
                        pt.format.fill.solid()
                        pt.format.fill.fore_color.rgb = color
                    elif kind == "line":
                        pt = ser.points[i]
                        pt.marker.style = XL_MARKER_STYLE.CIRCLE
                        pt.marker.size = rt.chart_hl_marker
                        pt.marker.format.fill.solid()
                        pt.marker.format.fill.fore_color.rgb = color
                        pt.marker.format.line.color.rgb = color
                    elif kind in _BAR_LIKE and si < real_series:
                        pt = ser.points[i]
                        if real_series == 1:  # one series: the point itself takes the color
                            pt.format.fill.solid()
                            pt.format.fill.fore_color.rgb = color
                        else:  # several series keep their colors: an outline marks the category
                            pt.format.line.color.rgb = color
                            pt.format.line.width = Pt(rt.chart_hl_line)
                except (IndexError, KeyError, AttributeError, ValueError):
                    continue
    return [cats[i] for i in idx]


def pin_plot(chart, frac: tuple[float, float, float, float]) -> None:
    """Write the inner plot area as ``c:manualLayout`` (fractions of the chart frame)."""
    area = chart._chartSpace.find(".//" + qn("c:plotArea"))
    if area is None:
        return
    layout = area.find(qn("c:layout"))
    if layout is None:
        layout = etree.Element(qn("c:layout"))
        area.insert(0, layout)
    for child in list(layout):
        layout.remove(child)
    man = etree.SubElement(layout, qn("c:manualLayout"))
    for tag, val in (
        ("layoutTarget", "inner"),
        ("xMode", "edge"),
        ("yMode", "edge"),
        ("x", frac[0]),
        ("y", frac[1]),
        ("w", frac[2]),
        ("h", frac[3]),
    ):
        el = etree.SubElement(man, qn(f"c:{tag}"))
        el.set("val", val if isinstance(val, str) else f"{val:.5f}")
