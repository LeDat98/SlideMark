"""`@` grid specs and automatic block arrangement. Pure geometry, no IR knowledge beyond block hints."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

FLAGS = {"flow", "chevron"}


@dataclass
class Rect:
    x: int
    y: int
    w: int
    h: int

    def inset(self, d: int) -> Rect:
        d = min(d, self.w // 2, self.h // 2)
        return Rect(self.x + d, self.y + d, self.w - 2 * d, self.h - 2 * d)

    @property
    def right(self) -> int:
        return self.x + self.w

    @property
    def bottom(self) -> int:
        return self.y + self.h


@dataclass
class GridSpec:
    cols: list[float]
    rows: list[float]
    areas: dict[int, tuple[int, int, int, int]] | None = None  # block index -> (r0, c0, r1, c1) inclusive
    flags: set[str] = field(default_factory=set)
    errors: list[str] = field(default_factory=list)


_N = re.compile(r"^\d+$")
_CXR = re.compile(r"^(\d+)[x×](\d+)$")
_RATIO = re.compile(r"^\d+(?:\.\d+)?(?::\d+(?:\.\d+)?)+$")
_AREAS = re.compile(r"^[a-z.]+(?:/[a-z.]+)*$")


def _areas_ok(tok: str) -> bool:
    if "/" in tok:
        return True
    letters = [c for c in tok if c != "."]
    seen: list[str] = []
    for c in letters:
        if c not in seen:
            seen.append(c)
    return len(tok) >= 2 and seen == [chr(97 + i) for i in range(len(seen))]


def parse_spec(spec: str | None, n_blocks: int, classes: list[str] | None = None) -> GridSpec | None:
    """Parse a raw grid spec (plus flow/chevron from ``classes``). ``None`` means "arrange automatically".

    Returns a ``GridSpec`` whose ``flags`` hold flow/chevron even when the grid itself is automatic
    (then ``cols``/``rows`` are empty). Problems go to ``errors``.
    """
    flags = {c for c in (classes or []) if c in FLAGS}
    tokens = (spec or "").split()
    main: str | None = None
    errors: list[str] = []
    for tok in tokens:
        low = tok.lower()
        if low in FLAGS:
            flags.add(low)
        elif main is None and (
            _N.match(low) or _CXR.match(low) or _RATIO.match(low) or (_AREAS.match(low) and _areas_ok(low))
        ):
            main = low
        elif "=" not in tok and not tok.isalpha():
            errors.append(f"unknown grid token {tok!r}")
    gs = GridSpec(cols=[], rows=[], flags=flags, errors=errors)
    if main is None:
        return gs if (flags or errors) else None
    try:
        if _N.match(main):
            c = max(int(main), 1)
            gs.cols, gs.rows = [1.0] * c, [1.0] * max(math.ceil(n_blocks / c), 1)
        elif m := _CXR.match(main):
            c, r = max(int(m.group(1)), 1), max(int(m.group(2)), 1)
            if c * r < n_blocks:
                errors.append(f"grid {main} has {c * r} cells for {n_blocks} blocks; added rows")
                r = math.ceil(n_blocks / c)
            gs.cols, gs.rows = [1.0] * c, [1.0] * r
        elif _RATIO.match(main):
            gs.cols = [float(p) for p in main.split(":")]
            gs.rows = [1.0] * max(math.ceil(n_blocks / len(gs.cols)), 1)
        else:
            rows = main.split("/")
            width = max(len(r) for r in rows)
            if any(len(r) != width for r in rows):
                raise ValueError(f"rows of {main!r} differ in length")
            areas: dict[int, list[int]] = {}
            for ri, row in enumerate(rows):
                for ci, ch in enumerate(row):
                    if ch == ".":
                        continue
                    idx = ord(ch) - 97
                    a = areas.setdefault(idx, [ri, ci, ri, ci])
                    a[0], a[1] = min(a[0], ri), min(a[1], ci)
                    a[2], a[3] = max(a[2], ri), max(a[3], ci)
            if len(areas) < n_blocks:
                raise ValueError(f"areas {main!r} define {len(areas)} blocks but the slide has {n_blocks}")
            gs.cols, gs.rows = [1.0] * width, [1.0] * len(rows)
            gs.areas = {k: (a[0], a[1], a[2], a[3]) for k, a in areas.items()}
    except ValueError as e:
        errors.append(str(e))
        gs.cols, gs.rows, gs.areas = [], [], None
    return gs


def auto_spec(n: int, *, text_visual: bool = False, short: bool = False) -> GridSpec:
    """Default arrangement by block count (docs/SYNTAX.md table)."""
    if n <= 1:
        return GridSpec([1.0], [1.0])
    if text_visual and n == 2:
        return GridSpec([2.0, 3.0], [1.0])
    if n == 4 and short:
        cols = 4
    elif n == 4:
        cols = 2
    elif n <= 3:
        cols = n
    elif n <= 6:
        cols = 3
    elif n <= 8:
        cols = 4
    else:
        cols = math.ceil(math.sqrt(n))
    return GridSpec([1.0] * cols, [1.0] * math.ceil(n / cols))


def cell_rects(spec: GridSpec, n: int, area: Rect, gap: int) -> list[Rect]:
    """Rect for each of ``n`` blocks in source order (areas map letters, otherwise row-major)."""
    nc, nr = len(spec.cols), len(spec.rows)
    avail_w = max(area.w - gap * (nc - 1), nc)
    avail_h = max(area.h - gap * (nr - 1), nr)
    xs, ys = [], []
    x = area.x
    for wgt in spec.cols:
        w = round(avail_w * wgt / sum(spec.cols))
        xs.append((x, w))
        x += w + gap
    y = area.y
    for wgt in spec.rows:
        h = round(avail_h * wgt / sum(spec.rows))
        ys.append((y, h))
        y += h + gap
    out: list[Rect] = []
    for i in range(n):
        if spec.areas is not None:
            r0, c0, r1, c1 = spec.areas.get(i, (0, 0, 0, 0))
        else:
            r0 = r1 = i // nc
            c0 = c1 = i % nc
            r0 = r1 = min(r0, nr - 1)
        x0, y0 = xs[c0][0], ys[r0][0]
        out.append(Rect(x0, y0, xs[c1][0] + xs[c1][1] - x0, ys[r1][0] + ys[r1][1] - y0))
    return out
