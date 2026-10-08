"""Card headings never wrap in a row (``heading.wrap=off``, the default): the last look at a finished slide.

The layout already shrinks the headings of a row of cards to one line while it places them
(``engine._fit_heads``). The passes that run after the placement (card growth, ``@steps`` card fill) scale a
card's heading together with its text and can bring a wrap back. This pass looks at the final geometry:

* the headings are the first ``heading`` text inside every card (a ``.kpi`` card, a text with a size of its
  own and a heading with several paragraphs are left alone);
* headings of one size form a group; when one wraps, the whole group shrinks to one common size, the
  largest step that makes every heading fit on one line, never below the card body text of the group;
* when even that does not fit, nothing changes: every heading keeps its size and wraps the same way.

The heading keeps its box (height, position), so nothing around it moves. Never raises.
"""

from __future__ import annotations

from ..ir import Container, Paragraph, Placed, Run, Text
from . import measure
from .l3fill import _text_pad
from .vfill import _contains

_STEP = 0.02


def _size(p: Placed) -> float:
    return (p.style.font_size or 18) * p.font_scale


def _wraps(p: Placed, k: float, margin: float) -> bool:
    """Would heading ``p`` drawn ``k`` x its size take more than one line (width a bit narrower than the
    estimate: the renderers wrap earlier)?"""
    pad = _text_pad(p)
    w = round((p.w - 2 * pad) * (1.0 - margin))
    scale = p.font_scale * k
    one = measure.paragraphs_height([Paragraph(runs=[Run(text="Ag")])], w, p.style, scale, gap=0.0)
    got = measure.paragraphs_height(p.element.paragraphs, w, p.style, scale, gap=0.0)
    return got > one * 1.45


def _own_size(p: Placed) -> bool:
    el = p.element
    return (
        getattr(el.style, "font_size", None) is not None
        or any(measure.has_exact(q) for q in el.paragraphs)
        or any(q.style is not None and q.style.font_size for q in el.paragraphs)
    )


def fit_headings(out: list[Placed], theme, lt) -> list[Placed]:
    """``out`` with the card headings of every group shrunk to one line where that is possible."""
    try:
        return _fit(out, theme, lt)
    except Exception:
        return out


def _fit(out: list[Placed], theme, lt) -> list[Placed]:
    if getattr(theme, "heading_wrap", False) or "heading" in (theme.pinned or []):
        return out
    cards = [
        p
        for p in out
        if isinstance(p.element, Container) and p.element.title is not None and "kpi" not in p.element.classes
    ]
    heads: list[tuple[Placed, Placed]] = []  # (card, its first heading text)
    for card in cards:
        inside = sorted(
            (p for p in out if p is not card and isinstance(p.element, Text) and _contains(card, p)),
            key=lambda p: (p.y, p.x),
        )
        head = next((p for p in inside if p.element.role == "heading"), None)
        if head is None or len(head.element.paragraphs) != 1 or _own_size(head):
            continue
        heads.append((card, head))
    groups: dict[int, list[tuple[Placed, Placed]]] = {}
    for card, head in heads:
        groups.setdefault(round(_size(head) * 4), []).append((card, head))
    res: dict[int, Placed] = {}
    margin = lt.l3_wrap_margin
    for group in groups.values():
        if len(group) < 2 or not any(_wraps(h, 1.0, margin) for _c, h in group):
            continue
        body = 0.0
        for card, head in group:
            for p in out:
                if (
                    p is not head
                    and isinstance(p.element, Text)
                    and p.element.role == "body"
                    and _contains(card, p)
                    and "callout" not in p.element.classes
                ):
                    body = max(body, _size(p))
        top = max(_size(h) for _c, h in group)
        floor = body or theme.sizes.get("body", 16)
        k_lo = floor / max(top, 1.0)
        if k_lo >= 1.0:
            continue
        k = 1.0
        while k > k_lo + 1e-9:
            k = max(round(k - _STEP, 4), k_lo)
            if not any(_wraps(h, k, margin) for _c, h in group):
                for _c, h in group:
                    res[id(h)] = h.model_copy(update={"font_scale": round(h.font_scale * k, 4)})
                break
    return [res.get(id(p), p) for p in out]
