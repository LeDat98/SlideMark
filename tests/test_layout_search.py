"""Automatic layout search (L7): candidates, explicit grids untouched, ties keep the rule, overflow out."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from slidemark.ir import Chart, Container, Image, Placed, Series, Text
from slidemark.layout import engine, layout_slide
from slidemark.layout.grid import Rect
from slidemark.layout.score import HARD_OVER, score
from slidemark.layout.search import MAX_ALTERNATIVES, alternatives
from slidemark.parser import parse
from slidemark.template import resolve_theme
from slidemark.theme import get_theme

LONG = (
    "Each of these points carries a full sentence of explanation, "
    "so the box is clearly longer than its neighbours."
)
CHART = '```column {title="T"}\n,Q1,Q2,Q3,Q4\n2025,10,12,15,14\n2026,12,16,21,25\n```\n'
WIDE = (
    '```column {title="M"}\n,Jan,Feb,Mar,Apr,May,Jun,Jul,Aug,Sep,Oct,Nov,Dec\n'
    "2025,10,12,15,14,11,13,16,18,17,19,20,22\n2026,12,16,21,25,22,24,27,29,28,30,33,35\n```\n"
)

THREE_LONG_MIDDLE = (
    f"# t\n## A\n- Receive\n## B\n{chr(10).join('- ' + LONG for _ in range(4))}\n## C\n- Deliver\n@end\n"
)
TEXT_CHART = "# t\n" + "".join(f"- {LONG}\n" for _ in range(7)) + WIDE
FOUR_THEN_CHART = (
    "# t\n## Plan\n- Define scope and success criteria\n- Agree the budget with finance\n"
    "## Build\n- Implement the core pipeline end to end, with a test for every parser rule\n"
    "- Keep the token benchmark green on every commit and record the history\n"
    "- Open each deck in LibreOffice and compare it with the golden image\n"
    "## Test\n- Run the suite and the fuzzers\n- Check CJK wrapping\n"
    "## Ship\n- Tag the release and publish the wheel\n- Announce the changes\n@end\n" + CHART
)


def lay(md: str, theme: str = "default"):
    deck = parse(f"theme: {theme}\n\n{md}")
    placed = layout_slide(deck.slides[0], deck, get_theme(deck.theme), 0)
    return placed, deck


def boxes_of(placed: list[Placed]):
    return [(p.x, p.y, p.w, p.h, p.font_scale) for p in placed]


def picked(deck) -> list[str]:
    return [d.message for d in deck.diagnostics if d.rule == "auto-layout"]


def no_search(monkeypatch):
    monkeypatch.setattr(engine, "MAX_CANDIDATES", 1)


def cards(placed):
    return [p for p in placed if isinstance(p.element, Container)]


# ---- candidate generation


def _blocks(*kinds):
    from slidemark.ir import Paragraph, Run

    t = Text(role="body", paragraphs=[Paragraph(runs=[Run(text="x")])])
    mk = {
        "text": lambda: t,
        "box": lambda: Container(title=t, children=[t]),
        "chart": lambda: Chart(kind="column", categories=["a"], series=[Series(name="s", values=[1])]),
        "image": lambda: Image(src="x.png"),
    }
    return [mk[k]() for k in kinds]


def test_alternatives_for_four_boxes_offer_a_2x2_and_a_row():
    toks = alternatives(_blocks("box", "box", "box", "box"), [10, 10, 10, 10], tail=True)
    assert "2x2" in toks and "4x1" in toks
    assert len(toks) <= MAX_ALTERNATIVES


def test_alternatives_without_tail_use_short_tokens():
    toks = alternatives(_blocks("box", "box", "box", "box"), [10, 10, 10, 10], tail=False)
    assert "4" in toks and "2x2" in toks


def test_alternatives_for_three_boxes_follow_the_heavy_one():
    toks = alternatives(_blocks("box", "box", "box"), [10, 90, 10], tail=False)
    assert {"3", "bba/bbc", "bb/ac", "ac/bb", "1"} <= set(toks)


def test_alternatives_for_text_and_visual():
    assert alternatives(_blocks("text", "chart"), [50, 10_000], tail=False) == ["1:1", "1:2", "2:1", "1"]
    assert alternatives(_blocks("chart", "text"), [10_000, 50], tail=False) == [
        "b/a"
    ]  # visual first: text on top


def test_alternatives_are_bounded_and_skip_kpi_flow_and_groups():
    for n in range(2, 13):
        assert len(alternatives(_blocks(*["box"] * n), [10] * n, tail=n % 2 == 0)) <= MAX_ALTERNATIVES
    assert alternatives(_blocks("box"), [10], tail=False) == []
    kpi = _blocks("box", "box")
    kpi[0].classes.append("kpi")
    assert alternatives(kpi, [10, 10], tail=False) == []


def test_every_alternative_is_a_valid_grid_token():
    from slidemark.layout.grid import parse_spec

    for kinds in (
        ("box",) * 2,
        ("box",) * 3,
        ("box",) * 4,
        ("box",) * 6,
        ("text", "chart"),
        ("chart", "text"),
    ):
        n = len(kinds)
        for tok in alternatives(_blocks(*kinds), [10] * n, tail=False):
            gs = parse_spec(tok, n, [])
            assert gs is not None and gs.cols and not gs.errors, tok


# ---- the scorer


def test_overflow_is_a_hard_penalty():
    ok = score([], Rect(0, 0, 100, 100), get_theme("default"), over=0)
    bad = score([], Rect(0, 0, 100, 100), get_theme("default"), over=1)
    assert bad.hard >= HARD_OVER and bad.total > ok.total + 900


# ---- the search itself


def test_four_boxes_then_chart_pick_2x2_and_pinning_reproduces_it(monkeypatch):
    placed, deck = lay(FOUR_THEN_CHART)
    (msg,) = picked(deck)
    assert "`@2x2`" in msg
    hint = next(d.hint for d in deck.diagnostics if d.rule == "auto-layout")
    assert hint == "write `@2x2` to pin it"
    cs = cards(placed)
    assert len({c.x for c in cs}) == 2 and len({c.y for c in cs}) == 2
    pinned, pdeck = lay(FOUR_THEN_CHART.replace("# t\n", "# t\n@2x2\n", 1))
    assert not picked(pdeck)
    assert boxes_of(pinned) == boxes_of(placed)
    no_search(monkeypatch)
    rule, _ = lay(FOUR_THEN_CHART)
    assert len({c.x for c in cards(rule)}) == 4  # the rule's choice: one row of four


def test_long_middle_box_gets_the_wide_area_and_pinning_reproduces_it(monkeypatch):
    placed, deck = lay(THREE_LONG_MIDDLE)
    (msg,) = picked(deck)
    assert "`@bb/ac`" in msg
    a, b, c = cards(placed)
    assert b.w > a.w and b.y < a.y + 1 and a.y == c.y  # the long box on top, full width
    pinned, _ = lay(THREE_LONG_MIDDLE.replace("# t\n", "# t\n@bb/ac\n", 1))
    assert boxes_of(pinned) == boxes_of(placed)
    no_search(monkeypatch)
    rule, _ = lay(THREE_LONG_MIDDLE)
    assert min(p.font_scale for p in rule if isinstance(p.element, Text)) <= min(
        p.font_scale for p in placed if isinstance(p.element, Text)
    )


def test_text_beside_a_wide_chart_tries_other_splits():
    placed, deck = lay(TEXT_CHART)
    (msg,) = picked(deck)
    assert "`@1:1`" in msg
    txt = next(p for p in placed if isinstance(p.element, Text) and p.element.role == "body")
    pinned, _ = lay(TEXT_CHART.replace("# t\n", "# t\n@1:1\n", 1))
    assert boxes_of(pinned) == boxes_of(placed)
    assert txt.w > 0.4 * 12 * 914400 * 0.9  # half the body instead of the default 40%


def test_explicit_grid_is_never_changed(monkeypatch):
    for token in ("3", "1:1:1", "aab/aac"):
        md = THREE_LONG_MIDDLE.replace("# t\n", f"# t\n@{token}\n", 1)
        placed, deck = lay(md)
        assert not picked(deck)
        no_search(monkeypatch)
        again, _ = lay(md)
        monkeypatch.undo()
        assert boxes_of(placed) == boxes_of(again)


def test_balanced_slide_keeps_the_rule_choice(monkeypatch):
    md = "# t\n## A\n- one\n- two\n## B\n- one\n- two\n## C\n- one\n- two\n@end\n"
    placed, deck = lay(md)
    assert not picked(deck)
    no_search(monkeypatch)
    rule, _ = lay(md)
    assert boxes_of(placed) == boxes_of(rule)


def test_tie_keeps_the_rule_choice(monkeypatch):
    """Alternatives that score the same (or better by less than the margin) never replace the rule."""
    calls: list[float] = []
    real = engine.score_layout

    def flat(items, body, theme, *, over=0):
        s = real(items, body, theme, over=over)
        calls.append(s.total)
        s.total = 5.0  # every candidate ties
        return s

    monkeypatch.setattr(engine, "score_layout", flat)
    placed, deck = lay(FOUR_THEN_CHART)
    assert len(calls) > 1 and not picked(deck)
    assert len({c.x for c in cards(placed)}) == 4


def test_overflowing_candidates_are_rejected(monkeypatch):
    seen: list[tuple[float, float]] = []
    real = engine.score_layout

    def spy(items, body, theme, *, over=0):
        s = real(items, body, theme, over=over)
        seen.append((s.hard, s.total))
        return s

    monkeypatch.setattr(engine, "score_layout", spy)
    placed, deck = lay(FOUR_THEN_CHART)
    assert any(h >= HARD_OVER for h, _ in seen)  # `1x4` (four stacked rows) overflows ...
    assert picked(deck) and "1x4" not in picked(deck)[0]  # ... and is not the winner
    assert not [d for d in deck.diagnostics if d.rule == "overflow"]


def test_search_is_bounded_and_deterministic(monkeypatch):
    n = []
    real = engine.score_layout

    def count(items, body, theme, *, over=0):
        n.append(1)
        return real(items, body, theme, over=over)

    monkeypatch.setattr(engine, "score_layout", count)
    a, _ = lay(FOUR_THEN_CHART)
    assert len(n) <= engine.MAX_CANDIDATES
    n.clear()
    b, _ = lay(FOUR_THEN_CHART)
    assert boxes_of(a) == boxes_of(b)


def test_slide_is_not_mutated():
    deck = parse(f"theme: default\n\n{FOUR_THEN_CHART}")
    s = deck.slides[0]
    before = s.model_dump()
    layout_slide(s, deck, get_theme("default"), 0)
    assert s.model_dump() == before and s.grid is None


def test_flow_links_and_kpi_slides_are_not_searched():
    for md in (
        "# t\n@flow\n## A\n- x\n## B\n- y\n## C\n- z\n@end\n",
        "# t\n@a>b\n## A\n- x\n## B\n- y\n@end\n",
        "# t\n## A {.kpi}\n1\n## B {.kpi}\n2\n@end\n",
    ):
        _, deck = lay(md)
        assert not picked(deck), md


def test_build_time_stays_under_50ms_per_slide():
    root = Path(__file__).resolve().parent.parent / "examples"
    jobs = []
    for md in sorted(root.glob("*.md")):
        deck = parse(md.read_text(encoding="utf-8"))
        theme, _ = resolve_theme(deck.theme, md.parent)
        jobs += [(s, deck, theme, i) for i, s in enumerate(deck.slides)]
    layout_slide(*jobs[0])  # warm the caches
    t0 = time.perf_counter()
    for job in jobs:
        layout_slide(*job)
    per_slide = (time.perf_counter() - t0) / len(jobs)
    assert per_slide < 0.05, f"{per_slide * 1000:.1f} ms/slide"


@pytest.mark.parametrize("name", ["04-jp-kpi", "09-midnight-tech"])
def test_examples_do_not_raise(name):
    root = Path(__file__).resolve().parent.parent / "examples"
    deck = parse((root / f"{name}.md").read_text(encoding="utf-8"))
    theme, _ = resolve_theme(deck.theme, root)
    for i, s in enumerate(deck.slides):
        assert layout_slide(s, deck, theme, i)
    assert not [d for d in deck.diagnostics if d.rule == "layout-error"]
