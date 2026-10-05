"""Chart series colors, data label contrast and axis ids (reopened .pptx)."""

from __future__ import annotations

from pptx import Presentation
from pptx.oxml.ns import qn

from slidemark.ir import Chart, Deck, Paragraph, Run, Series, Slide, Text
from slidemark.layout import layout_slide
from slidemark.render import render
from slidemark.theme import get_theme


def build_chart(tmp_path, kind, nseries=2, theme="default", **opts):
    series = [Series(name=f"s{i}", values=[1, 2]) for i in range(nseries)]
    title = Text(role="title", paragraphs=[Paragraph(runs=[Run(text="T")])])
    ch = Chart(kind=kind, categories=["a", "b"], series=series, options=opts)
    d = Deck(slides=[Slide(title=title, elements=[ch])], theme=theme)
    th = get_theme(theme)
    out = tmp_path / "c.pptx"
    render(d, [layout_slide(s, d, th, i) for i, s in enumerate(d.slides)], th, out)
    prs = Presentation(str(out))
    return [s for s in prs.slides[0].shapes if s.name.startswith("Chart")][0].chart


def test_series_colors_are_distinct_for_the_jp_business_palette(tmp_path):
    chart = build_chart(tmp_path, "stacked-bar", nseries=4, theme="jp-business", labels="on")
    fills = [str(s.format.fill.fore_color.rgb) for s in chart.plots[0].series]
    assert len(set(fills)) == 4, fills


def test_stacked_labels_are_white_on_dark_fills_and_dark_on_light(tmp_path):
    chart = build_chart(tmp_path, "stacked-column", labels="on", colors="#1E3A5F,#FFE9A8")
    colors = []
    for ser in chart.plots[0].series:
        d_lbls = ser._element.find(qn("c:dLbls"))
        assert d_lbls is not None
        colors.append(d_lbls.find(qn("c:txPr")).find(".//" + qn("a:srgbClr")).get("val"))
    assert colors[0] == "FFFFFF"
    assert colors[1] != "FFFFFF"


def test_axis_ids_are_positive_and_consistent(tmp_path):
    for kind in ("column", "bar", "line", "stacked-bar", "area", "scatter"):
        chart = build_chart(tmp_path, kind)
        cs = chart._chartSpace
        ax_ids = [int(e.get("val")) for e in cs.iter(qn("c:axId"))]
        cross = [int(e.get("val")) for e in cs.iter(qn("c:crossAx"))]
        assert ax_ids and all(v >= 0 for v in ax_ids + cross), kind
        plot_area = cs.find(".//" + qn("c:plotArea"))
        defined = {
            int(a.find(qn("c:axId")).get("val"))
            for a in plot_area
            if a.tag in (qn("c:catAx"), qn("c:valAx"), qn("c:dateAx"), qn("c:serAx"))
        }
        assert set(cross) <= defined, kind
