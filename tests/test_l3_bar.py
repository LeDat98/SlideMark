"""Cards reach the conclusion bar, the bar keeps air above the footnote, lone chevron text grows."""

# ruff: noqa: E501
from __future__ import annotations

import random

import pytest
from pptx import Presentation

from slidemark import build
from slidemark.ir import Container, Text
from slidemark.layout import measure
from slidemark.layout.grid import Rect
from slidemark.layout.l3fill import fill_cards_to_bar
from slidemark.theme import LayoutTokens
from slidemark.units import to_emu

from .test_layout_l3_fill import EX, cards, inside, lay, role

EMU_IN = 914400
CASES = [("16-jp-strategy.md", 10), ("11-jp-consulting.md", 9), ("11-jp-consulting.md", 8)]


def _bar(placed):
    return role(placed, "conclusion")[0]


@pytest.mark.parametrize(("name", "n"), CASES)
def test_cards_stretch_down_to_one_gap_above_the_bar(name, n):
    placed, _, theme = lay(name, n)
    cs, bar, lead = cards(placed), _bar(placed), role(placed, "lead")
    gap = to_emu(theme.gap) // 2
    last = max(c.y + c.h for c in cs)
    assert 0 <= bar.y - last <= gap + 2  # one standard gap, never into the bar
    if lead:
        assert min(c.y for c in cs) - (lead[0].y + lead[0].h) <= 0.3 * EMU_IN  # top-anchored under the lead
    rows: dict[int, set[int]] = {}
    for c in cs:
        rows.setdefault(c.y, set()).add(c.h)
    assert all(len(hs) == 1 for hs in rows.values())  # every card of a row shares one height
    off, _, _ = lay(name, n, cards_to_bar=False)
    assert last > max(c.y + c.h for c in cards(off))  # it really stretched


def test_grid_rows_share_the_slack_and_keep_their_gap():
    placed, _, _ = lay("11-jp-consulting.md", 8)
    off, _, _ = lay("11-jp-consulting.md", 8, cards_to_bar=False)
    ys = sorted({c.y for c in cards(placed)})
    assert len(ys) == 2
    gap = ys[1] - max(c.y + c.h for c in cards(placed) if c.y == ys[0])
    assert 0 < gap <= 0.2 * EMU_IN
    grew = [
        sum(c.h for c in cards(placed) if c.y == y) - sum(c.h for c in cards(off) if c.y == y0)
        for y, y0 in zip(ys, sorted({c.y for c in cards(off)}), strict=True)
    ]
    assert abs(grew[0] - grew[1]) <= 2 * 2  # rows split the slack evenly (2 cards per row)


@pytest.mark.parametrize(("name", "n"), CASES)
def test_stretched_cards_keep_header_text_and_are_not_hollow(name, n):
    placed, _, theme = lay(name, n)
    lt = theme.layout
    for c in cards(placed):
        heads = [p for p in placed if getattr(p.element, "role", None) == "heading" and p.y == c.y]
        assert heads  # the header band stays at the top of the card
        (body,) = inside(placed, c)
        assert body.style.valign in (None, "top")
        assert body.y + body.h <= c.y + c.h
        assert body.y >= max(h.y + h.h for h in heads)
        used = (
            body.y
            - c.y
            + measure.paragraphs_height(
                body.element.paragraphs,
                body.w,
                body.style,
                body.font_scale,
                gap=body.element.attrs.get("para_gap"),
            )
        ) / c.h
        if c.h > 0.4 * EMU_IN * 3:  # a tall card: its list is spread, not one dead band
            assert body.element.attrs.get("para_gap", 0) > 0.25
            assert body.element.attrs["para_gap"] <= max(
                0.25 + lt.card_hollow_gap_cap + 0.5, lt.card_spread_gap_max
            )
        assert used > 0.3


@pytest.mark.parametrize(
    ("name", "n"), [("16-jp-strategy.md", 10), ("11-jp-consulting.md", 8), ("11-jp-consulting.md", 9)]
)
def test_bar_keeps_air_above_the_footnote(name, n):
    placed, _, theme = lay(name, n)
    bar, foot = _bar(placed), role(placed, "footnote")[0]
    assert bar.y + bar.h + to_emu(theme.layout.conclusion_foot_gap) <= foot.y + 2
    tight, _, _ = lay(name, n, conclusion_foot_gap="0in")
    assert foot.y - (_bar(tight).y + _bar(tight).h) < to_emu(theme.layout.conclusion_foot_gap)  # the old 4px


def test_hollow_slide_keeps_hugging_cards():  # 01-basics slide 3: one short bullet per card
    placed, _, _ = lay("01-basics.md", 3)
    off, _, _ = lay("01-basics.md", 3, cards_to_bar=False)
    assert [(c.y, c.h) for c in cards(placed)] == [(c.y, c.h) for c in cards(off)]


def test_token_switches_it_off():
    placed, _, _ = lay("16-jp-strategy.md", 10, cards_to_bar=False)
    assert max(c.y + c.h for c in cards(placed)) < 0.7 * 720 * 9525


def test_render_reopens_with_cards_at_the_bar(tmp_path):
    out = tmp_path / "d.pptx"
    build(EX / "11-jp-consulting.md", out)
    prs = Presentation(out)
    sl = prs.slides[7]
    bar = next(s for s in sl.shapes if s.has_text_frame and "最大のリスク" in s.text_frame.text)
    foot = next(s for s in sl.shapes if s.has_text_frame and s.text_frame.text.startswith("※"))
    boxes = [
        s
        for s in sl.shapes
        if 0.15 * prs.slide_width < s.width < 0.6 * prs.slide_width
        and s.height > 0.2 * prs.slide_height * 0.6
    ]
    assert len(boxes) >= 4
    assert 0 <= bar.top - max(s.top + s.height for s in boxes) <= 0.2 * EMU_IN
    assert foot.top - (bar.top + bar.height) >= 0.1 * EMU_IN


def test_fuzz_never_raises():
    rng = random.Random(7)
    for _ in range(40):
        k = rng.randint(1, 6)
        cols = "".join(
            f"## H{i}\n"
            + "".join(f"- item {i}{j} " + "x" * rng.randint(0, 40) + "\n" for j in range(rng.randint(0, 5)))
            for i in range(k)
        )
        extra = rng.choice(["", "> bar\n", "※ note\n", "> bar\n※ note\n"])
        src = f"theme: jp-business\n\n# T\n> lead\n{rng.choice(['', '@2:2', '@1:1:1'])}\n{cols}{extra}"
        lay("", 1, src)
    assert fill_cards_to_bar([], Rect(0, 0, 10, 10), LayoutTokens(), True, True, True) is None


# ---- lone chevron rows ------------------------------------------------------------------------------

JA3 = "theme: jp-business\nlang: ja\n\n# 導入の進め方\n@chevron\n## 調査\n- 現状把握\n## 試作\n- 小さく検証\n## 展開\n- 全社へ拡大\n"
VI3 = "theme: jp-business\nlang: vi\n\n# Lộ trình\n@chevron\n## Khám phá\n- Phỏng vấn\n## Thử nghiệm\n- Hai cơ sở\n## Mở rộng\n- Toàn công ty\n"
JA5 = "theme: jp-business\nlang: ja\n\n# 新規事業の進め方\n@chevron\n## マーケティング\n- 市場調査\n## プロトタイプ\n- 試作と検証\n## パイロット運用\n- 現場での試行\n## 本格展開\n- 全社へ拡大\n## 効果測定\n- KPI確認\n"
VI5 = "theme: jp-business\nlang: vi\n\n# Lộ trình\n@chevron\n## Tháng 11\n- Thử nghiệm vị\n## Tháng 12\n- Sản xuất lô đầu\n## Tháng 1\n- Ra mắt tại TP.HCM\n## Tháng 3\n- Mở rộng toàn quốc\n## Tháng 6\n- Đánh giá kết quả\n"


def _chev(src, **tokens):
    placed, _, _ = lay("", 1, src, **tokens)
    return [p for p in placed if getattr(p.element, "shape", "") == "chevron"]


def _pt(p):
    return p.style.font_size * p.font_scale


@pytest.mark.parametrize("src", [JA3, VI3, JA5, VI5])
def test_lone_chevron_text_never_shrinks_and_never_breaks_a_word(src):
    from slidemark.layout.engine import _chevron_text_w, _longest_word_em

    on, off = _chev(src), _chev(src, chevron_text_max_pt=0)
    lt = LayoutTokens()
    assert len(on) == len(off) >= 3
    for a, b in zip(on, off, strict=True):
        assert _pt(a) >= _pt(b) - 1e-6
        assert _pt(a) <= max(lt.chevron_text_max_pt, _pt(b)) + 1e-3
        avail = (
            _chevron_text_w(Rect(a.x, a.y, a.w, a.h), a.style, a.element, a.element.attrs.get("adj")) / 12700
        )
        assert _longest_word_em(a.element.paragraphs) * _pt(a) * lt.chevron_word_slack <= avail + 1e-6
        assert (
            measure.paragraphs_height(a.element.paragraphs, avail * 12700, a.style, a.font_scale)
            <= lt.chevron_text_fill * a.h + 1
        )


@pytest.mark.parametrize("src", [JA3, VI3])
def test_lone_three_step_chevron_text_grows(src):
    on, off = _chev(src), _chev(src, chevron_text_max_pt=0)
    assert _pt(on[0]) > _pt(off[0]) * 1.1
    assert len({round(_pt(c), 3) for c in on}) == 1  # one size for the whole row


def test_chevron_render_reopens(tmp_path):
    f = tmp_path / "c.md"
    f.write_text(JA3, encoding="utf-8")
    build(f, tmp_path / "c.pptx")
    shapes = [
        s
        for s in Presentation(tmp_path / "c.pptx").slides[0].shapes
        if s.has_text_frame and s.text_frame.text
    ]
    sizes = [
        r.font.size.pt
        for s in shapes
        for p in s.text_frame.paragraphs
        for r in p.runs
        if r.font.size and "調査" in s.text_frame.text
    ]
    assert sizes and min(sizes) > 20


def test_chevron_alongside_text_is_untouched():
    src = JA3 + "\n> 結論です\n"
    assert isinstance(Container, type) and isinstance(Text, type)
    on, off = _chev(src), _chev(src, chevron_text_max_pt=0)
    assert [_pt(c) for c in on][0] >= _pt(off[0])
