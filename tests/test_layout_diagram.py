"""Mermaid flowcharts: text-sized nodes, edge-to-edge connectors, back edges around the side, edge labels."""

from __future__ import annotations

from pathlib import Path

from slidemark.ir import Shape, Text
from slidemark.layout import layout_slide, measure
from slidemark.layout.engine import _chevron_text_w
from slidemark.layout.grid import Rect
from slidemark.lint import lint
from slidemark.parser import parse
from slidemark.theme import get_theme
from slidemark.units import EMU_PER_INCH as IN
from slidemark.units import slide_size

ROOT = Path(__file__).resolve().parent.parent

APPROVAL = """# Approval flow
> Every request is reviewed within 2 days
```mermaid
graph TD
A[Submit request] --> B[Manager review]
B --> C{Approved?}
C -->|yes| D[Finance pays]
C -->|no| A
```
"""
LR = """# Release
```mermaid
graph LR
A[企画] --> B[設計] --> C[開発] --> D[テスト] --> E[リリース]
```
"""
BRANCH = """# Triage
```mermaid
graph TD
S[Incoming ticket] -->|bug| B[Fix in sprint]
S -->|feature| F[Add to roadmap]
S -->|question| Q[Answer in chat]
```
"""
LR_BACK = """# Loop
```mermaid
graph LR
A[Plan] --> B[Do] --> C[Check]
C -->|retry| A
```
"""


def lay(md: str):
    deck = parse(md)
    theme = get_theme(deck.theme)
    placed = layout_slide(deck.slides[0], deck, theme, 0)
    return deck, theme, placed


def nodes(placed):
    return [
        p for p in placed if isinstance(p.element, Shape) and p.element.shape in ("rounded-rect", "diamond")
    ]


def lines(placed):
    return [p for p in placed if isinstance(p.element, Shape) and p.element.shape == "line"]


def labels(placed):
    return [p for p in placed if isinstance(p.element, Text) and p.element.role == "caption"]


def text_of(p) -> str:
    return " ".join(q.plain for q in p.element.paragraphs)


def rect(p) -> Rect:
    return Rect(p.x, p.y, p.w, p.h)


def overlap(a: Rect, b: Rect) -> bool:
    return a.x < b.right and b.x < a.right and a.y < b.bottom and b.y < a.bottom


def check_clean(md: str):
    deck, theme, placed = lay(md)
    W, H = slide_size(deck.size)
    assert not [d for d in deck.diagnostics if d.level != "info"], deck.diagnostics
    for p in placed:
        assert p.x >= 0 and p.y >= 0 and p.x + p.w <= W and p.y + p.h <= H, (
            text_of(p) if p.element.type == "text" else p
        )
    assert not lint(deck, [placed], theme)
    return deck, theme, placed


def test_approval_nodes_are_text_sized_shapes():
    _deck, _theme, placed = check_clean(APPROVAL)
    ns = nodes(placed)
    assert [text_of(n) for n in ns] == ["Submit request", "Manager review", "Approved?", "Finance pays"]
    shapes = [n.element.shape for n in ns]
    assert shapes == ["rounded-rect", "rounded-rect", "diamond", "rounded-rect"]
    rects = [n for n in ns if n.element.shape == "rounded-rect"]
    assert len({(n.w, n.h) for n in rects}) == 1  # one shared size
    assert rects[0].w >= 1.4 * IN * 0.99 and rects[0].h >= 0.55 * IN * 0.99
    assert rects[0].w < 4 * IN  # not stretched over the slide
    dia = ns[2]
    assert dia.w > rects[0].w and dia.h > rects[0].h  # a diamond needs more room than a box
    centers = {n.x + n.w // 2 for n in ns}
    assert max(centers) - min(centers) <= 2  # a TD chain is centered on one axis
    for a, b in zip(ns, ns[1:], strict=False):
        assert b.y - (a.y + a.h) >= 0.45 * IN * 0.99  # arrows stay visible
    # node style comes from the theme classes
    assert ns[0].style.fill == "surface" and ns[0].style.line == "primary"
    assert ns[2].style.line == "accent"


def test_forward_connectors_run_edge_to_edge():
    _deck, _theme, placed = check_clean(APPROVAL)
    ns = nodes(placed)
    fwd = [ln for ln in lines(placed) if not ln.element.attrs.get("side")]
    assert len(fwd) == 3
    for ln, (a, b) in zip(fwd, zip(ns, ns[1:], strict=False), strict=True):
        assert ln.y == a.y + a.h and ln.y + ln.h == b.y
        assert ln.element.attrs["head"] == "arrow"
        assert ln.element.attrs["src_box"] == [a.x, a.y, a.w, a.h]
        assert ln.element.attrs["dst_box"] == [b.x, b.y, b.w, b.h]


def test_back_edge_goes_around_the_right_side():
    _deck, _theme, placed = check_clean(APPROVAL)
    ns = nodes(placed)
    legs = [ln for ln in lines(placed) if ln.element.attrs.get("side")]
    assert len(legs) == 3
    out, mid, back = legs
    c_node, a_node = ns[2], ns[0]
    right = max(n.x + n.w for n in ns)
    # leaves the decision at its right vertex, enters the first node at its right edge, bends past all nodes
    assert out.x == c_node.x + c_node.w and out.y == c_node.y + c_node.h // 2 and out.h == 0
    assert mid.x > right and mid.w <= 20_000
    assert mid.y <= a_node.y + a_node.h // 2 and mid.y + mid.h >= c_node.y + c_node.h // 2
    assert back.x == a_node.x + a_node.w and back.y == a_node.y + a_node.h // 2
    assert back.element.attrs["head"] == "arrow" and back.element.attrs["flip_h"] is True
    assert out.element.attrs["head"] == "none"
    for leg in legs:  # never through a node
        for n in ns:
            if leg is not back and leg is not out:
                assert not overlap(rect(leg), rect(n))


def test_edge_labels_sit_next_to_the_line_not_over_nodes():
    _deck, _theme, placed = check_clean(APPROVAL)
    ns = nodes(placed)
    labs = labels(placed)
    assert sorted(text_of(lb) for lb in labs) == ["no", "yes"]
    for lb in labs:
        assert lb.style.fill is None
        for n in ns:
            assert not overlap(rect(lb), rect(n))
        for ln in lines(placed):
            if ln.w and ln.h:  # no connector box is crossed by the text rectangle
                assert not (ln.w > 20_000 and ln.h > 20_000 and overlap(rect(lb), rect(ln)))
    yes = next(lb for lb in labs if text_of(lb) == "yes")
    fwd = nodes(placed)[2]
    assert yes.y >= fwd.y + fwd.h  # in the gap under the decision, not on the line
    assert yes.x > fwd.x + fwd.w // 2


def test_lr_chain_is_a_row_of_text_sized_nodes():
    _deck, _theme, placed = check_clean(LR)
    ns = nodes(placed)
    assert [text_of(n) for n in ns] == ["企画", "設計", "開発", "テスト", "リリース"]
    assert len({(n.w, n.h) for n in ns}) == 1
    assert len({n.y + n.h // 2 for n in ns}) == 1
    for a, b in zip(ns, ns[1:], strict=False):
        assert b.x - (a.x + a.w) >= 0.45 * IN * 0.99
    ls = lines(placed)
    assert len(ls) == 4
    for ln, (a, b) in zip(ls, zip(ns, ns[1:], strict=False), strict=True):
        assert ln.x == a.x + a.w and ln.x + ln.w == b.x and ln.h == 0
        assert ln.element.attrs["route"] == "h" and not ln.element.attrs["elbow"]


def test_lr_back_edge_loops_below():
    _deck, _theme, placed = check_clean(LR_BACK)
    ns = nodes(placed)
    legs = [ln for ln in lines(placed) if ln.element.attrs.get("side")]
    assert len(legs) == 3
    bottom = max(n.y + n.h for n in ns)
    out, mid, back = legs
    assert out.y == ns[2].y + ns[2].h or out.y + out.h == ns[2].y + ns[2].h
    assert mid.y > bottom or mid.y + mid.h > bottom
    assert (mid.y + mid.h // 2) > bottom
    assert [text_of(lb) for lb in labels(placed)] == ["retry"]
    assert back.element.attrs["head"] == "arrow"


def test_branching_uses_one_bus_and_distinct_labels():
    _deck, _theme, placed = check_clean(BRANCH)
    ns = nodes(placed)
    src, kids = ns[0], ns[1:]
    assert len({(k.y, k.h) for k in kids}) == 1 and kids[0].y > src.y + src.h
    ls = lines(placed)
    assert len(ls) == 3
    elbows = [ln for ln in ls if ln.element.attrs["elbow"]]
    assert len(elbows) == 2 and all(ln.element.attrs["route"] == "v" for ln in elbows)
    assert {ln.element.attrs["adj"] for ln in elbows} == {elbows[0].element.attrs["adj"]}  # same bus height
    labs = labels(placed)
    assert sorted(text_of(lb) for lb in labs) == ["bug", "feature", "question"]
    for i, a in enumerate(labs):
        assert not any(overlap(rect(a), rect(n)) for n in ns)
        assert not any(overlap(rect(a), rect(b)) for b in labs[i + 1 :])


def test_diagram_survives_unusual_input():
    md = "# T\n```mermaid\ngraph TD\nA[Lonely]\n```\n"
    _deck, _theme, placed = check_clean(md)
    assert [text_of(n) for n in nodes(placed)] == ["Lonely"] and not lines(placed)
    long = "# T\n```mermaid\ngraph TD\nA[A very long node text that wraps over lines] --> B[Short]\n```\n"
    deck, _theme, placed = lay(long)
    ns = nodes(placed)
    assert ns[0].w <= 3.5 * IN and ns[0].h > ns[1].h or ns[0].w == ns[1].w
    assert not [d for d in deck.diagnostics if d.rule == "layout-error"]
    chain = "\n".join(f"N{i}[Step {i}] --> N{i + 1}[Step {i + 1}]" for i in range(7))
    deck, theme, placed = lay(f"# T\n```mermaid\ngraph TD\n{chain}\n```\n")
    _W, H = slide_size(deck.size)
    assert all(p.y + p.h <= H for p in placed)  # the autofit scale shrinks the chart instead of overflowing
    chain = "\n".join(f"N{i}[Step {i}] --> N{i + 1}[Step {i + 1}]" for i in range(14))
    deck, theme, placed = lay(f"# T\n```mermaid\ngraph TD\n{chain}\n```\n")
    assert any(d.rule == "overflow" for d in deck.diagnostics)  # too tall even at the smallest size: reported


def test_chevron_label_does_not_leave_orphans():
    deck = parse((ROOT / "examples" / "02-jp-dense.md").read_text(encoding="utf-8"))
    theme = get_theme(deck.theme)
    placed = layout_slide(deck.slides[1], deck, theme, 1)
    chev = [p for p in placed if isinstance(p.element, Shape) and p.element.shape == "chevron"]
    assert len(chev) == 4
    assert len({round(p.font_scale, 3) for p in chev}) == 1  # one text size across the row
    for p in chev:
        width = _chevron_text_w(rect(p), p.style)
        wide = measure.paragraphs_height(p.element.paragraphs, width, p.style, p.font_scale)
        narrow = measure.paragraphs_height(p.element.paragraphs, round(width * 0.88), p.style, p.font_scale)
        assert narrow <= wide * 1.001  # still the same number of lines in a 12% narrower text area
