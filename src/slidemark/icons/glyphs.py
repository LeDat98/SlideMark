"""More built-in glyphs (same authoring rules as ``icons/__init__.py``: 24x24 grid, solid shapes)."""

from __future__ import annotations

import math

from . import _circ, _ell, _n, _poly, _rect, _rrect


def _spark(cx: float, cy: float, r: float, k: float) -> str:
    return _poly(
        (cx, cy - r),
        (cx + k, cy - k),
        (cx + r, cy),
        (cx + k, cy + k),
        (cx, cy + r),
        (cx - k, cy + k),
        (cx - r, cy),
        (cx - k, cy - k),
    )


def _sector(cx: float, cy: float, ri: float, ro: float, half: float = 45) -> str:
    """Ring segment centred on the vertical axis (a wifi bar), ``half`` degrees each side."""
    s, c = math.sin(math.radians(half)), math.cos(math.radians(half))
    return (
        f"M{_n(cx - ro * s)} {_n(cy - ro * c)}A{_n(ro)} {_n(ro)} 0 0 1 {_n(cx + ro * s)} {_n(cy - ro * c)}"
        f"L{_n(cx + ri * s)} {_n(cy - ri * c)}A{_n(ri)} {_n(ri)} 0 0 0 {_n(cx - ri * s)} {_n(cy - ri * c)}Z"
    )


def _rot(pts: list[tuple[float, float]], deg: float) -> list[tuple[float, float]]:
    s, c = math.sin(math.radians(deg)), math.cos(math.radians(deg))
    return [(12 + (x - 12) * c - (y - 12) * s, 12 + (x - 12) * s + (y - 12) * c) for x, y in pts]


def _wrench() -> str:
    cy, r, w = 6.5, 5.6, 1.9
    th = math.asin(w / r)
    pts: list[tuple[float, float]] = [(12 + w, 7.8), (12 + w, cy - r * math.cos(th))]
    steps = 28
    for i in range(steps + 1):
        a = th + (2 * math.pi - 2 * th) * i / steps
        pts.append((12 + r * math.sin(a), cy - r * math.cos(a)))
    pts += [(12 - w, cy - r * math.cos(th)), (12 - w, 7.8)]
    head = _poly(*_rot(pts, 45))
    handle = _poly(*_rot([(10.2, 10), (13.8, 10), (13.8, 20), (12, 21.8), (10.2, 20)], 45))
    return head + "|" + handle


def _arrow_ring() -> str:
    """``refresh``: a clockwise ring open at the top right, with an arrowhead at its end."""
    cx = cy = 12.0
    ro, ri, a0, a1 = 9.2, 6.4, -35.0, 225.0

    def at(r: float, deg: float) -> tuple[float, float]:
        a = math.radians(deg)
        return cx + r * math.cos(a), cy + r * math.sin(a)

    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = at(ro, a0), at(ro, a1), at(ri, a1), at(ri, a0)
    ring = (
        f"M{_n(x0)} {_n(y0)}A{_n(ro)} {_n(ro)} 0 1 1 {_n(x1)} {_n(y1)}L{_n(x2)} {_n(y2)}"
        f"A{_n(ri)} {_n(ri)} 0 1 0 {_n(x3)} {_n(y3)}Z"
    )
    mid = (ro + ri) / 2
    a = math.radians(a1)
    tan = (-math.sin(a), math.cos(a))  # clockwise (y down)
    bx, by = at(mid, a1)
    wing = (ro - ri) / 2 + 2.3
    nx, ny = math.cos(a), math.sin(a)
    head = _poly(
        (bx + nx * wing, by + ny * wing),
        (bx + tan[0] * 5.2, by + tan[1] * 5.2),
        (bx - nx * wing, by - ny * wing),
    )
    return ring + "|" + head


def _tooth() -> str:
    return (
        "M7.5 3C5 3 3 5 3 8C3 11 5 12.5 5.5 15.5C6 19 6.5 22 8.5 22C10.5 22 10.5 17.5 12 17.5"
        "C13.5 17.5 13.5 22 15.5 22C17.5 22 18 19 18.5 15.5C19 12.5 21 11 21 8C21 5 19 3 16.5 3"
        "C14.5 3 13.5 4 12 4C10.5 4 9.5 3 7.5 3Z"
    )


GLYPHS: dict[str, str] = {
    "headphones": "M3.5 15V12A8.5 8.5 0 0 1 20.5 12V15H18.5V12A6.5 6.5 0 0 0 5.5 12V15Z"
    + "|"
    + _rrect(2.5, 13, 5, 8, 2)
    + "|"
    + _rrect(16.5, 13, 5, 8, 2),
    "battery": _rrect(1.5, 6.5, 18, 11, 2)
    + _rect(3.5, 8.5, 14, 7)
    + "|"
    + _rect(5, 10, 3, 4)
    + _rect(9, 10, 3, 4)
    + _rect(13, 10, 3, 4)
    + "|"
    + _rrect(20.5, 9.8, 2, 4.4, 0.8),
    "music": _poly((8, 4.5), (20, 2.5), (20, 6.5), (8, 8.5))
    + "|"
    + _rect(8, 4.5, 2, 13.5)
    + _rect(18, 2.5, 2, 13.5)
    + "|"
    + _ell(6.5, 18.6, 3.6, 2.8)
    + "|"
    + _ell(16.5, 16.6, 3.6, 2.8),
    "sparkles": _spark(10, 13, 9, 2.4) + "|" + _spark(19, 5, 4, 1.1) + "|" + _spark(19.5, 19.5, 3, 0.8),
    "smile": _circ(12, 12, 10)
    + _circ(8.5, 9.5, 1.5)
    + _circ(15.5, 9.5, 1.5)
    + "M6.8 14C8 17.8 16 17.8 17.2 14L15.6 13.2C14.6 15.4 9.4 15.4 8.4 13.2Z",
    "camera": _rrect(2, 7, 20, 14, 2)
    + _circ(12, 14, 4.6)
    + _circ(12, 14, 2.8)
    + "|"
    + _poly((8, 4), (16, 4), (17.6, 7.2), (6.4, 7.2)),
    "book": "M11.2 7C9.5 5.6 6.5 5 2.5 5.4V19C6.5 18.6 9.5 19.2 11.2 20.6Z"
    + "|"
    + "M12.8 7C14.5 5.6 17.5 5 21.5 5.4V19C17.5 18.6 14.5 19.2 12.8 20.6Z",
    "graduation-cap": _poly((12, 4), (23, 9.5), (12, 15), (1, 9.5))
    + "|"
    + "M6 12.8V17C6 18.8 9 20 12 20C15 20 18 18.8 18 17V12.8L12 15.8Z"
    + "|"
    + _rect(20.8, 10, 1.4, 6.5),
    "home": "M12 3L22 12H19V21H14V15H10V21H5V12H2Z" + "|" + _rect(16.5, 4.5, 2.5, 4),
    "map-pin": "M12 22C12 22 4.5 14.5 4.5 9.5A7.5 7.5 0 0 1 19.5 9.5C19.5 14.5 12 22 12 22Z"
    + _circ(12, 9.5, 3),
    "wifi": _sector(12, 20, 4.5, 7)
    + "|"
    + _sector(12, 20, 9, 11.5)
    + "|"
    + _sector(12, 20, 13.5, 16)
    + "|"
    + _circ(12, 19.5, 1.9),
    "code": _poly((8, 6.5), (9.4, 7.9), (5.3, 12), (9.4, 16.1), (8, 17.5), (2, 12))
    + "|"
    + _poly((16, 6.5), (14.6, 7.9), (18.7, 12), (14.6, 16.1), (16, 17.5), (22, 12))
    + "|"
    + _poly((13.6, 4.5), (15.2, 5), (10.4, 19.5), (8.8, 19)),
    "cpu": _rrect(5, 5, 14, 14, 1.5)
    + _rect(8, 8, 8, 8)
    + _rect(10, 10, 4, 4)
    + "".join(
        _rect(x, 2, 1.6, 3) + _rect(x, 19, 1.6, 3) + _rect(2, x, 3, 1.6) + _rect(19, x, 3, 1.6)
        for x in (8, 11.2, 14.4)
    ),
    "bell": "M12 2.5C8.2 2.5 6 5.4 6 9V13.5L3.8 17V18.5H20.2V17L18 13.5V9C18 5.4 15.8 2.5 12 2.5Z"
    + "|"
    + "M9.6 19.8H14.4A2.4 2.4 0 0 1 9.6 19.8Z",
    "flag": _rect(4, 2, 2.2, 20) + "|" + "M6.2 3.5C9 2 11.5 5 14.5 4C16.5 3.4 18 3.2 20.5 4V13.5"
    "C18 12.7 16.5 12.9 14.5 13.5C11.5 14.5 9 11.5 6.2 13Z",
    "gift": _rect(4, 11.5, 7, 10)
    + _rect(13, 11.5, 7, 10)
    + "|"
    + _rect(2.5, 7.5, 8.5, 3.5)
    + _rect(13, 7.5, 8.5, 3.5)
    + "|"
    + _ell(8.6, 4.6, 3.2, 2.4)
    + _ell(8.6, 4.6, 1.4, 0.8)
    + "|"
    + _ell(15.4, 4.6, 3.2, 2.4)
    + _ell(15.4, 4.6, 1.4, 0.8),
    "coffee": "M3 8H17V14.5C17 17.6 14.5 20 11.5 20H8.5C5.5 20 3 17.6 3 14.5Z"
    + "|"
    + "M17 9.5H18.5A3.5 3.5 0 0 1 18.5 16.5H16.6V14.8H18.5A1.8 1.8 0 0 0 18.5 11.2H17Z"
    + "|"
    + _rrect(6, 2, 1.7, 4.2, 0.85)
    + _rrect(9.6, 2, 1.7, 4.2, 0.85)
    + _rrect(13.2, 2, 1.7, 4.2, 0.85)
    + "|"
    + _rrect(1.5, 21, 17, 1.8, 0.9),
    "plane": _poly(
        (12, 2),
        (13.6, 5),
        (13.6, 9.5),
        (22, 14.5),
        (22, 16.5),
        (13.6, 14),
        (13.4, 19),
        (16, 20.8),
        (16, 22.3),
        (12, 21.2),
        (8, 22.3),
        (8, 20.8),
        (10.6, 19),
        (10.4, 14),
        (2, 16.5),
        (2, 14.5),
        (10.4, 9.5),
        (10.4, 5),
    ),
    "wrench": _wrench(),
    "key": _circ(7, 12, 5.2)
    + _circ(7, 12, 2.2)
    + "|"
    + _rect(11, 10.8, 11, 2.6)
    + "|"
    + _rect(15.2, 13, 2.2, 3.6)
    + "|"
    + _rect(19.2, 13, 2.2, 3.6),
    "play": _circ(12, 12, 10) + _poly((9.5, 7), (17, 12), (9.5, 17)),
    "trophy": "M6.5 3H17.5V9.5A5.5 5.5 0 0 1 6.5 9.5Z"
    + "|"
    + "M6.5 5H3V8.5C3 11 4.7 12 7 12.3V10.6C5.8 10.4 4.8 9.8 4.8 8.5V6.8H6.5Z"
    + "|"
    + "M17.5 5H21V8.5C21 11 19.3 12 17 12.3V10.6C18.2 10.4 19.2 9.8 19.2 8.5V6.8H17.5Z"
    + "|"
    + _rect(10.8, 14.5, 2.4, 4.5)
    + "|"
    + _rrect(7, 18.5, 10, 3.2, 1),
    "briefcase": _rrect(2, 7, 20, 14, 2)
    + _rect(3.5, 12.2, 17, 1.3)
    + "|"
    + "M8.5 7V5A1.5 1.5 0 0 1 10 3.5H14A1.5 1.5 0 0 1 15.5 5V7H13.8V5.3H10.2V7Z"
    + "|"
    + _rect(10.5, 11, 3, 3.6),
    "chat": _rrect(2, 3, 20, 14, 3)
    + _circ(8, 10, 1.4)
    + _circ(12, 10, 1.4)
    + _circ(16, 10, 1.4)
    + "|"
    + _poly((5.5, 15), (5.5, 21.5), (11.5, 16)),
    "bolt": _poly((13.5, 2), (4, 13.8), (10.8, 13.8), (9.5, 22), (20, 9.6), (13, 9.6)),
    "tooth": _tooth(),
    "refresh": _arrow_ring(),
    "tag": _poly((2.5, 2.5), (12, 2.5), (21.5, 12), (12, 21.5), (2.5, 12)) + _circ(7.2, 7.2, 1.9),
}

ALIASES: dict[str, str] = {
    "sync": "refresh",
    "reload": "refresh",
    "loop": "refresh",
    "cycle": "refresh",
    "label": "tag",
    "price": "tag",
    "house": "home",
    "message": "chat",
    "comment": "chat",
    "pin": "map-pin",
    "location": "map-pin",
    "graduation": "graduation-cap",
    "education": "graduation-cap",
    "lightning": "bolt",
    "energy": "bolt",
    "sparkle": "sparkles",
    "magic": "sparkles",
    "audio": "headphones",
    "headset": "headphones",
    "photo": "camera",
    "travel": "plane",
    "flight": "plane",
    "tool": "wrench",
    "award": "trophy",
    "medal": "trophy",
    "work": "briefcase",
    "notification": "bell",
    "alert": "bell",
    "present": "gift",
    "chip": "cpu",
    "processor": "cpu",
    "signal": "wifi",
    "wireless": "wifi",
    "happy": "smile",
    "read": "book",
    "tea": "coffee",
    "cafe": "coffee",
    "password": "key",
    "video": "play",
    "dental": "tooth",
    "power": "battery",
}
