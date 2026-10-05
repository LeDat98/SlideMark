"""Sparse slides that left half the body empty: flow row + callout, a lone HTML block, a lone table."""

from __future__ import annotations

from pathlib import Path

from slidemark.ir import Placed, Raw, Table
from slidemark.layout import layout_slide
from slidemark.parser import parse
from slidemark.template import deck_theme

ROOT = Path(__file__).resolve().parent.parent
BODY_BOTTOM = 6492240  # slide bottom minus the page margin (EMU)


def _slide(name: str, number: int) -> tuple[list[Placed], int]:
    md = ROOT / "examples" / f"{name}.md"
    deck = parse(md.read_text(encoding="utf-8"))
    theme, _ = deck_theme(deck, md.parent)
    items = layout_slide(deck.slides[number - 1], deck, theme, number - 1)
    body = [p for p in items if p.h > 0 and 889000 < p.y and p.y < 6500000]
    top = min(p.y for p in body)
    return items, round((BODY_BOTTOM - max(p.y + p.h for p in body)) / (BODY_BOTTOM - top) * 100)


def test_flow_row_with_callout_fills_the_body():  # 05-jp-process slide 2
    items, band = _slide("05-jp-process", 2)
    assert band <= 22
    callout = next(p for p in items if "callout" in getattr(p.element, "classes", []))
    cards = [p for p in items if type(p.element).__name__ == "Container"]
    assert all(c.y + c.h <= callout.y for c in cards)  # the callout still closes the slide


def test_lone_html_block_fit_is_opt_in():  # 12-html-svg-math slide 1
    items, _ = _slide("12-html-svg-math", 1)  # default: stretched cards had ~70% empty interiors
    raw = next(p for p in items if isinstance(p.element, Raw))
    assert "100vh" not in raw.element.source
    md = ROOT / "examples" / "12-html-svg-math.md"
    deck = parse("style: layout.html_fit=on\n" + md.read_text(encoding="utf-8"))
    theme, _ = deck_theme(deck, md.parent)
    raw = next(p for p in layout_slide(deck.slides[0], deck, theme, 0) if isinstance(p.element, Raw))
    assert "100vh" in raw.element.source and raw.h > 0.6 * 6858000


def test_lone_table_grows_into_the_body():  # 03-vi-report slide 3
    items, band = _slide("03-vi-report", 3)
    assert any(isinstance(p.element, Table) for p in items)
    assert band <= 25
