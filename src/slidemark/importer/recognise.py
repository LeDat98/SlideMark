"""Geometry-based recognition of forms in a deck made elsewhere (DL3d lane B).

``vocab.py`` / ``forms2.py`` read shapes SlideMark named itself. A foreign deck (python-pptx, PowerPoint)
draws the same forms with unnamed rectangles and text boxes; ``recognise`` reads their geometry and prepares
the slide so the usual importer path writes the form:

* **quote card**  a big quote glyph + one text + an attribution line ``— Name``  -> the ``Quote *`` names
  ``forms2`` folds into ``@quote`` (``quote.mark.color`` rides in a slide ``style:`` line);
* **numbered bars and cards**  a small filled shape holding only a number, inside a wide bar or above a card
  body -> ``@rows`` (the slide is bars only: shapes renamed ``Row N`` / ``Row N num``, ``rows-num.fill=`` the
  badge colours) or the slide word ``num`` (badges dropped, ``box.num.fill=``);
* **number tiles**  a card whose first line is a short figure in a much larger size than the rest -> a
  label-less ``##`` card under ``@kpi`` (stripe and figure colours as tokens), or, when the figures are
  ``01 02 03``, a number heading (``sizes: heading=44!``, colour span);
* **dark statement panel**  a dark filled rectangle holding 3-7 short lines of different sizes -> one box
  whose lines carry their own sizes as spans (``[9,800円]{size=40 bold=true}``);
* **big-number bars**  filled bars with a left stripe whose one line mixes label, figure and note sizes ->
  ``@rows plain`` with ``rows.stripe=`` (bars alone on the slide) or boxes with a stripe class.

Everything is conservative: a form fires only when every card of its group matches, otherwise the slide keeps
the plain reading. All thresholds are in ``TH``. The step results are carried on the items (``rec``,
``rec_attrs``, ``RunT.span``) and on ``SlideData.style_lines`` / ``words``; ``structure.py`` only calls
``recognise`` before the title is chosen and prints what it left.
"""

from __future__ import annotations

import re
from dataclasses import replace

from .emit import one_line, text_lines
from .read import Item, ParaT, RunT, SlideData
from .runs import claim, free, is_foreign, put_span, span_runs

# every threshold of the recognisers (fractions of the slide width W / height H unless named otherwise)
TH = {
    "card_min_area": 0.025,  # a card covers at least this share of the slide ...
    "card_max_area": 0.62,  # ... and at most this share
    "card_max_w": 0.97,  # a card narrower than the slide (full-width bands are chrome)
    "body_top": 0.16,  # the body starts below this share of H (title zone above)
    "body_bottom": 0.93,  # ... and ends above this one (footer zone below)
    "align_tol": 0.012,  # edges of a stripe and its card agree within this share of W (H for y)
    "stripe_max": 0.03,  # a stripe is thinner than this share of the slide side ...
    "stripe_card": 0.22,  # ... and than this share of the card side it runs along
    "kpi_ratio": 1.8,  # the figure is at least this much larger than the rest of the tile
    "index_ratio": 1.2,  # a number heading (01 02 03) is at least this much larger than the body
    "num_chars": 10,  # a figure / number token has at most this many characters
    "num_unit": 3,  # ... and at most this many non-digit characters (units: 兆円 % 億円)
    "group_size_tol": 0.12,  # cards of one group differ in width and height by at most this share
    "group_max": 8,  # a group has at most this many cards
    "badge_max": 0.17,  # a badge is at most this share of W wide / tall
    "badge_min_in": 0.3,  # ... and at least this many inches
    "badge_aspect": (0.55, 1.8),  # w / h of a badge
    "bar_min_w": 0.45,  # a bar of `@rows` is at least this share of W wide
    "badge_edge": 0.12,  # the badge sits within this share of the bar width from its left edge
    "dark_lum": 0.32,  # a dark panel: relative luminance of the fill below this
    "panel_area": 0.035,  # a statement panel covers at least this share of the slide
    "panel_paras": (3, 7),  # ... holds this many lines
    "panel_chars": 40,  # ... each at most this long
    "panel_ratio": 1.4,  # ... and the largest is this much bigger than the smallest
    "bigrow_ratio": 1.25,  # a big-number bar: its largest run vs its smallest
    "span_tol": 0.08,  # a run differing from the base size by less than this share gets no size span
    "quote_mark_pt": 40,  # a quote glyph is at least this big
    "quote_by_chars": 80,
}

QUOTE_MARKS = {"“", '"', "「", "『", "”", "„", "‟"}
DASHES = ("—", "―", "-", "–", "−", "─", "ー", "─")
_NUMBERISH = re.compile(r"\d")
_STRIP_NUM = re.compile(r"[\d,.\s+\-−%％¥￥$▲△▼]")
_HEX = re.compile(r"[0-9A-Fa-f]{6}")
EMU_IN = 914400
# --------------------------------------------------------------------------- helpers


def _hex(v: str | None) -> str | None:
    return v.upper() if v and _HEX.fullmatch(v) else None


def _lum(h: str) -> float:
    def ch(i: int) -> float:
        c = int(h[i : i + 2], 16) / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * ch(0) + 0.7152 * ch(2) + 0.0722 * ch(4)


def _is_figure(text: str) -> bool:
    """A short figure: ``2.1兆円`` ``38%`` ``+22%`` ``01`` (digits plus at most a short unit)."""
    t = text.strip()
    if not 1 <= len(t) <= TH["num_chars"] or not _NUMBERISH.search(t):
        return False
    return len(_STRIP_NUM.sub("", t)) <= TH["num_unit"]


def _index(text: str) -> int | None:
    t = text.strip()
    return int(t) if re.fullmatch(r"\d{1,2}", t) else None


def _mid(it: Item, box: Item) -> bool:
    return box.x <= it.cx <= box.x + box.w and box.y <= it.cy <= box.y + box.h


def _live(data: SlideData) -> list[Item]:
    return [i for i in data.items if free(i)]


def _in_body(it: Item, W: int, H: int) -> bool:
    return TH["body_top"] * H <= it.cy <= TH["body_bottom"] * H


def _claim(it: Item, rec: str, role: str = "rec") -> None:
    claim(it, rec, role)


def _text_color(it: Item) -> str | None:
    for p in it.paras:
        for r in p.runs:
            if r.text.strip() and _hex(r.color):
                return _hex(r.color)
    return None


def _first_run(p: ParaT) -> RunT | None:
    return next((r for r in p.runs if r.text.strip()), None)


def _size_of(p: ParaT) -> float | None:
    sizes = [r.size for r in p.runs if r.text.strip() and r.size]
    return max(sizes) if sizes else p.size


def _all_paras(items: list[Item]) -> list[ParaT]:
    return [p for it in sorted(items, key=lambda i: (i.y, i.x)) for p in it.paras if p.plain.strip()]


def _cards(data: SlideData, deck, pool: list[Item] | None = None) -> list[Item]:
    """Filled rectangles that can hold a card: not chrome, not tiny, inside the body zone."""
    W, H = deck.width, deck.height
    out = []
    for it in pool if pool is not None else _live(data):
        f = _hex(it.fill)
        if not f or it.ph or it.kind not in ("shape", "text") or it.prst not in (None, "rect", "roundRect"):
            continue
        share = it.area / (W * H)
        if not TH["card_min_area"] <= share <= TH["card_max_area"] or it.w > TH["card_max_w"] * W:
            continue
        if it.y <= 0.01 * H and it.w >= 0.9 * W:  # a band on the top edge
            continue
        if _in_body(it, W, H):
            out.append(it)
    return out


def _stripe(card: Item, data: SlideData, deck) -> tuple[str, Item] | None:
    """The thin filled shape on the top or left edge of ``card`` (no text): ``("top" | "left", shape)``."""
    W, H = deck.width, deck.height
    tx, ty = TH["align_tol"] * W, TH["align_tol"] * H * 1.5
    for s in data.items:
        if s is card or s.kind != "shape" or s.paras or s.rec or not _hex(s.fill):
            continue
        if (
            abs(s.x - card.x) <= tx
            and abs(s.w - card.w) <= tx
            and abs(s.y - card.y) <= ty
            and s.h <= min(TH["stripe_max"] * H, TH["stripe_card"] * card.h)
            and s.h > 0
        ):
            return "top", s
        if (
            abs(s.y - card.y) <= ty
            and abs(s.h - card.h) <= ty
            and abs(s.x - card.x) <= tx
            and s.w <= min(TH["stripe_max"] * W, TH["stripe_card"] * card.w)
            and s.w > 0
        ):
            return "left", s
    return None


def _texts_in(card: Item, data: SlideData) -> list[Item]:
    return [
        t
        for t in data.items
        if t is not card and t.kind == "text" and t.paras and not t.ph and not t.rec and _mid(t, card)
    ]


def _similar(cards: list[Item]) -> bool:
    ws, hs = [c.w for c in cards], [c.h for c in cards]
    tol = 1 + TH["group_size_tol"]
    return max(ws) <= tol * min(ws) and max(hs) <= tol * min(hs)


def _groups(cards: list[Item]) -> list[list[Item]]:
    """Cards of about the same size (each group at least 2, at most ``group_max``)."""
    rest = sorted(cards, key=lambda c: (c.y, c.x))
    out: list[list[Item]] = []
    while rest:
        a = rest[0]
        g = [c for c in rest if _similar([a, c])]
        rest = [c for c in rest if c not in g]
        if 2 <= len(g) <= TH["group_max"]:
            out.append(g)
    return out


def _reading(cards: list[Item]) -> list[Item]:
    return sorted(cards, key=lambda c: (round(c.y / max(c.h * 0.5, 1)), c.x))


class _Styles:
    """Stripe classes: one ``sN`` class per (side, thickness, colour), written as a ``style:`` token."""

    def __init__(self) -> None:
        self.names: dict[tuple[str, int, str], str] = {}

    def cls(self, side: str, s: Item) -> str:
        pt = max(1, round((s.h if side == "top" else s.w) / 12700))
        key = (side, pt, _hex(s.fill) or "000000")
        if key not in self.names:
            self.names[key] = f"s{len(self.names) + 1}"
        return self.names[key]

    def tokens(self) -> list[str]:
        return [f'{n}.border-{side}="{pt}pt solid #{col}"' for (side, pt, col), n in self.names.items()]


def _add_style(data: SlideData, tokens: list[str]) -> None:
    """Slide ``style:`` tokens (``runs.merge_lines`` joins every writer's line into one at emission)."""
    if tokens := [t for t in tokens if t]:
        data.style_lines.append("style: " + " ".join(tokens))


def _ranks(names: list[str]) -> str:
    return names[0] if len(set(names)) == 1 else ",".join(names)


def _split_head(it: Item, data: SlideData) -> Item:
    """A text whose first paragraph is the figure and which holds more paragraphs becomes two items (the
    figure on top): ``container`` reads a card heading from a single-paragraph text."""
    if len(it.paras) < 2:
        return it
    uid = max((i.uid for i in data.items), default=0) + 1
    half = it.h // 2
    rest = replace(it, paras=it.paras[1:], y=it.y + half, h=it.h - half, uid=uid)
    it.paras, it.h = it.paras[:1], half
    data.items.append(rest)
    return it


# --------------------------------------------------------------------------- quote card


def _quote(data: SlideData, deck) -> bool:
    live = _live(data)
    marks = [
        i
        for i in live
        if i.kind == "text"
        and not i.ph
        and i.text.strip() in QUOTE_MARKS
        and (i.max_size or 0) >= TH["quote_mark_pt"]
    ]
    if len(marks) != 1:
        return False
    mk = marks[0]
    bys = [
        i
        for i in live
        if i.kind == "text"
        and not i.ph
        and i is not mk
        and len(i.paras) == 1
        and i.text.lstrip()[:1] in DASHES
        and len(i.text) <= TH["quote_by_chars"]
    ]
    if len(bys) != 1:
        return False
    by = bys[0]
    texts = [
        i
        for i in live
        if i.kind == "text" and not i.ph and i is not mk and i is not by and i.y < by.y and len(i.text) >= 6
    ]
    texts = [t for t in texts if not t.fill or _hex(t.fill)]
    if not texts:
        return False
    text = max(texts, key=lambda i: i.area)
    if text.y + text.h > by.y + 0.5 * by.h or mk.y > text.y + 0.5 * text.h:
        return False
    panels = [
        p
        for p in live
        if p is not text and p.kind in ("shape", "text") and _hex(p.fill) and _mid(text, p) and _mid(by, p)
    ]
    panels = [p for p in panels if not p.paras]
    panel = min(panels, key=lambda p: p.area) if panels else None
    mk.name, text.name, by.name = "Quote mark", "Quote text", "Quote by"
    for it in (mk, text, by):
        _claim(it, "quote")
    toks = []
    if panel is not None:
        panel.name = "Quote panel"
        _claim(panel, "quote")
        if (st := _stripe(panel, data, deck)) is not None:
            _claim(st[1], "quote", "decor")
    if c := _text_color(mk):
        toks.append(f"quote.mark.color=#{c}")
    _add_style(data, toks)
    if text.max_size:
        data.words.append(f"size={text.max_size:g}")
    return True


# --------------------------------------------------------------------------- numbered bars and cards


def _badges(data: SlideData, deck) -> bool:
    W, H = deck.width, deck.height
    lim = TH["badge_max"]
    cand = []
    for i in _live(data):
        if (
            i.kind == "text"
            and not i.ph
            and _hex(i.fill)
            and len(i.paras) == 1
            and _index(i.text) is not None
            and i.w <= lim * W
            and i.h <= lim * H * 1.4
            and i.w >= TH["badge_min_in"] * EMU_IN
            and TH["badge_aspect"][0] <= i.w / max(i.h, 1) <= TH["badge_aspect"][1]
            and i.prst in (None, "rect", "roundRect", "ellipse")
            and _in_body(i, W, H)
        ):
            cand.append(i)
    if len(cand) < 2:
        return False
    cand = _reading(cand)
    nums = [_index(b.text) for b in cand]
    if nums != list(range(nums[0], nums[0] + len(nums))) or nums[0] > 1 or len(cand) > 12:
        return False
    if max(b.w for b in cand) > 1.3 * min(b.w for b in cand):
        return False
    hosts: list[Item | None] = []
    labels: list[Item | None] = []
    pool = _live(data)
    for b in cand:
        bars = [
            c
            for c in pool
            if c is not b
            and c.kind in ("shape", "text")
            and _hex(c.fill)
            and _mid(b, c)
            and c.area >= 2 * b.area
            and c.w < TH["card_max_w"] * W
            and c not in cand
            and not (c.y <= 0.01 * H and c.w >= 0.9 * W)
        ]
        host = min(bars, key=lambda c: c.area) if bars else None
        inner = [
            t
            for t in pool
            if t is not b
            and t not in cand
            and t.kind == "text"
            and not t.ph
            and not _hex(t.fill)
            and (_mid(t, host) if host is not None else False)
        ]
        if inner:
            label = min(inner, key=lambda t: (t.y, t.x))
        else:
            label = host if host is not None and host.paras else None
        if host is None or label is None:
            return False
        hosts.append(host)
        labels.append(label)
    if len({id(h) for h in hosts}) != len(hosts):
        return False
    return _apply_badges(data, deck, cand, hosts, labels)


def _others_in_body(data: SlideData, deck, taken: set[int]) -> bool:
    """Is there content (text, chart, table, picture) beside or between the recognised items? A lead above
    and a footnote or conclusion below do not count (``@rows`` lets them surround the bars)."""
    W, H = deck.width, deck.height
    mine = [i for i in data.items if id(i) in taken]
    y0, y1 = min(i.y for i in mine), max(i.y + i.h for i in mine)
    for i in data.items:
        if id(i) in taken or i.role == "decor" or i.ph in ("ftr", "sldNum", "dt", "title", "ctrTitle"):
            continue
        if not y0 <= i.cy <= y1:
            continue
        if i.kind in ("chart", "table", "image", "math"):
            return True
        if i.kind == "text" and i.text.strip() and _in_body(i, W, H) and not any(_mid(i, t) for t in mine):
            return True
    return False


def _apply_badges(data, deck, badges: list[Item], hosts: list[Item], labels: list[Item]) -> bool:
    W = deck.width
    fills = [_hex(b.fill) or "000000" for b in badges]
    ink = _text_color(badges[0])
    toks: list[str] = []
    prim = (deck.colors.get("primary") or "").upper()
    wide = all(h.w >= TH["bar_min_w"] * W for h in hosts)
    left = all(
        b.x - h.x <= TH["badge_edge"] * h.w and b.x + b.w <= h.x + 0.5 * h.w
        for b, h in zip(badges, hosts, strict=True)
    )
    one_line_bars = all(len(lb.paras) == 1 for lb in labels)
    taken = {id(x) for x in (*badges, *hosts, *labels)}
    stripes = [_stripe(h, data, deck) for h in hosts]
    for st in stripes:
        if st is not None:
            taken.add(id(st[1]))
    rows = wide and left and one_line_bars and not _others_in_body(data, deck, taken)
    if rows:
        for k, (b, h, lb) in enumerate(zip(badges, hosts, labels, strict=True), 1):
            if lb is not h:
                h.kind, h.paras = "text", lb.paras
                data.items.remove(lb)
            h.name, b.name = f"Row {k}", f"Row {k} num"
            _claim(h, "rows")
            _claim(b, "rows")
            if stripes[k - 1] is not None:
                _claim(stripes[k - 1][1], "rows", "decor")
        if any(f != prim for f in fills):
            toks.append("rows-num.fill=" + _ranks([f"#{f}" for f in fills]))
        if ink and ink not in ("FFFFFF",):
            toks.append(f"rows-num.color=#{ink}")
        bar_fills = {_hex(h.fill) for h in hosts}
        surf = (deck.colors.get("surface") or "").upper()
        if len(bar_fills) == 1 and (bf := next(iter(bar_fills))) and bf != surf:
            toks.append(f"rows.fill=#{bf}")
        size = max((_size_of(h.paras[0]) or 0) for h in hosts)
        if size:
            toks.append(f"rows.size={size:g}")
    else:
        for b in badges:
            _claim(b, "num", "decor")
        data.words.append("num")
        if any(f != prim for f in fills):
            toks.append(f"box.num.fill=#{fills[0]}")
        if ink and ink not in ("FFFFFF",):
            toks.append(f"box.num.color=#{ink}")
        for st in stripes:
            if st is not None:
                _claim(st[1], "num", "decor")
    _add_style(data, toks)
    return True


# --------------------------------------------------------------------------- number tiles and number headings


def _tile_parts(card: Item, data: SlideData) -> tuple[list[Item], ParaT, list[ParaT]] | None:
    texts = sorted(_texts_in(card, data), key=lambda t: (t.y, t.x))
    if card.kind == "text" and card.paras:
        return None
    paras = _all_paras(texts)
    if len(paras) < 2:
        return None
    return texts, paras[0], paras[1:]


def _tiles(data: SlideData, deck) -> bool:
    """Number tiles (``2.1兆円`` + caption) and number headings (``01`` + text): groups of equal cards."""
    cands = []
    for c in _cards(data, deck):
        if c.paras:  # a card that holds its own text is a bar, not a tile
            continue
        got = _tile_parts(c, data)
        if got is not None:
            cands.append((c, *got))
    if len(cands) < 2:
        return False
    done = False
    for g in _groups([c for c, *_ in cands]):
        info = {id(c): (texts, p0, rest) for c, texts, p0, rest in cands}
        if any(id(c) not in info for c in g):
            continue
        parts = [info[id(c)] for c in g]
        if not all(_is_figure(p0.plain) for _t, p0, _r in parts):
            continue
        sizes = []
        ok = True
        for _t, p0, rest in parts:
            s0, others = _size_of(p0), [_size_of(p) for p in rest if _size_of(p)]
            if not s0 or not others:
                ok = False
                break
            sizes.append((s0, max(others)))
        if not ok:
            continue
        order = _reading(g)
        idx = [_index(info[id(c)][1].plain) for c in order]
        is_index = all(i is not None for i in idx) and idx == list(range(idx[0], idx[0] + len(idx)))
        need = TH["index_ratio"] if is_index else TH["kpi_ratio"]
        if not all(s0 >= need * so for s0, so in sizes):
            continue
        _apply_tiles(data, deck, order, info, is_index)
        done = True
    return done


def _apply_tiles(data: SlideData, deck, order: list[Item], info: dict, is_index: bool) -> None:
    styles = _Styles()
    fg = (deck.colors.get("fg") or "").upper()
    toks: list[str] = []
    first_p0 = info[id(order[0])][1]
    for c in order:
        texts, p0, rest = info[id(c)]
        head_item = texts[0]
        if len(head_item.paras) > 1:
            head_item = _split_head(head_item, data)
        _claim(c, "numcard" if is_index else "kpi")
        for t in data.items:
            if t.kind == "text" and t.paras and not t.ph and not t.rec and _mid(t, c):
                _claim(t, c.rec)
        attrs: list[str] = []
        st = _stripe(c, data, deck)
        if st is not None:
            side, s = st
            attrs.append("." + styles.cls(side, s))
            _claim(s, c.rec, "decor")
        col = _hex(_first_run(p0).color if _first_run(p0) else None)
        if is_index:
            if col and col != fg:
                for r in p0.runs:
                    if r.text.strip():
                        put_span(r, [f"color=#{col}"])
        elif col and col != fg:
            attrs.append(f"color=#{col}")
        c.rec_attrs = " ".join(attrs)
    toks += styles.tokens()
    others = [p for _t, _p, rest in info.values() for p in rest]
    s_rest = max((_size_of(p) or 0) for p in others)
    s_fig = _size_of(first_p0) or 0
    if is_index:
        _add_style(data, toks)
        data.style_lines.append(f"sizes: heading={s_fig:g}! body={s_rest:g}!")
        return
    surf = (deck.colors.get("surface") or "").upper()
    fill = {_hex(c.fill) for c in order}
    if len(fill) == 1 and (f := next(iter(fill))) and f != surf:
        toks.append(f"kpi.fill=#{f}")
    if first_p0.align in (None, "l"):
        toks += ["kpi.align=left", "kpi.note.align=left"]
    toks.append(f"kpi.note.size={s_rest:g}")
    runs = [r for p in others for r in p.runs if r.text.strip()]
    if runs and all(r.bold for r in runs):
        toks.append("kpi.note.bold=on")
    if runs and (nc := _hex(runs[0].color)) and all(_hex(r.color) == nc for r in runs):
        toks.append(f"kpi.note.color=#{nc}")
    _add_style(data, toks)
    data.style_lines.append(f"sizes: kpi={s_fig:g}")
    data.words.append("kpi")


# --------------------------------------------------------------------------- dark statement panel


def _spans(paras: list[ParaT], base_size: float | None, base_color: str | None, every: bool = False) -> None:
    """Give each run that differs from the base (size, colour) its own span; ``every`` spans all runs."""
    span_runs(
        paras,
        size_off=lambda r: every or base_size is None or abs(r.size - base_size) / base_size > TH["span_tol"],
        color_of=lambda r: f"#{c}" if (c := _hex(r.color)) and (every or c != base_color) else None,
        bold=True,
    )


def _panel(data: SlideData, deck) -> bool:
    W, H = deck.width, deck.height
    lo, hi = TH["panel_paras"]
    for c in _cards(data, deck):
        f = _hex(c.fill)
        if c.paras or not f or _lum(f) > TH["dark_lum"] or c.area < TH["panel_area"] * W * H:
            continue
        texts = _texts_in(c, data)
        paras = _all_paras(texts)
        if not lo <= len(paras) <= hi or any(len(p.plain) > TH["panel_chars"] for p in paras):
            continue
        sizes = [s for p in paras if (s := _size_of(p))]
        if len(sizes) != len(paras) or max(sizes) < TH["panel_ratio"] * min(sizes):
            continue
        if any(p.marker for p in paras):
            continue
        if _stripe(c, data, deck) is not None:
            continue
        _spans(paras, None, None, every=True)
        merged = replace(
            c,
            kind="text",
            paras=[ParaT(runs=list(p.runs), size=p.size) for p in paras],
            rec="panel",
            role="rec",
        )
        ink = next((x for p in paras[1:] for r in p.runs if (x := _hex(r.color))), "FFFFFF")
        attrs = f"fill=#{f} color=#{ink}"
        if "num" in data.words:
            attrs = f".kpi {attrs} align=left"
        merged.rec_attrs = attrs
        data.items = [i for i in data.items if i is not c and i not in texts]
        data.items.append(merged)
        return True
    return False


def _dark_cards(data: SlideData, deck) -> bool:
    """A dark filled card with its own text keeps its look: ``{fill=#122B4A color=#FFFFFF}``."""
    W = deck.width
    done = False
    cards = _cards(data, deck)
    for c in cards:
        f = _hex(c.fill)
        if not f or _lum(f) > TH["dark_lum"] or c.w >= 0.7 * W or c.rec:
            continue
        if any(p is not c and p.area > c.area and _mid(c, p) for p in cards):
            continue  # a heading band of another card
        texts = [c] if c.paras else _texts_in(c, data)
        if len(texts) != 1 or any(p.marker for p in texts[0].paras):
            continue
        ink = _text_color(texts[0]) or "FFFFFF"
        for p in texts[0].paras:  # (a heading-only box draws its text in the heading ink, not the box ink)
            for r in p.runs:
                if r.text.strip():
                    put_span(r, [f"color=#{_hex(r.color) or ink}"], bold=True)
        c.rec, c.role = "dark", "rec"
        c.rec_attrs = f"fill=#{f} color=#{ink}"
        for t in texts:
            if t is not c:
                _claim(t, "dark")
        done = True
    return done


# --------------------------------------------------------------------------- big-number bars


def _bars(data: SlideData, deck) -> bool:
    got = []
    for c in _cards(data, deck):
        if c.paras:
            continue
        st = _stripe(c, data, deck)
        texts = _texts_in(c, data)
        if st is None or len(texts) != 1 or len(texts[0].paras) != 1:
            continue
        p = texts[0].paras[0]
        runs = [r for r in p.runs if r.text.strip() and r.size]
        if len(runs) < 2:
            continue
        hi, lo = max(r.size for r in runs), min(r.size for r in runs)
        big = next((r for r in runs if r.size == hi), None)
        if hi < TH["bigrow_ratio"] * lo or big is None or not _NUMBERISH.search(big.text):
            continue
        got.append((c, st, texts[0]))
    if len(got) < 2:
        return False
    bars = [c for c, _s, _t in got]
    done = False
    for g in _groups(bars):
        sel = [x for x in got if x[0] in g]
        if len(sel) != len(g):
            continue
        _apply_bars(data, deck, _reading_triples(sel))
        done = True
    return done


def _reading_triples(sel: list[tuple]) -> list[tuple]:
    return sorted(sel, key=lambda x: (round(x[0].y / max(x[0].h * 0.5, 1)), x[0].x))


def _apply_bars(data: SlideData, deck, sel: list[tuple]) -> None:
    W = deck.width
    styles = _Styles()
    taken = {id(x) for c, st, t in sel for x in (c, st[1], t)}
    first = sel[0][2].paras[0]
    base_run = _first_run(first)
    base_size = base_run.size if base_run else None
    base_color = _hex(base_run.color) if base_run else None
    for _c, _st, t in sel:
        _spans(t.paras, base_size, base_color)
    wide = all(c.w >= 0.6 * W for c, _s, _t in sel)
    c0 = sel[0][0]
    stacked = all(abs(c.x - c0.x) <= 0.02 * W and abs(c.w - c0.w) <= 0.02 * W for c, _s, _t in sel)
    rows = wide and stacked and len(sel) >= 3 and not _others_in_body(data, deck, taken)
    toks: list[str] = []
    stripe_cols = []
    if rows:
        for k, (c, (_side, s), t) in enumerate(sel, 1):
            c.kind, c.paras, c.name = "text", t.paras, f"Row {k}"
            data.items.remove(t)
            _claim(c, "rows")
            _claim(s, "rows", "decor")
            stripe_cols.append(f"#{_hex(s.fill)}")
        toks.append("rows.stripe=" + _ranks(stripe_cols))
        if base_size:
            toks.append(f"rows.size={base_size:g}")
        surf = (deck.colors.get("surface") or "").upper()
        fills = [_hex(c.fill) for c, _s, _t in sel]
        if fills[0] != surf and len(set(fills)) <= 2:
            toks.append(f"rows.fill=#{fills[0]}")
        _add_style(data, toks)
        return
    for c, (side, s), t in sel:
        _claim(c, "bar")
        _claim(t, "bar")
        _claim(s, "bar", "decor")
        c.rec_attrs = "." + styles.cls(side, s)
    toks += styles.tokens()
    _add_style(data, toks)
    if base_size:
        data.style_lines.append(f"sizes: heading={base_size:g}!")


# --------------------------------------------------------------------------- entry


def recognise(data: SlideData, deck) -> None:
    """Prepare the slide: claimed shapes get ``rec`` (and role ``rec`` / ``decor``), see the module doc."""
    if not is_foreign(deck):  # (computed once per deck: runs.is_slidemark_deck)
        return
    for step in (_quote, _badges, _panel, _tiles, _bars, _dark_cards):
        try:
            step(data, deck)
        except Exception:  # never raise on a foreign deck: the slide is read as plain shapes
            continue


# --------------------------------------------------------------------------- emission


def box_chunks(b, acc: str | None, classes: dict[str, str]) -> list[tuple[str, list[str]]] | None:
    """Lines of a recognised box that ``emit_block`` does not write by itself, else ``None``."""
    it = b.item
    if it is None or it.rec not in ("kpi", "panel"):
        return None
    attrs = it.rec_attrs.strip()
    paras = [*(b.heading or []), *[p for ch in b.children if ch.kind == "text" for p in ch.paras]]
    if it.rec == "kpi":
        lines = [one_line([p], accent=acc, classes=classes, plain_bold=True) for p in paras]
        head = "##" + (f" {{{attrs}}}" if attrs else "")
        return [("meta", [head, *[ln for ln in lines if ln]])]
    head_txt = one_line(b.heading or [], accent=acc, classes=classes, plain_bold=True)
    head = f"## {head_txt}" + (f" {{{attrs}}}" if attrs else "")
    if ".kpi" in attrs:
        body = [one_line([p], accent=acc, classes=classes) for p in paras[1:]]
        return [("meta", [head, *[ln for ln in body if ln]])]
    return [("meta", [head, *text_lines(paras[1:], accent=acc, classes=classes)])]


__all__ = ["TH", "box_chunks", "recognise"]
