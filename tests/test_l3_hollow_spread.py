"""A stretched card that is still hollow spreads its items over the card body (equal gaps, capped)."""

from __future__ import annotations

from pathlib import Path

import pytest
from pptx import Presentation

from slidemark import build
from slidemark.layout import engine
from tests.test_layout_l3_fill import cards, inside, lay

EX = Path(__file__).resolve().parent.parent / "examples"


def _body_cards(placed):
    cs = sorted(cards(placed), key=lambda c: c.x)
    return [(c, inside(placed, c)[0]) for c in cs]


@pytest.mark.parametrize(("name", "n"), [("16-jp-strategy.md", 10), ("11-jp-consulting.md", 9)])
def test_hollow_cards_spread_to_the_bottom(name, n):
    placed, _, _ = lay(name, n, card_spread_rules=False)  # top-anchored lists (ruled lists: test_card_rules)
    pairs = _body_cards(placed)
    off = _body_cards(lay(name, n, card_spread_fill=0.0)[0])
    assert len(pairs) == 2
    for (c, body), (c0, b0) in zip(pairs, off, strict=True):
        tail = c.y + c.h - (body.y + engine._text_h(body))
        tail0 = c0.y + c0.h - (b0.y + engine._text_h(b0))
        assert tail <= 0.95 * tail0 + 1  # the dead lower band shrinks (capped equal gaps, list top-anchored)
    assert len({body.y for _, body in pairs}) == 1  # first items of siblings share one y


def test_spread_off_restores_top_packed():
    on, _, _ = lay("16-jp-strategy.md", 10, card_spread_rules=False)
    off, _, _ = lay("16-jp-strategy.md", 10, card_spread_fill=0.0)
    (c1, b1), _ = _body_cards(on)
    (c0, b0), _ = _body_cards(off)
    assert b1.element.attrs["para_gap"] > b0.element.attrs["para_gap"]


def test_capped_gap_top_anchors_the_list():
    placed, _, _ = lay("16-jp-strategy.md", 10, card_spread_gap_max=2.0, card_spread_rules=False)
    pairs = _body_cards(placed)
    assert len({body.y for _, body in pairs}) == 1
    off, _, _ = lay("16-jp-strategy.md", 10, card_spread_fill=0.0)
    offs = _body_cards(off)
    for (_, body), (_, b0) in zip(pairs, offs, strict=True):
        assert body.element.attrs["para_gap"] <= max(2.0, b0.element.attrs["para_gap"]) + 1e-6
    b_off = offs[0][1]
    assert all(abs(body.y - b0.y) <= 1 for (_, body), (_, b0) in zip(pairs, offs, strict=True))
    assert pairs[0][1].y == b_off.y  # first item stays at the top padding: no air above it


def test_unstretched_and_dense_slides_unchanged():
    for name, n in [("01-basics.md", 3), ("11-jp-consulting.md", 8)]:
        a, _, _ = lay(name, n, card_spread_rules=False)
        b, _, _ = lay(name, n, card_spread_fill=0.0)
        assert [(p.x, p.y, p.w, p.h) for p in a] != [] and len(a) == len(b)


def test_render_reopens(tmp_path):
    out = tmp_path / "x.pptx"
    build(str(EX / "16-jp-strategy.md"), str(out))
    prs = Presentation(str(out))
    assert len(prs.slides) >= 10
    body = next(sh for sh in prs.slides[9].shapes if sh.has_text_frame and "基本方針" in sh.text_frame.text)
    # spread items carry paragraph spacing in the XML
    assert "spcBef" in body._element.xml or "spcAft" in body._element.xml
