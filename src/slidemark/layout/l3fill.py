"""L3 fill: text cards and text panels use the height they have (token driven, geometry only).

Two cases, both applied to the finished placed items of a content slide body:

* ``fill_row``: a sparse slide (the completion ran) whose body is ONE row of text cards. The row stays
  top-anchored right under the lead; the cards share one height that reaches down to
  ``layout.sparse_row_bottom_band`` of the body above its bottom; inside each card the paragraphs spread with
  even gaps (at most ``layout.l3_gap_extra`` em more per gap, ``l3_gap_extra_numbered`` for numbered lists).
  When the cap is hit the rest stays at the bottom of the card (text is never centered).
* ``fill_panels``: a text card beside a chart / image whose content fills less than
  ``layout.panel_fill_min`` of its height: paragraphs spread the same way and a trailing note / callout
  anchors to the card bottom.

Explicit author input wins: a ``{h=}`` box, a vertical alignment, ``@free`` (never reaches here) and
``layout.body_valign=top`` leave everything as it is. Never raises: anything unexpected returns the items
unchanged.
"""

from __future__ import annotations

from ..ir import Chart, Container, Image, Media, Placed, Shape, Table, Text
from ..theme import LayoutTokens
from ..units import EMU_PER_PT, to_emu
from . import measure
from .grid import Rect
from .vfill import _contains

_HEAD_ROLES = {"title", "subtitle", "lead", "conclusion", "caption", "footnote"}


def _pad(p: Placed, card: Placed) -> int:
    """Inner inset of a card: the horizontal gap between the card edge and its text."""
    return max(0, min(p.x - card.x, to_emu("0.15in")))


def _is_note(p: Placed) -> bool:
    return "callout" in p.element.classes or bool(p.style.fill or p.style.line)


def _explicit(p: Placed) -> bool:
    if p.element.box is not None:
        return True
    if getattr(p.element, "role", None) == "heading":
        return False  # a heading band centres its text by design (its box never moves relative to the card)
    return p.style.valign not in (None, "top") and not _is_note(p)


def _inner_texts(card: Placed, out: list[Placed], deco: bool = False) -> list[Placed] | None:
    """The placed texts inside ``card``; ``None`` when it holds anything else (nested cards, tables ...).

    ``deco``: header bars and icons (shapes in the top band of the card) stay put and are skipped."""
    inner = [p for p in out if p is not card and _contains(card, p)]
    if deco:
        inner = [
            p for p in inner if not (isinstance(p.element, Shape) and p.y + p.h <= card.y + (card.h // 3) + 2)
        ]
    if not inner or any(not isinstance(p.element, Text) for p in inner):
        return None
    return inner


def _text_pad(p: Placed) -> int:
    if p.style.padding is None:
        return 0
    try:
        return to_emu(p.style.padding)
    except ValueError:
        return 0


def _spread(
    p: Placed,
    avail: int,
    lt: LayoutTokens,
    pad: int,
    s: float = 1.0,
    short: bool = False,
    cap_to: float | None = None,
    gap_cap: float | None = None,
) -> tuple[Placed, float, float] | None:
    """Text of ``p`` grown by ``s`` and its paragraph gaps spread (capped) to span ``avail`` EMU.

    Returns the new item (``h`` = ``avail``), the free height left under the text and the extra gap (em) it
    got; ``None`` when the grown text would wrap onto more lines or not fit (caller keeps the smaller one)."""
    paras = p.element.paragraphs
    pad = _text_pad(p)  # the text's own inset (what lint and the renderer measure with)
    width = p.w - 2 * pad
    if s > 1.0:
        h0 = measure.paragraphs_height(paras, width, p.style, p.font_scale, gap=0.0)
        p = p.model_copy(update={"font_scale": p.font_scale * s})
        tight = round(width * (1.0 - lt.l3_wrap_margin))  # the render wraps a bit earlier than the estimate
        if measure.paragraphs_height(paras, tight, p.style, p.font_scale, gap=0.0) > h0 * s * 1.015:
            return None  # a new wrapped line / orphan (CJK wrap guard)
    p = p.model_copy(update={"h": avail})
    n = len(paras)
    g0 = measure.element_gap(p.element)
    g0 = measure.para_gap() if g0 is None else g0
    need = measure.paragraphs_height(paras, width, p.style, p.font_scale, gap=g0)
    free = avail - 2 * pad - need
    if free < 0 and s > 1.0:
        return None
    size = (p.style.font_size or 18) * p.font_scale * EMU_PER_PT
    if n < 2 or free <= 0 or size <= 0:
        return p, max(free, 0.0), 0.0
    cap = lt.l3_gap_extra_numbered if paras[0].marker == "number" else lt.l3_gap_extra
    if short and n <= lt.l3_short_items:
        cap = max(cap, lt.l3_gap_extra_short)
    cap = min(cap, lt.l3_gap_cap if gap_cap is None else gap_cap)  # one even rhythm, never a stretched list
    if cap_to is not None:
        cap = min(cap, cap_to)  # sibling cards share the smallest rhythm
    extra = min(max(cap, 0.0), free / ((n - 1) * size))
    for _ in range(10):  # the estimate carries a safety factor: shrink until it surely fits
        if extra <= 0.01 or measure.paragraphs_height(
            paras, width, p.style, p.font_scale, gap=g0 + extra
        ) <= (avail - 2 * pad):
            break
        extra *= 0.9
    if extra <= 0.01:
        return p, free, 0.0
    need = measure.paragraphs_height(paras, width, p.style, p.font_scale, gap=g0 + extra)
    p = p.model_copy(
        update={
            "element": p.element.model_copy(
                update={"attrs": {**p.element.attrs, "para_gap": round(g0 + extra, 3)}}
            )
        }
    )
    return p, max(avail - 2 * pad - need, 0.0), extra


def _max_step(card: Placed, inner: list[Placed], lt: LayoutTokens) -> float:
    """Largest text growth factor a card's body text may take (explicit sizes never grow)."""
    heads = [p for p in inner if p.element.role == "heading"]
    mains = [p for p in inner if p.element.role != "heading" and not _is_note(p)]
    if len(mains) != 1 or getattr(mains[0].element, "style", None) and mains[0].element.style.font_size:
        return 1.0
    m = mains[0]
    pt = (m.style.font_size or 18) * m.font_scale
    cap = lt.l3_text_max_pt
    if heads:
        hp = max((h.style.font_size or 18) * h.font_scale for h in heads)
        cap = min(cap, hp * lt.l3_body_head_max)
    return max(cap / pt, 1.0) if pt > 0 else 1.0


def _fill_card(
    card: Placed,
    inner: list[Placed],
    top: int,
    bottom: int,
    lt: LayoutTokens,
    s: float = 1.0,
    short: bool = False,
    cap_to: float | None = None,
    gap_cap: float | None = None,
) -> tuple[dict[int, Placed], float, float, float] | None:
    """New geometry of ``card`` and its texts for the box ``top..bottom``; ``None`` = leave it alone.

    Also returns the free height under the body text, the text's end below ``top`` (EMU) and the extra
    paragraph gap (em) the text got."""
    dy = top - card.y
    heads = [p for p in inner if p.element.role == "heading"]
    notes = [p for p in inner if p.element.role != "heading" and _is_note(p)]
    mains = [p for p in inner if p not in heads and p not in notes]
    kpi = "kpi" in card.element.classes  # a KPI value stays centred in its (taller) card, no spread
    if len(mains) != 1 or any(_explicit(p) and not (kpi and p is mains[0]) for p in (card, *inner)):
        return None
    main = mains[0]
    pad = _pad(main, card)
    res: dict[int, Placed] = {id(card): card.model_copy(update={"y": top, "h": bottom - top})}
    for p in heads:
        res[id(p)] = p.model_copy(update={"y": p.y + dy})
    floor = bottom - pad
    for p in sorted(notes, key=lambda q: -q.y):  # the last note sits on the bottom, the others stack above
        y = floor - p.h
        res[id(p)] = p.model_copy(update={"y": y})
        floor = y - pad
    m = main.model_copy(update={"y": main.y + dy})
    avail = floor - m.y
    if avail < main.h - 2:  # never squeeze the text
        return None
    if kpi:
        res[id(main)] = m.model_copy(update={"h": avail})
        return res, 0.0, avail, 0.0
    sp = None
    if heads:  # air between the heading band and the first item
        size = (m.style.font_size or 18) * m.font_scale * EMU_PER_PT
        gap = round(lt.l3_head_pad * size)
        if gap and avail - gap >= main.h - 2:
            mg = m.model_copy(update={"y": m.y + gap})
            sp = _spread(mg, avail - gap, lt, pad, s, short, cap_to, gap_cap)
            if sp is not None:
                m, avail = mg, avail - gap
    if sp is None:
        sp = _spread(m, avail, lt, pad, s, short, cap_to, gap_cap)
    if sp is None:
        return None
    res[id(main)], free, extra = sp
    return res, free + pad, m.y - top + (avail - free), extra  # the card's bottom inset is empty too


def _apply(out: list[Placed], res: dict[int, Placed]) -> list[Placed]:
    return [res.get(id(p), p) for p in out]


def _body_items(out: list[Placed], body: Rect) -> list[Placed]:
    return [
        p
        for p in out
        if p.y >= body.y - 2
        and p.y + p.h <= body.bottom + 2
        and getattr(p.element, "role", None) not in _HEAD_ROLES
    ]


def fill_row(
    out: list[Placed], body: Rect, lt: LayoutTokens, consulting: bool = True, sparse: bool = True
) -> list[Placed]:
    """A sparse slide of one row of text cards: top-anchored, equal tall cards, spread paragraphs.

    A row followed by a table keeps its top and its height at most (``bounded``): the text grows first,
    then the cards shrink to their content and the table follows them up (the free band ends up at the
    bottom of the body). ``sparse=False`` only accepts that bounded case."""
    try:
        return _fill_row(out, body, lt, consulting, sparse)
    except Exception:  # never raise on bad input
        return out


def _row_extras(items: list[Placed], cards: list[Placed], covered: set[int]):
    """Arrows between the cards and notes under them; ``None`` when anything else shares the body."""
    top = min(c.y for c in cards)
    bottom = max(c.y + c.h for c in cards)
    arrows: list[Placed] = []
    tails: list[Placed] = []
    for p in items:
        if id(p) in covered:
            continue
        if isinstance(p.element, Shape) and p.h <= to_emu("0.05in") and top <= p.y <= bottom:
            arrows.append(p)  # a flow arrow: stays centred between the cards
        elif isinstance(p.element, (Text, Table)) and p.y >= bottom - 2:
            tails.append(p)  # a callout / conclusion bar under the row: follows the cards
        else:
            return None
    return arrows, tails


def _fill_row(
    out: list[Placed], body: Rect, lt: LayoutTokens, consulting: bool, sparse: bool = True
) -> list[Placed]:
    if not lt.l3_fill or lt.body_valign == "top" or body.h <= 0:
        return out
    items = _body_items(out, body)
    cards = [p for p in items if isinstance(p.element, Container)]
    if not cards or any(isinstance(p.element, (Chart, Image, Media)) for p in items):
        return out
    if not consulting and not all("kpi" in c.element.classes for c in cards):
        return out  # normal-density themes keep their hugging cards (only KPI rows are top-anchored)
    bounded = any(isinstance(p.element, Table) for p in items)  # a table below: keep top, shrink only
    if not sparse and not bounded:
        return out
    plan: dict[int, list[Placed]] = {}
    for c in cards:
        inner = _inner_texts(c, items, deco=bounded)
        if inner is None:
            return out
        plan[id(c)] = inner
    covered = {id(p) for ps in plan.values() for p in ps} | set(plan)
    if bounded:  # decoration inside the cards (header bars, icons) is covered too
        covered |= {id(p) for p in items if any(_contains(c, p) for c in cards)}
    extras = _row_extras(items, cards, covered)
    if extras is None:  # free text / tables / shapes next to the cards
        return out
    arrows, tails = extras
    if min(c.y + c.h for c in cards) <= max(c.y for c in cards):  # not one row
        return out
    old_bottom = max(c.y + c.h for c in cards)
    bounded = bounded and any(isinstance(p.element, Table) for p in tails)
    if not sparse and not bounded:
        return out
    if bounded:  # a table fills the rest: the row keeps its top and never grows taller
        top = min(c.y for c in cards)
        bottom = old_bottom
    else:
        top = body.y
        tail_h = max((p.y + p.h for p in tails), default=old_bottom) - old_bottom
        bottom = body.bottom - round(lt.sparse_row_bottom_band * body.h) - tail_h
    if bottom - top < max(c.h for c in cards) or any(c.y < top for c in cards):
        return out
    kpi = all("kpi" in c.element.classes for c in cards)
    full = bottom - top

    def run(h: int, s: float, short: bool):
        """(placed items, free heights, text ends) of every card at row height ``h``; ``None`` = refused."""
        rs = [_fill_card(c, plan[id(c)], top, top + h, lt, s, short) for c in cards]
        if any(r is None for r in rs):
            return None
        extras = [r[3] for r in rs]
        if max(extras) - min(extras) > 0.01:  # one rhythm for every card of the row
            rs = [_fill_card(c, plan[id(c)], top, top + h, lt, s, short, min(extras)) for c in cards]
            if any(r is None for r in rs):
                return None
        res: dict[int, Placed] = {}
        for r in rs:
            res.update(r[0])
        return res, [r[1] for r in rs], [r[2] for r in rs]

    r = run(full, 1.0, False)
    if r is None:
        return out  # one card refuses: the row stays as it was
    h, s_ok = full, 1.0
    tail_max = lt.l3_tail_max * full
    if not kpi and max(r[1]) > tail_max:  # (a) grow the text (capped gaps), (c) shorter cards
        s_top = min(_max_step(c, plan[id(c)], lt) for c in cards)
        k = 1
        while s_top > 1.0 + 1e-6 and max(r[1]) > tail_max:
            s = min(1.0 + k * lt.l3_grow_step, s_top)
            nxt = run(full, s, False)
            if nxt is None:
                break
            r, s_ok = nxt, s
            k += 1
            if s >= s_top:
                break
        if max(r[1]) > tail_max:  # (c) the shortest row whose emptiest card keeps its tail within the limit
            nat = max(c.h for c in cards)
            h0 = max((full - max(r[1])) / (1.0 - lt.l3_tail_aim), nat)
            for k in range(0, 40):
                h = round(min(h0 * (1.0 + 0.03 * k), full))
                nxt = run(h, s_ok, True)
                if nxt is not None or h >= full:
                    break
            if nxt is not None:
                r = nxt
            else:
                h = full
    res = dict(r[0])
    if arrows:  # keep the arrows on the middle of the new card row
        old_mid = (min(c.y for c in cards) + old_bottom) / 2
        for a in arrows:
            res[id(a)] = a.model_copy(update={"y": round(top + h / 2 - (old_mid - a.y))})
    for p in tails:
        res[id(p)] = p.model_copy(update={"y": top + h + (p.y - old_bottom)})
    return _apply(out, res)


def fill_cards_to_bar(
    out: list[Placed], body: Rect, lt: LayoutTokens, bar: bool, anchored: bool, foot: bool
) -> list[Placed] | None:
    """A body of text cards (one row or a grid) above a conclusion bar: top-anchored, stretched to the bar.

    ``None`` = not this case (caller continues with the other fills). Applies with a conclusion bar, or with
    a footnote when the block is already top-anchored (``anchored``)."""
    try:
        return _cards_to_bar(out, body, lt, bar, anchored, foot)
    except Exception:  # never raise on bad input
        return None


def _card_rows(cards: list[Placed]) -> list[list[Placed]]:
    rows: list[list[Placed]] = []
    bottom = -1
    for c in sorted(cards, key=lambda p: (p.y, p.x)):
        if rows and c.y < bottom - 2:
            rows[-1].append(c)
            bottom = max(bottom, c.y + c.h)
        else:
            rows.append([c])
            bottom = c.y + c.h
    return rows


def _cards_to_bar(
    out: list[Placed], body: Rect, lt: LayoutTokens, bar: bool, anchored: bool, foot: bool
) -> list[Placed] | None:
    if not lt.l3_fill or not lt.cards_to_bar or lt.body_valign == "top" or body.h <= 0:
        return None
    if not (bar or (foot and anchored)):
        return None
    items = _body_items(out, body)
    boxes = [p for p in items if isinstance(p.element, Container)]
    cards = [p for p in boxes if not any(q is not p and _contains(q, p) for q in boxes)]
    if len(cards) < 2 or any("kpi" in c.element.classes for c in cards):
        return None
    plan: dict[int, list[Placed]] = {}
    for c in cards:
        inner = _inner_texts(c, items, deco=True)
        if inner is None:
            return None
        plan[id(c)] = inner
    covered = {id(p) for p in items if any(_contains(c, p) for c in cards)}
    if any(id(p) not in covered for p in items):  # arrows, charts, tables, loose text share the body
        return None
    rows = _card_rows(cards)
    nat = [max(c.h for c in r) for r in rows]
    gaps = [min(q.y for q in rows[i + 1]) - max(q.y + q.h for q in rows[i]) for i in range(len(rows) - 1)]
    if any(g < 0 for g in gaps):
        return None
    gap = min(gaps, default=0)
    top, bottom = body.y, body.bottom
    slack = (bottom - top) - sum(nat) - gap * (len(rows) - 1)
    if slack < 0:
        return None
    if not bar and (max(c.y + c.h for c in cards) - min(c.y for c in cards)) >= (bottom - top) * 0.97:
        return None
    heights = [h + slack // len(rows) for h in nat]
    heights[-1] += slack - (slack // len(rows)) * len(rows)
    tops = [top]
    for h in heights[:-1]:
        tops.append(tops[-1] + h + gap)
    tail_max = lt.l3_tail_max

    def run(s: float, hollow_cap: float | None):
        res: dict[int, Placed] = {}
        shares: list[float] = []
        for row, t, h in zip(rows, tops, heights, strict=True):
            rs = [_fill_card(c, plan[id(c)], t, t + h, lt, s) for c in row]
            if any(r is None for r in rs):
                return None
            sh = [r[2] / max(h, 1) for r in rs]
            if hollow_cap is not None and min(sh) < lt.card_hollow_fill:  # one larger rhythm for the row
                rs = [_fill_card(c, plan[id(c)], t, t + h, lt, s, False, None, hollow_cap) for c in row]
                if any(r is None for r in rs):
                    return None
            ex = [r[3] for r in rs]
            if max(ex) - min(ex) > 0.01:  # one rhythm for every card of the row
                cap = hollow_cap if hollow_cap is not None and min(sh) < lt.card_hollow_fill else None
                rs = [_fill_card(c, plan[id(c)], t, t + h, lt, s, False, min(ex), cap) for c in row]
                if any(r is None for r in rs):
                    return None
            sh = [r[2] / max(h, 1) for r in rs]
            for r in rs:
                res.update(r[0])
            shares += sh
        return res, shares, [1.0 - x for x in shares]

    r = run(1.0, None)
    if r is None:
        return None
    s_ok = 1.0
    s_top = min(_max_step(c, plan[id(c)], lt) for c in cards)
    k = 1
    while s_top > 1.0 + 1e-6 and max(r[2]) > tail_max:
        s = min(1.0 + k * lt.l3_grow_step, s_top)
        nxt = run(s, None)
        if nxt is None:
            break
        r, s_ok = nxt, s
        k += 1
        if s >= s_top:
            break
    if min(r[1]) < lt.card_hollow_fill:  # an obviously hollow card: its items spread further (token cap)
        nxt = run(s_ok, lt.card_hollow_gap_cap)
        if nxt is not None:
            r = nxt
    if min(r[1]) < lt.card_stretch_min_fill:  # even spread out, a card would stay a mostly empty box
        return None
    res = dict(r[0])
    if lt.card_spread_fill > 0:
        for row in rows:
            if min(_card_share(res, c, plan[id(c)]) for c in row) < lt.card_spread_fill:
                _distribute_row(res, row, plan, lt)
    for c in cards:  # decoration inside a card (icons, header bars) follows the card top
        dy = res[id(c)].y - c.y
        for p in items:
            if p is not c and id(p) not in res and _contains(c, p):
                res[id(p)] = p.model_copy(update={"y": p.y + dy})
    return _apply(out, res)


def _main_of(inner: list[Placed]) -> Placed | None:
    mains = [p for p in inner if p.element.role != "heading" and not _is_note(p)]
    return mains[0] if len(mains) == 1 else None


def _card_share(res: dict[int, Placed], card: Placed, inner: list[Placed]) -> float:
    """Share of the (placed) card its text ends at."""
    from .engine import _text_h

    c = res[id(card)]
    m = res.get(id(_main_of(inner)))
    return (m.y + _text_h(m) - c.y) / max(c.h, 1) if m is not None else 1.0


def _distribute_row(res: dict[int, Placed], row: list[Placed], plan: dict, lt: LayoutTokens) -> None:
    """Spread the paragraphs of every card of ``row`` over its body (equal gaps, capped); the rest is air
    above the first item, equal for the whole row so the first items share one y."""
    jobs = []
    for c in row:
        main = _main_of(plan[id(c)])
        if main is None or len(main.element.paragraphs) < 2:
            return
        m = res[id(main)]
        card = res[id(c)]
        pad = _pad(main, card)
        floor = card.y + card.h - pad
        for p in plan[id(c)]:
            if p is not main and _is_note(p) and p.element.role != "heading":
                floor = min(floor, res[id(p)].y - pad)
        tpad = _text_pad(m)
        width = m.w - 2 * tpad
        paras = m.element.paragraphs
        n = len(paras)
        size = (m.style.font_size or 18) * m.font_scale * EMU_PER_PT
        if size <= 0:
            return
        avail = floor - m.y - 2 * tpad - round(lt.card_spread_tail * size)
        g0 = m.element.attrs.get("para_gap")
        if g0 is None:
            g0 = measure.element_gap(m.element)
            g0 = measure.para_gap() if g0 is None else g0
        width = min(width, round(width * (1.0 - lt.l3_wrap_margin)))  # renders wrap earlier: fit that
        need = measure.paragraphs_height(paras, width, m.style, m.font_scale, gap=g0)
        free = avail - need
        if free <= 0:
            jobs.append((c, m, g0, 0, avail, paras, width))
            continue
        gap = min(g0 + free / ((n - 1) * size), lt.card_spread_gap_max)
        gap = max(gap, g0)
        for _ in range(12):  # the estimate has a safety factor: shrink until it surely fits
            used = measure.paragraphs_height(paras, width, m.style, m.font_scale, gap=gap)
            if used <= avail or gap <= g0:
                break
            gap = max(g0, gap - 0.05)
        used = measure.paragraphs_height(paras, width, m.style, m.font_scale, gap=gap)
        jobs.append((c, m, round(gap, 3), max(avail - used, 0), avail, paras, width))
    top_gap = min(j[2] for j in jobs) * lt.card_spread_ratio  # siblings keep a similar rhythm
    capped = []
    for c, m, g, rest, av, ps, w in jobs:
        if g > top_gap:
            g = top_gap
            rest = max(av - measure.paragraphs_height(ps, w, m.style, m.font_scale, gap=g), 0)
        capped.append((c, m, g, rest, av))
    jobs = capped
    lead = min(j[3] for j in jobs) // 2  # siblings share the first-item line
    for c, m, gap, _rest, _avail in jobs:
        el = m.element.model_copy(update={"attrs": {**m.element.attrs, "para_gap": gap}})
        res[id(_main_of(plan[id(c)]))] = m.model_copy(
            update={"element": el, "y": m.y + lead, "h": m.h - lead}
        )


def _fill_share(card: Placed, inner: list[Placed]) -> float:
    from .engine import _text_h

    return (max(p.y + _text_h(p) for p in inner) - card.y) / max(card.h, 1)


def fill_panels(
    out: list[Placed], body: Rect, lt: LayoutTokens, consulting: bool = False, title_scale: float = 1.2
) -> list[Placed]:
    """Text panels beside a chart / image: text grows, gaps stay even and capped, the panel shrinks to its
    content (a trailing note follows the text)."""
    try:
        return _fill_panels(out, body, lt, consulting, title_scale)
    except Exception:  # never raise on bad input
        return out


def _fill_panel(c: Placed, inner: list[Placed], lt: LayoutTokens, consulting: bool):
    """Geometry of one panel: grow the text (capped gaps), then shrink the panel to its content."""
    bottom = c.y + c.h
    r = _fill_card(c, inner, c.y, bottom, lt)
    if r is None:
        return None
    if not consulting:
        return r[0]
    tail_max = lt.l3_tail_max * c.h
    s_top = _max_step(c, inner, lt)
    k = 1
    while s_top > 1.0 + 1e-6 and r[1] > tail_max:
        s = min(1.0 + k * lt.l3_grow_step, s_top)
        nxt = _fill_card(c, inner, c.y, bottom, lt, s)
        if nxt is None:
            break
        r = nxt
        k += 1
        if s >= s_top:
            break
    res = r[0]
    if r[1] > tail_max:  # still sparse: the panel ends at its content (+ padding), not at the chart bottom
        pad = _pad(next(p for p in inner if p.element.role != "heading"), c)
        h = round(c.h - (r[1] - pad) * lt.l3_panel_shrink)
        s_ok = max(
            (
                res[id(p)].font_scale / p.font_scale
                for p in inner
                if id(p) in res and p.element.role != "heading"
            ),
            default=1.0,
        )
        nxt = _fill_card(c, inner, c.y, c.y + h, lt, s_ok)
        if nxt is not None:
            res = nxt[0]
    return res


def _align_plot(
    c: Placed,
    r: dict[int, Placed],
    items: list[Placed],
    visuals: list[Placed],
    lt: LayoutTokens,
    scale: float,
) -> dict[int, Placed]:
    """A panel that now ends after its content moves down so its top meets the plot area of the titled chart
    beside it (never the chart title); it stays inside the chart's height."""
    new = r[id(c)]
    if new.h >= c.h or lt.chart_plot_top_em <= 0:
        return r
    side = [
        v
        for v in visuals
        if isinstance(v.element, Chart)
        and v.element.title
        and (v.x + v.w <= c.x + 2 or c.x + c.w <= v.x + 2)
        and v.y <= c.y + 2
        and v.y + v.h >= c.y + c.h - 2
    ]
    if not side:
        return r
    v = side[0]
    title_pt = (v.style.font_size or 10.5) * v.font_scale * scale
    dy = round(v.y + lt.chart_plot_top_em * title_pt * EMU_PER_PT) - c.y
    if dy <= 0 or new.y + dy + new.h > v.y + v.h:
        return r
    out = {k: q.model_copy(update={"y": q.y + dy}) for k, q in r.items()}
    for q in items:  # decoration inside the panel (header bar, icon) follows it
        if q is not c and id(q) not in r and _contains(c, q):
            out[id(q)] = q.model_copy(update={"y": q.y + dy})
    return out


def _fill_panels(
    out: list[Placed], body: Rect, lt: LayoutTokens, consulting: bool, title_scale: float = 1.2
) -> list[Placed]:
    if not lt.l3_fill or lt.body_valign == "top" or body.h <= 0:
        return out
    items = _body_items(out, body)
    if not any(isinstance(p.element, (Chart, Image, Media)) for p in items):
        return out
    res: dict[int, Placed] = {}
    visuals = [p for p in items if isinstance(p.element, (Chart, Image, Media))]
    visual_h = max(p.h for p in visuals)
    for c in (p for p in items if isinstance(p.element, Container)):
        inner = _inner_texts(c, items)
        if inner is None or c.h < visual_h * 0.9 or _fill_share(c, inner) >= lt.panel_fill_min:
            continue
        r = _fill_panel(c, inner, lt, consulting)
        if r is not None:
            res.update(_align_plot(c, r, items, visuals, lt, title_scale) if consulting else r)
    return _apply(out, res) if res else out


def fill_chevron_row(out: list[Placed], body: Rect, lt: LayoutTokens) -> list[Placed]:
    """A lone chevron row is top-anchored right under the lead (never floating mid-slide)."""
    try:
        return _fill_chevron_row(out, body, lt)
    except Exception:  # never raise on bad input
        return out


def _fill_chevron_row(out: list[Placed], body: Rect, lt: LayoutTokens) -> list[Placed]:
    if not lt.l3_fill or lt.body_valign == "top" or body.h <= 0:
        return out
    items = _body_items(out, body)
    chevs = [p for p in items if isinstance(p.element, Shape) and p.element.shape == "chevron"]
    if len(chevs) < 2:
        return out
    ids = {id(c) for c in chevs}
    for p in items:  # only icons sitting on a chevron may share the body
        if id(p) not in ids and not (
            isinstance(p.element, Shape) and p.element.shape == "icon" and any(_contains(c, p) for c in chevs)
        ):
            return out
    if min(c.y + c.h for c in chevs) <= max(c.y for c in chevs):  # not one row
        return out
    res: dict[int, Placed] = {}
    top = min(c.y for c in chevs)
    h0 = max(c.h for c in chevs)
    if lt.sparse_left_max > 0 and body.bottom - (body.y + h0) > round(lt.sparse_left_max * body.h):
        grow = max(round(lt.chevron_fill_share * body.h) - h0, 0)
        if grow > body.bottom - (top + h0):  # never past the body
            grow = max(body.bottom - (top + h0), 0)
        dy = min(body.y - top, 0)
        if body.y - top < 0 or grow:
            for p in items:
                if (
                    id(p) in ids
                ):  # the point depth (adj x shorter side) stays, so the text area keeps its width
                    short = min(p.w, p.h)
                    adj = p.element.attrs.get("adj", lt.chevron_adj) * short / max(min(p.w, p.h + grow), 1)
                    el = p.element.model_copy(update={"attrs": {**p.element.attrs, "adj": round(adj, 4)}})
                    res[id(p)] = p.model_copy(update={"y": p.y + dy, "h": p.h + grow, "element": el})
                else:  # an icon stays centred on its chevron
                    res[id(p)] = p.model_copy(update={"y": p.y + dy + grow // 2})
    grown = _grow_chevron_text([res.get(id(c), c) for c in chevs], lt)
    if grown:
        res.update({id(c): g for c, g in zip(chevs, grown, strict=True)})
    return _apply(out, res) if res else out


def _grow_chevron_text(chevs: list[Placed], lt: LayoutTokens) -> list[Placed] | None:
    """Text of a lone chevron row grows to fill the chevron: one factor for the whole row, capped by
    ``chevron_text_max_pt`` and ``chevron_text_fill`` of the height. A word never breaks (it fits one line
    ``chevron_word_slack`` narrower) and no paragraph wraps onto more lines than it did (in an area
    ``chevron_cjk_slack`` / ``chevron_head_slack`` narrower). Rows with icons keep their size. ``None`` =
    unchanged."""
    from .engine import _chevron_text_w, _longest_word_em

    if lt.chevron_text_max_pt <= 0 or any("icon_side" in c.element.attrs for c in chevs):
        return None
    sizes = [(c.style.font_size or 18) * c.font_scale for c in chevs]
    s_top = min(lt.chevron_text_max_pt / max(sz, 1.0) for sz in sizes)
    step = max(lt.l3_grow_step, 0.01)

    def fits(s: float) -> bool:
        for c, sz in zip(chevs, sizes, strict=True):
            paras = c.element.paragraphs
            rect = Rect(c.x, c.y, c.w, c.h)
            adj = c.element.attrs.get("adj")
            avail = _chevron_text_w(rect, c.style, c.element, adj) / EMU_PER_PT
            if avail <= 0:
                return False
            new_fs = c.font_scale * s
            if measure.paragraphs_height(paras, round(avail * EMU_PER_PT), c.style, new_fs) > (
                lt.chevron_text_fill * c.h
            ):
                return False
            em = _longest_word_em(paras)
            if em * sz * s * lt.chevron_word_slack > avail:
                return False
            for i, para in enumerate(paras):
                cjk = measure.has_cjk(para.plain)
                slack = lt.chevron_cjk_slack if cjk else lt.chevron_head_slack
                segs = measure.para_segments(
                    para, i == 0 and bool(para.runs) and all(r.bold for r in para.runs)
                )
                narrow = avail / max(slack, 1.0)
                if measure.count_lines(segs, narrow, sz * s, c.style.font) > max(
                    measure.count_lines(segs, narrow, sz, c.style.font), 1
                ):
                    return False
        return True

    best = 1.0
    k = 1
    while True:
        s = min(1.0 + k * step, s_top)
        if s <= best + 1e-9 or not fits(s):
            break
        best = s
        k += 1
    if best <= 1.0 + 1e-9:
        return None
    return [c.model_copy(update={"font_scale": round(c.font_scale * best, 4)}) for c in chevs]
