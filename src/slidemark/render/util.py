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
    "transparent": "FFFFFF",  # fully transparent: parse_color reports alpha 0
}


_HEX = re.compile(r"#?([0-9a-f]{3,4}|[0-9a-f]{6}|[0-9a-f]{8})")
_FUNC = re.compile(r"rgba?\(\s*([\d.]+%?)[\s,]+([\d.]+%?)[\s,]+([\d.]+%?)(?:[\s,/]+([\d.]+%?))?\s*\)")
_GRADIENT = re.compile(r"^\s*(?:repeating-)?(?:linear|radial)-gradient\(", re.I)
_DIRECTION = re.compile(
    r"^(?:-?[\d.]+(?:deg|rad|turn|grad)|to\s.*|(?:circle|ellipse|closest|farthest)\b.*|at\s.*)$", re.I
)


def split_top(text: str) -> list[str]:
    """Split on commas that are not inside parentheses (``rgba(0, 0, 0, .5)`` stays whole)."""
    out, depth, cur = [], 0, []
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            out.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    out.append("".join(cur).strip())
    return [p for p in out if p]


def gradient_args(css: str) -> tuple[str, list[str]]:
    """``('linear' | 'radial', top-level arguments)`` of a CSS gradient string (arguments may be empty)."""
    m = _GRADIENT.match(css)
    if not m:
        return "", []
    kind = "radial" if "radial" in m.group(0).lower() else "linear"
    body = css.strip()[m.end() :]
    if body.endswith(")"):
        body = body[:-1]
    return kind, split_top(body)


def is_direction(part: str) -> bool:
    return bool(_DIRECTION.match(part.strip()))


def is_gradient(value: str | None) -> bool:
    return bool(value) and bool(_GRADIENT.match(value))  # type: ignore[arg-type]


def _channel(v: str) -> int:
    n = float(v[:-1]) * 2.55 if v.endswith("%") else float(v)
    return max(0, min(255, round(n)))


def _alpha(v: str) -> float:
    n = float(v[:-1]) / 100 if v.endswith("%") else float(v)
    return max(0.0, min(1.0, n))


def try_color(theme: Theme, value: str | None, names: bool = True) -> tuple[str, float | None] | None:
    """Like ``parse_color`` but None when ``value`` does not name a color. ``names`` = look up theme names."""
    if not value:
        return None
    candidate = (theme.color(value) if names else value) or ""
    c = candidate.strip().lower()
    if _GRADIENT.match(c):
        stops = [p for p in gradient_args(candidate)[1] if not is_direction(p)]
        # the first stop stands in for the whole gradient
        return try_color(theme, re.sub(r"\s+[-\d.]+(?:%|px|pt)$", "", stops[0])) if stops else None
    if c in _NAMED:
        return _NAMED[c], (0.0 if c == "transparent" else None)
    m = _HEX.fullmatch(c)
    if m:
        h = m.group(1)
        if len(h) in (3, 4):
            h = "".join(ch * 2 for ch in h)
        return h[:6].upper(), (int(h[6:8], 16) / 255 if len(h) == 8 else None)
    m = _FUNC.fullmatch(c)
    if m:
        try:
            return "".join(f"{_channel(m.group(i)):02X}" for i in (1, 2, 3)), (
                _alpha(m.group(4)) if m.group(4) else None
            )
        except ValueError:
            return None
    return None


def parse_color(theme: Theme, value: str | None, fallback: str = "#000000") -> tuple[str, float | None]:
    """Resolve a theme color name / #RGB / #RGBA / #RRGGBB / #RRGGBBAA / rgb() / rgba() / CSS name to
    ``('RRGGBB', alpha)``; ``alpha`` is 0..1 or None when opaque. A gradient string yields its first stop.
    Never raises: unresolvable values use ``fallback`` and finally black."""
    return try_color(theme, value) or try_color(theme, fallback, names=False) or ("000000", None)


def hex6(theme: Theme, value: str | None, fallback: str = "#000000") -> str:
    """Resolve a theme color name / #RGB / #RRGGBB / #RRGGBBAA / CSS name to 'RRGGBB' (never raises).

    An alpha channel is dropped here; ``parse_color`` returns it.
    """
    return parse_color(theme, value, fallback)[0]


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
