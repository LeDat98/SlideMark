"""A ruled panel beside a chart: capped gaps, the callout follows the last item, the air goes below it."""

from __future__ import annotations

from slidemark.ir import Container, Text
from slidemark.layout import engine
from tests.test_layout_l3_fill import lay


def _parts(**tokens):
    placed, deck, theme = lay("11-jp-consulting.md", 3, **tokens)
    panel = next(p for p in placed if isinstance(p.element, Container))
    texts = [p for p in placed if isinstance(p.element, Text) and panel.y <= p.y < panel.y + panel.h]
    body = next(p for p in texts if p.element.role == "body" and len(p.element.paragraphs) > 1)
    note = next(p for p in texts if "callout" in p.element.classes)
    return panel, body, note, theme, deck


def test_callout_follows_the_last_item_and_air_goes_below():
    panel, body, note, theme, _ = _parts()
    gap = note.y - (body.y + engine._text_h(body))
    size = (body.style.font_size or 18) * body.font_scale * 12700
    assert 0 <= gap <= 3.5 * size  # right after the list: no loose band
    below = panel.y + panel.h - (note.y + note.h)
    assert below > gap  # the leftover air is under the callout
    assert panel.h > 0.9 * 4872253 * 0.9  # the panel still spans the chart


def test_spread_gaps_are_capped_like_cards():
    _, body, _, theme, _ = _parts()
    em = (body.style.font_size or 18) * body.font_scale
    gap_em = body.element.attrs["para_gap"]
    assert gap_em <= theme.layout.card_spread_gap_max + 1e-6
    assert em > 0


def test_note_stays_inside_the_panel_and_clear_of_the_list():
    panel, body, note, _, deck = _parts()
    assert note.y + note.h <= panel.y + panel.h
    assert body.y + body.h <= note.y + 2
    assert not [d for d in deck.diagnostics if d.level == "error"]
