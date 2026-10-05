"""Consulting-grade metric: how much of each card and each slide body is empty.

For every box card on every example slide, fill = (text height of the items inside the card) / (card height).
A card below 35% fill is "sparse" (the 01-basics slide 3 defect). Lower sparse counts are better.

Usage: python bench/whitespace.py [--verbose]
"""

from __future__ import annotations

import sys
from pathlib import Path

from slidemark.ir import Container, Placed
from slidemark.layout import layout_slide, measure
from slidemark.parser import parse
from slidemark.template import deck_theme
from slidemark.units import slide_size, to_emu

ROOT = Path(__file__).resolve().parent.parent
SPARSE = 0.35
TAIL_MAX = 0.25


def _content_height(p: Placed) -> float:
    paras = getattr(p.element, "paragraphs", None)
    if not paras:
        return p.h  # visuals (charts, tables, images) fill their box
    pad = 0
    if p.style.padding is not None:
        try:
            pad = to_emu(p.style.padding)
        except ValueError:
            pad = 0
    gap = measure.element_gap(p.element)
    return min(p.h, measure.paragraphs_height(paras, p.w - 2 * pad, p.style, p.font_scale, gap=gap) + 2 * pad)


def _inside(a: Placed, b: Placed) -> bool:
    return a.x >= b.x - 2 and a.y >= b.y - 2 and a.x + a.w <= b.x + b.w + 2 and a.y + a.h <= b.y + b.h + 2


def card_fills(items: list[Placed]) -> list[tuple[str, float]]:
    out = []
    for c in items:
        if not isinstance(c.element, Container) or c.h <= 0 or "plain" in c.element.classes:
            continue
        inner = [p for p in items if p is not c and _inside(p, c) and not isinstance(p.element, Container)]
        if not inner:
            continue
        used = sum(_content_height(p) for p in inner)
        title = c.element.title.paragraphs[0].plain if c.element.title and c.element.title.paragraphs else "?"
        out.append((title, min(used / c.h, 1.0)))
    return out


def _pinned(items: list[Placed], c: Placed) -> bool:
    """True when a chart / image / table beside the card (outside it) spans much of its height."""
    beside = [
        p
        for p in items
        if isinstance(p.element, Container)
        and p is not c
        and (p.x + p.w <= c.x + 2 or p.x >= c.x + c.w - 2)
        and min(p.y + p.h, c.y + c.h) - max(p.y, c.y) > 0
        and p.h < 0.9 * c.h
    ]
    if len(beside) >= 2 and sum(p.h for p in beside) >= 0.8 * c.h:
        return True  # a column of stacked cards beside it sets its height
    for p in items:
        if p.element is None or getattr(p.element, "paragraphs", None) or isinstance(p.element, Container):
            continue
        if _inside(p, c) or p.x < c.x - 2 and p.x + p.w > c.x + c.w:
            continue
        ov = min(p.y + p.h, c.y + c.h) - max(p.y, c.y)
        if ov > 0.3 * c.h and p.h >= 0.6 * c.h and (p.x + p.w <= c.x + 2 or p.x >= c.x + c.w - 2):
            return True
    return False


def card_tails(items: list[Placed]) -> list[tuple[str, float, bool | None]]:
    """Empty height inside each card below its last content line, as a share of the card height.

    The third value is True for the row leader: the card whose content is the tallest of the cards sharing
    its row (same top and height). Shorter siblings cannot shrink, so the gate looks at the leaders.
    """
    raw = []
    for c in items:
        if not isinstance(c.element, Container) or c.h <= 0 or "plain" in c.element.classes:
            continue
        inner = [p for p in items if p is not c and _inside(p, c) and not isinstance(p.element, Container)]
        if not inner:
            continue
        last = max(p.y + _content_height(p) for p in inner)
        title = c.element.title.paragraphs[0].plain if c.element.title and c.element.title.paragraphs else "?"
        raw.append((title, c, last))
    out = []
    for title, c, last in raw:
        mates = [last2 - c2.y for _t, c2, last2 in raw if abs(c2.y - c.y) <= 2 and abs(c2.h - c.h) <= 2]
        lead = last - c.y >= max(mates) - 2
        if lead and _pinned(items, c):
            lead = None  # a visual / stack of cards beside it sets its height: reported as pinned, not gated
        out.append((title, max(0.0, min((c.y + c.h - last) / c.h, 1.0)), lead))
    return out


def body_band(items: list[Placed], top_gap: int, H: int, my: int) -> tuple[float, float, float] | None:
    """(free above, free below, body height) of the slide body, in EMU.

    The body runs from the bottom of the title / lead to the top of the conclusion / footnote / footer.
    Free space is measured between those limits and the content (everything else, incl. card fills).
    """
    head, tail, content = [], [], []
    for p in items:
        el = p.element
        role = getattr(el, "role", None)
        if role in ("title", "subtitle", "lead") or getattr(el, "id", None) == "band":
            head.append(p.y + p.h)
        elif role in ("footnote", "conclusion") or (role == "caption" and el.attrs.get("field")):
            tail.append(p.y)
        else:
            content.append(p)
    if not content or not head:
        return None
    top = max(head)
    bottom = min(tail) if tail else H - my
    if bottom <= top:
        return None
    c0, c1 = min(p.y for p in content), max(p.y + p.h for p in content)
    return max(c0 - top - top_gap, 0), max(bottom - c1, 0), bottom - top


def bands(verbose: bool) -> None:
    """Per slide: the share of the body left empty above / below the content (``--bands``)."""
    worst = []
    for md in sorted((ROOT / "examples").glob("*.md")):
        deck = parse(md.read_text(encoding="utf-8"))
        theme, _ = deck_theme(deck, md.parent)
        if "--top" in sys.argv:  # baseline: no vertical fill
            theme.layout.body_valign = "top"
        measure.set_tokens(theme.layout)
        tg = to_emu(theme.layout.top_gap)
        for i, s in enumerate(deck.slides):
            b = body_band(
                layout_slide(s, deck, theme, i), tg, slide_size(deck.size)[1], to_emu(theme.margin_y)
            )
            if b is None:
                continue
            a, d, h = b
            worst.append((max(a, d) / h, md.stem, i + 1, a / h, d / h))
    for w, stem, n, a, d in worst:
        if verbose or w > 0.2:
            print(f"  band {w:4.0%} {stem} slide {n}: above {a:4.0%} below {d:4.0%}")
    over = sum(w > 0.2 for w, *_ in worst)
    print(f"body band: slides {len(worst)}, empty band > 20%: {over}")


def main() -> int:
    verbose = "--verbose" in sys.argv
    if "--bands" in sys.argv:
        bands("--all" in sys.argv)
        return 0
    tails: list[float] = []
    leads: list[float] = []
    pinned: list[float] = []
    per_deck: dict[str, list[float]] = {}
    cards = sparse = 0
    fills: list[float] = []
    for md in sorted((ROOT / "examples").glob("*.md")):
        deck = parse(md.read_text(encoding="utf-8"))
        theme, _ = deck_theme(deck, md.parent)
        for i, s in enumerate(deck.slides):
            for title, tail, lead in card_tails(layout_slide(s, deck, theme, i)):
                tails.append(tail)
                if lead:
                    leads.append(tail)
                elif lead is None:
                    pinned.append(tail)
                    if verbose:
                        print(f"  pinned {tail:4.0%} {md.stem} slide {i + 1}: {title}")
                if lead:
                    per_deck.setdefault(md.stem, []).append(tail)
                if tail > TAIL_MAX and verbose:
                    print(
                        f"  tail {tail:4.0%}{' lead' if lead else '     '} {md.stem} slide {i + 1}: {title}"
                    )
            for title, fill in card_fills(layout_slide(s, deck, theme, i)):
                cards += 1
                fills.append(fill)
                if fill < SPARSE:
                    sparse += 1
                    if verbose:
                        print(f"  sparse {fill:4.0%}  {md.stem} slide {i + 1}: {title}")
    mean = sum(fills) / len(fills) if fills else 0
    print(f"cards {cards}, sparse (<{SPARSE:.0%} filled) {sparse}, mean fill {mean:.0%}")
    if tails:
        over = sum(t > TAIL_MAX for t in tails)
        lo = sum(t > TAIL_MAX for t in leads)
        print(
            f"row-leader tail: mean {sum(leads) / len(leads):.0%}, max {max(leads):.0%}, "
            f"count >{TAIL_MAX:.0%}: {lo}/{len(leads)}"
        )
        print(f"pinned (not gated): {len(pinned)}, max {max(pinned, default=0):.0%}")
        print(
            f"card tail: mean {sum(tails) / len(tails):.0%}, max {max(tails):.0%}, "
            f"count >{TAIL_MAX:.0%}: {over}/{len(tails)}"
        )
    if "--decks" in sys.argv:
        for name, ts in per_deck.items():
            n_over = sum(t > TAIL_MAX for t in ts)
            print(
                f"  {name:28s} leaders={len(ts):3d} mean {sum(ts) / len(ts):4.0%} "
                f"max {max(ts):4.0%} >25%: {n_over}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
