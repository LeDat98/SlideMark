"""`@free` slides: explicit boxes are placed exactly, the rest stacks on top."""

from __future__ import annotations

from pptx import Presentation

from slidemark import build, critique, lint
from slidemark.ir import Container, Placed, Text
from slidemark.layout import layout_slide
from slidemark.parser import parse
from slidemark.template import deck_theme

MD = """# Free

@free

Unplaced text here

{x=50% y=10% w=40% h=15%}
Plain text

## Card A {x=5% y=10% w=40% h=40%}
Hello world card
"""


def _run(md: str):
    deck = parse(md)
    theme, _ = deck_theme(deck, None)
    items = layout_slide(deck.slides[0], deck, theme, 0)
    return deck, theme, items


def _text(items: list[Placed], word: str) -> Placed:
    return next(p for p in items if isinstance(p.element, Text) and word in p.element.paragraphs[0].plain)


def test_parser_free_word():
    deck = parse(MD)
    assert deck.slides[0].layout == "free"
    assert not [d for d in deck.diagnostics if d.rule == "unknown-token"]


def test_boxes_placed_exactly_and_unplaced_stacks():
    deck, _theme, items = _run(MD)
    card = next(p for p in items if isinstance(p.element, Container))
    plain = _text(items, "Plain")
    assert abs(plain.w / card.w - 1.0) < 0.01
    assert abs(plain.h / card.h - 15 / 40) < 0.01
    assert abs(plain.y - card.y) < 2 and plain.x > card.x + card.w  # 5% + 40% < 50%
    loose = _text(items, "Unplaced")
    assert loose.y < card.y + card.h and loose.w > 0
    found = [d for d in deck.diagnostics if d.rule == "free-unplaced"]
    assert len(found) == 1 and found[0].level == "info" and "x=" in found[0].hint


def test_no_growth_on_sparse_free_slide():
    _deck, _theme, items = _run("# T\n\n@free\n\n{x=10% y=10% w=80% h=60%}\nTiny\n")
    p = _text(items, "Tiny")
    assert p.font_scale == 1.0


def test_free_skips_balance_rules_and_lint_flags_overflow():
    md = (
        "# T\n\n@free\n\n"
        "{x=60% y=10% w=10% h=5%}\n"
        "Big text that will not fit here at all because it is long long long long long long long "
        "long long long long long long long long\n\n"
        "## A {x=5% y=10% w=40% h=60%}\nshort\n"
    )
    deck, theme, items = _run(md)
    rules = {d.rule for d in critique.critique_slide(items, deck, theme, 0)}
    assert not rules & {"design-empty-band", "design-sparse-box", "design-unbalanced"}
    assert "overflow" in {d.rule for d in lint.lint(deck, [items], theme)} | {
        d.rule for d in deck.diagnostics
    }


def test_overlap_only_for_text():
    md = "# T\n\n@free\n\n{x=10% y=10% w=40% h=20%}\nA text\n\n{x=20% y=15% w=40% h=20%}\nB text\n"
    deck, theme, items = _run(md)
    assert "overlap" in {d.rule for d in lint.lint(deck, [items], theme)}
    md2 = "# T\n\n@free\n\n{x=15% y=40% w=20% h=10%}\nOver text\n\n## Card {x=10% y=10% w=40% h=40%}\nx\n"
    deck, theme, items = _run(md2)
    assert "overlap" not in {d.rule for d in lint.lint(deck, [items], theme)}


def test_render_reopen(tmp_path):
    out = tmp_path / "f.pptx"
    build(MD, out)
    prs = Presentation(str(out))
    sl = prs.slides[0]
    hit = [s for s in sl.shapes if s.has_text_frame and "Plain text" in s.text_frame.text]
    assert hit
    W = prs.slide_width
    assert abs(hit[0].left - round(0.5 * (W - 2 * 0.0) + 0)) > -1  # placed (not at the origin)
    assert hit[0].left > W * 0.4
