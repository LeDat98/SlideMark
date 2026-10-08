"""Composition vocabulary, wave 2026-10-08 lane B: ``@stairs`` ``@nested`` ``@flow disc``.

Same contract as ``vocab.py`` (which dispatches here): a composer works on the body rectangle with its own
context, names every shape (``Stairs 2``, ``Nested 1`` / ``Nested 1 text`` / ``Nested 1 list``,
``Flow 2 disc`` / ``Flow 2 line`` / ``Flow 2 text``) so ``importer/vocab.py`` folds them back, reads every
number from a token (``forms4.py``) and never raises on bad input (the parser warned; a slide that lacks what
the form needs is laid out as ordinary blocks).
"""

from __future__ import annotations

import math
from typing import Any

from .. import forms
from ..ir import Paragraph, Run, Shape, Slide, fast_style
from ..units import EMU_PER_PT
from . import vocab as V
from .grid import Rect

_UNIT = 0.04 * 914400  # a step of the disc-size search (EMU)


def _tints(c, color: str, n: int, lo: float) -> list[str]:
    """``n`` tints of ``color`` from ``lo`` (light) to 1.0 (the colour itself), in order."""
    E = V._eng()
    out = []
    for i in range(n):
        t = lo + (1.0 - lo) * (i / max(n - 1, 1))
        out.append(E._tint(c.theme, color, t) or color)
    return out


def _card_radius(c) -> Any:
    card = c.theme.classes.get("card")
    return card.radius if card is not None and card.radius is not None else None


# --------------------------------------------------------------------------- @stairs


def _stairs(c, slide: Slide, body: Rect, sg: int, info: dict) -> bool:
    th = c.theme
    bx = forms.boxes(slide) or []
    n = len(bx)
    up = forms.words(slide.attrs, "stairs", "dir") == "up"
    base, _ratio, hi, lo, pinned = V._sizes(c, slide)
    gap = V._emu(th.stairs_gap) if th.stairs_gap else sg
    ws = V._weights(c, slide, n, "stairs") or [1.0] * n
    cols = V._split(body.w, ws, gap)
    if th.stairs_step:  # the step is stated: the highest card still reaches the body top
        step = V._emu(th.stairs_step)
        low = max(body.h - (n - 1) * step, round(0.2 * body.h))
    else:
        low = round(th.stairs_low * body.h)
    step = (body.h - low) / max(n - 1, 1)
    levels = [round(low + k * step) for k in range(n)]  # lowest first
    heights = levels if up else levels[::-1]
    pad_pt = th.stairs_pad_ratio * max(base, lo)
    pad = round(pad_pt * EMU_PER_PT)
    parts = [V._split_box(b) for b in bx]
    fills = V._colors(slide, th.stairs_fill)
    default = _tints(c, "primary", n, th.stairs_tint)
    radius = _card_radius(c)

    def paras_of(i: int, s: float) -> list[Paragraph]:
        h, bd = parts[i]
        return V._paras(h, bd, s, 1.0, None)

    def fits(s: float) -> bool:
        st = V._text_style(c, s)
        return all(
            V._need(c, paras_of(i, s), max(cols[i][1] - 2 * pad, 1), st) <= max(heights[i] - 2 * pad, 1)
            for i in range(n)
        )

    size, fit = V._largest(hi, lo, fits) if not pinned else (hi, fits(hi))
    for i, ((off, w), h_i) in enumerate(zip(cols, heights, strict=True)):
        fill = V._own(bx[i], "fill") or V._pick(fills, i) or default[i]
        ink = V._own(bx[i], "color") or th.stairs_color or th.ink_on(fill, "fg")
        st = V._text_style(
            c,
            size,
            fill=fill,
            color=ink,
            radius=radius,
            padding=f"{pad_pt:.2f}pt",
            align="left",
            valign="top",
        )
        V._emit_text(
            c, f"Stairs {i + 1}", paras_of(i, size), Rect(body.x + off, body.bottom - h_i, w, h_i), st
        )
    info.update(n=n, dir="up" if up else "down", size=size, fit=fit, step=_pt_of(step))
    if not fit:
        c.over.append("@stairs text")
    return True


def _pt_of(emu: float) -> float:
    return round(emu / EMU_PER_PT, 1)


# --------------------------------------------------------------------------- @nested


def _nested(c, slide: Slide, body: Rect, sg: int, info: dict) -> bool:
    th, lt = c.theme, c.lt
    E = V._eng()
    bx = forms.boxes(slide) or []
    n = len(bx)
    left = forms.words(slide.attrs, "nested", "side") == "left"
    base, ratio, hi, lo, pinned = V._sizes(c, slide)
    parts = [V._split_box(b) for b in bx]
    icons_ = [E._icon_name(b) for b in bx]
    ring_w = round(body.w * th.nested_share)
    gutter = max(sg * 2, 1)
    list_w = max(body.w - ring_w - gutter, 1)
    ring_x = body.x if left else body.right - ring_w
    list_x = body.x + ring_w + gutter if left else body.x
    dia = min(ring_w, body.h)
    cx, cy = ring_x + ring_w // 2, body.y + body.h // 2
    diams = [dia * (1 - (1 - th.nested_core) * i / max(n - 1, 1)) for i in range(n)]
    band = dia * (1 - th.nested_core) / (2 * max(n - 1, 1))  # ring thickness: room for a heading
    fills = V._colors(slide, th.nested_fill)
    default = _tints(c, "secondary", n, th.nested_tint)
    ring_fill = [V._own(bx[i], "fill") or V._pick(fills, i) or default[i] for i in range(n)]
    ring_ink = [V._own(bx[i], "color") or th.nested_color or th.ink_on(ring_fill[i], "fg") for i in range(n)]
    heads = [p[0] for p in parts]

    def head_rect(i: int) -> Rect:
        r = diams[i] / 2
        if i == n - 1:  # the innermost disc holds its heading in the middle (the inscribed square)
            side = round(diams[i] * lt.cycle_node_inner)
            return Rect(round(cx - side / 2), round(cy - side / 2), side, side)
        depth = band * 0.94
        chord = 2 * math.sqrt(max(r * r - (r - depth) ** 2, 0.0)) * 0.92
        return Rect(round(cx - chord / 2), round(cy - r + band * 0.06), round(chord), round(band * 0.88))

    def head_paras(i: int, s: float) -> list[Paragraph]:
        h = heads[i]
        if h is None:
            return []
        st = fast_style(font_size=s, bold=True)
        return [p.model_copy(update={"style": st.merged(p.style)}) for p in h.paragraphs]

    def head_ok(s: float) -> bool:
        st = V._text_style(c, s, bold=True)
        for i in range(n):
            ps = head_paras(i, s)
            if not ps:
                continue
            r = head_rect(i)
            if V._word_em(heads[i]) * s * EMU_PER_PT > r.w or V._need(c, ps, r.w, st) > r.h:
                return False
        return True

    top_pt = min(hi * ratio, band / EMU_PER_PT * 0.7) if not pinned else hi
    hsize = th.nested_size or None
    if hsize:
        hfit = head_ok(hsize)
    else:
        hsize, hfit = V._largest(max(top_pt, lo), lo, head_ok)
    # rings: largest first, so the smaller ones are drawn over it
    line = th.nested_line
    lw = V._pt(V._emu(th.nested_line_w))
    for i in range(n):
        d = round(diams[i])
        c.emit(
            Shape(shape="ellipse", attrs={"shape_name": f"Nested {i + 1}"}),
            Rect(round(cx - d / 2), round(cy - d / 2), d, d),
            fast_style(fill=ring_fill[i], line=line, **({"line_width": lw} if line else {})),
        )
    for i in range(n):
        ps = head_paras(i, hsize)
        if ps:
            V._emit_text(
                c,
                f"Nested {i + 1} text",
                ps,
                head_rect(i),
                V._text_style(c, hsize, bold=True, color=ring_ink[i], align="center", valign="middle"),
            )
    # the bodies as an icon list on the other half
    lratio = th.nested_text_ratio
    show_title = th.nested_list_title
    row = body.h // n
    isz_k = th.nested_icon_ratio

    def item_paras(i: int, s: float) -> list[Paragraph]:
        h, bd = parts[i]
        out: list[Paragraph] = []
        if show_title and h is not None:
            st = fast_style(font_size=s, bold=True)
            out += [p.model_copy(update={"style": st.merged(p.style)}) for p in h.paragraphs]
        bs = fast_style(font_size=round(s * lratio, 2))
        out += [p.model_copy(update={"style": bs.merged(p.style)}) for t in bd for p in t.paragraphs]
        return out

    def geom(s: float) -> tuple[int, int, int]:
        isz = round(isz_k * s * EMU_PER_PT) if any(icons_) else 0
        gi = round(0.45 * isz)
        return isz, gi, max(list_w - isz - gi, 1)

    def list_ok(s: float) -> bool:
        _isz, _gi, tw = geom(s)
        st = V._text_style(c, s)
        return all(V._need(c, item_paras(i, s), tw, st) <= row * lt.vocab_fill for i in range(n))

    lsize, lfit = V._largest(hi, lo, list_ok) if not pinned else (hi, list_ok(hi))
    isz, gi, tw = geom(lsize)
    for i in range(n):
        y = body.y + i * row
        tx = list_x + isz + gi
        V._emit_text(
            c,
            f"Nested {i + 1} list",
            item_paras(i, lsize),
            Rect(tx, y, tw, row),
            V._text_style(c, lsize, align="left", valign="middle"),
        )
        if icons_[i]:
            c.emit(
                Shape(
                    shape="icon",
                    classes=["iconlist-icon", "nested-icon"],
                    attrs={"icon": icons_[i], "shape_name": f"Nested {i + 1} icon"},
                ),
                Rect(list_x, y + (row - isz) // 2, isz, isz),
                fast_style(fill=th.iconlist_icon_color or "primary", line=None),
            )
    info.update(n=n, side="left" if left else "right", size=lsize, head=hsize, fit=hfit and lfit)
    if not (hfit and lfit):
        c.over.append("@nested text")
    return True


# --------------------------------------------------------------------------- @flow disc


def _flowdisc(c, slide: Slide, body: Rect, sg: int, info: dict) -> bool:
    th, lt = c.theme, c.lt
    E = V._eng()
    bx = forms.boxes(slide) or []
    parts = [V._split_box(b) for b in bx]
    icons_ = [E._icon_name(b) for b in bx]
    above = ("above" in bx[0].classes or str(slide.attrs.get("above", "")).lower() in ("1", "on")) and len(
        bx
    ) >= 3
    row_ix = list(range(1, len(bx))) if above else list(range(len(bx)))
    m = len(row_ix)
    base, ratio, hi, lo, pinned = V._sizes(c, slide)
    gap = max(sg, 1)
    col_w = (body.w - gap * (m - 1)) // m
    fills = V._colors(slide, th.flow_disc_fill)
    line_col = th.flow_line
    line_w = V._pt(V._emu(th.flow_line_w))
    stem = round(0.3 * 914400)

    def paras_of(i: int, s: float) -> list[Paragraph]:
        h, bd = parts[i]
        return V._paras(h, bd, s, 1.0, None)

    def text_h(s: float) -> int:
        st = V._text_style(c, s)
        idx = row_ix if not above else [*row_ix]
        return max((round(V._need(c, paras_of(i, s), col_w, st)) for i in idx), default=0)

    # disc size: asked, else a share of the room; the text under it never loses its place
    def pick(s: float) -> tuple[int, bool]:
        d_ask = (
            V._emu(th.flow_disc_size)
            if th.flow_disc_size
            else round(min(col_w * 0.6, th.flow_disc_ratio * body.h))
        )
        d = d_ask
        extra = (d + stem) if above else 0  # the side node and its stem take a band above the row
        while d > _UNIT * 4:
            extra = (d + stem) if above else 0
            if d + gap + text_h(s) + extra <= body.h * lt.vocab_fill or th.flow_disc_size:
                return d, True
            d -= round(_UNIT)
        return d, False

    size, fit = hi, False
    for size in [hi] if pinned else _steps(hi, lo):
        d, fit = pick(size)
        if fit:
            break
    d, _ok = pick(size)
    total = d + gap + text_h(size) + ((d + stem) if above else 0)
    y0 = body.y + max(round((body.h - total) * lt.vocab_top), 0)
    row_y = y0 + ((d + stem) if above else 0)
    cx = [body.x + k * (col_w + gap) + col_w // 2 for k in range(m)]
    # lines first (behind the discs)
    for k in range(m - 1):
        x0 = cx[k] + d // 2 + round(0.08 * 914400)
        x1 = cx[k + 1] - d // 2 - round(0.08 * 914400)
        if x1 > x0:
            V._line(
                c,
                f"Flow {row_ix[k] + 1} line",
                x0,
                row_y + d // 2,
                x1,
                row_y + d // 2,
                line_col,
                line_w,
                "arrow",
            )
    ink_pref = "bg"

    def disc(i: int, k: int, x: int, y: int) -> None:
        fill = V._own(bx[i], "fill") or V._pick(fills, k, "primary") or "primary"
        ink = V._own(bx[i], "color") or th.flow_disc_color or th.ink_on(fill, ink_pref)
        paras: list[Paragraph] = []
        if not icons_[i]:  # no glyph: the step number
            paras = [Paragraph(runs=[Run(text=str(i + 1), bold=True)])]
        c.emit(
            Shape(shape="ellipse", paragraphs=paras, attrs={"shape_name": f"Flow {i + 1} disc"}),
            Rect(x - d // 2, y, d, d),
            fast_style(
                fill=fill,
                line=None,
                font=th.fonts.heading,
                font_ea=th.fonts.ea,
                font_size=round(d / EMU_PER_PT * 0.42, 1),
                bold=True,
                color=ink,
                align="center",
                valign="middle",
                padding="0pt",
            ),
        )
        if icons_[i]:
            isz = round(d * th.cycle_icon_ratio * 1.1)
            c.emit(
                Shape(shape="icon", attrs={"icon": icons_[i], "shape_name": f"Flow {i + 1} icon"}),
                Rect(x - isz // 2, y + (d - isz) // 2, isz, isz),
                fast_style(fill=ink, line=None),
            )

    for k, i in enumerate(row_ix):
        disc(i, k, cx[k], row_y)
        V._emit_text(
            c,
            f"Flow {i + 1} text",
            paras_of(i, size),
            Rect(cx[k] - col_w // 2, row_y + d + gap, col_w, max(body.bottom - (row_y + d + gap), 1)),
            V._text_style(c, size, align="center", valign="top"),
        )
    if above:  # the side node: a disc above the second step, joined to it by a vertical line
        k = 1 if m > 1 else 0
        x = cx[k]
        disc(0, 0, x, y0)
        V._line(c, "Flow 1 line", x, y0 + d, x, row_y, line_col, line_w, "none")
        side = x + d // 2 + gap
        V._emit_text(
            c,
            "Flow 1 text",
            paras_of(0, size),
            Rect(side, y0, max(body.right - side, 1), d),
            V._text_style(c, size, align="left", valign="middle"),
        )
    info.update(n=len(bx), above=above, size=size, disc=_pt_of(d), fit=fit)
    if not fit:
        c.over.append("@flow disc text")
    return True


def _steps(hi: float, lo: float) -> list[float]:
    out, s = [], hi
    while s >= lo - 1e-9:
        out.append(s)
        s -= V._STEP
    return out or [lo]


FORMS = {"stairs": _stairs, "nested": _nested, "flowdisc": _flowdisc}
