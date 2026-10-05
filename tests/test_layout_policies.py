"""Layout policies: sparse boxes, kpi cards, callouts, table sizing, connector routing."""

from __future__ import annotations

from slidemark.ir import Cell, Container, Deck, Link, Paragraph, Run, Shape, Slide, Style, Table, Text
from slidemark.layout import layout_slide
from slidemark.layout.tables import column_widths, is_numeric, table_grid
from slidemark.theme import get_theme
from slidemark.units import EMU_PER_INCH, slide_size

W, H = slide_size("16:9")


def T(s, role="body", **kw):
    return Text(role=role, paragraphs=[Paragraph(runs=[Run(text=s)])], **kw)


def bullets(*items, **kw):
    return Text(
        role="body",
        paragraphs=[Paragraph(runs=[Run(text=t)], marker="bullet") for t in items],
        **kw,
    )


def box(h, *items, **kw):
    return Container(title=T(h, "heading"), children=[bullets(*items or ("x",))], **kw)


def cell(t, **kw):
    return Cell(paragraphs=[Paragraph(runs=[Run(text=t)])], **kw)


def lay(slide, theme="jp-business"):
    deck = Deck(slides=[slide])
    return layout_slide(slide, deck, get_theme(theme), 0), deck


def of(placed, cls):
    return [p for p in placed if isinstance(p.element, cls)]


def lines(placed):
    return [p for p in placed if isinstance(p.element, Shape) and p.element.shape == "line"]


def cards(placed):
    return of(placed, Container)


def _gap_below(placed, theme):
    """(empty band below the lowest content, body height) of a slide laid out without footer / conclusion."""
    from slidemark.units import to_emu

    th = get_theme(theme)
    bottom = H - to_emu(th.margin_y)
    title = next(p for p in placed if isinstance(p.element, Text) and p.element.role == "title")
    body_h = bottom - (title.y + title.h)
    low = max(p.y + p.h for p in placed if p is not title and p.h > 0 and p.y >= title.y + title.h)
    return bottom - low, body_h


def test_sparse_boxes_are_capped_and_top_aligned():
    s = Slide(
        title=T("t", "title"),
        grid="3",
        elements=[box("a", "x", "y"), box("b", "x", "y"), box("c", "x", "y")],
    )
    for theme in ("default", "jp-business"):
        placed, _ = lay(s, theme)
        cs = cards(placed)
        assert len({c.h for c in cs}) == 1 and len({c.y for c in cs}) == 1  # equal heights in a row
        assert cs[0].h < 0.75 * H  # not stretched over the whole body
        assert cs[0].h > 0.2 * H  # but not tiny either
        below, body_h = _gap_below(placed, theme)
        assert 0.22 * body_h <= cs[0].h <= 0.5 * body_h  # card height follows content (+ a modest factor)
        title = next(p for p in placed if isinstance(p.element, Text) and p.element.role == "title")
        above = cs[0].y - (title.y + title.h)
        assert above > 0 and below > above  # a single sparse row sits in the upper-middle of the free body


def test_sparse_slide_keeps_the_block_low_enough_with_a_third_above():
    s = Slide(title=T("t", "title"), grid="3", elements=[box("a"), box("b"), box("c")])
    placed, _ = lay(s, "default")
    title = next(p for p in placed if isinstance(p.element, Text) and p.element.role == "title")
    above = cards(placed)[0].y - (title.y + title.h)
    below, _ = _gap_below(placed, "default")
    assert 0 <= above < below  # the leftover is split towards the bottom (1/3 above, 2/3 below)


def test_sparse_boxes_grow_text_uniformly_within_the_theme_limit():
    s = Slide(
        title=T("t", "title"),
        grid="3",
        elements=[box("a", "x", "y"), box("b", "x" * 10, "y"), box("c", "x", "y")],
    )
    for theme, limit in (("default", 1.4), ("jp-business", 1.35)):
        placed, _ = lay(s, theme)
        scales = {p.font_scale for p in of(placed, Text) if p.element.role == "body"}
        assert len(scales) == 1
        assert 1.0 < scales.pop() <= limit + 1e-9


def test_table_text_and_rows_grow_within_limits():
    rows = [[cell("項目"), cell("値")]] + [[cell("a"), cell("12")] for _ in range(2)]
    s = Slide(title=T("t", "title"), elements=[Table(rows=rows)])
    placed, _ = lay(s, "jp-business")
    (tp,) = of(placed, Table)
    assert 1.0 < tp.font_scale <= 1.2 + 1e-9
    line = 11 * 1.2 * 12700 * tp.font_scale
    assert max(tp.element.attrs["_row_h"]) <= 2.0 * (1.8 * line + 2 * 45720) + 1  # at most 2x (roomy)


def test_table_rows_do_not_stretch_over_the_body():
    rows = [[cell("項目"), cell("値")]] + [[cell("a"), cell("12")] for _ in range(5)]
    s = Slide(title=T("t", "title"), elements=[Table(rows=rows)])
    placed, _ = lay(s, "jp-business")
    (tp,) = of(placed, Table)
    rh = tp.element.attrs["_row_h"]
    assert max(rh) <= 2.0 * (1.8 * (tp.style.font_size or 14) * tp.font_scale * 1.2 * 12700 + 2 * 45720) + 1
    assert tp.h < 0.6 * H  # leftover room is not poured into the rows


def test_dense_boxes_do_not_grow():
    items = [f"line {i} " + "word " * 30 for i in range(10)]
    s = Slide(title=T("t", "title"), grid="2", elements=[box("a", *items), box("b", *items)])
    placed, _ = lay(s)
    assert all(p.font_scale <= 1.0 for p in of(placed, Text))


def test_kpi_cards_have_natural_height_and_table_follows():
    kpis = [
        Container(title=T("売上", "heading"), classes=["kpi"], children=[T("62.4億円\n計画比 +6%")])
        for _ in range(4)
    ]
    tbl = Table(rows=[[cell("a"), cell("b")], [cell("x"), cell("y")]])
    s = Slide(title=T("t", "title"), grid="4", elements=[*kpis, tbl])
    placed, _ = lay(s)
    cs = cards(placed)
    assert len(cs) == 4 and len({c.y for c in cs}) == 1
    assert cs[0].h < 2.0 * EMU_PER_INCH
    (tp,) = of(placed, Table)
    assert tp.y > cs[0].y + cs[0].h and tp.x == cs[0].x
    assert tp.x + tp.w == cs[-1].x + cs[-1].w  # full width below the card row


def test_callout_is_a_full_width_row_below_the_grid():
    callout = T("careful", classes=["callout", "warn"])
    tbl = Table(rows=[[cell("a"), cell("b")], [cell("x"), cell("y")]])
    s = Slide(title=T("t", "title"), elements=[tbl, callout])
    placed, _ = lay(s)
    (tp,) = of(placed, Table)
    co = next(p for p in of(placed, Text) if "callout" in p.element.classes)
    assert co.y >= tp.y + tp.h and co.w == tp.w
    assert co.h < 0.9 * EMU_PER_INCH  # natural height, never stretched


def test_callout_in_a_box_keeps_natural_height():
    callout = T("careful", classes=["callout", "note"])
    s = Slide(title=T("t", "title"), elements=[Container(title=T("h", "heading"), children=[callout])])
    placed, _ = lay(s)
    co = next(p for p in of(placed, Text) if "callout" in p.element.classes)
    assert co.h < 0.9 * EMU_PER_INCH


def test_table_rows_grow_but_not_beyond_1_6x():
    rows = [[cell("a"), cell("b")]] + [[cell("x"), cell("1")] for _ in range(3)]
    s = Slide(title=T("t", "title"), elements=[Table(rows=rows)])
    placed, _ = lay(s)
    (tp,) = of(placed, Table)
    rh = tp.element.attrs["_row_h"]
    assert sum(rh) == tp.h
    nat = 14 * 1.2 * 12700 * 1.03 + 2 * 45720  # one 14pt row, roughly
    assert min(rh) > 1.2 * nat * 0.9  # grew
    assert max(rh) <= 1.6 * nat * 1.3  # but capped


def test_numeric_detection():
    for ok in ["38.2", "+14%", "-8%", "▲3.1", "62.4億円", "¥1,200", "5万円〜", "1か月", "120", "-"]:
        assert is_numeric(ok), ok
    for bad in ["SaaS事業", "10月〜11月", "◎", "2026年度", "", "A社"]:
        assert not is_numeric(bad), bad


def test_numeric_cells_right_aligned_unless_explicit():
    rows = [
        [cell("項目"), cell("値")],
        [cell("a"), cell("12.5%")],
        [cell("b"), cell("7", style=Style(align="center"))],
    ]
    s = Slide(title=T("t", "title"), elements=[Table(rows=rows)])
    placed, _ = lay(s)
    (tp,) = of(placed, Table)
    al = [[(c.style.align if c.style else None) for c in r] for r in tp.element.rows]
    assert al[1] == [None, "right"] and al[2] == [None, "center"]
    assert al[0] == [None, "right"]  # the header of an all-numeric column follows its figures


def test_columns_follow_content_and_headers_do_not_wrap():
    t = Table(
        rows=[
            [cell("指標"), cell("2026年度（見込）"), cell("メモ")],
            [cell("売上高"), cell("126億円"), cell("これは長めの説明テキストが入る列です。これは長めの説明")],
        ]
    )
    _, ncols, anchors = table_grid(t)
    total = int(9 * EMU_PER_INCH)
    cw = column_widths(t, ncols, anchors, total, 14.0)
    assert sum(cw) == total
    assert cw[2] > cw[0]  # the long text column is wider
    assert cw[1] >= 8 * 14 * 12700  # the header stays on one line
    t2 = t.model_copy(update={"col_widths": [1, 1, 2]})
    assert column_widths(t2, ncols, anchors, total, 14.0)[2] == round(total / 2)


def test_org_chart_links_leave_bottom_and_enter_top():
    elements = [box("a"), box("b"), box("c"), box("d")]
    s = Slide(
        title=T("t", "title"),
        grid=".a./bcd",
        elements=elements,
        links=[Link(src=0, dst=1), Link(src=0, dst=2), Link(src=0, dst=3)],
    )
    placed, _ = lay(s)
    cs = cards(placed)
    ls = lines(placed)
    assert len(ls) == 3
    kinds = sorted((ln.element.attrs["route"], ln.element.attrs["elbow"]) for ln in ls)
    assert kinds == [("v", False), ("v", True), ("v", True)]
    for ln in ls:
        assert ln.y == cs[0].y + cs[0].h  # starts at the parent's bottom edge
        assert any(c.y == ln.y + ln.h for c in cs[1:])  # ends on a child's top edge
        assert ln.element.attrs["head"] == "arrow"
        for c in cs[1:]:  # no line passes through a box
            inside_x = ln.x < c.x + c.w and ln.x + ln.w > c.x
            assert not (inside_x and ln.y + ln.h > c.y + 1 and ln.y < c.y + c.h)


def test_vertical_link_skips_a_third_box_without_crashing():
    s = Slide(
        title=T("t", "title"),
        grid="aa/bb/cc",
        elements=[box("a"), box("b"), box("c")],
        links=[Link(src=0, dst=2)],
    )
    placed, deck = lay(s)
    assert len(lines(placed)) == 1 and not [d for d in deck.diagnostics if d.rule == "layout-error"]


def test_horizontal_elbow_for_offset_neighbours():
    s = Slide(
        title=T("t", "title"),
        grid="1:2",
        elements=[box("a"), box("b", "x", "y", "z")],
        links=[Link(src=0, dst=1)],
    )
    placed, _ = lay(s)
    (ln,) = lines(placed)
    a, b = cards(placed)
    assert ln.element.attrs["route"] == "h"
    assert ln.x == a.x + a.w and ln.x + ln.w == b.x


def test_mixed_numeric_columns_stay_left_aligned_but_mostly_numeric_ones_go_right():
    rows = [
        [cell("項目"), cell("価格"), cell("導入"), cell("数")],
        [cell("a"), cell("5万円〜"), cell("1か月"), cell("12")],
        [cell("b"), cell("20万円〜"), cell("即日"), cell("8")],
        [cell("c"), cell("3万円〜"), cell("6か月"), cell("40%")],
        [cell("d"), cell("4万円〜"), cell("即時"), cell("-")],
        [cell("e"), cell("要相談"), cell("3か月"), cell("7")],
    ]
    s = Slide(title=T("t", "title"), elements=[Table(rows=rows)])
    placed, _ = lay(s)
    (tp,) = of(placed, Table)
    al = [[(c.style.align if c.style else None) for c in r] for r in tp.element.rows]
    price = [r[1] for r in al]
    assert price == ["right"] * 6  # 4 of 5 (80%) numeric: whole column and header right-aligned
    assert [r[2] for r in al] == [None] * 6  # only 3 of 5 numeric: the whole column stays left
    assert [r[3] for r in al] == ["right"] * 6  # "-" counts as a figure placeholder


def _body_scales(slide, theme="default"):
    placed, _ = lay(slide, theme)
    body = {p.font_scale for p in of(placed, Text) if p.element.role == "body"}
    head = {p.font_scale for p in of(placed, Text) if p.element.role == "heading"}
    return body, head, placed


def test_very_sparse_boxes_of_a_large_theme_grow_up_to_1_4_and_headings_up_to_1_25():
    s = Slide(
        title=T("t", "title"),
        grid="3",
        elements=[box("a", "one"), box("b", "two"), box("c", "three")],
    )
    body, head, placed = _body_scales(s)
    assert len(body) == 1 and len(head) == 1  # siblings share one scale
    bs, hs = body.pop(), head.pop()
    assert 1.15 < bs <= 1.4 + 1e-9
    assert 1.0 < hs <= 1.25 + 1e-9
    assert get_theme("default").sizes["body"] * bs <= 26 + 1e-6


def test_normal_boxes_of_a_large_theme_keep_the_small_growth():
    s = Slide(
        title=T("t", "title"),
        grid="3",
        elements=[box("a", "x", "y", "z"), box("b", "x", "y", "z"), box("c", "x", "y", "z")],
    )
    body, head, _ = _body_scales(s)
    assert max(body) <= 1.15 + 1e-9
    assert head == {1.0}


def test_text_above_code_has_no_gap():
    from slidemark.ir import Code

    s = Slide(
        title=T("Title", "title"),
        grid="b/a",
        elements=[Code(text="x = 1\ny = 2", lang="python"), bullets("one", "two")],
    )
    placed, _deck = lay(s, "midnight")
    text = of(placed, Text)
    body = next(p for p in text if p.element.role == "body")
    code = of(placed, Code)[0]
    assert 0 <= code.y - (body.y + body.h) <= 0.35 * EMU_PER_INCH  # the code follows the text directly
