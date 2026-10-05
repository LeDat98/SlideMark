"""Flat items -> SlideMark structure: title, lead, boxes, grid (``@`` line), footnotes, conclusion."""

from __future__ import annotations

import math
import re
from collections.abc import Callable
from dataclasses import dataclass, field

from ..ir import Diagnostic
from .emit import chart_lines, one_line, table_lines, text_lines
from .read import Item, ParaT, SlideData

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
    callout: str = "note"
    icon: str | None = None


# --------------------------------------------------------------------------- classification


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


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
            or nm == "background"
            or nm.endswith(" accent")
            or (it.kind == "text" and it.y >= 0.85 * H and _norm(it.text) in deck.footers)
            or (it.kind in ("shape", "line") and not it.fill and not it.line)
            or (it.kind != "image" and it.area == 0 and not it.text)
        ):
            it.role = "decor"
        if it.kind == "image" and it.area >= 0.9 * W * H and it.w >= 0.95 * W:
            it.role = "decor"  # full-slide background picture
    live = [i for i in items if i.role is None]
    title = next((i for i in live if i.kind == "text" and i.ph in ("title", "ctrTitle")), None)
    if title is None:
        top = [
            i for i in live if i.kind == "text" and i.y < 0.3 * H and len(i.paras) <= 2 and len(i.text) <= 120
        ]
        if top:
            title = max(top, key=lambda i: (i.max_size or 0, -i.y))
    if title:
        title.role = "title"
    # callouts: a filled text shape with a thin filled bar on its left edge
    for it in live:
        if it.role or it.kind != "text" or not it.fill:
            continue
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
        if it.kind == "text" and (
            it.name.lower().startswith("footnote")
            or (not it.fill and not it.line and it.y >= 0.8 * H and it.h <= 0.12 * H and small)
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


def make_blocks(pool: list[Item], deck: DeckInfo) -> list[Block]:
    W, H = deck.width, deck.height
    slide_area = W * H
    cands = [
        i
        for i in pool
        if i.kind in ("text", "shape")
        and (i.fill or i.line)
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
        if it.kind == "table" or it.kind == "chart" or it.kind == "image":
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
            return [Block("box", it.x, it.y, it.w, it.h, item=it, heading=[it.paras[0]], paras=it.paras[1:])]
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
            if (
                k0.kind == "text"
                and not kids.get(k0.uid)
                and len(k0.paras) == 1
                and not k0.paras[0].marker
                and not (k0.role or "").startswith("callout")
                and k0.y - it.y <= 0.3 * it.h
            ):
                head, body = k0.paras, real[1:]
        blocks: list[Block] = []
        for k in body:
            blocks.extend(make(k, True))
        blocks.sort(key=lambda b: (b.y, b.x))
        if head is None:
            return blocks
        if extra:
            blocks.insert(0, Block("text", it.x, it.y, it.w, it.h, paras=extra))
        return [Block("box", it.x, it.y, it.w, it.h, item=it, heading=head, children=blocks, sub=nested)]

    out: list[Block] = []
    for it in pool:
        if it.uid in parent:
            continue
        out.extend(make(it, False))
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


def plan_grid(
    blocks: list[Block], W: int, H: int, diags: list[str]
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
    full_cells = single and n == C * R
    if R == 1 and single:
        if chev:
            return [str(n), "chevron"], ordered, extras
        if not equal:
            return [":".join(map(str, _units(cw)))], ordered, extras
        if not extras and n in (2, 3):
            return [], ordered, extras
        return [str(n)], ordered, extras
    if full_cells and equal:
        if not extras and (C, R) == (3, 2):
            return [], ordered, extras
        return [f"{C}x{R}"], ordered, extras
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
        tokens.append("chevron")
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


def _kpi(b: Block) -> bool:
    if len(b.children) != 1 or b.children[0].kind != "text":
        return False
    ps = b.children[0].paras
    if not 2 <= len(ps) <= 3 or any(p.marker for p in ps):
        return False
    s0, s1 = ps[0].size, ps[1].size
    return bool(s0 and s1 and s0 >= 1.5 * s1)


def _head(paras: list[ParaT], out: Out) -> str:
    txt = one_line(paras, plain_bold=True, accent=None, classes=out.classes)
    return txt[:-1] + "\\}" if txt.endswith("}") else txt


def emit_block(b: Block, out: Out) -> list[tuple[str, list[str]]]:
    acc, cls = out.deck.accent, out.classes
    if b.kind == "text":
        lines = text_lines(b.paras, accent=acc, classes=cls)
        return [("text", lines)] if lines else []
    if b.kind == "code":
        text = "\n".join("".join(r.text.replace("\n", "\n") for r in p.runs) for p in b.paras)
        fence = "```" if "```" not in text else "````"
        return [("fence", [fence, *text.split("\n"), fence])]
    if b.kind == "callout":
        lines = [one_line([p], accent=acc, classes=cls) for p in b.paras]
        lines = [ln for ln in lines if ln]
        if not lines:
            return []
        lines[0] = f"[!{b.callout}] {lines[0]}"
        return [("quote", ["> " + ln for ln in lines])]
    if b.kind == "table":
        lines, lost = table_lines(b.item.rows, accent=acc, classes=cls)
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
        return [("table", lines)] if lines else []
    if b.kind == "chart":
        return [("fence", chart_lines(b.item.chart))]
    if b.kind == "image":
        out.img_n += 1
        blob, ext = b.item.img
        ref = out.save_image(out.slide_no, out.img_n, blob, ext)
        alt = (b.item.alt or b.item.name or "image").replace("[", "(").replace("]", ")").replace("\n", " ")
        return [("image", [f"![{alt}]({ref})"])]
    # box
    mark = "###" if b.sub else "##"
    chunks: list[tuple[str, list[str]]] = []
    kpi = _kpi(b)
    attrs = (".kpi " if kpi else "") + (f"icon={b.icon}" if b.icon else "")
    head = f"{mark} {_head(b.heading or [], out)}" + (f" {{{attrs.strip()}}}" if attrs else "")
    if b.chevron:
        content = text_lines(b.paras, accent=acc, classes=cls)
        return [("meta", [head, *content])]
    if kpi:
        lines = [one_line([p], accent=acc, classes=cls, plain_bold=True) for p in b.children[0].paras]
        return [("meta", [head, *[ln for ln in lines if ln]])]
    chunks.append(("meta", [head]))
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
    title, pool = classify(data, deck)
    by_role = {r: [i for i in data.items if i.role == r] for r in ("lead", "conclusion", "footnote")}
    blocks = make_blocks(pool, deck)
    _attach_icons([i for i in data.items if i.role == "icon"], blocks)
    arrows = sum(1 for i in pool if i.kind == "shape" and i.prst and "rrow" in i.prst)
    notes: list[str] = []
    texts = [b for b in blocks if b.kind == "text"]
    if data.connectors >= 2 and len(texts) >= 3:  # a diagram: keep its labels as a list
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
    gdiag: list[str] = []
    tokens, grid, extras = plan_grid(blocks, deck.width, deck.height, gdiag)
    for g in gdiag:
        diags.append(
            Diagnostic(level="info", message=g, slide=n, rule="import-layout", hint="check the arrangement")
        )
    if data.connectors:
        diags.append(
            Diagnostic(
                level="info",
                message=f"{data.connectors} connector(s) dropped",
                slide=n,
                rule="import-skipped",
                hint="add arrows back with '@' tokens such as a>b if they matter",
            )
        )
    out = Out(deck, n, diags, save_image, classes)
    lines: list[str] = []
    if title is not None:
        lines.append("# " + _head(title.paras, out))
    else:
        lines.append("---")
        if not blocks and not any(by_role.values()) and not tokens:
            tokens = ["blank"]
    lead = by_role["lead"]
    if lead:
        lines.append("> " + one_line(lead[0].paras, accent=deck.accent, classes=classes))
    if arrows and tokens and tokens[0].isdigit() and len(grid) > 1 and arrows >= len(grid) - 1:
        tokens.append("flow")
    if info is not None:
        info["tokens"] = [t for t in tokens if t != "blank"]
        info["at"] = None
    if data.hidden:
        tokens = [*tokens, "hidden"]
    if tokens:
        if info is not None:
            info["at"] = len(lines)
        lines.append("@" + " ".join(tokens))
    chunks: list[tuple[str, list[str]]] = []
    seq = [*grid, *extras]
    for i, b in enumerate(seq):
        chunks.extend(emit_block(b, out))
        if b.kind == "box":
            nxt = seq[i + 1] if i + 1 < len(seq) else None
            if nxt is not None and nxt.kind != "box":
                chunks.append(("meta", ["@end"]))
    lines.extend(join_chunks(chunks, True))
    for it in sorted(by_role["footnote"], key=lambda i: (i.y, i.x)):
        for p in it.paras:
            txt = one_line([p], accent=deck.accent, classes=classes)
            if txt:
                lines.append("※ " + txt)
    if by_role["conclusion"]:
        txt = one_line(by_role["conclusion"][0].paras, accent=deck.accent, classes=classes, plain_bold=True)
        if txt:
            lines.append("> " + txt)
    if data.notes:
        nl = data.notes.replace("\r", "").split("\n")
        nl = [(" " + x) if re.match(r"^(#|---)", x) else x for x in nl]
        notes = ["??? " + nl[0].strip(), *nl[1:]]
        lines.extend(notes)
    return lines
