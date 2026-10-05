from __future__ import annotations

import pytest

from slidemark.ir import (
    Box,
    Cell,
    Chart,
    Container,
    Deck,
    Image,
    Paragraph,
    Placed,
    Run,
    Series,
    Shape,
    Slide,
    Style,
    Table,
    Text,
)
from slidemark.layout import layout_slide
from slidemark.layout.grid import Rect, auto_spec, cell_rects, parse_spec
from slidemark.layout.measure import count_lines, paragraphs_height
from slidemark.theme import get_theme
from slidemark.units import slide_size


def T(s, role="body", **kw):
    return Text(role=role, paragraphs=[Paragraph(runs=[Run(text=s)])], **kw)


def box(h, body="text", **kw):
    return Container(title=T(h, "heading"), children=[T(body)], **kw)


def lay(slide, deck=None, theme="default", index=0):
    deck = deck or Deck(slides=[slide])
    return layout_slide(slide, deck, get_theme(theme), index), deck


def cards(placed):
    return [p for p in placed if isinstance(p.element, Container)]


def inside(p: Placed, W, H):
    return p.x >= 0 and p.y >= 0 and p.x + p.w <= W and p.y + p.h <= H


def overlap(a: Placed, b: Placed) -> bool:
    return a.x < b.x + b.w and b.x < a.x + a.w and a.y < b.y + b.h and b.y < a.y + a.h


@pytest.mark.parametrize("theme", ["default", "midnight", "jp-business"])
@pytest.mark.parametrize("n", [1, 2, 3, 4, 5, 6, 7, 9])
def test_auto_arrangement_inside_and_disjoint(theme, n):
    s = Slide(title=T("Title", "title"), lead=T("lead", "lead"), elements=[box(f"B{i}") for i in range(n)])
    s.footnotes = [T("note", "footnote")]
    s.conclusion = T("done", "conclusion")
    placed, deck = lay(s, Deck(slides=[s], footer="f", slide_number=True), theme)
    W, H = slide_size("16:9")
    assert all(inside(p, W, H) for p in placed)
    cs = cards(placed)
    assert len(cs) == n
    for i, a in enumerate(cs):
        for b in cs[i + 1 :]:
            assert not overlap(a, b)
    assert not [d for d in deck.diagnostics if d.rule == "overflow"]
    roles = [p.element.role for p in placed if isinstance(p.element, Text)]
    assert roles.count("title") == 1 and "lead" in roles and "conclusion" in roles and "footnote" in roles


def test_auto_column_counts():
    def xs(n):
        placed, _ = lay(Slide(title=T("t", "title"), elements=[box(str(i)) for i in range(n)]))
        cs = cards(placed)
        return len({c.x for c in cs}), len({c.y for c in cs})

    assert xs(1) == (1, 1)
    assert xs(2) == (2, 1)
    assert xs(3) == (3, 1)
    assert xs(4) == (4, 1)  # short blocks -> 4 columns
    assert xs(5) == (3, 2)
    assert xs(6) == (3, 2)
    long = "word " * 40
    placed, _ = lay(Slide(title=T("t", "title"), elements=[box(str(i), long) for i in range(4)]))
    cs = cards(placed)
    assert (len({c.x for c in cs}), len({c.y for c in cs})) == (2, 2)


def test_text_plus_visual_text_left():
    ch = Chart(kind="column", categories=["a"], series=[Series(name="s", values=[1])])
    placed, _ = lay(Slide(title=T("t", "title"), elements=[ch, T("explanation")]))
    body = [
        p
        for p in placed
        if p.element.type in ("text", "chart") and getattr(p.element, "role", "body") == "body"
    ]
    txt = next(p for p in body if p.element.type == "text")
    cht = next(p for p in body if p.element.type == "chart")
    assert txt.x < cht.x and cht.w > txt.w


def test_area_spans():
    s = Slide(title=T("t", "title"), grid="aab/aac", elements=[box("a"), box("b"), box("c")])
    placed, deck = lay(s)
    a, b, c = cards(placed)
    assert a.x < b.x == c.x
    assert a.h > b.h and b.y < c.y
    assert abs(a.h - (c.y + c.h - b.y)) < 5  # a spans both rows
    assert a.w > b.w  # a spans two columns of three
    assert not deck.diagnostics


def test_dot_means_empty_area():
    s = Slide(title=T("t", "title"), grid="a./.b", elements=[box("a"), box("b")])
    placed, _ = lay(s)
    a, b = cards(placed)
    assert a.x < b.x and a.y < b.y


@pytest.mark.parametrize("spec", ["3", "2x2", "1:2", "1:2:1", "aab/aac", "abc"])
def test_grid_specs_parse(spec):
    gs = parse_spec(spec, 3)
    assert gs is not None and gs.cols and not gs.errors


def test_ratio_widths():
    gs = parse_spec("1:2", 2)
    rs = cell_rects(gs, 2, Rect(0, 0, 3000, 100), 0)
    assert rs[0].w == 1000 and rs[1].w == 2000


def test_cxr_and_n_grids():
    s = Slide(title=T("t", "title"), grid="2x2", elements=[box(str(i)) for i in range(4)])
    placed, _ = lay(s)
    cs = cards(placed)
    assert len({c.x for c in cs}) == 2 and len({c.y for c in cs}) == 2
    s = Slide(title=T("t", "title"), grid="2", elements=[box(str(i)) for i in range(4)])
    placed, _ = lay(s)
    cs = cards(placed)
    assert len({c.x for c in cs}) == 2 and len({c.y for c in cs}) == 2


def test_unknown_grid_falls_back_without_crash():
    s = Slide(title=T("t", "title"), grid="zz/9", elements=[box("a"), box("b")])
    placed, deck = lay(s)
    assert len(cards(placed)) == 2
    s = Slide(title=T("t", "title"), grid="aab/aac", elements=[box("a"), box("b"), box("c"), box("d")])
    placed, deck = lay(s)
    assert len(cards(placed)) == 4
    assert any(d.rule == "grid" for d in deck.diagnostics)


def test_flow_arrows_and_chevrons():
    s = Slide(title=T("t", "title"), grid="3", classes=["flow"], elements=[box(str(i)) for i in range(3)])
    placed, _ = lay(s)
    arrows = [p for p in placed if isinstance(p.element, Shape) and p.element.shape == "arrow-right"]
    cs = cards(placed)
    assert len(arrows) == 2
    for ar in arrows:
        assert all(not overlap(ar, c) for c in cs)
    s = Slide(title=T("t", "title"), grid="4 chevron", elements=[T(w) for w in "abcd"])
    placed, _ = lay(s)
    chev = [p for p in placed if isinstance(p.element, Shape) and p.element.shape == "chevron"]
    assert len(chev) == 4 and chev[0].element.paragraphs[0].plain == "a"
    for a in chev:
        for b in chev:
            if a is not b:
                assert not overlap(a, b)


def test_nested_grid_in_box():
    inner = Container(
        title=T("outer", "heading"),
        grid="2",
        children=[box("x"), box("y")],
    )
    placed, _ = lay(Slide(title=T("t", "title"), elements=[inner]))
    cs = cards(placed)
    assert len(cs) == 3
    outer, x, y = cs
    assert x.x > outer.x and x.x + x.w < y.x and y.x + y.w < outer.x + outer.w
    assert x.y > outer.y


def test_explicit_box_relative_to_area():
    t = T("abs", box=Box(x="50%", y="0", w="25%", h="20%"))
    placed, _ = lay(Slide(title=T("t", "title"), elements=[box("a"), t]))
    pl = next(p for p in placed if p.element is t)
    cs = cards(placed)
    assert len(cs) == 1  # the absolute block is out of the flow
    assert pl.w > 0 and pl.x > cs[0].x + cs[0].w // 3 - 10**6


def test_bad_box_length_is_diagnostic():
    t = T("abs", box=Box(x="oops"))
    placed, deck = lay(Slide(title=T("t", "title"), elements=[t]))
    assert any(d.rule == "bad-length" for d in deck.diagnostics)
    assert placed


def test_style_merge_order():
    c = Container(
        title=T("h", "heading"),
        classes=["card"],
        style=Style(fill="#112233"),
        children=[T("x", style=Style(font_size=9))],
    )
    placed, _ = lay(Slide(title=T("t", "title"), elements=[c]), theme="midnight")
    card = cards(placed)[0]
    assert card.style.fill == "#112233"  # inline beats theme
    assert card.style.line == "border" and card.style.radius == 8  # theme class
    body = next(p for p in placed if isinstance(p.element, Text) and p.element.role == "body")
    assert body.style.font_size == 9


def test_plain_class_has_no_card_fill():
    c = box("a", classes=["plain"])
    placed, _ = lay(Slide(title=T("t", "title"), elements=[c]))
    assert cards(placed)[0].style.fill is None


def test_overflow_autofit_and_diagnostic():
    items = [
        Paragraph(runs=[Run(text="line of body text that is moderately long " * 2)], marker="bullet")
        for _ in range(16)
    ]
    s = Slide(title=T("t", "title"), elements=[Text(paragraphs=items)])
    placed, deck = lay(s)
    body = next(p for p in placed if isinstance(p.element, Text) and p.element.role == "body")
    assert body.font_scale < 1.0
    assert body.font_scale * body.style.font_size >= get_theme("default").min_font_size
    assert not [d for d in deck.diagnostics if d.rule == "overflow"]

    items = [
        Paragraph(runs=[Run(text="line of body text that is moderately long " * 4)], marker="bullet")
        for _ in range(80)
    ]
    s = Slide(title=T("t", "title"), elements=[Text(paragraphs=items)])
    placed, deck = lay(s)
    body = next(p for p in placed if isinstance(p.element, Text) and p.element.role == "body")
    assert abs(body.font_scale * body.style.font_size - get_theme("default").min_font_size) < 0.01
    ov = [d for d in deck.diagnostics if d.rule == "overflow"]
    assert ov and "split" in ov[0].hint


def test_layout_kinds():
    placed, _ = lay(Slide(title=T("Cover", "title"), subtitle=T("sub", "subtitle")), index=0)
    ys = {p.element.role: p.y for p in placed if isinstance(p.element, Text)}
    assert ys["title"] > 500000 and ys["subtitle"] > ys["title"]
    placed, _ = lay(Slide(layout="blank", title=T("x", "title"), elements=[T("body")]))
    assert not [p for p in placed if isinstance(p.element, Text) and p.element.role == "title"]
    placed, deck = lay(Slide(layout="weird", title=T("x", "title"), elements=[T("body")]))
    assert any(d.rule == "layout" for d in deck.diagnostics)
    placed, _ = lay(Slide(layout="center", title=T("x", "title"), elements=[T("body")]))
    body = next(p for p in placed if isinstance(p.element, Text) and p.element.role == "body")
    assert body.style.align == "center" and body.style.valign == "middle"


def test_footer_and_number_items():
    s = Slide(title=T("t", "title"), elements=[T("b")])
    placed, _ = lay(s, Deck(slides=[s], footer="ACME", slide_number=True), index=4)
    f = [p for p in placed if isinstance(p.element, Text) and p.element.attrs.get("field")]
    assert {p.element.attrs["field"] for p in f} == {"footer", "slide_number"}
    num = next(p for p in f if p.element.attrs["field"] == "slide_number")
    assert num.element.paragraphs[0].plain == "5"


def test_table_row_heights_in_attrs():
    from slidemark.ir import Cell

    t = Table(rows=[[Cell(paragraphs=[Paragraph(runs=[Run(text="a")])]) for _ in range(3)] for _ in range(3)])
    placed, _ = lay(Slide(title=T("t", "title"), elements=[t]))
    tp = next(p for p in placed if isinstance(p.element, Table))
    assert len(tp.element.attrs["_row_h"]) == 3 and sum(tp.element.attrs["_col_w"]) == tp.w
    assert tp.h == sum(tp.element.attrs["_row_h"])


def test_dense_theme_is_smaller():
    s = Slide(title=T("t", "title"), elements=[T("body")])
    jp, _ = lay(s, theme="jp-business")
    df, _ = lay(s, theme="default")

    def f(pl):
        return next(p for p in pl if isinstance(p.element, Text) and p.element.role == "body").style.font_size

    assert 10.5 <= f(jp) <= 12 and f(df) == 18


def test_images_get_flexible_space():
    c = Container(title=T("img", "heading"), children=[T("caption"), Image(src="x.png", alt="x")])
    placed, _ = lay(Slide(title=T("t", "title"), elements=[c]))
    img = next(p for p in placed if isinstance(p.element, Image))
    card = cards(placed)[0]
    assert img.h > 1_000_000 and img.y + img.h <= card.y + card.h


# ----------------------------------------------------------------------------- measure


def test_measure_wrap_and_cjk():
    seg = [("hello world " * 10, False, False)]
    assert count_lines(seg, 600, 12) < count_lines(seg, 150, 12)
    cjk = [("あ" * 20, False, False)]
    assert count_lines(cjk, 10 * 10, 10) == 2  # 10 chars per line at 1em each
    assert count_lines([("a\nb", False, False)], 1000, 10) == 2
    h1 = paragraphs_height([Paragraph(runs=[Run(text="x")])], 3_000_000, Style(font_size=18))
    h2 = paragraphs_height([Paragraph(runs=[Run(text="x")])] * 2, 3_000_000, Style(font_size=18))
    assert h2 > 2 * h1


def test_kinsoku_no_line_start_punct():
    # 10 columns. The full stop would be the 11th char: it must not start a line, so the 10th goes down too.
    text = "あ" * 9 + "。" + "い"
    assert count_lines([(text, False, False)], 100, 10) == 2
    text = "あ" * 10 + "。"
    assert count_lines([(text, False, False)], 100, 10) == 2  # no hanging punctuation
    # the pushed-down char plus punctuation still fits on one extra line, never more
    assert count_lines([("あ" * 10 + "、」", False, False)], 100, 10) == 2
    assert count_lines([("あ" * 10 + "。。。", False, False)], 100, 10) == 2


def test_kinsoku_no_line_end_opening():
    # an opening bracket may not end a line: it moves down with the next char
    text = "あ" * 9 + "「" + "い"
    assert count_lines([(text, False, False)], 100, 10) == 2
    # without kinsoku this is 2 lines (10 + 10); with it the bracket moves down: 9 / 10 / 1
    text = "あ" * 9 + "「" + "い" * 10
    assert count_lines([(text, False, False)], 100, 10) == 3
    text = "あ" * 9 + "【「" + "い"
    assert count_lines([(text, False, False)], 100, 10) == 2


def test_kinsoku_ascii_unaffected():
    seg = [("(hello) world, (foo) bar.", False, False)]
    assert count_lines(seg, 1000, 10) == 1


def test_dense_jp_box_shrinks_to_fit():
    jp = "新規顧客の獲得数は前年同期比で十二パーセント増加し、既存顧客の解約率も一・五ポイント改善した。" * 5
    boxes = [
        Container(
            title=T(f"施策{i}", "heading"),
            children=[
                Text(
                    paragraphs=[
                        Paragraph(runs=[Run(text=jp)], marker="bullet"),
                        Paragraph(runs=[Run(text=jp)], marker="bullet"),
                    ]
                )
            ],
        )
        for i in range(4)
    ]
    s = Slide(title=T("現状分析", "title"), grid="2x2", elements=boxes)
    placed, deck = lay(s, theme="jp-business")
    body = [p for p in placed if isinstance(p.element, Text) and p.element.role == "body"]
    assert len(body) == 4 and all(p.font_scale < 1.0 for p in body)
    th = get_theme("jp-business")
    assert all(p.font_scale * p.style.font_size >= th.min_font_size - 0.01 for p in body)
    assert not [d for d in deck.diagnostics if d.rule == "overflow"]


def test_absurd_text_overflow_diagnostic_jp_and_latin():
    for word in ("日本語の長い文章がここに入ります。" * 400, "lorem ipsum dolor sit amet " * 600):
        s = Slide(title=T("t", "title"), elements=[T(word)])
        placed, deck = lay(s)
        body = next(p for p in placed if isinstance(p.element, Text) and p.element.role == "body")
        assert abs(body.font_scale * body.style.font_size - get_theme("default").min_font_size) < 0.01
        ov = [d for d in deck.diagnostics if d.rule == "overflow"]
        assert ov and "shorten" in ov[0].hint and "split" in ov[0].hint


def test_long_table_shrinks_then_reports():
    def c(t):
        return Cell(paragraphs=[Paragraph(runs=[Run(text=t)])])

    rows = [[c("項目"), c("内容")]] + [[c(f"行{i}"), c("説明文がここに入ります " * 3)] for i in range(16)]
    placed, deck = lay(Slide(title=T("t", "title"), elements=[Table(rows=rows)]))
    tb = next(p for p in placed if isinstance(p.element, Table))
    assert tb.font_scale < 1.0 and not [d for d in deck.diagnostics if d.rule == "overflow"]
    rows = [[c("項目"), c("内容")]] + [[c(f"行{i}"), c("説明文がここに入ります " * 3)] for i in range(200)]
    _, deck = lay(Slide(title=T("t", "title"), elements=[Table(rows=rows)]))
    assert [d for d in deck.diagnostics if d.rule == "overflow"]


def test_footnotes_shrink_and_report():
    notes = [T("※ 注記の文章がここに入ります。" * 6, "footnote") for _ in range(6)]
    placed, deck = lay(Slide(title=T("t", "title"), elements=[T("body")], footnotes=notes))
    fn = [p for p in placed if isinstance(p.element, Text) and p.element.role == "footnote"]
    assert fn and all(p.font_scale < 1.0 for p in fn)
    assert all(p.y >= 0 and p.y + p.h <= slide_size("16:9")[1] for p in fn)
    notes = [T("※ 注記の文章がここに入ります。" * 80, "footnote") for _ in range(6)]
    _, deck = lay(Slide(title=T("t", "title"), elements=[T("body")], footnotes=notes))
    assert [d for d in deck.diagnostics if d.rule == "overflow" and "footnote" in d.message]


def test_chevron_box_keeps_table_child():
    tbl = Table(rows=[[Cell(paragraphs=[Paragraph(runs=[Run(text="a")])])]])
    s = Slide(
        title=T("t", "title"),
        classes=["chevron"],
        grid="2",
        elements=[
            Container(title=T("Step 1", "heading"), children=[T("text"), tbl]),
            Container(title=T("Step 2", "heading"), children=[T("text")]),
        ],
    )
    placed, deck = lay(s)
    chev = [p for p in placed if isinstance(p.element, Shape) and p.element.shape == "chevron"]
    tables = [p for p in placed if isinstance(p.element, Table)]
    assert len(chev) == 2 and len(tables) == 1
    assert tables[0].y >= chev[0].y + chev[0].h
    assert not [d for d in deck.diagnostics if d.rule == "dropped-content"]
    # a bare visual in a chevron grid is placed as a normal block instead of an empty chevron
    s = Slide(title=T("t", "title"), classes=["chevron"], grid="2", elements=[T("a"), tbl])
    placed, _ = lay(s)
    assert len([p for p in placed if isinstance(p.element, Shape) and p.element.shape == "chevron"]) == 1
    assert len([p for p in placed if isinstance(p.element, Table)]) == 1


def test_never_raises():
    s = Slide(
        title=None,
        grid="???",
        classes=["flow", "chevron"],
        elements=[Container(children=[]), Table(), Chart(kind="pie")],
    )
    placed, _ = lay(s, Deck(slides=[s], size="nonsense"))
    assert isinstance(placed, list)


def test_auto_spec_5_6():
    for n in (5, 6):
        g = auto_spec(n)
        assert len(g.cols) == 3 and len(g.rows) == 2
