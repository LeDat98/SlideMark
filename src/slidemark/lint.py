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

import re

from .ir import Container, Deck, Diagnostic, Image, Media, Placed, Shape, Text
from .layout import css, measure
from .theme import Theme
from .units import EMU_PER_PT, slide_size

_TOL = int(EMU_PER_PT)  # 1pt slack for rounding
_OVERFLOW_TOL = 1.08  # measurement is an estimate: report only clear overflows


RGB = tuple[float, float, float]
_GRADIENT = re.compile(r"^\s*(?:repeating-)?(?:linear|radial)-gradient\(", re.I)
_RGBFN = re.compile(r"rgba?\(\s*([\d.]+%?)[\s,]+([\d.]+%?)[\s,]+([\d.]+%?)(?:[\s,/]+([\d.]+%?))?\s*\)", re.I)


def _rgba(color: str | None, theme: Theme) -> tuple[RGB, float] | None:
    """(rgb 0..1, alpha) of a theme color name, #hex (3-8 digits) or rgb()/rgba(); None if unknown."""
    c = (theme.color(color) if color else None) or ""
    c = c.strip()
    try:
        if c.startswith("#"):
            h = c[1:]
            if len(h) in (3, 4):
                h = "".join(ch * 2 for ch in h)
            if len(h) not in (6, 8):
                return None
            rgb = tuple(int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))
            return rgb, (int(h[6:8], 16) / 255 if len(h) == 8 else 1.0)  # type: ignore[return-value]
        if m := _RGBFN.fullmatch(c):

            def ch(v: str) -> float:
                return min(max(float(v[:-1]) * 2.55 if v.endswith("%") else float(v), 0), 255) / 255

            a = m.group(4)
            alpha = (float(a[:-1]) / 100 if a.endswith("%") else float(a)) if a else 1.0
            return (ch(m.group(1)), ch(m.group(2)), ch(m.group(3))), min(max(alpha, 0.0), 1.0)
    except ValueError:
        return None
    return None


def _hex(color: str | None, theme: Theme) -> RGB | None:
    got = _rgba(color, theme)
    return got[0] if got else None


def _top_commas(text: str) -> list[str]:
    out, depth, cur = [], 0, []
    for ch in text:
        depth += (ch == "(") - (ch == ")")
        if ch == "," and depth == 0:
            out.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    out.append("".join(cur).strip())
    return [p for p in out if p]


def _blend(top: tuple[RGB, float], behind: RGB | None) -> RGB:
    rgb, a = top
    if a >= 1.0 or behind is None:
        return rgb
    return tuple(r * a + b * (1 - a) for r, b in zip(rgb, behind, strict=True))  # type: ignore[return-value]


def _backs(fill: str | None, theme: Theme, behind: RGB | None) -> list[RGB]:
    """Colors a fill puts behind text: one for a solid color, one per gradient stop (alpha blended over
    ``behind``). Empty when it cannot be judged (an image, an unknown value) or the fill is transparent."""
    if not fill:
        return []
    if _GRADIENT.match(fill):
        inner = fill.strip()[fill.index("(") + 1 :].rstrip().removesuffix(")")
        stops = []
        for part in _top_commas(inner):
            if re.match(
                r"^(-?[\d.]+(deg|rad|turn|grad)|to\s|circle|ellipse|closest|farthest|at\s)", part, re.I
            ):
                continue
            got = _rgba(re.sub(r"\s+-?[\d.]+(%|px|pt)$", "", part), theme)
            if got:
                stops.append(_blend(got, behind))
        return stops
    got = _rgba(fill, theme)
    if got is None or got[1] <= 0:
        return []
    return [_blend(got, behind)]


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


def _is_image(fill: str | None, theme: Theme) -> bool:
    """A fill that is neither a color nor a gradient (``url(...)``, a picture path): not judgeable."""
    return bool(fill) and not _GRADIENT.match(fill or "") and _rgba(fill, theme) is None


def _backdrop(items: list[Placed], i: int, bg: list[RGB], theme: Theme) -> list[RGB]:
    """Colors directly behind item ``i``: the topmost earlier filled item containing its center (a gradient
    gives one color per stop), else the slide background."""
    p = items[i]
    cx, cy = p.x + p.w // 2, p.y + p.h // 2
    for q in reversed(items[:i]):
        if q.style.fill and q.x <= cx <= q.x + q.w and q.y <= cy <= q.y + q.h:
            if _is_image(q.style.fill, theme):
                return []  # a picture behind the text: no verdict
            got = _backs(q.style.fill, theme, bg[0] if bg else None)
            if got:
                return got
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

    base = _hex("bg", theme)
    bg: list[RGB] = []
    if slide:
        fill = slide.background or css.slide_style(deck, slide, index).fill
        bg = _backs(fill, theme, base)
        if _is_image(fill, theme):
            base = None  # a picture background: no verdict for text straight on it
    if not bg and base:
        bg = [base]

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
        if isinstance(el, Text) and p.h > 0 and el.attrs.get("measured") != "html":  # Chromium measured it
            ph, pv = css.inset_hv(p.style)
            need = (
                measure.paragraphs_height(paras, p.w - ph, p.style, p.font_scale, gap=measure.element_gap(el))
                + pv
            )
            if need > p.h * _OVERFLOW_TOL + _TOL:
                warn(
                    "overflow",
                    f"{_label(p)} needs {need / EMU_PER_PT:.0f}pt but has {p.h / EMU_PER_PT:.0f}pt",
                    "shorten the text, split the slide, or give the block more room (@ ratios)",
                    p,
                )
        # contrast
        # Judged on the actual merged colors (CSS included). A gradient is checked against every stop and
        # reported only when the text fails on all of them or on their average; custom colors are never odd.
        fg_c = _rgba(p.style.color or "fg", theme)
        backdrop = _backdrop(items, i, bg, theme)
        backs = _backs(p.style.fill, theme, backdrop[0] if backdrop else None) or backdrop
        if _is_image(p.style.fill, theme):
            backs = []  # a picture fill cannot be judged
        if fg_c and backs:
            alpha = fg_c[1] * (p.style.opacity if p.style.fill is None and p.style.opacity is not None else 1)
            ratios = [contrast_ratio(_blend((fg_c[0], alpha), b), b) for b in backs]
            ratio = min(ratios)
            bad = all(r < 3.0 for r in ratios)
            if len(backs) > 1:
                mean = tuple(sum(b[k] for b in backs) / len(backs) for k in range(3))
                ratio = contrast_ratio(_blend((fg_c[0], alpha), mean), mean)  # type: ignore[arg-type]
                bad = bad or ratio < 3.0
            if bad:
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
    measure.set_tokens(theme.layout)
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
