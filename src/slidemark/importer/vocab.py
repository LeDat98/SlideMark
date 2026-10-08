"""Import of the composition vocabulary (DL3b): the named shapes of ``@timeline`` ``@vs`` ``@matrix``
``@funnel`` ``@pyramid`` ``@cycle`` ``@agenda`` ``@statement`` fold back into their source.

The layout names every shape it draws for a form (``Timeline 2``, ``Timeline 2 dot``, ``Funnel 1 up``,
``Cycle 3 arrow ccw``, ``Agenda 2 now`` ...), so the importer needs no geometry guessing: the name says the
form, the number the order, a suffix the choice (``now`` = ``{.accent}``, ``up`` / ``down`` / ``ccw`` =
``dir=``).
``extract`` marks every named shape as decor (so classification ignores them) and returns a ``FormFold``:

- ``@timeline @funnel @pyramid @cycle @agenda @statement``: the texts carry the content; the fold builds the
  ``##`` boxes (or the list / lines) itself;
- ``@vs @matrix``: the cards are ordinary boxes the usual path imports; the fold adds the form word, the axis
  labels (``x=`` ``y=``), the verdict box and the ``{.hero}`` mark.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace

from .read import Item, ParaT, RunT, SlideData
from .structure import Block

_NAMES = {
    "timeline": re.compile(r"Timeline (?:line|(\d+)(?: (?:stem|dot|now))?)"),
    "vs": re.compile(r"VS (?:badge|verdict)"),
    "matrix": re.compile(r"Matrix [xy] (?:axis|label)"),
    "funnel": re.compile(r"Funnel (\d+)(?: (?:up|down))?(?: text)?"),
    "pyramid": re.compile(r"Pyramid (\d+)(?: (?:up|down))?(?: text)?"),
    "cycle": re.compile(r"Cycle (?:center|(\d+)(?: text| icon| arrow(?: ccw)?)?)"),
    "agenda": re.compile(r"Agenda (\d+)(?: now)?(?: (?:num|rule|fill))?"),
    "statement": re.compile(r"Statement(?: caption)?"),
    "stairs": re.compile(r"Stairs (\d+)"),
    "nested": re.compile(r"Nested (\d+)(?: text| list| icon)?"),
    "flowdisc": re.compile(r"Flow (\d+) (?:disc|line|text|icon)"),
}
_TEXT = {
    "timeline": re.compile(r"Timeline (\d+)( now)?"),
    "funnel": re.compile(r"Funnel (\d+)(?: (up|down))?( text)?"),
    "pyramid": re.compile(r"Pyramid (\d+)(?: (up|down))?( text)?"),
    "cycle": re.compile(r"Cycle (\d+)( text)?"),
    "agenda": re.compile(r"Agenda (\d+)( now)?"),
    "stairs": re.compile(r"Stairs (\d+)"),
}


_WITH_DATA = (
    "cycle",
    "nested",
    "flowdisc",
)  # folds that also read the slide's other shapes (the icons drawn in the nodes)


@dataclass
class FormFold:
    form: str
    tokens: list[str]
    boxes: list[Block] = field(default_factory=list)  # content the fold built itself
    keep: bool = False  # vs / matrix: the usual path builds the cards, `adjust` finishes them
    verdict: Block | None = None
    hero: bool = False  # vs: one card is drawn as the winner

    def adjust(self, blocks: list[Block], border: str | None) -> list[Block]:
        """vs / matrix: the card blocks with the winner marked and the verdict box last. The winner's border
        is drawn in ``vs.win.line``: the one card whose border is not the deck's plain card border."""
        if self.form == "vs":
            cards = [b for b in blocks if b.kind == "box" and b.item is not None]
            odd = [c for c in cards if c.item.line_color not in (None, border)]  # type: ignore[union-attr]
            if len(cards) == 2 and len(odd) == 1:
                odd[0].flag = "hero"
            if self.verdict is not None:
                return [*blocks, self.verdict]
        return blocks


def _name(it: Item) -> str:
    return (it.name or "").strip()


def detect(data: SlideData) -> str | None:
    """The form whose named shapes the slide holds (the first one found), else ``None``."""
    for it in data.items:
        nm = _name(it)
        for form, pat in _NAMES.items():
            if pat.fullmatch(nm):
                return form
    return None


def _plain(r: RunT) -> RunT:
    """A run without the form's own bold and ink (the layout sets them: they are not emphasis)."""
    return replace(r, bold=False, color=None)


def _quote(v: str) -> str:
    return '"' + v.replace('"', "'") + '"' if re.search(r"[\s\"']", v) or not v.isascii() else v


def _box(it: Item, heading: list[ParaT], rest: list[ParaT], flag: str = "") -> Block:
    kids = [Block("text", it.x, it.y, it.w, it.h, paras=rest)] if rest else []
    return Block(
        "box", it.x, it.y, it.w, it.h, item=it, heading=heading, children=kids, flag=flag, drawn=True
    )


def _stack(its: list[Item]) -> list[Item]:
    return sorted(its, key=lambda i: i.y)


def extract(data: SlideData) -> FormFold | None:
    """Fold the named shapes of a form slide; marks them ``decor``. ``None`` when the slide holds no form."""
    form = detect(data)
    if form is None:
        return None
    named = [it for it in data.items if _NAMES[form].fullmatch(_name(it))]
    for it in named:
        it.role = "decor"
    data.conns, data.connectors = [], 0  # stems, axis arrows and rules are the form's, not links
    texts = [it for it in named if it.kind == "text" or it.paras]
    fold = {
        "timeline": _timeline,
        "funnel": _stage,
        "pyramid": _stage,
        "cycle": _cycle,
        "agenda": _agenda,
        "statement": _statement,
        "stairs": _stairs,
        "nested": _nested,
        "flowdisc": _flowdisc,
        "vs": _vs,
        "matrix": _matrix,
    }[form]
    return fold(form, named, texts, data) if form in _WITH_DATA else fold(form, named, texts)


# --------------------------------------------------------------------------- one fold per form


def _timeline(form: str, named: list[Item], texts: list[Item]) -> FormFold | None:
    ms = sorted(
        ((int(m.group(1)), bool(m.group(2)), it) for it in texts if (m := _TEXT[form].fullmatch(_name(it)))),
        key=lambda t: t[0],
    )
    if len(ms) < 2:
        return None
    xs = [it.cx for _n, _now, it in ms]
    vertical = max(xs) - min(xs) < 0.05 * max(it.w for _n, _now, it in ms)
    dots = [it for it in named if re.fullmatch(r"Timeline \d+ dot", _name(it))]
    marks = "off" if not dots else "num" if any(it.paras for it in dots) else "on"
    tokens = ["timeline"]
    if vertical:
        tokens.append("dir=v")
    if marks != "on":
        tokens.append(f"marks={marks}")
    boxes = []
    for _n, now, it in ms:
        paras = [p for p in it.paras if p.plain.strip()]
        if not paras:
            continue
        boxes.append(_box(it, paras[:1], paras[1:], "accent" if now else ""))
    return FormFold("timeline", tokens, boxes)


def _stage(form: str, named: list[Item], texts: list[Item]) -> FormFold | None:
    shapes: dict[int, Item] = {}
    bodies: dict[int, Item] = {}
    narrow = None
    for it in texts:
        m = _TEXT[form].fullmatch(_name(it))
        if not m:
            continue
        n = int(m.group(1))
        if m.group(3):
            bodies[n] = it
        else:
            shapes[n] = it
            narrow = m.group(2) or narrow
    if len(shapes) < 2:
        return None
    default = "down" if form == "funnel" else "up"
    tokens = [form] + ([f"dir={narrow}"] if narrow and narrow != default else [])
    boxes = []
    for n in sorted(shapes):
        it = shapes[n]
        head = [p for p in it.paras if p.plain.strip()]
        rest = [p for p in (bodies[n].paras if n in bodies else []) if p.plain.strip()]
        boxes.append(_box(it, head[:1], rest))
    return FormFold(form, tokens, boxes)


def _icon_in(data: SlideData | None, it: Item) -> str | None:
    """The ``icon <name>`` shape whose centre lies inside ``it`` (a glyph a form drew in a node), or None."""
    for ic in data.items if data is not None else ():
        if (
            ic.kind == "shape"
            and ic.name.lower().startswith("icon ")
            and it.x <= ic.cx <= it.x + it.w
            and it.y <= ic.cy <= it.y + it.h
        ):
            return ic.name.strip()[5:].strip() or None
    return None


def _cycle(form: str, named: list[Item], texts: list[Item], data: SlideData | None = None) -> FormFold | None:
    nodes: dict[int, Item] = {}
    bodies: dict[int, Item] = {}
    for it in named:  # (a node that holds an icon has no text: its ellipse is not a text shape)
        m = _TEXT[form].fullmatch(_name(it))
        if m:
            (bodies if m.group(2) else nodes)[int(m.group(1))] = it
    if len(nodes) < 3:
        return None
    ccw = any(_name(it).endswith("arrow ccw") for it in named)
    boxes = []
    for n in sorted(nodes):
        icon = _icon_in(data, nodes[n])
        head = [p for p in nodes[n].paras if p.plain.strip()]
        rest = [p for p in (bodies[n].paras if n in bodies else []) if p.plain.strip()]
        if icon and not head and rest:  # the heading moved out of the node: it leads the text beside it
            head, rest = rest[:1], rest[1:]
        blk = _box(nodes[n], head[:1], rest)
        blk.icon = icon
        boxes.append(blk)
    tokens = ["cycle"] + (["dir=ccw"] if ccw else [])
    center = next((t for t in texts if _name(t) == "Cycle center"), None)
    if center is None:
        center = next((t for t in named if _name(t) == "Cycle center" and t.text), None)
    if center is not None and center.text:
        tokens.append(f"center={_quote(center.text.replace(chr(10), ' ').strip())}")
    return FormFold("cycle", tokens, boxes)


def _stairs(form: str, named: list[Item], texts: list[Item]) -> FormFold | None:
    cards = sorted(
        ((int(m.group(1)), it) for it in texts if (m := _TEXT[form].fullmatch(_name(it)))), key=lambda t: t[0]
    )
    if len(cards) < 2:
        return None
    boxes = []
    for _n, it in cards:
        paras = [p for p in it.paras if p.plain.strip()]
        boxes.append(_box(it, paras[:1], paras[1:]))
    down = cards[0][1].h > cards[-1][1].h  # the first card is the tallest: the staircase falls
    return FormFold("stairs", ["stairs"] + (["dir=down"] if down else []), boxes)


def _icon_beside(data: SlideData | None, it: Item) -> str | None:
    """The ``icon <name>`` shape on the row of ``it``: its centre inside the item's height, beside it."""
    best: tuple[int, str] | None = None
    for ic in data.items if data is not None else ():
        if ic.kind == "shape" and ic.name.lower().startswith("icon ") and it.y <= ic.cy <= it.y + it.h:
            dist = min(abs(ic.cx - it.x), abs(ic.cx - (it.x + it.w)))
            if best is None or dist < best[0]:
                best = (dist, ic.name.strip()[5:].strip())
    return best[1] if best and best[1] else None


def _nested(
    form: str, named: list[Item], texts: list[Item], data: SlideData | None = None
) -> FormFold | None:
    rings: dict[int, Item] = {}
    heads: dict[int, Item] = {}
    lists: dict[int, Item] = {}
    for it in named:
        m = re.fullmatch(r"Nested (\d+)( text| list| icon)?", _name(it))
        if not m or m.group(2) == " icon":
            continue
        {None: rings, " text": heads, " list": lists}[m.group(2)][int(m.group(1))] = it
    if len(rings) < 3:
        return None
    boxes = []
    for n in sorted(rings):
        head = [p for p in (heads[n].paras if n in heads else []) if p.plain.strip()][:1]
        rest = [p for p in (lists[n].paras if n in lists else []) if p.plain.strip()]
        if head and rest and rest[0].plain.strip() == head[0].plain.strip():
            rest = rest[1:]  # the list item starts with the ring heading (`nested.list.title`)
        elif not head and rest:
            head, rest = rest[:1], rest[1:]
        blk = _box(lists.get(n, rings[n]), head, rest)  # (rows do not overlap: the rings do)
        if n in lists:
            blk.icon = _icon_beside(data, lists[n])
        boxes.append(blk)
    first = lists.get(min(lists)) if lists else None
    right = first is not None and rings[min(rings)].cx > first.cx
    return FormFold("nested", ["nested"] + (["side=right"] if right else []), boxes)


def _flowdisc(
    form: str, named: list[Item], texts: list[Item], data: SlideData | None = None
) -> FormFold | None:
    discs: dict[int, Item] = {}
    bodies: dict[int, Item] = {}
    for it in named:
        m = re.fullmatch(r"Flow (\d+) (disc|text)", _name(it))
        if m:
            (discs if m.group(2) == "disc" else bodies)[int(m.group(1))] = it
    if len(discs) < 2:
        return None
    ys = sorted(d.cy for d in discs.values())
    row = ys[len(ys) // 2]  # the row's height: the median disc
    boxes = []
    for n in sorted(discs):
        d = discs[n]
        paras = [p for p in (bodies[n].paras if n in bodies else []) if p.plain.strip()]
        blk = _box(bodies.get(n, d), paras[:1], paras[1:], "above" if d.cy < row - 0.5 * d.h else "")
        blk.icon = _icon_in(data, d)
        boxes.append(blk)
    return FormFold("flowdisc", ["flow", "disc"], boxes)


def _agenda(form: str, named: list[Item], texts: list[Item]) -> FormFold | None:
    rows = sorted(
        ((int(m.group(1)), bool(m.group(2)), it) for it in texts if (m := _TEXT[form].fullmatch(_name(it)))),
        key=lambda t: t[0],
    )
    if len(rows) < 2:
        return None
    paras: list[ParaT] = []
    now: list[int] = []
    for _n, cur, it in rows:
        ps = [p for p in it.paras if p.plain.strip()]
        if not ps:
            continue
        if cur:
            now.append(len(paras))
        paras.append(replace(ps[0], marker="number", level=0, runs=[_plain(r) for r in ps[0].runs]))
        paras += [replace(p, level=max(p.level, 1)) for p in ps[1:]]
    first = rows[0][2]
    blk = Block("text", first.x, first.y, first.w, first.h, paras=paras, marks=now)
    return FormFold("agenda", ["agenda"], [blk])


def _statement(form: str, named: list[Item], texts: list[Item]) -> FormFold | None:
    big = next((it for it in texts if _name(it) == "Statement"), None)
    if big is None:
        return None
    cap = next((it for it in texts if _name(it) == "Statement caption"), None)
    paras = [replace(p, runs=[_plain(r) for r in p.runs]) for p in big.paras if p.plain.strip()]
    if cap is not None:
        paras += [p for p in cap.paras if p.plain.strip()]
    align = next((p.align for p in big.paras if p.align), None)
    tokens = ["statement"] + ({"l": ["align=left"], "r": ["align=right"]}.get(align or "", []))
    return FormFold("statement", tokens, [Block("text", big.x, big.y, big.w, big.h, paras=paras)])


def _vs(form: str, named: list[Item], texts: list[Item]) -> FormFold | None:
    verdict = next((it for it in texts if _name(it) == "VS verdict"), None)
    block = None
    if verdict is not None:
        ps = [p for p in verdict.paras if p.plain.strip()]
        if ps:
            first = ps[0]
            lead, tail = _split_bold(first.runs)
            head = [ParaT(runs=lead, size=first.size)]
            rest = ([ParaT(runs=tail, size=first.size)] if tail else []) + ps[1:]
            block = _box(verdict, head, rest)
    return FormFold("vs", ["vs"], keep=True, verdict=block)


def _split_bold(runs: list[RunT]) -> tuple[list[RunT], list[RunT]]:
    """The leading bold runs (the verdict heading) and what follows the double space after them."""
    i = 0
    while i < len(runs) and runs[i].bold:
        i += 1
    lead, tail = runs[:i], runs[i:]
    if tail and tail[0].text.strip() == "":
        tail = tail[1:]
    elif tail:
        tail = [replace(tail[0], text=tail[0].text.lstrip()), *tail[1:]]
    return (lead or runs[:1]), (tail if lead else runs[1:])


def _matrix(form: str, named: list[Item], texts: list[Item]) -> FormFold | None:
    tokens = ["matrix"]
    for axis in ("x", "y"):
        it = next((t for t in texts if _name(t) == f"Matrix {axis} label"), None)
        if it is not None and it.text:
            tokens.append(f"{axis}={_quote(it.text.replace(chr(10), ' ').strip())}")
    return FormFold("matrix", tokens, keep=True)


__all__ = ["FormFold", "detect", "extract"]
