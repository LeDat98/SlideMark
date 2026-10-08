"""Area-grid org charts (`@.a./bcd a>b a>c a>d`) fill the body; the lone root fits its heading on a line."""

from __future__ import annotations

from pathlib import Path

from slidemark.ir import Container, Shape, Text
from slidemark.layout import layout_slide
from slidemark.parser import parse
from slidemark.template import deck_theme

EXAMPLE = Path(__file__).parent.parent / "examples" / "19-vi-consulting-brand.md"


def lay(md: str | None = None, **layout):
    deck = parse(md or EXAMPLE.read_text(encoding="utf-8"))
    th = deck_theme(deck, ".")[0].model_copy(deep=True)
    for k, v in layout.items():
        setattr(th.layout, k, v)
    return deck, layout_slide(deck.slides[2], deck, th, 2)


def test_grid_tree_fills_body_and_root_heading_is_one_line():
    deck, pl = lay()
    boxes = [p for p in pl if isinstance(p.element, Container)]
    assert len(boxes) == 4
    top = min(p.y for p in boxes)
    span = max(p.y + p.h for p in boxes) - top
    body_h = 6858000 - top - 0.55 * 914400  # slide height minus the footer area
    assert span >= 0.75 * body_h
    root = boxes[0]
    head = next(
        p for p in pl if isinstance(p.element, Text) and p.element.role == "heading" and p.y == root.y
    )
    from slidemark.layout import measure

    st = head.style
    one = measure.paragraphs_height(head.element.paragraphs, 10**9, st, head.font_scale)
    assert (
        measure.paragraphs_height(head.element.paragraphs, head.w - 2 * 91440, st, head.font_scale)
        <= one * 1.01
    )
    mid = root.x + root.w // 2
    kids = sorted(boxes[1:], key=lambda p: p.x)
    assert abs(mid - (kids[1].x + kids[1].w // 2)) <= 2  # centered over the middle child


def test_grid_tree_connectors_attach():
    _, pl = lay()
    rects = {(p.x, p.y, p.w, p.h) for p in pl if isinstance(p.element, Container)}
    lines = [p for p in pl if isinstance(p.element, Shape) and p.element.attrs.get("src_box")]
    assert len(lines) == 3
    for ln in lines:
        a = ln.element.attrs
        sb, db = tuple(a["src_box"]), tuple(a["dst_box"])
        assert sb in rects and db in rects
        assert ln.y == sb[1] + sb[3] and ln.y + ln.h == db[1]


def test_head_fit_off_keeps_the_old_width():
    _, on = lay(tree_parent_span=0)
    _, off = lay(tree_head_fit=0, tree_parent_span=0)
    w_on = next(p for p in on if isinstance(p.element, Container)).w
    w_off = next(p for p in off if isinstance(p.element, Container)).w
    assert w_on > w_off
