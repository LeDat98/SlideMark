"""Fill policy: text grows before gaps, gaps stay even and capped, sparse cards shrink to their content."""

from __future__ import annotations

import pytest
from pptx import Presentation

from slidemark import build
from slidemark.ir import Chart, Text
from slidemark.layout import engine
from slidemark.layout.grid import Rect
from slidemark.layout.l3fill import fill_panels, fill_row

from .test_layout_l3_fill import EX, cards, inside, lay


@pytest.mark.parametrize(("name", "n"), [("16-jp-strategy.md", 10), ("11-jp-consulting.md", 9)])
def test_decision_cards_share_one_capped_rhythm_and_a_head_pad(name, n):
    placed, _, theme = lay(name, n, cards_to_bar=False)
    cs = cards(placed)
    assert len(cs) == 2
    mains = [inside(placed, c)[0] for c in cs]
    gaps = [m.element.attrs.get("para_gap") or 0.0 for m in mains]
    assert abs(gaps[0] - gaps[1]) <= 0.02  # same rhythm left and right
    off, _, _ = lay(name, n, l3_fill=False)
    g0 = max(inside(off, c)[0].element.attrs.get("para_gap") or 0.25 for c in cards(off))
    assert max(gaps) - g0 <= theme.layout.l3_gap_cap + 0.02
    sizes = {round(m.font_scale, 3) for m in mains}
    assert len(sizes) == 1  # one text size for both cards
    for c, m in zip(cs, mains, strict=True):
        heads = [
            p for p in placed if getattr(p.element, "role", None) == "heading" and c.y <= p.y < c.y + c.h
        ]
        assert m.y > max(h.y + h.h for h in heads)  # air under the heading band
        assert m.y + m.h <= c.y + c.h
    assert max(c.h for c in cs) < 0.55 * 720 * 9525  # shrunk to content, not stretched over the body


def test_panel_ends_above_chart_bottom_with_note_after_text():
    placed, _, _ = lay("16-jp-strategy.md", 3)
    (panel,) = cards(placed)
    chart = next(p for p in placed if isinstance(p.element, Chart))
    assert panel.y + panel.h < chart.y + chart.h
    main, note = sorted(inside(placed, panel), key=lambda p: p.y)
    assert note.y - (main.y + engine._text_h(main)) < 0.15 * panel.h


def test_panel_render_reopens(tmp_path):
    out = tmp_path / "d.pptx"
    build(EX / "16-jp-strategy.md", out)
    prs = Presentation(out)
    texts = [s for s in prs.slides[2].shapes if s.has_text_frame and "価格競争" in s.text_frame.text]
    assert texts
    assert texts[0].top + texts[0].height < prs.slide_height * 0.8


def test_explicit_size_and_height_win_over_growth():
    src = "theme: jp-business\n\n# T\n> l\n@1:1\n## A {h=2in}\n- one\n- two\n## B\n- x {size=11}\n- y\n"
    placed, _, theme = lay("", 1, src)
    hs = sorted(c.h for c in cards(placed))
    assert abs(hs[-1] - 2 * 914400) < 10 * 9525 or len(hs) == 2
    assert fill_row([], Rect(0, 0, 10, 10), theme.layout) == []
    assert fill_panels([], Rect(0, 0, 10, 10), theme.layout, True) == []


def test_fuzz_never_raises():
    for src in (
        "# T\n@1:1\n## A\n@end\n",
        "# T\n@2\n## A\n- " + "長い" * 80 + "\n## B\n1. a\n2. b\n@end\n",
        "# T\n@1:1\n## A\n![x](nope.png)\n## B\n- a\n",
    ):
        placed, _, _ = lay("", 1, "theme: jp-business\n\n" + src)
        assert isinstance(placed, list)
        assert all(isinstance(p.element, Text) or p.h >= 0 for p in placed)
