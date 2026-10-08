"""Length parsing. All layout math happens in EMU (914400 per inch, 12700 per pt)."""

from __future__ import annotations

import re
from functools import lru_cache

EMU_PER_INCH = 914400
EMU_PER_PT = 12700
EMU_PER_CM = 360000
EMU_PER_PX = 9525  # 96 dpi

SLIDE_SIZES = {
    "16:9": (12192000, 6858000),  # 13.333in x 7.5in (PowerPoint default)
    "4:3": (9144000, 6858000),
    "A4": (9906000, 6858000),  # PowerPoint "A4 paper" landscape: 27.517cm x 19.05cm
    "16:10": (10972800, 6858000),
}

_LEN = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*(%|in|pt|cm|mm|px|emu)?\s*$")


def to_emu(value: str | float | int, ref: int = 0) -> int:
    """Convert a length to EMU. ``ref`` is the parent size used for percentages. Bare numbers are pt."""
    if isinstance(value, (int, float)):
        return round(value * EMU_PER_PT)
    return _str_emu(value, ref)


@lru_cache(maxsize=4096)
def _str_emu(value: str, ref: int) -> int:
    m = _LEN.match(value)
    if not m:
        raise ValueError(f"invalid length {value!r}; use e.g. 50%, 2in, 36pt, 3cm, 120px")
    num, unit = float(m.group(1)), m.group(2) or "pt"
    factor = {
        "%": ref / 100,
        "in": EMU_PER_INCH,
        "pt": EMU_PER_PT,
        "cm": EMU_PER_CM,
        "mm": EMU_PER_CM / 10,
        "px": EMU_PER_PX,
        "emu": 1,
    }[unit]
    return round(num * factor)


def slide_size(size: str) -> tuple[int, int]:
    """Resolve a deck size ("16:9", "A4", "10inx7.5in") to (width, height) EMU."""
    if size in SLIDE_SIZES:
        return SLIDE_SIZES[size]
    if "x" in size:
        w, h = size.split("x", 1)
        return to_emu(w), to_emu(h)
    raise ValueError(f"unknown slide size {size!r}; use one of {', '.join(SLIDE_SIZES)} or e.g. 10inx7.5in")
