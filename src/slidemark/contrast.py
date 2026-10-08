"""WCAG contrast helpers. Pure functions, stdlib only, never raise on bad input."""

from __future__ import annotations

import colorsys
import re

_HEX = re.compile(r"^#?([0-9a-fA-F]{6}|[0-9a-fA-F]{3})$")


def _rgb(color: str) -> tuple[int, int, int] | None:
    m = _HEX.match(color.strip()) if isinstance(color, str) else None
    if not m:
        return None
    h = m.group(1)
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _hex(r: float, g: float, b: float) -> str:
    return "#{:02X}{:02X}{:02X}".format(*(max(0, min(255, round(v * 255))) for v in (r, g, b)))


def _lum(rgb: tuple[int, int, int]) -> float:
    def ch(v: int) -> float:
        c = v / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def ratio(fg: str, bg: str) -> float:
    """WCAG contrast ratio (1..21) of two ``#RRGGBB`` colors; 1.0 when either cannot be read."""
    a, b = _rgb(fg), _rgb(bg)
    if a is None or b is None:
        return 1.0
    hi, lo = sorted((_lum(a), _lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _worst(color: str, backs: list[str]) -> float:
    return min(ratio(color, b) for b in backs)


def nearest_passing(color: str, backs: list[str], need: float = 4.5) -> str:
    """The shade of ``color`` closest to it that reaches ``need`` on every back (hue/saturation kept).

    Only lightness moves: darker on light backs, lighter on dark ones. If no lightness passes the
    result is ``#000000`` or ``#FFFFFF``, whichever scores better. A passing color is returned
    unchanged (upper-case). Bad input returns ``color`` unchanged.
    """
    rgb = _rgb(color)
    valid = [b for b in (backs or []) if _rgb(b) is not None]
    if rgb is None or not valid:
        return color
    start = _hex(*(v / 255 for v in rgb))
    if _worst(start, valid) >= need:
        return start
    h, light, s = colorsys.rgb_to_hls(*(v / 255 for v in rgb))
    mean_lum = sum(_lum(_rgb(b)) for b in valid) / len(valid)  # type: ignore[arg-type]
    direction = -1 if mean_lum > 0.18 else 1  # darker on light backs, lighter on dark ones
    best: str | None = None
    steps = 1000
    for i in range(1, steps + 1):
        lt = light + direction * i / steps
        if not 0.0 <= lt <= 1.0:
            break
        cand = _hex(*colorsys.hls_to_rgb(h, lt, s))
        if _worst(cand, valid) >= need:
            best = cand
            break
    if best is not None:
        return best
    black, white = "#000000", "#FFFFFF"
    return black if _worst(black, valid) >= _worst(white, valid) else white


def best_ink(fill: str, candidates: list[str], need: float = 4.5) -> str:
    """First candidate reaching ``need`` on ``fill``, else the one with the highest ratio."""
    if not candidates:
        return "#000000" if _rgb(fill) is None or _lum(_rgb(fill)) > 0.18 else "#FFFFFF"  # type: ignore[arg-type]
    for c in candidates:
        if ratio(c, fill) >= need:
            return c
    return max(candidates, key=lambda c: ratio(c, fill))


def mix(a: str, b: str, t: float) -> str:
    """``a`` moved ``t`` (0..1) of the way toward ``b``, ``#RRGGBB``; ``a`` unchanged on bad input."""
    ra, rb = _rgb(a), _rgb(b)
    if ra is None or rb is None:
        return a
    return _hex(*((x + (y - x) * t) / 255 for x, y in zip(ra, rb, strict=True)))
