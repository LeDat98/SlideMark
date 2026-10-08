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

from ..ir import Chart, Container, Image, Media, Placed, Shape, Style, Table, Text
from ..theme import LayoutTokens
from ..units import EMU_PER_PT, to_emu
from . import css, kpirow, measure
from .grid import Rect
from .kpiunit import value_em
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


def _max_step(card: Placed, inner: list[Placed], lt: LayoutTokens, to_bar: bool = False) -> float:
    """Largest text growth factor a card's body text may take (explicit sizes never grow).

    ``to_bar``: cards stretched to a conclusion bar also respect ``card_text_max``."""
    heads = [p for p in inner if p.element.role == "heading"]
    mains = [p for p in inner if p.element.role != "heading" and not _is_note(p)]
    if len(mains) != 1 or getattr(mains[0].element, "style", None) and mains[0].element.style.font_size:
        return 1.0
    m = mains[0]
    pt = (m.style.font_size or 18) * m.font_scale
    cap = lt.l3_text_max_pt
    if to_bar and lt.card_text_max > 0:
        cap = min(cap, lt.card_text_max)
    if heads:
        hp = max((h.style.font_size or 18) * h.font_scale for h in heads)
        cap = min(cap, hp * lt.l3_body_head_max)
    return measure.grow_cap(lt, m.style.font_size, pt, cap) if pt > 0 else 1.0  # ... and layout.grow_max


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
    head_air: bool = True,
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
    if heads and head_air:  # air between the heading band and the first item
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
    bounded = any(isinstance(p.element, Table) for p in items)  # a table below: keep top, shrink only
    if not consulting and not all("kpi" in c.element.classes for c in cards):
        if not ((bounded and lt.card_table_balance) or (sparse and lt.sparse_cards_top)):
            return out  # normal-density themes keep their hugging cards (only KPI rows are top-anchored)
    if not sparse and not bounded:
        return out
    deco = bounded or not consulting
    plan: dict[int, list[Placed]] = {}
    for c in cards:
        inner = _inner_texts(c, items, deco=deco)
        if inner is None:
            return out
        plan[id(c)] = inner
    covered = {id(p) for ps in plan.values() for p in ps} | set(plan)
    if deco:  # decoration inside the cards (header bars, icons) is covered too
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
    top_only = not consulting and not bounded and not kpi  # normal density: top-anchored, same card height
    reach = full
    if top_only:  # cards keep their height (hugging); they may grow toward the completion's band target
        reach = min(full, body.bottom - round(lt.sparse_left_target * body.h) - top)
        full = max(c.h for c in cards)

    def run(h: int, s: float, short: bool):
        """(placed items, free heights, text ends) of every card at row height ``h``; ``None`` = refused."""
        air = True
        rs = [_fill_card(c, plan[id(c)], top, top + h, lt, s, short) for c in cards]
        if any(r is None for r in rs):
            return None
        starts = {  # first item of every card sits at the same offset below its heading band
            round((r[0][id(m)].y - c.y) / EMU_PER_PT)
            for c, r in zip(cards, rs, strict=True)
            for m in plan[id(c)]
            if m.element.role != "heading" and not _is_note(m) and id(m) in r[0]
        }
        if len(starts) > 1:  # one card could not take the heading air: none does
            air = False
            rs = [_fill_card(c, plan[id(c)], top, top + h, lt, s, short, head_air=False) for c in cards]
            if any(r is None for r in rs):
                return None
        extras = [r[3] for r in rs]
        if max(extras) - min(extras) > 0.01:  # one rhythm for every card of the row
            rs = [
                _fill_card(c, plan[id(c)], top, top + h, lt, s, short, min(extras), head_air=air)
                for c in cards
            ]
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
    if top_only:  # taller cards only while their emptiest card keeps its tail within the rule
        for k in range(1, 40):
            hh = round(full * (1.0 + 0.03 * k))
            if hh > reach:
                break
            nxt = run(hh, 1.0, False)
            if nxt is None or max(nxt[1]) > lt.l3_tail_max * hh:
                break
            r, h = nxt, hh
    tail_max = lt.l3_tail_max * full
    if (
        not kpi and not top_only and (max(r[1]) > tail_max or (bounded and not consulting))
    ):  # (a) grow the text (capped gaps), (c) shorter cards
        s_top = min(_max_step(c, plan[id(c)], lt) for c in cards) if consulting else 1.0
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
        if max(r[1]) > tail_max or (
            bounded and not consulting
        ):  # (c) the shortest row whose emptiest card keeps its tail within the limit
            nat = max(c.h for c in cards)
            if not consulting:  # table below, normal density: the cards hug their tallest content
                nat = min(nat, _hug_height(cards, plan, top, lt))
            h0 = max((full - max(r[1])) / (1.0 - lt.l3_tail_aim), nat)
            if not consulting:
                h0 = nat
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
    if deco:  # header bars / icons inside a card travel with it
        for c in cards:
            dy = top - c.y
            for p in items:
                if p is not c and id(p) not in res and _contains(c, p) and dy:
                    res[id(p)] = p.model_copy(update={"y": p.y + dy})
    if arrows:  # keep the arrows on the middle of the new card row
        old_mid = (min(c.y for c in cards) + old_bottom) / 2
        for a in arrows:
            res[id(a)] = a.model_copy(update={"y": round(top + h / 2 - (old_mid - a.y))})
    for p in tails:
        res[id(p)] = p.model_copy(update={"y": top + h + (p.y - old_bottom)})
    return _apply(out, res)


def _hug_height(cards: list[Placed], plan: dict[int, list[Placed]], top: int, lt: LayoutTokens) -> int:
    """Height of a card row that just holds the tallest card content: heading band, text, one inset below."""
    best = 0
    for c in cards:
        inner = plan[id(c)]
        main = [p for p in inner if p.element.role != "heading" and not _is_note(p)]
        if len(main) != 1:
            return max(x.h for x in cards)
        m = main[0]
        best = max(best, m.y + m.h + _pad(m, c) - c.y)
    return best


def fill_steps(out: list[Placed], body: Rect, lt: LayoutTokens, to_body: bool = False) -> list[Placed]:
    """``@steps``: the cards under the arrows grow down to the conclusion bar / footnote.

    The arrows stay where they are; the cards are stretched like any card row above a bar (text grows up to
    ``card_text_max``, items spread, never a mostly empty box). Nothing else may share the body under the
    arrows. ``to_body`` (small-body themes, ``steps_to_body``): a sparse group fills the body (see
    ``_compose_steps``). Never raises: anything unexpected returns the items."""
    try:
        return _fill_steps(out, body, lt, to_body)
    except Exception:
        return out


def _is_step_arrow(p: Placed) -> bool:
    return isinstance(p.element, Shape) and str(p.element.attrs.get("shape_name", "")).endswith(" arrow")


def _fill_steps(out: list[Placed], body: Rect, lt: LayoutTokens, to_body: bool = False) -> list[Placed]:
    if not lt.l3_fill or not lt.steps_stretch or not lt.cards_to_bar or body.h <= 0:
        return out
    items = _body_items(out, body)
    arrows = [p for p in items if _is_step_arrow(p)]
    cards = [p for p in items if isinstance(p.element, Container) and "steps-card" in p.element.classes]
    if not arrows or len(cards) < 2:
        return out
    rest = [
        p for p in items if not _is_step_arrow(p) and all(p is not c and not _contains(c, p) for c in cards)
    ]
    if any(p.y >= min(c.y for c in cards) - 2 for p in rest):
        return out  # a table / chart under the cards shares the body: they keep their height
    dy = body.y - min(a.y for a in arrows)  # top-anchored, right under the lead
    arrow_icons = _arrow_icons(
        [p for p in out if isinstance(p.element, Shape) and p.element.shape == "icon"], arrows
    )
    moved = {id(p): p.model_copy(update={"y": p.y + dy}) for p in items} if dy else {}
    if dy:  # (an icon sits on its arrow and travels with it, even when it pokes out of the body rectangle)
        moved.update({id(ic): ic.model_copy(update={"y": ic.y + dy}) for ic in arrow_icons.values()})
    out = [moved.get(id(p), p) for p in out]
    arrows = [moved.get(id(p), p) for p in arrows]
    glyphs = {id(moved.get(id(ic), ic)) for ic in arrow_icons.values()}
    top = min(moved.get(id(c), c).y for c in cards)
    up = top - (
        max(a.y + a.h for a in arrows) + to_emu(lt.steps_gap)
    )  # the sparse passes may have spread them
    if up > 0:
        shifted = {
            id(p): p.model_copy(update={"y": p.y - up})
            for p in out
            if not _is_step_arrow(p) and id(p) not in glyphs
        }
        out = [shifted.get(id(p), p) for p in out]
        top -= up
    keep = [p for p in out if not _is_step_arrow(p)]
    full = body.bottom - top
    step = max(lt.steps_stretch_step, 0.05)
    low = lt.steps_stretch_min
    shares = [1.0, *(round(1.0 - k * step, 3) for k in range(1, 20) if 1.0 - k * step >= low)]
    for share in shares:  # as far as the content keeps the cards from looking hollow
        res = _cards_to_bar(keep, Rect(body.x, top, body.w, round(full * share)), lt, True, True, False, True)
        if res is not None:
            new = {id(old): nw for old, nw in zip(keep, res, strict=False)}
            out = [new.get(id(p), p) for p in out] + res[len(keep) :]
            break
    out = _grow_step_arrows(out, arrows, lt)
    return _compose_steps(out, body, lt, to_body)


def _compose_steps(out: list[Placed], body: Rect, lt: LayoutTokens, to_body: bool = False) -> list[Placed]:
    """A sparse steps group (a few short bullets) uses the body: bigger text, taller arrows, centred.

    Only when the group (arrows to card bottoms) covers less than ``steps_sparse_below`` of the body and
    every card holds one text of at most ``steps_sparse_items`` paragraphs. Card text grows first (up to
    ``steps_text_max_pt``, never onto a new wrapped line), then the arrows (label up to
    ``steps_arrow_text_max_pt``, never wrapped) and the card height (``steps_sparse_fill`` of the body, a
    card at most ``steps_card_max_aspect`` x its width tall, text centred in it); the group sits with
    ``steps_top_share`` of the leftover height above it. Dense steps are left as they are.

    ``to_body`` (``steps_to_body``, small-body themes): the group fills ``steps_to_body_fill`` of the body,
    cards up to ``steps_to_body_aspect`` x their width tall, text up to ``steps_to_body_text_max_pt``, the
    group sitting with ``steps_to_body_top`` of the leftover above it."""
    if not lt.steps_sparse or body.h <= 0:
        return out
    to_body = to_body and lt.steps_to_body and lt.body_valign != "top"
    fill = lt.steps_to_body_fill if to_body else lt.steps_sparse_fill
    aspect = lt.steps_to_body_aspect if to_body else lt.steps_card_max_aspect
    text_max = lt.steps_to_body_text_max_pt if to_body else lt.steps_text_max_pt
    top_share = lt.steps_to_body_top if to_body else lt.steps_top_share
    items = _body_items(out, body)
    arrows = [p for p in items if _is_step_arrow(p)]
    cards = [p for p in items if isinstance(p.element, Container) and "steps-card" in p.element.classes]
    if not arrows or not cards:
        return out
    inner: dict[int, Placed] = {}
    for c in cards:
        texts = [p for p in items if p is not c and _contains(c, p) and not _is_rule(p)]
        if len(texts) != 1 or not isinstance(texts[0].element, Text) or texts[0].style.font_size is None:
            return out
        n_items = sum(1 for q in texts[0].element.paragraphs if not q.attrs.get("_caption"))
        if n_items > lt.steps_sparse_items or texts[0].element.box is not None:
            return out
        inner[id(c)] = texts[0]
    icon_of = _arrow_icons(items, arrows)
    other = [
        p
        for p in items
        if not _is_step_arrow(p)
        and not _is_rule(p)
        and p not in cards
        and p not in inner.values()
        and all(p is not ic for ic in icon_of.values())
    ]
    if other:
        return out  # something else (a table under the cards) shares the body
    top0 = min(a.y for a in arrows)
    bottom0 = max(c.y + c.h for c in cards)
    if (bottom0 - top0) >= (fill if to_body else lt.steps_sparse_below) * body.h:
        return out
    mains = list(inner.values())
    pad_v = max(min(m.y - c.y for c, m in zip(cards, mains, strict=True)), 0)
    # 1. card text: the largest common growth that wraps nothing new and stays under the cap
    cur_pt = max(m.style.font_size * m.font_scale for m in mains)  # type: ignore[operator]
    s_top = measure.grow_cap(lt, max(m.style.font_size for m in mains), cur_pt, text_max)  # ... and grow_max
    step = max(lt.l3_grow_step, 0.01)
    best, k = 1.0, 1
    while True:
        s = min(1.0 + k * step, s_top)
        if s <= best + 1e-9 or any(_spread(m, 10**9, lt, _text_pad(m), s) is None for m in mains):
            break
        best, k = s, k + 1
    grown = {id(m): m.model_copy(update={"font_scale": round(m.font_scale * best, 4)}) for m in mains}
    # 2. arrows: taller for their text, label grown (no new wrap) to at least the card text x the ratio
    arrow_pt = max(
        min((a.style.font_size or 18) * a.font_scale for a in arrows),
        cur_pt * best * lt.steps_arrow_text_ratio,
    )
    arrow_pt = min(arrow_pt, lt.steps_arrow_text_max_pt)
    h_now = max(a.h for a in arrows)
    h_arrow = min(
        max(h_now, round(lt.steps_arrow_h_em * arrow_pt * EMU_PER_PT)), to_emu(lt.steps_arrow_sparse_max_h)
    )
    new_arrows = [_resize_chevron(a, 0, h_arrow - a.h, lt) if h_arrow != a.h else a for a in arrows]
    cap = lt.model_copy(
        update={"chevron_text_max_pt": arrow_pt, "chevron_text_fill": lt.steps_arrow_text_fill}
    )
    ga = _grow_chevron_text(new_arrows, cap, strict=True, icons=True)
    if ga:
        new_arrows = ga
    # 3. card height: the share of the body the group should cover, not taller than its width allows
    gap = to_emu(lt.steps_gap)
    text_h = max(
        measure.paragraphs_height(
            g.element.paragraphs,
            g.w - 2 * _text_pad(g),
            g.style,
            g.font_scale,
            gap=measure.element_gap(g.element),
        )
        for g in grown.values()
    )
    colw = min(c.w for c in cards)
    want = round(fill * body.h) - h_arrow - gap
    card_h = max(round(text_h + 2 * _text_pad(mains[0]) + 2 * pad_v), min(want, round(aspect * colw)))
    group_h = h_arrow + gap + card_h
    if group_h > body.h:
        return out
    top = body.y + round((body.h - group_h) * min(max(top_share, 0.0), 1.0))
    res: dict[int, Placed] = {}
    for a, na in zip(arrows, new_arrows, strict=True):
        placed = na.model_copy(update={"y": top})
        if (ic := icon_of.get(id(a))) is not None:  # the icon follows its arrow (size, place)
            placed, res[id(ic)] = _icon_arrow(placed, ic, lt)
        res[id(a)] = placed
    ctop = top + h_arrow + gap
    for c in cards:
        m = inner[id(c)]
        res[id(c)] = c.model_copy(update={"y": ctop, "h": card_h})
        g = grown[id(m)]
        el = g.element.model_copy(
            update={"attrs": {k: v for k, v in g.element.attrs.items() if k != "para_gap"}}
        )
        own = getattr(c.element, "style", None)  # `## a {valign=top}` on the step: the author's anchor wins
        res[id(m)] = g.model_copy(
            update={
                "y": ctop + pad_v,
                "h": card_h - 2 * pad_v,
                "element": el,
                "style": g.style.model_copy(update={"valign": (own.valign if own else None) or "middle"}),
            }
        )
    inside = [p for p in items if _is_rule(p)]
    return [res.get(id(p), p) for p in out if p not in inside]


def _is_rule(p: Placed) -> bool:
    return isinstance(p.element, Shape) and p.element.shape == "line"


def _grow_step_arrows(out: list[Placed], arrows: list[Placed], lt: LayoutTokens) -> list[Placed]:
    """The arrow headings are at least as large as the card text (x ``steps_arrow_text_ratio``)."""
    if lt.steps_arrow_text_ratio <= 0:
        return out
    inner = [
        p
        for p in out
        if isinstance(p.element, Text) and p.element.role == "body" and p.style.font_size is not None
    ]
    if not inner:
        return out
    card_pt = max(p.style.font_size * p.font_scale for p in inner)  # type: ignore[operator]
    want = card_pt * lt.steps_arrow_text_ratio
    now = min((a.style.font_size or 18) * a.font_scale for a in arrows)
    if want <= now * 1.02:
        return out
    cap = lt.model_copy(update={"chevron_text_max_pt": want, "chevron_text_fill": lt.steps_arrow_text_fill})
    grown = _grow_chevron_text(arrows, cap, strict=True, icons=True)
    if not grown:
        return out
    swap = {id(c): g for c, g in zip(arrows, grown, strict=True)}
    icon_of = _arrow_icons(
        [p for p in out if isinstance(p.element, Shape) and p.element.shape == "icon"], arrows
    )
    for a, g in zip(arrows, grown, strict=True):
        if (ic := icon_of.get(id(a))) is not None:
            swap[id(a)], swap[id(ic)] = _icon_arrow(g, ic, lt)
    return [swap.get(id(p), p) for p in out]


def _arrow_icons(items: list[Placed], arrows: list[Placed]) -> dict[int, Placed]:
    """``id(arrow) -> its icon``: the glyph an ``icon=`` heading draws inside a step arrow."""
    out: dict[int, Placed] = {}
    for a in arrows:
        for p in items:
            if isinstance(p.element, Shape) and p.element.shape == "icon" and _contains(a, p):
                out[id(a)] = p
                break
    return out


def _icon_arrow(a: Placed, ic: Placed, lt: LayoutTokens) -> tuple[Placed, Placed]:
    """The arrow ``a`` and its icon ``ic`` after the arrow's size or text size changed: the icon side follows
    the label (``icon_head`` x its size, at most 40% of the height) and sits before the centred text block,
    as the first layout placed it."""
    from .engine import _chevron_text_w, _pad

    size_pt = (a.style.font_size or 18) * a.font_scale
    side = min(round(lt.icon_head * size_pt * EMU_PER_PT), round(0.4 * a.h))
    attrs = {**a.element.attrs, "icon_side": side, "icon_inset": side + round(lt.icon_gap * side)}
    a2 = a.model_copy(update={"element": a.element.model_copy(update={"attrs": attrs})})
    adj = attrs.get("adj", lt.chevron_adj)
    avail = _chevron_text_w(Rect(a2.x, a2.y, a2.w, a2.h), a2.style, a2.element, adj)
    line = max(
        (measure.text_em(q.plain, bold=True) * size_pt * EMU_PER_PT for q in a2.element.paragraphs), default=0
    )
    left = a2.x + round(adj * min(a2.w, a2.h)) + _pad(a2.style)
    off = max(round((avail - min(line, avail)) / 2), 0)
    return a2, ic.model_copy(update={"x": left + off, "y": a2.y + (a2.h - side) // 2, "w": side, "h": side})


def fill_cards_to_bar(
    out: list[Placed],
    body: Rect,
    lt: LayoutTokens,
    bar: bool,
    anchored: bool,
    foot: bool,
    to_body: bool = False,
) -> list[Placed] | None:
    """A body of text cards (one row or a grid) above a conclusion bar: top-anchored, stretched to the bar.

    ``None`` = not this case (caller continues with the other fills). Applies with a conclusion bar, or with
    a footnote when the block is already top-anchored (``anchored``). ``to_body`` (small-body themes): cards
    alone on a sparse slide stretch down the body without a bar (``_cards_to_body``)."""
    try:
        return _cards_to_bar(out, body, lt, bar, anchored, foot, False, to_body)
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


def _cap_card_text(plan: dict[int, list[Placed]], lt: LayoutTokens) -> dict[int, Placed]:
    """Body text of the cards that grew beyond ``card_text_max`` (pt), back at that size.

    Never below the theme size (font scale 1) and never larger than it is; explicit sizes are left alone."""
    caps: dict[int, Placed] = {}
    if lt.card_text_max <= 0:
        return caps
    for inner in plan.values():
        m = _main_of(inner)
        if m is None or (getattr(m.element, "style", None) and m.element.style.font_size):
            continue
        pt = (m.style.font_size or 18) * m.font_scale
        if pt <= lt.card_text_max + 0.01 or m.style.font_size is None:
            continue
        fs = max(lt.card_text_max / m.style.font_size, min(m.font_scale, 1.0))
        if fs < m.font_scale - 1e-6:
            caps[id(m)] = m.model_copy(update={"font_scale": round(fs, 4)})
    return caps


def _cards_to_body(
    out: list[Placed], body: Rect, lt: LayoutTokens, force: bool = False
) -> list[Placed] | None:
    """Text cards alone on a slide (no bar to stretch to) that leave much of the body empty.

    The cards stretch down the body like cards above a bar, as far as their content keeps them from looking
    hollow: the share of the body height is tried from the full height down (``cards_to_body_min`` in steps of
    ``cards_to_body_step``); text grows up to ``card_fill_text_max_pt`` and the items spread inside."""
    if not lt.cards_to_body or lt.card_fill_text_max_pt <= 0:
        return None
    items = _body_items(out, body)
    boxes = [p for p in items if isinstance(p.element, Container)]
    cards = [p for p in boxes if not any(q is not p and _contains(q, p) for q in boxes)]
    if len(cards) < 2 or any("kpi" in c.element.classes for c in cards):
        return None
    if any(not any(q is p or _contains(q, p) for q in cards) for p in items):
        return None  # a table / chart / loose text shares the body: the cards keep their height
    free = (min(c.y for c in cards) - body.y) + (body.bottom - max(c.y + c.h for c in cards))
    if free <= lt.cards_to_body_free * body.h:
        return None
    lt2 = lt.model_copy(
        update={
            "card_text_max": lt.card_fill_text_max_pt,
            "l3_text_max_pt": max(lt.l3_text_max_pt, lt.card_fill_text_max_pt),
            "card_stretch_min_fill": max(lt.card_stretch_min_fill, lt.cards_to_body_fill),
        }
    )
    air = to_emu(lt.cards_to_body_air)
    step = max(lt.cards_to_body_step, 0.02)
    k = 0
    while True:
        share = round(1.0 - k * step, 3)
        if share < lt.cards_to_body_min - 1e-9:
            return None
        res = _cards_to_bar(
            out, Rect(body.x, body.y, body.w, round(body.h * share) - air), lt2, True, True, False, force
        )
        if res is not None:
            return res
        k += 1


def _cards_to_bar(
    out: list[Placed],
    body: Rect,
    lt: LayoutTokens,
    bar: bool,
    anchored: bool,
    foot: bool,
    force: bool = False,
    to_body: bool = False,
) -> list[Placed] | None:
    if not lt.l3_fill or not lt.cards_to_bar or (lt.body_valign == "top" and not force) or body.h <= 0:
        return None
    if not (bar or (foot and anchored)):
        return _cards_to_body(out, body, lt, force) if to_body else None
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
    caps = _cap_card_text(plan, lt)
    if caps:  # growth stays within card_text_max: the stretch below spreads the (now shorter) text
        out = _apply(out, caps)
        items = _apply(items, caps)
        plan = {k: _apply(v, caps) for k, v in plan.items()}
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
    s_top = min(_max_step(c, plan[id(c)], lt, True) for c in cards)
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
    rules: list[Placed] = []
    if lt.card_spread_fill > 0:
        for row in rows:
            if min(_card_share(res, c, plan[id(c)]) for c in row) < lt.card_spread_fill:
                rules += _distribute_row(res, row, plan, lt, align=True)
    for c in cards:  # decoration inside a card (icons, header bars) follows the card top
        dy = res[id(c)].y - c.y
        for p in items:
            if p is not c and id(p) not in res and _contains(c, p):
                res[id(p)] = p.model_copy(update={"y": p.y + dy})
    return _apply(out, res) + rules


def _main_of(inner: list[Placed]) -> Placed | None:
    mains = [p for p in inner if p.element.role != "heading" and not _is_note(p)]
    return mains[0] if len(mains) == 1 else None


def _card_share(res: dict[int, Placed], card: Placed, inner: list[Placed]) -> float:
    """Share of the (placed) card its text ends at."""
    from .engine import _text_h

    c = res[id(card)]
    m = res.get(id(_main_of(inner)))
    return (m.y + _text_h(m) - c.y) / max(c.h, 1) if m is not None else 1.0


def _distribute_row(
    res: dict[int, Placed],
    row: list[Placed],
    plan: dict,
    lt: LayoutTokens,
    follow: bool = False,
    align: bool = False,
) -> list[Placed]:
    """Spread the paragraphs of every card of ``row`` over its body (equal gaps, capped).

    With ``card_spread_rules`` the items form a ruled list: every item sits in its own band (half a gap
    above and below), a thin rule in the gap centre separates consecutive items, and the cards of the row
    keep a similar rhythm. Otherwise the list stays top-anchored (first items share one y), the rest is air
    at the card bottom. Returns the rule shapes (empty without ``card_spread_rules``).

    ``follow`` (a panel beside a chart): the gap is capped at ``card_spread_gap_max`` em (the cards' ruled cap
    is twice that), the list starts half a gap under the heading and a trailing note / callout follows the
    last item one padding below it; the leftover air goes under the note (the panel keeps its height).

    ``align`` (cards side by side, ``card_align_rows``): every card takes the smallest gap of the row and
    the smallest lead, so item ``k`` and rule ``k`` sit at the same height in every card; a card with fewer
    items just ends earlier."""
    ruled = lt.card_spread_rules
    jobs = []
    for c in row:
        main = _main_of(plan[id(c)])
        if main is None or len(main.element.paragraphs) < 2:
            return []
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
            return []
        avail = floor - m.y - 2 * tpad - round(lt.card_spread_tail * size)
        g0 = m.element.attrs.get("para_gap")
        if g0 is None:
            g0 = measure.element_gap(m.element)
            g0 = measure.para_gap() if g0 is None else g0
        true_w = width  # rules and the centring use the real wrap width, the fit the narrower one
        width = min(width, round(width * (1.0 - lt.l3_wrap_margin)))  # renders wrap earlier: fit that
        need = measure.paragraphs_height(paras, width, m.style, m.font_scale, gap=g0)
        free = avail - need
        if free <= 0:
            jobs.append((c, m, g0, 0, avail, paras, width, card, pad, tpad, true_w))
            continue
        # ruled: n bands (half a gap above the first and below the last item); plain: n - 1 gaps
        gap = min(
            g0 + free / ((n if ruled else n - 1) * size),
            lt.card_spread_gap_max * (2 if ruled and not follow else 1),
        )
        gap = max(gap, g0)
        for _ in range(12):  # the estimate has a safety factor: shrink until it surely fits
            used = measure.paragraphs_height(paras, width, m.style, m.font_scale, gap=gap)
            if used <= avail or gap <= g0:
                break
            gap = max(g0, gap - 0.05)
        used = measure.paragraphs_height(paras, width, m.style, m.font_scale, gap=gap)
        jobs.append((c, m, round(gap, 3), max(avail - used, 0), avail, paras, width, card, pad, tpad, true_w))
    shared = align and ruled and not follow and lt.card_align_rows and len(jobs) > 1
    top_gap = min(j[2] for j in jobs) * (1.0 if shared else lt.card_spread_ratio)  # similar rhythm
    rules: list[Placed] = []
    line = Style(line="border", line_width=0.75)

    def lead_of(g: float, m, av: int, ps, tw: int) -> int:
        used = measure.paragraphs_height(ps, tw, m.style, m.font_scale, gap=g)
        lead = max(round((av - used) / 2), 0)  # centred in the card body: equal air above and below
        if follow:
            lead = min(lead, round(g * (m.style.font_size or 18) * m.font_scale * EMU_PER_PT / 2))
        return lead

    shared_lead = (
        min(lead_of(min(j[2], top_gap), j[1], j[4], j[5], j[10]) for j in jobs)
        if shared and top_gap > 0
        else None
    )
    for c, m, g, _rest, av, ps, _w, card, pad, tpad, tw in jobs:
        if g > top_gap:
            g = top_gap
        el = m.element.model_copy(update={"attrs": {**m.element.attrs, "para_gap": g}})
        lead = 0
        if ruled and g > 0:
            used = measure.paragraphs_height(ps, tw, m.style, m.font_scale, gap=g)
            lead = lead_of(g, m, av, ps, tw) if shared_lead is None else shared_lead
            size = (m.style.font_size or 18) * m.font_scale * EMU_PER_PT
            for i in range(len(ps) - 1):
                end = measure.paragraphs_height(ps[: i + 1], tw, m.style, m.font_scale, gap=g)
                y = m.y + lead + tpad + round(end + g * size / 2)
                rules.append(_rule(card, pad, y, line))
        res[id(_main_of(plan[id(c)]))] = m.model_copy(
            update={"element": el, "y": m.y + lead, "h": m.h - lead}
        )
        if follow and ruled and g > 0:
            _follow_notes(res, plan[id(c)], m.y + lead + tpad + used, g, m, pad)
            q = res[id(_main_of(plan[id(c)]))]  # the text box ends with its text, the note starts below it
            res[id(_main_of(plan[id(c)]))] = q.model_copy(update={"h": min(q.h, round(used + 2 * tpad))})
    return rules


def _follow_notes(
    res: dict[int, Placed], inner: list[Placed], end: int, gap: float, main: Placed, pad: int
) -> None:
    """Move the trailing notes of a panel up so the first one starts ``pad`` (+ half a gap) below ``end``."""
    notes = [res.get(id(p), p) for p in inner if p.element.role != "heading" and _is_note(p)]
    if not notes:
        return
    top = min(q.y for q in notes)
    half = round(gap * (main.style.font_size or 18) * main.font_scale * EMU_PER_PT / 2)
    dy = min(round(end + pad + half - top), 0)  # never lower than the bottom-anchored position
    if dy:
        for p in inner:
            if p.element.role != "heading" and _is_note(p):
                q = res.get(id(p), p)
                res[id(p)] = q.model_copy(update={"y": q.y + dy})


def _rule(card: Placed, pad: int, y: int, style: Style) -> Placed:
    """A thin horizontal rule inside ``card`` (native line shape), inset by the card padding."""
    return Placed(
        element=Shape(id="Rule", shape="line", attrs={"head": "none", "flip_h": False, "flip_v": False}),
        x=card.x + pad,
        y=y,
        w=max(card.w - 2 * pad, 0),
        h=0,
        style=style,
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


def _panel_span(c: Placed, visuals: list[Placed], lt: LayoutTokens, scale: float) -> tuple[int, int] | None:
    """``(top, bottom)`` a panel takes beside a visual that spans it: the top meets the plot area of a titled
    chart (the visual's top otherwise), the bottom is the visual's bottom."""
    side = [
        v
        for v in visuals
        if (v.x + v.w <= c.x + 2 or c.x + c.w <= v.x + 2) and v.y <= c.y + 2 and v.y + v.h >= c.y + c.h - 2
    ]
    if not side:
        return None
    v = side[0]
    top = v.y
    if lt.panel_top_plot and isinstance(v.element, Chart) and v.element.title and lt.chart_plot_top_em > 0:
        title_pt = (v.style.font_size or 10.5) * v.font_scale * scale
        top = max(top, round(v.y + lt.chart_plot_top_em * title_pt * EMU_PER_PT))
    return (top, v.y + v.h) if v.y + v.h - top > c.h * 0.5 else None


def _fill_panel_span(
    c: Placed, inner: list[Placed], lt: LayoutTokens, top: int, bottom: int
) -> tuple[dict[int, Placed], list[Placed]] | None:
    """A panel stretched over ``top..bottom`` (the visual beside it): the text grows first, the gaps spread
    (ruled list when the panel stays hollow). ``None`` when the content would fill less than
    ``card_hollow_fill`` of the span: the panel then ends at its content (``_fill_panel``)."""
    r = _fill_card(c, inner, top, bottom, lt)
    if r is None:
        return None
    full = bottom - top
    s_top = _max_step(c, inner, lt)
    k = 1
    while s_top > 1.0 + 1e-6 and r[1] > lt.l3_tail_max * full:
        s = min(1.0 + k * lt.l3_grow_step, s_top)
        nxt = _fill_card(c, inner, top, bottom, lt, s)
        if nxt is None:
            break
        r = nxt
        k += 1
        if s >= s_top:
            break
    notes = sum(p.h for p in inner if p.element.role != "heading" and _is_note(p))
    if (r[2] + notes) / max(full, 1) < lt.card_hollow_fill:  # text + trailing note vs the span
        return None
    res = dict(r[0])
    rules: list[Placed] = []
    if lt.card_spread_fill > 0 and _card_share(res, c, inner) < lt.card_spread_fill:
        rules = _distribute_row(res, [c], {id(c): inner}, lt, follow=True)
        _end_at_note(res, c, inner, lt, bottom - top)
    return res, rules


def _end_at_note(res: dict[int, Placed], c: Placed, inner: list[Placed], lt: LayoutTokens, full: int) -> None:
    """A ruled panel whose trailing note follows the list ends one padding below that note when the rest
    of its span would stay empty (``panel_end_air`` to ``panel_end_max``): it lines up with the chart plot,
    not its legend. A much emptier panel keeps the chart span (a shrunk one would leave a hole)."""
    notes = [res[id(p)] for p in inner if p.element.role != "heading" and _is_note(p) and id(p) in res]
    if lt.panel_end_air <= 0 or not notes or id(c) not in res:
        return
    card = res[id(c)]
    end = max(q.y + q.h for q in notes) + _pad(notes[0], card)
    if lt.panel_end_air * full < card.y + card.h - end <= lt.panel_end_max * full:
        res[id(c)] = card.model_copy(update={"h": end - card.y})


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
    panel_rules: list[Placed] = []
    for c in (p for p in items if isinstance(p.element, Container)):
        inner = _inner_texts(c, items)
        if inner is None or c.h < visual_h * 0.9 or _fill_share(c, inner) >= lt.panel_fill_min:
            continue
        if consulting and lt.panel_to_visual:
            span = _panel_span(c, visuals, lt, title_scale)
            if span is not None:
                got = _fill_panel_span(c, inner, lt, *span)
                if got is not None:
                    res.update(got[0])
                    panel_rules += got[1]
                    continue
        r = _fill_panel(c, inner, lt, consulting)
        if r is not None:
            res.update(_align_plot(c, r, items, visuals, lt, title_scale) if consulting else r)
    rules = panel_rules + _spread_stack(items, visuals, res, lt)
    return _apply(out, res) + rules if res or rules else out


def _spread_stack(
    items: list[Placed], visuals: list[Placed], res: dict[int, Placed], lt: LayoutTokens
) -> list[Placed]:
    """Hollow cards stacked in a column beside a chart / image (together as tall as the visual): their items
    are spread like cards above a conclusion bar (ruled list, siblings share one rhythm). Cards that are
    ``card_spread_fill`` full keep their layout. Fills ``res``; returns the rule shapes."""
    if lt.card_spread_fill <= 0:
        return []
    rules: list[Placed] = []
    for v in visuals:
        col = [
            c
            for c in items
            if isinstance(c.element, Container)
            and id(c) not in res
            and "kpi" not in c.element.classes
            and (v.x + v.w <= c.x + 2 or c.x + c.w <= v.x + 2)
            and c.y >= v.y - 2
            and c.y + c.h <= v.y + v.h + 2
        ]
        col = [c for c in col if not any(q is not c and _contains(q, c) for q in col)]
        if len(col) < 2 or any(abs(c.x - col[0].x) > 2 or abs(c.w - col[0].w) > 2 for c in col):
            continue
        col.sort(key=lambda c: c.y)
        if sum(c.h for c in col) < v.h * 0.8 or any(
            col[i + 1].y < col[i].y + col[i].h - 2 for i in range(len(col) - 1)
        ):
            continue
        plan = {id(c): _inner_texts(c, items, deco=True) for c in col}
        if any(inner is None for inner in plan.values()):
            continue
        local: dict[int, Placed] = {}
        for c in col:
            r = _fill_card(c, plan[id(c)], c.y, c.y + c.h, lt)
            if r is None:
                local = {}
                break
            local.update(r[0])
        if not local or min(_card_share(local, c, plan[id(c)]) for c in col) >= lt.card_spread_fill:
            continue
        new_rules = _distribute_row(local, col, plan, lt)
        if not new_rules:
            continue
        for c in col:  # decoration inside a card (icons, header bars) keeps its place
            for q in items:
                if q is not c and id(q) not in local and _contains(c, q):
                    local[id(q)] = q
        res.update(local)
        rules += new_rules
    return rules


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
        want = round(lt.chevron_fill_share * body.h)
        if lt.chevron_lone_h > 0:  # taller, up to a share of the body and an aspect of the chevron width
            wide = (
                round(lt.chevron_lone_aspect * min(c.w for c in chevs)) if lt.chevron_lone_aspect > 0 else 0
            )
            want = max(want, min(round(lt.chevron_lone_h * body.h), wide or want))
        want = _lone_chevron_cap(chevs, want, lt)
        grow = want - h0 if want < h0 else max(want - h0, 0)
        if grow > body.bottom - (top + h0):  # never past the body
            grow = max(body.bottom - (top + h0), 0)
        dy = min(body.y - top, 0)
        if lt.chevron_lone_top > 0:  # the leftover is split (optical center), not left as a dead lower half
            left = body.bottom - (body.y + h0 + grow)
            dy = body.y - top + round(max(left, 0) * min(lt.chevron_lone_top, 1.0))
        if dy or grow:
            for p in items:
                if id(p) in ids:
                    res[id(p)] = _resize_chevron(p, dy, grow, lt)
                else:  # an icon stays centred on its chevron
                    res[id(p)] = p.model_copy(update={"y": p.y + dy + grow // 2})
    grown = _grow_chevron_text([res.get(id(c), c) for c in chevs], lt)
    if grown:
        res.update({id(c): g for c, g in zip(chevs, grown, strict=True)})
    return _apply(out, res) if res else out


def _lone_chevron_cap(chevs: list[Placed], want: int, lt: LayoutTokens) -> int:
    """A lone chevron row is never taller than ``chevron_lone_cap_aspect`` x its chevron width nor
    ``chevron_lone_cap_text`` x its text block (no giant arrows around two small lines); never below what
    its text needs."""
    cap, floor = want, 0
    if lt.chevron_lone_cap_aspect > 0:
        cap = min(cap, round(lt.chevron_lone_cap_aspect * min(c.w for c in chevs)))
    if lt.chevron_lone_cap_text > 0:
        text = max(
            measure.paragraphs_height(c.element.paragraphs, max(round(0.6 * c.w), 1), c.style, c.font_scale)
            for c in chevs
        )
        cap = min(cap, round(lt.chevron_lone_cap_text * text))
        floor = round(text / max(lt.chevron_text_fill, 0.3))  # the text keeps its share of the height
    return max(cap, floor)


def _resize_chevron(p: Placed, dy: int, grow: int, lt: LayoutTokens) -> Placed:
    """Move chevron ``p`` by ``dy`` and make it ``grow`` taller. The point depth (adj x shorter side) stays,
    so the text area keeps its width."""
    short = min(p.w, p.h)
    adj = p.element.attrs.get("adj", lt.chevron_adj) * short / max(min(p.w, p.h + grow), 1)
    el = p.element.model_copy(update={"attrs": {**p.element.attrs, "adj": round(adj, 4)}})
    return p.model_copy(update={"y": p.y + dy, "h": p.h + grow, "element": el})


def align_chevron_table(out: list[Placed], body: Rect, lt: LayoutTokens) -> list[Placed]:
    """A chevron row right above a table with as many columns as chevrons: chevron i spans table column i
    (point depth and the gap between chevrons stay). Skipped when a text would wrap more in its new width."""
    try:
        return _align_chevron_table(out, body, lt)
    except Exception:  # never raise on bad input
        return out


def _align_chevron_table(out: list[Placed], body: Rect, lt: LayoutTokens) -> list[Placed]:
    from .engine import _chevron_text_w, _longest_word_em

    if not lt.chevron_table_align or body.h <= 0:
        return out
    items = _body_items(out, body)
    chevs = sorted(
        (p for p in items if isinstance(p.element, Shape) and p.element.shape == "chevron"),
        key=lambda p: p.x,
    )
    tables = [p for p in items if isinstance(p.element, Table)]
    if len(chevs) < 2 or len(tables) != 1:
        return out
    tp = tables[0]
    cw = tp.element.attrs.get("_col_w")
    if not cw or len(cw) != len(chevs) or abs(sum(cw) - tp.w) > 2 + len(cw):
        return out
    ids = {id(c) for c in chevs} | {id(tp)}
    for p in items:  # nothing else may share the body (icons on a chevron excepted)
        if id(p) not in ids and not (
            isinstance(p.element, Shape) and p.element.shape == "icon" and any(_contains(c, p) for c in chevs)
        ):
            return out
    if min(c.y + c.h for c in chevs) <= max(c.y for c in chevs) or tp.y < max(c.y + c.h for c in chevs) - 2:
        return out
    gap = max(chevs[i + 1].x - (chevs[i].x + chevs[i].w) for i in range(len(chevs) - 1))
    gap = min(max(gap, 0), min(cw) // 4)
    res: dict[int, Placed] = {}
    left = tp.x
    for i, (c, w) in enumerate(zip(chevs, cw, strict=True)):
        nw = w if i == len(chevs) - 1 else w - gap
        depth = c.element.attrs.get("adj", lt.chevron_adj) * min(c.w, c.h)
        adj = round(depth / max(min(nw, c.h), 1), 4)
        el = c.element.model_copy(update={"attrs": {**c.element.attrs, "adj": adj}})
        new = c.model_copy(update={"x": left, "w": nw, "element": el})
        if not _chevron_text_ok(c, new, _chevron_text_w, _longest_word_em, lt):
            return out
        res[id(c)] = new
        for p in items:  # an icon keeps its place relative to the chevron's left end
            if id(p) not in ids and _contains(c, p):
                res[id(p)] = p.model_copy(update={"x": p.x + left - c.x})
        left += w
    return _apply(out, res)


def _chevron_text_ok(old: Placed, new: Placed, text_w, longest_word_em, lt: LayoutTokens) -> bool:
    """The text of chevron ``new`` wraps like it did in ``old`` and its longest word still fits."""
    sz = (old.style.font_size or 18) * old.font_scale
    paras = old.element.paragraphs
    areas = []
    for c in (old, new):
        adj = c.element.attrs.get("adj")
        areas.append(text_w(Rect(c.x, c.y, c.w, c.h), c.style, c.element, adj) / EMU_PER_PT)
    if areas[1] <= 0 or longest_word_em(paras) * sz * lt.chevron_word_slack > areas[1]:
        return False
    for i, para in enumerate(paras):
        cjk = measure.has_cjk(para.plain)
        slack = max(lt.chevron_cjk_slack if cjk else lt.chevron_head_slack, 1.0)
        segs = measure.para_segments(para, i == 0 and bool(para.runs) and all(r.bold for r in para.runs))
        was = measure.count_lines(segs, areas[0] / slack, sz, old.style.font)
        if measure.count_lines(segs, areas[1] / slack, sz, new.style.font) > max(was, 1):
            return False
    return True


def grow_chevron_table(out: list[Placed], body: Rect, lt: LayoutTokens) -> list[Placed]:
    """A chevron row above a table: its text grows while the row has width to spare, so the table below may
    follow (table text never out-sizes the chevron text). Runs before the vertical fill."""
    try:
        return _grow_chevron_table(out, body, lt)
    except Exception:  # never raise on bad input
        return out


def _grow_chevron_table(out: list[Placed], body: Rect, lt: LayoutTokens) -> list[Placed]:
    from .tables import pinned, row_heights, table_grid

    if not lt.l3_fill or body.h <= 0 or lt.chevron_table_fill <= 0 or lt.chevron_text_max_pt <= 0:
        return out
    items = _body_items(out, body)
    chevs = [p for p in items if isinstance(p.element, Shape) and p.element.shape == "chevron"]
    tables = [p for p in items if isinstance(p.element, Table)]
    if len(chevs) < 2 or len(tables) != 1:
        return out
    tp = tables[0]
    ids = {id(c) for c in chevs} | {id(tp)}
    for p in items:  # nothing else may share the body (icons on a chevron excepted)
        if id(p) not in ids and not (
            isinstance(p.element, Shape) and p.element.shape == "icon" and any(_contains(c, p) for c in chevs)
        ):
            return out
    bottom = max(c.y + c.h for c in chevs)
    if min(c.y + c.h for c in chevs) <= max(c.y for c in chevs) or tp.y < bottom - 2:
        return out
    t = tp.element
    rh, cw = t.attrs.get("_row_h"), t.attrs.get("_col_w")
    slack = 0
    nat: list[int] = []
    if rh and cw and not pinned(t):  # pinned rows never give height back
        _n, _c, anchors = table_grid(t)
        nat = row_heights(t, anchors, cw, tp.style, tp.font_scale)
        if len(nat) == len(rh):
            slack = max(sum(rh) - sum(nat), 0)
    cap = min(
        to_emu(lt.chevron_table_grow), slack, max(to_emu(lt.chevron_max_h) - max(c.h for c in chevs), 0)
    )
    best: tuple[float, int, list[Placed]] | None = None
    for k in range(4):  # the smallest height that reaches the largest text
        dh = round(cap * k / 3)
        trial = [_resize_chevron(c, 0, dh, lt) if dh else c for c in chevs]
        grown = _grow_chevron_text(trial, lt, lt.chevron_table_fill, strict=True)
        if grown is None:
            continue
        factor = grown[0].font_scale / max(chevs[0].font_scale, 1e-6)
        if best is None or factor > best[0] + 1e-6:
            best = (factor, dh, grown)
    if best is None:
        return out
    _f, dh, grown = best
    res: dict[int, Placed] = {id(c): g for c, g in zip(chevs, grown, strict=True)}
    for p in items:
        if id(p) in ids or dh == 0:
            continue
        res[id(p)] = p.model_copy(update={"y": p.y + dh // 2})  # an icon stays centred on its chevron
    if dh and slack:  # the table gives the height back out of its stretched rows
        new = [r - round(dh * (r - n) / slack) for r, n in zip(rh, nat, strict=True)]
        el = t.model_copy(update={"attrs": {**t.attrs, "_row_h": new}})
        res[id(tp)] = tp.model_copy(update={"element": el, "y": tp.y + dh, "h": sum(new)})
    return _apply(out, res)


def _grow_chevron_text(
    chevs: list[Placed],
    lt: LayoutTokens,
    fill: float | None = None,
    strict: bool = False,
    icons: bool = False,
) -> list[Placed] | None:
    """Text of a lone chevron row grows to fill the chevron: one factor for the whole row, capped by
    ``chevron_text_max_pt`` and ``chevron_text_fill`` of the height. A word never breaks (it fits one line
    ``chevron_word_slack`` narrower) and no paragraph wraps onto more lines than it did (in an area
    ``chevron_cjk_slack`` / ``chevron_head_slack`` narrower). Rows with icons keep their size unless
    ``icons`` (the caller then moves the icons: the icon's room grows with the text). ``None`` = unchanged."""
    from .engine import _chevron_text_w, _longest_word_em

    if lt.chevron_text_max_pt <= 0 or (not icons and any("icon_side" in c.element.attrs for c in chevs)):
        return None
    sizes = [(c.style.font_size or 18) * c.font_scale for c in chevs]
    s_top = min(
        measure.grow_cap(lt, c.style.font_size or 18, sz, lt.chevron_text_max_pt)  # ... and grow_max
        for c, sz in zip(chevs, sizes, strict=True)
    )
    step = max(lt.l3_grow_step, 0.01)

    def fits(s: float) -> bool:
        for c, sz in zip(chevs, sizes, strict=True):
            paras = c.element.paragraphs
            rect = Rect(c.x, c.y, c.w, c.h)
            adj = c.element.attrs.get("adj")
            el = c.element
            if icons and el.attrs.get("icon_inset"):  # the icon grows with the text: so does its room
                el = el.model_copy(
                    update={"attrs": {**el.attrs, "icon_inset": round(el.attrs["icon_inset"] * s)}}
                )
            avail = _chevron_text_w(rect, c.style, el, adj) / EMU_PER_PT
            if avail <= 0:
                return False
            new_fs = c.font_scale * s
            if measure.paragraphs_height(paras, round(avail * EMU_PER_PT), c.style, new_fs) > (
                (lt.chevron_text_fill if fill is None else fill) * c.h
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
                ref = measure.count_lines(segs, avail if strict else narrow, sz, c.style.font)
                if measure.count_lines(segs, narrow, sz * s, c.style.font) > max(ref, 1):
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


# --------------------------------------------------------------------------- KPI rows


def _kpi_parts(items: list[Placed], cards: list[Placed]) -> list[tuple[Placed, Placed, Placed]] | None:
    """``(card, label, value text)`` of each KPI card, ``None`` when a card holds anything else."""
    parts: list[tuple[Placed, Placed, Placed]] = []
    for c in cards:
        inner = [p for p in items if p is not c and _contains(c, p)]
        heads = [p for p in inner if getattr(p.element, "role", None) == "heading"]
        mains = [p for p in inner if p not in heads]
        if len(heads) != 1 or len(mains) != 1 or not isinstance(mains[0].element, Text):
            return None
        if not heads[0].element.paragraphs or not mains[0].element.paragraphs:
            return None
        if (
            c.element.box is not None and not kpirow.pinned(c.element)  # h= y= w= place the row, not the text
        ) or mains[0].element.box is not None:
            return None
        parts.append((c, heads[0], mains[0]))
    return parts


def _value_pt(m: Placed) -> float:
    return (m.element.paragraphs[0].style.font_size or 36) * m.font_scale


def _value_fit(m: Placed, lt: LayoutTokens) -> float:
    """Largest size (pt) at which the number of ``m`` stays on one line of its text width (CJK guard)."""
    p0 = m.element.paragraphs[0]
    em = value_em(p0, p0.style.font_size or 36)  # a `kpi.unit.size` tail counts at its own size
    return m.w / EMU_PER_PT * lt.kpi_fit_margin * lt.kpi_lone_fit / max(em, 1e-6)


def _value_cap(parts: list[tuple[Placed, Placed, Placed]], sizes: list[float], lt: LayoutTokens) -> float:
    """Largest common growth of the numbers that keeps each within ``layout.grow_max`` x its role size."""
    if lt.grow_max <= 1.0:
        return 1.0
    caps = [
        measure.ceiling(lt) * (m.element.paragraphs[0].style.font_size or 36) / max(s, 1e-6)
        for (_c, _h, m), s in zip(parts, sizes, strict=True)
    ]
    return max(min(caps, default=1.0), 1.0)


def _hero_sizes(parts: list[tuple[Placed, Placed, Placed]], lt: LayoutTokens) -> list[float]:
    """Number sizes of one KPI row after the width rule: a card k times wider than the narrowest gets
    k^``kpi_value_exp`` times the narrowest card's number, within one line of its card, never smaller."""
    cur = [_value_pt(m) for _, _, m in parts]
    wmin = min(c.w for c, _, _ in parts)
    if lt.kpi_value_exp <= 0 or len(parts) < 2 or max(c.w for c, _, _ in parts) < 1.15 * wmin:
        return cur
    base = min(cur)
    return [
        max(s, min(base * (c.w / wmin) ** lt.kpi_value_exp, _value_fit(m, lt)))
        for (c, _h, m), s in zip(parts, cur, strict=True)
    ]


def _with_value(m: Placed, pt: float, cap_pt: float, lt: LayoutTokens) -> Placed:
    """``m`` with its number at ``pt`` and caption lines at least ``cap_pt`` (absolute, when they fit)."""
    paras = list(m.element.paragraphs)
    paras[0] = paras[0].model_copy(
        update={"style": paras[0].style.model_copy(update={"font_size": pt / m.font_scale})}
    )
    for i in range(1, len(paras)):
        st = paras[i].style
        size = (st.font_size or 12) * m.font_scale
        if cap_pt > size and measure.text_em(paras[i].plain) * cap_pt <= m.w / EMU_PER_PT * lt.kpi_fit_margin:
            paras[i] = paras[i].model_copy(
                update={"style": st.model_copy(update={"font_size": cap_pt / m.font_scale})}
            )
    return m.model_copy(update={"element": m.element.model_copy(update={"paragraphs": paras})})


def _kpi_text_h(m: Placed) -> float:
    return measure.paragraphs_height(
        m.element.paragraphs, m.w, m.style, m.font_scale, gap=m.element.attrs.get("para_gap")
    )


def _label_h(h: Placed, pt: float) -> int:
    pv = css.inset_hv(h.style)[1]  # a label on a `kpi.band` carries its padding
    return pv + round(
        measure.paragraphs_height(h.element.paragraphs, h.w, h.style, pt / max(h.style.font_size or 11, 1e-6))
    )


def _banded(parts) -> bool:
    """The label of every card sits on a `kpi.band` (a filled text box at the card's top edge)."""
    return bool(parts) and all(h.style.fill for _c, h, _m in parts)


def _label_step(h: Placed, inner_pt: float, lt: LayoutTokens) -> float:
    """The label size a KPI row may step up to; a size the author pinned (`kpi.band.size`) stays."""
    pt = (h.style.font_size or 11) * h.font_scale
    if h.element.attrs.get("pin_size"):
        return pt
    return _step_up(h.element.paragraphs[0].plain, pt, inner_pt, True, lt, h.style.font_size)


def scale_kpi_values(out: list[Placed], body: Rect, lt: LayoutTokens, fixed: bool = False) -> list[Placed]:
    """KPI cards that keep their (tall) row height, e.g. above a list: the card text uses the card.

    A wider card gets a bigger number (the hero, ``kpi_value_exp``); then the numbers of the row grow by one
    factor (at most ``kpi_lone_value_grow``) and label and caption step up (as in a lone row) as far as they
    stay on one line and fill at most ``kpi_card_fill`` of the card. ``fixed`` (the author set the size):
    unchanged. Never raises."""
    try:
        return _scale_kpi_values(out, body, lt, fixed)
    except Exception:  # never raise on bad input
        return out


def _scale_kpi_values(out: list[Placed], body: Rect, lt: LayoutTokens, fixed: bool) -> list[Placed]:
    if fixed or body.h <= 0:
        return out
    items = _body_items(out, body)
    cards = [p for p in items if isinstance(p.element, Container) and "kpi" in p.element.classes]
    res: dict[int, Placed] = {}
    for y in {c.y for c in cards}:
        parts = _kpi_parts(items, [c for c in cards if c.y == y])
        if parts is None:
            continue
        cur = [_value_pt(m) for _, _, m in parts]
        hero = _hero_sizes(parts, lt)
        inner_pt = min(m.w for _, _, m in parts) / EMU_PER_PT
        g_fit = min(_value_fit(m, lt) / s for (_, _, m), s in zip(parts, hero, strict=True))
        gmax = max(min(lt.kpi_lone_value_grow, g_fit, _value_cap(parts, hero, lt)), 1.0)
        label0 = min((h.style.font_size or 11) * h.font_scale for _, h, _ in parts)
        label_hi = min(_label_step(h, inner_pt, lt) for _, h, _ in parts)
        caps = [
            (m.element.paragraphs[1].style.font_size or 12) * m.font_scale
            for _, _, m in parts
            if len(m.element.paragraphs) > 1
        ]
        cap0 = min(caps, default=0.0)
        cap_hi = min(
            (
                _step_up(
                    m.element.paragraphs[1].plain,
                    c0,
                    inner_pt,
                    False,
                    lt,
                    m.element.paragraphs[1].style.font_size or 12,
                )
                for (_, _, m), c0 in zip(
                    [p for p in parts if len(p[2].element.paragraphs) > 1], caps, strict=True
                )
            ),
            default=0.0,
        )
        grow_steps = (1.0, 0.75, 0.5, 0.25, 0.0) if lt.kpi_lone and lt.kpi_card_fill > 0 else (0.0,)
        for k in grow_steps:  # the largest growth step whose cards still have air
            sizes = [s * (1 + (gmax - 1) * k) for s in hero]
            label_pt = label0 + (label_hi - label0) * k
            cap_pt = cap0 + (cap_hi - cap0) * k
            news = [
                (_with_value(m, s, cap_pt, lt), _label_h(h, max(label_pt, 1.0)))
                for (_c, h, m), s in zip(parts, sizes, strict=True)
            ]
            if all(
                hh + _kpi_text_h(m2) <= (lt.kpi_card_fill or 1.0) * c.h
                for (c, _h, _m), (m2, hh) in zip(parts, news, strict=True)
            ):
                break
        else:
            continue
        if k == 0.0 and hero == cur:
            continue
        for (_c, h, m), (m2, hh) in zip(parts, news, strict=True):
            lab = max(label_pt, (h.style.font_size or 11) * h.font_scale)
            top = h.y + max(hh, h.h)
            res[id(h)] = h.model_copy(
                update={"font_scale": lab / max(h.style.font_size or 11, 1e-6), "h": max(hh, h.h)}
            )
            res[id(m)] = m2.model_copy(update={"y": max(m.y, top), "h": m.y + m.h - max(m.y, top)})
    return _apply(out, res) if res else out


def fit_lone_kpi(
    out: list[Placed],
    body: Rect,
    lt: LayoutTokens,
    on_bar: bool = False,
    fixed: bool = False,
    to_body: bool = False,
) -> list[Placed]:
    """A body of nothing but KPI cards: cards that use the body height in a balanced way, centred.

    The numbers grow together (``kpi_lone_value_grow``, at most ``kpi_lone_value_max_pt``, never wrap, ratios
    between cards kept), label and caption step up, the card is content + padding tall, between
    ``kpi_lone_min_h`` and ``kpi_lone_h`` of the body, and the row sits with ``kpi_lone_center`` of the free
    height above it (``on_bar``: ``kpi_lone_bar_center``, nearer to the conclusion bar).
    ``fixed``: the author set the KPI text size (CSS, {size=}): only the card height follows its content.
    Other blocks, icons, explicit sizes / heights: unchanged.
    ``to_body`` (small-body themes, ``kpi_to_body``): the cards stretch down the body to
    ``kpi_to_body_h`` of its height and the text grows with them, within the ``kpi_lone_*`` caps.
    A row whose cards carry ``h=`` / ``y=`` / ``w=`` is left alone (``kpirow``)."""
    try:
        return _fit_lone_kpi(out, body, lt, on_bar, fixed, to_body)
    except Exception:  # never raise on bad input
        return out


def _step_up(
    plain: str, pt: float, wpt: float, bold: bool, lt: LayoutTokens, base: float | None = None
) -> float:
    """``pt`` stepped up (``kpi_lone_text_grow``, max ``kpi_lone_text_max_pt`` and ``grow_max`` x the role
    size ``base``) while it stays on one line."""
    big = min(pt * lt.kpi_lone_text_grow, max(lt.kpi_lone_text_max_pt, pt))
    big = min(big, max(pt, measure.ceiling(lt) * (base or pt)))
    return big if measure.text_em(plain, bold=bold) * big <= wpt * lt.kpi_fit_margin else pt


def _fit_lone_kpi(
    out: list[Placed],
    body: Rect,
    lt: LayoutTokens,
    on_bar: bool,
    fixed: bool,
    to_body: bool = False,
) -> list[Placed]:
    if not lt.kpi_lone or body.h <= 0:
        return out
    items = _body_items(out, body)
    cards = [p for p in items if isinstance(p.element, Container)]
    if not cards or any("kpi" not in c.element.classes for c in cards) or len({c.y for c in cards}) != 1:
        return out
    parts = _kpi_parts(items, cards)
    if parts is None or any(kpirow.pinned(c.element) for c in cards):
        return out  # (a row the author sized and placed keeps its cards: only the text may grow, see scale)
    seen = {id(c) for c in cards} | {id(p) for part in parts for p in part[1:]}
    if any(id(p) not in seen for p in items):
        return out  # icons, notes or other blocks share the body

    inner_pt = min(m.w for _, _, m in parts) / EMU_PER_PT
    # the numbers grow by one factor (the ratios between cards stay), never wrap, never get smaller
    sizes0 = [_value_pt(m) for _, _, m in parts] if fixed else _hero_sizes(parts, lt)
    fits = [_value_fit(m, lt) / s for (_, _, m), s in zip(parts, sizes0, strict=True)]
    g = max(
        min(
            lt.kpi_lone_value_grow,
            min(fits),
            lt.kpi_lone_value_max_pt / max(sizes0),
            _value_cap(parts, sizes0, lt),
        ),
        1.0,
    )
    label_hi = min(_label_step(h, inner_pt, lt) for _, h, _ in parts)
    cap_hi = min(
        (
            _step_up(
                m.element.paragraphs[1].plain,
                (m.element.paragraphs[1].style.font_size or 12) * m.font_scale,
                inner_pt,
                False,
                lt,
                m.element.paragraphs[1].style.font_size or 12,
            )
            for _, _, m in parts
            if len(m.element.paragraphs) > 1
        ),
        default=0.0,
    )
    label0 = min((h.style.font_size or 11) * h.font_scale for _, h, _ in parts)
    cap0 = min(
        (
            (m.element.paragraphs[1].style.font_size or 12) * m.font_scale
            for _, _, m in parts
            if len(m.element.paragraphs) > 1
        ),
        default=0.0,
    )
    band = _banded(parts)
    stretch = to_body and lt.kpi_to_body and lt.body_valign != "top"
    limit = round(max(lt.kpi_lone_h, lt.kpi_to_body_h if stretch else 0.0) * body.h)
    own_h = to_emu(lt.kpi_h) if lt.kpi_h is not None else 0  # `kpi.h=4.4in`: the author's own card height
    if own_h > 0:
        limit = min(own_h, body.h)
    if fixed:
        g, label_hi, cap_hi = 1.0, label0, cap0
    # largest step of the growth (1 = full, 0 = the sizes the slide had) whose card stays within the share
    for k in (1.0, 0.8, 0.6, 0.4, 0.2, 0.0):
        values = [s * (1 + (g - 1) * k) for s in sizes0]
        label_pt = label0 + (label_hi - label0) * k
        cap_pt = cap0 + (cap_hi - cap0) * k
        news, hh, mh, pad, gap = _lone_geometry(parts, values, label_pt, cap_pt, lt)
        card_h = (hh + gap + mh + pad) if band else (2 * pad + hh + gap + mh)  # a band sits flush on top
        if card_h <= limit:
            break
    floor = min(round(max(lt.kpi_lone_min_h, lt.kpi_to_body_h if stretch else 0.0) * body.h), limit)
    if own_h > 0:
        floor = limit
    extra = max(
        floor - card_h, 0
    )  # a short row still fills its share of the body: the air goes into the card
    card_h = min(
        max(card_h, floor), body.h
    )  # content is never cut: at the old sizes the card may pass its share
    centre = lt.kpi_lone_bar_center if on_bar else lt.kpi_lone_center
    top = body.y + round((body.h - card_h) * centre)
    top = max(body.y, min(top, body.bottom - card_h))
    lab_y = top if band else top + pad + round(extra * lt.kpi_lone_label_air)
    res: dict[int, Placed] = {}
    for (c, h, m), (h2, m2) in zip(parts, news, strict=True):
        res[id(c)] = c.model_copy(update={"y": top, "h": card_h})
        res[id(h)] = h2.model_copy(update={"y": lab_y, "h": hh})
        res[id(m)] = m2.model_copy(update={"y": lab_y + hh + gap, "h": top + card_h - pad - lab_y - hh - gap})
    return _apply(out, res)


def _lone_geometry(parts, values: list[float], label_pt: float, cap_pt: float, lt: LayoutTokens):
    """(new label / text items, label height, text height, padding, gap) of a lone KPI row at these sizes."""
    pad = round(lt.kpi_lone_pad_em * max(values) * EMU_PER_PT)
    gap = round(lt.kpi_lone_gap_em * label_pt * EMU_PER_PT)
    news: list[tuple[Placed, Placed]] = []
    hhs: list[int] = []
    mhs: list[int] = []
    for (_c, h, m), value_pt in zip(parts, values, strict=True):
        hscale = label_pt / max(h.style.font_size or 11, 1e-6)
        hhs.append(
            css.inset_hv(h.style)[1]
            + round(measure.paragraphs_height(h.element.paragraphs, h.w, h.style, hscale))
        )
        paras = [
            p.model_copy(
                update={"style": p.style.model_copy(update={"font_size": value_pt if i == 0 else cap_pt})}
            )
            for i, p in enumerate(m.element.paragraphs)
        ]
        m2 = m.model_copy(
            update={"font_scale": 1.0, "element": m.element.model_copy(update={"paragraphs": paras})}
        )
        mhs.append(
            round(measure.paragraphs_height(paras, m.w, m.style, 1.0, gap=m.element.attrs.get("para_gap")))
        )
        news.append((h.model_copy(update={"font_scale": hscale}), m2))
    return news, max(hhs), max(mhs), pad, gap


# --------------------------------------------------------------------------- band balance


def _draws(p: Placed) -> bool:
    """True when a placed container paints something below its top rule (fill, outline, side borders)."""
    st = p.style
    fill = str(st.fill or "").lower()
    painted = (
        bool(fill) and fill not in ("none", "transparent") and not (len(fill) == 9 and fill.endswith("00"))
    )
    outlined = bool(st.line) and (st.line_width is None or st.line_width > 0)
    sides = any((st.border_right, st.border_bottom, st.border_left))
    return painted or outlined or sides or bool(st.shadow)


def center_band(out: list[Placed], body: Rect, lt: LayoutTokens) -> list[Placed]:
    """A block of cards / columns that leaves a band under it: the block sits at the optical center.

    Normal-density slides only (the caller gates it). When more than ``band_max`` of the body is empty under
    the block, it moves down until ``band_shift`` of the free height is above it, by at most
    ``band_shift_max`` of the body. Cards and texts only: tables, charts, pictures, loose shapes and
    blocks that already fill the body stay put. Never raises: anything unexpected returns the items."""
    try:
        return _center_band(out, body, lt)
    except Exception:
        return out


def _center_band(out: list[Placed], body: Rect, lt: LayoutTokens) -> list[Placed]:
    from .engine import _text_h

    if lt.band_shift <= 0 or body.h <= 0:
        return out
    items = _body_items(out, body)
    cards = [p for p in items if isinstance(p.element, Container)]
    if not cards or any(isinstance(p.element, (Chart, Image, Media, Table)) for p in items):
        return out
    if any({"diagram", "flow", "chevron"} & set(c.element.classes) for c in cards):
        return out  # diagrams own their labels and connectors
    if any(isinstance(p.element, Shape) and not any(_contains(c, p) for c in cards) for p in items):
        return out
    top = min(p.y for p in items)
    bottom = 0
    for p in items:
        if isinstance(p.element, Text) and p.element.paragraphs:
            bottom = max(bottom, p.y + _text_h(p))
        elif not isinstance(p.element, Container) or _draws(p):
            bottom = max(bottom, p.y + p.h)
    if bottom <= top:
        return out
    below = body.bottom - bottom
    above = top - body.y
    if below <= lt.band_max * body.h:
        return out
    dy = min(round((above + below) * lt.band_shift) - above, round(lt.band_shift_max * body.h), below)
    if dy <= 0:
        return out
    ids = {id(p) for p in items}
    return [p.model_copy(update={"y": p.y + dy}) if id(p) in ids else p for p in out]
