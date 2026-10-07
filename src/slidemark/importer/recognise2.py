"""Geometry-based recognition of a foreign deck's design (DL3d, lane C).

A deck made elsewhere draws its design with loose shapes: a chevron row with a card under each arrow, a dark
bar at the bottom, a highlighted table row, a chart with per-bar colours, a slide-filling rectangle behind the
cover. SlideMark states each of these in a token, so the importer recognises them from geometry and writes
the token instead of the boxes. Every recognition is conservative (it fires only when the geometry matches,
else the older fallback stays), works on foreign decks only (a deck with its own design part says its design
itself) and never raises. All thresholds are in one table, ``T``.

Entry points: ``recognise`` (one slide, from ``structure.build_slide``), ``deck_tokens`` (deck-wide chrome,
from the importer header), ``read_chart_look`` (chart fills and label size, from ``read.read_chart``).
"""

from __future__ import annotations

import functools
import re
from dataclasses import dataclass, field, replace

from .look import _contrast, _dist, _lum
from .read import Item, ParaT, SlideData
from .runs import claim, free, is_foreign, span_runs

CHEVRON_PRST = ("chevron", "homePlate", "pentagon")
_HEX = re.compile(r"^[0-9A-Fa-f]{6}$")
_DIGITS = re.compile(r"^\d{1,3}$")


@dataclass(frozen=True)
class Thresholds:
    """Every geometric decision of this module (shares of the slide width / height unless noted)."""

    bleed: float = 0.90  # area share of a slide-filling rectangle (the background)
    edge: float = 0.01  # a shape this close to a slide edge touches it
    strip_w: float = 0.94  # width share of a full-width strip
    strip_h: float = 0.06  # a strip on the top / bottom edge is at most this high (more = a band)
    band_h: float = 0.2  # a title band is at most this high
    cover_strip_h: float = 0.2  # ... on the cover (a foot band can be thick)
    rule_h: float = 0.025  # a rule under the title is at most this high
    rule_y: tuple = (0.05, 0.3)  # ... and starts between these shares of the height
    rule_full: float = 0.8  # a rule this wide (the title's inner width, or the slide's) is the title rule
    rule2_w: float = 0.5  # a short rule segment is at most this wide
    chrome_share: float = 0.4  # chrome (strip, rule, page number) must repeat on this share of the slides
    bar_w: float = 0.04  # a vertical bar is at most this wide
    bar_h: tuple = (0.1, 0.95)  # ... and this high (a full-height bar is an edge bar)
    page_y: float = 0.88  # a page number text starts below this height
    page_h: float = 0.1  # ... and is at most this high
    row_dy: float = 0.15  # chevrons of one row: centres within this share of their height
    same: float = 0.06  # equal sizes / positions within this share (chevron width, card x)
    card_gap: float = 0.15  # a card starts within this share of the height below its arrow
    bar_min_w: float = 0.75  # a takeaway bar is at least this wide
    bar_min_y: float = 0.55  # ... starts below this share of the height
    bar_max_h: float = 0.25  # ... and is at most this high
    footer_y: float = 0.9  # items from here down are footer chrome
    tint_sat: float = 0.06  # an emphasised table row is tinted: HSV saturation at least this
    bar_lum: float = 0.25  # a takeaway bar is dark: relative luminance below this
    near: float = 40.0  # two colours closer than this (RGB distance) are the same ink
    same_fill: float = 12.0  # two fills closer than this are the same fill
    name_dist: float = 6.0  # a colour this close to a declared one is written with its name
    span_dsize: float = 1.0  # a run this many pt off the first run's size gets ``size=``
    panel_dy: float = 0.5  # a panel overlaps its chart on this share of the card height
    panel_h: float = 0.7  # ... and is at least this share of the chart height (smaller cards are tiles)
    gap_tol: int = 2  # a chart gap within this of the build default is not stated


T = Thresholds()


@dataclass
class Found:
    """What ``recognise`` tells ``build_slide``: slide words (``bg=primary dark``) and a ``style:`` line."""

    words: list[str] = field(default_factory=list)
    style: dict[str, str] = field(default_factory=dict)

    def style_line(self) -> str | None:
        return "style: " + " ".join(f"{k}={v}" for k, v in self.style.items()) if self.style else None


# --------------------------------------------------------------------------- colour helpers


def _is_hex(v: str | None) -> bool:
    return bool(v) and bool(_HEX.match(v or ""))


_NAMES = ("primary", "secondary", "accent", "danger", "success", "muted", "fg", "bg", "surface")


def name_or_hex(deck, hexv: str, near: bool = False) -> str:
    """A declared colour name when ``hexv`` is one of the deck's colours (``near``: or within ``T.name_dist``
    of one, for text ink, where the eye cannot tell them apart), else ``#RRGGBB``."""
    h = hexv.lstrip("#").upper()
    named = [(n, v) for n in _NAMES if (v := deck.colors.get(n, ""))]
    named += [
        (n, v) for n, v in deck.colors.items() if n not in _NAMES and re.fullmatch(r"[A-Za-z][\w-]*", n)
    ]
    for n, v in named:
        if v.upper() == h:
            return n
    close = [(_dist(h, v.upper()), n) for n, v in named if _is_hex(v)] if near else []
    best = min(close, default=(1e9, ""))
    return best[1] if best[0] <= T.name_dist else "#" + h


def _sat(h: str) -> float:
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return (max(r, g, b) - min(r, g, b)) / max(r, g, b, 1)


def _length(emu: float) -> str:
    return f"{round(emu / 914400, 2):g}in"


def _shape(it: Item) -> bool:
    return it.kind == "shape" and _is_hex(it.fill) and not it.paras


def _safe(default):
    """A helper the importer calls outside ``recognise``: any error means ``default`` (never raise)."""

    def deco(fn):
        @functools.wraps(fn)
        def inner(*a, **k):
            try:
                return fn(*a, **k)
            except Exception:
                return default

        return inner

    return deco


def _foreign_name(it: Item) -> bool:
    """False for a shape SlideMark itself drew (its names are folded by name elsewhere)."""
    return not re.match(
        r"(Step|Row|Item|Card|Num|num|KPI|Timeline|Funnel|Cycle|Agenda|Split|Conclusion)\b", it.name or ""
    )


# --------------------------------------------------------------------------- entry points


def recognise(data: SlideData, deck, n: int) -> Found:
    """Recognise the slide's designed shapes; renames / merges items in place and returns tokens to write."""
    found = Found()
    if not is_foreign(deck):
        return found
    for step in (_page_number, _cover_background, _chevron_steps, _takeaway_bar, _tables, _charts, _panels):
        try:
            step(data, deck, n, found)
        except Exception:  # a foreign deck never makes the import fail
            continue
    return found


# --------------------------------------------------------------------------- 4. backgrounds and chrome


def is_page_number(it: Item, n: int, W: int, H: int) -> bool:
    """A loose text at the bottom whose only content is the slide number."""
    return (
        it.kind == "text"
        and it.ph is None
        and not it.fill
        and it.y >= T.page_y * H
        and it.h <= T.page_h * H
        and bool(_DIGITS.match(it.text.strip()))
        and int(it.text.strip()) == n
    )


def _page_number(data: SlideData, deck, n: int, found: Found) -> None:
    for it in data.items:
        if it.role is None and is_page_number(it, n, deck.width, deck.height):
            it.role = "decor"


@_safe(False)
def has_page_numbers(datas: list[SlideData], W: int, H: int) -> bool:
    """A loose number text on at least half of the slides after the first (a hand-drawn slide number)."""
    rest = list(enumerate(datas, 1))[1:]
    hits = sum(any(is_page_number(it, k, W, H) for it in sd.items) for k, sd in rest)
    return bool(rest) and hits >= max(1, len(rest) / 2)


def _bleed(data: SlideData, W: int, H: int) -> Item | None:
    best = None
    for it in data.items:
        if (
            _shape(it)
            and it.area >= T.bleed * W * H
            and it.x <= T.edge * W
            and it.y <= T.edge * H
            and _foreign_name(it)
            and (best is None or it.area > best.area)
        ):
            best = it
    return best


def _cover_background(data: SlideData, deck, n: int, found: Found) -> None:
    bg = _bleed(data, deck.width, deck.height)
    if bg is None or _dist(bg.fill.upper(), deck.colors.get("bg", "FFFFFF")) <= T.same_fill:
        return
    bg.role = "decor"
    found.words.append("bg=" + name_or_hex(deck, bg.fill))
    if _lum(bg.fill.upper()) < 0.2:
        found.words.append("dark")


def _strips(data: SlideData, W: int, H: int, bg: Item | None, tall: float) -> list[tuple[str, Item]]:
    """Full-width filled strips touching the top or bottom edge: ("top" | "bottom", item)."""
    out = []
    for it in data.items:
        if it is bg or not _shape(it) or not _foreign_name(it) or it.w < T.strip_w * W or it.h > tall * H:
            continue
        if it.y <= T.edge * H:
            out.append(("top", it))
        elif it.y + it.h >= (1 - T.edge) * H:
            out.append(("bottom", it))
    return out


def _cover_chrome(data: SlideData, deck_w: int, deck_h: int, colors: dict) -> dict[str, str]:
    """Cover tokens of a slide with a slide-filling rectangle: the band is off (the rectangle is the
    background), the title block sits where the original text does, and the bars / strips drawn over it."""
    W, H = deck_w, deck_h
    bg = _bleed(data, W, H)
    if bg is None or _dist(bg.fill.upper(), colors.get("bg", "FFFFFF")) <= T.same_fill:
        return {}
    out: dict[str, str] = {"cover.band": "none"}
    texts = [
        i
        for i in data.items
        if i.kind == "text" and i.role is None and i.paras and i.y < T.footer_y * H and i.ph != "ftr"
    ]
    rule = next(
        (
            it
            for it in data.items
            if it is not bg
            and _shape(it)
            and _foreign_name(it)
            and it.w >= T.rule_full * W
            and it.h <= T.rule_h * H
            and 0.2 * H <= it.y <= 0.9 * H
        ),
        None,
    )  # a full-width line across the cover: the edge of the band (`cover.rule` is drawn on it)
    if texts:
        bottom = 0.0
        for i in texts:
            lines = max(len(i.paras), 1)
            size = (i.max_size or 18) * 12700 * 1.25
            bottom = max(bottom, i.cy + lines * size / 2)  # text is centred in its box: the ink bottom
        pad = 0.6 * 914400
        edge = rule.y if rule is not None and rule.y > bottom else bottom + pad
        if rule is not None and rule.y > bottom:
            pad = rule.y - bottom
            out["cover.pad"] = _length(max(pad, 0.1 * 914400))
        out["cover.band_h"] = f"{min(max(edge / H, 0.2), 0.9) * 100:.0f}%"
    if rule is not None:
        out["cover.rule"] = f"#{rule.fill.upper()}"
        out["cover.rule_h"] = _length(rule.h)
    first_text_x = min((i.x for i in texts), default=0)
    for it in data.items:
        if it is bg or not _shape(it) or not _foreign_name(it):
            continue
        if it.w <= T.bar_w * W and T.bar_h[0] * H <= it.h <= H:  # a vertical bar
            if it.x <= T.edge * W and it.h >= T.bar_h[1] * H:
                out["cover.bar"] = f"#{it.fill.upper()}@edge"
                out["cover.bar_w"] = _length(it.w)
            elif it.x < first_text_x and "cover.bar" not in out and it.h < T.bar_h[1] * H:
                out["cover.bar"] = f"#{it.fill.upper()}"
                out["cover.bar_w"] = _length(it.w)
    for where, it in _strips(data, W, H, bg, T.cover_strip_h):
        out[f"cover.{where}_bar"] = f"#{it.fill.upper()}"
        out[f"cover.{where}_bar_h"] = _length(it.h)
    return out


def _band_candidates(data: SlideData, W: int, H: int) -> list[Item]:
    """A filled strip across the top that is thicker than an edge bar: the title band."""
    return [
        it
        for it in data.items
        if _shape(it)
        and _foreign_name(it)
        and it.w >= T.strip_w * W
        and it.y <= T.edge * H
        and T.strip_h * H < it.h <= T.band_h * H
    ]


def _rule_candidates(data: SlideData, W: int, H: int) -> list[Item]:
    return [
        it
        for it in data.items
        if _shape(it)
        and _foreign_name(it)
        and it.h <= T.rule_h * H
        and it.x <= T.edge * W + 0.1 * W
        and T.rule_y[0] * H <= it.y <= T.rule_y[1] * H
    ]


def _repeating(per_slide: list[list[Item]], slides: int) -> list[Item] | None:
    """The items of the first slide's list that every kind of slide share: the fill + height repeats on at
    least ``chrome_share`` of the slides. Returns one representative per distinct (fill, y) group."""
    groups: dict[tuple, list[Item]] = {}
    for items in per_slide:
        seen = set()
        for it in items:
            key = (it.fill.upper(), round(it.y / 91440), round(it.w / 91440))
            if key not in seen:
                groups.setdefault(key, []).append(it)
                seen.add(key)
    best = [v for v in groups.values() if len(v) >= max(2, T.chrome_share * slides)]
    return [v[0] for v in best] or None


def deck_tokens(datas: list[SlideData], deck) -> dict[str, str]:
    """Deck-wide chrome as token paths: cover decoration, edge bars, the title rule, the chevron shape."""
    out: dict[str, str] = {}
    W, H = deck.width, deck.height
    try:
        if datas:
            out.update(_cover_chrome(datas[0], W, H, deck.colors))
        body = [sd for k, sd in enumerate(datas) if k > 0 or _bleed(sd, W, H) is None]
        if body:
            for where in ("top", "bottom"):
                got = _repeating(
                    [[it for w, it in _strips(sd, W, H, None, T.strip_h) if w == where] for sd in body],
                    len(body),
                )
                if got:
                    out[f"{where}.bar"] = "#" + got[0].fill.upper()
                    out[f"{where}.bar_h"] = _length(got[0].h)
            bands = _repeating([_band_candidates(sd, W, H) for sd in body], len(body))
            rules = _repeating([_rule_candidates(sd, W, H) for sd in body], len(body))
            full_rule = next((it for it in rules or [] if it.w >= T.rule_full * W), None)
            if bands and deck.margin_y:  # the band's bottom edge is where the title area ends
                out["title.height"] = _length(max(bands[0].h - deck.margin_y // 2, 0.3 * 914400))
            elif full_rule is not None and deck.margin_y:
                out["title.height"] = _length(max(full_rule.y + full_rule.h - deck.margin_y, 0.3 * 914400))
            if rules:
                full = [it for it in rules if it.w >= T.rule_full * W]
                short = [it for it in rules if it.w <= T.rule2_w * W]
                if full:
                    out["title.rule"] = "#" + full[0].fill.upper()
                    out["title.rule_h"] = _length(full[0].h)
                if short:
                    out["title.rule2"] = "#" + short[0].fill.upper()
                    out["title.rule2_w"] = _length(short[0].w)
                    out.setdefault("title.rule_h", _length(short[0].h))
        shapes = {
            it.prst
            for sd in datas
            for it in sd.items
            if it.prst in CHEVRON_PRST and it.paras and _is_hex(it.fill)
        }
        if shapes and shapes <= {"homePlate", "pentagon"}:
            out["render.chevron_shape"] = "pentagon"
    except Exception:
        return {}
    return out


# --------------------------------------------------------------------------- 1. chevron sequence


def _chevron_steps(data: SlideData, deck, n: int, found: Found) -> None:
    H = deck.height
    chevs = [
        i
        for i in data.items
        if i.prst in CHEVRON_PRST and i.paras and _is_hex(i.fill) and _foreign_name(i) and i.role is None
    ]
    if len(chevs) < 2:
        return
    chevs.sort(key=lambda i: i.x)
    c0 = chevs[0]
    row = [
        c
        for c in chevs
        if abs(c.cy - c0.cy) <= T.row_dy * c0.h
        and abs(c.w - c0.w) <= T.same * c0.w
        and abs(c.h - c0.h) <= T.same * c0.h
    ]
    if len(row) != len(chevs):
        return  # two rows, or sizes that differ: not one sequence
    cards: list[Item] = []
    for c in row:
        under = [
            s
            for s in data.items
            if _shape(s)
            and s is not c
            and _foreign_name(s)
            and abs(s.x - c.x) <= T.same * c.w
            and abs(s.w - c.w) <= T.same * c.w
            and c.y + c.h - 0.02 * H <= s.y <= c.y + c.h + T.card_gap * H
            and s.h > 0.5 * c.h
        ]
        if not under:
            return  # an arrow without a card stays a plain chevron row
        cards.append(min(under, key=lambda s: s.y))
    if len({id(c) for c in cards}) != len(cards):
        return
    arrows = [c.fill.upper() for c in row]
    for k, (a, card) in enumerate(zip(row, cards, strict=True), 1):
        a.name, card.name = f"Step {k} arrow", f"Step {k} card"
        claim(a, "steps")  # (recognise.py leaves the steps to this module)
        claim(card, "steps")
    if any(_dist(a, deck.colors.get("primary", "")) > T.same_fill for a in arrows):
        found.style["steps-arrow.fill"] = ",".join(name_or_hex(deck, a) for a in arrows)
    asz = _modal([r.size for a in row for p in a.paras for r in p.runs if r.size and r.text.strip()])
    if asz:
        found.style["steps-arrow.size"] = f"{asz:g}"
    ink = _modal(
        [r.color.upper() for a in row for p in a.paras for r in p.runs if r.text.strip() and r.color]
    )
    if ink:
        found.style["steps-arrow.color"] = name_or_hex(deck, ink)
    if all(r.bold for a in row for p in a.paras for r in p.runs if r.text.strip()):
        found.style["steps-arrow.bold"] = "on"
    if all(p.align == "l" for a in row for p in a.paras if p.plain.strip()):
        found.style["steps-arrow.align"] = "left"
    inside = [
        t
        for t in data.items
        if t.kind == "text"
        and t not in row
        and any(c.x <= t.cx <= c.x + c.w and c.y <= t.cy <= c.y + c.h for c in cards)
    ]
    for t in inside:
        claim(t, "steps")
    csz = _modal([r.size for t in inside for p in t.paras for r in p.runs if r.size and r.text.strip()])
    if csz:
        found.style["steps-card.size"] = f"{csz:g}"
    fills = {c.fill.upper() for c in cards}
    surf = deck.colors.get("surface", "")
    if len(fills) == 1 and _dist(next(iter(fills)), surf) > T.same_fill:
        found.style["steps-card.fill"] = name_or_hex(deck, next(iter(fills)))
    # exact geometry (DL3d part 2): the layout chooses these itself, the original states them
    found.style["steps-arrow.h"] = _length(_modal([float(c.h) for c in row]) or row[0].h)
    found.style["steps-card.h"] = _length(_modal([float(c.h) for c in cards]) or cards[0].h)
    gaps = [float(k.y - (a.y + a.h)) for a, k in zip(row, cards, strict=True)]
    found.style["steps.gap"] = _length(max(_modal(gaps) or 0.0, 0.0))
    below = [
        b
        for b in data.items
        if b.kind in ("shape", "text")
        and _is_hex(b.fill)
        and _foreign_name(b)
        and b.role is None
        and b not in row
        and b not in cards
        and b.y >= max(k.y + k.h for k in cards) - 0.02 * H
        and b.w >= T.bar_min_w * deck.width
        and b.h <= T.bar_max_h * H
        and b.y + b.h <= T.footer_y * H
        and _lum(b.fill.upper()) < T.bar_lum
    ]
    if below:  # the takeaway bar under the cards (the next step claims it as the conclusion)
        found.style["conclusion.h"] = _length(min(below, key=lambda b: b.y).h)


# --------------------------------------------------------------------------- 1b. takeaway bar


def _modal(sizes: list[float]) -> float | None:
    """The commonest value (the larger on a tie), None for an empty list."""
    return max(set(sizes), key=lambda v: (sizes.count(v), v)) if sizes else None


def _repeats(bar: Item, live: list[Item]) -> bool:
    """Another filled item of the same fill and width: the bar is one of a stack of rows, not a takeaway."""
    return any(
        o is not bar
        and _is_hex(o.fill)
        and o.kind in ("shape", "text")
        and _dist(o.fill.upper(), bar.fill.upper()) <= T.same_fill
        and abs(o.w - bar.w) <= T.same * bar.w
        and o.h > 0.3 * bar.h
        for o in live
    )


def _takeaway_bar(data: SlideData, deck, n: int, found: Found) -> None:
    W, H = deck.width, deck.height
    live = [i for i in data.items if i.role is None]
    if any((i.name or "").lower().startswith("conclusion") for i in data.items):
        return
    bars: list[tuple[Item, Item | None]] = []
    for r in live:
        if not (
            _is_hex(r.fill)
            and r.kind in ("shape", "text")
            and _foreign_name(r)
            and r.w >= T.bar_min_w * W
            and r.y >= T.bar_min_y * H
            and r.h <= T.bar_max_h * H
            and r.y + r.h <= T.footer_y * H
        ):
            continue
        if r.kind == "text":
            if len(r.paras) <= 2 and not any(p.marker for p in r.paras):
                bars.append((r, None))
            continue
        inside = [
            t
            for t in live
            if t.kind == "text" and not t.fill and r.x <= t.cx <= r.x + r.w and r.y <= t.cy <= r.y + r.h
        ]
        if len(inside) == 1 and len(inside[0].paras) <= 2 and not any(p.marker for p in inside[0].paras):
            bars.append((r, inside[0]))
    bars = [(r, t) for r, t in bars if _lum(r.fill.upper()) < T.bar_lum and not _repeats(r, live)]
    if not bars:
        return
    bar, txt = max(bars, key=lambda b: b[0].y)
    below = [
        i
        for i in live
        if i is not bar
        and i is not txt
        and i.kind != "shape"
        and i.cy > bar.y + 0.5 * bar.h
        and i.y < T.footer_y * H
        and not (i.kind == "text" and not i.fill and i.y >= T.footer_y * H)
    ]
    if below:
        return
    if txt is None:
        bar.name = "Conclusion"
        claim(bar, "conclusion")
    else:
        data.items[:] = [i for i in data.items if i is not txt and i is not bar]
        merged = replace(
            txt, fill=bar.fill, x=bar.x, y=bar.y, w=bar.w, h=bar.h, name="Conclusion", line=bar.line
        )
        claim(merged, "conclusion")
        data.items.append(merged)
    if _dist(bar.fill.upper(), deck.colors.get("primary", "")) > T.same_fill:
        found.style["conclusion.fill"] = name_or_hex(deck, bar.fill)
    sz = _modal([r.size for p in (txt or bar).paras for r in p.runs if r.size and r.text.strip()])
    if sz:
        found.style["conclusion.size"] = f"{sz:g}"


# --------------------------------------------------------------------------- 2. tables


def _row_fill(row) -> str | None:
    """The one fill a whole row shares (None when its cells differ or carry no fill)."""
    fills = {c.fill.upper() for c in row if c.fill}
    return next(iter(fills)) if len(fills) == 1 and all(c.fill for c in row) else None


def emphasised_rows(rows, header_rows: int, deck) -> tuple[list[int], str | None]:
    """Body rows that share one tinted fill unlike the other body rows (the zebra / body fills)."""
    body = list(range(header_rows, len(rows)))
    fills = {ri: _row_fill(rows[ri]) for ri in body}
    if len(body) < 2 or any(f is None for f in fills.values()):
        return [], None
    bgc = deck.colors.get("bg", "FFFFFF")
    count: dict[str, int] = {}
    for f in fills.values():
        count[f] = count.get(f, 0) + 1
    # the zebra pair is the (at most two) fills that are not a tint: close to white / the surface
    plain = {f for f in count if _sat(f) < T.tint_sat or _dist(f, bgc) <= T.same_fill}
    odd = [ri for ri in body if fills[ri] not in plain]
    if not odd or not plain or len(odd) > len(body) // 2 or len({fills[ri] for ri in odd}) != 1:
        return [], None
    return odd, fills[odd[0]]


def zebra_pair(rows, header_rows: int, skip: set[int], deck) -> tuple[str, str] | None:
    """(body fill, zebra fill) when the body rows alternate between two plain fills (``skip``: hl rows)."""
    even: set[str] = set()
    odd: set[str] = set()
    n = 0
    bgc = deck.colors.get("bg", "FFFFFF")
    for ri in range(header_rows, len(rows)):
        if ri in skip:
            continue
        f = _row_fill(rows[ri])
        if f is None:
            return None
        (odd if (ri - header_rows) % 2 else even).add(f)
        n += 1
    if n < 2 or len(even) != 1 or len(odd) != 1:
        return None
    a, b = next(iter(even)), next(iter(odd))
    plain = all(_sat(f) < T.tint_sat or _dist(f, bgc) <= T.same_fill for f in (a, b))
    return (a, b) if plain and _dist(a, b) > T.same_fill else None


@_safe("")
def deck_ink(datas: list[SlideData], bg: str, H: int) -> str:
    """The commonest run colour (by characters) that reads on the background: the deck's body ink (footers
    and page numbers at the bottom are not body text)."""
    count: dict[str, int] = {}
    for sd in datas:
        for it in sd.items:
            paras = [p for r in it.rows for c in r for p in c.paras] if it.kind == "table" else it.paras
            if (
                it.kind in ("text", "table")
                and it.y < T.footer_y * H
                and not (it.fill and _lum(it.fill.upper()) < 0.2)
            ):
                for p in paras:
                    for r in p.runs:
                        if r.color and _contrast(r.color, bg) >= 3.0:
                            count[r.color] = count.get(r.color, 0) + len(r.text.strip())
    return max(count, key=lambda c: count[c]) if count else ""


def _tag_spans(paras: list[ParaT], deck, base_size: float | None = None, multi_only: bool = False) -> None:
    """Runs of another size or colour than the text around them get ``size=`` / ``color=`` (span syntax).

    ``base_size`` is the size the container's text already has (a table's ``size=``); without it the first
    run's size is the base. The reference colour is the deck ink (``fg``). ``multi_only`` leaves a text of one
    run alone (a heading, a lone number)."""
    runs = [r for p in paras for r in p.runs if r.text.strip()]
    if not runs:
        return
    base_pt = base_size or runs[0].size
    ink = deck.ink or deck.colors.get("fg", "")
    accent = (deck.accent or "").split("|")
    markup = (deck.colors.get("success"), deck.colors.get("danger"))  # colours the markup already says

    def color_of(r) -> str | None:
        handled = r.color is not None and (r.color in accent or r.color in markup)
        if r.color and not handled and not r.badge and ink and _dist(r.color, ink) > T.near:
            return name_or_hex(deck, r.color, near=True)
        return None

    span_runs(
        paras,
        size_off=lambda r: bool(base_pt) and abs(r.size - base_pt) >= T.span_dsize,
        color_of=color_of,
        multi_only=multi_only,
    )


def _tables(data: SlideData, deck, n: int, found: Found) -> None:
    from ..layout.tablehl import join_names
    from .emit import header_rows_of, hl_row_set

    for it in data.items:
        if it.kind != "table" or not it.rows:
            continue
        hdr = header_rows_of(it.rows)
        if not it.hl:
            odd, fill = emphasised_rows(it.rows, hdr, deck)
            names = ["".join(p.plain for p in it.rows[ri][0].paras).strip() for ri in odd]
            if odd and all(names) and len(set(names)) == len(names):
                it.hl = join_names(names)
                found.style["table.hl.fill"] = name_or_hex(deck, fill)
                found.style["table.hl.strength"] = "1"
        zp = zebra_pair(it.rows, hdr, set(hl_row_set(it.rows, it.hl, hdr)) if it.hl else set(), deck)
        if zp is not None:
            it.zebra = True
            found.style["table.zebra.fill"] = name_or_hex(deck, zp[1])
            if _dist(zp[0], deck.colors.get("bg", "FFFFFF")) > T.same_fill:
                found.style["table.body.fill"] = name_or_hex(deck, zp[0])
        firsts = [
            r.size
            for row in it.rows[hdr:]
            for c in row
            for r in next(((p.runs[:1]) for p in c.paras if p.runs and p.plain.strip()), [])
            if r.size
        ]
        if firsts:  # the table's text size: the commonest size a body cell starts with (the larger on a tie)
            it.size = max(set(firsts), key=lambda v: (firsts.count(v), v))
        for ri in range(hdr, len(it.rows)):
            for c in it.rows[ri]:
                _tag_spans(c.paras, deck, it.size)


# --------------------------------------------------------------------------- 3. charts and the panel


def _fill_hex(sp) -> str | None:
    """RRGGBB of a ``c:spPr`` solid fill (a line chart: its ``a:ln`` colour)."""
    if sp is None:
        return None
    for path in ("./a:solidFill/a:srgbClr/@val", "./a:ln/a:solidFill/a:srgbClr/@val"):
        got = sp.xpath(path)
        if got and _is_hex(str(got[0])):
            return str(got[0]).upper()
    return None


def read_chart_look(chart, kind: str, nser: int, ncat: int) -> dict:
    """Series fills, per-point fills, data-label size, chart text size and gap width of a chart's XML."""
    from pptx.oxml.ns import qn

    look: dict = {}
    try:
        cs = chart._chartSpace
        plots = [p for p in cs.xpath(".//c:plotArea/*") if p.find(qn("c:ser")) is not None]
        if not plots:
            return {}
        plot = plots[0]
        sers = plot.findall(qn("c:ser"))
        look["series"] = [_fill_hex(s.find(qn("c:spPr"))) for s in sers]
        look["points"] = [
            {
                int(d.find(qn("c:idx")).get("val")): _fill_hex(d.find(qn("c:spPr")))
                for d in s.findall(qn("c:dPt"))
                if d.find(qn("c:idx")) is not None
            }
            for s in sers
        ]
        sz = plot.xpath("./c:dLbls/c:txPr//a:defRPr/@sz")
        if sz:
            look["label_size"] = int(sz[0]) / 100
        base = cs.xpath("./c:txPr//a:defRPr/@sz")
        if base:
            look["chart_size"] = int(base[0]) / 100
        gap = plot.find(qn("c:gapWidth"))
        if gap is not None and gap.get("val"):
            look["gap"] = int(gap.get("val"))
    except Exception:
        return {}
    return look


def _chart_colors(look: dict, kind: str, nser: int, ncat: int, palette: list[str]) -> list[str] | None:
    """The ``colors=`` list (RRGGBB) a chart states beyond the build's default palette, or None."""
    series = look.get("series") or []
    points = look.get("points") or []
    if not series or not palette:
        return None
    pal = [p.upper() for p in palette]

    def default(i: int) -> str:
        return pal[i % len(pal)]

    if kind in ("pie", "doughnut"):
        pts = points[0] if points else {}
        if not any(pts.values()):
            return None
        got = [pts.get(i) or default(i) for i in range(ncat)]
        return got if got != [default(i) for i in range(ncat)] else None
    if nser == 1 and kind in ("bar", "column"):
        base = series[0] or default(0)
        pts = points[0] if points else {}
        if any(pts.values()):
            got = [pts.get(i) or base for i in range(ncat)]
            return got if got != [default(0)] * ncat else None
        return [base] if base != default(0) else None
    got = [series[i] if i < len(series) and series[i] else default(i) for i in range(nser)]
    if len(got) == nser and got != [default(i) for i in range(nser)]:
        return got
    return None


def _charts(data: SlideData, deck, n: int, found: Found) -> None:
    from ..theme import RenderTokens

    for it in data.items:
        ch = it.chart
        if it.kind != "chart" or ch is None or not ch.look:
            continue
        look, opts = ch.look, ch.options
        nser, ncat = len(ch.series), len(ch.categories)
        cols = _chart_colors(look, ch.kind, nser, ncat, getattr(deck, "palette", []))
        if cols and "colors" not in opts:
            opts["colors"] = ",".join(name_or_hex(deck, c) for c in cols)
        size = look.get("label_size") or look.get("chart_size")
        if size and "size" not in opts:
            opts["size"] = f"{size:g}"
        gap = look.get("gap")
        if gap is not None and "gap" not in opts and ch.kind not in ("pie", "doughnut"):
            default = getattr(RenderTokens(), "chart_gap", None)
            if default is None or abs(gap - default) > T.gap_tol:
                opts["gap"] = str(gap)


def _panels(data: SlideData, deck, n: int, found: Found) -> None:
    """The one big card beside a chart (a total, then coloured values): runs of another size or colour in its
    texts become spans. Several small cards beside a chart are tiles, not a panel."""
    for chart in (i for i in data.items if i.kind == "chart"):
        cards = [
            c
            for c in data.items
            if _shape(c)
            and _foreign_name(c)
            and c.h >= T.panel_h * chart.h
            and not (chart.x <= c.cx <= chart.x + chart.w)
            and min(c.y + c.h, chart.y + chart.h) - max(c.y, chart.y) >= T.panel_dy * c.h
        ]
        if len(cards) != 1:
            continue
        card = cards[0]
        if not free(card):
            continue
        claim(card, "chartpanel")  # (recognise.py's dark panel / tiles skip it)
        for t in data.items:
            if t.kind == "text" and t.role is None and card.x <= t.cx <= card.x + card.w:
                if card.y <= t.cy <= card.y + card.h:
                    claim(t, "chartpanel")
                    _tag_spans(t.paras, deck, multi_only=True)
