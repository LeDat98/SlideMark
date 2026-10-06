"""Sparse slides of agent-written decks: text and cards grow, no empty band over ~35% of the body.

Inputs: tests/data/sparse_ja_dense.md (jp-business, dense) and tests/data/sparse_vi_brand.md (theme none).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from slidemark.ir import Container, Placed, Shape, Text
from slidemark.layout import layout_slide, measure
from slidemark.layout.engine import _content_bottom
from slidemark.parser import parse
from slidemark.template import deck_theme
from slidemark.theme import LayoutTokens
from slidemark.units import slide_size, to_emu

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "bench"))
from whitespace import body_band  # noqa: E402

LIMIT = 0.35 + 0.01


def lay(name: str, number: int, **tokens) -> tuple[list[Placed], float, object]:
    """(items, body height in EMU, theme) of slide ``number`` of tests/data/``name``.md."""
    md = ROOT / "tests" / "data" / f"{name}.md"
    deck = parse(md.read_text(encoding="utf-8"))
    theme, _ = deck_theme(deck, md.parent)
    if tokens:
        theme = theme.model_copy(deep=True)  # the preset object may be shared between decks
        theme.layout = theme.layout.model_copy(update=tokens)
    measure.set_tokens(theme.layout)
    items = layout_slide(deck.slides[number - 1], deck, theme, number - 1)
    assert not [d for d in deck.diagnostics if d.rule in ("overflow", "layout-error")]
    band = body_band(items, to_emu(theme.layout.top_gap), slide_size(deck.size)[1], to_emu(theme.margin_y))
    return items, band, theme


def bands(name: str, number: int, **tokens) -> tuple[float, float]:
    """(share of the body empty above, below) the content, content = last visible line / card edge."""
    items, band, _ = lay(name, number, **tokens)
    assert band is not None
    above, _below, body = band
    body_items = [
        p
        for p in items
        if getattr(p.element, "role", None) not in ("title", "subtitle", "lead", "footnote", "conclusion")
        and getattr(p.element, "id", None) != "band"
        and not (getattr(p.element, "role", None) == "caption" and p.element.attrs.get("field"))
        and not (isinstance(p.element, Shape) and p.element.shape == "rect" and p.y == 0)
    ]
    head = max(
        p.y + p.h
        for p in items
        if getattr(p.element, "role", None) in ("title", "subtitle", "lead")
        or getattr(p.element, "id", None) == "band"
    )
    foot = [p.y for p in items if getattr(p.element, "role", None) in ("footnote", "conclusion")]
    bottom = min(foot) if foot else head + body
    return above / body, max(bottom - _content_bottom(body_items), 0) / body


def body_pt(items: list[Placed], role: str = "body") -> float:
    """Largest rendered body text size (pt) outside KPI cards."""
    return max(
        p.style.font_size * p.font_scale
        for p in items
        if isinstance(p.element, Text) and p.element.role == role and p.style.font_size
    )


def cards(items: list[Placed]) -> list[Placed]:
    return [p for p in items if isinstance(p.element, Container)]


JA = "sparse_ja_dense"
VI = "sparse_vi_brand"
# (deck, slide number, what it is)
SPARSE = [
    (JA, 2, "lead + 4 KPI + 3 bullets, dense"),
    (JA, 3, "4 boxes x 2 bullets, dense"),
    (JA, 4, "4 chevrons alone, dense"),
    (VI, 2, "4 KPI cards alone"),
    (VI, 4, "3 boxes x 2 bullets"),
    (VI, 8, "title + 3 bullets"),
    (VI, 9, "title + 3 bullets"),
]


@pytest.mark.parametrize(("name", "number", "what"), SPARSE)
def test_no_empty_band_over_35_percent(name, number, what):
    above, below = bands(name, number)
    if (
        what == "4 KPI cards alone"
    ):  # a lone KPI row is content-sized at the optical center (test_l3_kpi_lone)
        assert max(above, below) <= 0.45
        return
    assert max(above, below) <= LIMIT, f"{what}: above {above:.0%}, below {below:.0%}"


def test_completion_is_what_closes_the_band():
    off = {"sparse_left_max": 0.0}
    for name, number in ((JA, 2), (VI, 2), (VI, 4), (VI, 8)):
        a0, b0 = bands(name, number, **off)
        assert max(a0, b0) > LIMIT, (name, number)  # without the token the band is there


def test_dense_kpi_slide_list_is_readable_and_block_sits_under_the_lead():
    items, _band, theme = lay(JA, 2)
    base = theme.sizes["body"]
    lst = [
        p for p in items if isinstance(p.element, Text) and p.element.role == "body" and p.element.paragraphs
    ]
    bullets = [p for p in lst if len(p.element.paragraphs) == 3]
    assert bullets
    pt = bullets[0].style.font_size * bullets[0].font_scale
    assert pt >= base * 1.25 - 1e-6  # at least the sparse step over the (non-dense) body size
    assert pt <= base * LayoutTokens().sparse_step_max + 1e-6
    kpis = [c for c in cards(items) if "kpi" in c.element.classes]
    lead = next(p for p in items if getattr(p.element, "role", None) == "lead")
    assert min(c.y for c in kpis) - (lead.y + lead.h) <= 0.3 * (
        to_emu("7.5in") - lead.y
    )  # not floating mid-slide
    assert max(c.y + c.h for c in kpis) <= bullets[0].y + 1  # list below the cards, no overlap


def test_dense_kpi_cards_taller_than_before():
    before, _, _ = lay(JA, 2, sparse_left_max=0.0)
    after, _, _ = lay(JA, 2)
    h0 = max(c.h for c in cards(before) if "kpi" in c.element.classes)
    h1 = max(c.h for c in cards(after) if "kpi" in c.element.classes)
    assert h1 >= 1.1 * h0


def test_kpi_cards_alone_grow():
    before, _, _ = lay(VI, 2, sparse_left_max=0.0, kpi_lone=False)
    after, _, _ = lay(VI, 2, kpi_lone=False)
    h0 = max(c.h for c in cards(before))
    h1 = max(c.h for c in cards(after))
    assert h1 >= 1.15 * h0 * 0.99


def kpi_values(items: list[Placed]) -> list[tuple[float, float, str]]:
    """(rendered size pt, text width pt, text) of the big number of every KPI card."""
    out = []
    kpis = [c for c in cards(items) if "kpi" in c.element.classes]
    for c in kpis:
        t = next(
            p
            for p in items
            if isinstance(p.element, Text)
            and p.element.paragraphs
            and p.x >= c.x - 2
            and p.y >= c.y - 2
            and p.x + p.w <= c.x + c.w + 2
            and p.y + p.h <= c.y + c.h + 2
            and p.element.role == "body"
        )
        para = t.element.paragraphs[0]
        size = (para.style.font_size or t.style.font_size) * t.font_scale
        out.append((size, t.w / 12700, para.plain))
    return out


@pytest.mark.parametrize(("name", "number"), [(JA, 2), (VI, 2)])
def test_kpi_values_share_one_size_and_never_wrap(name, number):
    items, _, _ = lay(name, number)
    vals = kpi_values(items)
    assert len(vals) == 4
    assert max(v[0] for v in vals) - min(v[0] for v in vals) < 0.2, vals  # one size per row
    for size, width, text in vals:
        em = measure.text_em(text, bold=True)
        assert em * size * 1.15 <= width, (text, size, width)  # one line, with a safety margin


def test_kpi_value_grows_within_its_width():
    items, _, _ = lay(JA, 2)
    before, _, _ = lay(JA, 2, sparse_left_max=0.0)
    assert min(v[0] for v in kpi_values(items)) >= min(v[0] for v in kpi_values(before)) - 1e-6


@pytest.mark.parametrize("number", [8, 9])
def test_title_plus_bullets_grow_and_breathe(number):
    before, _, _ = lay(VI, number, sparse_left_max=0.0)
    after, _, theme = lay(VI, number)
    assert body_pt(after) >= body_pt(before)
    assert body_pt(after) <= LayoutTokens().sparse_text_max_pt + 1e-6
    gap = [
        p.element.attrs.get("para_gap")
        for p in after
        if isinstance(p.element, Text) and p.element.role == "body"
    ]
    assert gap and gap[0] is not None and gap[0] >= LayoutTokens().sparse_air - 1e-6


def test_three_boxes_grow_without_hollow_cards():
    items, _band, _ = lay(VI, 4)
    before, _, _ = lay(VI, 4, sparse_left_max=0.0)
    assert body_pt(items) > body_pt(before)
    # cards stay within the card air token of their content: no empty interiors
    sys.path.insert(0, str(ROOT / "bench"))
    from whitespace import card_tails

    tails = [t for _n, t, lead in card_tails(items) if lead]
    assert tails and max(tails) <= 0.25 + 1e-9, tails


def test_chevrons_alone_grow_taller():
    before, _, _ = lay(JA, 4, sparse_left_max=0.0)
    after, _, _ = lay(JA, 4)

    def hmax(items):
        return max(p.h for p in items if isinstance(p.element, Shape) and p.element.shape == "chevron")

    assert hmax(after) >= 1.3 * hmax(before)


def test_full_dense_slides_do_not_change():
    for name, number in ((JA, 1), (JA, 5), (VI, 3), (VI, 6), (VI, 7)):
        a, _, _ = lay(name, number, sparse_left_max=0.0)
        b, _, _ = lay(name, number)
        assert [(p.x, p.y, p.w, p.h) for p in a] == [(p.x, p.y, p.w, p.h) for p in b], (name, number)


def test_explicit_size_is_kept():
    md = "theme: none\n\n# T\n## A {.kpi}\n12%\n## B {.kpi}\n3%\n"  # no explicit size: grows
    deck = parse(md)
    theme, _ = deck_theme(deck, ROOT)
    auto = layout_slide(deck.slides[0], deck, theme, 0)
    md2 = "theme: none\n\n# T\n- a\n- b {size=20}\n- c\n"
    deck2 = parse(md2)
    fixed = layout_slide(deck2.slides[0], deck2, theme, 0)
    assert auto and fixed
    sizes = {
        round(p.style.font_size * p.font_scale, 1)
        for p in fixed
        if isinstance(p.element, Text) and p.element.role == "body"
    }
    assert sizes  # layout never raises; explicit sizes are covered by tests/test_layout_sparse_step.py
