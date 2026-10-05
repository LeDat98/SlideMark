"""Consulting-grade layout: card heights, balanced bands, table rows, title gap, stacked boxes, chevrons."""

from __future__ import annotations

from pptx import Presentation
from pptx.oxml.ns import qn

from slidemark.ir import Chart, Container, Deck, Shape, Slide, Table, Text
from slidemark.layout import layout_slide
from slidemark.render import render
from slidemark.theme import get_theme

from .test_layout_policies import H, T, box, bullets, cards, cell, lay, of


def _title(placed):
    return next(p for p in placed if isinstance(p.element, Text) and p.element.role == "title")


def _gap_after_title(placed):
    t = _title(placed)
    top = min(
        p.y for p in placed if p is not t and p.y >= t.y + t.h - 1 and p.h > 0 and p.element is not None
    )
    return top - (t.y + t.h)


def test_sparse_cards_follow_content_not_the_body():
    s = Slide(title=T("t", "title"), grid="3", elements=[box("a", "x"), box("b", "x"), box("c", "x")])
    placed, _ = lay(s, "default")
    nat = 18 * 1.2 * 12700 * 2 + 2 * 10 * 12700  # heading + one bullet, rough
    cs = cards(placed)
    assert cs[0].h < 0.45 * H and cs[0].h >= 0.8 * nat


def test_two_by_two_with_conclusion_has_no_big_empty_band():
    s = Slide(
        title=T("t", "title"),
        grid="2x2",
        elements=[box(n, "x", "y") for n in "abcd"],
        conclusion=T("so what", "conclusion"),
    )
    placed, _ = lay(s, "jp-business")
    cs = cards(placed)
    bar = next(p for p in placed if isinstance(p.element, Text) and p.element.role == "conclusion")
    band = bar.y - max(c.y + c.h for c in cs)
    assert band < 0.12 * H
    assert min(c.y for c in cs) - (_title(placed).y + _title(placed).h) < 0.12 * H


def test_title_to_body_gap_is_identical_across_slide_kinds():
    dense = [f"line {i} " + "word " * 25 for i in range(9)]
    slides = [
        Slide(title=T("t", "title"), elements=[Chart(kind="line")]),
        Slide(title=T("t", "title"), grid="2", elements=[box("a", *dense), box("b", *dense)]),
        Slide(title=T("t", "title"), elements=[bullets(*dense)]),
        Slide(title=T("t", "title"), lead=T("lead", "lead"), elements=[Chart(kind="line")]),
    ]
    for theme in ("jp-business", "default"):
        gaps = [_gap_after_title(lay(s, theme)[0]) for s in slides[:3]]
        assert max(gaps) - min(gaps) <= 2, gaps
        assert gaps[0] > 0.15 * 914400  # a real gap, not touching the title band
    lead_gap = _gap_after_title(lay(slides[3], "jp-business")[0])
    assert lead_gap > 0


def test_flow_boxes_above_a_chart_take_natural_height():
    s = Slide(
        title=T("t", "title"),
        grid="flow",
        elements=[*(box(n, "one", "two") for n in "abc"), Chart(kind="line")],
    )
    placed, _ = lay(s, "jp-business")
    cs = cards(placed)
    (chart,) = of(placed, Chart)
    assert cs[0].h < 0.3 * H  # the box row hugs its text
    assert chart.h > 1.5 * cs[0].h  # the chart gets the rest


def test_stacked_boxes_share_height_by_content_and_align_with_the_tall_box():
    left = Container(title=T("L", "heading"), children=[Chart(kind="column")])
    short = box("s", "one")
    long = Container(title=T("l", "heading"), children=[bullets(*[f"item {i}" for i in range(5)])])
    s = Slide(title=T("t", "title"), grid="aab/aac", elements=[left, short, long])
    placed, _ = lay(s, "jp-business")
    cs = {id(p.element): p for p in cards(placed)}
    a, b, c = cs[id(left)], cs[id(short)], cs[id(long)]
    assert c.h > b.h  # more content -> more height
    assert abs((c.y + c.h) - (a.y + a.h)) <= 2 and b.y == a.y  # fills the column, bottoms align


def test_chevron_lists_have_no_bullet_markers(tmp_path):
    boxes = [Container(title=T(f"S{i}", "heading"), children=[bullets("alpha", "beta")]) for i in range(3)]
    s = Slide(title=T("t", "title"), grid="chevron", elements=boxes)
    th = get_theme("jp-business")
    deck = Deck(slides=[s])
    placed = layout_slide(s, deck, th, 0)
    chev = [p for p in placed if isinstance(p.element, Shape) and p.element.shape == "chevron"]
    assert len(chev) == 3
    assert all(par.marker is None for p in chev for par in p.element.paragraphs)
    out = tmp_path / "c.pptx"
    render(deck, [placed], th, out)
    prs = Presentation(str(out))
    for shp in prs.slides[0].shapes:
        if shp.has_text_frame and "alpha" in shp.text_frame.text:
            for para in shp.text_frame.paragraphs:
                ppr = para._p.pPr
                assert ppr is None or ppr.find(qn("a:buChar")) is None
                assert ppr is None or ppr.find(qn("a:buAutoNum")) is None


def test_table_rows_are_capped_near_text_height():
    rows = [[cell("項目"), cell("値")]] + [[cell("a"), cell("1")] for _ in range(3)]
    s = Slide(title=T("t", "title"), elements=[Table(rows=rows)])
    placed, _ = lay(s, "jp-business")
    (tp,) = of(placed, Table)
    size = (tp.style.font_size or 12) * tp.font_scale
    assert max(tp.element.attrs["_row_h"]) <= (1.8 * size * 1.2 + 7.3) * 12700
