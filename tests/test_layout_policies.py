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
        assert (
            0.22 * body_h <= cs[0].h <= (0.5 if theme == "default" else 0.65) * body_h
        )  # follows content; consulting rows reach ~60%
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
    for theme, limit in (("default", 1.4), ("jp-business", 1.35 * 1.2)):  # consulting: + roomy pass
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


def test_very_sparse_boxes_of_a_large_theme_grow_up_to_1_4_and_headings_follow_the_body():
    s = Slide(
        title=T("t", "title"),
        grid="3",
        elements=[box("a", "one"), box("b", "two"), box("c", "three")],
    )
    body, head, placed = _body_scales(s)
    assert len(body) == 1 and len(head) == 1  # siblings share one scale
    bs, hs = body.pop(), head.pop()
    assert 1.15 < bs <= 1.4 + 1e-9
    th = get_theme("default")
    assert 1.0 < hs
    assert th.sizes["heading"] * hs >= th.sizes["body"] * bs * 0.98  # heading never smaller than its body
    assert th.sizes["body"] * bs <= 26 + 1e-6


def test_normal_boxes_of_a_large_theme_keep_the_small_growth():
    s = Slide(
        title=T("t", "title"),
        grid="3",
        elements=[box("a", "x", "y", "z"), box("b", "x", "y", "z"), box("c", "x", "y", "z")],
    )
    body, head, _ = _body_scales(s)
    assert max(body) <= 1.15 + 1e-9
    th = get_theme("default")
    assert th.sizes["heading"] * min(head) >= th.sizes["body"] * max(body) * 0.98


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


# --------------------------------------------------------------------------- heading bands, paragraph room


def _pt(p):
    return (p.style.font_size or 0) * p.font_scale


def _role(placed, role):
    return [p for p in of(placed, Text) if p.element.role == role]


def test_box_heading_is_never_smaller_than_the_grown_body_text():
    for theme in ("jp-business", "default", "midnight"):
        s = Slide(title=T("t", "title"), grid="2", elements=[box("a", "x", "y"), box("b", "x", "y")])
        placed, _ = lay(s, theme)
        body = max(_pt(p) for p in _role(placed, "body"))
        heads = {round(_pt(p), 2) for p in _role(placed, "heading")}
        assert len(heads) == 1  # siblings share one heading size
        assert min(heads) >= body * 0.98, (theme, heads, body)
        assert min(heads) <= body * 1.2  # ... of the same order as the body text


LONG_HEAD = "とても長い見出しとても長い見出しとても長い見出しとても長い見出し"  # wraps in a quarter-width box


def test_heading_band_height_follows_the_heading_text_and_is_equal_in_a_row():
    s = Slide(
        title=T("t", "title"),
        grid="4",
        elements=[
            box("短い", "x", "y"),
            box(LONG_HEAD, "x", "y"),
            box("見出し", "x", "y"),
            box("見出し", "x", "y"),
        ],
    )
    placed, _ = lay(s)
    heads = _role(placed, "heading")
    assert len(heads) == 4 and len({p.h for p in heads}) == 1  # one band height for the row
    assert len({p.y for p in heads}) == 1
    solo, _ = lay(
        Slide(
            title=T("t", "title"),
            grid="4",
            elements=[box("a", "x"), box("b", "x"), box("c", "x"), box("d", "x")],
        )
    )
    assert heads[0].h > _role(solo, "heading")[0].h * 1.5  # the shared band is taller than a one-line band
    assert len({p.y for p in _role(placed, "body")}) == 1  # bodies start at the same height


def test_band_height_is_per_row():
    s = Slide(
        title=T("t", "title"),
        grid="2x2",
        elements=[box("短い", "x"), box(LONG_HEAD, "x"), box("c", "x"), box("d", "x")],
    )
    placed, _ = lay(s)
    h = _role(placed, "heading")
    assert h[0].h == h[1].h and h[2].h == h[3].h and h[0].h > h[2].h


def test_roomy_card_spreads_its_paragraphs_and_the_measure_matches():
    from slidemark.layout import measure

    s = Slide(title=T("t", "title"), grid="2", elements=[box("a", "x", "y", "z"), box("b", "x", "y", "z")])
    placed, _ = lay(s, "default")
    for b in _role(placed, "body"):
        gap = b.element.attrs.get("para_gap")
        assert gap is not None and measure.PARA_GAP < gap <= 0.6 + 1e-9
        plain = measure.paragraphs_height(b.element.paragraphs, b.w, b.style, b.font_scale)
        spread = measure.paragraphs_height(b.element.paragraphs, b.w, b.style, b.font_scale, gap=gap)
        assert spread > plain
        assert spread <= b.h * 1.01  # the text with its spacing fits the box it was given


def test_full_or_single_paragraph_cards_get_no_extra_spacing():
    many = tuple(f"line number {i} of a very full card" for i in range(9))
    shrunk = tuple(f"line {i} with some more words to wrap around the card width" for i in range(30))
    for items in (("x",), many, shrunk):
        s = Slide(title=T("t", "title"), grid="2", elements=[box("a", *items), box("b", *items)])
        placed, _ = lay(s, "default")
        assert all("para_gap" not in b.element.attrs for b in _role(placed, "body"))


def test_slide_text_beside_grown_boxes_is_at_most_one_step_smaller():
    s = Slide(
        title=T("t", "title"),
        elements=[bullets("日時: 10月2日", "場所: 会議室A", "出席者: 5名"), box("決定事項", "a", "b", "c")],
    )
    placed, _ = lay(s)
    text, in_box = _role(placed, "body")
    assert text.element.paragraphs[0].plain.startswith("日時")
    assert _pt(in_box) > get_theme("jp-business").sizes["body"]  # the box text did grow
    assert _pt(text) > get_theme("jp-business").sizes["body"]  # ... and the slide text follows it
    assert _pt(in_box) / 1.12 - 0.05 <= _pt(text) <= _pt(in_box) + 1e-6


def test_badge_is_never_split_across_lines_in_the_measure():
    from slidemark.layout import measure

    p = Paragraph(runs=[Run(text="画面設計 "), Run(text="進行中", highlight="primary")])
    segs = measure.para_segments(p)
    assert measure.count_lines(segs, 8 * 10, 10) == 2  # 4em + badge 5em (padded) > 8em: the badge moves down
    assert measure.count_lines([s[:3] for s in segs], 8 * 10, 10) == 1  # plain text of the same width fits
    assert measure.count_lines(segs, 12 * 10, 10) == 1
    latin = Paragraph(runs=[Run(text="status "), Run(text="in progress", highlight="primary")])
    assert measure.count_lines(measure.para_segments(latin), 7 * 10, 10) == 2  # a Latin badge keeps its space


def _gaps(placed):
    return [b.element.attrs.get("para_gap") for b in _role(placed, "body")]


def test_sibling_boxes_in_a_row_share_the_smallest_paragraph_gap():
    full = tuple(f"line number {i} of a very full card" for i in range(9))
    s = Slide(title=T("t", "title"), grid="2", elements=[box("a", "x", "y", "z"), box("b", *full)])
    placed, _ = lay(s, "default")
    assert _gaps(placed) == [None, None]  # the full box has no room to spread: the roomy one follows it


def test_sibling_boxes_with_different_spread_end_up_equal():
    s = Slide(
        title=T("t", "title"), grid="2", elements=[box("a", "x", "y", "z"), box("b", "x", "y", "z", "w")]
    )
    placed, _ = lay(s, "default")
    g = _gaps(placed)
    assert g[0] == g[1]  # 3 bullets would be spread alone; the 4-bullet sibling is not


def test_single_paragraph_sibling_does_not_pull_the_gap_down():
    s = Slide(title=T("t", "title"), grid="2", elements=[box("a", "x", "y", "z"), box("b", "x")])
    placed, _ = lay(s, "default")
    assert _gaps(placed)[0] is not None


def test_stacked_boxes_share_the_gap():
    full = tuple(f"line number {i} of a very full card" for i in range(6))
    s = Slide(title=T("t", "title"), grid="1", elements=[box("a", "x", "y", "z"), box("b", *full)])
    placed, _ = lay(s, "default")
    g = _gaps(placed)
    assert g[0] == g[1]
