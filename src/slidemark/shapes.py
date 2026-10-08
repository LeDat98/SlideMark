"""Preset geometries an author can name: ``{shape=hexagon}`` on a box, card, text block, code block, image.

``SHAPES`` maps the author's name to ``(MSO_SHAPE member, adjustment)``: the member name is resolved by the
renderer (``getattr(MSO_SHAPE, member)``) so this module needs no python-pptx; ``adjustment`` is the first
adjust handle (``0.5`` on a rounded rectangle = a pill) or ``None`` for the preset's own default.
``tests/test_shapes.py`` checks that every member exists and that every name draws its ``a:prstGeom``.
"""

from __future__ import annotations

import difflib

SHAPES: dict[str, tuple[str, float | None]] = {
    # rectangles
    "rect": ("RECTANGLE", None),
    "rounded": ("ROUNDED_RECTANGLE", None),
    "pill": ("ROUNDED_RECTANGLE", 0.5),
    "snip": ("SNIP_1_RECTANGLE", None),
    "snip2": ("SNIP_2_SAME_RECTANGLE", None),
    "round1": ("ROUND_1_RECTANGLE", None),
    "round2": ("ROUND_2_SAME_RECTANGLE", None),
    "round-diag": ("ROUND_2_DIAG_RECTANGLE", None),
    "snip-round": ("SNIP_ROUND_RECTANGLE", None),
    "folded": ("FOLDED_CORNER", None),
    "plaque": ("PLAQUE", None),
    "bevel": ("BEVEL", None),
    "frame": ("FRAME", None),
    # round and polygons
    "ellipse": ("OVAL", None),
    "circle": ("OVAL", None),
    "diamond": ("DIAMOND", None),
    "triangle": ("ISOSCELES_TRIANGLE", None),
    "right-triangle": ("RIGHT_TRIANGLE", None),
    "parallelogram": ("PARALLELOGRAM", None),
    "trapezoid": ("TRAPEZOID", None),
    "pentagon": ("PENTAGON", None),  # the arrow pentagon (flat tail, pointed head), like render.chevron_shape
    "regular-pentagon": ("REGULAR_PENTAGON", None),
    "hexagon": ("HEXAGON", None),
    "heptagon": ("HEPTAGON", None),
    "octagon": ("OCTAGON", None),
    "decagon": ("DECAGON", None),
    "dodecagon": ("DODECAGON", None),
    "donut": ("DONUT", None),
    # arrows
    "chevron": ("CHEVRON", None),
    "arrow-right": ("RIGHT_ARROW", None),
    "arrow-left": ("LEFT_ARROW", None),
    "arrow-up": ("UP_ARROW", None),
    "arrow-down": ("DOWN_ARROW", None),
    "arrow-both": ("LEFT_RIGHT_ARROW", None),
    "arrow-notched": ("NOTCHED_RIGHT_ARROW", None),
    # stars, symbols
    "star": ("STAR_5_POINT", None),
    "star4": ("STAR_4_POINT", None),
    "star6": ("STAR_6_POINT", None),
    "star8": ("STAR_8_POINT", None),
    "burst": ("EXPLOSION1", None),
    "heart": ("HEART", None),
    "lightning": ("LIGHTNING_BOLT", None),
    "sun": ("SUN", None),
    "moon": ("MOON", None),
    "cloud": ("CLOUD", None),
    "plus": ("MATH_PLUS", None),
    "cross": ("CROSS", None),
    "gear": ("GEAR_6", None),
    # solids, banners, callouts
    "cylinder": ("CAN", None),
    "cube": ("CUBE", None),
    "funnel": ("FUNNEL", None),
    "wave": ("WAVE", None),
    "ribbon": ("UP_RIBBON", None),
    "scroll": ("HORIZONTAL_SCROLL", None),
    "tear": ("TEAR", None),
    "callout": ("RECTANGULAR_CALLOUT", None),
    "callout-round": ("ROUNDED_RECTANGULAR_CALLOUT", None),
    "callout-oval": ("OVAL_CALLOUT", None),
    "callout-cloud": ("CLOUD_CALLOUT", None),
}
# spellings an agent reaches for first; they resolve to a name above
ALIASES = {
    "roundrect": "rounded",
    "rounded-rect": "rounded",
    "rounded-rectangle": "rounded",
    "rectangle": "rect",
    "square": "rect",
    "oval": "ellipse",
    "capsule": "pill",
    "stadium": "pill",
    "arrow": "arrow-right",
    "pentagon-arrow": "pentagon",
    "homeplate": "pentagon",
    "star5": "star",
    "can": "cylinder",
    "bolt": "lightning",
    "note": "folded",
    "banner": "ribbon",
}


def resolve(name: str) -> str | None:
    """The canonical table name of ``name`` (case and ``_`` / space insensitive), or ``None``."""
    key = name.strip().lower().replace("_", "-").replace(" ", "-")
    key = ALIASES.get(key, key)
    return key if key in SHAPES else None


def suggest(name: str) -> str:
    """One-line hint for an unknown shape name: the nearest names, else the common ones."""
    key = name.strip().lower().replace("_", "-")
    near = difflib.get_close_matches(key, [*SHAPES, *ALIASES], n=3, cutoff=0.5)
    if near:
        best = ALIASES.get(near[0], near[0])
        more = [ALIASES.get(n, n) for n in near[1:] if ALIASES.get(n, n) != best]
        return f"did you mean '{best}'?" + (f" (also {', '.join(more)})" if more else "")
    return "use rounded, pill, ellipse, diamond, hexagon, parallelogram, chevron, pentagon, star, cloud ..."


def member(name: str):
    """The python-pptx ``MSO_SHAPE`` member of table name ``name`` (``None`` for an unknown name)."""
    spec = SHAPES.get(name or "")
    if spec is None:
        return None
    from pptx.enum.shapes import MSO_SHAPE

    return getattr(MSO_SHAPE, spec[0])


def prst(name: str) -> str | None:
    """The DrawingML ``prstGeom`` value of table name ``name`` (``pill`` -> ``roundRect``)."""
    m = member(name)
    if m is None:
        return None
    from pptx.shapes.autoshape import AutoShapeType

    return AutoShapeType(m).prst


def name_of_prst(value: str) -> str | None:
    """The table name for a ``prstGeom`` value (the importer's way back); ``None`` when no name draws it."""
    for name in SHAPES:
        if name in ("pill", "circle") or prst(name) != value:
            continue
        return name
    return None


__all__ = ["ALIASES", "SHAPES", "member", "name_of_prst", "prst", "resolve", "suggest"]
