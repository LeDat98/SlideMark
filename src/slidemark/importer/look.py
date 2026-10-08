"""A foreign deck's own look -> a compact token header (``colors:`` / ``fonts:`` / ``style:``).

Reads what the slides actually use (explicit sRGB fills, run colors, typefaces, bands) and keeps only the
tokens that differ from the base theme. Never raises: any problem means "no tokens".
"""

from __future__ import annotations

import colorsys
import re
from collections import Counter
from typing import Any

from ..theme import Theme
from .design import token_lines

_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_HEX = re.compile(r"^[0-9A-F]{6}$")


def _rgb(h: str) -> tuple[int, int, int]:
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _dist(a: str, b: str) -> float:
    return sum((x - y) ** 2 for x, y in zip(_rgb(a), _rgb(b), strict=True)) ** 0.5


def _lin(c: float) -> float:
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _lum(h: str) -> float:
    r, g, b = (_lin(c / 255) for c in _rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(a: str, b: str) -> float:
    hi, lo = sorted((_lum(a), _lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _hls(h: str) -> tuple[float, float, float]:
    r, g, b = (c / 255 for c in _rgb(h))
    return colorsys.rgb_to_hls(r, g, b)


def _saturated(h: str) -> bool:
    _, light, sat = _hls(h)
    return sat >= 0.3 and 0.12 <= light <= 0.85


def _top(counter: Counter, tol: float = 10.0) -> list[tuple[str, float]]:
    """Counter merged so colors within ``tol`` count as one (the heaviest spelling represents it)."""
    out: list[list] = []
    for c, n in counter.most_common():
        for e in out:
            if _dist(e[0], c) <= tol:
                e[1] += n
                break
        else:
            out.append([c, n])
    return sorted(((c, n) for c, n in out), key=lambda t: -t[1])


class _Facts:
    def __init__(self) -> None:
        self.bg: Counter = Counter()
        self.text: Counter = Counter()  # run color -> chars
        self.big: Counter = Counter()  # run color of size >= 28pt -> chars
        self.fills: Counter = Counter()  # shape fill -> area share
        self.lines: Counter = Counter()  # outline of a light filled shape -> count
        self.light_fills: Counter = Counter()
        self.th_fill: Counter = Counter()
        self.th_text: Counter = Counter()
        self.bands: list[tuple[int, str]] = []  # (slide, fill) of a full-width strip at the top
        self.radius: list[float] = []
        self.rects = 0
        self.latin: Counter = Counter()
        self.latin_big: Counter = Counter()
        self.ea: Counter = Counter()
        self.slides = 0


def _first(el, path: str) -> Any:
    got = el.xpath(path)
    return got[0] if got else None


def _srgb(el, path: str) -> str | None:
    v = _first(el, path)
    v = str(v).upper() if v is not None else None
    return v if v and _HEX.match(v) else None


def _collect(prs, W: int, H: int) -> _Facts:
    f = _Facts()
    for s in prs.slides:
        f.slides += 1
        el = s._element
        bg = _srgb(el, "./p:cSld/p:bg//a:srgbClr/@val")
        for sp in el.xpath(".//p:sp"):
            fill = _srgb(sp, "./p:spPr/a:solidFill/a:srgbClr/@val")
            ext = _first(sp, "./p:spPr/a:xfrm/a:ext")
            off = _first(sp, "./p:spPr/a:xfrm/a:off")
            w = h = x = y = 0
            if ext is not None:
                w, h = int(ext.get("cx", 0)), int(ext.get("cy", 0))
            if off is not None:
                x, y = int(off.get("x", 0)), int(off.get("y", 0))
            area = w * h / (W * H) if W and H else 0.0
            if fill and area >= 0.9:
                bg = bg or fill
            elif fill and area > 0:
                f.fills[fill] += area
                if x <= 0.03 * W and w >= 0.94 * W and y <= 0.05 * H and 0.04 * H <= h <= 0.2 * H:
                    f.bands.append((f.slides, fill))
                geom = _first(sp, "./p:spPr/a:prstGeom/@prst")
                if area >= 0.004 and geom in ("rect", "roundRect"):
                    if geom == "rect":
                        f.rects += 1
                    else:
                        gd = _first(sp, "./p:spPr/a:prstGeom/a:avLst/a:gd/@fmla")
                        m = re.search(r"val (\d+)", str(gd or ""))
                        a = int(m.group(1)) / 100000 if m else 0.16667
                        if a < 0.4:  # a pill or circle is not a corner radius
                            f.radius.append(a * min(w, h) / 12700)
                if area >= 0.004 and not _saturated(fill) and _hls(fill)[1] > 0.85:
                    f.light_fills[fill] += area
                    ln = _srgb(sp, "./p:spPr/a:ln/a:solidFill/a:srgbClr/@val")
                    if ln:
                        f.lines[ln] += 1
        for r in el.iter(f"{{{_A}}}r"):
            t = "".join(r.xpath("./a:t/text()")).strip()
            if not t:
                continue
            c = _srgb(r, "./a:rPr/a:solidFill/a:srgbClr/@val")
            sz = _first(r, "./a:rPr/@sz")
            size = int(sz) / 100 if sz else 0
            if c:
                f.text[c] += len(t)
                if size >= 28:
                    f.big[c] += len(t)
            lat = _first(r, "./a:rPr/a:latin/@typeface")
            if lat and not str(lat).startswith(("+", "Consolas", "Courier")):
                f.latin[str(lat)] += len(t)
                if size >= 24:
                    f.latin_big[str(lat)] += len(t)
            ea = _first(r, "./a:rPr/a:ea/@typeface")
            if ea and not str(ea).startswith("+"):
                f.ea[str(ea)] += len(t)
        for tbl in el.xpath(".//a:tbl"):
            for tr in tbl.xpath("./a:tr")[:1]:
                for tc in tr.xpath("./a:tc"):
                    c = _srgb(tc, "./a:tcPr/a:solidFill/a:srgbClr/@val")
                    if c:
                        f.th_fill[c] += 1
                    t = _srgb(tc, ".//a:rPr/a:solidFill/a:srgbClr/@val")
                    if t:
                        f.th_text[t] += 1
        f.bg[bg or ""] += 1
    return f


def _tokens(f: _Facts, base: Theme) -> dict[str, str]:
    bc = {k: v.lstrip("#").upper() for k, v in base.colors.items()}
    out: dict[str, str] = {}

    def put(name: str, hexv: str | None) -> None:
        if hexv and _dist(hexv, bc.get(name, "")) > 12 if name in bc else bool(hexv):
            out[f"colors.{name}"] = "#" + hexv

    explicit = _top(Counter({k: v for k, v in f.bg.items() if k}))
    bg = bc["bg"]
    if explicit and explicit[0][1] > 0.5 * f.slides:
        bg = explicit[0][0]
    put("bg", bg)
    # foreground: the most used run color that reads on the background
    texts = _top(Counter({c: n for c, n in f.text.items() if _contrast(c, bg) >= 3.0}))
    fg = bc["fg"] if _contrast(bc["fg"], bg) >= 3.0 else ("FFFFFF" if _lum(bg) < 0.4 else "111111")
    if texts:
        fg = texts[0][0]
    put("fg", fg)
    # accents: saturated fills by area (plus big numbers), by weight; distinct hues only
    weight: Counter = Counter()
    for c, a in f.fills.items():
        if _saturated(c) and _dist(c, bg) > 40:
            weight[c] += a
    for c, n in f.big.items():
        if _saturated(c) and _dist(c, bg) > 40:
            weight[c] += n * 0.0005
    cands = _top(weight)
    chosen: list[str] = []
    for c, n in cands:
        if all(_dist(c, o) > 60 for o in chosen) and (not chosen or n >= 0.12 * cands[0][1]):
            chosen.append(c)
        if len(chosen) == 3:
            break
    for name, c in zip(("primary", "secondary", "accent"), chosen, strict=False):
        put(name, c)
    # muted: a low-saturation text color that reads weaker than the foreground
    for c, _n in texts[1:]:
        if _hls(c)[2] < 0.25 and _dist(c, fg) > 30 and _contrast(c, bg) < _contrast(fg, bg):
            put("muted", c)
            break
    # cards: a light fill that is not the background, and its outline
    lights = _top(Counter({c: a for c, a in f.light_fills.items() if _dist(c, bg) > 6}))
    if lights and lights[0][1] > 0.02:
        put("surface", lights[0][0])
        ln = _top(f.lines)
        if ln and _dist(ln[0][0], bc["border"]) > 12:
            put("border", ln[0][0])
    # title band: a full-width strip at the top of most slides
    n_band = len({s for s, _ in f.bands})
    if n_band >= max(1, 0.4 * f.slides):
        out["title_band"] = "#" + _top(Counter(c for _, c in f.bands))[0][0]
    # table header
    th = _top(f.th_fill)
    if th and _dist(th[0][0], bc["surface"]) > 12:
        out["table_header_fill"] = "#" + th[0][0]
        tt = _top(f.th_text)
        if tt and _dist(tt[0][0], bc["fg"]) > 12:
            out["table_header_color"] = "#" + tt[0][0]
    # corner radius shared by the filled boxes
    if len(f.radius) >= 3 and f.rects < len(f.radius):
        rs = sorted(f.radius)
        r = rs[len(rs) // 2]
        if abs(r - 6) > 2 and r <= 24 and rs[-1] - rs[0] <= 4:  # only when the boxes agree
            out["classes.card.radius"] = str(round(r))
    elif f.rects >= 3 and not f.radius:
        out["classes.card.radius"] = "0"
    # fonts
    body = f.latin.most_common(1)[0][0] if f.latin else None
    head = f.latin_big.most_common(1)[0][0] if f.latin_big else body
    if body and body != base.fonts.body:
        out["fonts.body"] = body
    if head and head != base.fonts.heading:
        out["fonts.heading"] = head
    ea = f.ea.most_common(1)[0][0] if f.ea else None
    if ea and ea != base.fonts.ea and ea != body:
        out["fonts.ea"] = ea
    return out


def _keep_valid(tokens: dict[str, str]) -> dict[str, str]:
    """Drop tokens the theme loader rejects: a bad value must never reach the header."""
    from ..parser import parse
    from ..template import deck_theme

    keep: dict[str, str] = {}
    for k, v in tokens.items():
        deck = parse("\n".join(token_lines({k: v})) + "\n\n# t\n")
        _theme, diags = deck_theme(deck, ".")
        if not [d for d in [*deck.diagnostics, *diags] if d.rule in ("bad-token", "unknown-token")]:
            keep[k] = v
    return keep


def derive_tokens(prs, base: Theme) -> dict[str, str]:
    """Token path -> value of the look the slides use, where it differs from ``base``; {} on any problem."""
    try:
        f = _collect(prs, int(prs.slide_width), int(prs.slide_height))
        return _keep_valid(_tokens(f, base)) if f.slides else {}
    except Exception:
        return {}


def look_lines(tokens: dict[str, str]) -> list[str]:
    """``colors:`` / ``fonts:`` / ``style:`` header lines (at most 3) for derived tokens."""
    return token_lines(tokens)


# --------------------------------------------------------------------------- color score


def _bg_of(slide) -> str:
    for part in (slide, slide.slide_layout, slide.slide_layout.slide_master):
        hit = part._element.xpath("./p:cSld/p:bg//a:srgbClr/@val")
        if hit:
            return str(hit[0]).upper()
    return "FFFFFF"


def color_facts(prs) -> list[dict]:
    """Per slide: effective bg, run colors weighted by characters, shape fills weighted by area."""
    W, H = int(prs.slide_width), int(prs.slide_height)
    out = []
    for s in prs.slides:
        el = s._element
        text: Counter = Counter()
        for r in el.iter(f"{{{_A}}}r"):
            t = "".join(r.xpath("./a:t/text()")).strip()
            c = _srgb(r, "./a:rPr/a:solidFill/a:srgbClr/@val")
            if t and c:
                text[c] += len(t)
        fills: Counter = Counter()
        for sp in el.xpath(".//p:sp"):
            c = _srgb(sp, "./p:spPr/a:solidFill/a:srgbClr/@val")
            ext = _first(sp, "./p:spPr/a:xfrm/a:ext")
            if c and ext is not None:
                area = int(ext.get("cx", 0)) * int(ext.get("cy", 0)) / (W * H)
                if area < 0.9:  # a full-slide rectangle is the background
                    fills[c] += area
        out.append({"bg": _bg_of(s), "text": text, "fills": fills})
    return out


def _intersect(a: Counter, b: Counter, tol: float = 18.0) -> float | None:
    """Histogram intersection of two color histograms; colors within ``tol`` (RGB distance) are equal."""
    ta, tb = sum(a.values()), sum(b.values())
    if not ta:
        return None
    if not tb:
        return 0.0
    left = dict(b)
    got = 0.0
    for c, n in sorted(a.items(), key=lambda kv: -kv[1]):
        for d in sorted(left, key=lambda d: _dist(c, d)):
            if _dist(c, d) <= tol:
                take = min(n / ta, left[d] / tb)
                got += take
                left[d] -= take * tb
                if left[d] <= 1e-9:
                    del left[d]
                break
    return got


def color_similarity(original, rebuilt) -> float:
    """Mean over slides of (background match, text-color overlap, fill-color overlap); two Presentations."""
    a, b = color_facts(original), color_facts(rebuilt)
    vals = []
    for i, fa in enumerate(a):
        fb = b[i] if i < len(b) else {"bg": "000000", "text": Counter(), "fills": Counter()}
        parts = [1.0 if _dist(fa["bg"], fb["bg"]) <= 18 else 0.0]
        for k in ("text", "fills"):
            v = _intersect(fa[k], fb[k])
            if v is not None:
                parts.append(v)
        vals.append(sum(parts) / len(parts))
    return sum(vals) / len(vals) if vals else 1.0
