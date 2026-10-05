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
    cap = min(cap, lt.l3_gap_cap)  # one even rhythm, never a stretched list
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
            sp = _spread(mg, avail - gap, lt, pad, s, short, cap_to)
            if sp is not None:
                m, avail = mg, avail - gap
    if sp is None:
        sp = _spread(m, avail, lt, pad, s, short, cap_to)
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
    if not lt.l3_fill or lt.sparse_left_max <= 0 or lt.body_valign == "top" or body.h <= 0:
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
    top = min(c.y for c in chevs)
    h0 = max(c.h for c in chevs)
    if body.bottom - (body.y + h0) <= round(lt.sparse_left_max * body.h):
        return out  # the row already fills the body (a conclusion bar may sit below it)
    grow = max(round(lt.chevron_fill_share * body.h) - h0, 0)
    if grow > body.bottom - (top + h0):  # never past the body
        grow = max(body.bottom - (top + h0), 0)
    dy = body.y - top
    if dy >= 0 and not grow:
        return out
    dy = min(dy, 0)
    res: dict[int, Placed] = {}
    for p in items:
        if id(p) in ids:  # the point depth (adj x shorter side) stays, so the text area keeps its width
            adj = p.element.attrs.get("adj", lt.chevron_adj) * min(p.w, p.h) / max(min(p.w, p.h + grow), 1)
            el = p.element.model_copy(update={"attrs": {**p.element.attrs, "adj": round(adj, 4)}})
            res[id(p)] = p.model_copy(update={"y": p.y + dy, "h": p.h + grow, "element": el})
        else:  # an icon stays centred on its chevron
            res[id(p)] = p.model_copy(update={"y": p.y + dy + grow // 2})
    return _apply(out, res)
