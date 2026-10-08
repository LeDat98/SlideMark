"""Wave 2026-10-08 lane B: tokens of the grown-up composition forms (``style:`` keys).

======================  ===========================================================================
token                   meaning
======================  ===========================================================================
``cycle.center``        text at the centre of the ``@cycle`` ring (``center="..."`` on the ``@`` line wins)
``cycle.center.size``   its size in pt (default: as large as the free disc holds)
``cycle.center.color``  its colour (default ``primary``)
``cycle.center.fill``   a disc behind it (default: none)
``cycle.head.color``    ink of a heading written beside a node that holds an icon (default ``fg``)
``cycle.icon.ratio``    icon edge / node diameter (default 0.45)
``cycle.icon.color``    icon colour (default: readable on the node fill)
``stairs.fill``         card fills ``a,b,c`` cycled (default: tints of ``primary``, light to dark)
``stairs.color``        card ink (default: readable on the fill)
``stairs.step``         height difference between neighbours (a length; default from the body)
``stairs.gap``          air between cards (a length; default the slide gap)
``stairs.low``          height of the lowest card as a share of the body (default 0.4)
``stairs.tint``         strength of the lightest default fill (default 0.3 of ``primary``)
``nested.fill``         ring fills ``a,b,c`` outer to inner (default: tints of ``secondary``)
``nested.color``        ring heading ink (default: readable on the fill)
``nested.size``         ring heading size in pt (default: as large as the ring band holds)
``nested.core``         diameter of the innermost ring / the outer one (default 0.4)
``nested.tint``         strength of the lightest default fill (default 0.25 of ``secondary``)
``nested.share``        share of the body width the rings' half takes (default 0.5)
``nested.line``         ring outline colour (default: none) and ``nested.line.w`` its width
``nested.list.title``   the list item starts with the ring heading (``on``, default) or not (``off``)
``flow.disc.size``      disc diameter (a length; default from the room)
``flow.disc.fill``      disc fills ``a,b`` cycled (default ``primary``)
``flow.disc.color``     icon / number ink (default: readable on the fill)
``flow.line``           colour of the lines joining the discs (default ``muted``), ``flow.line.w`` width
======================  ===========================================================================

Fields are theme fields (``Theme`` inherits them), so every token is also a preset key.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from pydantic import Field

from .forms3 import Forms3Tokens

Length = str | float | int


class Forms4Tokens(Forms3Tokens):
    """Theme fields of wave 2026-10-08 lane B (``None`` = derive: the layout decides)."""

    # @cycle (grown up): centre label, icon in the node
    cycle_center: str | None = None
    cycle_center_size: float | None = None
    cycle_center_color: str | None = None
    cycle_center_fill: str | None = None
    cycle_head_color: str | None = None
    cycle_icon_ratio: float = Field(0.45, ge=0.1, le=0.9)
    cycle_icon_color: str | None = None
    # @stairs
    stairs_fill: str | None = None
    stairs_color: str | None = None
    stairs_step: Length | None = None
    stairs_gap: Length | None = None
    stairs_low: float = Field(0.4, ge=0.1, le=0.9)
    stairs_pad_ratio: float = 0.7  # card padding = this x the text size (pt)
    stairs_tint: float = Field(0.3, ge=0.05, le=1.0)  # the lightest default fill: this share of `primary`
    # @nested
    nested_fill: str | None = None
    nested_color: str | None = None
    nested_size: float | None = None
    nested_core: float = Field(0.4, ge=0.1, le=0.9)
    nested_tint: float = Field(0.25, ge=0.05, le=1.0)  # the lightest default fill: this share of `secondary`
    nested_share: float = Field(0.5, ge=0.25, le=0.75)
    nested_line: str | None = None
    nested_line_w: Length = "1.5pt"
    nested_list_title: bool = True
    nested_icon_ratio: float = 2.2  # list icon edge = this x the list title size
    nested_text_ratio: float = 0.9  # list body size / title size
    # @flow disc
    flow_disc_size: Length | None = None
    flow_disc_fill: str | None = None
    flow_disc_color: str | None = None
    flow_line: str = "muted"
    flow_line_w: Length = "3pt"
    flow_disc_ratio: float = Field(0.5, ge=0.2, le=1.0)  # disc diameter = this x the row's height


_COLOR_LISTS = {"stairs_fill", "nested_fill", "flow_disc_fill"}
_COLORS = {
    "cycle_center_color",
    "cycle_center_fill",
    "cycle_head_color",
    "cycle_icon_color",
    "stairs_color",
    "nested_color",
    "nested_line",
    "flow_disc_color",
    "flow_line",
}
_LENGTHS = {"stairs_step", "stairs_gap", "nested_line_w", "flow_disc_size", "flow_line_w"}
_PTS = {"cycle_center_size", "nested_size"}
_NONE = ("none", "null", "off")


def normalize(path: str, raw: str, names: set[str] | None) -> list[tuple[str, Any]] | None:
    """Validate one of this module's tokens (``None`` = not one of them). Raises ``theme.TokenValueError``."""
    if path not in Forms4Tokens.model_fields or path in Forms3Tokens.model_fields:
        return None
    from .theme import TokenValueError, _color_value, _length_value, _pt_value, _unquote

    v = _unquote(raw)
    key = path.replace("_", ".")
    if path == "cycle_center":
        return [(path, None if v.lower() in _NONE else v)]
    if path == "nested_list_title":
        if v.lower() in ("on", "true", "yes", "1"):
            return [(path, True)]
        if v.lower() in ("off", "false", "no", "0", "none"):
            return [(path, False)]
        raise TokenValueError("nested.list.title is on or off", "write nested.list.title=off (or on)")
    if path in _COLOR_LISTS:
        if v.lower() in _NONE:
            return [(path, None)]
        items = [p.strip() for p in v.split(",") if p.strip()]
        if not items:
            raise TokenValueError(f"{key} needs a color", f"write {key}=primary,secondary")
        return [(path, ",".join(_color_value(p, names) for p in items))]
    if path in _COLORS:
        if v.lower() in _NONE and path != "flow_line":
            return [(path, None)]
        return [(path, _color_value(raw, names))]
    if path in _PTS:
        if v.lower() in _NONE:
            return [(path, None)]
        return [(path, _pt_value(raw))]
    if path in _LENGTHS:
        if v.lower() in _NONE and path not in ("nested_line_w", "flow_line_w"):
            return [(path, None)]
        return [(path, _length_value(raw))]
    return None


# --------------------------------------------------------------------------- build feedback


def _needs_flow_disc(facts: Any) -> bool:
    return any({"flow", "disc"} <= set(s.classes) for s in facts.deck.slides)


# (pattern over the lower-cased ``style:`` key, what the deck needs, hint): appended to honour.STYLE_NEEDS
STYLE_NEEDS: list[tuple[re.Pattern[str], Callable[[Any], bool], str]] = [
    (
        re.compile(r"^flow[.-]"),
        _needs_flow_disc,
        "no `@flow disc` slide in the deck: write `@flow disc` before 2-7 `##` boxes",
    ),
]

# fit-line name of a form
FIT_NAMES = {"stairs": "stairs", "nested": "nested rings", "flowdisc": "flow of discs"}
