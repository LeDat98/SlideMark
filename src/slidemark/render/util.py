"""Small helpers shared by the renderer modules."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from pptx.dml.color import RGBColor

from ..ir import Deck, Diagnostic
from ..theme import Theme
from ..units import to_emu

_NAMED = {
    "white": "FFFFFF",
    "black": "000000",
    "red": "FF0000",
    "green": "008000",
    "blue": "0000FF",
    "yellow": "FFFF00",
    "gray": "808080",
    "grey": "808080",
    "orange": "FFA500",
    "transparent": "FFFFFF",
}


def hex6(theme: Theme, value: str | None, fallback: str = "#000000") -> str:
    """Resolve a theme color name / #RGB / #RRGGBB / CSS name to 'RRGGBB' (never raises)."""
    for candidate in (theme.color(value) if value else None, fallback):
        if not candidate:
            continue
        c = candidate.strip().lower()
        if c in _NAMED:
            return _NAMED[c]
        m = re.fullmatch(r"#?([0-9a-f]{6})", c)
        if m:
            return m.group(1).upper()
        m = re.fullmatch(r"#?([0-9a-f]{3})", c)
        if m:
            return "".join(ch * 2 for ch in m.group(1)).upper()
    return "000000"


def rgb(theme: Theme, value: str | None, fallback: str = "#000000") -> RGBColor:
    return RGBColor.from_string(hex6(theme, value, fallback))


def emu(value, ref: int = 0, default: int = 0) -> int:
    try:
        return to_emu(value, ref)
    except (ValueError, TypeError):
        return default


@dataclass
class RenderCtx:
    deck: Deck
    theme: Theme
    slide_index: int = 0
    base_dir: str = "."
    # (run element, rPr element, link target, source slide index) for the second pass
    links: list[tuple[object, object, str, int]] = field(default_factory=list)
    slides: list = field(default_factory=list)
    template: bool = False  # the base presentation comes from a user template

    def diag(self, rule: str, message: str, hint: str, level: str = "warning", line: int | None = None):
        self.deck.diagnostics.append(
            Diagnostic(  # type: ignore[arg-type]
                level=level, message=message, slide=self.slide_index + 1, rule=rule, hint=hint, line=line
            )
        )
