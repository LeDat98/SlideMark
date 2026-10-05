"""Layout linter: checks the placed items of every slide and returns one-line ``Diagnostic``s.

Rules (all warnings, cheap to read for an agent):

- ``overflow``: text needs more height than its box, even at the autofit scale.
- ``off-slide``: an item extends past the slide edge.
- ``overlap``: two items overlap (one fully inside another, e.g. a heading in its card, is fine).
- ``contrast``: text color vs the fill behind it is below WCAG 3:1.
- ``tiny-text``: text renders below the theme's minimum font size.
- ``alt``: an image without alt text.
- ``connector-crosses``: a connector runs through a block that is not one of its ends.
"""

from __future__ import annotations

from .ir import Container, Deck, Diagnostic, Image, Media, Placed, Shape, Text
from .layout import measure
from .theme import Theme
from .units import EMU_PER_PT, slide_size

_TOL = int(EMU_PER_PT)  # 1pt slack for rounding
_OVERFLOW_TOL = 1.08  # measurement is an estimate: report only clear overflows


def _hex(color: str | None, theme: Theme) -> tuple[float, float, float] | None:
    c = theme.color(color)
    if not c or not c.startswith("#") or len(c) != 7:
        return None
    try:
        return tuple(int(c[i : i + 2], 16) / 255 for i in (1, 3, 5))  # type: ignore[return-value]
    except ValueError:
        return None


def _luminance(rgb: tuple[float, float, float]) -> float:
    def ch(v: float) -> float:
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = (ch(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _label(p: Placed) -> str:
    el = p.element
    paras = getattr(el, "paragraphs", None)
    if paras:
        text = " ".join(q.plain for q in paras).strip()
        if text:
            return f"'{text[:24]}…'" if len(text) > 24 else f"'{text}'"
    if isinstance(el, (Image, Media)):
        return f"{el.type} {el.src}"
    return el.type


def _inside(a: Placed, b: Placed) -> bool:
    """True when ``a`` lies within ``b`` (with tolerance)."""
    return (
        a.x >= b.x - _TOL
        and a.y >= b.y - _TOL
        and a.x + a.w <= b.x + b.w + _TOL
        and a.y + a.h <= b.y + b.h + _TOL
    )


def _overlap_area(a: Placed, b: Placed) -> int:
    w = min(a.x + a.w, b.x + b.w) - max(a.x, b.x)
    h = min(a.y + a.h, b.y + b.h) - max(a.y, b.y)
    return max(w, 0) * max(h, 0)


def _is_line(p: Placed) -> bool:
    return isinstance(p.element, Shape) and p.element.shape in ("line", "arrow-right", "connector")


def _is_band(p: Placed) -> bool:
    """Decoration drawn behind other items (title band, background shapes)."""
    el = p.element
    return isinstance(el, Shape) and not el.paragraphs and el.shape in ("rect", "rounded-rect")


def _backdrop(items: list[Placed], i: int, bg: tuple[float, float, float] | None, theme: Theme):
    """Fill color directly behind item ``i``: the topmost earlier filled item containing its center."""
    p = items[i]
    cx, cy = p.x + p.w // 2, p.y + p.h // 2
    for q in reversed(items[:i]):
        if q.style.fill and q.x <= cx <= q.x + q.w and q.y <= cy <= q.y + q.h:
            rgb = _hex(q.style.fill, theme)
            if rgb:
                return rgb
    return bg


def lint_slide(items: list[Placed], deck: Deck, theme: Theme, index: int) -> list[Diagnostic]:
    out: list[Diagnostic] = []
    slide = deck.slides[index] if index < len(deck.slides) else None
    try:
        W, H = slide_size(deck.size)
    except ValueError:
        W, H = slide_size("16:9")

    def warn(rule: str, msg: str, hint: str, p: Placed | None = None) -> None:
        line = getattr(p.element, "line", None) if p else None
        out.append(Diagnostic(level="warning", message=msg, slide=index + 1, line=line, rule=rule, hint=hint))

    bg = None
    if slide and slide.background and slide.background.startswith("#"):
        bg = _hex(slide.background, theme)
    bg = bg or _hex("bg", theme)

    for i, p in enumerate(items):
        el = p.element
        # off-slide
        if p.x < -_TOL or p.y < -_TOL or p.x + p.w > W + _TOL or p.y + p.h > H + _TOL:
            warn(
                "off-slide",
                f"{_label(p)} extends past the slide edge",
                "check its {x y w h} or remove them",
                p,
            )
        # alt text
        if isinstance(el, (Image, Media)) and not el.alt.strip():
            what = "image" if isinstance(el, Image) else el.kind
            warn("alt", f"{what} {el.src} has no alt text", "write ![what it shows](path)", p)
        paras = getattr(el, "paragraphs", None)
        if not paras or not any(q.plain.strip() for q in paras):
            continue
        size = (p.style.font_size or theme.sizes.get("body", 18)) * p.font_scale
        if size < theme.min_font_size - 0.05:
            warn(
                "tiny-text",
                f"{_label(p)} renders at {size:.1f}pt (< {theme.min_font_size:g}pt)",
                "shorten the text or split the slide",
                p,
            )
        # overflow (text frames only; shapes like chevrons carry short labels)
        if isinstance(el, Text) and p.h > 0:
            pad = 0
            if p.style.padding is not None:
                try:
                    from .units import to_emu

                    pad = to_emu(p.style.padding)
                except ValueError:
                    pad = 0
            need = measure.paragraphs_height(paras, p.w - 2 * pad, p.style, p.font_scale) + 2 * pad
            if need > p.h * _OVERFLOW_TOL + _TOL:
                warn(
                    "overflow",
                    f"{_label(p)} needs {need / EMU_PER_PT:.0f}pt but has {p.h / EMU_PER_PT:.0f}pt",
                    "shorten the text, split the slide, or give the block more room (@ ratios)",
                    p,
                )
        # contrast
        fg = _hex(p.style.color or "fg", theme)
        back = _hex(p.style.fill, theme) if p.style.fill else _backdrop(items, i, bg, theme)
        if fg and back:
            ratio = contrast_ratio(fg, back)
            if ratio < 3.0:
                warn(
                    "contrast",
                    f"{_label(p)} has low contrast {ratio:.1f}:1",
                    "use a darker text color or a lighter fill (need >= 3:1)",
                    p,
                )

    # overlap between items that are not nested in each other
    solid = [p for p in items if not _is_line(p) and not _is_band(p) and p.w > 0 and p.h > 0]
    for a_i, a in enumerate(solid):
        for b in solid[a_i + 1 :]:
            area = _overlap_area(a, b)
            if area <= 0 or _inside(a, b) or _inside(b, a):
                continue
            small = min(a.w * a.h, b.w * b.h)
            if small and area / small > 0.02:
                warn(
                    "overlap",
                    f"{_label(a)} overlaps {_label(b)}",
                    "remove explicit {x y w h} or use an @ grid so blocks do not collide",
                    b,
                )
    for _line, block in _connector_crossings(items):
        warn(
            "connector-crosses",
            f"a connector runs through {_label(block)}",
            "link neighbouring blocks only, or reorder the blocks / use an @ areas grid",
            block,
        )
    return out


def _polyline(p: Placed) -> list[tuple[float, float]]:
    """Points of a connector ``Shape(shape="line")`` from its box, flips and elbow attrs."""
    a = p.element.attrs
    x0, x1 = (p.x + p.w, p.x) if a.get("flip_h") else (p.x, p.x + p.w)
    y0, y1 = (p.y + p.h, p.y) if a.get("flip_v") else (p.y, p.y + p.h)
    if not a.get("elbow"):
        return [(x0, y0), (x1, y1)]
    adj = float(a.get("adj", 0.5))
    if a.get("route") == "h":
        xm = x0 + (x1 - x0) * adj
        return [(x0, y0), (xm, y0), (xm, y1), (x1, y1)]
    ym = y0 + (y1 - y0) * adj
    return [(x0, y0), (x0, ym), (x1, ym), (x1, y1)]


def _seg_hits(u, v, r: tuple[int, int, int, int]) -> bool:
    """Liang-Barsky: does segment u-v enter the open rectangle r = (x, y, w, h)?"""
    x, y, w, h = r
    if w <= 0 or h <= 0:
        return False
    dx, dy = v[0] - u[0], v[1] - u[1]
    t0, t1 = 0.0, 1.0
    for pv, qv in ((-dx, u[0] - x), (dx, x + w - u[0]), (-dy, u[1] - y), (dy, y + h - u[1])):
        if pv == 0:
            if qv <= 0:
                return False
            continue
        t = qv / pv
        if pv < 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 >= t1:
            return False
    return True


def _connector_crossings(items: list[Placed]) -> list[tuple[Placed, Placed]]:
    inset = 3 * _TOL
    blocks = [
        q
        for q in items
        if isinstance(q.element, Container) or (isinstance(q.element, Shape) and q.element.paragraphs)
    ]
    out = []
    for p in items:
        if not (isinstance(p.element, Shape) and p.element.shape == "line"):
            continue
        pts = _polyline(p)
        for q in blocks:
            if _inside(p, q):  # the connector's own parent box (links between a box's children)
                continue
            r = (q.x + inset, q.y + inset, q.w - 2 * inset, q.h - 2 * inset)
            if any(_seg_hits(u, v, r) for u, v in zip(pts, pts[1:], strict=False)):
                out.append((p, q))
                break
    return out


def lint(deck: Deck, placed: list[list[Placed]], theme: Theme) -> list[Diagnostic]:
    """Lint every slide. ``placed[i]`` is the layout output of slide ``i``."""
    out: list[Diagnostic] = []
    for i, items in enumerate(placed):
        try:
            out.extend(lint_slide(items, deck, theme, i))
        except Exception as e:  # the linter must never break a build
            out.append(
                Diagnostic(
                    level="info",
                    message=f"lint skipped: {type(e).__name__}: {e}",
                    slide=i + 1,
                    rule="lint-error",
                    hint="report a bug",
                )
            )
    return out
