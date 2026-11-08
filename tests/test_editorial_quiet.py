"""Editorial look as tokens: quiet lead, no stretch, hairline tables, sans box headings, CJK phrase lines."""

from __future__ import annotations

from pptx import Presentation
from pptx.util import Emu

from slidemark import build
from slidemark.layout import measure
from slidemark.layout.jbreak import packed_lines
from slidemark.theme import LayoutTokens, get_theme

CARDS = """theme: editorial

# Request path
> A quiet lead line
@3
## Web client {.input}
Browser app
## API gateway {.focal}
Auth and routing
## Postgres {.store}
Orders and users
"""

TABLE = """theme: editorial

# Costs
```table
Service,Owner,Cost
Gateway,Platform,"$4,200"
Orders DB,Data,"$6,800"
```
"""


def _prs(tmp_path, text):
    out = tmp_path / "d.pptx"
    build(text, out)
    return Presentation(out)


def _named(slide, prefix):
    return [s for s in slide.shapes if s.name.startswith(prefix)]


def _sizes(shape):
    return {r.font.size.pt for p in shape.text_frame.paragraphs for r in p.runs if r.font.size}


def test_lead_is_quiet_in_editorial(tmp_path):
    prs = _prs(tmp_path, CARDS)
    lead = next(
        s for s in prs.slides[0].shapes if s.has_text_frame and s.text_frame.text.startswith("A quiet")
    )
    assert max(_sizes(lead)) <= 14.5
    assert lead.text_frame.paragraphs[0].runs[0].font.bold in (None, False)


def test_editorial_cards_hug_their_content(tmp_path):
    prs = _prs(tmp_path, CARDS)
    slide = prs.slides[0]
    cards = [s for s in slide.shapes if s.name.startswith("Card") or s.name.startswith("Box")]
    assert cards
    tallest = max(c.height for c in cards)
    assert Emu(tallest).inches < 1.6  # a few lines of 13pt text, never stretched down the body
    for c in cards:
        for s in _sizes(c):
            assert s <= 14.5  # no 15pt+ body in cards


def test_box_heading_is_bold_body_sans(tmp_path):
    prs = _prs(tmp_path, CARDS)
    runs = [
        r
        for s in prs.slides[0].shapes
        if s.has_text_frame
        for p in s.text_frame.paragraphs
        for r in p.runs
        if r.text == "Web client"
    ]
    assert runs
    assert runs[0].font.name == "Arial"  # the body face, not the Georgia of the titles
    assert runs[0].font.bold


def test_table_has_hairline_rows_and_no_vertical_rules(tmp_path):
    prs = _prs(tmp_path, TABLE)
    tbl = next(s for s in prs.slides[0].shapes if s.has_table).table
    tcpr = tbl.cell(1, 1)._tc.tcPr
    ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
    for side in ("lnL", "lnR"):
        ln = tcpr.find(ns + side)
        assert ln is not None and ln.find(ns + "noFill") is not None
    assert tcpr.find(ns + "lnB").find(ns + "solidFill") is not None
    head = tbl.cell(0, 1)._tc.tcPr.find(ns + "lnB")
    assert head.get("w") == "12700"  # the 1 pt rule under the header
    sizes = {r.font.size.pt for c in tbl.iter_cells() for p in c.text_frame.paragraphs for r in p.runs}
    assert max(sizes) <= 12.5


def test_table_rows_are_not_stretched(tmp_path):
    prs = _prs(tmp_path, TABLE)
    tbl = next(s for s in prs.slides[0].shapes if s.has_table).table
    assert all(Emu(r.height).inches < 0.5 for r in tbl.rows)


def test_other_presets_keep_stretching_defaults():
    assert get_theme("default").layout.grow_max == LayoutTokens().grow_max
    assert get_theme("editorial").layout.grow_max == 1
    assert get_theme("default").table_rules == "grid"
    assert get_theme("editorial").table_rules == "rows"


def test_chart_title_is_quiet_and_only_one_bar_is_outlined(tmp_path):
    deck = """theme: editorial

# Orders
```column {title="Orders (k)" hl=Q3}
,Q1,Q2,Q3
Orders,120,150,240
Refunds,12,14,18
```
"""
    prs = _prs(tmp_path, deck)
    chart = next(s for s in prs.slides[0].shapes if s.has_chart).chart
    assert not chart.chart_title.text_frame.paragraphs[0].runs[0].font.bold
    outlined = [
        si
        for si, ser in enumerate(chart.plots[0].series)
        if ser.points[2].format.line.fill.type is not None and ser.points[2].format.line.width
    ]
    assert outlined == [0]


def _para(text):
    from slidemark.ir import Paragraph, Run

    return Paragraph(runs=[Run(text=text)])


def test_cjk_phrase_lines_reserve_the_lines_whole_phrases_need():
    # 161pt at 21pt: character-wise it is 2 lines (注文処理は単一 / の DB に集中), by phrases it is 3
    from slidemark.ir import Style

    p = _para("注文処理は単一のDBに集中")
    st = Style(font_size=21, font="Arial")
    measure.set_tokens(LayoutTokens(cjk_phrase_lines=True))
    try:
        assert packed_lines(p, st, 161.2, 21) == 3
        h_on = measure.paragraphs_height([p], 161.2 * 12700, st)
        measure.set_tokens(LayoutTokens(cjk_phrase_lines=False))
        h_off = measure.paragraphs_height([p], 161.2 * 12700, st)
        assert h_on > h_off
    finally:
        measure.set_tokens(LayoutTokens())


def test_cjk_phrase_binding_holds_in_editorial_cards(tmp_path):
    deck = """theme: editorial
style: card.font_size=21

# 計画
@4
## 現状
- 注文処理は単一のDBに集中
## 課題
- 読み取りと書き込みが競合
## 施策
- 読み取りレプリカを追加
## 管理
- 鍵はVaultで集中管理
"""
    prs = _prs(tmp_path, deck)
    texts = []
    for s in prs.slides[0].shapes:
        if s.has_text_frame:
            for p in s.text_frame.paragraphs:
                # the renderer writes a soft break (a:br) at the phrase boundary: "単一の" is never cut
                xml = p._p.xml
                if "注文処理は" in "".join(r.text for r in p.runs):
                    texts.append([r.text for r in p.runs])
                    assert "<a:br" in xml
    assert texts
    assert all("単一の" in "".join(t) for t in texts)
    assert not any(t and t[0].endswith("単一") for t in texts)
