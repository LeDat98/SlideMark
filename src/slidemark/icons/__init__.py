"""Built-in vector icons: simple solid glyphs on a 24x24 grid, authored for SlideMark (no third-party art).

Each icon is an SVG-style path string (absolute ``M L H V C Q A Z``). Sub-paths of one layer are filled with
the even-odd rule (so a nested sub-path is a hole). ``|`` separates *layers*: every layer becomes its own
``a:path`` in the custom geometry, so layers may overlap freely (a union, no holes where they cross).
``commands(name)`` returns the parsed layers with arcs already converted to cubic Béziers.
"""

from __future__ import annotations

import math
import re

GRID = 24

Point = tuple[float, float]
Command = tuple[str, list[Point]]  # ("M"|"L"|"C"|"Q"|"Z", points)


def _n(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s if s != "-0" else "0"


def _poly(*pts: Point) -> str:
    return "M" + "L".join(f"{_n(x)} {_n(y)}" for x, y in pts) + "Z"


def _rect(x: float, y: float, w: float, h: float) -> str:
    return f"M{_n(x)} {_n(y)}H{_n(x + w)}V{_n(y + h)}H{_n(x)}Z"


def _circ(cx: float, cy: float, r: float) -> str:
    return _ell(cx, cy, r, r)


def _ell(cx: float, cy: float, rx: float, ry: float) -> str:
    return (
        f"M{_n(cx - rx)} {_n(cy)}A{_n(rx)} {_n(ry)} 0 1 0 {_n(cx + rx)} {_n(cy)}"
        f"A{_n(rx)} {_n(ry)} 0 1 0 {_n(cx - rx)} {_n(cy)}Z"
    )


def _rrect(x: float, y: float, w: float, h: float, r: float) -> str:
    a = f"A{_n(r)} {_n(r)} 0 0 1 "
    return (
        f"M{_n(x + r)} {_n(y)}H{_n(x + w - r)}{a}{_n(x + w)} {_n(y + r)}V{_n(y + h - r)}"
        f"{a}{_n(x + w - r)} {_n(y + h)}H{_n(x + r)}{a}{_n(x)} {_n(y + h - r)}V{_n(y + r)}"
        f"{a}{_n(x + r)} {_n(y)}Z"
    )


def _star(cx: float, cy: float, ro: float, ri: float, n: int = 5) -> str:
    pts = []
    for k in range(2 * n):
        r = ro if k % 2 == 0 else ri
        a = -math.pi / 2 + k * math.pi / n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return _poly(*pts)


def _gear() -> str:
    pts: list[Point] = []
    ri, ro = 8.0, 10.8
    for k in range(8):
        for da, r in ((-14, ri), (-9, ro), (9, ro), (14, ri)):
            a = math.radians(k * 45 + da - 90)
            pts.append((12 + r * math.cos(a), 12 + r * math.sin(a)))
    return _poly(*pts) + _circ(12, 12, 3.4)


def _disk(y: float, h: float) -> str:
    """One tier of a database cylinder: ends at ``y``..``y+h``, bowed bottom and top edges."""
    return f"M4 {_n(y)}A8 3 0 0 0 20 {_n(y)}V{_n(y + h)}A8 3 0 0 1 4 {_n(y + h)}Z"


_ICONS: dict[str, str] = {
    "check": _poly((3, 12.5), (6, 9.5), (10, 13.5), (18, 5.5), (21, 8.5), (10, 19.5)),
    "x": _poly(
        (5, 7.5),
        (7.5, 5),
        (12, 9.5),
        (16.5, 5),
        (19, 7.5),
        (14.5, 12),
        (19, 16.5),
        (16.5, 19),
        (12, 14.5),
        (7.5, 19),
        (5, 16.5),
        (9.5, 12),
    ),
    "warning": _poly((12, 2.5), (22.5, 20.5), (1.5, 20.5))
    + _rrect(10.9, 8.5, 2.2, 6.3, 1)
    + _circ(12, 17.5, 1.3),
    "info": _circ(12, 12, 10) + _circ(12, 7.6, 1.4) + _rrect(10.8, 10.4, 2.4, 7.2, 1),
    "user": _circ(12, 7, 4.5) + "M3.5 21C3.5 15.8 7.4 13.5 12 13.5C16.6 13.5 20.5 15.8 20.5 21Z",
    "users": _circ(9, 8, 4)
    + "M1.5 20.5C1.5 16 4.8 13.5 9 13.5C13.2 13.5 16.5 16 16.5 20.5Z"
    + "|"
    + _circ(17.5, 7.5, 3.2)
    + "M15.2 12.8C20 12.4 22.8 14.8 22.8 19.8L17.8 19.8C17.8 17 16.8 14.4 15.2 12.8Z",
    "building": _rect(5, 2.5, 14, 19)
    + "".join(_rect(8 + 5 * cx, 5.5 + 3.8 * cy, 3, 2.2) for cx in range(2) for cy in range(3))
    + _rect(10.5, 17, 3, 4.5),
    "factory": "M2 21.5V10L8 13.5V10L14 13.5V3H18V10H22V21.5Z"
    + _rect(4.8, 16, 2.6, 2.6)
    + _rect(10.2, 16, 2.6, 2.6)
    + _rect(15.4, 16, 2.6, 2.6),
    "chart": _rect(3, 12, 4.5, 9) + _rect(9.75, 5, 4.5, 16) + _rect(16.5, 9, 4.5, 12),
    "money": _rrect(1.5, 5.5, 21, 13, 1.8) + _circ(12, 12, 3.3) + _circ(5.6, 12, 1.1) + _circ(18.4, 12, 1.1),
    "yen": _circ(12, 12, 10)
    + _poly(
        (7.5, 6),
        (9.6, 6),
        (12, 10.2),
        (14.4, 6),
        (16.5, 6),
        (12.9, 11.4),
        (15.5, 11.4),
        (15.5, 13),
        (12.9, 13),
        (12.9, 14.3),
        (15.5, 14.3),
        (15.5, 15.9),
        (12.9, 15.9),
        (12.9, 18),
        (11.1, 18),
        (11.1, 15.9),
        (8.5, 15.9),
        (8.5, 14.3),
        (11.1, 14.3),
        (11.1, 13),
        (8.5, 13),
        (8.5, 11.4),
        (11.1, 11.4),
    ),
    "target": _circ(12, 12, 10) + _circ(12, 12, 7) + _circ(12, 12, 3.5),
    "rocket": "M12 1.8C16.2 4.8 17.8 9.6 16.6 15.2L7.4 15.2C6.2 9.6 7.8 4.8 12 1.8Z"
    + _circ(12, 9, 1.9)
    + "|"
    + _poly((7.6, 10.6), (3.8, 15.4), (3.8, 19.6), (8, 16.8))
    + "|"
    + _poly((16.4, 10.6), (20.2, 15.4), (20.2, 19.6), (16, 16.8))
    + "|"
    + _poly((9.6, 16.8), (12, 22.5), (14.4, 16.8)),
    "lightbulb": "M12 2C7.6 2 5 5.2 5 8.8C5 11.4 6.4 13 7.8 14.5C8.7 15.5 9 16.3 9 17.5L15 17.5"
    "C15 16.3 15.3 15.5 16.2 14.5C17.6 13 19 11.4 19 8.8C19 5.2 16.4 2 12 2Z"
    + "|"
    + _rrect(9, 19, 6, 1.8, 0.9)
    + _rrect(10.2, 21.3, 3.6, 1.5, 0.7),
    "gear": _gear(),
    "clock": _circ(12, 12, 10) + "M11 5.8H13V11.2L16.8 15L15.4 16.4L11 12Z",
    "calendar": _rrect(3, 5, 18, 16.5, 2)
    + _rect(5, 10, 14, 9.5)
    + _rect(7, 12, 3, 2.4)
    + _rect(10.5, 12, 3, 2.4)
    + _rect(14, 12, 3, 2.4)
    + _rect(7, 15.5, 3, 2.4)
    + _rect(10.5, 15.5, 3, 2.4)
    + "|"
    + _rrect(7, 2, 2.2, 4.8, 1)
    + _rrect(14.8, 2, 2.2, 4.8, 1),
    "document": "M5 2H14L19 7V22H5Z" + _rect(8, 11, 8, 1.6) + _rect(8, 14.4, 8, 1.6) + _rect(8, 17.8, 5, 1.6),
    "mail": _rrect(2, 4, 20, 16, 2)
    + _poly((3.8, 6.6), (5, 5.4), (12, 11), (19, 5.4), (20.2, 6.6), (12, 13.4)),
    "phone": _rrect(6.5, 1.5, 11, 21, 2.2) + _rrect(8.5, 4.5, 7, 12.5, 0.8) + _circ(12, 19.5, 1.1),
    "globe": _circ(12, 12, 10)
    + _circ(12, 12, 8.4)
    + "|"
    + _ell(12, 12, 4.4, 8.6)
    + _ell(12, 12, 2.8, 8.6)
    + "|"
    + _rect(3.6, 11.2, 16.8, 1.6),
    "lock": _rrect(4.5, 10.5, 15, 11.5, 2)
    + _circ(12, 14.8, 1.7)
    + _rrect(11.25, 15.8, 1.5, 3.4, 0.5)
    + "|"
    + "M7.5 11V7.5A4.5 4.5 0 0 1 16.5 7.5V11H14.5V7.5A2.5 2.5 0 0 0 9.5 7.5V11Z",
    "shield": "M12 2L20 5V11C20 16.5 16.5 20.5 12 22C7.5 20.5 4 16.5 4 11V5Z"
    + _poly((8, 11.5), (9.4, 10.1), (11, 11.7), (14.6, 8), (16, 9.4), (11, 14.5)),
    "cloud": _circ(7, 15, 4)
    + "|"
    + _circ(12, 10.5, 5.5)
    + "|"
    + _circ(17.5, 14.5, 4.5)
    + "|"
    + _rect(7, 13, 10.5, 6),
    "database": _ell(12, 5, 8, 3) + "|" + _disk(6.2, 3.8) + "|" + _disk(11.2, 3.8) + "|" + _disk(16.2, 3.4),
    "search": _circ(10, 10, 7.6)
    + _circ(10, 10, 5.4)
    + "|"
    + _poly((14.6, 16.1), (16.1, 14.6), (22.2, 20.7), (20.7, 22.2)),
    "star": _star(12, 12.6, 10.6, 4.4),
    "heart": "M12 21.5C6 17 2 13.5 2 8.8C2 5.6 4.4 3.5 7.2 3.5C9.2 3.5 11 4.6 12 6.5C13 4.6 14.8 3.5 16.8 3.5"
    "C19.6 3.5 22 5.6 22 8.8C22 13.5 18 17 12 21.5Z",
    "truck": _rect(1.5, 4.5, 12, 10.5)
    + "|"
    + "M14.5 8H18.7L22.5 12V15H14.5Z"
    + _poly((16, 9.5), (18.1, 9.5), (20.4, 12), (16, 12))
    + "|"
    + _circ(6.5, 18, 2.5)
    + _circ(6.5, 18, 0.9)
    + "|"
    + _circ(18, 18, 2.5)
    + _circ(18, 18, 0.9),
    "cart": _poly((5, 6), (22.2, 6), (19.6, 14), (7.3, 14))
    + "|"
    + _poly((1.5, 2.8), (5.2, 2.8), (9, 15.5), (20, 15.5), (20, 17.2), (7.8, 17.2), (4, 4.5), (1.5, 4.5))
    + "|"
    + _circ(9.5, 20.4, 1.8)
    + "|"
    + _circ(18, 20.4, 1.8),
    "leaf": "M20.5 3.5C11 3.5 4.5 8 4.5 14.5C4.5 16 5 17.3 5.7 18.3L3 21L4.3 22L7 19.3"
    "C8 20 9.3 20.5 10.8 20.5C17.5 20.5 20.5 13 20.5 3.5Z"
    + _poly((8.4, 15.4), (9.4, 16.4), (16.2, 9.6), (15.2, 8.6)),
    "arrow-up": _poly((12, 3), (20, 11.5), (14.5, 11.5), (14.5, 21), (9.5, 21), (9.5, 11.5), (4, 11.5)),
    "arrow-down": _poly((12, 21), (20, 12.5), (14.5, 12.5), (14.5, 3), (9.5, 3), (9.5, 12.5), (4, 12.5)),
    "arrow-right": _poly((21, 12), (12.5, 4), (12.5, 9.5), (3, 9.5), (3, 14.5), (12.5, 14.5), (12.5, 20)),
}


def names() -> list[str]:
    """All icon names, in a stable order."""
    return list(_ICONS)


def path(name: str) -> str | None:
    """The raw path string of an icon (``None`` when unknown)."""
    return _ICONS.get(name.strip().lower()) if isinstance(name, str) else None


_TOKEN = re.compile(r"([MLHVCQAZ])|(-?\d*\.?\d+(?:e-?\d+)?)", re.I)
_ARGS = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "Q": 4, "A": 7, "Z": 0}


def _arc(p0: Point, rx: float, ry: float, large: bool, sweep: bool, p1: Point) -> list[Command]:
    """SVG elliptical arc (axis-aligned, no rotation) -> cubic Béziers."""
    (x0, y0), (x1, y1) = p0, p1
    if (x0, y0) == (x1, y1) or rx == 0 or ry == 0:
        return [("L", [p1])]
    rx, ry = abs(rx), abs(ry)
    dx, dy = (x0 - x1) / 2, (y0 - y1) / 2
    lam = (dx / rx) ** 2 + (dy / ry) ** 2
    if lam > 1:
        rx, ry = rx * math.sqrt(lam), ry * math.sqrt(lam)
    num = rx**2 * ry**2 - rx**2 * dy**2 - ry**2 * dx**2
    den = rx**2 * dy**2 + ry**2 * dx**2
    coef = math.sqrt(max(num / den, 0)) if den else 0
    if large == sweep:
        coef = -coef
    cxp, cyp = coef * rx * dy / ry, -coef * ry * dx / rx
    cx, cy = cxp + (x0 + x1) / 2, cyp + (y0 + y1) / 2
    t0 = math.atan2((dy - cyp) / ry, (dx - cxp) / rx)
    t1 = math.atan2((-dy - cyp) / ry, (-dx - cxp) / rx)
    d = t1 - t0
    if sweep and d < 0:
        d += 2 * math.pi
    elif not sweep and d > 0:
        d -= 2 * math.pi
    n = max(1, math.ceil(abs(d) / (math.pi / 2) - 1e-9))
    step = d / n
    k = 4 / 3 * math.tan(step / 4)
    out: list[Command] = []
    t = t0
    for i in range(n):
        c0, s0, c1, s1 = math.cos(t), math.sin(t), math.cos(t + step), math.sin(t + step)
        a = (cx + rx * (c0 - k * s0), cy + ry * (s0 + k * c0))
        b = (cx + rx * (c1 + k * s1), cy + ry * (s1 - k * c1))
        e = p1 if i == n - 1 else (cx + rx * c1, cy + ry * s1)
        out.append(("C", [a, b, e]))
        t += step
    return out


def _parse_layer(src: str) -> list[Command]:
    cmds: list[Command] = []
    cur: Point = (0.0, 0.0)
    start: Point = cur
    toks = [(m.group(1), m.group(2)) for m in _TOKEN.finditer(src)]
    i = 0
    op = ""
    while i < len(toks):
        if toks[i][0]:
            op = toks[i][0].upper()
            i += 1
            if op == "Z":
                cmds.append(("Z", []))
                cur = start
                continue
        n = _ARGS.get(op)
        if not n or i + n > len(toks) or any(t[1] is None for t in toks[i : i + n]):
            break
        a = [float(t[1]) for t in toks[i : i + n]]
        i += n
        if op == "M":
            cur = start = (a[0], a[1])
            cmds.append(("M", [cur]))
            op = "L"
        elif op == "L":
            cur = (a[0], a[1])
            cmds.append(("L", [cur]))
        elif op == "H":
            cur = (a[0], cur[1])
            cmds.append(("L", [cur]))
        elif op == "V":
            cur = (cur[0], a[0])
            cmds.append(("L", [cur]))
        elif op == "C":
            pts = [(a[0], a[1]), (a[2], a[3]), (a[4], a[5])]
            cmds.append(("C", pts))
            cur = pts[-1]
        elif op == "Q":
            pts = [(a[0], a[1]), (a[2], a[3])]
            cmds.append(("Q", pts))
            cur = pts[-1]
        elif op == "A":
            end = (a[5], a[6])
            cmds.extend(_arc(cur, a[0], a[1], bool(a[3]), bool(a[4]), end))
            cur = end
    return cmds


def commands(name: str) -> list[list[Command]]:
    """Parsed layers of an icon (absolute M/L/C/Q/Z commands); ``[]`` for an unknown name."""
    src = path(name)
    if src is None:
        return []
    return [c for c in (_parse_layer(layer) for layer in src.split("|")) if c]
