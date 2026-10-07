"""Importer folds of the DL3b part 2 forms: named shapes -> the same ``@word`` slides.

``layout/forms2.py`` names every shape it draws (``Iconlist N``, ``Quote text``, ``Proscons 1 item 2``,
``Progress N fill``, ``Harvey r,c q3``, ``Pin N``, ``Split fill``; a heatmap table carries `` heatmap=lo;hi;
colors;text`` in its name). ``fold`` reads them back: the shapes leave the pool and the slide gets its word,
its secondary attributes and the body lines the form is written with. A deck that was edited in PowerPoint
keeps whatever the names still say; a shape that lost its name is read like any other shape.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from fractions import Fraction

from .emit import inline, one_line, table_lines
from .read import CellT, Item, ParaT, RunT, SlideData

_ICON = re.compile(r"Iconlist (\d+)")
_PROS = re.compile(r"Proscons (\d+)( head| item (\d+)( glyph)?)?")
_PROG = re.compile(r"Progress (\d+) (label|track|fill|value)")
_HARVEY = re.compile(r"Harvey (?:(head|row|col|text) )?(\d+)(?:,(\d+))?(?: (q\d|pie))?")
_PIN = re.compile(r"Pin (\d+)( legend)?")
_PINS_LEG = re.compile(r"Pins legend (\d+)")
_ALIGN = {"ctr": "center", "r": "right"}


@dataclass
class Folded:
    """What a form leaves for ``build_slide``: the pool without the form's shapes, the ``@`` tokens, and
    blocks (``Block`` objects) to put before / after the planned grid."""

    pool: list[Item]
    tokens: list[str]
    replace_tokens: bool = True  # False: the tokens join the planned grid tokens (``@split`` keeps its grid)
    before: list = field(default_factory=list)
    after: list = field(default_factory=list)


def _named(pool: list[Item], pat: re.Pattern[str]) -> list[tuple[re.Match[str], Item]]:
    return [(m, it) for it in pool if (m := pat.fullmatch(it.name or ""))]


def _hex(it: Item) -> str | None:
    f = it.fill
    return f"#{f}" if f and re.fullmatch(r"[0-9A-Fa-f]{6}", f) else None


def _fence(Block, items: list[Item], lines: list[str]):
    x0, y0 = min(i.x for i in items), min(i.y for i in items)
    x1, y1 = max(i.x + i.w for i in items), max(i.y + i.h for i in items)
    return Block("fence", x0, y0, x1 - x0, y1 - y0, lines=lines)


def _md(paras: list[ParaT], deck, plain_bold: bool = False) -> str:
    return one_line(paras, accent=deck.accent, classes={}, plain_bold=plain_bold) if paras else ""


def _unbold(paras: list[ParaT]) -> list[ParaT]:
    """The paragraphs without the bold the form itself adds to labels and headings."""
    return [replace(p, runs=[replace(r, bold=False) for r in p.runs]) for p in paras]


def _runs_md(runs: list[RunT], deck) -> str:
    return inline(runs, accent=deck.accent, classes={}).replace("\n", " ").strip()


# --------------------------------------------------------------------------- iconlist


def _iconlist(pool: list[Item], data: SlideData, deck, Block) -> Folded | None:
    texts = sorted(((int(m.group(1)), it) for m, it in _named(pool, _ICON) if it.paras), key=lambda t: t[0])
    if not texts:
        return None
    icons = [i for i in data.items if i.role == "icon" and i.name.lower().startswith("icon ")]
    lines: list[str] = []
    for _n, it in texts:
        box = [
            i
            for i in icons
            if it.x - 2 <= i.x <= it.x + it.w
            and it.y - 2 <= i.cy <= it.y + it.h  # the icon at the cell's left
        ]
        name = ""
        if box:
            name = min(box, key=lambda i: i.x).name[5:].strip()
        head = f"icon={name} " if name else ""
        paras = [p for p in it.paras if p.runs and p.plain.strip()]
        if not paras:
            continue
        first = _md(paras[:1], deck)
        if len(paras) >= 2:  # **Title** + the first text paragraph on one line, further ones nested
            first += " " + _md(paras[1:2], deck)
        lines.append("- " + head + first)
        lines += ["  - " + _md([p], deck) for p in paras[2:]]
    xs = sorted({round(it.x / max(deck.width * 0.02, 1)) for _n, it in texts})
    cols = max(min(len(xs), 3), 1)
    tokens = ["iconlist", f"cols={cols}"]
    if (fill := _hex(texts[0][1])) is not None:
        tokens.append(f"fill={fill}")
    drop = {it.uid for _n, it in texts}
    drop |= {i.uid for i in icons if i.name.lower().startswith("icon ")}
    rest = [i for i in pool if i.uid not in drop]
    return Folded(rest, tokens, after=[_fence(Block, [it for _n, it in texts], lines)])


# --------------------------------------------------------------------------- quote


def _quote(pool: list[Item], data: SlideData, deck, Block) -> Folded | None:
    text = next((it for it in pool if it.name == "Quote text" and it.paras), None)
    if text is None:
        return None
    by = next((it for it in pool if it.name == "Quote by"), None)
    gone = {
        it.uid
        for it in pool
        if it.name in ("Quote text", "Quote by", "Quote mark", "Quote panel", "Quote bar")
    }
    lines = []
    for p in text.paras:
        if p.plain.strip():
            lines += [f"> {_md([p], deck)}", ">"]
    if by is not None and by.paras:
        lines.append(f"> {_md(by.paras, deck)}")
    elif lines:
        lines.pop()
    tokens = ["quote"]
    align = _ALIGN.get(text.paras[0].align or "")
    if align:
        tokens.append(f"align={align}")
    panel = next((it for it in pool if it.name == "Quote panel"), None)
    if panel is not None and _hex(panel):
        tokens.append(f"fill={_hex(panel)}")
    rest = [i for i in pool if i.uid not in gone]
    return Folded(rest, tokens, after=[_fence(Block, [text, *([by] if by else [])], lines)])


# --------------------------------------------------------------------------- proscons


def _proscons(pool: list[Item], data: SlideData, deck, Block) -> Folded | None:
    got = [(m, it) for m, it in _named(pool, _PROS)]
    heads = {int(m.group(1)): it for m, it in got if (m.group(2) or "").strip() == "head"}
    if len(heads) < 2:
        return None
    lines: list[str] = []
    for k in sorted(heads):
        lines.append(f"## {_md(heads[k].paras, deck, plain_bold=True)}")
        items = sorted(
            (
                (int(m.group(3)), it)
                for m, it in got
                if m.group(1) == str(k) and m.group(3) and not m.group(4)
            ),
            key=lambda t: t[0],
        )
        glyphs = {int(m.group(3)): it for m, it in got if m.group(1) == str(k) and m.group(3) and m.group(4)}
        for n, it in items:
            g = glyphs.get(n)
            sign = "+" if g is not None and g.text.strip() in ("+", "✓", "✔") else "-"
            if g is None:
                sign = "+" if k == min(heads) else "-"
            lines.append(f"{sign} {_md(it.paras, deck)}")
    drop = {it.uid for _m, it in got}
    rest = [i for i in pool if i.uid not in drop]
    return Folded(rest, ["proscons"], after=[_fence(Block, [it for _m, it in got], lines)])


# --------------------------------------------------------------------------- progress


def _progress(pool: list[Item], data: SlideData, deck, Block) -> Folded | None:
    got = _named(pool, _PROG)
    labels = {int(m.group(1)): it for m, it in got if m.group(2) == "label"}
    if not labels:
        return None
    values = {int(m.group(1)): it for m, it in got if m.group(2) == "value"}
    tracks = {int(m.group(1)): it for m, it in got if m.group(2) == "track"}
    fills = {int(m.group(1)): it for m, it in got if m.group(2) == "fill"}
    lines, maxes = [], []
    pct = True
    for n in sorted(labels):
        v = values.get(n)
        val = v.text.strip() if v is not None else ""
        pct = pct and val.endswith("%")
        lines.append(f"- {_md(labels[n].paras, deck)} {val}".rstrip())
        num = re.match(r"[-+]?\d+(?:\.\d+)?", val)
        if num and n in tracks and n in fills and tracks[n].w and fills[n].w and not val.endswith(("%", "/")):
            if "/" not in val:
                maxes.append(float(num.group(0)) * tracks[n].w / fills[n].w)
    tokens = ["progress"]
    if not pct and maxes:
        m = sorted(maxes)[len(maxes) // 2]
        nice = round(m, 2)
        tokens.append("max=" + (str(int(nice)) if nice == int(nice) else str(nice)))
    drop = {it.uid for _m, it in got}
    rest = [i for i in pool if i.uid not in drop]
    return Folded(rest, tokens, after=[_fence(Block, [it for _m, it in got], lines)])


# --------------------------------------------------------------------------- harvey


def _cell(text: str = "", paras: list[ParaT] | None = None) -> CellT:
    return CellT(paras=paras if paras is not None else ([ParaT(runs=[RunT(text=text)])] if text else []))


def _harvey(pool: list[Item], data: SlideData, deck, Block) -> Folded | None:
    got = [(m, it) for m, it in _named(pool, _HARVEY)]
    if not any(m.group(4) and m.group(4).startswith("q") for m, _it in got):
        return None
    grid: dict[tuple[int, int], CellT] = {}
    labels: dict[int, list[ParaT]] = {}
    col_cells: dict[int, list[ParaT]] = {}
    hrow: int | None = None
    for m, it in got:
        kind, r, c, tail = m.group(1), int(m.group(2)), m.group(3), m.group(4)
        if kind == "head":  # the header row's label cell (the table's corner)
            labels[r] = _unbold(it.paras)
            hrow = r
        elif kind == "row":
            labels[r] = _unbold(it.paras)
        elif kind == "col":  # `Harvey col C`: the header of column C
            col_cells[r] = _unbold(it.paras)
        elif kind == "text" and c is not None:
            grid[(r, int(c))] = _cell(it.text.strip())
        elif c is not None and tail and tail.startswith("q"):
            grid[(r, int(c))] = _cell(tail[1:])
    body_rows = sorted({r for (r, _c) in grid})
    ncols = max([c for (_r, c) in grid] + list(col_cells), default=0)
    first_c = min([c for (_r, c) in grid] + list(col_cells), default=1)
    has_labels = bool(labels)
    head = [_cell(paras=labels[hrow])] if has_labels and hrow in labels else ([_cell()] if has_labels else [])
    head += [_cell(paras=col_cells[c]) if c in col_cells else _cell() for c in range(first_c, ncols + 1)]
    rows = [head]
    for r in body_rows:
        row = [_cell(paras=labels[r])] if has_labels and r in labels else ([_cell()] if has_labels else [])
        row += [grid.get((r, c), _cell()) for c in range(first_c, ncols + 1)]
        rows.append(row)
    lines, _lost = table_lines(rows, accent=deck.accent, classes={}, header_rows=1)
    drop = {it.uid for _m, it in got}
    rest = [i for i in pool if i.uid not in drop]
    return Folded(rest, ["harvey"], after=[_fence(Block, [it for _m, it in got], lines)])


# --------------------------------------------------------------------------- heatmap


def _heatmap(pool: list[Item], data: SlideData, deck, Block) -> Folded | None:
    t = next((i for i in pool if i.kind == "table" and getattr(i, "heatmap", "")), None)
    if t is None:
        return None
    parts = t.heatmap.split(";")
    tokens = ["heatmap"]
    if len(parts) >= 2:
        tokens += [f"min={parts[0]}", f"max={parts[1]}"]
    if len(parts) >= 3 and parts[2]:
        tokens.append(f"colors={parts[2]}")
    if len(parts) >= 4 and parts[3] not in ("", "auto"):
        tokens.append(f"text={parts[3]}")
    return Folded(pool, tokens, replace_tokens=False)


# --------------------------------------------------------------------------- split, pins


def _split(pool: list[Item], data: SlideData, deck, Block) -> Folded | None:
    W, H = deck.width, deck.height
    fill = next((i for i in pool if i.name == "Split fill"), None)
    tol = 0.01
    img = next(
        (
            i
            for i in pool
            if i.kind == "image"
            and i.h >= (1 - tol) * H
            and i.y <= tol * H
            and (i.x <= tol * W or i.x + i.w >= (1 - tol) * W)
            and i.w < 0.9 * W
        ),
        None,
    )
    side_item = fill or img
    if side_item is None:
        return None
    side = "left" if side_item.x + side_item.w / 2 < W / 2 else "right"
    iw = side_item.w
    ratio = Fraction(iw, max(W - iw, 1)).limit_denominator(5)
    tokens = ["split", f"side={side}", f"ratio={ratio.numerator}:{ratio.denominator}"]
    bleed = side_item.h >= (1 - tol) * H and side_item.y <= tol * H
    if bleed:
        tokens.append("bleed=on")
    if fill is not None and _hex(fill):
        tokens.append(f"fill={_hex(fill)}")
    rest = [i for i in pool if i is not fill and i is not img]
    before = []
    if img is not None:
        before = [Block("image", img.x, img.y, img.w, img.h, item=img)]
    return Folded(rest, tokens, replace_tokens=False, before=before)


def _pct(v: float) -> str:
    return f"{round(v * 100):g}%"


def _pins(pool: list[Item], data: SlideData, deck, Block) -> Folded | None:
    pins = {int(m.group(1)): it for m, it in _named(pool, _PIN) if not m.group(2)}
    if not pins:
        return None
    img = next((i for i in pool if i.kind == "image"), None)
    if img is None:
        return None
    legend = {int(m.group(1)): it for m, it in _named(pool, _PINS_LEG)}
    lines = []
    for n in sorted(pins):
        p = pins[n]
        fx, fy = (p.cx - img.x) / max(img.w, 1), (p.cy - img.y) / max(img.h, 1)
        label = _md(legend[n].paras, deck) if n in legend else ""
        lines.append(f"- x={_pct(fx)} y={_pct(fy)} {label}".rstrip())
    tokens = ["pins"]
    if not legend:
        tokens.append("legend=off")
    else:
        first = next(iter(legend.values()))
        if first.x < img.x + img.w:  # the legend sits under the image
            tokens.append("legend=bottom")
    drop = {it.uid for it in [*pins.values(), *legend.values()]}
    drop |= {it.uid for m, it in _named(pool, _PIN) if m.group(2)}
    drop.add(img.uid)
    rest = [i for i in pool if i.uid not in drop]
    members = [*pins.values(), *legend.values()]
    return Folded(
        rest,
        tokens,
        before=[Block("image", img.x, img.y, img.w, img.h, item=img)],
        after=[_fence(Block, members, lines)],
    )


_FOLDS = (_iconlist, _quote, _proscons, _progress, _harvey, _heatmap, _pins, _split)


def fold(pool: list[Item], data: SlideData, deck) -> Folded | None:
    """The first form whose named shapes the slide holds, or ``None`` (the slide is read as usual)."""
    from .structure import Block

    for fn in _FOLDS:
        try:
            got = fn(pool, data, deck, Block)
        except Exception:  # an unreadable form is read as plain shapes
            got = None
        if got is not None:
            return got
    return None


__all__ = ["Folded", "fold"]
