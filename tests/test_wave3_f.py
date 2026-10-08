"""Wave 2026-10-08 lane F: one step label, card headings that never wrap in a row, palette `@proscons`."""

# ruff: noqa: E501

from __future__ import annotations

import pytest
from pptx import Presentation

from slidemark import build, parse
from slidemark.ir import Paragraph, Run
from slidemark.layout import layout_slide, measure
from slidemark.template import deck_theme

HEAD = (
    "theme: none\n"
    "colors: bg=#FFFFFF fg=#14272F primary=#0B2A3C secondary=#1B8A8F accent=#F2A33A surface=#EEF4F6 "
    "muted=#5A6F78\n"
    "fonts: heading=Arial body=Arial\n"
    "sizes: title=34 heading=20 body=16 caption=12\n"
)
STEPS = "# Steps\n@3 steps num\n## Một\n- a\n## Hai\n- b\n## Ba\n- c\n"


def _texts(path) -> list[str]:
    prs = Presentation(str(path))
    return [s.text_frame.text for s in prs.slides[0].shapes if s.has_text_frame]


def _build(tmp_path, src: str, name: str = "d.pptx"):
    out = tmp_path / name
    deck = build(HEAD + src, out)
    return deck, out


# --------------------------------------------------------------------------- 1. one step label


def test_steps_num_draws_no_step_caption_on_the_card_look(tmp_path):
    _deck, out = _build(tmp_path, STEPS)
    assert not any("STEP" in t for t in _texts(out))
    names = [s.name for s in Presentation(str(out)).slides[0].shapes]
    assert "Step 1 arrow" in names and "Heading 1" in names


def test_steps_caption_token_states_the_caption_on_the_card_look(tmp_path):
    _deck, out = _build(tmp_path, 'style: steps.caption="Bước {n}"\n' + STEPS)
    assert any(t.startswith("Bước 1") for t in _texts(out))


def test_steps_num_with_head_arrow_draws_the_caption(tmp_path):
    _deck, out = _build(tmp_path, STEPS.replace("steps num", "steps head=arrow num"))
    assert any(t.startswith("STEP 1") for t in _texts(out))
    _deck, out2 = _build(tmp_path, "style: steps.head=arrow\n" + STEPS, "e.pptx")
    assert any(t.startswith("STEP 2") for t in _texts(out2))


def test_steps_num_is_fuzz_safe():
    for src in (
        "# T\n@steps num\n",
        "# T\n@2 steps num\n## a\n",
        "# T\n@3 steps num head=card\n## a\n## b\n",
    ):
        parse(src)


# --------------------------------------------------------------------------- 2. headings never wrap in a row

ROW = (
    "sizes: title=34 heading=22 body=16 caption=12\n\n"
    "# Lộ trình\n@4 num\n"
    "## Thí điểm\n- Chọn 1 bài toán nhỏ\n## Mở rộng\n- Nhân rộng sang các nhóm\n"
    "## Chuẩn hóa\n- Quy tắc về dữ liệu\n## Tối ưu\n- Theo dõi hiệu quả\n"
)
ROW_HEAD = HEAD.replace("sizes: title=34 heading=20 body=16 caption=12\n", "")


def _placed(src: str):
    deck = parse(ROW_HEAD + src)
    theme, _diags = deck_theme(deck, None)
    return layout_slide(deck.slides[0], deck, theme, 0)


def _heading_lines(src: str, extra: str = "") -> list[tuple[float, int, float]]:
    """(drawn size pt, lines, body pt) of every heading text of the first slide, in reading order."""
    placed = _placed(extra + src)
    body = max(
        (
            (p.style.font_size or 18) * p.font_scale
            for p in placed
            if getattr(p.element, "role", "") == "body"
        ),
        default=0.0,
    )
    got = []
    for p in sorted(placed, key=lambda p: (p.x, p.y)):
        el = p.element
        if getattr(el, "role", None) != "heading" or not getattr(el, "paragraphs", None):
            continue
        one = measure.paragraphs_height([Paragraph(runs=[Run(text="Ag")])], p.w, p.style, p.font_scale)
        h = measure.paragraphs_height(el.paragraphs, p.w, p.style, p.font_scale)
        got.append(
            (round((p.style.font_size or 18) * p.font_scale, 1), 1 if h < one * 1.5 else 2, round(body, 1))
        )
    return got


def _row(tmp_path, extra: str = "", src: str = ROW, name: str = "r.pptx"):
    out = tmp_path / name
    deck = build(ROW_HEAD + extra + src, out)
    return deck, out


def test_a_4up_heading_that_would_wrap_shrinks_to_one_line_with_its_siblings(tmp_path):
    got = _heading_lines(ROW)
    assert len(got) == 4
    assert len({g[0] for g in got}) == 1  # one size for the whole row
    assert {g[1] for g in got} == {1}  # no heading wraps
    assert got[0][0] >= got[0][2] * 0.97  # never below the body text of the cards
    _deck, out = _row(tmp_path)  # the .pptx reopens with the four headings
    heads = [s for s in Presentation(str(out)).slides[0].shapes if s.name.startswith("Heading ")]
    assert [h.text_frame.text for h in heads] == ["Thí điểm", "Mở rộng", "Chuẩn hóa", "Tối ưu"]


def test_heading_wrap_on_keeps_the_natural_sizes():
    off = _heading_lines(ROW)
    on = _heading_lines(ROW, "style: heading.wrap=on\n")
    assert max(g[0] for g in on) >= max(g[0] for g in off)
    assert 2 in {g[1] for g in on}  # (the 4-up row wrapped one heading before the fit)


def test_a_pinned_heading_size_keeps_the_row(tmp_path):
    got = _heading_lines(ROW.replace("heading=22", "heading=30!"))
    assert len({g[0] for g in got}) == 1 and got[0][0] >= 29  # the pinned size stays, wrapped or not
    span = ROW.replace("## Chuẩn hóa", "## [Chuẩn hóa]{size=24}")
    _deck, out = _row(tmp_path, src=span, name="span.pptx")
    assert out.exists()


def test_headings_that_cannot_fit_at_the_body_size_keep_one_size():
    src = ROW.replace("## Thí điểm", "## Một tiêu đề rất dài không thể nằm trên một dòng")
    got = _heading_lines(src)
    assert len({g[0] for g in got}) == 1  # one size for every heading of the row
    assert max(g[1] for g in got) == 2  # wrapped, the way the row keeps its natural size


def test_steps_card_headings_never_wrap_in_a_row():
    src = "# Lộ trình\n@4 steps\n## Thí điểm\n- a\n## Mở rộng\n- b\n## Chuẩn hóa số\n- c\n## Tối ưu\n- d\n"
    got = _heading_lines(src, "sizes: heading=26\n")
    assert len(got) == 4 and len({g[0] for g in got}) == 1 and {g[1] for g in got} == {1}
    assert got[0][0] >= got[0][2] * 0.97  # not below the card text
    on = _heading_lines(src, "sizes: heading=26\nstyle: heading.wrap=on\n")
    assert 2 in {g[1] for g in on}  # (it wrapped before)


def test_2x2_cards_share_one_heading_size_and_none_wraps():
    src = (
        "# Lộ trình\n@2x2\n## Thí điểm\n- a\n## Chuẩn hóa dữ liệu nguồn nhiều nơi\n- b\n"
        "## Chuẩn hóa\n- c\n## Tối ưu\n- d\n"
    )
    got = _heading_lines(src)
    assert len(got) == 4 and len({g[0] for g in got}) == 1 and {g[1] for g in got} == {1}
    assert 2 in {g[1] for g in _heading_lines(src, "style: heading.wrap=on\n")}


def test_3up_cards_heading_shrinks_not_wraps():
    src = "# L\n@3\n## Thí điểm\n- a\n## Chuẩn hóa quy trình\n- b\n## Chuẩn hóa\n- c\n"
    got = _heading_lines(src)
    assert {g[1] for g in got} == {1} and len({g[0] for g in got}) == 1
    assert 2 in {g[1] for g in _heading_lines(src, "style: heading.wrap=on\n")}


def test_heading_wrap_token_is_checked():
    deck = parse(ROW_HEAD + "style: heading.wrap=maybe\n" + ROW)
    assert [d.rule for d in deck.diagnostics if d.rule == "bad-token"]


@pytest.mark.parametrize(
    "src",
    [
        "# T\n@2\n## \n- a\n## b\n- c\n",
        "# T\n@4 num\n## a {size=0}\n## b\n## c\n## d\n",
        "# T\n@3\n## 長い見出しのテスト項目です\n- a\n## b\n- b\n## c\n- c\n",
        "# T\n@2x2\n## a\n## b\n## c\n## d\n",
    ],
)
def test_headings_fit_is_fuzz_safe(tmp_path, src):
    deck = build(ROW_HEAD + "sizes: body=16\n\n" + src, tmp_path / "f.pptx")
    assert deck is not None


# --------------------------------------------------------------------------- 3. proscons palette

PROS = "# P\n@proscons\n## Ưu\n- a\n- b\n## Nhược\n- c\n- d\n> Kết luận\n"


def _fills(path) -> dict[str, str]:
    out = {}
    for s in Presentation(str(path)).slides[0].shapes:
        if s.name in (
            "Proscons 1 head",
            "Proscons 2 head",
            "Proscons 1 item 1 glyph",
            "Proscons 2 item 1 glyph",
        ):
            out[s.name] = str(s.fill.fore_color.rgb)
    return out


def test_proscons_default_colours_are_the_palette(tmp_path):
    _deck, out = _build(tmp_path, PROS, "p.pptx")
    f = _fills(out)
    assert f["Proscons 1 head"] == "1B8A8F" == f["Proscons 1 item 1 glyph"]  # secondary
    assert f["Proscons 2 head"] == "F2A33A" == f["Proscons 2 item 1 glyph"]  # accent


def test_proscons_success_and_danger_only_when_asked(tmp_path):
    from slidemark.theme import NEUTRAL_COLORS

    style = "style: proscons.plus.color=success proscons.minus.color=danger\n"
    _deck, out = _build(tmp_path, style + PROS, "pd.pptx")
    f = _fills(out)
    assert f["Proscons 1 head"] == NEUTRAL_COLORS["success"].lstrip("#").upper()
    assert f["Proscons 2 head"] == NEUTRAL_COLORS["danger"].lstrip("#").upper()


def test_proscons_header_ink_is_readable(tmp_path):
    deck, _out = _build(tmp_path, PROS, "pi.pptx")
    assert [d for d in deck.diagnostics if d.rule == "contrast"] == []
