"""Layout of leftover blocks, KPI cards, callouts, connectors, heading bands, dense tightening, tracks."""

from __future__ import annotations

import pytest

from slidemark.ir import Cell, Container, Deck, Link, Paragraph, Run, Shape, Slide, Table, Text
from slidemark.layout import layout_slide
from slidemark.layout.grid import Rect, cell_rects, parse_spec, track_counts
from slidemark.layout.tables import table_grid
from slidemark.theme import get_theme
from slidemark.units import EMU_PER_PT, slide_size, to_emu

THEMES = ["default", "midnight", "jp-business"]


def T(s, role="body", **kw):
    return Text(role=role, paragraphs=[Paragraph(runs=[Run(text=s)])], **kw)


def box(h, body="text", **kw):
    return Container(title=T(h, "heading"), children=[T(body)], **kw)


def cell(t, **kw):
    return Cell(paragraphs=[Paragraph(runs=[Run(text=t)])], **kw)


def lay(slide, theme="default", deck=None):
    deck = deck or Deck(slides=[slide])
    return layout_slide(slide, deck, get_theme(theme), 0), deck


def of(placed, cls):
    return [p for p in placed if isinstance(p.element, cls)]


def lines(placed):
    return [p for p in placed if isinstance(p.element, Shape) and p.element.shape == "line"]


def in_bounds(placed, deck_size="16:9"):
    W, H = slide_size(deck_size)
    for p in placed:
        assert p.x >= 0 and p.y >= 0 and p.x + p.w <= W + 1 and p.y + p.h <= H + 1, p.element.type


def overlap(a, b):
    return a.x < b.x + b.w and b.x < a.x + a.w and a.y < b.y + b.h and b.y < a.y + a.h


def schedule():
    rows = [[cell("a"), cell("b"), cell("c"), cell("d"), cell("e")]]
    rows.append([cell("x"), cell("y"), cell("●", colspan=3), cell(""), cell("")])
    rows.append([cell("p"), cell("q"), cell("1"), cell("2"), cell("3")])
    return Table(rows=rows)


# --------------------------------------------------------------------------- leftover


@pytest.mark.parametrize("theme", THEMES)
def test_chevron_row_then_full_width_table(theme):
    s = Slide(
        title=T("t", "title"),
        grid="4",
        classes=["chevron"],
        elements=[box(f"P{i}") for i in range(4)] + [schedule()],
    )
    placed, deck = lay(s, theme)
    chev = [p for p in placed if isinstance(p.element, Shape) and p.element.shape == "chevron"]
    (tbl,) = of(placed, Table)
    assert len(chev) == 4
    assert len({c.y for c in chev}) == 1  # a single row
    assert tbl.y >= max(c.y + c.h for c in chev)
    th = get_theme(theme)
    assert tbl.x == to_emu(th.margin_x) and tbl.w <= slide_size("16:9")[0] - 2 * to_emu(th.margin_x)
    assert chev[0].h <= tbl.y - chev[0].y  # compact: the table follows right below
    in_bounds(placed)
    assert not [d for d in deck.diagnostics if d.rule == "overflow"]


def test_areas_leftover_block_is_full_width_below_the_grid():
    s = Slide(title=T("t", "title"), grid="aab/aac", elements=[box(f"B{i}") for i in range(4)])
    placed, deck = lay(s)
    cs = of(placed, Container)
    assert len(cs) == 4
    grid, last = cs[:3], cs[3]
    assert last.y >= max(c.y + c.h for c in grid)
    assert last.w > grid[1].w * 2
    for i, a in enumerate(cs):
        for b in cs[i + 1 :]:
            assert not overlap(a, b)
    in_bounds(placed)


def test_cxr_leftover_and_flow_leftover():
    s = Slide(title=T("t", "title"), grid="2x1", elements=[box("a"), box("b"), box("c")])
    placed, _ = lay(s)
    a, b, c = of(placed, Container)
    assert a.y == b.y and c.y > a.y and c.x == a.x and c.w > a.w
    s = Slide(title=T("t", "title"), grid="3", classes=["flow"], elements=[box(str(i)) for i in range(4)])
    placed, _ = lay(s)
    cs = of(placed, Container)
    assert cs[3].y > cs[0].y and cs[3].w > cs[0].w
    in_bounds(placed)


def test_plain_n_grid_still_wraps_into_rows():
    s = Slide(title=T("t", "title"), grid="2", elements=[box(str(i)) for i in range(4)])
    placed, _ = lay(s)
    cs = of(placed, Container)
    assert len({c.w for c in cs}) == 1 and len({c.y for c in cs}) == 2


# --------------------------------------------------------------------------- tables


def test_table_with_placeholders_keeps_five_columns():
    n_rows, n_cols, anchors = table_grid(schedule())
    assert (n_rows, n_cols) == (3, 5)
    assert len(anchors) == 5 + 3 + 5  # covered placeholders are not anchors
    s = Slide(title=T("t", "title"), elements=[schedule()])
    placed, _ = lay(s)
    assert len(of(placed, Table)[0].element.attrs["_col_w"]) == 5


def test_table_without_placeholders_still_works():
    t = Table(rows=[[cell("a"), cell("b"), cell("c")], [cell("x", colspan=2), cell("z")]])
    assert table_grid(t)[1] == 3


# --------------------------------------------------------------------------- kpi


@pytest.mark.parametrize("theme", THEMES)
def test_kpi_number_and_caption(theme):
    th = get_theme(theme)
    kpi = Container(
        classes=["kpi"],
        title=T("売上", "heading"),
        children=[
            Text(
                paragraphs=[
                    Paragraph(runs=[Run(text="12.4億円")]),
                    Paragraph(runs=[Run(text="前年比 +8%")]),
                ]
            )
        ],
    )
    s = Slide(title=T("t", "title"), grid="3", elements=[kpi, kpi.model_copy(), kpi.model_copy()])
    placed, deck = lay(s, theme)
    texts = [p for p in of(placed, Text) if p.element.paragraphs and p.element.role == "body"]
    assert len(texts) == 3
    big, cap = texts[0].element.paragraphs
    assert big.style.font_size >= th.classes["kpi"].font_size and big.style.bold  # a lone row may grow
    assert big.style.color == "primary" and big.style.align == "center"
    assert cap.style.color == "muted" and cap.style.font_size < big.style.font_size
    assert cap.style.align == "center"
    card = of(placed, Container)[0]
    assert texts[0].y > card.y and texts[0].y + texts[0].h <= card.y + card.h
    in_bounds(placed)
    assert not [d for d in deck.diagnostics if d.rule == "overflow"]


def test_kpi_number_shrinks_to_card_width():
    kpi = Container(
        classes=["kpi"], title=T("x", "heading"), children=[T("1,234,567,890,123.45 million yen")]
    )
    s = Slide(title=T("t", "title"), grid="4", elements=[kpi] * 4)
    placed, _ = lay(s)
    big = [p for p in of(placed, Text) if p.element.role == "body"][0]
    assert big.element.paragraphs[0].style.font_size < 36


# --------------------------------------------------------------------------- callouts


@pytest.mark.parametrize("kind,color", [("note", "primary"), ("tip", "success"), ("warn", "accent")])
def test_callout_card_fill_and_border(kind, color):
    th = get_theme("default")
    s = Slide(title=T("t", "title"), elements=[T("careful", classes=["callout", kind])])
    placed, _ = lay(s)
    p = [q for q in of(placed, Text) if "callout" in q.element.classes][0]
    assert p.style.line == color
    assert p.style.fill and p.style.fill != th.color(color) and p.style.fill.startswith("#")
    assert p.style.padding is not None


def test_callout_kinds_have_distinct_tints_and_work_in_boxes():
    kinds = ["note", "tip", "warn", "caution"]
    inner = [T(k, classes=["callout", k]) for k in kinds]
    s = Slide(title=T("t", "title"), elements=[Container(title=T("h", "heading"), children=inner)])
    placed, _ = lay(s, "midnight")
    cs = [q for q in of(placed, Text) if "callout" in q.element.classes]
    assert len({c.style.fill for c in cs}) == 4
    card = of(placed, Container)[0]
    for c in cs:
        assert c.x >= card.x and c.x + c.w <= card.x + card.w and c.y + c.h <= card.y + card.h
    for a, b in zip(cs, cs[1:], strict=False):
        assert not overlap(a, b)


# --------------------------------------------------------------------------- connectors


def test_horizontal_links_between_grid_cells():
    s = Slide(
        title=T("t", "title"),
        grid="3",
        elements=[box("a"), box("b"), box("c")],
        links=[Link(src=0, dst=1), Link(src=1, dst=2, arrow=False)],
    )
    placed, deck = lay(s)
    cs = of(placed, Container)
    ls = lines(placed)
    assert len(ls) == 2 and placed.index(ls[0]) > max(placed.index(c) for c in cs)  # on top
    assert ls[0].x == cs[0].x + cs[0].w and ls[0].x + ls[0].w == cs[1].x
    a0 = ls[0].element.attrs
    assert (a0["head"], a0["flip_h"], a0["flip_v"], a0["elbow"], a0["route"]) == (
        "arrow",
        False,
        False,
        False,
        "h",
    )
    assert ls[1].element.attrs["head"] == "none"
    assert ls[0].y == cs[0].y + cs[0].h // 2 and ls[0].h == 0
    assert ls[0].w > 0.3 * 914400 * 0.9  # room for an arrow head
    assert not deck.diagnostics


def test_vertical_and_reversed_links():
    s = Slide(
        title=T("t", "title"),
        grid="1x2",
        elements=[box("a"), box("b")],
        links=[Link(src=0, dst=1), Link(src=1, dst=0)],
    )
    placed, _ = lay(s)
    a, b = of(placed, Container)
    down, up = lines(placed)
    assert down.y == a.y + a.h and down.y + down.h == b.y and down.w == 0
    assert not down.element.attrs["flip_v"] and up.element.attrs["flip_v"]
    assert up.y == down.y and up.h == down.h


def test_reversed_horizontal_link_flips_x():
    s = Slide(title=T("t", "title"), grid="2", elements=[box("a"), box("b")], links=[Link(src=1, dst=0)])
    placed, _ = lay(s)
    a, b = of(placed, Container)
    (ln,) = lines(placed)
    assert ln.element.attrs["flip_h"] is True
    assert ln.x == a.x + a.w and ln.x + ln.w == b.x


def test_container_links_between_children():
    inner = Container(
        grid="3",
        classes=["plain"],
        children=[box("x"), box("y"), box("z")],
        links=[Link(src=0, dst=1), Link(src=1, dst=2)],
    )
    s = Slide(title=T("t", "title"), elements=[Container(title=T("h", "heading"), children=[inner])])
    placed, _ = lay(s)
    inner_cards = of(placed, Container)[2:]
    ls = lines(placed)
    assert len(ls) == 2
    for ln, (a, b) in zip(ls, zip(inner_cards, inner_cards[1:], strict=False), strict=True):
        assert ln.x == a.x + a.w and ln.x + ln.w == b.x
    in_bounds(placed)


def test_links_follow_chevron_actual_rects_and_bad_link_is_diagnostic():
    s = Slide(
        title=T("t", "title"),
        grid="3",
        elements=[box("a"), box("b")],
        links=[Link(src=0, dst=7)],
    )
    placed, deck = lay(s)
    assert not lines(placed)
    assert any(d.rule == "link" and d.hint for d in deck.diagnostics)


def test_links_after_leftover_use_real_rects():
    s = Slide(
        title=T("t", "title"),
        grid="2x1",
        elements=[box("a"), box("b"), box("c")],
        links=[Link(src=0, dst=2)],
    )
    placed, _ = lay(s)
    a, _b, c = of(placed, Container)
    (ln,) = lines(placed)
    assert ln.y == a.y + a.h and ln.y + ln.h == c.y


# --------------------------------------------------------------------------- band, dense, tracks


def test_heading_band_on_jp_business_only():
    s = Slide(title=T("t", "title"), elements=[box("Head", "body")])
    jp, _ = lay(s, "jp-business")
    card = of(jp, Container)[0]
    head = [p for p in of(jp, Text) if p.element.role == "heading"][0]
    th = get_theme("jp-business")
    assert head.style.fill == th.heading_band and head.style.color == th.heading_band_color
    assert head.style.bold
    assert (head.x, head.y, head.w) == (card.x, card.y, card.w)
    body = [p for p in of(jp, Text) if p.element.role == "body"][0]
    assert body.y >= head.y + head.h
    default, _ = lay(s, "default")
    head2 = [p for p in of(default, Text) if p.element.role == "heading"][0]
    assert head2.style.fill is None and head2.x > of(default, Container)[0].x


@pytest.mark.parametrize("theme", THEMES)
def test_dense_tightens_gaps_and_paddings(theme):
    els = [box("a"), box("b")]
    th = get_theme(theme).model_copy(deep=True)  # the sparse step (padding x step) is tested elsewhere
    th.layout = th.layout.model_copy(update={"sparse_step": 1.0, "sparse_step_min": 1.0})

    def lay_(slide):
        return layout_slide(slide, Deck(slides=[slide]), th, 0), None

    normal, _ = lay_(Slide(title=T("t", "title"), grid="2", elements=els))
    dense, _ = lay_(Slide(title=T("t", "title"), grid="2", classes=["dense"], elements=els))
    n1, n2 = of(normal, Container)
    d1, d2 = of(dense, Container)
    gap_n, gap_d = n2.x - (n1.x + n1.w), d2.x - (d1.x + d1.w)
    assert gap_d == pytest.approx(gap_n * 0.7, abs=EMU_PER_PT)
    pad = lambda p: to_emu(p.style.padding)  # noqa: E731
    assert pad(d1) == pytest.approx(pad(n1) * 0.7, abs=EMU_PER_PT * 0.1)
    inset = lambda ps, c: [t.x - c.x for t in of(ps, Text) if t.element.role == "body"][0]  # noqa: E731
    assert inset(dense, d1) < inset(normal, n1)


def test_deck_level_dense_also_tightens():
    s = Slide(title=T("t", "title"), grid="2", elements=[box("a"), box("b")])
    a, _ = lay(s)
    b, _ = lay(s, deck=Deck(slides=[s], density="dense"))
    ga = of(a, Container)[1].x - (of(a, Container)[0].x + of(a, Container)[0].w)
    gb = of(b, Container)[1].x - (of(b, Container)[0].x + of(b, Container)[0].w)
    assert gb < ga


def test_track_counts():
    assert track_counts([1, 2], 12) == [4, 8]
    assert track_counts([1, 2, 1], 12) == [3, 6, 3]
    assert track_counts([1, 1.5], 12) == [5, 7]
    assert track_counts([1, 1, 1], 12) is None  # equal columns already align
    assert track_counts([1], 12) is None
    assert sum(track_counts([1, 3, 7, 2, 5], 12)) == 12


def test_ratio_edges_land_on_tracks_and_keep_gap():
    gap = 100_000
    area = Rect(500_000, 0, 12_000_000, 1000)
    tw = (area.w - gap * 11) / 12
    for spec, expect in (("1:2", [4, 8]), ("1:3", [3, 9]), ("1:1:2", [3, 3, 6])):
        gs = parse_spec(spec, len(expect))
        rs = cell_rects(gs, len(expect), area, gap)
        t0 = 0
        for r, k in zip(rs, expect, strict=True):
            assert r.x == pytest.approx(area.x + t0 * (tw + gap), abs=1)
            assert r.w == pytest.approx(k * tw + (k - 1) * gap, abs=1)
            t0 += k
        for a, b in zip(rs, rs[1:], strict=False):
            assert b.x - (a.x + a.w) == pytest.approx(gap, abs=1)


def test_area_grid_snaps_and_rows_share_edges():
    gs = parse_spec("aab/aac", 3)
    rs = cell_rects(gs, 3, Rect(0, 0, 3_000_000, 600_000), 0)
    assert rs[0].w == 2_000_000 and rs[1].x == rs[2].x == 2_000_000


def test_odd_input_never_raises():
    s = Slide(
        title=T("t", "title"),
        grid="3 chevron",
        links=[Link(src=5, dst=5), Link(src=0, dst=0)],
        elements=[Container(classes=["kpi"]), Container(classes=["kpi"], children=[Table()]), T("x")],
    )
    placed, deck = lay(s)
    assert placed  # no exception; problems are diagnostics
    assert [d.rule for d in deck.diagnostics].count("link") == 2
