"""The conclusion bar is never smaller than the largest card body text of its slide."""

from __future__ import annotations

from pathlib import Path

from slidemark.ir import Text
from slidemark.layout import layout_slide
from slidemark.parser import parse
from slidemark.template import deck_theme

CARDS = "# T\n\n## A\n- one\n- two\n\n## B\n- three\n- four\n\n> {concl}\n"


def _sizes(src: str, slide: int = 0):
    deck = parse(src)
    theme, _ = deck_theme(deck, ".")
    pl = layout_slide(deck.slides[slide], deck, theme, slide)
    pt = lambda p: p.style.font_size * p.font_scale  # noqa: E731
    bar = next(p for p in pl if isinstance(p.element, Text) and p.element.role == "conclusion")
    body = [pt(p) for p in pl if isinstance(p.element, Text) and p.element.role == "body"]
    return pt(bar), max(body), bar, deck


def test_bar_at_least_card_body_example_11():
    src = (Path(__file__).parent.parent / "examples" / "11-jp-consulting.md").read_text()
    bar, body, _b, deck = _sizes(src, 8)
    assert bar >= body - 0.01
    assert not [d for d in deck.diagnostics if d.rule == "overflow"]


def test_explicit_size_untouched():
    bar, _body, _b, _d = _sizes(
        "```css\n.conclusion { font-size: 11pt }\n```\n\n" + CARDS.format(concl="Take away")
    )
    assert abs(bar - 11) < 0.01


def test_long_bar_text_stays_inside_and_never_raises():
    bar, _body, b, _d = _sizes(CARDS.format(concl="very long takeaway " * 12))
    assert bar > 0
    assert b.h <= 0.5 * 7.5 * 914400
