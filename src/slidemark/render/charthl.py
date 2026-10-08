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


def apply_hl(
    ch: Chart, chart, cats: list[str], real_series: int, wf: dict | None, theme: Theme, pal: list[str]
) -> list[str]:
    """Emphasise the ``hl=`` categories; returns their names. Never raises: a missing point is skipped."""
    idx = chartnote.resolve_hl(ch, cats)
    color, rt = hl_color(theme), theme.render
    kind = ch.kind
    sers = [str(n).strip().casefold() for n in ch.options.get("hl_series") or []]
    nser = min(real_series, len(ch.series)) if wf is None else 0
    if (
        sers and nser
    ):  # `hl=<series name>`: the whole series takes the emphasis color (a line gets a thicker stroke)
        for plot in chart.plots:
            for si, ser in enumerate(plot.series):
                if si >= nser or str(ch.series[si].name).strip().casefold() not in sers:
                    continue
                try:
                    if kind in ("line", "radar"):
                        ser.format.line.color.rgb = color
                        ser.format.line.width = Pt(rt.chart_hl_line + rt.chart_line_width)
                        ser.marker.format.fill.solid()
                        ser.marker.format.fill.fore_color.rgb = color
                        ser.marker.format.line.color.rgb = color
                    elif kind in _BAR_LIKE or kind == "area":
                        ser.format.fill.solid()
                        ser.format.fill.fore_color.rgb = color
                except (IndexError, AttributeError, ValueError):
                    continue
    named = [ch.series[i].name for i in range(nser) if str(ch.series[i].name).strip().casefold() in sers]
    if not idx:
        return named

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
                            pt.format.fill.solid()  # (a point without a fill falls back to the auto color)
                            pt.format.fill.fore_color.rgb = RGBColor.from_string(pal[si % len(pal)])
                            pt.format.line.color.rgb = color
                            pt.format.line.width = Pt(rt.chart_hl_line)
                except (IndexError, KeyError, AttributeError, ValueError):
                    continue
    return [*named, *(cats[i] for i in idx)]


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
