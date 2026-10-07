"""Flat items -> SlideMark structure: title, lead, boxes, grid (``@`` line), footnotes, conclusion."""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from functools import cmp_to_key

from ..ir import Diagnostic
from .emit import (
    _attr,
    chart_lines,
    detect_lang,
    header_rows_of,
    hl_row_set,
    one_line,
    table_lines,
    text_lines,
)
from .links import find_links, recover_diagram
from .links import tokens as link_tokens
from .read import Item, ParaT, RunT, SlideData

CHEVRONS = ("chevron", "homePlate", "pentagon")
STACKABLE = ("table", "callout", "text", "code")
KIND_BY_COLOR = (("primary", "note"), ("success", "tip"), ("accent", "warn"), ("danger", "caution"))


@dataclass
class DeckInfo:
    width: int
    height: int
    accent: str | None = None  # RRGGBB of the theme accent (emphasis color)
    colors: dict[str, str] = field(default_factory=dict)  # name -> RRGGBB
    footers: set[str] = field(default_factory=set)
    sections: list[tuple[str, list[int]]] = field(
        default_factory=list
    )  # PowerPoint sections (name, slide numbers)
    margin_x: int = 0  # theme side margin and column gap (EMU); 0 = unknown
    gap: int = 0
    implied: dict[str, object] = field(default_factory=dict)  # role (lead, ...) -> Style a css rule gives it
    css_heading: bool = False  # a css rule sets the font size of ## headings (sizes say nothing about a KPI)


@dataclass
class Block:
    kind: str  # box | text | table | chart | image | code | callout
    x: int
    y: int
    w: int
    h: int
    item: Item | None = None
    heading: list[ParaT] | None = None
    children: list[Block] = field(default_factory=list)
    paras: list[ParaT] = field(default_factory=list)
    sub: bool = False
    chevron: bool = False
    steps: bool = False  # chevron box of an ``@steps`` slide (the card text is its content)
    callout: str = "note"
    icon: str | None = None
    lines: list[str] = field(default_factory=list)  # kind "fence": the fence lines (a recovered diagram)
    links: list[str] = field(default_factory=list)  # box: link tokens between its children
    card: bool = False  # box: an ``Item N`` card (a bullet drawn as a card by ``@items``)
    items: bool = False  # box: its bullets were item cards (the slide gets the ``items`` word)


# --------------------------------------------------------------------------- classification


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


_BAR_FILL = 0.85  # a filled shape this much of the width of the cells it covers is a Gantt bar


def _fold_bars(data: SlideData, t: Item, xs: list[int], ys: list[int]) -> None:
    """Filled shapes with text spanning body cells (a ``{.gantt}`` table's bars) become cell text; a bar over
    several columns restores the ``<`` merge. The table is flagged ``gantt``."""
    nc, nr = len(t.col_w), len(t.row_h)
    for it in list(data.items):
        if it.kind != "text" or it.ph or it.role or not it.fill or not it.text:
            continue
        r = next((k for k in range(nr) if ys[k] <= it.cy < ys[k + 1]), None)
        c0 = next((k for k in range(nc) if xs[k] <= it.x + it.w * 0.15 < xs[k + 1]), None)
        c1 = next((k for k in range(nc) if xs[k] < it.x + it.w * 0.85 <= xs[k + 1]), None)
        if r is None or c0 is None or c1 is None or r < 1 or c0 < 1 or c1 < c0 or r >= len(t.rows):
            continue
        row = t.rows[r]
        if c1 >= len(row) or it.h > 1.0 * t.row_h[r] or it.w < _BAR_FILL * (xs[c1 + 1] - xs[c0]):
            continue
        if any(row[k].paras or row[k].vmerge for k in range(c0, c1 + 1)):
            continue
        if row[c0].hmerge:
            continue
        row[c0].paras = it.paras
        for k in range(c0 + 1, c1 + 1):
            row[k].hmerge = True
        t.gantt = True
        data.items.remove(it)


def _fold_pill(cell, it: Item) -> None:
    """A ``Pill`` shape over a table cell becomes a badge run: alone in an empty cell, else after its text."""
    runs = [
        RunT(text=r.text.strip(), badge=it.fill, size=r.size)
        for p in it.paras
        for r in p.runs
        if r.text.strip()
    ]
    if not runs:
        return
    if cell.paras and cell.paras[-1].runs:
        last = cell.paras[-1]
        if last.runs[-1].text and not last.runs[-1].text.endswith(" "):
            last.runs[-1].text += " "
        last.runs.extend(runs)
    else:
        cell.paras = [ParaT(runs=runs, size=it.paras[0].size)]


def _bar_anchor(t: Item, r: int, c: int):
    """The cell with the text of the bar covering cell (r, c): walk left over ``<``, up over ``^``."""
    while c > 0 and t.rows[r][c].hmerge:
        c -= 1
    while r > 0 and t.rows[r][c].vmerge:
        r -= 1
    return t.rows[r][c]


def fold_into_tables(data: SlideData) -> None:
    """Text drawn on top of an empty table cell (status pills, tags) becomes that cell's text."""
    for t in [i for i in data.items if i.kind == "table" and i.col_w and i.row_h]:
        xs = [t.x]
        for w in t.col_w:
            xs.append(xs[-1] + w)
        ys = [t.y]
        for h in t.row_h:
            ys.append(ys[-1] + h)
        _fold_bars(data, t, xs, ys)
        for it in list(data.items):
            if it.kind != "text" or it.ph or it.role:
                continue
            c = next((k for k in range(len(t.col_w)) if xs[k] <= it.cx < xs[k + 1]), None)
            r = next((k for k in range(len(t.row_h)) if ys[k] <= it.cy < ys[k + 1]), None)
            if c is None or r is None or r >= len(t.rows) or c >= len(t.rows[r]):
                continue
            cell = t.rows[r][c]
            if t.gantt and it.name.lower().startswith("pill") and it.fill and it.text:
                cell = _bar_anchor(t, r, c)  # a pill inside a Gantt bar goes back to the bar cell's badge
            if (
                it.name.lower().startswith("pill")
                and it.fill
                and it.text
                and not (cell.hmerge or cell.vmerge)
            ):
                _fold_pill(cell, it)  # a table-cell status pill goes back to its badge
                data.items.remove(it)
                continue
            if (
                cell.paras
                or cell.hmerge
                or cell.vmerge
                or it.w > 1.05 * t.col_w[c]
                or it.h > 1.05 * t.row_h[r]
            ):
                continue
            cell.paras = it.paras
            data.items.remove(it)


def classify(data: SlideData, deck: DeckInfo) -> tuple[Item | None, list[Item]]:
    """Set ``role`` on special items; returns (title item, pool of content items)."""
    W, H = deck.width, deck.height
    items = data.items
    for it in items:
        nm = it.name.lower().strip()
        if nm.startswith("icon ") and it.kind == "shape":
            it.role = "icon"
        elif (
            it.ph in ("ftr", "sldNum", "dt")
            or nm in ("footer", "slide number")
            or it.has_slidenum
            or nm.startswith("band")
            or nm == "rule"
            or _NUM_BADGE.fullmatch(nm)  # `@num`: the numbered circle of a box heading
            or nm == "background"
            or nm.endswith(" accent")
            or (it.kind == "text" and it.y >= 0.85 * H and _norm(it.text) in deck.footers)
            or (
                it.kind in ("shape", "line")
                and not it.fill
                and not it.line
                and not (it.kind == "shape" and nm.startswith("card "))  # transparent css card
            )
            or (it.kind != "image" and it.area == 0 and not it.text)
        ):
            it.role = "decor"
        if it.kind == "image" and it.area >= 0.9 * W * H and it.w >= 0.95 * W:
            it.role = "decor"  # full-slide background picture
    live = [i for i in items if i.role is None]
    title = next((i for i in live if i.kind == "text" and i.ph in ("title", "ctrTitle")), None)
    if title is None:

        def in_card(i: Item) -> bool:
            return any(
                c is not i
                and c.fill
                and c.kind in ("shape", "text")
                and c.area > i.area
                and c.w < 0.9 * W
                and c.x <= i.cx <= c.x + c.w
                and c.y <= i.cy <= c.y + c.h
                for c in items
            )

        reach = max(  # a title on a band anchored to the top (cover.band_h) may sit lower than 0.3 H
            [
                0.3 * H,
                *(
                    i.y + i.h
                    for i in items
                    if i.role == "decor" and i.name.lower().startswith("band") and i.y <= 0
                ),
            ]
        )
        top = [
            i
            for i in live
            if i.kind == "text"
            and i.y < reach
            and len(i.paras) <= 2
            and len(i.text) <= 120
            and not in_card(i)
        ]
        if top:
            title = max(top, key=lambda i: (i.max_size or 0, -i.y))
    if title:
        title.role = "title"
    # callouts: a filled text shape with a thin filled bar on its left edge
    for it in live:
        if it.role or it.kind != "text" or not it.fill or _ROW.fullmatch(it.name or ""):
            continue  # (an `@rows` bar with a `rows.stripe` is no callout)
        for bar in items:
            if (
                bar is not it
                and bar.kind == "shape"
                and bar.fill
                and bar.w < 0.02 * W
                and abs(bar.y - it.y) <= 0.01 * H
                and abs(bar.h - it.h) <= 0.01 * H
                and abs(bar.x - it.x) <= 0.01 * W
            ):
                kind = "note"
                for cname, ckind in KIND_BY_COLOR:
                    if deck.colors.get(cname) == bar.fill:
                        kind = ckind
                        break
                it.role = f"callout:{kind}"
                bar.role = "decor"
                break
    pool = [i for i in items if i.role is None]
    for it in pool:
        if it.role:
            continue
        small = it.max_size is not None and it.max_size <= 12
        label = data.connectors >= 2 and len(it.text) <= 20  # a short text on a diagram: an edge label
        if it.kind == "text" and (
            it.name.lower().startswith("footnote")
            or (not it.fill and not it.line and it.y >= 0.8 * H and it.h <= 0.12 * H and small and not label)
        ):
            it.role = "footnote"
    for it in pool:
        if it.kind == "text" and it.name.lower().startswith("conclusion"):
            it.role = "conclusion"
    if not any(i.role == "conclusion" for i in pool):
        cands = [
            i
            for i in pool
            if i.kind == "text"
            and i.fill
            and i.ph is None
            and i.w >= 0.75 * W
            and i.y >= 0.7 * H
            and i.h <= 0.15 * H
            and len(i.paras) <= 2
            and not any(p.marker for p in i.paras)
            and not any(o is not i and o.role is None and o.y >= i.y and o.kind != "shape" for o in pool)
        ]
        if cands:
            max(cands, key=lambda i: i.y).role = "conclusion"
    rest = [i for i in pool if i.role is None]
    lead = next((i for i in rest if i.kind == "text" and i.name.lower() == "lead"), None)
    if lead is None and title is not None:
        body = [i for i in rest if i.kind != "shape"]
        cand = min(body, key=lambda i: (i.y, i.x), default=None)
        if (
            cand is not None
            and cand.kind == "text"
            and cand.ph in (None, "obj")
            and not cand.fill
            and not cand.line
            and cand.w >= 0.7 * W
            and cand.h <= 0.12 * H
            and len(cand.paras) == 1
            and not cand.paras[0].marker
            and len(cand.text) <= 200
            and cand.y >= title.y + 0.5 * title.h
            and (cand.max_size is None or title.max_size is None or cand.max_size <= title.max_size)
            and len(body) >= 2
            and not cand.name.lower().startswith("heading")
            and not any(
                c is not cand
                and (c.fill or c.line)
                and c.kind in ("shape", "text")
                and c.area > cand.area
                and c.x - 0.01 * W <= cand.cx <= c.x + c.w + 0.01 * W
                and c.y - 0.01 * H <= cand.cy <= c.y + c.h + 0.01 * H
                for c in rest
            )
        ):
            lead = cand
    if lead:
        lead.role = "lead"
    return title, [i for i in items if i.role is None or i.role.startswith("callout")]


# --------------------------------------------------------------------------- blocks


def _is_decor(it: Item, kids: dict[int, list[Item]]) -> bool:
    return it.kind == "shape" and not kids.get(it.uid)


def _heading_like(paras: list[ParaT]) -> bool:
    p0 = paras[0]
    rest = max((p.size or 0 for p in paras[1:]), default=0)
    return p0.all_bold or bool(p0.size and rest and p0.size > 1.15 * rest)


def _is_code(it: Item) -> bool:
    runs = [r for p in it.paras for r in p.runs if r.text.strip()]
    return it.name.lower().startswith("code") or (
        bool(runs) and all(r.code for r in runs) and len(it.paras) > 1
    )


_STEP = re.compile(r"Step (\d+) (arrow|card)")


def _is_step_caption(p: ParaT, n: int) -> bool:
    """The first line of a step card is the generated caption ("STEP 2", "手順2"): bold, unlisted, ends in the
    step number."""
    return (
        not p.marker
        and bool(p.runs)
        and all(r.bold for r in p.runs if r.text.strip())
        and re.fullmatch(rf"\D{{0,12}}\s*{n}\D{{0,2}}", p.plain.strip()) is not None
    )


def fold_steps(pool: list[Item]) -> list[Item]:
    """``@steps`` arrows (shape names ``Step N arrow``) take the text of their ``Step N card`` as content.

    The card and the texts inside it leave the pool; the arrow becomes one chevron item (``steps``), which
    the usual chevron path turns into a ``##`` box with its bullets. Without a second arrow nothing changes.
    """
    named = {(m.group(2), int(m.group(1))): it for it in pool if (m := _STEP.fullmatch(it.name or ""))}
    arrows = sorted(k[1] for k in named if k[0] == "arrow")
    if len(arrows) < 2 or any(not named[("arrow", n)].paras for n in arrows):
        return pool
    drop: set[int] = set()
    new: dict[int, Item] = {}
    for n in arrows:
        arrow, card = named[("arrow", n)], named.get(("card", n))
        paras = list(arrow.paras)
        if card is not None:
            inside = [
                i
                for i in pool
                if i is not card
                and i is not arrow
                and i.kind == "text"
                and card.x - 2 <= i.cx <= card.x + card.w + 2
                and card.y - 2 <= i.cy <= card.y + card.h + 2
            ]
            for k, i in enumerate(sorted(inside, key=lambda i: (i.y, i.x))):
                ps = list(i.paras)
                if k == 0 and ps and _is_step_caption(ps[0], n):  # `steps.caption` is a token, not content
                    ps = ps[1:]
                paras += ps
                drop.add(i.uid)
            drop.add(card.uid)
        new[arrow.uid] = replace(arrow, paras=paras, steps=True)
    return [new.get(i.uid, i) for i in pool if i.uid not in drop]


def fold_kpi(pool: list[Item]) -> list[Item]:
    """``kpi.rule`` splits a KPI card's text into ``KPI value`` and ``KPI caption`` boxes: put them back.

    The caption's paragraphs join the value box (the card holds one text again, as `_kpi` expects); the
    caption leaves the pool. A caption without a value box above it stays as it is."""
    caps = [i for i in pool if i.kind == "text" and (i.name or "") == "KPI caption"]
    vals = [i for i in pool if i.kind == "text" and (i.name or "") == "KPI value"]
    if not caps or not vals:
        return pool
    drop: set[int] = set()
    new: dict[int, Item] = {}
    for cap in caps:
        above = [
            v
            for v in vals
            if v.uid not in new and abs(v.x - cap.x) <= 2 and abs(v.w - cap.w) <= 2 and v.y + v.h <= cap.y + 2
        ]
        if not above:
            continue
        v = max(above, key=lambda i: i.y)
        new[v.uid] = replace(v, paras=[*v.paras, *cap.paras], h=cap.y + cap.h - v.y, name="Text")
        drop.add(cap.uid)
    return [new.get(i.uid, i) for i in pool if i.uid not in drop]


_ROW = re.compile(r"Row (\d+)( num| stripe| glyph)?")
_NUM_BADGE = re.compile(r"num \d+")
_ITEM_CARD = re.compile(r"Item \d+")


def fold_rows(pool: list[Item]) -> tuple[list[Item], str | None]:
    """``@rows`` bars (shape names ``Row N`` / ``Row N num`` / ``stripe`` / ``glyph``) become one list:
    ``"rows"`` = ordered (numbered bars), ``"plain"`` = bullets (no badges: ``@rows plain``), ``None`` = no
    bars."""
    rows = sorted(
        (int(m.group(1)), it)
        for it in pool
        if (m := _ROW.fullmatch(it.name or "")) and not m.group(2) and it.paras
    )
    if not rows:
        return pool, None
    plain = not any((m := _ROW.fullmatch(it.name or "")) and m.group(2) == " num" for it in pool)
    first = rows[0][1]
    paras = [
        ParaT(runs=list(p.runs), marker="bullet" if plain else "number", size=p.size)
        for _n, it in rows
        for p in it.paras[:1]
        if p.plain.strip()
    ]
    x0, y0 = min(it.x for _n, it in rows), min(it.y for _n, it in rows)
    merged = replace(
        first,
        kind="text",
        name="Rows",
        fill=None,
        line=False,
        paras=paras,
        x=x0,
        y=y0,
        w=max(it.x + it.w for _n, it in rows) - x0,
        h=max(it.y + it.h for _n, it in rows) - y0,
    )
    drop = {it.uid for it in pool if _ROW.fullmatch(it.name or "")}
    return [merged if i.uid == first.uid else i for i in pool if i.uid not in drop or i.uid == first.uid], (
        "plain" if plain else "rows"
    )


def make_blocks(pool: list[Item], deck: DeckInfo, icons: list[Item] | None = None) -> list[Block]:
    W, H = deck.width, deck.height
    slide_area = W * H
    # a transparent card (css: background none, border-top only) still groups its heading and text
    cands = [
        i
        for i in pool
        if i.kind in ("text", "shape")
        and (i.fill or i.line or (i.kind == "shape" and i.name.startswith("Card ")))
        and 0.004 * slide_area <= i.area <= 0.85 * slide_area
        and not (i.role or "").startswith("callout")
    ]
    tol = 0.01 * W
    cands = [  # a heading band shares the top edge and width of its card: it is decoration, not a box
        c
        for c in cands
        if not (
            c.kind == "shape"
            and any(
                p is not c
                and p.area > c.area
                and abs(p.x - c.x) <= tol
                and abs(p.w - c.w) <= tol
                and abs(p.y - c.y) <= tol
                for p in cands
            )
        )
    ]
    parent: dict[int, Item] = {}
    kids: dict[int, list[Item]] = {}
    for it in pool:
        if it.area <= 0:
            continue
        best = None
        for c in cands:
            if c is it or c.area <= it.area:
                continue
            ix = max(0, min(it.x + it.w, c.x + c.w) - max(it.x, c.x))
            iy = max(0, min(it.y + it.h, c.y + c.h) - max(it.y, c.y))
            if ix * iy >= 0.7 * it.area and (best is None or c.area < best.area):
                best = c
        if best is not None:
            parent[it.uid] = best
            kids.setdefault(best.uid, []).append(it)

    def leaf_text(it: Item) -> Block:
        kind = "code" if _is_code(it) else "text"
        return Block(kind, it.x, it.y, it.w, it.h, item=it, paras=it.paras)

    def make(it: Item, nested: bool) -> list[Block]:
        if it.kind in ("table", "chart", "image", "math"):
            return [Block(it.kind, it.x, it.y, it.w, it.h, item=it)]
        if (it.role or "").startswith("callout"):
            return [Block("callout", it.x, it.y, it.w, it.h, item=it, paras=it.paras, callout=it.role[8:])]
        real = [k for k in kids.get(it.uid, []) if not _is_decor(k, kids)]
        if real:
            return container(it, real, nested)
        if it.kind == "shape":
            return []
        if it.prst in CHEVRONS and it.paras:
            return [
                Block(
                    "box",
                    it.x,
                    it.y,
                    it.w,
                    it.h,
                    item=it,
                    heading=[it.paras[0]],
                    paras=it.paras[1:],
                    chevron=True,
                    steps=it.steps,
                    sub=nested,
                )
            ]
        if (
            not nested
            and (it.fill or it.line)
            and len(it.paras) >= 2
            and not _is_code(it)
            and _heading_like(it.paras)
        ):
            rest = Block("text", it.x, it.y, it.w, it.h, paras=it.paras[1:])
            return [Block("box", it.x, it.y, it.w, it.h, item=it, heading=[it.paras[0]], children=[rest])]
        return [leaf_text(it)]

    def container(it: Item, real: list[Item], nested: bool) -> list[Block]:
        real = sorted(real, key=lambda k: (k.y, k.x))
        head: list[ParaT] | None = None
        extra: list[ParaT] = []
        body = real
        if it.kind == "text":
            head, extra = [it.paras[0]], it.paras[1:]
        else:
            k0 = real[0]
            top = it.y  # an icon at the card's top edge pushes the heading down
            for ic in icons or ():
                if it.x <= ic.cx <= it.x + it.w and it.y <= ic.cy <= it.y + 0.4 * it.h:
                    top = max(top, ic.y + ic.h)
            if (
                k0.kind == "text"
                and not kids.get(k0.uid)
                and len(k0.paras) == 1
                and not k0.paras[0].marker
                and not (k0.role or "").startswith("callout")
                and k0.y - top <= 0.3 * it.h
            ):
                head, body = k0.paras, real[1:]
        blocks: list[Block] = []
        for k in body:
            blocks.extend(make(k, True))
        blocks.sort(key=lambda b: (b.y, b.x))
        blocks = fold_subheads(blocks, W, H)
        if head is None:
            return blocks
        if extra:
            blocks.insert(0, Block("text", it.x, it.y, it.w, it.h, paras=extra))
        card = bool(_ITEM_CARD.fullmatch(it.name or ""))
        if (  # a box whose children are all `Item N` cards: the cards are its bullets (`@items`)
            not nested
            and blocks
            and all(b.kind == "box" and b.card and not b.children and not b.paras for b in blocks)
        ):
            paras = [
                ParaT(runs=list(p.runs), marker="bullet", size=p.size)
                for b in blocks
                for p in (b.heading or [])
            ]
            x0, y0 = min(b.x for b in blocks), min(b.y for b in blocks)
            text = Block(
                "text",
                x0,
                y0,
                max(b.x + b.w for b in blocks) - x0,
                max(b.y + b.h for b in blocks) - y0,
                paras=paras,
            )
            return [Block("box", it.x, it.y, it.w, it.h, item=it, heading=head, children=[text], items=True)]
        return [
            Block(
                "box", it.x, it.y, it.w, it.h, item=it, heading=head, children=blocks, sub=nested, card=card
            )
        ]

    out: list[Block] = []
    for it in pool:
        if it.uid in parent:
            continue
        out.extend(make(it, False))
    return _group_columns(_merge_cards(out, deck), deck)


def fold_subheads(blocks: list[Block], W: int, H: int) -> list[Block]:
    """A bold one-line text right above a text block at the same left edge is a ``###`` heading
    (a sub-box without fill)."""
    out: list[Block] = []
    i = 0
    while i < len(blocks):
        b = blocks[i]
        nxt = blocks[i + 1] if i + 1 < len(blocks) else None
        if (
            nxt is not None
            and b.kind == "text"
            and nxt.kind == "text"
            and len(b.paras) == 1
            and not b.paras[0].marker
            and b.paras[0].all_bold
            and not (b.item and b.item.role)
            and abs(nxt.x - b.x) <= 0.02 * W
            and -0.01 * H <= nxt.y - (b.y + b.h) <= 0.04 * H
        ):
            x0, y0 = min(b.x, nxt.x), b.y
            x1, y1 = max(b.x + b.w, nxt.x + nxt.w), max(b.y + b.h, nxt.y + nxt.h)
            out.append(Block("box", x0, y0, x1 - x0, y1 - y0, heading=b.paras, children=[nxt], sub=True))
            i += 2
            continue
        out.append(b)
        i += 1
    return out


def _group_columns(blocks: list[Block], deck: DeckInfo) -> list[Block]:
    """Loose texts stacked at the same left edge, side by side with similar stacks (numbered steps drawn
    as a circle, a title and a description), become one ``##`` box per column."""
    W, H = deck.width, deck.height
    loose = [
        b for b in blocks if b.kind == "text" and b.item is not None and b.item.paras and not b.item.role
    ]
    cols: list[list[Block]] = []
    for b in sorted(loose, key=lambda b: b.x):
        if cols and abs(cols[-1][0].x - b.x) <= 0.02 * W:
            cols[-1].append(b)
        else:
            cols.append([b])
    good: list[list[Block]] = []
    for c in cols:
        c = sorted(c, key=lambda b: b.y)
        if len(c) not in (2, 3) or any(
            b.y - (a.y + a.h) > min(0.12 * H, 0.4 * min(a.h, b.h)) for a, b in zip(c, c[1:], strict=False)
        ):
            continue
        if any(p.marker for b in c[:-1] for p in b.paras):
            continue
        good.append(c)
    if len(good) < 2 or len(good) != len(cols) or len({len(c) for c in good}) != 1:
        return blocks
    out = [b for b in blocks if not any(b is m for c in good for m in c)]
    for c in good:
        first = c[0].paras[0]
        rest = list(c[0].paras[1:])
        idx = 1
        if len(first.plain.strip()) <= 3 and len(c[0].paras) == 1:
            nxt = c[1].paras
            head = ParaT(runs=[*first.runs, RunT(" "), *nxt[0].runs], size=nxt[0].size)
            rest, idx = list(nxt[1:]), 2
        else:
            head = first
        body = [*rest, *[p for b in c[idx:] for p in b.paras]]
        x0, y0 = min(b.x for b in c), min(b.y for b in c)
        x1, y1 = max(b.x + b.w for b in c), max(b.y + b.h for b in c)
        kids = [Block("text", x0, y0, x1 - x0, y1 - y0, paras=body)] if body else []
        out.append(Block("box", x0, y0, x1 - x0, y1 - y0, heading=[head], children=kids))
    out.sort(key=lambda b: (b.y, b.x))
    return out


def _merge_cards(blocks: list[Block], deck: DeckInfo) -> list[Block]:
    """A card drawn as a header shape with a body shape right below it (same width, other fill) is one box."""
    tolx, toly = 0.01 * deck.width, 0.02 * deck.height
    out = list(blocks)
    changed = True
    while changed:
        changed = False
        for a in out:
            ia = a.item
            if a.kind not in ("box", "text") or ia is None or not ia.fill or a.chevron or not ia.paras:
                continue
            if a.kind == "text" and (
                len(ia.paras) > 3
                or any(p.marker for p in ia.paras)
                or not (ia.paras[0].all_bold or _heading_like(ia.paras))
            ):
                continue
            if a.kind == "box" and (len(a.children) != 1 or a.children[0].kind != "text" or a.sub):
                continue
            for b in out:
                ib = b.item
                if (
                    b is a
                    or b.kind != "text"
                    or ib is None
                    or not ib.fill
                    or ib.fill == ia.fill
                    or ib.role
                    or abs(b.x - a.x) > tolx
                    or abs(b.w - a.w) > tolx
                    or abs(b.y - (a.y + a.h)) > toly
                    or b.h < 0.5 * a.h
                    or _is_code(ib)
                ):
                    continue
                if a.kind == "text":
                    head, extra = [ia.paras[0]], ia.paras[1:]
                else:
                    head, extra = a.heading or [], a.children[0].paras
                body = [*extra, *b.paras]
                merged = Block(
                    "box",
                    a.x,
                    a.y,
                    a.w,
                    b.y + b.h - a.y,
                    item=ia,
                    heading=head,
                    children=[Block("text", b.x, b.y, b.w, b.h, paras=body)],
                )
                out = [merged if x is a else x for x in out if x is not b]
                changed = True
                break
            if changed:
                break
    return out


def _attach_icons(icons: list[Item], blocks: list[Block]) -> None:
    """``icon <name>`` shapes belong to the smallest box that contains their center."""
    boxes: list[Block] = []

    def walk(bs: list[Block]) -> None:
        for b in bs:
            if b.kind == "box":
                boxes.append(b)
                walk(b.children)

    walk(blocks)
    for ic in icons:
        inside = [b for b in boxes if b.x <= ic.cx <= b.x + b.w and b.y <= ic.cy <= b.y + b.h]
        if inside:
            min(inside, key=lambda b: b.w * b.h).icon = ic.name.strip()[5:].strip()


# --------------------------------------------------------------------------- grid


def _clusters(vals: list[int], tol: float) -> list[float]:
    out: list[list[int]] = []
    for v in sorted(vals):
        if out and v - out[-1][-1] <= tol:
            out[-1].append(v)
        else:
            out.append([v])
    return [min(c) for c in out]


def _nearest(starts: list[float], v: float) -> int:
    return min(range(len(starts)), key=lambda i: abs(starts[i] - v))


def _units(widths: list[float]) -> list[int]:
    tot = sum(widths) or 1
    r = [w / tot for w in widths]
    for d in range(len(r), 13):
        u = [round(x * d) for x in r]
        if min(u) >= 1 and all(abs(x * d - ui) <= 0.12 * ui for x, ui in zip(r, u, strict=True)):
            break
    else:
        u = [max(1, round(x * 12)) for x in r]
    g = 0
    for x in u:
        g = math.gcd(g, x)
    return [x // g for x in u]


def stretch_visuals(blocks: list[Block]) -> None:
    """Pictures, diagrams and charts are centred in their cell: one beside a taller block takes its row."""
    for v in blocks:
        if v.kind not in ("fence", "image", "chart", "math"):
            continue
        for s in blocks:
            if (
                s is not v
                and (v.x + v.w / 2 <= s.x or v.x + v.w / 2 >= s.x + s.w)
                and s.y <= v.y
                and s.y + s.h >= v.y + v.h
                and s.h > 1.3 * v.h
            ):
                v.y, v.h = s.y, s.h
                break


def _reading_order(a: Block, b: Block) -> int:
    """Top to bottom; blocks sharing most of their vertical span go left to right."""
    ov = min(a.y + a.h, b.y + b.h) - max(a.y, b.y)
    if ov > 0.5 * min(a.h, b.h):
        return (a.x > b.x) - (a.x < b.x)
    return (a.y > b.y) - (a.y < b.y)


def split_row_groups(blocks: list[Block], W: int, H: int) -> list[list[Block]] | None:
    """Rows of boxes with different column counts are row groups (``@end`` + a new ``@`` line each)."""
    if len(blocks) < 3 or any(b.kind != "box" for b in blocks):
        return None
    toly = 0.03 * H
    ys = _clusters([b.y for b in blocks], toly)
    if len(ys) < 2:
        return None
    rows: list[list[Block]] = [[] for _ in ys]
    for b in blocks:
        rows[_nearest(ys, b.y)].append(b)
    for r in rows:
        r.sort(key=lambda b: b.x)
        if max(b.w for b in r) > 1.12 * min(b.w for b in r) and not all(b.chevron for b in r):
            return None
    for a, b in zip(rows, rows[1:], strict=False):
        if max(x.y + x.h for x in a) > min(x.y for x in b) + toly:
            return None  # a box spans several rows: one grid
    if len({len(r) for r in rows}) == 1:
        return None  # same count per row: a plain grid
    return rows


def plan_grid(
    blocks: list[Block], W: int, H: int, diags: list[str], margin: int = 0, gap: int = 0
) -> tuple[list[str], list[Block], list[Block]]:
    """(tokens of the ``@`` line, grid blocks in source order, extras stacked full width below)."""
    if not blocks:
        return [], [], []
    tolx, toly = 0.02 * W, 0.03 * H
    ys = _clusters([b.y for b in blocks], toly)
    rows: list[list[Block]] = [[] for _ in ys]
    for b in blocks:
        rows[_nearest(ys, b.y)].append(b)
    x0, x1 = min(b.x for b in blocks), max(b.x + b.w for b in blocks)
    uw = x1 - x0

    def full(b: Block) -> bool:
        return b.w >= 0.88 * uw

    k = len(rows)
    for cand in range(1, len(rows) + 1):
        tail = rows[cand:]
        head_bottom = max((b.y + b.h for r in rows[:cand] for b in r), default=0)
        # charts and pictures below a grid are sized by the grid column in the engine: spell their cells out
        if all(
            len(r) == 1 and full(r[0]) and r[0].kind in STACKABLE and r[0].y >= head_bottom - toly
            for r in tail
        ):
            k = cand
            break
    grid = [b for r in rows[:k] for b in r]
    extras = [r[0] for r in rows[k:]]
    if len(grid) == 1:
        tokens = ["1"] if extras else []
        return tokens, grid, extras

    gx = _clusters([b.x for b in grid], tolx)
    gy = _clusters([b.y for b in grid], toly)
    C, R = len(gx), len(gy)
    cells: dict[tuple[int, int], int] = {}
    spans: list[tuple[list[int], list[int]]] = []
    ok = True
    for bi, b in enumerate(grid):
        c0, r0 = _nearest(gx, b.x), _nearest(gy, b.y)
        cols = [c for c in range(C) if c == c0 or (gx[c] >= b.x - tolx and gx[c] < b.x + b.w - tolx)]
        rws = [r for r in range(R) if r == r0 or (gy[r] >= b.y - toly and gy[r] < b.y + b.h - toly)]
        spans.append((cols, rws))
        for c in cols:
            for r in rws:
                if (r, c) in cells:
                    ok = False
                cells[(r, c)] = bi
    if not ok or len(grid) > 26:
        diags.append("blocks overlap or are not grid-aligned; the layout is approximated")
        order = sorted(grid, key=lambda b: (b.y, b.x))
        return (["1"] if extras else []), order, extras
    single = all(len(c) == 1 and len(r) == 1 for c, r in spans)
    # column widths: widest single-column block starting there, else the distance to the next start
    cw: list[float] = []
    for c in range(C):
        own = [grid[i].w for i, (cs, rs) in enumerate(spans) if cs == [c]]
        nxt = (gx[c + 1] - gx[c]) if c + 1 < C else (x1 - gx[c])
        cw.append(max(own) if own else nxt)
    equal = max(cw) <= 1.12 * min(cw)
    # order: row-major first appearance
    seen: list[int] = []
    for r in range(R):
        for c in range(C):
            bi = cells.get((r, c))
            if bi is not None and bi not in seen:
                seen.append(bi)
    ordered = [grid[i] for i in seen]
    n = len(grid)
    chev = all(b.kind == "box" and b.chevron for b in grid)
    flag = "steps" if chev and all(b.steps for b in grid) else "chevron"
    full_cells = single and n == C * R
    ncols = n
    if equal and margin and C == n and abs(x0 - margin) <= tolx:
        # columns left empty at the right (``@3`` with two boxes): the column width tells the count
        avg = sum(cw) / len(cw)
        total = round((W - 2 * margin + gap) / (avg + gap)) if avg + gap > 0 else n
        if total > n and abs((W - 2 * margin + gap) / total - gap - avg) <= 0.03 * avg:
            ncols = total
    if R == 1 and single:
        if chev:
            return [str(ncols), flag], ordered, extras
        if not equal:
            return [":".join(map(str, _units(cw)))], ordered, extras
        if not extras and n in (2, 3) and ncols == n:
            return [], ordered, extras
        return [str(ncols)], ordered, extras
    if full_cells and equal:
        if C == 1:  # one column of blocks: ``@1`` stacks them at their natural heights
            return ["1"], ordered, extras
        if not extras and (C, R) == (3, 2):
            return [], ordered, extras
        return [f"{C}x{R}"], ordered, extras
    if (
        single
        and equal
        and C >= 2
        and R >= 2
        and all(cells.get((i // C, i % C)) == seen[i] for i in range(n))
    ):
        return [str(C)], ordered, extras  # N columns, blocks wrap row by row, the last row may be short
    if (
        single
        and not extras
        and (C, R) == (3, 2)
        and n == 5
        and equal
        and (1, 2) not in cells
        and (R - 1, C - 1) not in cells
    ):
        return [], ordered, extras
    u = _units(cw)
    letters = {bi: chr(97 + i) for i, bi in enumerate(seen)}
    area_rows = []
    for r in range(R):
        s = ""
        for c in range(C):
            bi = cells.get((r, c))
            s += (letters[bi] if bi is not None else ".") * u[c]
        area_rows.append(s)
    tokens = ["/".join(area_rows)]
    if chev:
        tokens.append(flag)
    return tokens, ordered, extras


# --------------------------------------------------------------------------- emission

TEXTY = {"text", "itext", "table", "image", "quote"}


@dataclass
class Out:
    deck: DeckInfo
    slide_no: int
    diags: list[Diagnostic]
    save_image: Callable[[int, int, bytes, str], str]
    classes: dict[str, str]
    img_n: int = 0
    shadow: str | None = (
        None  # the shadow most filled shapes of the slide share: a deck style, not a per-box choice
    )


def _kpi(b: Block, css_heading: bool = False) -> bool:
    if len(b.children) != 1 or b.children[0].kind != "text":
        return False
    ps = b.children[0].paras
    if not 1 <= len(ps) <= 3 or any(p.marker for p in ps):
        return False
    s0 = ps[0].size
    if len(ps) == 1:  # a lone value: big next to the heading
        s1 = None if css_heading else (b.heading[0].size if b.heading else None)
    else:
        s1 = ps[1].size
    return bool(s0 and s1 and s0 >= 1.5 * s1)


def _box_class(b: Block, out: Out) -> str | None:
    """A box color class: card border in a class color (`.muted` too), or all-muted body text (old decks)."""
    cols = out.deck.colors
    lc = b.item.line_color if b.item is not None else None
    if lc and lc != cols.get("border"):
        for cname in ("primary", "success", "danger", "accent", "muted"):
            if cols.get(cname) == lc:
                return cname
    muted = cols.get("muted")
    runs = [r for ch in b.children if ch.kind == "text" for p in ch.paras for r in p.runs if r.text.strip()]
    if muted and muted != cols.get("fg") and runs and all(r.color == muted for r in runs):
        return "muted"
    return None


def _head(paras: list[ParaT], out: Out) -> str:
    txt = one_line(paras, plain_bold=True, accent=None, classes=out.classes)
    return txt[:-1] + "\\}" if txt.endswith("}") else txt


def _table_align(rows, hdr: int = 1) -> str | None:
    """``lrrl`` when the body columns are aligned differently from the automatic rule (figures right).

    Spanning cells of a grouped header table are centered by default: they do not vote.
    """
    from ..layout.tables import NUMERIC_SHARE, is_numeric

    ncols = max((len(r) for r in rows), default=0)
    if ncols < 2 or len(rows) < 2:
        return None
    grouped = any(cell.hmerge for row in rows[:hdr] for cell in row)
    letters, differs = [], False
    for c in range(ncols):
        body = [
            row[c]
            for row in rows[hdr:]
            if c < len(row)
            and not row[c].hmerge
            and not row[c].vmerge
            and not (grouped and c + 1 < len(row) and row[c + 1].hmerge)
            and any(p.plain.strip() for p in row[c].paras)
        ]
        if not body:
            letters.append("l")
            continue
        algs = [(cell.paras[0].align or "l") for cell in body]
        mode = max(set(algs), key=algs.count)
        let = {"l": "l", "ctr": "c", "r": "r"}.get(mode, "l")
        texts = ["".join(p.plain for p in cell.paras).strip() for cell in body]
        auto = "r" if sum(is_numeric(t) for t in texts) >= NUMERIC_SHARE * len(texts) else "l"
        letters.append(let)
        differs = differs or let != auto
    return "".join(letters) if differs else None


def _control_attrs(it: Item | None, common: str | None = None) -> list[str]:
    """``rotate=15``, ``shape=hexagon``, ``shadow="0 4 12 #00000040"`` of a card or picture: what the renderer
    wrote for ``{rotate= shape= shadow=}``. A plain rectangle / rounded rectangle says nothing."""
    if it is None:
        return []
    from .. import shapes

    out: list[str] = []
    if it.rot:
        out.append(f"rotate={it.rot:g}")
    if it.prst == "roundRect" and it.radius is not None and it.radius >= 0.49 * min(it.w, it.h) / 12700:
        out.append("shape=pill")
    elif it.prst and it.prst not in ("rect", "roundRect") and (name := shapes.name_of_prst(it.prst)):
        out.append(f"shape={name}")
    if it.shadow and it.shadow != common:
        out.append(f'shadow="{it.shadow}"')
    return out


def _fit_attr(it: Item) -> str:
    """``{fit=cover}`` for a cropped picture, ``{fit=stretch}`` when the box aspect differs from the image;
    ``rotate`` / ``shape`` / ``shadow`` of the picture join the same list."""
    attrs = _control_attrs(it)
    if it.cropped:
        attrs.insert(0, "fit=cover")
    else:
        try:
            import io

            from PIL import Image as PILImage

            with PILImage.open(io.BytesIO(it.img[0])) as im:
                iw, ih = im.size
            if iw and ih and it.w and it.h and abs((it.w / it.h) / (iw / ih) - 1) > 0.04:
                attrs.insert(0, "fit=stretch")
        except Exception:
            pass
    return "{" + " ".join(attrs) + "}" if attrs else ""


def _narrow_cols(b: Block, out: Out) -> int | None:
    """One block narrower than its box: the box's own ``@N`` line made N columns and it took the first."""
    if len(b.children) != 1 or b.children[0].kind == "box":
        return None
    c = b.children[0]
    pad = c.x - b.x
    inner = b.w - 2 * pad
    g = out.deck.gap / 2
    if 0 <= pad <= 0.03 * out.deck.width and inner > 0 and g > 0 and c.w < 0.85 * inner:
        ncol = round((inner + g) / (c.w + g))
        if 2 <= ncol <= 4 and abs((inner - (ncol - 1) * g) / ncol - c.w) <= 0.06 * c.w:
            return ncol
    return None


def emit_block(b: Block, out: Out) -> list[tuple[str, list[str]]]:
    acc, cls = out.deck.accent, out.classes
    if b.kind == "text":
        lines = text_lines(b.paras, accent=acc, classes=cls)
        return [("text", lines)] if lines else []
    if b.kind == "code":
        text = "\n".join("".join(r.text.replace("\n", "\n") for r in p.runs) for p in b.paras)
        fence = "```" if "```" not in text else "````"
        return [("fence", [fence + (detect_lang(b.paras) or ""), *text.split("\n"), fence])]
    if b.kind == "callout":
        lines = [one_line([p], accent=acc, classes=cls) for p in b.paras]
        lines = [ln for ln in lines if ln]
        if not lines:
            return []
        lines[0] = f"[!{b.callout}] {lines[0]}"
        return [("quote", ["> " + ln for ln in lines])]
    if b.kind == "table":
        hdr = header_rows_of(b.item.rows)
        hl = b.item.hl.strip()
        lines, lost = table_lines(
            b.item.rows,
            accent=acc,
            classes=cls,
            header_rows=hdr,
            hl_rows=hl_row_set(b.item.rows, hl, hdr) if hl else set(),
            hl_cols={int(x) - 1 for x in b.item.hlcol.split(",") if x.isdigit()},
        )
        if lost:
            out.diags.append(
                Diagnostic(
                    level="info",
                    message=f"{lost} cell(s) merged both ways were emptied",
                    slide=out.slide_no,
                    rule="import-merge",
                    hint="< and ^ cannot be combined in one cell; check the table",
                )
            )
        align = None if b.item.gantt else _table_align(b.item.rows, hdr)
        attrs = (
            ([".gantt"] if b.item.gantt else [])
            + ([f"header={hdr}"] if hdr > 1 else [])
            + ([f"align={align}"] if align else [])
            + ([_attr("hl", hl)] if hl else [])
            + ([f"hlcol={b.item.hlcol}"] if b.item.hlcol else [])
        )
        if attrs and lines:
            lines = ["{" + " ".join(attrs) + "}", *lines]
        return [("table", lines)] if lines else []
    if b.kind == "chart":
        return [("fence", chart_lines(b.item.chart))]
    if b.kind == "fence":
        return [("fence", b.lines)]
    if b.kind == "math":
        return [("fence", ["```math", *(b.item.latex or "").split("\n"), "```"])]
    if b.kind == "image":
        out.img_n += 1
        if b.item.missing is not None:  # placeholder of an absent file: write a reference that stays absent
            kind, label = b.item.missing
            label = label.replace("[", "(").replace("]", ")").replace("\n", " ")
            if re.fullmatch(r"[^\s()]+\.(png|jpe?g|gif|svg|webp|mp4|mov|webm|mp3|wav|m4a)", label, re.I):
                return [("image", [f"![]({label})"])]
            ext = {"image": "png", "video": "mp4", "audio": "mp3"}[kind]
            return [("image", [f"![{label}](images/{out.slide_no}-{out.img_n}.{ext})"])]
        blob, ext = b.item.img
        ref = out.save_image(out.slide_no, out.img_n, blob, ext)
        alt = (b.item.alt or b.item.name or "image").replace("[", "(").replace("]", ")").replace("\n", " ")
        return [("image", [f"![{alt}]({ref})" + _fit_attr(b.item)])]
    # box
    mark = "###" if b.sub else "##"
    chunks: list[tuple[str, list[str]]] = []
    kpi = _kpi(b, out.deck.css_heading)
    cname = None if kpi or b.chevron else _box_class(b, out)
    attrs = (".kpi " if kpi else "") + (f".{cname} " if cname else "") + (f"icon={b.icon} " if b.icon else "")
    attrs += " ".join(_control_attrs(b.item if not b.chevron else None, out.shadow))
    head = f"{mark} {_head(b.heading or [], out)}" + (f" {{{attrs.strip()}}}" if attrs.strip() else "")
    if b.chevron:
        content = text_lines(b.paras, accent=acc, classes=cls)
        return [("meta", [head, *content])]
    if kpi:
        lines = [one_line([p], accent=acc, classes=cls, plain_bold=True) for p in b.children[0].paras]
        narrow = _narrow_cols(b, out)
        return [("meta", [head, *[ln for ln in lines if ln], *([f"@{narrow}"] if narrow else [])])]
    toks = list(b.links)
    kids = [c for c in b.children if c.kind == "box"]
    if kids and all(c.chevron and c.sub for c in kids) and len(kids) == len(b.children):
        if len(kids) == 1:  # one chevron: its text, then the box's own ``@chevron`` line
            k = kids[0]
            lines = text_lines([*(k.heading or []), *k.paras], accent=acc, classes=cls)
            return [("meta", [head]), ("text", lines), ("meta", ["@chevron"])]
        toks = ["chevron", *toks]  # sub-boxes drawn as chevrons: the box's own ``@`` line says so
    if not toks and (ncol := _narrow_cols(b, out)):
        toks = [str(ncol)]
    chunks.append(("meta", [head, "@" + " ".join(toks)] if toks else [head]))
    for ch in b.children:
        chunks.extend(("itext" if k == "text" else k, ln) for k, ln in emit_block(ch, out))
    return chunks


def join_chunks(chunks: list[tuple[str, list[str]]], top: bool) -> list[str]:
    res: list[str] = []
    prev: str | None = None
    for kind, lines in chunks:
        if prev is not None:
            if top and kind == "text" and prev == "text":
                res.append("{}")
            elif kind in TEXTY and prev in TEXTY:
                listy = bool(re.match(r"(- |\d+\. )", lines[0])) if lines else False
                if not (listy and prev in ("text", "itext")):
                    res.append("")
        res.extend(lines)
        prev = kind
    return res


def build_slide(
    n: int,
    data: SlideData,
    deck: DeckInfo,
    diags: list[Diagnostic],
    save_image: Callable[[int, int, bytes, str], str],
    classes: dict[str, str],
    info: dict | None = None,
) -> list[str]:
    fold_into_tables(data)
    title, pool = classify(data, deck)
    pool = fold_kpi(fold_steps(pool))
    pool, rows_mode = fold_rows(pool)
    rows_slide = rows_mode is not None
    by_role = {r: [i for i in data.items if i.role == r] for r in ("lead", "conclusion", "footnote")}
    icons = [i for i in data.items if i.role == "icon"]
    blocks = make_blocks(pool, deck, icons)
    _attach_icons(icons, blocks)
    arrows = sum(1 for i in pool if i.kind == "shape" and i.prst and "rrow" in i.prst)
    dia = recover_diagram(blocks, data.conns, data.items)
    if dia is not None:
        x, y, w, h = dia.box
        blocks = [b for b in blocks if not any(b is u for u in dia.used)]
        fence = ["```mermaid", *dia.lines, "```"]
        blocks.append(Block("fence", round(x), round(y), round(w), round(h), lines=fence))
        blocks.sort(key=cmp_to_key(_reading_order))
        data.conns = []
        data.connectors = 0
    top, inner, lost = find_links(blocks, data.conns, data.items)
    texts = [b for b in blocks if b.kind == "text"]
    if data.connectors >= 2 and len(texts) >= 3 and not top:  # a diagram: keep its labels as a list
        texts.sort(key=lambda b: (round(b.y / (0.05 * deck.height)), b.x))
        paras = [
            ParaT(runs=p.runs, marker="bullet", size=p.size)
            for b in texts
            for p in b.paras
            if p.plain.strip()
        ]
        x0, y0 = min(b.x for b in texts), min(b.y for b in texts)
        merged = Block(
            "text",
            x0,
            y0,
            max(b.x + b.w for b in texts) - x0,
            max(b.y + b.h for b in texts) - y0,
            paras=paras,
        )
        blocks = [b for b in blocks if b.kind != "text"] + [merged]
        diags.append(
            Diagnostic(
                level="info",
                message="diagram flattened to a list of its labels",
                slide=n,
                rule="import-skipped",
                hint="redraw it as a mermaid fence if the flow matters",
            )
        )
        data.connectors = 0
        data.conns = []
        lost = 0
    gdiag: list[str] = []
    stretch_visuals(blocks)
    groups = None if (top or inner) else split_row_groups(blocks, deck.width, deck.height)
    group_tokens: list[list[str]] = []
    arrow_items = [i for i in pool if i.kind == "shape" and i.prst and "rrow" in i.prst]
    if groups:
        grid, extras = [], []
        for g in groups:
            tk, gr, ex = plan_grid(g, deck.width, deck.height, gdiag, deck.margin_x, deck.gap)
            tk = tk or [str(len(gr))]
            top_y, bot_y = min(b.y for b in g), max(b.y + b.h for b in g)
            nar = sum(
                1 for a in arrow_items if top_y - 0.03 * deck.height <= a.cy <= bot_y + 0.03 * deck.height
            )
            if nar and "chevron" not in tk and len(gr) > 1 and nar >= len(gr) - 1:
                tk = [*tk, "flow"]
            group_tokens.append(tk)
            grid += gr
        tokens = group_tokens[0]
    else:
        tokens, grid, extras = plan_grid(blocks, deck.width, deck.height, gdiag, deck.margin_x, deck.gap)
    if rows_slide:
        tokens = ["rows"]
    for g in gdiag:
        diags.append(
            Diagnostic(level="info", message=g, slide=n, rule="import-layout", hint="check the arrangement")
        )
    lost = lost if data.conns else data.connectors
    if lost:
        diags.append(
            Diagnostic(
                level="info",
                message=f"{lost} connector(s) dropped",
                slide=n,
                rule="import-skipped",
                hint="add arrows back with '@' tokens such as a>b if they matter",
            )
        )
    out = Out(deck, n, diags, save_image, classes)
    shared = Counter(it.shadow for it in data.items if it.shadow and it.fill).most_common(1)
    out.shadow = shared[0][0] if shared and shared[0][1] >= 2 else None
    lines: list[str] = []
    if title is not None:
        lines.append("# " + _head(title.paras, out))
    else:
        lines.append("---")
        if not blocks and not any(by_role.values()) and not tokens:
            tokens = ["blank"]
    lead = by_role["lead"]
    if lead:
        lines.append(
            "> "
            + one_line(lead[0].paras, accent=deck.accent, classes=classes, implied=deck.implied.get("lead"))
        )
    n_boxes = sum(1 for b in grid if b.kind == "box")
    if not groups and arrows and "chevron" not in tokens and n_boxes > 1 and arrows >= n_boxes - 1:
        tokens.append("flow")
    if info is not None:
        info["tokens"] = [] if groups else [t for t in tokens if t != "blank"]
        info["at"] = None
    seq = [*grid, *extras]
    links = link_tokens(top, seq, drop_next="flow" in tokens)
    for b in seq:
        if b.kind == "box" and id(b) in inner:
            b.links = link_tokens(inner[id(b)], b.children)
    if info is not None:
        info["links"] = links
    extra: list[str] = []
    title_only = (
        title is not None
        and all(b.kind == "text" for b in blocks)
        and sum(len(b.paras) for b in blocks) + len(by_role["lead"]) <= 2
        and not any(p.marker for b in blocks for p in b.paras)
        and not by_role["conclusion"]
        and not by_role["footnote"]
        and not arrows
        and not data.conns
    )
    if title_only:
        footer_row = any(
            i.role == "decor"
            and (i.ph in ("ftr", "sldNum") or i.has_slidenum or i.name.lower() in ("footer", "slide number"))
            for i in data.items
        )
        anchored = any(  # cover.band_h: a band anchored to the top or its rule marks the cover, not a section
            i.role == "decor"
            and (
                i.name.lower() == "rule"
                or (i.name.lower().startswith("band") and i.y <= 0 and i.h >= 0.3 * deck.height)
            )
            for i in data.items
        )
        starts = {nums[0] for _, nums in deck.sections if nums}
        if n == 1 and not anchored and (footer_row or len(deck.sections) == 1):
            extra.append("section")
        elif n > 1 and deck.sections and n not in starts:
            extra.append("cover")
    if any(_NUM_BADGE.fullmatch((i.name or "").lower().strip()) for i in data.items):
        extra.append("num")  # `@4 num`: the badges are decor, the slide word draws them again
    boxes = [b for b in seq if b.kind == "box"]
    if any(b.items for b in boxes) and not any(
        not b.items and any(p.marker for c in b.children if c.kind == "text" for p in c.paras) for b in boxes
    ):
        extra.append("items")  # `@4 items`: the item cards are the boxes' bullets
    if rows_mode == "plain":
        extra.append("plain")  # `@rows plain`: bars without number badges
    if data.transition:
        extra.append("t=" + data.transition)
    if data.build:
        extra.append("build")
    if data.hidden:
        extra.append("hidden")
    if info is not None:
        info["extra"] = extra
        info["title_only"] = title_only
    tokens = [*tokens, *links, *extra]
    if info is not None:
        info["pos"] = len(lines)
    if tokens:
        if info is not None:
            info["at"] = len(lines)
        lines.append("@" + " ".join(tokens))
    chunks: list[tuple[str, list[str]]] = []
    starts: dict[int, list[str]] = {}
    if groups:
        pos = 0
        for g, tk in zip(groups, group_tokens, strict=True):
            starts[pos] = tk
            pos += len(g)
    for i, b in enumerate(seq):
        if i in starts and i > 0:
            chunks.append(("meta", ["@end", "@" + " ".join(starts[i])]))
        chunks.extend(emit_block(b, out))
        if b.kind == "box":
            nxt = seq[i + 1] if i + 1 < len(seq) else None
            if nxt is not None and nxt.kind != "box":
                chunks.append(("meta", ["@end"]))
    lines.extend(join_chunks(chunks, True))
    for it in sorted(by_role["footnote"], key=lambda i: (i.y, i.x)):
        for p in it.paras:
            txt = one_line([p], accent=deck.accent, classes=classes, implied=deck.implied.get("footnote"))
            if txt.startswith("&#8251;"):
                lines.append("※" + txt[len("&#8251;") :])
            elif txt:
                lines.append(txt if txt.startswith("※") else "^ " + txt)
    if by_role["conclusion"]:
        txt = one_line(
            by_role["conclusion"][0].paras,
            accent=deck.accent,
            classes=classes,
            plain_bold=True,
            implied=deck.implied.get("conclusion"),
        )
        if txt:
            lines.append("> " + txt)
    lines.extend(notes_lines(data.notes))
    return lines


def notes_lines(text: str | None) -> list[str]:
    """Speaker notes as a ``???`` block (empty when there are none)."""
    if not text:
        return []
    nl = text.replace("\r", "").split("\n")
    nl = [(" " + x) if re.match(r"^(#|---)", x) else x for x in nl]
    return ["??? " + nl[0].strip(), *nl[1:]]
