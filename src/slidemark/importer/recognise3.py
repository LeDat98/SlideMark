"""Geometry recognition of four forms a foreign deck draws by hand (DL3d part 2, lane E; the t2 round trip).

``recognise2`` reads text-less step cards under chevrons and a takeaway bar that ends above the footer zone;
``recognise`` reads figure-first tiles. The t2 deck (python-pptx, 15 slides) draws four more things that fell
back to plain boxes. Each is read here and written as the token SlideMark already has:

* **steps with their own text**  pentagons / chevrons, a card under each (a little narrower than its arrow)
  holding its own text, and a ``STEP n`` caption under every card -> ``@N steps num`` +
  ``steps-arrow.fill=a,b`` (+ ``steps.caption=`` when the pattern is not ``STEP {n}``,
  ``steps.caption_color`` / ``_size``; sizes are left to the layout: an explicit size turns its sparse-group
  centring off);
* **centred KPI cards**  label on top, a big number, an optional thin divider rule, a coloured delta below,
  an optional stripe on the top edge -> ``@kpi`` + ``kpi.rule=`` ``kpi.stripe=``
  ``kpi.label.*`` ``kpi.note.*`` ``kpi.h=``;
* **header-band cards**  a card, a dark header rectangle holding the title on its top edge, a body of ``■``
  bullets -> boxes with ``heading.band=`` ``heading.align=``, the glyph a real bullet (``bullet=■``);
* **full-width takeaway bar**  a filled bar low on the slide that ends just above the footer text -> the ``>``
  conclusion + ``conclusion.fill=`` (``recognise2`` stops its search at the footer line).

Conservative: a form fires only when EVERY card of its group matches, never on a deck SlideMark built (the
``is_foreign`` guard), never raises. Shapes it takes are claimed (``runs.claim``) so ``recognise`` skips them.
All thresholds are in one table, ``TH3``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace

from .look import _dist, _lum
from .read import Item, ParaT, SlideData
from .recognise2 import (
    CHEVRON_PRST,
    Found,
    _foreign_name,
    _is_hex,
    _length,
    _modal,
    name_or_hex,
)
from .runs import claim, free, is_foreign

EMU_PT = 12700
GLYPHS = "■□●○◆◇▪▫•・▶►"


@dataclass(frozen=True)
class Thresholds:
    """Every geometric decision of this module (shares of the slide width W / height H unless noted)."""

    # chevron row with cards that hold text, caption under them
    row_dy: float = 0.15  # arrows of one row: centres within this share of their height
    same: float = 0.06  # equal sizes / aligned edges within this share of the arrow width / height
    card_w: tuple = (0.75, 1.06)  # a step card is this share of its arrow's width (a pentagon overlaps)
    card_gap: float = 0.15  # a card starts at most this share of H below its arrow
    caption_gap: float = 0.12  # a caption starts at most this share of H below its card
    caption_h: float = 0.12  # ... and is at most this high
    caption_chars: int = 12  # the caption's words around the step number
    # groups of cards
    card_area: tuple = (0.02, 0.40)  # share of the slide one card covers
    group: tuple = (2, 8)  # cards of one group
    group_tol: float = 0.12  # cards of one group differ in width and height by at most this share
    body_y: tuple = (0.14, 0.93)  # the cards sit between these shares of H
    # KPI card
    value_ratio: float = 1.4  # the number is at least this much bigger than the label and the delta
    rule_h: float = 0.012  # a divider rule is at most this high (share of H) ...
    rule_w: float = 0.9  # ... and this wide (share of the card width)
    rule_mid: float = 0.1  # ... centred within this share of the card width
    stripe_h: float = 0.03  # a stripe is at most this high (share of H) ...
    stripe_card: float = 0.2  # ... and this share of the card height
    # header-band card
    band_h: float = 0.35  # the header is at most this share of the card height
    band_w: float = 0.96  # ... and at least this share of its width
    band_dy: float = 0.02  # ... and sits at the card's top edge within this share of H
    band_lum: float = 0.40  # a header band is darker than this (relative luminance)
    # takeaway bar
    bar_min_w: float = 0.75
    bar_min_y: float = 0.55
    bar_max_h: float = 0.25
    bar_bottom: float = 0.93  # the bar ends above this share of H (recognise2: 0.90)
    footer_y: float = 0.9  # items from here down are footer chrome
    bar_lum: float = 0.25  # the bar is dark (relative luminance)
    same_fill: float = 12.0  # RGB distance under which two fills are one fill
    ink_near: float = 12.0  # a text colour this close to the deck ink is the ink
    anchor_tol: float = (
        0.03  # a row of cards this close (share of H) to a body edge / the middle is anchored there
    )


TH3 = Thresholds()


# --------------------------------------------------------------------------- helpers


def _live(data: SlideData) -> list[Item]:
    return [i for i in data.items if free(i) and _foreign_name(i)]


def _inside(t: Item, card: Item) -> bool:
    return card.x <= t.cx <= card.x + card.w and card.y <= t.cy <= card.y + card.h


def _fill_shape(it: Item) -> bool:
    """A filled shape without text (a card, a rule, a stripe)."""
    return it.kind == "shape" and _is_hex(it.fill) and not it.paras and not it.ph


def _runs(paras: list[ParaT]):
    return [r for p in paras for r in p.runs if r.text.strip()]


def _sizes(paras: list[ParaT]) -> list[float]:
    return [r.size for r in _runs(paras) if r.size]


def _size(it: Item) -> float:
    return max(_sizes(it.paras), default=0.0)


def _all(paras: list[ParaT], test) -> bool:
    runs = _runs(paras)
    return bool(runs) and all(test(r) for r in runs)


def _color(paras: list[ParaT]) -> str | None:
    """The one colour (RRGGBB) every run of ``paras`` has, else None."""
    cols = {(r.color or "").upper() for r in _runs(paras)}
    return next(iter(cols)) if len(cols) == 1 and _is_hex(next(iter(cols))) else None


def _centred(it: Item) -> bool:
    return bool(it.paras) and all(p.align == "ctr" for p in it.paras if p.plain.strip())


def _put(found: Found, key: str, value: str | None) -> None:
    if value:
        found.style.setdefault(key, value)


def _ink(deck, hexv: str | None) -> str | None:
    """A colour token for ``hexv`` (name or hex), None when it is the deck's text colour."""
    if not hexv:
        return None
    ink = deck.ink or deck.colors.get("fg", "")
    if ink and _dist(hexv, ink.upper()) <= TH3.ink_near:
        return None
    return name_or_hex(deck, hexv, near=True)


def _groups(cards: list[Item]) -> list[list[Item]]:
    """Cards of about one size (``TH3.group`` of them), in reading order (rows, then x)."""
    rest = sorted(cards, key=lambda c: (c.y, c.x))
    tol = 1 + TH3.group_tol
    out: list[list[Item]] = []
    while rest:
        a = rest[0]
        g = [c for c in rest if max(a.w, c.w) <= tol * min(a.w, c.w) and max(a.h, c.h) <= tol * min(a.h, c.h)]
        rest = [c for c in rest if c not in g]
        if TH3.group[0] <= len(g) <= TH3.group[1]:
            out.append(sorted(g, key=lambda c: (round(c.y / max(0.5 * c.h, 1)), c.x)))
    return out


def _cards(data: SlideData, deck) -> list[Item]:
    W, H = deck.width, deck.height
    lo, hi = TH3.card_area
    y0, y1 = TH3.body_y
    return [
        c
        for c in _live(data)
        if _fill_shape(c)
        and lo <= c.area / (W * H) <= hi
        and y0 * H <= c.y
        and c.y + c.h <= y1 * H
        and c.w < 0.97 * W
    ]


# --------------------------------------------------------------------------- 1. steps whose cards hold text


def _step_caption_template(texts: list[str]) -> str | None:
    """``STEP {n}`` for ``["STEP 1", "STEP 2", ...]`` (the number of step k is k), else None."""
    tpl = None
    for k, t in enumerate(texts, 1):
        t = t.strip()
        m = re.fullmatch(rf"(\D{{0,{TH3.caption_chars}}}?)\s*{k}(\D{{0,2}})", t)
        if not m:
            return None
        cur = t.replace(str(k), "{n}", 1)
        if tpl not in (None, cur):
            return None
        tpl = cur
    return tpl


def _steps(data: SlideData, deck, found: Found) -> None:
    H = deck.height
    chevs = [i for i in _live(data) if i.prst in CHEVRON_PRST and i.paras and _is_hex(i.fill)]
    if len(chevs) < 2:
        return
    chevs.sort(key=lambda i: i.x)
    c0 = chevs[0]
    if any(
        abs(c.cy - c0.cy) > TH3.row_dy * c0.h
        or abs(c.w - c0.w) > TH3.same * c0.w
        or abs(c.h - c0.h) > TH3.same * c0.h
        for c in chevs
    ):
        return  # two rows, or sizes that differ: not one sequence
    lo, hi = TH3.card_w
    cards: list[Item] = []
    for a in chevs:
        under = [
            s
            for s in _live(data)
            if _fill_shape(s)
            and s.h > 0.5 * a.h
            and abs(s.x - a.x) <= TH3.same * a.w
            and lo * a.w <= s.w <= hi * a.w
            and a.y + a.h - 0.02 * H <= s.y <= a.y + a.h + TH3.card_gap * H
        ]
        if not under:
            return  # an arrow without a card stays a plain chevron row
        cards.append(min(under, key=lambda s: s.y))
    if len({id(c) for c in cards}) != len(cards):
        return
    texts = [
        [t for t in _live(data) if t.kind == "text" and t.paras and not t.fill and _inside(t, c)]
        for c in cards
    ]
    if not all(texts):
        return  # text-less cards are recognise2's
    caps: list[Item | None] = []
    for c in cards:
        below = [
            t
            for t in _live(data)
            if t.kind == "text"
            and len(t.paras) == 1
            and not t.fill
            and abs(t.x - c.x) <= TH3.same * c.w
            and abs(t.w - c.w) <= TH3.same * c.w
            and c.y + c.h - 0.02 * H <= t.y <= c.y + c.h + TH3.caption_gap * H
            and t.h <= TH3.caption_h * H
        ]
        caps.append(min(below, key=lambda t: t.y) if below else None)
    tpl = _step_caption_template([c.text for c in caps if c]) if all(caps) else None
    row = chevs
    for k, (a, card, tx) in enumerate(zip(row, cards, texts, strict=True), 1):
        a.name, card.name = f"Step {k} arrow", f"Step {k} card"
        claim(a, "steps")
        claim(card, "steps")
        for t in tx:
            claim(t, "steps")
    if tpl is not None:
        for cap in caps:
            claim(cap, "steps", "decor")  # a token, not content: the card's first line again
        data.words.append("num")
        if tpl != "STEP {n}":
            found.style.setdefault("steps.caption", f'"{tpl}"')
        cap_runs = [r for cap in caps if cap for r in _runs(cap.paras)]
        if (col := _color([p for cap in caps if cap for p in cap.paras])) is not None:
            _put(found, "steps.caption_color", name_or_hex(deck, col))
        if sz := _modal([r.size for r in cap_runs if r.size]):
            _put(found, "steps.caption_size", f"{sz:g}")
    arrows = [a.fill.upper() for a in row]
    if any(_dist(a, deck.colors.get("primary", "")) > TH3.same_fill for a in arrows):
        _put(found, "steps-arrow.fill", ",".join(name_or_hex(deck, a) for a in arrows))
    # (sizes and the arrow height are NOT stated: an explicit size turns the sparse-group layout off, and the
    # layout then keeps the strip at the top; left to itself it grows and centres the group like the original)
    body = [p for tx in texts for t in tx for p in t.paras]
    if body and _all(body, lambda r: r.bold):
        _put(found, "steps-card.bold", "on")
    if all(_centred(t) for tx in texts for t in tx):
        _put(found, "steps-card.align", "center")
    _card_look(found, "steps-card", cards, deck)


def _card_look(found: Found, cls: str, cards: list[Item], deck) -> None:
    """``<cls>.fill`` / ``<cls>.line`` when the cards share a fill / outline unlike the theme's."""
    fills = {c.fill.upper() for c in cards}
    surf = deck.colors.get("surface", "")
    if len(fills) == 1 and _dist(next(iter(fills)), surf) > TH3.same_fill:
        _put(found, f"{cls}.fill", name_or_hex(deck, next(iter(fills))))
    lines = {(c.line_color or "").upper() for c in cards}
    if len(lines) == 1 and _is_hex(next(iter(lines))):
        _put(found, f"{cls}.line", name_or_hex(deck, next(iter(lines))))


# --------------------------------------------------------------------------- 2. centred KPI cards


def _kpi_parts(card: Item, data: SlideData, H: int) -> dict | None:
    """label / value / delta texts, the optional rule and stripe of one card, or None (not a KPI card)."""
    texts = sorted(
        (t for t in _live(data) if t.kind == "text" and t.paras and not t.fill and _inside(t, card)),
        key=lambda t: (t.y, t.x),
    )
    if len(texts) != 3 or any(len(t.paras) != 1 or not _centred(t) for t in texts):
        return None
    label, value, note = texts
    sv, sl, sn = _size(value), _size(label), _size(note)
    if not (sv and sl and sn) or sv < TH3.value_ratio * max(sl, sn) or not re.search(r"\d", value.text):
        return None
    shapes = [s for s in _live(data) if _fill_shape(s) and s is not card and _inside(s, card)]
    rule = [
        s
        for s in shapes
        if s.h <= TH3.rule_h * H
        and s.w <= TH3.rule_w * card.w
        and abs(s.cx - card.cx) <= TH3.rule_mid * card.w
        and value.cy < s.cy < note.cy
    ]
    stripe = [
        s
        for s in shapes
        if abs(s.y - card.y) <= 0.01 * H
        and abs(s.x - card.x) <= TH3.same * card.w
        and abs(s.w - card.w) <= TH3.same * card.w
        and 0 < s.h <= min(TH3.stripe_h * H, TH3.stripe_card * card.h)
    ]
    if len(rule) > 1 or len(stripe) > 1:
        return None
    return {
        "label": label,
        "value": value,
        "note": note,
        "rule": rule[0] if rule else None,
        "stripe": stripe[0] if stripe else None,
    }


def _kpi(data: SlideData, deck, found: Found) -> None:
    H = deck.height
    parts = {id(c): p for c in _cards(data, deck) if (p := _kpi_parts(c, data, H)) is not None}
    for g in _groups(_cards(data, deck)):
        if not all(id(c) in parts for c in g):
            continue  # a card of the group that is not a KPI card: none of them is read
        ps = [parts[id(c)] for c in g]
        if len({p["rule"] is None for p in ps}) > 1 or len({p["stripe"] is None for p in ps}) > 1:
            continue  # every card has its rule / stripe, or none does
        _apply_kpi(data, deck, found, g, ps)
        return


def _apply_kpi(data: SlideData, deck, found: Found, cards: list[Item], ps: list[dict]) -> None:
    for c, p in zip(cards, ps, strict=True):
        claim(c, "kpi3")
        for k in ("label", "value", "note"):
            claim(p[k], "kpi3")
        for k in ("rule", "stripe"):
            if p[k] is not None:
                claim(p[k], "kpi3", "decor")
    data.words.append("kpi")
    labels = [p["label"].paras for p in ps]
    notes = [p["note"].paras for p in ps]
    values = [p["value"].paras for p in ps]
    flat = lambda xs: [q for x in xs for q in x]  # noqa: E731
    look = (("kpi.label", labels), ("kpi.note", notes))
    for cls, paras in look:
        if sz := _modal(_sizes(flat(paras))):
            _put(found, f"{cls}.size", f"{sz:g}")
        _put(found, f"{cls}.bold", "on" if _all(flat(paras), lambda r: r.bold) else "off")
        _put(found, f"{cls}.color", _ink(deck, _color(flat(paras))))
    if vc := _color(flat(values)):
        _put(found, "kpi.color", name_or_hex(deck, vc))
    if sz := _modal(_sizes(flat(values))):
        data.style_lines.append(f"sizes: kpi={sz:g}")
    _card_look(found, "kpi", cards, deck)
    _put(found, "kpi.h", _length(_modal([c.h for c in cards]) or cards[0].h))
    rules = [p["rule"] for p in ps if p["rule"] is not None]
    if rules:
        cols = {r.fill.upper() for r in rules}
        _put(
            found,
            "kpi.rule",
            ",".join(name_or_hex(deck, c) for c in sorted(cols)) if len(cols) == 1 else None,
        )
        _put(found, "kpi.rule_h", f"{max(round(rules[0].h / EMU_PT, 1), 0.5):g}pt")
        _put(found, "kpi.rule_w", _length(rules[0].w))
    stripes = [p["stripe"] for p in ps if p["stripe"] is not None]
    if stripes:
        cols = [s.fill.upper() for s in stripes]
        _put(
            found,
            "kpi.stripe",
            ",".join(name_or_hex(deck, c) for c in (cols[:1] if len(set(cols)) == 1 else cols)),
        )
        _put(found, "kpi.stripe_h", f"{max(round(stripes[0].h / EMU_PT), 1)}pt")


# --------------------------------------------------------------------------- 3. cards with a dark header band


def _band_parts(card: Item, data: SlideData, H: int) -> tuple[Item, list[Item]] | None:
    """(header, body texts) of a card whose top edge carries a dark rectangle with the title."""
    head = [
        s
        for s in _live(data)
        if s is not card
        and s.kind in ("shape", "text")
        and s.paras
        and len(s.paras) == 1
        and _is_hex(s.fill)
        and abs(s.x - card.x) <= TH3.same * card.w
        and s.w >= TH3.band_w * card.w
        and s.w <= 1.04 * card.w
        and abs(s.y - card.y) <= TH3.band_dy * H
        and s.h <= TH3.band_h * card.h
        and _lum(s.fill.upper()) < TH3.band_lum
    ]
    if len(head) != 1:
        return None
    h = head[0]
    body = sorted(
        (
            t
            for t in _live(data)
            if t.kind == "text"
            and t.paras
            and not t.fill
            and t is not h
            and _inside(t, card)
            and t.y >= h.y + h.h - 2
        ),
        key=lambda t: (t.y, t.x),
    )
    return (h, body) if body else None


def _anchor(cards: list[Item], deck) -> str | None:
    """Where the row of cards sits in the body (``top`` / ``center`` / ``bottom``): the edge or the middle of
    the body area it is nearest to, within ``TH3.anchor_tol`` of the slide height; None when it floats."""
    top, bottom = deck.body_top, deck.body_bottom
    if not top or bottom <= top:
        return "top"
    y0 = min(c.y for c in cards)
    y1 = max(c.y + c.h for c in cards)
    near = {
        "top": abs(y0 - top),
        "bottom": abs(y1 - bottom),
        "center": abs((y0 + y1) / 2 - (top + bottom) / 2),
    }
    word, dist = min(near.items(), key=lambda t: t[1])
    return word if dist <= TH3.anchor_tol * deck.height else None


def _glyph_bullets(paras: list[ParaT]) -> str | None:
    """The glyph every paragraph of the body starts with (``■ text``), or None."""
    firsts = []
    for p in paras:
        runs = [r for r in p.runs if r.text.strip()]
        if len(runs) < 2 or p.marker or not (g := runs[0].text.strip()) or len(g) != 1 or g not in GLYPHS:
            return None
        firsts.append(g)
    return firsts[0] if firsts and len(set(firsts)) == 1 else None


def _bands(data: SlideData, deck, found: Found) -> None:
    H = deck.height
    parts = {id(c): p for c in _cards(data, deck) if (p := _band_parts(c, data, H)) is not None}
    for g in _groups(_cards(data, deck)):
        if not all(id(c) in parts for c in g):
            continue
        heads = [parts[id(c)][0] for c in g]
        if len({h.fill.upper() for h in heads}) > 1:
            continue
        bodies = [t for c in g for t in parts[id(c)][1]]
        if not _glyph_bullets_all(bodies):
            continue
        _apply_bands(data, deck, found, g, heads, bodies, [parts[id(c)][1] for c in g])
        return


def _glyph_bullets_all(bodies: list[Item]) -> bool:
    """True when every body paragraph is ``■ text`` (one glyph) or none is (plain text): bullets or not."""
    paras = [p for t in bodies for p in t.paras if p.plain.strip()]
    return bool(paras) and (
        _glyph_bullets(paras) is not None or not any(p.marker is None and _gl(p) for p in paras)
    )


def _gl(p: ParaT) -> bool:
    runs = [r for r in p.runs if r.text.strip()]
    return bool(runs) and runs[0].text.strip() in GLYPHS


def _apply_bands(
    data: SlideData,
    deck,
    found: Found,
    cards: list[Item],
    heads: list[Item],
    bodies: list[Item],
    per_card: list[list[Item]],
) -> None:
    for c, h, texts in zip(cards, heads, per_card, strict=True):
        claim(c, "bandcard")
        claim(h, "bandcard")
        for t in texts:
            claim(t, "bandcard")
    _put(found, "heading.band", name_or_hex(deck, heads[0].fill))
    if all(_centred(h) for h in heads):
        _put(found, "heading.align", "center")
    paras = [p for t in bodies for p in t.paras if p.plain.strip()]
    glyph = _glyph_bullets(paras)
    if glyph:
        gcol = _color([ParaT(runs=[p.runs[0] for p in paras])])
        for p in paras:  # the glyph is a real bullet: marker set, glyph run removed (bullet token below)
            first = next(i for i, r in enumerate(p.runs) if r.text.strip())
            p.runs = [r for i, r in enumerate(p.runs) if i != first]
            if p.runs and p.runs[0].text.startswith(" "):
                p.runs[0] = replace(p.runs[0], text=p.runs[0].text.lstrip())
            p.marker = "bullet"
            p.size = None if p.size is None else p.size
        _put(found, "bullet", glyph)
        if gcol:
            _put(found, "bullet.color", name_or_hex(deck, gcol))
    hsz = _modal([s for h in heads for s in _sizes(h.paras)])
    sizes = ([f"heading={hsz:g}!"] if hsz else []) + (
        [f"body={b:g}!"] if (b := _modal(_sizes(paras))) else []
    )
    if sizes:
        data.style_lines.append("sizes: " + " ".join(sizes))
    if bc := _ink(deck, _color(paras)):
        _put(found, "box.color", bc)
    _card_look(found, "card", cards, deck)
    hcol = _color([p for h in heads for p in h.paras])
    if hcol and _dist(hcol, "FFFFFF") > TH3.ink_near:
        _put(found, "heading.band.color", name_or_hex(deck, hcol))
    _put(found, "box.h", _length(_modal([float(c.h) for c in cards]) or cards[0].h))  # exact card height
    _put(found, "box.anchor", _anchor(cards, deck))


# --------------------------------------------------------------------------- 4. full-width takeaway bar


def _bar(data: SlideData, deck, found: Found) -> None:
    W, H = deck.width, deck.height
    live = [i for i in data.items if i.role is None]
    if any((i.name or "").lower().startswith("conclusion") for i in data.items):
        return
    bars: list[tuple[Item, Item | None]] = []
    for r in live:
        if not (
            free(r)
            and _is_hex(r.fill)
            and r.kind in ("shape", "text")
            and _foreign_name(r)
            and r.w >= TH3.bar_min_w * W
            and r.y >= TH3.bar_min_y * H
            and r.h <= TH3.bar_max_h * H
            and r.y + r.h <= TH3.bar_bottom * H
            and _lum(r.fill.upper()) < TH3.bar_lum
        ):
            continue
        if r.kind == "text":
            if len(r.paras) <= 2 and not any(p.marker for p in r.paras):
                bars.append((r, None))
            continue
        inside = [t for t in live if free(t) and t.kind == "text" and not t.fill and _inside(t, r)]
        if len(inside) == 1 and len(inside[0].paras) <= 2 and not any(p.marker for p in inside[0].paras):
            bars.append((r, inside[0]))
    if not bars:
        return
    bar, txt = max(bars, key=lambda b: b[0].y)
    if any(  # another bar of this fill and width: a stack of rows, not a takeaway
        o is not bar
        and _is_hex(o.fill)
        and o.kind in ("shape", "text")
        and _dist(o.fill.upper(), bar.fill.upper()) <= TH3.same_fill
        and abs(o.w - bar.w) <= TH3.same * bar.w
        and o.h > 0.3 * bar.h
        for o in live
    ):
        return
    below = [
        i
        for i in live
        if i is not bar
        and i is not txt
        and i.kind != "shape"
        and i.cy > bar.y + 0.5 * bar.h
        and i.y < TH3.footer_y * H
    ]
    if below:
        return
    if txt is None:
        bar.name = "Conclusion"
        claim(bar, "conclusion")
        src = bar
    else:
        data.items[:] = [i for i in data.items if i is not txt and i is not bar]
        merged = replace(
            txt, fill=bar.fill, x=bar.x, y=bar.y, w=bar.w, h=bar.h, name="Conclusion", line=bar.line
        )
        claim(merged, "conclusion")
        data.items.append(merged)
        src = txt
    _put(found, "conclusion.fill", name_or_hex(deck, bar.fill))
    if sz := _modal(_sizes(src.paras)):
        _put(found, "conclusion.size", f"{sz:g}")


# --------------------------------------------------------------------------- entry


def recognise(data: SlideData, deck, n: int, found: Found) -> None:
    """Read the four forms (in this order: the first to claim a shape owns it); ``found`` collects the
    ``style:`` tokens. Never raises."""
    if not is_foreign(deck):
        return
    for step in (_steps, _kpi, _bands, _bar):
        try:
            step(data, deck, found)
        except Exception:  # a foreign deck never makes the import fail
            continue


__all__ = ["TH3", "recognise"]
