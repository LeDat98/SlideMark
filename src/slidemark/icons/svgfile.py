"""``icon=file.svg``: a simple filled SVG becomes native custom geometry (None: embed a picture instead).

Handled: ``path`` (every command, relative or absolute), ``rect``, ``circle``, ``ellipse``, ``polygon``,
``polyline``, nested ``g``. Not handled (returns ``None``): strokes, gradients / ``url()`` fills, transforms,
``use``, ``image``, ``text``. Nothing here raises.
"""

from __future__ import annotations

import math
import re

from . import GRID, Command, Point, _arc

_NUM = r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?"
_NUM_RE = re.compile(_NUM)
_ARGS = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7, "Z": 0}
MAX_BYTES = 200_000


class _Complex(Exception):
    """The SVG needs more than filled outlines."""


def _path(d: str) -> list[Command]:
    cmds: list[Command] = []
    pos, n = 0, len(d)
    cur: Point = (0.0, 0.0)
    start: Point = cur
    last_c: Point | None = None  # previous cubic control (for S)
    last_q: Point | None = None  # previous quad control (for T)
    op = ""

    def number() -> float | None:
        nonlocal pos
        m = re.compile(r"[\s,]*(" + _NUM + ")").match(d, pos)
        if not m:
            return None
        pos = m.end()
        return float(m.group(1))

    def flag() -> float | None:
        nonlocal pos
        m = re.compile(r"[\s,]*([01])").match(d, pos)
        if not m:
            return None
        pos = m.end()
        return float(m.group(1))

    while pos < n:
        m = re.compile(r"[\s,]*([MmLlHhVvCcSsQqTtAaZz])").match(d, pos)
        if m:
            op, pos = m.group(1), m.end()
        elif re.compile(r"[\s,]*$").match(d, pos):
            break
        elif not op or op in "Zz":
            raise _Complex
        rel = op.islower()
        o = op.upper()
        if o == "Z":
            cmds.append(("Z", []))
            cur = start
            last_c = last_q = None
            continue
        a: list[float] = []
        for i in range(_ARGS[o]):
            v = flag() if (o == "A" and i in (3, 4)) else number()
            if v is None:
                raise _Complex
            a.append(v)
        ox, oy = cur if rel else (0.0, 0.0)
        nc = nq = None
        if o == "M":
            cur = start = (a[0] + ox, a[1] + oy)
            cmds.append(("M", [cur]))
            op = "l" if rel else "L"
        elif o == "L":
            cur = (a[0] + ox, a[1] + oy)
            cmds.append(("L", [cur]))
        elif o == "H":
            cur = (a[0] + ox, cur[1])
            cmds.append(("L", [cur]))
        elif o == "V":
            cur = (cur[0], a[0] + oy)
            cmds.append(("L", [cur]))
        elif o in "CS":
            if o == "C":
                c1 = (a[0] + ox, a[1] + oy)
                c2, e = (a[2] + ox, a[3] + oy), (a[4] + ox, a[5] + oy)
            else:
                c1 = (2 * cur[0] - last_c[0], 2 * cur[1] - last_c[1]) if last_c else cur
                c2, e = (a[0] + ox, a[1] + oy), (a[2] + ox, a[3] + oy)
            cmds.append(("C", [c1, c2, e]))
            cur, nc = e, c2
        elif o in "QT":
            if o == "Q":
                q = (a[0] + ox, a[1] + oy)
                e = (a[2] + ox, a[3] + oy)
            else:
                q = (2 * cur[0] - last_q[0], 2 * cur[1] - last_q[1]) if last_q else cur
                e = (a[0] + ox, a[1] + oy)
            cmds.append(("Q", [q, e]))
            cur, nq = e, q
        else:  # A (the x-axis rotation is ignored: exact for circles, close for the rest)
            e = (a[5] + ox, a[6] + oy)
            cmds.extend(_arc(cur, a[0], a[1], bool(a[3]), bool(a[4]), e))
            cur = e
        last_c, last_q = nc, nq
    return cmds


def _poly(pts: str, close: bool) -> list[Command]:
    v = [float(x) for x in _NUM_RE.findall(pts)]
    p = list(zip(v[0::2], v[1::2], strict=False))
    if len(p) < 2:
        raise _Complex
    out: list[Command] = [("M", [p[0]])] + [("L", [q]) for q in p[1:]]
    return out + [("Z", [])] if close else out


def _ellipse(cx: float, cy: float, rx: float, ry: float) -> list[Command]:
    return [
        ("M", [(cx - rx, cy)]),
        *_arc((cx - rx, cy), rx, ry, True, False, (cx + rx, cy)),
        *_arc((cx + rx, cy), rx, ry, True, False, (cx - rx, cy)),
        ("Z", []),
    ]


def _f(el, name: str, default: float = 0.0) -> float:
    m = _NUM_RE.match((el.get(name) or "").strip())
    return float(m.group(0)) if m else default


def _props(el) -> dict[str, str]:
    out = {k: v for k, v in el.attrib.items() if k in ("fill", "stroke", "display", "visibility", "opacity")}
    for decl in (el.get("style") or "").split(";"):
        k, _, v = decl.partition(":")
        if v.strip():
            out[k.strip().lower()] = v.strip().lower()
    return out


def _shape(el, tag: str) -> list[Command] | None:
    if tag == "path":
        return _path(el.get("d") or "")
    if tag == "rect":
        x, y, w, h = _f(el, "x"), _f(el, "y"), _f(el, "width"), _f(el, "height")
        if w <= 0 or h <= 0:
            return None
        r = min(_f(el, "rx", _f(el, "ry")), w / 2, h / 2)
        if r <= 0:
            return [
                ("M", [(x, y)]),
                ("L", [(x + w, y)]),
                ("L", [(x + w, y + h)]),
                ("L", [(x, y + h)]),
                ("Z", []),
            ]
        out: list[Command] = [("M", [(x + r, y)]), ("L", [(x + w - r, y)])]
        for corner, nxt in (
            ((x + w, y + r), (x + w, y + h - r)),
            ((x + w - r, y + h), (x + r, y + h)),
            ((x, y + h - r), (x, y + r)),
            ((x + r, y), None),
        ):
            out += _arc(out[-1][1][-1], r, r, False, True, corner)
            out.append(("L", [nxt]) if nxt else ("Z", []))
        return out
    if tag in ("circle", "ellipse"):
        rx = _f(el, "r") if tag == "circle" else _f(el, "rx")
        ry = rx if tag == "circle" else _f(el, "ry")
        return _ellipse(_f(el, "cx"), _f(el, "cy"), rx, ry) if rx > 0 and ry > 0 else None
    if tag in ("polygon", "polyline"):
        return _poly(el.get("points") or "", True)
    return None


def _walk(el, inherited: dict[str, str], out: list[list[Command]]) -> None:
    from ..render.svg import _local

    tag = _local(el.tag)
    if tag in ("title", "desc", "metadata", "defs", "style", "namedview"):
        return
    if tag in ("use", "image", "text", "mask", "clippath", "lineargradient", "radialgradient", "pattern"):
        raise _Complex
    if el.get("transform") or el.get("clip-path") or el.get("mask") or el.get("filter"):
        raise _Complex
    props = {**inherited, **_props(el)}
    if props.get("display") == "none" or props.get("visibility") == "hidden":
        return
    if tag in ("svg", "g", "a", "switch"):
        for ch in el:
            if isinstance(ch.tag, str):
                _walk(ch, props, out)
        return
    fill = props.get("fill", "black")
    stroke = props.get("stroke", "none")
    if (
        "url(" in fill
        or (stroke not in ("none", "transparent", "") and stroke != "currentcolor")
        or "url(" in stroke
    ):
        raise _Complex
    if stroke == "currentcolor":
        raise _Complex
    if fill in ("none", "transparent", "white", "#fff", "#ffffff"):  # white = a cut-out on a light page
        return
    cmds = _shape(el, tag)
    if cmds:
        out.append(cmds)


def _bounds(layers: list[list[Command]]) -> tuple[float, float, float, float] | None:
    pts = [p for layer in layers for _, ps in layer for p in ps]
    if not pts:
        return None
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def svg_layers(text: str) -> list[list[Command]] | None:
    """Layers (absolute M/L/C/Q/Z on the 24 grid, aspect kept, centred) of a simple filled SVG, else None."""
    from lxml import etree

    from ..render.svg import sanitize_svg

    try:
        if len(text) > MAX_BYTES:
            return None
        clean, _ = sanitize_svg(text)
        if clean is None:
            return None
        root = etree.fromstring(clean.encode("utf-8"))
        layers: list[list[Command]] = []
        _walk(root, {}, layers)
        if not layers:
            return None
        vb = [float(x) for x in _NUM_RE.findall(root.get("viewBox") or "")]
        if len(vb) == 4 and vb[2] > 0 and vb[3] > 0:
            x0, y0, w, h = vb
        else:
            b = _bounds(layers)
            if b is None or b[2] <= b[0] or b[3] <= b[1]:
                return None
            x0, y0, w, h = b[0], b[1], b[2] - b[0], b[3] - b[1]
        s = GRID / max(w, h)
        ox, oy = (GRID - w * s) / 2, (GRID - h * s) / 2

        def tf(p: Point) -> Point:
            x = min(max((p[0] - x0) * s + ox, 0.0), GRID)  # clamp: custom geometry may not leave its box
            y = min(max((p[1] - y0) * s + oy, 0.0), GRID)
            return (x, y) if math.isfinite(x) and math.isfinite(y) else (0.0, 0.0)

        return [[(op, [tf(p) for p in ps]) for op, ps in layer] for layer in layers]
    except Exception:
        return None
