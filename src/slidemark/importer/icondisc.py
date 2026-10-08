"""Icon discs on import: a filled disc with a glyph centred in it is ONE icon, ``icon=name`` + a disc colour.

The renderer draws ``icon=`` with ``icon.disc`` as a native ``Icon disc`` shape under an ``icon <name>`` glyph
(``render/icons.py``). This module folds that pair (the glyph centred in a filled, text-less, square-ish
ellipse / rounded / plain square, between a quarter and four fifths of its size) back into the glyph:
``Item.disc`` / ``Item.disc_shape`` carry the disc and the disc item becomes decor, so the box stays
``## Title {icon=name}`` (the deck's ``icon.disc=`` token or a per-heading ``disc=``) and no second shape is
imported. Decks whose glyph has no ``icon <name>`` (a picture, a foreign path) are left as they are: their
name is unknowable.

``deck_disc`` states the deck-wide disc (``icon.disc=``) of a foreign deck; ``attr`` writes what one icon
needs on top of it (``disc=accent`` for another colour, ``disc=none`` for a bare one). Never raises.
"""

from __future__ import annotations

import re
from collections import Counter

from .read import Item, SlideData

_HEX = re.compile(r"^[0-9A-Fa-f]{6}$")
SHAPES = {"ellipse": "circle", "roundRect": "rounded", "rect": "square"}
_SQUARE = 0.08  # |w - h| / max(w, h) of a disc
_CENTRE = 0.08  # glyph centre off the disc centre, in disc sizes
_SIZE = (0.25, 0.8)  # glyph side / disc side


def is_glyph(it: Item) -> bool:
    """A SlideMark icon glyph: a shape named ``icon <name>`` (not the disc itself)."""
    nm = it.name.lower().strip()
    return it.kind == "shape" and nm.startswith("icon ") and nm != "icon disc"


def is_disc_shape(it: Item) -> bool:
    return (
        it.kind == "shape"
        and not it.paras
        and not it.ph
        and bool(it.fill)
        and bool(_HEX.match(it.fill or ""))
        and it.prst in SHAPES
        and it.w > 0
        and it.h > 0
        and abs(it.w - it.h) <= _SQUARE * max(it.w, it.h)
    )


def fold(data: SlideData) -> None:
    """Pair every glyph with the disc under it (see the module doc). Idempotent; never raises."""
    try:
        glyphs = [i for i in data.items if is_glyph(i)]
        discs = [
            i
            for i in data.items
            if is_disc_shape(i) and (i.name.lower().strip() == "icon disc" or i.prst == "ellipse")
        ]
        for d in discs:
            if d.name.lower().strip() == "icon disc":
                d.role = "decor"  # an orphan disc (its glyph missing) is still not content
        for g in glyphs:
            best = None
            for d in discs:
                size = max(g.w, g.h) / max(d.w, d.h)
                if not _SIZE[0] <= size <= _SIZE[1]:
                    continue
                off = max(abs(g.cx - d.cx), abs(g.cy - d.cy)) / max(d.w, d.h)
                if off <= _CENTRE and (best is None or d.w < best.w):
                    best = d
            if best is not None:
                g.disc = best.fill.upper() if best.fill else None
                g.disc_shape = SHAPES.get(best.prst or "")
                best.role = "decor"
    except Exception:  # noqa: BLE001 - a deck that does not fold stays as it was
        return


def deck_disc(datas: list[SlideData]) -> tuple[str | None, str | None]:
    """The disc colour and shape most icons of a foreign deck share (2+ icons, half of them) or ``None``."""
    seen: Counter[str | None] = Counter()
    shapes: Counter[str] = Counter()
    for sd in datas:
        for it in sd.items:
            if is_glyph(it):
                seen[it.disc] += 1
                if it.disc and it.disc_shape:
                    shapes[it.disc_shape] += 1
    total = sum(seen.values())
    colors = Counter({k: n for k, n in seen.items() if k})
    if not colors or total < 2:
        return None, None
    best, n = colors.most_common(1)[0]
    if n < 2 or n < 0.5 * total:
        return None, None
    return best, (shapes.most_common(1)[0][0] if shapes else None)


def color_token(hex6: str, colors: dict[str, str]) -> str:
    """The deck colour name of ``hex6`` (``accent``), else ``#RRGGBB``."""
    h = hex6.lstrip("#").upper()
    first = ("primary", "secondary", "accent", "muted", "success", "danger", "surface", "border")
    for name in [*first, *(k for k in colors if k not in first)]:
        if name in colors and colors[name].lstrip("#").upper() == h and re.fullmatch(r"[A-Za-z][\w-]*", name):
            return name
    return f"#{h}"


def attr(disc: str | None, default: str | None, colors: dict[str, str]) -> str:
    """What one icon says on top of the deck's ``icon.disc``: ``""`` when it agrees, else ``disc=...``."""
    if (disc or None) == (default or None):
        return ""
    if not disc:
        return "disc=none"
    if default and disc.upper() == default.upper():
        return ""
    return f"disc={color_token(disc, colors)}"
