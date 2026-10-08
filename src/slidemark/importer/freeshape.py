"""Text-less preset shapes of a foreign deck -> ``{x= y= w= h= shape= fill=}`` blocks on a ``@free`` slide.

A chevron between two cards, a hexagon badge, a rounded plate: a shape with a fill or outline and no text,
that no recogniser read and no SlideMark name explains, used to be dropped. It is now a shape block, and the
slide becomes ``@free`` (every block of it pinned, positions as lengths from the body's top-left corner, which
is ``margin`` and ``layout.top_gap`` away from the slide edge / the title). A SlideMark deck keeps its own
shapes: only a text-less ``Shape N`` (what a shape block builds as) is read back.
"""

from __future__ import annotations

import re

from .. import shapes
from .read import Item

IN = 914400
_GENERATED = re.compile(
    r"(Step|Row|Item|Card|Num|num|KPI|Timeline|Funnel|Cycle|Agenda|Split|Conclusion|Band|Rule|Stripe|Icon|"
    r"Pill|Arrow|Title|Lead|Footer|Slide|Background|Text|Heading|Code|Table|Chart|Image|Media)\b"
)
_OWN = re.compile(r"Shape \d+")
_PLAIN = ("rect", "roundRect")
BEHIND = 0.7  # a shape this much covered by another item is that item's plate, not a loose shape


def _inside(a: Item, b: Item) -> bool:
    """Most of ``a`` lies inside ``b``."""
    ix = max(0, min(a.x + a.w, b.x + b.w) - max(a.x, b.x))
    iy = max(0, min(a.y + a.h, b.y + b.h) - max(a.y, b.y))
    return a.area > 0 and ix * iy >= BEHIND * a.area


def free_shapes(pool: list[Item], foreign: bool) -> list[Item]:
    """The loose shapes of ``pool``: filled or outlined, no text, a preset, owned by nobody. Foreign decks:
    any preset but a rectangle and an arrow (arrows are read as ``flow``); a SlideMark deck: ``Shape N``."""
    out: list[Item] = []
    for it in pool:
        if it.kind != "shape" or it.role or it.rec or it.text:
            continue
        if not (it.fill or it.line_color) or not it.prst or it.w <= 0 or it.h <= 0:
            continue
        name = it.name or ""
        own = bool(_OWN.fullmatch(name))
        if not own and not (foreign and not _GENERATED.match(name)):
            continue
        if not own and (it.prst in _PLAIN or "rrow" in it.prst):
            continue
        if shapes.name_of_prst(it.prst) is None:
            continue
        if any(
            o is not it
            and o.uid != it.uid
            and (o.text or o.kind in ("table", "image", "chart"))
            and _inside(o, it)
            for o in pool
        ):
            continue  # a plate under text: a card (make_blocks reads it)
        out.append(it)
    return out


def length(v: float) -> str:
    """``1.25in`` of an EMU value (two decimals, no trailing zeros)."""
    s = f"{v / IN:.2f}".rstrip("0").rstrip(".")
    return f"{s or '0'}in"


def origin(margin_x: int, body_top: int, margin_y: int, lead_bottom: int | None) -> tuple[int, int]:
    """The top-left corner of the body the layout measures ``x=`` / ``y=`` from."""
    ox = margin_x or round(0.5 * IN)
    oy = body_top or ((margin_y or round(0.4 * IN)) + round(0.9 * IN) + round(0.25 * IN))
    if lead_bottom is not None:
        oy = max(oy, lead_bottom + round(0.25 * IN))
    return ox, oy


def pin(x: int, y: int, w: int, h: int, o: tuple[int, int]) -> str:
    """``x=1.2in y=2in w=3in h=1in`` of a box against the body origin ``o``."""
    return f"x={length(x - o[0])} y={length(y - o[1])} w={length(w)} h={length(h)}"


def shape_line(it: Item, o: tuple[int, int], names: dict[str, str]) -> str:
    """The attribute-only block of a loose shape."""
    toks = [pin(it.x, it.y, it.w, it.h, o)]
    name = shapes.name_of_prst(it.prst or "rect")
    if it.prst == "roundRect":
        if it.radius is not None and it.radius >= 0.49 * min(it.w, it.h) / 12700:
            toks.append("shape=pill")
        elif it.radius:
            toks.append(f"radius={it.radius:g}")
    elif name and name != "rect":
        toks.append(f"shape={name}")
    if it.fill and re.fullmatch(r"[0-9A-Fa-f]{6}", it.fill):
        toks.append("fill=" + names.get(it.fill.upper(), "#" + it.fill.upper()))
    if it.line_color:
        toks.append("line=" + names.get(it.line_color.upper(), "#" + it.line_color.upper()))
    if it.rot:
        toks.append(f"rotate={it.rot:g}")
    if it.shadow:
        toks.append(f'shadow="{it.shadow}"')
    return "{" + " ".join(toks) + "}"


_STANDALONE = re.compile(r"^\{([^{}]*)\}$")
_HEAD = re.compile(r"^(#{2,3}(?: .*?)?)(?: \{([^{}]*)\})?$")
_IMAGE = re.compile(r"^(!\[.*\]\([^)]*\))(?:\{([^{}]*)\})?$")


def pin_first(lines: list[str], pin_attrs: str) -> list[str]:
    """``lines`` (one block) with the position attributes put on it: inside its heading's or image's braces,
    inside its attribute line, or as a new ``{...}`` line before it."""
    if not lines:
        return lines
    first = lines[0]
    if (m := _STANDALONE.match(first)) is not None:
        inner = m.group(1).strip()
        return [("{" + pin_attrs + (" " + inner if inner else "") + "}"), *lines[1:]]
    if first.startswith("#") and (m := _HEAD.match(first)) is not None:
        inner = (m.group(2) or "").strip()
        return [f"{m.group(1)} {{{pin_attrs}{' ' + inner if inner else ''}}}", *lines[1:]]
    if first.startswith("![") and (m := _IMAGE.match(first)) is not None:
        inner = (m.group(2) or "").strip()
        return [f"{m.group(1)}{{{pin_attrs}{' ' + inner if inner else ''}}}", *lines[1:]]
    return ["{" + pin_attrs + "}", *lines]
