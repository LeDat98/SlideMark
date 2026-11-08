"""The built-in CSS kit of ```html fences (`render/htmlkit.py`): a few class names give the editorial look."""

from __future__ import annotations

import pytest

from slidemark.htmlnative import html_to_placed
from slidemark.ir import Shape, Text
from slidemark.parser import parse
from slidemark.render.htmlimg import HtmlRenderer, _page
from slidemark.theme import get_theme

PX = 9525
THEME = get_theme("editorial")
ACCENT = "#BF4520"


@pytest.fixture(scope="module")
def renderer():
    pytest.importorskip("playwright.sync_api")
    r = HtmlRenderer()
    if r.render("<p>x</p>", 40, 20, THEME) is None:
        r.close()
        pytest.skip("Chromium cannot be launched")
    yield r
    r.close()


def _place(renderer, html, w=800, h=300):
    res = html_to_placed(html, 0, 0, w * PX, h * PX, THEME, ".", renderer=renderer)
    assert res is not None
    return res[0]


def _shapes(items, kind=None):
    return [p for p in items if isinstance(p.element, Shape) and (kind is None or p.element.shape == kind)]


def _texts(items):
    return [p for p in items if isinstance(p.element, Text)]


def test_page_injects_kit_before_author_css_and_markers():
    page = _page('<style>.tag{color:red}</style><b class="tag">x</b>', THEME)
    assert page.index(".node{") < page.index(".tag{color:red}")  # the author's rules come later: they win
    assert 'id="arrow-primary"' in page and "--accent-rgb:191,69,32" in page


def test_lone_card_stays_structural():
    deck = parse('# T\n\n```html\n<div class="card"><h2>A</h2><p>x</p></div>\n```\n')
    assert not any(type(e).__name__ == "Raw" for e in deck.slides[0].elements)


def test_kit_class_makes_a_fence_designed():
    deck = parse('# T\n\n```html\n<div class="node focal"><b>X</b></div>\n```\n')
    assert any(
        type(e).__name__ == "Raw" for e in deck.slides[0].elements
    )  # kept as html, not read as a document


def test_tag_is_a_bordered_shape_with_uppercase_mono_text(renderer):
    items = _place(renderer, '<div class="node"><span class="tag">api</span><b>Gateway</b></div>')
    tag_box = [s for s in _shapes(items) if s.style.line and s.w < 100 * PX]
    assert tag_box, "the tag keeps its hairline border as a shape"
    tag = next(t for t in _texts(items) if t.element.paragraphs[0].plain.upper() == "API")
    assert tag.element.paragraphs[0].plain == "API"  # converted run text is uppercase
    assert tag.style.font == "Consolas"
    assert (tag.style.letter_spacing or 0) > 0  # tracked


def test_label_text_is_uppercase(renderer):
    items = _place(renderer, '<span class="label">write path</span>')
    assert [t.element.paragraphs[0].plain for t in _texts(items)] == ["WRITE PATH"]


def test_blocked_card_has_dashed_accent_line_and_bar(renderer):
    items = _place(
        renderer, '<div class="card blocked"><b>Postgres 16</b><div class="meta">AVA-118 · sam</div></div>'
    )
    rects = _shapes(items)
    main = rects[0]
    assert main.style.line_dash == "dash" and main.style.line == ACCENT
    bar = next(s for s in rects[1:] if s.style.fill == ACCENT)
    assert bar.w < 8 * PX and bar.h == main.h  # the left accent bar spans the card
    assert [t.element.paragraphs[0].plain for t in _texts(items)] == ["Postgres 16", "AVA-118 · sam"]


def test_node_roles_match_the_preset_roles(renderer):
    items = _place(
        renderer, '<div class="node focal"><b>A</b></div><div class="node optional"><b>B</b></div>'
    )
    focal, optional = _shapes(items)[:2]
    assert (
        focal.style.line == ACCENT
        and focal.style.fill == ACCENT
        and focal.style.opacity == pytest.approx(0.08, abs=0.01)
    )
    assert optional.style.line_dash == "dash"


def test_badge_over_is_accent(renderer):
    items = _place(renderer, '<span class="badge over">4/3</span>')
    assert _shapes(items)[0].style.line == ACCENT
    assert _texts(items)[0].style.color == ACCENT


def test_arrow_markers_without_defs_give_an_accent_head(renderer):
    svg = (
        '<svg width="400" height="100"><line x1="10" y1="20" x2="300" y2="20" class="arrow primary"/>'
        '<line x1="10" y1="60" x2="300" y2="60" stroke="#123456" stroke-width="2" '
        'marker-end="url(#arrow-primary)"/>'
        '<line x1="10" y1="90" x2="300" y2="90" class="arrow return"/></svg>'
    )
    lines = _shapes(_place(renderer, svg), "line")
    assert [ln.element.attrs["head"] for ln in lines] == ["arrow", "arrow", "arrow"]
    assert lines[0].style.line == ACCENT
    assert lines[2].style.line_dash == "dash"  # `.arrow.return`


def test_svg_text_uppercase_and_tracked(renderer):
    svg = '<svg width="300" height="60"><text class="cat" x="150" y="30">people</text></svg>'
    t = _texts(_place(renderer, svg))[0]
    assert t.element.paragraphs[0].plain == "PEOPLE"
    assert (t.style.letter_spacing or 0) > 0


def test_cjk_text_in_mono_slots_switches_register(renderer):
    items = _place(
        renderer, '<div lang="ja"><span class="tag">要因</span> <span class="sub">原因の説明</span></div>'
    )
    texts = [t.element.paragraphs[0].plain for t in _texts(items)]
    assert "要因" in texts and "原因の説明" in texts  # no uppercase, no mono tracking
    assert all((t.style.letter_spacing or 0) == 0 for t in _texts(items))


def test_unknown_kit_combinations_never_crash(renderer):
    html = (
        '<div class="node focal store col board card blocked done wait badge over tag legend key">'
        '<i class="eyebrow label sub"></i></div>'
    )
    assert _place(renderer, html) is not None
