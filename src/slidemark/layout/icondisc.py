"""Icon discs: an ``icon=`` glyph sitting centred on a filled disc (``icon.disc=secondary``).

Tokens (``theme.py``): ``icon.disc`` (colour, none = a bare glyph), ``icon.disc.size`` (diameter),
``icon.disc.shape`` (``circle`` / ``rounded`` / ``square``), ``icon.color`` (glyph ink); ratios in
``layout.icon_disc_*``. Per element: ``{icon=bolt disc=accent}`` (``disc=none`` takes the disc away).

The disc is part of the icon element: its ``Placed`` rectangle is the DISC (a square), the renderer draws a
native ``Icon disc`` shape on it and the glyph centred inside at ``layout.icon_disc_glyph`` of the diameter
(``render/icons.py``). The layout therefore reserves the disc's size, never the glyph's, and a pass that
moves the icon moves the disc with it. Never raises: an unusable value is a diagnostic and the theme's disc.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..ir import Shape
from ..theme import LayoutTokens, Theme
from ..units import to_emu

_OFF = ("none", "off", "no", "false", "null")
_ON = ("on", "yes", "true")


def _valid_color(theme: Theme, value: str) -> str | None:
    from ..parser.css import parse_color

    return parse_color(value, set(theme.colors))


def disc_color(
    theme: Theme, attrs: dict[str, Any] | None, diag: Callable[..., Any] | None = None
) -> str | None:
    """The disc fill of an element: its own ``disc=`` (``none`` = no disc), else ``icon.disc``."""
    raw = (attrs or {}).get("disc")
    if raw is not None:
        v = str(raw).strip()
        low = v.lower()
        if low in _OFF:
            return None
        if low in _ON:
            return theme.icon_disc or "primary"
        got = _valid_color(theme, v)
        if got is not None:
            return got
        if diag is not None:
            diag(
                "bad-attr",
                f"disc={v}: not a color",
                "use a theme color name (accent), #RRGGBB or disc=none",
            )
    return theme.icon_disc


def diameter(theme: Theme, lt: LayoutTokens, side: int, ratio: float) -> int:
    """Disc diameter (EMU): ``icon.disc.size`` when set, else ``ratio`` x the ``side`` of the bare glyph."""
    if theme.icon_disc_size is not None:
        try:
            return max(to_emu(theme.icon_disc_size), 1)
        except (ValueError, TypeError):
            pass
    return max(round(side * ratio), 1)


def ink(theme: Theme, disc: str | None, fallback: str) -> str:
    """Glyph ink: ``icon.color``, else (on a disc) a readable ink on the disc, else ``fallback``.

    A glyph is a graphic, not body text: it needs the large-text contrast (``render.contrast_large``)."""
    if theme.icon_color:
        return theme.icon_color
    if disc:
        return theme.ink_on(disc, theme.render.ink_light, theme.render.contrast_large)
    return fallback


def icon_shape(theme: Theme, lt: LayoutTokens, name: str, disc: str | None) -> Shape:
    """The ``icon`` element; with ``disc`` its attributes tell the renderer to draw the disc below."""
    attrs: dict[str, Any] = {"icon": name}
    if disc:
        attrs.update(
            disc=disc,
            disc_shape=theme.icon_disc_shape,
            disc_glyph=lt.icon_disc_glyph,
            disc_round=lt.icon_disc_round,
        )
    return Shape(shape="icon", attrs=attrs)
