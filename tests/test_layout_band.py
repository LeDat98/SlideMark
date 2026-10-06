"""Band balance: a block of cards / columns that leaves a band under it sits at the optical center."""

from __future__ import annotations

from pathlib import Path

from slidemark.ir import Container, Placed, Text
from slidemark.layout import layout_slide
from slidemark.parser import parse
from slidemark.template import deck_theme

ROOT = Path(__file__).resolve().parent.parent
SLIDE_H = 6858000


def _slide(name: str, number: int, tokens: str = "") -> list[Placed]:
    md = ROOT / "examples" / f"{name}.md"
    text = md.read_text(encoding="utf-8")
    if tokens:
        text = f"style: {tokens}\n" + text
    deck = parse(text)
    theme, _ = deck_theme(deck, md.parent)
    return layout_slide(deck.slides[number - 1], deck, theme, number - 1)


def _cards(items: list[Placed]) -> list[Placed]:
    return [p for p in items if isinstance(p.element, Container)]


def _above_below(items: list[Placed]) -> tuple[int, int]:
    """(top of the cards, bottom of the cards) in EMU."""
    cards = _cards(items)
    return min(c.y for c in cards), max(c.y + c.h for c in cards)


def _lead_bottom(items: list[Placed]) -> int:
    return max(p.y + p.h for p in items if isinstance(p.element, Text) and p.element.role == "lead")


def test_cards_move_off_the_lead_when_a_band_stays():  # 13-brand-aurora slide 2
    on = _slide("13-brand-aurora", 2)
    off = _slide("13-brand-aurora", 2, "layout.band_shift=0")
    top_on, bottom_on = _above_below(on)
    top_off, bottom_off = _above_below(off)
    assert top_on > top_off  # moved down ...
    assert top_on - top_off <= 0.15 * SLIDE_H  # ... by at most band_shift_max of the body
    assert top_on - _lead_bottom(on) < SLIDE_H - bottom_on  # optical center: more air below than above
    assert bottom_on < SLIDE_H * 0.92


def test_text_sizes_and_card_geometry_are_unchanged_by_the_shift():
    on = _slide("13-brand-aurora", 2)
    off = _slide("13-brand-aurora", 2, "layout.band_shift=0")
    assert [(p.h, p.w, p.font_scale) for p in on] == [(p.h, p.w, p.font_scale) for p in off]


def test_ruled_columns_with_css_sizes_keep_their_sizes():  # 17-editorial-css slide 2
    on = _slide("17-editorial-css", 2)
    off = _slide("17-editorial-css", 2, "layout.band_shift=0")
    heads = [p for p in on if isinstance(p.element, Text) and p.element.role == "heading"]
    assert heads and all(round((p.style.font_size or 0) * p.font_scale, 1) == 12.0 for p in heads)  # CSS 12pt
    heads_off = [p for p in off if isinstance(p.element, Text) and p.element.role == "heading"]
    assert min(p.y for p in heads) > min(p.y for p in heads_off)
    assert [round((p.style.font_size or 0) * p.font_scale, 1) for p in heads_off] == [12.0] * 3


def test_conclusion_bar_slides_do_not_float():  # 01-basics slide 3
    on = _slide("01-basics", 3)
    off = _slide("01-basics", 3, "layout.band_shift=0")
    assert [p.y for p in on] == [p.y for p in off]


def test_diagram_and_consulting_slides_are_untouched():
    for name, number in (("09-midnight-tech", 3), ("02-jp-dense", 1)):
        path = ROOT / "examples" / f"{name}.md"
        if not path.exists():
            continue
        on = _slide(name, number)
        off = _slide(name, number, "layout.band_shift=0")
        assert [p.y for p in on] == [p.y for p in off]


def test_lone_kpi_row_stays_at_its_optical_center():  # 17-editorial-css slide 3
    on = _slide("17-editorial-css", 3)
    off = _slide("17-editorial-css", 3, "layout.band_shift=0")
    assert [p.y for p in on] == [p.y for p in off]  # fit_lone_kpi already centered it
    top, bottom = _above_below(on)
    assert 0.3 * SLIDE_H < top and bottom < 0.75 * SLIDE_H


def test_band_balance_never_raises_on_empty_input():
    from slidemark.layout.grid import Rect
    from slidemark.layout.l3fill import center_band
    from slidemark.theme import LayoutTokens

    assert center_band([], Rect(0, 0, 100, 100), LayoutTokens()) == []
