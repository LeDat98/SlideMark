"""Wave 4: deliberate covers (title grows, block centred on a token line); cards keep a gutter to the bar."""

from __future__ import annotations

from pathlib import Path

from slidemark.ir import Text
from slidemark.layout import layout_slide
from slidemark.parser import parse
from slidemark.template import resolve_theme
from tests.test_layout_l3_fill import lay

H = 720 * 9525
EX = Path(__file__).resolve().parent.parent / "examples"
SRC = "theme: {theme}\n\n# {title}\n\n{sub}\n"


def _cover(theme: str, title: str = "Logistics DX Plan", sub: str = "FY2027 board paper", **tokens):
    src = f"theme: {theme}\n\n# {title}\n\n## {sub}\n" if theme else f"# {title}\n\n## {sub}\n"
    placed, deck, th = lay("x", 1, src=src, **tokens)
    t = next(p for p in placed if isinstance(p.element, Text) and p.element.role == "title")
    s = [p for p in placed if isinstance(p.element, Text) and p.element.role == "subtitle"]
    return t, (s[0] if s else None), th


def _legacy(title: str = "Logistics DX Plan", **tokens):
    """The centred cover (``cover.band_h=0``)."""
    src = f"theme: jp-business\n\n# {title}\n\n## FY2027 board paper\n"
    deck = parse(src)
    theme, _ = resolve_theme(deck.theme, EX)
    theme = theme.model_copy(update={"cover_band_h": 0, "layout": theme.layout.model_copy(update=tokens)})
    placed = layout_slide(deck.slides[0], deck, theme, 0)
    t = next(p for p in placed if isinstance(p.element, Text) and p.element.role == "title")
    s = next(p for p in placed if isinstance(p.element, Text) and p.element.role == "subtitle")
    return t, s, theme


def test_cover_title_grows_and_block_is_centred_on_the_token_line():
    t, s, th = _legacy()
    t0, _, _ = _legacy(cover_title_y=0.0)
    assert t.font_scale * t.style.font_size > t0.font_scale * t0.style.font_size
    assert t.font_scale * t.style.font_size <= th.layout.cover_title_max_pt + 0.01
    top, bottom = t.y, s.y + s.h
    assert abs((top + bottom) / 2 - th.layout.cover_title_y * H) <= 0.02 * H


def test_cover_without_band_is_centred_not_top_packed():
    t, s, th = _cover("none")
    assert t.y > 0.2 * H


def test_cover_never_wraps_more_after_growth():
    long = "A very long cover title that needs two lines at least"
    t, _, _ = _cover("jp-business", title=long)
    t0, _, _ = _cover("jp-business", title=long, cover_title_y=0.0)
    from slidemark.layout import engine

    assert engine._text_h(t) <= engine._text_h(t0) * (t.font_scale / t0.font_scale) * 1.05


def test_explicit_size_cover_is_unchanged():
    src = "theme: jp-business\n\n# Plan {size=30}\n\n## Sub\n"
    a, _, _ = lay("x", 1, src=src)
    b, _, _ = lay("x", 1, src=src, cover_title_y=0.0)
    assert [(p.x, p.y, p.w, p.h) for p in a] == [(p.x, p.y, p.w, p.h) for p in b]
