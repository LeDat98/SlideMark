"""Sparse rows of short boxes: one row, text and cards grow together, a small empty band."""

from __future__ import annotations

from pathlib import Path

from slidemark.ir import Container, Placed
from slidemark.layout import layout_slide
from slidemark.parser import parse
from slidemark.template import deck_theme

ROOT = Path(__file__).resolve().parent.parent


def _slide(name: str, number: int) -> tuple[list[Placed], int]:
    md = ROOT / "examples" / f"{name}.md"
    deck = parse(md.read_text(encoding="utf-8"))
    theme, _ = deck_theme(deck, md.parent)
    items = layout_slide(deck.slides[number - 1], deck, theme, number - 1)
    return items, 6492240  # slide bottom minus the page margin (EMU)


def _cards(items: list[Placed]) -> list[Placed]:
    return [p for p in items if isinstance(p.element, Container)]


def _band(items: list[Placed], height: int) -> float:
    """Empty height between the cards and the next element below them (or the slide bottom), per body."""
    cards = _cards(items)
    top, bottom = min(c.y for c in cards), max(c.y + c.h for c in cards)
    below = [p.y for p in items if p.y >= bottom and not isinstance(p.element, Container)]
    limit = min(below) if below else height
    return (limit - bottom) / max(limit - top, 1)


def test_three_short_boxes_stay_one_row_and_fill_the_body():  # 13-brand-aurora slide 2
    items, h = _slide("13-brand-aurora", 2)
    cards = _cards(items)
    assert len(cards) == 3 and len({c.y for c in cards}) == 1  # not stacked into wide bars
    assert max(c.w for c in cards) < 0.4 * 12192000
    assert _band(items, h) <= 0.2


def test_row_above_a_conclusion_bar_loses_most_of_the_band():  # 01-basics slide 3
    items, h = _slide("01-basics", 3)
    cards = _cards(items)
    assert len(cards) == 3 and len({c.y for c in cards}) == 1
    assert _band(items, h) <= 0.22  # was ~45%


def test_html_mixed_card_row_has_no_big_band():  # 15-html-mixed slide 2
    items, h = _slide("15-html-mixed", 2)
    cards = _cards(items)
    assert len(cards) == 3 and len({c.y for c in cards}) == 1
    assert _band(items, h) <= 0.2


def test_dense_two_box_slide_loses_most_of_its_band():  # 11-jp-consulting slide 9
    items, h = _slide("11-jp-consulting", 9)
    cards = _cards(items)
    assert len(cards) == 2 and len({c.y for c in cards}) == 1
    assert _band(items, h) <= 0.15  # was ~35% of the body


def test_text_grows_before_cards_stretch():  # 13-brand-aurora slide 2: cards were ~3x their text
    import sys

    sys.path.insert(0, str(ROOT / "bench"))
    from whitespace import card_fills

    items, h = _slide("13-brand-aurora", 2)
    fills = [f for _t, f in card_fills(items)]
    assert fills and max(fills) >= 0.5 and sum(fills) / len(fills) >= 0.38
    assert _band(items, h) <= 0.22
    body = [p for p in items if getattr(p.element, "role", None) == "body"]
    assert min(p.font_scale for p in body) >= 1.4  # text grew first
