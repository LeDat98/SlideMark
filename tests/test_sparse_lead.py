"""Sparse slides: the lead line and footnotes follow the grown body text, never past the title."""

from __future__ import annotations

from slidemark.ir import Container, Text
from slidemark.theme import LayoutTokens
from tests.test_sparse_slides import bands, lay

JA = "sparse_ja_short"


def _pt(items, role):
    return max(p.style.font_size * p.font_scale for p in items if getattr(p.element, "role", None) == role)


def test_sparse_slide_lead_and_boxes_are_readable():
    items, _band, theme = lay(JA, 2)
    assert _pt(items, "lead") >= 14
    box_body = [
        p.style.font_size * p.font_scale
        for p in items
        if isinstance(p.element, Text) and p.element.role == "body" and p.element.paragraphs
    ]
    assert box_body
    assert min(box_body) >= 14
    assert any(isinstance(p.element, Container) for p in items)
    above, below = bands(JA, 2)
    assert (
        max(above, below) <= 0.6
    )  # text is at its cap (layout.grow_max): the card shrinks, the band stays below


def test_lead_stays_secondary_to_the_title():
    lt = LayoutTokens()
    for number in (2, 3):
        items, _b, theme = lay(JA, number)
        cap = max(
            _pt(items, "title") * lt.sparse_lead_title_max, theme.sizes["lead"]
        )  # growth stops at the cap
        assert _pt(items, "lead") <= cap + 1e-6 < _pt(items, "title")


def test_footnote_grows_a_little():
    lt = LayoutTokens()
    off, _b, _t = lay(JA, 2, sparse_lead_grow=1.0, sparse_footnote_grow=1.0)
    on, _b, _t = lay(JA, 2)
    assert _pt(on, "footnote") > _pt(off, "footnote")
    assert _pt(on, "footnote") <= _pt(off, "footnote") * lt.sparse_footnote_grow + 1e-6


def test_tokens_switch_it_off():
    off, _b, theme = lay(JA, 2, sparse_lead_grow=1.0, sparse_footnote_grow=1.0)
    assert _pt(off, "lead") <= theme.sizes["lead"] + 0.01
