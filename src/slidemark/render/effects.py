"""Native fills and effects for shapes: CSS gradients -> ``a:gradFill``, CSS box-shadows -> ``a:outerShdw``.

``Style.fill`` may be a solid color (theme name, #RGB, #RRGGBB, #RRGGBBAA, rgb(), rgba()) or a CSS
``linear-gradient`` / ``radial-gradient``. ``Style.shadow`` may be ``True`` (``theme.render.shadow``) or
``"x y blur [spread] color"`` in pt. ``Style.opacity`` multiplies the fill alpha. Nothing here raises:
a value that does not parse becomes a solid first color / no shadow plus a one-line diagnostic.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from lxml import etree
from pptx.oxml.ns import qn

from ..ir import Style
from .util import RenderCtx, gradient_args, is_direction, is_gradient, parse_color, try_color

_FILLS = ("a:noFill", "a:solidFill", "a:gradFill", "a:blipFill", "a:pattFill", "a:grpFill")
# children of a:spPr that follow the fill / the effect list (schema order)
_AFTER_FILL = ("a:ln", "a:effectLst", "a:effectDag", "a:scene3d", "a:sp3d", "a:extLst")
_AFTER_EFFECT = ("a:effectDag", "a:scene3d", "a:sp3d", "a:extLst")
_TO = {
    "top": 0.0,
    "right": 90.0,
    "bottom": 180.0,
    "left": 270.0,
    "top right": 45.0,
    "right top": 45.0,
    "bottom right": 135.0,
    "right bottom": 135.0,
    "bottom left": 225.0,
    "left bottom": 225.0,
    "top left": 315.0,
    "left top": 315.0,
}
_ANGLE = re.compile(r"^(-?[\d.]+)(deg|rad|turn|grad)$", re.I)
_STOP = re.compile(r"^(.*?)(?:\s+(-?[\d.]+)%)?$", re.S)
_NUM = re.compile(r"^(-?\d+(?:\.\d+)?|-?\.\d+)(px|pt)?$", re.I)
_PT = 12700  # EMU per point


@dataclass
class Gradient:
    kind: str  # "linear" | "radial"
    css_angle: float  # degrees, CSS convention (0 = to top, 90 = to right); linear only
    stops: list[tuple[str, float | None, int]]  # (RRGGBB, alpha, position in 1/1000 %)


def _angle(part: str) -> float | None:
    p = part.strip().lower()
    m = _ANGLE.match(p)
    if m:
        v = float(m.group(1))
        return v * {"deg": 1.0, "rad": 180 / math.pi, "turn": 360.0, "grad": 0.9}[m.group(2)]
    if p.startswith("to "):
        return _TO.get(" ".join(p[3:].split()))
    return None


def parse_gradient(rc: RenderCtx, css: str) -> Gradient | None:
    """A ``Gradient`` from a CSS gradient string, or None when it has fewer than two usable stops."""
    kind, args = gradient_args(css)
    angle = 180.0  # CSS default: to bottom
    if args and is_direction(args[0]):
        a = _angle(args[0])
        if a is not None:
            angle = a
        args = args[1:]
    raw: list[tuple[str, float | None, float | None]] = []
    for part in args:
        m = _STOP.match(part.strip())
        color_text = (m.group(1) if m else part).strip()
        pos = float(m.group(2)) if m and m.group(2) is not None else None
        if not color_text:
            continue
        got = try_color(rc.theme, color_text)
        if got is None:
            continue
        hex_, alpha = got
        raw.append((hex_, alpha, pos))
    if len(raw) < 2:
        return None
    # CSS stop positions: missing first = 0, missing last = 100, the rest spread evenly between neighbours
    pos: list[float | None] = [p for _, _, p in raw]
    pos[0] = 0.0 if pos[0] is None else pos[0]
    pos[-1] = 100.0 if pos[-1] is None else pos[-1]
    i = 0
    while i < len(pos):
        if pos[i] is None:
            j = i
            while pos[j] is None:
                j += 1
            lo, hi = pos[i - 1], pos[j]
            for k in range(i, j):
                pos[k] = lo + (hi - lo) * (k - i + 1) / (j - i + 1)  # type: ignore[operator]
            i = j
        i += 1
    last = 0.0
    stops = []
    for (hx, al, _), p in zip(raw, pos, strict=True):
        last = max(last, min(max(p or 0.0, 0.0), 100.0))  # positions never go backwards
        stops.append((hx, al, round(last * 1000)))
    return Gradient(kind, angle, stops)


def _clr(parent, hex_: str, alpha: float | None) -> None:
    c = etree.SubElement(parent, qn("a:srgbClr"))
    c.set("val", hex_)
    if alpha is not None and alpha < 1:
        etree.SubElement(c, qn("a:alpha")).set("val", str(round(max(alpha, 0.0) * 100000)))


def _insert(spPr, el, successors: tuple[str, ...]) -> None:
    for tag in successors:
        nxt = spPr.find(qn(tag))
        if nxt is not None:
            nxt.addprevious(el)
            return
    spPr.append(el)


def _strip_fills(spPr) -> None:
    for tag in _FILLS:
        for old in spPr.findall(qn(tag)):
            spPr.remove(old)


def set_solid(spPr, hex_: str, alpha: float | None) -> None:
    _strip_fills(spPr)
    fill = etree.Element(qn("a:solidFill"))
    _clr(fill, hex_, alpha)
    _insert(spPr, fill, _AFTER_FILL)


def set_gradient(spPr, g: Gradient, opacity: float | None) -> None:
    _strip_fills(spPr)
    fill = etree.Element(qn("a:gradFill"))
    fill.set("rotWithShape", "1")
    lst = etree.SubElement(fill, qn("a:gsLst"))
    for hx, al, pos in g.stops:
        if opacity is not None:
            al = (1.0 if al is None else al) * opacity
        gs = etree.SubElement(lst, qn("a:gs"))
        gs.set("pos", str(pos))
        _clr(gs, hx, al)
    if g.kind == "radial":
        path = etree.SubElement(fill, qn("a:path"))
        path.set("path", "circle")
        rect = etree.SubElement(path, qn("a:fillToRect"))
        for side in "ltrb":
            rect.set(side, "50000")
    else:
        lin = etree.SubElement(fill, qn("a:lin"))
        lin.set("ang", str(round(((g.css_angle - 90) % 360) * 60000)))
        lin.set("scaled", "0")
    _insert(spPr, fill, _AFTER_FILL)


def apply_fill(rc: RenderCtx, spPr, st: Style) -> bool:
    """Write ``st.fill`` (solid, #RRGGBBAA or gradient) and ``st.opacity`` into ``spPr``.

    Returns False when the style has no fill (the caller then clears it).
    """
    if not st.fill:
        return False
    opacity = st.opacity if st.opacity is not None and 0 <= st.opacity < 1 else None
    if is_gradient(st.fill):
        g = parse_gradient(rc, st.fill)
        if g is not None:
            set_gradient(spPr, g, opacity)
            return True
        rc.diag(
            "bad-gradient",
            f"cannot parse gradient {st.fill[:60]!r}; used its first color",
            "write linear-gradient(135deg, #7C5CFF, #00D1B2) or radial-gradient(#fff, #000)",
        )
    hex_, alpha = parse_color(rc.theme, st.fill)
    if alpha == 0:  # `background: none` / transparent: no fill at all
        return False
    if opacity is not None:
        alpha = (1.0 if alpha is None else alpha) * opacity
    set_solid(spPr, hex_, alpha)
    return True


def set_picture(
    spPr, rid: str, crop: tuple[float, float, float, float] | None, opacity: float | None
) -> None:
    """``a:blipFill`` (stretched picture) for image relationship ``rid``; ``crop`` = (l, t, r, b) shares."""
    _strip_fills(spPr)
    fill = etree.Element(qn("a:blipFill"))
    fill.set("rotWithShape", "1")
    blip = etree.SubElement(fill, qn("a:blip"))
    blip.set(qn("r:embed"), rid)
    if opacity is not None:
        etree.SubElement(blip, qn("a:alphaModFix")).set("amt", str(round(opacity * 100000)))
    if crop and any(crop):
        src = etree.SubElement(fill, qn("a:srcRect"))
        for name, v in zip("ltrb", crop, strict=True):
            if v:
                src.set(name, str(round(v * 100000)))
    etree.SubElement(etree.SubElement(fill, qn("a:stretch")), qn("a:fillRect"))
    _insert(spPr, fill, _AFTER_FILL)


def cover_crop(img_w: int, img_h: int, w: int, h: int) -> tuple[float, float, float, float]:
    """(l, t, r, b) shares that make an ``img_w`` x ``img_h`` picture cover a ``w`` x ``h`` box."""
    if not (img_w and img_h and w and h):
        return 0.0, 0.0, 0.0, 0.0
    ia, ba = img_w / img_h, w / h
    if ia > ba:
        c = (1 - ba / ia) / 2
        return c, 0.0, c, 0.0
    c = (1 - ia / ba) / 2
    return 0.0, c, 0.0, c


def parse_shadow(
    rc: RenderCtx, value: bool | str
) -> tuple[float, float, float, float, str, float | None] | None:
    """``(x, y, blur, spread, RRGGBB, alpha)`` in pt from ``True`` or ``"x y blur [spread] color"``."""
    text = rc.theme.render.shadow if value is True else str(value)
    if " inset" in f" {text.lower()}" or text.lower().startswith("inset"):
        rc.diag(
            "bad-shadow",
            f"inset shadow {text[:40]!r} is not supported",
            "use an outer shadow: 0 4 12 #00000040",
        )
        return None
    nums: list[float] = []
    rest = text.strip()
    while len(nums) < 4 and rest:
        head, _, tail = rest.partition(" ")
        m = _NUM.match(head)
        if not m:
            break
        v = float(m.group(1))
        nums.append(v * 0.75 if (m.group(2) or "").lower() == "px" else v)
        rest = tail.strip()
    if len(nums) < 2:
        rc.diag(
            "bad-shadow",
            f"cannot parse shadow {text[:40]!r}; no shadow drawn",
            'write "x y blur [spread] color" in pt, e.g. "0 4 12 #00000040"',
        )
        return None
    nums += [0.0] * (4 - len(nums))
    got = try_color(rc.theme, rest)
    if got is None:  # no (or an unreadable) color: the dark ink at a quarter strength
        got = (parse_color(rc.theme, rc.theme.render.ink_dark)[0], 0.25)
    hex_, alpha = got
    return nums[0], nums[1], max(nums[2], 0.0), nums[3], hex_, alpha


def apply_shadow(rc: RenderCtx, spPr, st: Style, w: int, h: int) -> None:
    """Replace the effect list of ``spPr``: an ``a:outerShdw`` for ``st.shadow``, else an empty list
    (no theme shadow either)."""
    for old in spPr.findall(qn("a:effectLst")):
        spPr.remove(old)
    eff = etree.Element(qn("a:effectLst"))
    parsed = parse_shadow(rc, st.shadow) if st.shadow else None
    if parsed is not None:
        x, y, blur, spread, hex_, alpha = parsed
        sh = etree.SubElement(eff, qn("a:outerShdw"))
        sh.set("blurRad", str(round(blur * _PT)))
        sh.set("dist", str(round(math.hypot(x, y) * _PT)))
        sh.set("dir", str(round((math.degrees(math.atan2(y, x)) % 360) * 60000)))
        if spread and w > 0 and h > 0:
            sh.set("sx", str(round((w + 2 * spread * _PT) / w * 100000)))
            sh.set("sy", str(round((h + 2 * spread * _PT) / h * 100000)))
        sh.set("algn", "ctr")
        sh.set("rotWithShape", "0")
        _clr(sh, hex_, alpha)
    _insert(spPr, eff, _AFTER_EFFECT)
