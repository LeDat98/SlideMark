"""Layout linter rules: each fires on a crafted slide and stays quiet on the examples."""

from __future__ import annotations

from pathlib import Path

from slidemark.ir import Deck, Image, Paragraph, Placed, Run, Slide, Style, Text
from slidemark.layout import layout_slide
from slidemark.lint import contrast_ratio, lint, lint_slide
from slidemark.parser import parse
from slidemark.template import deck_theme
from slidemark.theme import get_theme

TH = get_theme("default")
EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def _text(s: str, **kw) -> Text:
    return Text(paragraphs=[Paragraph(runs=[Run(text=s)])], **kw)


def _rules(items: list[Placed], deck: Deck | None = None) -> list[str]:
    deck = deck or Deck(slides=[Slide()])
    return [d.rule for d in lint_slide(items, deck, TH, 0)]


def test_contrast_ratio_extremes():
    assert round(contrast_ratio((0, 0, 0), (1, 1, 1))) == 21
    assert contrast_ratio((1, 1, 1), (1, 1, 1)) == 1


def test_low_contrast():
    p = Placed(
        element=_text("hello"), x=0, y=0, w=3_000_000, h=800_000, style=Style(color="#FFFFFF", font_size=18)
    )
    assert "contrast" in _rules([p])
    ok = p.model_copy(update={"style": Style(color="#000000", font_size=18)})
    assert "contrast" not in _rules([ok])


def test_contrast_uses_fill_behind():
    card = Placed(element=_text(" "), x=0, y=0, w=4_000_000, h=2_000_000, style=Style(fill="#0F172A"))
    txt = Placed(
        element=_text("on dark"), x=100_000, y=100_000, w=3_000_000, h=800_000, style=Style(color="#FFFFFF")
    )
    assert "contrast" not in _rules([card, txt])


def test_off_slide_and_alt():
    img = Image(src="a.png", alt="")
    p = Placed(element=img, x=11_000_000, y=0, w=3_000_000, h=1_000_000)
    rules = _rules([p])
    assert "off-slide" in rules and "alt" in rules


def test_overlap_but_not_nesting():
    a = Placed(element=_text("A"), x=0, y=0, w=2_000_000, h=1_000_000, style=Style(color="#000000"))
    b = Placed(element=_text("B"), x=1_000_000, y=0, w=2_000_000, h=1_000_000, style=Style(color="#000000"))
    inner = Placed(
        element=_text("C"), x=100_000, y=100_000, w=500_000, h=300_000, style=Style(color="#000000")
    )
    assert "overlap" in _rules([a, b])
    assert "overlap" not in _rules([a, inner])


def test_overflow_uses_the_paragraph_gap_of_a_spread_box():
    from slidemark.layout import measure

    paras = [Paragraph(runs=[Run(text=f"line {i}")]) for i in range(8)]
    st = Style(font_size=18, color="#000000")
    plain = measure.paragraphs_height(paras, 3_000_000, st, 1.0)
    p = Placed(element=Text(paragraphs=paras), x=0, y=0, w=3_000_000, h=round(plain * 1.02), style=st)
    assert "overflow" not in _rules([p])
    spread = p.model_copy(update={"element": Text(paragraphs=paras, attrs={"para_gap": 0.6})})
    assert "overflow" in _rules([spread])


def test_overflow_and_tiny_text():
    long = _text("word " * 400)
    p = Placed(element=long, x=0, y=0, w=2_000_000, h=300_000, style=Style(font_size=18, color="#000000"))
    assert "overflow" in _rules([p])
    tiny = Placed(
        element=_text("x"),
        x=0,
        y=0,
        w=2_000_000,
        h=600_000,
        style=Style(font_size=12, color="#000000"),
        font_scale=0.4,
    )
    assert "tiny-text" in _rules([tiny])


def test_explicit_boxes_collide_end_to_end():
    deck = parse("# T\n## A {x=10% y=20% w=50% h=40%}\n- one\n## B {x=30% y=30% w=50% h=40%}\n- two\n")
    th = TH
    placed = [layout_slide(s, deck, th, i) for i, s in enumerate(deck.slides)]
    assert "overlap" in [d.rule for d in lint(deck, placed, th)]


def test_examples_are_clean():
    for md in sorted(EXAMPLES.glob("*.md")):
        deck = parse(md.read_text(encoding="utf-8"))
        th, _ = deck_theme(deck, md.parent)
        placed = [layout_slide(s, deck, th, i) for i, s in enumerate(deck.slides)]
        bad = [
            str(d) for d in lint(deck, placed, th) if d.rule in ("off-slide", "overlap", "contrast", "alt")
        ]
        assert not bad, f"{md.name}: {bad}"


def test_connector_through_a_block():
    deck = parse("# T\n@3 a>c\n## A\n- a\n## B\n- b\n## C\n- c\n")
    th = TH
    placed = [layout_slide(s, deck, th, i) for i, s in enumerate(deck.slides)]
    assert "connector-crosses" in [d.rule for d in lint(deck, placed, th)]
    ok = parse("# T\n@3 a>b\n## A\n- a\n## B\n- b\n## C\n- c\n")
    placed = [layout_slide(s, ok, th, i) for i, s in enumerate(ok.slides)]
    assert "connector-crosses" not in [d.rule for d in lint(ok, placed, th)]
