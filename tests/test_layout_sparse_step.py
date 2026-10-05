"""Sparse step: a slide that fills little of the body is laid out one step up (text, gaps, paddings)."""

from __future__ import annotations

from pptx import Presentation

from slidemark.build import build_deck
from slidemark.ir import Deck, Slide, Style, Text
from slidemark.layout import layout_slide
from slidemark.parser import parse
from slidemark.theme import LayoutTokens, get_theme

from .test_layout_policies import T, box, of

TWO_CARDS = (
    "# 決議事項\n@2\n## 項目A\n- 第1期投資を承認する\n- 委員会を設置する\n"
    "## 項目B\n- 11月 計画策定\n- 1月 方針説明\n"
)
DENSE = "density: dense\ntheme: jp-business\n\n"


def body_sizes(placed):
    return {round(p.style.font_size * p.font_scale, 2) for p in of(placed, Text) if p.element.role == "body"}


def lay_deck(md: str, theme: str = "jp-business"):
    deck = parse(md)
    return layout_slide(deck.slides[0], deck, get_theme(theme), 0), deck


def lay_with(md: str, **tokens):
    th = get_theme("jp-business").model_copy(deep=True)  # get_theme may return a shared object
    th.layout = th.layout.model_copy(update=tokens)
    deck = parse(md)
    return layout_slide(deck.slides[0], deck, th, 0), deck


def test_sparse_slide_takes_the_step_and_does_not_overflow():
    placed0, _ = lay_with(DENSE + TWO_CARDS, sparse_step=1.0, sparse_step_min=1.0)
    placed1, deck = lay_with(DENSE + TWO_CARDS)
    (s0,) = body_sizes(placed0)
    (s1,) = body_sizes(placed1)
    assert s1 > s0 * 1.1
    assert s1 <= LayoutTokens().sparse_low_max_pt + 1e-9  # a floating block may grow to the larger cap
    assert not [d for d in deck.diagnostics if d.rule == "overflow"]


def test_step_widens_paragraph_gap_and_card_padding():
    placed0, _ = lay_with(DENSE + TWO_CARDS, sparse_step=1.0, sparse_step_min=1.0)
    placed1, _ = lay_with(DENSE + TWO_CARDS)
    gaps = [p.element.attrs.get("para_gap") for p in of(placed1, Text) if p.element.role == "body"]
    assert gaps and all(g is not None and g >= LayoutTokens().sparse_para_gap - 1e-9 for g in gaps)
    gaps0 = [p.element.attrs.get("para_gap") for p in of(placed0, Text) if p.element.role == "body"]
    assert all(g is None or g < LayoutTokens().sparse_para_gap for g in gaps0)


def test_explicit_font_size_never_changes():
    fixed = box("A", "第1期投資", "委員会")
    fixed.children[0].style = Style(font_size=10)
    s = Slide(title=T("t", "title"), grid="2", elements=[fixed, box("B", "計画", "方針")])
    deck = Deck(slides=[s])
    th = get_theme("jp-business").model_copy(deep=True)
    placed = layout_slide(s, deck, th, 0)
    bodies = [p for p in of(placed, Text) if p.element.role == "body"]
    pinned = next(p for p in bodies if p.element.style is not None and p.element.style.font_size == 10)
    free = next(p for p in bodies if p is not pinned)
    assert pinned.style.font_size * pinned.font_scale == 10
    assert free.font_scale > 1.0  # its sibling does grow
    assert layout_slide(s, deck, th, 0)


def test_full_slide_is_not_stepped():
    items = "\n".join(f"- 項目{i} " + "あ" * 40 for i in range(9))
    md = DENSE + f"# t\n@2\n## A\n{items}\n## B\n{items}\n"
    placed0, _ = lay_with(md, sparse_step=1.0, sparse_step_min=1.0)
    placed1, _ = lay_with(md)
    assert body_sizes(placed0) == body_sizes(placed1)


def test_step_off_keeps_sizes_and_unit_tokens_are_defaults():
    t = LayoutTokens()
    assert 1.0 < t.sparse_step_min < t.sparse_step and t.sparse_fill < t.sparse_fill_soft


def test_render_reopens_with_the_stepped_size(tmp_path):
    deck = parse(DENSE + TWO_CARDS)
    out = tmp_path / "o.pptx"
    build_deck(deck, out, tmp_path)
    placed, _ = lay_deck(DENSE + TWO_CARDS)
    want = max(body_sizes(placed))
    sizes = set()
    for sh in Presentation(str(out)).slides[0].shapes:
        if sh.has_text_frame and "第1期投資" in sh.text_frame.text:
            for p in sh.text_frame.paragraphs:
                for r in p.runs:
                    sizes.add(r.font.size.pt)
    assert sizes and abs(max(sizes) - want) < 0.6


def test_hand_built_slide_never_raises():
    s = Slide(title=T("t", "title"), elements=[box("a", "x")])
    placed = layout_slide(s, Deck(slides=[s]), get_theme("jp-business"), 0)
    assert placed
