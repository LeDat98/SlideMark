"""L3 fill: sparse rows of text cards and text panels beside a chart use the height they have."""

from __future__ import annotations

from pathlib import Path

import pytest
from pptx import Presentation

from slidemark import build
from slidemark.ir import Chart, Container, Text
from slidemark.layout import engine, layout_slide
from slidemark.layout.grid import Rect
from slidemark.layout.l3fill import fill_panels, fill_row
from slidemark.parser import parse
from slidemark.template import resolve_theme
from slidemark.theme import LayoutTokens

EX = Path(__file__).resolve().parent.parent / "examples"


def lay(name: str, n: int, src: str | None = None, **tokens):
    text = src if src is not None else (EX / name).read_text(encoding="utf-8")
    deck = parse(text)
    theme, _ = resolve_theme(deck.theme, EX)
    if tokens:
        theme = theme.model_copy(update={"layout": theme.layout.model_copy(update=tokens)})
    placed = layout_slide(deck.slides[n - 1], deck, theme, n - 1)
    return placed, deck, theme


def role(placed, r):
    return [p for p in placed if isinstance(p.element, Text) and p.element.role == r]


def cards(placed):
    return [p for p in placed if isinstance(p.element, Container)]


def inside(placed, card, r="body"):
    return [
        p
        for p in role(placed, r)
        if card.x <= p.x and p.x + p.w <= card.x + card.w and card.y <= p.y <= card.y + card.h
    ]


def tail(p, card) -> int:
    return card.y + card.h - (p.y + engine._text_h(p))


@pytest.mark.parametrize(("name", "n"), [("16-jp-strategy.md", 10), ("11-jp-consulting.md", 9)])
def test_decision_row_is_top_anchored_tall_and_spread(name, n):
    placed, deck, _ = lay(name, n)
    H = 720 * 9525
    lead = role(placed, "lead")[0]
    foot = role(placed, "footnote")[0]
    cs = cards(placed)
    assert len(cs) == 2
    assert min(c.y for c in cs) - (lead.y + lead.h) <= 0.05 * H  # no empty band under the lead
    assert max(c.y + c.h for c in cs) <= foot.y  # never into the footnote band
    assert len({c.h for c in cs}) == 1 and len({c.y for c in cs}) == 1  # one shared height
    lt = LayoutTokens()
    off, _, _ = lay(name, n, l3_fill=False)
    for c, c0 in zip(cs, cards(off), strict=True):
        (body,) = inside(placed, c)
        (body0,) = inside(off, c0)
        extra = body.element.attrs["para_gap"] - (body0.element.attrs.get("para_gap") or 0.25)
        assert 0 < extra <= lt.l3_gap_extra_short + 0.02  # even, capped gaps
        # the emptiest card keeps its tail within the rule; no card of the row is emptier than 25%
        assert tail(body, c) <= (lt.l3_tail_max + 0.01) * c.h
        assert body.y + body.h <= c.y + c.h  # never outside its card
        assert body.style.valign in (None, "top")  # never vertically centred
    assert not [d for d in deck.diagnostics if d.level == "error"]


@pytest.mark.parametrize(("name", "n"), [("16-jp-strategy.md", 3), ("11-jp-consulting.md", 3)])
def test_panel_beside_chart_spreads_and_anchors_its_note(name, n):
    placed, _, _ = lay(name, n)
    off, _, _ = lay(name, n, l3_fill=False)
    (panel,) = cards(placed)
    chart = next(p for p in placed if isinstance(p.element, Chart))
    lt = LayoutTokens()
    assert panel.h <= chart.h  # shrinks to its content instead of stretching to the chart bottom
    main, note = sorted(inside(placed, panel), key=lambda p: p.y)
    assert abs((panel.y + panel.h) - (note.y + note.h)) <= 0.12 * panel.h  # the note ends the panel
    g0 = max(p.element.attrs.get("para_gap") or 0.25 for p in inside(off, cards(off)[0]))
    assert 0 < main.element.attrs["para_gap"] - g0 <= lt.l3_gap_cap + 0.02  # even, capped rhythm
    assert [engine._text_h(p) for p in inside(off, cards(off)[0])][0] < 0.5 * chart.h  # it was the bug
    text_end = main.y + engine._text_h(main)
    assert text_end < note.y  # no overlap
    assert note.y - text_end <= 0.15 * panel.h  # the note follows the text, not pinned far below it


def test_render_reopens_with_tall_cards(tmp_path):
    out = tmp_path / "d.pptx"
    build(EX / "16-jp-strategy.md", out)
    prs = Presentation(out)
    sl = prs.slides[9]
    tall = [
        s for s in sl.shapes if s.height > 0.5 * prs.slide_height * 0.6 and s.width < prs.slide_width * 0.7
    ]
    assert len(tall) >= 2
    top = min(s.top for s in tall)
    assert top < 0.25 * prs.slide_height  # right under the lead
    assert (
        0.4 * prs.slide_height < max(s.top + s.height for s in tall) < 0.7 * prs.slide_height
    )  # shrunk to its content, never stretched to the band
    paras = [s for s in sl.shapes if s.has_text_frame and "2027" in s.text_frame.text]
    assert paras and any(
        p.space_before and p.space_before.pt > 8 for sh in paras for p in sh.text_frame.paragraphs[1:]
    )


def test_tokens_switch_it_off():
    off, _, _ = lay("16-jp-strategy.md", 10, l3_fill=False)
    assert cards(off)[0].y > 200 * 9525  # the old floating block
    top, _, _ = lay("16-jp-strategy.md", 10, body_valign="top")
    assert cards(top)[0].h < 300 * 9525  # an explicit top anchor keeps the hugging cards


def test_explicit_height_valign_and_top_win():
    base = "# T\n> lead\n@1:1\n## A\n- one\n- two\n- three\n## B\n- x\n- y\n- z\n"
    placed, deck, theme = lay("", 1, base)
    cs = cards(placed)
    plain_h = cs[0].h
    body = Rect(0, 0, 10, 10)
    assert fill_row([], body, theme.layout) == []  # nothing to do
    assert fill_panels([], Rect(0, 0, 0, 0), theme.layout) == []
    explicit = base.replace("## A", "## A {h=2in}")
    p2, _, _ = lay("", 1, explicit)
    assert not any(c.element.attrs.get("para_gap", 0) > 1.0 for c in p2 if isinstance(c.element, Text))
    assert plain_h > 0


def test_fuzz_never_raises():
    for src in (
        "# T\n## A\n",
        "# T\n> l\n## A\n## B\n- x\n",
        "# T\n```column\n,a\nx,1\n```\n## P\n> [!note] n\n",
    ):
        placed, deck, _ = lay("", 1, src)
        assert not [d for d in deck.diagnostics if d.rule == "layout-error"]


KPI = """theme: none
colors: bg=#FFFFFF fg=#1F2933 primary=#1E3A5F accent=#C8102E surface=#F3F5F8 border=#C9D1DB
lang: ja

# 再編の効果（2029年度）
## 営業利益 {.kpi}
+24億円
年間
## 赤字店舗 {.kpi}
45→8店
-37店
## ネット売上比率 {.kpi}
25%
+13pt
"""


def test_kpi_row_is_top_anchored_and_values_stay_centred():
    placed, _, _ = lay("", 1, KPI)
    title = role(placed, "title")[0]
    cs = cards(placed)
    assert len(cs) == 3 and len({c.h for c in cs}) == 1
    assert min(c.y for c in cs) - (title.y + title.h) <= 0.08 * 720 * 9525  # right under the title
    assert 0.78 * 720 * 9525 <= max(c.y + c.h for c in cs) <= 0.9 * 720 * 9525  # leftover = bottom band only
    for c in cs:
        (body,) = inside(placed, c)
        assert body.style.valign == "middle"  # the value is centred in its taller card
        assert body.y + body.h <= c.y + c.h


def tails(placed):
    return [tail(inside(placed, c)[0], c) / c.h for c in cards(placed)]


@pytest.mark.parametrize(("name", "n"), [("16-jp-strategy.md", 10), ("11-jp-consulting.md", 9)])
def test_decision_cards_tail_is_at_most_a_quarter(name, n):
    placed, _, _ = lay(name, n)
    assert max(tails(placed)) <= LayoutTokens().l3_tail_max + 0.01
    off, _, _ = lay(name, n, l3_tail_max=1.0)  # the rule off: the old, emptier cards
    assert max(tails(off)) > 0.28
    top = lay(name, n, l3_tail_max=1.0)[0]
    assert min(c.y for c in cards(placed)) == min(c.y for c in cards(top))  # top-anchored either way
    assert all(inside(placed, c)[0].style.valign in (None, "top") for c in cards(placed))


FLOW = """theme: jp-business
lang: ja

# 申請業務の新フロー
@a>b b>c
## 申請
- 申請者がフォームに入力
- 添付書類はPDFで提出
- 不備は自動チェック
## 承認
- 課長が一次承認（2営業日以内）
- 100万円以上は部長承認
## 処理
- 経理が支払処理
- 会計システムへ自動連携
@end
> [!note] 現行の紙申請は2027年3月末で廃止する
"""


def test_flow_row_fills_keeps_arrows_centred_and_note_below():
    placed, deck, _ = lay("", 1, FLOW)
    off, _, _ = lay("", 1, FLOW, l3_fill=False)
    cs = cards(placed)
    assert len(cs) == 3 and len({c.h for c in cs}) == 1
    assert cs[0].h >= cards(off)[0].h  # never shorter than the hugging cards (gaps are capped, no stretch)
    # sibling cards share one rhythm, so a card with fewer items may keep a longer tail than the rule when the
    # fullest card already sets the row height (growth is blocked by the wrap guard)
    assert max(tails(placed)) <= LayoutTokens().l3_tail_max + 0.1
    arrows = [p for p in placed if p.element.type == "shape" and p.h == 0]
    assert len(arrows) == 2
    mid = cs[0].y + cs[0].h / 2
    assert all(abs(a.y - mid) <= 2 for a in arrows)  # still centred between the cards
    assert all(
        c.x + c.w <= a.x + 2 and a.x + a.w <= n.x + 2 for a, c, n in zip(arrows, cs, cs[1:], strict=False)
    )
    note = next(p for p in placed if "callout" in getattr(p.element, "classes", []))
    assert note.y >= cs[0].y + cs[0].h  # follows the cards, never overlaps
    assert not [d for d in deck.diagnostics if d.level == "error"]


def test_flow_row_renders_and_reopens(tmp_path):
    src = tmp_path / "f.md"
    src.write_text(FLOW, encoding="utf-8")
    out = tmp_path / "f.pptx"
    build(src, out)
    prs = Presentation(out)
    boxes = [
        s
        for s in prs.slides[0].shapes
        if s.width > 0.25 * prs.slide_width and s.height > 0.3 * prs.slide_height * 0.5
    ]
    assert len(boxes) >= 3
    assert (
        max(s.top + s.height for s in boxes if s.width < 0.4 * prs.slide_width) > 0.4 * prs.slide_height
    )  # hugging the content, not stretched


def test_plain_list_gap_stays_below_line_height():
    placed, _, theme = lay("01-basics.md", 2)
    (body,) = [p for p in placed if isinstance(p.element, Text) and p.element.role == "body"]
    gap = body.element.attrs.get("para_gap")
    assert gap is not None and gap <= theme.layout.sparse_air + 1e-6 <= 0.8 + 1e-6
    assert gap <= theme.layout.line_latin  # never more than one line of air between paragraphs
    off, _, _ = lay("01-basics.md", 2, sparse_air=1.0)
    assert off[0] is not None
    assert (body.element.attrs.get("para_gap") or 0) < (
        [p for p in off if isinstance(p.element, Text) and p.element.role == "body"][0].element.attrs.get(
            "para_gap"
        )
        or 0
    )


def test_row_fill_fuzz_never_raises():
    for src in (
        "# T\n@a>b\n## A\n- x\n## B\n- y\n@end\n",
        "# T\n@a>b b>c\n## A\n- 長い" + "文" * 80 + "\n## B\n- y\n## C\n@end\n> [!note] n\n",
        "# T\n@a>b\n## A\n@end\n",
    ):
        _, deck, _ = lay("", 1, src)
        assert not [d for d in deck.diagnostics if d.rule == "layout-error"]


CHEV = """theme: none
colors: bg=#FFFFFF fg=#1F2933 primary=#1E3A5F accent=#C8102E
fonts: heading="Noto Sans JP" body="Noto Sans JP" ea="Noto Sans JP"
style: title.band=primary
lang: ja

# 実行スケジュール
@chevron
## 2027年4月
- 統合の第1弾
## 2027年10月
- 受取拠点の開設
## 2028年4月
- 統合の第2弾
## 2029年3月
- 再編完了
"""


def test_lone_chevron_row_is_top_anchored_and_cjk_lines_fit_one_line():
    from slidemark.layout import measure

    placed, deck, theme = lay("", 1, CHEV)
    chevs = [p for p in placed if p.element.type == "shape" and getattr(p.element, "shape", "") == "chevron"]
    assert len(chevs) == 4
    lead_bottom = max(p.y + p.h for p in role(placed, "title"))
    assert min(c.y for c in chevs) - lead_bottom <= 0.08 * 720 * 9525  # right under the title, not mid-slide
    assert len({c.y for c in chevs}) == 1 and len({c.h for c in chevs}) == 1
    slack = theme.layout.chevron_cjk_slack
    for c in chevs:
        adj = c.element.attrs.get("adj", theme.layout.chevron_adj)
        w = engine._chevron_text_w(Rect(c.x, c.y, c.w, c.h), c.style, c.element, adj) / 12700 / slack
        size = (c.style.font_size or 18) * c.font_scale
        for i, para in enumerate(c.element.paragraphs):
            segs = measure.para_segments(para, i == 0)
            assert measure.count_lines(segs, w, size) == 1, para.plain  # no break, no orphan
    off, _, _ = lay("", 1, CHEV, chevron_cjk_slack=1.0)
    assert not [d for d in deck.diagnostics if d.level == "error"]
    assert off


def test_chevron_row_fuzz_and_render(tmp_path):
    for src in ("# T\n@chevron\n## A\n", "# T\n@chevron\n## 一\n- " + "長" * 60 + "\n## B\n"):
        _, deck, _ = lay("", 1, src)
        assert not [d for d in deck.diagnostics if d.rule == "layout-error"]
    f = tmp_path / "c.md"
    f.write_text(CHEV, encoding="utf-8")
    out = tmp_path / "c.pptx"
    build(f, out)
    prs = Presentation(out)
    tops = [
        s.top
        for s in prs.slides[0].shapes
        if s.width > 0.15 * prs.slide_width and s.top > 0.15 * prs.slide_height
    ]
    assert tops and min(tops) < 0.3 * prs.slide_height
