"""Composition vocabulary (DL3b): ``@timeline @vs @matrix @funnel @pyramid @cycle @agenda @statement``.

Each form is one slide directive (``@timeline dir=v marks=num``) with secondary attributes (``dir=``
``marks=`` ``x=`` ``y=`` ``size=`` ``fill=`` ``gap=`` ``align=`` ``valign=``, see ``forms.py``); looks are
theme tokens (``timeline.dot``, ``vs.badge.fill``, ``funnel.fill`` ...). The composer runs like ``@rows``: on
the body rectangle, on its own context, after the slide was copied by the chevron / items rewrites, so the
parsed IR the importer and ``honour`` read stays as written. Every shape has a name (``Timeline 2 dot``,
``Funnel 1``, ``Cycle 3 arrow``) that ``importer/vocab.py`` folds back into the source. ``compose`` returns
``None`` when the slide does not hold what the form needs (the parser warned): the slide is then laid out as
ordinary blocks.

Never raises: bad values were reported by the parser; the layout reads defaults.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable
from typing import Any

from .. import forms
from ..ir import Container, Paragraph, Run, Shape, Slide, Style, Text, fast_style
from ..units import EMU_PER_PT
from . import css, measure
from .grid import Rect

_RATIO = re.compile(r"^\d+(?:\.\d+)?(?::\d+(?:\.\d+)?)+$")
_STEP = 0.5  # pt granularity of the size search


# --------------------------------------------------------------------------- shared helpers


def _eng():
    from . import engine

    return engine


def _new_ctx(ctx, slide: Slide, **kw):
    E = _eng()
    return E._Ctx(
        ctx.deck,
        ctx.theme,
        slide,
        ctx.index,
        ctx.W,
        ctx.H,
        dense_k=ctx.dense_k,
        tight=ctx.tight,
        css=ctx.css,
        **kw,
    )


def _emu(v) -> int:
    return _eng()._emu(v)


def _weights(c, slide: Slide, k: int, form: str) -> list[float] | None:
    """Column / row ratios of the ``@`` line (``@1:2:1 timeline``): ``k`` numbers, else ``None`` (equal)."""
    g = slide.grid
    if not g or g.isdigit() or re.fullmatch(r"\d+x\d+", g):
        return None
    if _RATIO.match(g) and len(g.split(":")) == k:
        return [float(x) for x in g.split(":")]
    c.diag(
        "form-grid",
        f"@{form} takes {k} ratios (e.g. @{':'.join('1' * k)}), not '{g}': equal parts are used",
        f"write @{':'.join('1' * k)} or drop the grid token",
    )
    return None


def _split(total: int, weights: list[float], gap: int = 0) -> list[tuple[int, int]]:
    """``(offset, size)`` of parts of ``total`` (EMU) with ``weights`` and ``gap`` between them."""
    room = max(total - gap * (len(weights) - 1), 0)
    s = sum(weights) or 1.0
    out, pos = [], 0
    for i, w in enumerate(weights):
        size = round(room * w / s) if i < len(weights) - 1 else room - pos
        out.append((pos + gap * i, size))
        pos += size
    return out


def _colors(slide: Slide, token: str | None) -> list[str]:
    """``fill=a,b,c`` of the slide, else the token's list (``funnel.fill``)."""
    raw = slide.attrs.get("fill") or token or ""
    return [x.strip() for x in str(raw).split(",") if x.strip()]


def _pick(cols: list[str], i: int, default: str | None = None) -> str | None:
    return cols[i % len(cols)] if cols else default


def _largest(hi: float, lo: float, ok: Callable[[float], bool]) -> tuple[float, bool]:
    """The largest size in ``[lo, hi]`` (steps of ``_STEP``) where ``ok`` holds; ``(lo, False)`` if none."""
    s = hi
    while s >= lo - 1e-9:
        if ok(s):
            return s, True
        s -= _STEP
    return lo, False


def _need(c, paras: list[Paragraph], width: int, st: Style) -> float:
    """Height (EMU) of ``paras`` in ``width`` with the text style ``st`` (insets included)."""
    ph, pv = css.inset_hv(st)
    return measure.paragraphs_height(paras, max(width - ph, 1), st) + pv


def _sizes(c, slide: Slide) -> tuple[float, float, float, float, bool]:
    """``(body pt, heading / body ratio, hi, lo, pinned)``: the text size range of a form."""
    th = c.theme
    body = th.sizes.get("body", 18) * c.dense_k
    head = th.sizes.get("heading", 20)
    ratio = max(head / max(th.sizes.get("body", 18), 1), 1.0)
    pin = forms.num(slide.attrs, "size")
    if pin:
        return pin, ratio, pin, pin, True
    return body, ratio, body * c.lt.vocab_grow, min(th.min_font_size, body), False


def _text_style(c, size: float, **kw) -> Style:
    E = _eng()
    return E._role_style(c, "body").merged(fast_style(font_size=size, **{"padding": "0pt", **kw}))


def _paras(
    head: Text | None, body: list[Text], size: float, ratio: float, head_color: str | None
) -> list[Paragraph]:
    """A milestone / stage text: the heading (bold, ``ratio`` x size, ``head_color``) and the body."""
    out: list[Paragraph] = []
    if head is not None:
        st = fast_style(font_size=size * ratio, bold=True, **({"color": head_color} if head_color else {}))
        out += [p.model_copy(update={"style": st.merged(p.style)}) for p in head.paragraphs]
    for t in body:
        out += list(t.paragraphs)
    return out


def _word_em(h: Text | None) -> float:
    """Width (em, bold) of the longest word of a heading; a CJK run counts half its length (it may break).
    The orphan control (the last two words of a 3-word line share a no-break space) counts as one word."""
    if h is None:
        return 0.0
    best = 0.0
    for p in h.paragraphs:
        text = "".join(measure.bound_texts(p.runs))
        for tok in re.split(r"[ \t\n\v\r]+", text):
            em = (len(tok) + 1) / 2 if measure.has_cjk(tok) else measure.text_em(tok, bold=True)
            best = max(best, em)
    return best


def _own(el, field: str):
    """A value the author wrote on ``el`` itself (``## a {fill=#EEE color=primary}``), else ``None``."""
    st = getattr(el, "style", None)
    return getattr(st, field, None) if st is not None else None


def _split_box(box: Container) -> tuple[Text | None, list[Text]]:
    return box.title, [ch for ch in box.children if isinstance(ch, Text) and ch.paragraphs]


def _emit_text(
    c, name: str, paras: list[Paragraph], rect: Rect, st: Style, classes: list[str] | None = None
) -> None:
    c.emit(
        Text(role="body", paragraphs=paras, classes=classes or [], attrs={"shape_name": name}),
        rect,
        st,
    )


def _line(
    c, name: str, x0: int, y0: int, x1: int, y1: int, color: str, width_pt: float, head: str = "none"
) -> None:
    """A straight line (native connector) from ``(x0, y0)`` to ``(x1, y1)``; ``head=arrow`` draws the tip."""
    left, top = min(x0, x1), min(y0, y1)
    c.emit(
        Shape(
            shape="line",
            attrs={"head": head, "flip_h": x1 < x0, "flip_v": y1 < y0, "shape_name": name},
        ),
        Rect(left, top, abs(x1 - x0), abs(y1 - y0)),
        fast_style(line=color, line_width=width_pt),
    )


def _pt(emu: int) -> float:
    return round(emu / EMU_PER_PT, 2)


def _block_top(body: Rect, used: int, share: float) -> int:
    """Top of a block of height ``used`` in ``body``: ``share`` of the leftover above it."""
    return body.y + round(max(body.h - used, 0) * share)


def _inherit(c, slide: Slide) -> Style:
    E = _eng()
    inherit = fast_style()
    for n in slide.classes:
        if n in c.theme.classes:
            inherit = inherit.merged(E._only_inheritable(c.theme.classes[n]))
    return inherit.merged(E._only_inheritable(c.css.own(slide)))


def _ink(c, fill: str | None, prefer: str | None, size: float | None = None) -> str:
    return c.theme.ink_on(fill, prefer or "bg")


# --------------------------------------------------------------------------- entry


def compose(ctx, slide: Slide, body: Rect, sg: int) -> tuple[Any, dict] | None:
    """``(context holding the placed items, fit facts)`` of the slide's form, or ``None`` (not a form slide,
    or it lacks what the form needs). Never raises."""
    form = forms.form_of(slide)
    if form is None or slide.layout in ("cover", "section", "blank", "center", "free"):
        return None
    if forms.fits(form, slide) is not None or body.w <= 0 or body.h <= 0:
        return None
    c = _new_ctx(ctx, slide)
    info: dict[str, Any] = {"form": form}
    try:
        ok = _FORMS[form](c, slide, body, sg, info)
    except Exception as e:  # never raise on user input: the slide is laid out as ordinary blocks
        ctx.diag(
            "form-error",
            f"@{form} could not be composed ({type(e).__name__})",
            "the slide is laid out as ordinary blocks; report a bug with this slide",
        )
        return None
    info.setdefault("base", forms.num(slide.attrs, "size") or ctx.theme.sizes.get("body", 18) * ctx.dense_k)
    return (c, info) if ok else None


# --------------------------------------------------------------------------- @timeline


def _timeline(c, slide: Slide, body: Rect, sg: int, info: dict) -> bool:
    th, lt = c.theme, c.lt
    bx = forms.boxes(slide) or []
    n = len(bx)
    horiz = forms.words(slide.attrs, "timeline", "dir") == "h"
    marks = forms.words(slide.attrs, "timeline", "marks")
    base, ratio, hi, lo, pinned = _sizes(c, slide)
    dot_d = round(_emu(th.timeline_dot_size) * (lt.timeline_num_ratio if marks == "num" else 1.0))
    stem = _emu(lt.timeline_stem)
    line_w = _pt(_emu(th.timeline_line_w))
    fills = _colors(slide, th.timeline_dot)
    head_col = th.legible(th.timeline_date_color or "primary")
    now_col = th.legible(th.timeline_now)
    parts = [_split_box(b) for b in bx]
    now = ["accent" in b.classes for b in bx]
    ws = _weights(c, slide, n, "timeline") or [1.0] * n
    info.update(n=n, dir="h" if horiz else "v", marks=marks)

    if horiz:
        slots = _split(body.w, ws)
        axis_y = body.y + body.h // 2
        half = body.h // 2 - dot_d // 2 - stem
        rects = []
        for off, w in slots:
            cx = body.x + off + w // 2
            # centred on its dot, never wider than twice the room to the nearer edge (so no text is clamped
            # into its neighbour on the same side)
            tw = min(
                round(w * 1.9), round(lt.timeline_text_w * body.w), 2 * (cx - body.x), 2 * (body.right - cx)
            )
            rects.append((cx, Rect(cx - tw // 2, 0, tw, half)))

        def ok(s: float) -> bool:
            st = _text_style(c, s)
            return all(
                _need(c, _paras(h, bd, s, ratio, head_col), r.w, st) <= half * lt.vocab_fill
                for (h, bd), (_cx, r) in zip(parts, rects, strict=True)
            )

        size, fit = _largest(hi, lo, ok)
        lw_emu = _emu(th.timeline_line_w)
        _axis(c, Rect(body.x, axis_y - lw_emu // 2, body.w, lw_emu), th.timeline_line)
        for i, ((h, bd), (cx, r)) in enumerate(zip(parts, rects, strict=True)):
            above = i % 2 == 0
            y = axis_y - dot_d // 2 - stem - half if above else axis_y + dot_d // 2 + stem
            col = _own(bx[i], "color") or (now_col if now[i] else head_col)
            name = f"Timeline {i + 1}" + (" now" if now[i] else "")
            _emit_text(
                c,
                name,
                _paras(h, bd, size, ratio, col),
                Rect(r.x, y, r.w, half),
                _text_style(c, size, align="center", valign="bottom" if above else "top"),
            )
            reach = 0 if marks == "off" else dot_d // 2  # without dots the stem runs to the axis
            ys = (
                (axis_y - dot_d // 2 - stem, axis_y - reach)
                if above
                else (axis_y + reach, axis_y + dot_d // 2 + stem)
            )
            _line(c, f"Timeline {i + 1} stem", cx, ys[0], cx, ys[1], th.timeline_line, line_w)
            _dot(
                c,
                th,
                i,
                cx,
                axis_y,
                dot_d,
                marks,
                fills,
                _own(bx[i], "fill") or (th.timeline_now if now[i] else None),
                size,
            )
    else:
        rows = _split(body.h, ws)
        axis_x = body.x + dot_d // 2
        tx = axis_x + dot_d // 2 + stem
        tw = body.right - tx

        def ok(s: float) -> bool:
            st = _text_style(c, s)
            return all(
                _need(c, _paras(h, bd, s, ratio, head_col), tw, st) <= (rh * lt.vocab_fill)
                for (h, bd), (_o, rh) in zip(parts, rows, strict=True)
            )

        size, fit = _largest(hi, lo, ok)
        lw_emu = _emu(th.timeline_line_w)
        _axis(c, Rect(axis_x - lw_emu // 2, body.y, lw_emu, body.h), th.timeline_line)
        for i, ((h, bd), (off, rh)) in enumerate(zip(parts, rows, strict=True)):
            cy = body.y + off + rh // 2
            col = _own(bx[i], "color") or (now_col if now[i] else head_col)
            name = f"Timeline {i + 1}" + (" now" if now[i] else "")
            _emit_text(
                c,
                name,
                _paras(h, bd, size, ratio, col),
                Rect(tx, body.y + off, tw, rh),
                _text_style(c, size, align="left", valign="middle"),
            )
            reach = 0 if marks == "off" else dot_d // 2
            _line(c, f"Timeline {i + 1} stem", axis_x + reach, cy, tx, cy, th.timeline_line, line_w)
            _dot(
                c,
                th,
                i,
                axis_x,
                cy,
                dot_d,
                marks,
                fills,
                _own(bx[i], "fill") or (th.timeline_now if now[i] else None),
                size,
            )
    info.update(size=size, base=base, fit=fit)
    if not fit:
        c.over.append("@timeline text")
    return True


def _axis(c, rect: Rect, color: str) -> None:
    """The timeline axis: a thin filled rectangle (a line would be "crossing" the numbered dots)."""
    c.emit(
        Shape(shape="rect", attrs={"shape_name": "Timeline line"}), rect, fast_style(fill=color, line=None)
    )


def _dot(
    c, th, i: int, cx: int, cy: int, d: int, marks: str, fills: list[str], now: str | None, size: float
) -> None:
    """The milestone dot (``marks=on``), a numbered dot (``num``), or nothing (``off``)."""
    if marks == "off":
        return
    fill = now or _pick(fills, i, th.timeline_dot) or th.timeline_dot
    paras = []
    st = fast_style(fill=fill, line=None)
    if marks == "num":
        digit = max(_pt(d) * 0.46, 1.0)
        paras = [Paragraph(runs=[Run(text=str(i + 1), bold=True)])]
        st = st.merged(
            fast_style(
                font=th.fonts.body,
                font_ea=th.fonts.ea,
                font_size=digit,
                color=_ink(c, fill, "bg"),
                align="center",
                valign="middle",
                padding="0pt",
            )
        )
    c.emit(
        Shape(shape="ellipse", paragraphs=paras, attrs={"shape_name": f"Timeline {i + 1} dot"}),
        Rect(cx - d // 2, cy - d // 2, d, d),
        st,
    )


# --------------------------------------------------------------------------- cards (vs, matrix)


def _fit_boxes(
    c, slide: Slide, items: list[tuple[Container, Rect]], inherit: Style, info: dict, grow: float
) -> Any:
    """Place ``items`` (box, rect) as ordinary cards with one text size: shrink to fit, else grow into the
    room (up to ``layout.vocab_grow``). Returns the context of the chosen run (``out`` holds the cards)."""
    E = _eng()
    lt = c.lt
    pinned = forms.num(slide.attrs, "size")

    def run(rects: list[Rect], **kw):
        cc = _new_ctx(c, slide, **kw)
        cc.spans = []  # (first, end) index in ``out`` of every box: its card, heading and content
        E._equalize_heads(cc, [(b, r.w, 0) for (b, _), r in zip(items, rects, strict=True)])
        for (b, _r), r in zip(items, rects, strict=True):
            start = len(cc.out)
            E._place_container(cc, b, r, inherit)
            cc.spans.append((start, len(cc.out)))
        return cc

    tight = [Rect(r.x, r.y, r.w, round(r.h * lt.vocab_fill)) for _b, r in items]
    real = [r for _b, r in items]
    best = None
    for s in E._SCALES:
        trial = run(tight, scale=s)
        if not trial.over:
            best = (s, 1.0)
            break
    if best is None:
        best = (E._SCALES[-1], 1.0)
    elif best[0] >= 1.0 and not pinned:
        g = grow
        while g > 1.04:
            if not (trial := run(tight, grow=round(g, 2))).over and trial.grew:
                best = (1.0, round(g, 2))
                break
            g -= 0.05
    final = run(real, scale=best[0], grow=best[1])
    info.update(scale=best[0], grow=best[1])
    return final


def _natural(c, final, slide: Slide, items: list[tuple[Container, Rect]], inherit: Style) -> int:
    """Tallest natural box height at the chosen text size (EMU)."""
    E = _eng()
    cc = _new_ctx(c, slide, scale=final.scale, grow=final.grow)
    hs = [E._box_nat(cc, b, r.w, inherit) for b, r in items]
    return max((h for h in hs if h is not None), default=0)


def _with_style(box: Container, **kw) -> Container:
    return box.model_copy(update={"style": (box.style or Style()).merged(fast_style(**kw))})


def _card_fill(c, box: Container, fill: str | None, inherit_color: bool = True) -> Container:
    """``fill`` on a box that sets none itself, with a readable ink for its text."""
    if not fill or (box.style and box.style.fill):
        return box
    ink = c.theme.ink_on(fill, "fg")
    return _with_style(
        box, fill=fill, **({"color": ink} if inherit_color and not (box.style and box.style.color) else {})
    )


def _center_content(cc) -> None:
    """Move the content of every placed box (everything under its heading) to the middle of the space the card
    leaves under the heading: a quadrant holds a phrase or a few lines, which read better centred than hanging
    from the heading."""
    for start, end in cc.spans:
        items = cc.out[start:end]
        if len(items) < 3:
            continue
        card = items[0]
        k = next(
            (i for i, p in enumerate(items) if isinstance(p.element, Text) and p.element.role == "heading"),
            None,
        )
        if k is None:
            continue
        while k + 1 < len(items) and getattr(items[k + 1].element, "id", None) == "rule":
            k += 1  # a `heading.rule` belongs to the heading
        head, body = items[: k + 1], items[k + 1 :]
        if not body:
            continue
        top = max(p.y + p.h for p in head if p is not card)
        free = (card.y + card.h - top) - (max(p.y + p.h for p in body) - min(p.y for p in body))
        shift = round((free - (min(p.y for p in body) - top)) / 2)
        if shift > 0:
            for p in body:
                p.y += shift


# --------------------------------------------------------------------------- @vs


def _vs(c, slide: Slide, body: Rect, sg: int, info: dict) -> bool:
    th, lt = c.theme, c.lt
    bx = forms.boxes(slide) or []
    sides, verdict = bx[:2], (bx[2] if len(bx) > 2 else None)
    base, ratio, _hi, _lo, _pinned = _sizes(c, slide)
    d = _emu(th.vs_badge_size) if th.vs_badge_size else round(base * lt.vs_badge_ratio * EMU_PER_PT)
    gap = _emu(lt.vs_gap)
    between = d + 2 * gap
    ws = _weights(c, slide, 2, "vs") or [1.0, 1.0]
    cols = _split(max(body.w - between, 1), ws)
    xl, wl = body.x + cols[0][0], cols[0][1]
    xr, wr = body.x + cols[1][0] + between, cols[1][1]
    inherit = _inherit(c, slide)
    fills = _colors(slide, None)
    win = [i for i, b in enumerate(sides) if "hero" in b.classes]
    prepared = []
    for i, b in enumerate(sides):
        b = _card_fill(c, b, _pick(fills, i))
        if i in win[:1]:
            kw: dict[str, Any] = {"line": th.vs_win_line, "line_width": th.vs_win_w}
            if th.vs_win_fill:
                kw["fill"] = th.vs_win_fill
            b = _with_style(b, **kw)
            if th.vs_win_fill:
                b = _with_style(b, color=th.ink_on(th.vs_win_fill, "fg"))
        prepared.append(b)
    vh = 0
    vparas: list[Paragraph] = []
    vsize = base * ratio
    if verdict is not None:
        h, bd = _split_box(verdict)
        vparas = _verdict_paras(h, bd)
        vst = _verdict_style(c, vsize, th.vs_verdict_fill)
        vh = round(_need(c, vparas, body.w, vst) * 1.0)
    room = body.h - (vh + sg if verdict is not None else 0)
    rects = [Rect(xl, body.y, wl, room), Rect(xr, body.y, wr, room)]
    items = list(zip(prepared, rects, strict=True))
    final = _fit_boxes(c, slide, items, inherit, info, lt.vocab_grow_box)
    nat = _natural(c, final, slide, items, inherit)
    card_h = min(max(round(nat * 1.05), round(lt.vs_card_min * room)), room)
    used = card_h + (vh + sg if verdict is not None else 0)
    top = _block_top(body, used, lt.vocab_top)
    rects = [Rect(r.x, top, r.w, card_h) for r in rects]
    final = _fit_boxes(c, slide, list(zip(prepared, rects, strict=True)), inherit, info, lt.vocab_grow_box)
    c.out += final.out
    c.over += final.over
    c.diags += final.diags
    cy = top + card_h // 2
    c.emit(
        Shape(
            shape="ellipse",
            paragraphs=[Paragraph(runs=[Run(text=th.vs_badge_text, bold=True)])],
            attrs={"shape_name": "VS badge"},
        ),
        Rect(xl + wl + gap, cy - d // 2, d, d),
        fast_style(
            font=th.fonts.heading,
            font_ea=th.fonts.ea,
            font_size=max(_pt(d) * 0.4, 1.0),
            fill=th.vs_badge_fill,
            color=th.vs_badge_color or th.ink_on(th.vs_badge_fill, "bg"),
            bold=True,
            align="center",
            valign="middle",
            padding="0pt",
        ),
    )
    if verdict is not None:
        vy = top + card_h + sg
        c.emit(
            Text(role="body", paragraphs=vparas, attrs={"shape_name": "VS verdict"}),
            Rect(body.x, vy, body.w, vh),
            _verdict_style(c, vsize, th.vs_verdict_fill),
        )
    info.update(n=len(bx), win=bool(win), verdict=verdict is not None, size=base * (final.grow or 1.0))
    return True


def _verdict_paras(head: Text | None, body: list[Text]) -> list[Paragraph]:
    """The verdict bar text: the heading in bold, then the first body line on the same line."""
    paras = [p for t in body for p in t.paragraphs]
    hruns = [r.model_copy(update={"bold": True}) for p in (head.paragraphs if head else []) for r in p.runs]
    if not paras:
        return [Paragraph(runs=hruns)]
    first = paras[0]
    lead = hruns + ([Run(text="  ")] if hruns else [])
    return [Paragraph(runs=lead + list(first.runs), style=first.style), *paras[1:]]


def _verdict_style(c, size: float, fill: str) -> Style:
    th = c.theme
    return _text_style(
        c,
        size,
        fill=fill,
        color=th.vs_verdict_color or th.ink_on(fill, "bg"),
        align="center",
        valign="middle",
        padding="8pt",
    )


# --------------------------------------------------------------------------- @matrix


def _matrix(c, slide: Slide, body: Rect, sg: int, info: dict) -> bool:
    th, lt = c.theme, c.lt
    bx = forms.boxes(slide) or []
    xl, yl = str(slide.attrs.get("x", "")), str(slide.attrs.get("y", ""))
    size = th.matrix_axis_size or th.sizes.get("caption", 12)
    label_h = round(size * 1.5 * EMU_PER_PT)
    aw = _emu(th.matrix_axis_w)
    ag = _emu(lt.matrix_axis_gap)
    strip_h = (ag + aw + label_h) if xl else 0
    strip_w = (label_h + aw + ag) if yl else 0
    area = Rect(body.x + strip_w, body.y, body.w - strip_w, body.h - strip_h)
    gap = _emu(lt.matrix_gap)
    cw = _split(area.w, _weights(c, slide, 2, "matrix") or [1.0, 1.0], gap)
    rh = _split(area.h, [1.0, 1.0], gap)
    fills = _colors(slide, th.matrix_fill)
    inherit = _inherit(c, slide)
    items = []
    for i, b in enumerate(bx):
        r, k = divmod(i, 2)
        items.append(
            (
                _card_fill(c, b, _pick(fills, i)),
                Rect(area.x + cw[k][0], area.y + rh[r][0], cw[k][1], rh[r][1]),
            )
        )
    final = _fit_boxes(c, slide, items, inherit, info, lt.vocab_grow)
    _center_content(final)
    c.out += final.out
    c.over += final.over
    c.diags += final.diags
    col = th.matrix_axis_color
    lw = _pt(aw)
    ink = th.legible(col)
    st = _text_style(c, size, color=ink, align="center", valign="middle")
    if xl:
        y = area.bottom + ag + aw // 2
        _line(c, "Matrix x axis", area.x, y, area.right, y, col, lw, "arrow")
        _emit_text(
            c,
            "Matrix x label",
            [Paragraph(runs=[Run(text=xl)])],
            Rect(area.x, y + aw // 2, area.w, label_h),
            st,
        )
    if yl:
        x = body.x + label_h + aw // 2
        _line(c, "Matrix y axis", x, area.bottom, x, area.y, col, lw, "arrow")
        c.emit(
            Text(
                role="body",
                paragraphs=[Paragraph(runs=[Run(text=yl)])],
                attrs={"shape_name": "Matrix y label", "vert": "vert270", "measured": "html"},
            ),
            Rect(body.x, area.y, label_h, area.h),
            st,
        )
    info.update(
        n=len(bx), size=th.sizes.get("body", 18) * c.dense_k * (final.grow or 1.0), axes=bool(xl) + bool(yl)
    )
    return True


# --------------------------------------------------------------------------- @funnel / @pyramid


def _stack(c, slide: Slide, body: Rect, sg: int, info: dict, form: str) -> bool:
    th, lt = c.theme, c.lt
    bx = forms.boxes(slide) or []
    n = len(bx)
    narrow_down = forms.words(slide.attrs, form, "dir") == "down"  # the direction the narrow end points
    gap = _emu(getattr(th, f"{form}_gap"))
    taper = float(getattr(th, f"{form}_taper"))
    share = float(getattr(th, f"{form}_share"))
    parts = [_split_box(b) for b in bx]
    has_body = any(bd for _h, bd in parts)
    ws = _weights(c, slide, 2, form)
    if ws:
        share = ws[0] / sum(ws)
    elif not has_body:
        share = lt.funnel_solo_share
    base, ratio, hi, lo, pinned = _sizes(c, slide)
    shapes_w = round(body.w * share)
    gutter = max(sg, 1)
    text_x = body.x + shapes_w + gutter
    text_w = max(body.right - text_x, 1)
    stage_h = min((body.h - gap * (n - 1)) // n, _emu(lt.funnel_h_max))
    used = stage_h * n + gap * (n - 1)
    top = _block_top(body, used, lt.vocab_top)
    cx = body.x + (shapes_w // 2 if has_body else (body.w // 2))
    fills = _colors(slide, getattr(th, f"{form}_fill"))
    word = form.capitalize()
    # a non-default direction rides in the shape name (the importer reads it back as `dir=`)
    dir_name = "" if narrow_down == (form == "funnel") else (" down" if narrow_down else " up")

    def width_at(t: float) -> float:
        """Width share at fraction ``t`` of the height (0 = top): the narrow end is ``taper``."""
        return (1 - (1 - taper) * t) if narrow_down else (taper + (1 - taper) * t)

    heads: list[tuple[Text | None, float]] = []
    geo = []
    usable = []  # share of the shape width a heading may use: the narrower edge (a point: the lower part)
    for i in range(n):
        t0, t1 = i / n, (i + 1) / n
        w0, w1 = width_at(t0), width_at(t1)
        geo.append((w0, w1))
        u = min(w0, w1) if min(w0, w1) > 0.02 else 0.6 * max(w0, w1)
        usable.append(u)
        heads.append((parts[i][0], u))
    # heading size: one size for all stages; each heading fits its shape's mean width (on at most two lines)
    shape_w = shapes_w if has_body else round(body.w * share)

    def head_ok(s: float, lines: float) -> bool:
        st = _text_style(c, s, bold=True)
        for h, mean in heads:
            if h is None:
                continue
            w = round(shape_w * mean * 0.85)
            paras = [
                p.model_copy(update={"style": fast_style(font_size=s, bold=True).merged(p.style)})
                for p in h.paragraphs
            ]
            if _need(c, paras, w, st) > min(stage_h * lt.vocab_fill, lines * s * EMU_PER_PT):
                return False
        return True

    # headings stay on one line unless that would make them smaller than the body text
    top_pt = hi * ratio if not pinned else hi
    hsize, hfit = _largest(top_pt, max(base, lo), lambda s: head_ok(s, lt.line_probe))
    if not hfit:
        hsize, hfit = _largest(top_pt, lo, lambda s: head_ok(s, 2 * lt.line_probe))

    def body_ok(s: float) -> bool:
        st = _text_style(c, s)
        return all(
            _need(c, [p for t in bd for p in t.paragraphs], text_w, st) <= stage_h * lt.vocab_fill
            for _h, bd in parts
            if bd
        )

    bsize, bfit = (
        _largest(min(hi, max(hsize / ratio, base)) if not pinned else hi, lo, body_ok)
        if has_body
        else (hsize, True)
    )
    stage_cols: list[str] = []
    for i in range(n):
        col = _own(bx[i], "fill") or _pick(fills, i)
        if col is None:  # tints of primary, strongest at the wide end
            frac = (i / max(n - 1, 1)) if narrow_down else (1 - i / max(n - 1, 1))
            from . import engine as E

            col = E._tint(th, "primary", 1.0 - 0.45 * frac) or "primary"
        stage_cols.append(col)
    for i in range(n):
        y = top + i * (stage_h + gap)
        w0, w1 = geo[i]
        full = shape_w
        left0 = (1 - w0) / 2
        left1 = (1 - w1) / 2
        col = stage_cols[i]
        ink = _own(bx[i], "color") or (th.funnel_color if form == "funnel" else th.pyramid_color)
        h = parts[i][0]
        paras = (
            [
                p.model_copy(update={"style": fast_style(font_size=hsize, bold=True).merged(p.style)})
                for p in h.paragraphs
            ]
            if h is not None
            else []
        )
        point = min(w0, w1) <= 0.02  # an apex stage: its text stands on the base
        c.emit(
            Shape(
                shape="trap",
                paragraphs=paras,
                attrs={
                    "shape_name": f"{word} {i + 1}{dir_name}",
                    "top": left0,
                    "bot": left1,
                    "text": usable[i],
                },
            ),
            Rect(cx - full // 2, y, full, stage_h),
            fast_style(
                fill=col,
                line=None,
                font=th.fonts.heading,
                font_ea=th.fonts.ea,
                font_size=hsize,
                bold=True,
                color=ink or th.ink_on(col, "bg"),
                align="center",
                valign="bottom" if point else "middle",
                padding="0pt",
            ),
        )
        bd = parts[i][1]
        if bd:
            _emit_text(
                c,
                f"{word} {i + 1} text",
                [p for t in bd for p in t.paragraphs],
                Rect(text_x, y, text_w, stage_h),
                _text_style(c, bsize, align="left", valign="middle"),
            )
    info.update(
        n=n,
        dir="down" if narrow_down else "up",
        size=bsize if has_body else None,
        head=hsize,
        fit=hfit and bfit,
    )
    if not (hfit and bfit):
        c.over.append(f"@{form} text")
    return True


def _funnel(c, slide, body, sg, info) -> bool:
    return _stack(c, slide, body, sg, info, "funnel")


def _pyramid(c, slide, body, sg, info) -> bool:
    return _stack(c, slide, body, sg, info, "pyramid")


# --------------------------------------------------------------------------- @cycle


def _cycle(c, slide: Slide, body: Rect, sg: int, info: dict) -> bool:
    th, lt = c.theme, c.lt
    E = _eng()
    bx = forms.boxes(slide) or []
    n = len(bx)
    cw = forms.words(slide.attrs, "cycle", "dir") == "cw"
    parts = [_split_box(b) for b in bx]
    icons_ = [
        E._icon_name(b) for b in bx
    ]  # `## Plan {icon=target}`: the glyph sits in the node, the heading beside it
    base, ratio, hi, lo, pinned = _sizes(c, slide)
    start = -90.0 if n % 2 else -90.0 + 180.0 / n
    step = 360.0 / n * (1 if cw else -1)
    angles = [start + i * step for i in range(n)]
    sin_max = max(abs(math.sin(math.radians(a))) for a in angles)
    base_pt = max(base, lo)
    pad2 = 2 * lt.cycle_node_pad * EMU_PER_PT
    text_nodes = [p for p, ic in zip(parts, icons_, strict=True) if not ic and p[0] is not None]

    def inner_of(dia: int) -> int:  # the text square of a circle
        return round(dia * lt.cycle_node_inner - pad2)

    def head_fits(s: float, inner: int) -> bool:
        st = _text_style(c, s, bold=True)
        return all(
            _word_em(h) * s * EMU_PER_PT <= inner  # no word is cut in two
            and _need(
                c,
                [p.model_copy(update={"style": fast_style(font_size=s, bold=True)}) for p in h.paragraphs],
                inner,
                st,
            )
            <= inner
            for h, _b in text_nodes
        )

    def ring_r(dia: int) -> float:
        r_ = min((body.h - dia) / (2 * sin_max), (body.w * (1 - lt.cycle_body_share) - dia) / 2)
        return max(r_, dia * 0.6)

    def chord_ok(dia: int) -> bool:  # neighbours stay apart: the chord holds both nodes and an arrow
        return 2 * ring_r(dia) * math.sin(math.pi / n) / lt.cycle_chord_ratio >= dia

    if th.cycle_node_size:
        d = _emu(th.cycle_node_size)
    else:
        d_room = round(lt.cycle_node_ratio * body.h)
        unit = round(0.04 * 914400)
        d_cap = d_room
        while not chord_ok(d_cap) and d_cap > unit * 4:  # the room cannot hold the preferred node: shrink it
            d_cap -= unit
        while chord_ok(d_cap + unit) and d_cap < 0.5 * body.h:  # ... or it holds a larger one
            d_cap += unit
        d = min(d_room, d_cap)
        if text_nodes:  # a node grows until its heading fits at the body size (the ring allows it)
            while d < d_cap and not head_fits(base_pt, inner_of(d)):
                d = min(d + unit, d_cap)
    r = ring_r(d)
    ccx, ccy = body.x + body.w // 2, body.y + body.h // 2
    aw = _emu(th.cycle_arrow_w)
    ag = _emu(lt.cycle_arrow_gap)
    fills = _colors(slide, th.cycle_fill)
    pos = [(ccx + r * math.cos(math.radians(a)), ccy + r * math.sin(math.radians(a))) for a in angles]
    side = ["r" if math.cos(math.radians(a)) > -0.05 else "l" for a in angles]
    inner = inner_of(d)
    bw = max(round(min(body.w / 2 - r - d / 2 - sg, body.w * 0.4)), 1)
    # body text height: bounded by the vertical distance to the next node on the same side
    ys = {s: sorted(p[1] for p, sd in zip(pos, side, strict=True) if sd == s) for s in ("r", "l")}
    gaps = [b - a for v in ys.values() for a, b in zip(v, v[1:], strict=False)]
    # bodies hang from the top of upper nodes and stand on the bottom of lower ones: two neighbours need
    # bh_a + bh_b <= gap + d, so each gets half of it
    bh = round(min(max((min(gaps, default=d * 2) + d) / 2 * 0.96, d), d * 2.2))
    out_head = th.legible(th.cycle_head_color or "fg")

    if text_nodes:
        top_pt = max(min(hi * ratio, d / EMU_PER_PT * 0.3), base_pt) if not pinned else hi
        hsize, hfit = _largest(top_pt, lo, lambda s: head_fits(s, inner))
    else:
        hsize, hfit = base_pt, True

    def side_paras(i: int, s: float) -> list[Paragraph]:
        h, bd = parts[i]
        if icons_[i]:  # the heading moved out of the node: it leads the text beside it
            return _paras(h, bd, s, ratio, _own(bx[i], "color") or out_head)
        return [p for t in bd for p in t.paragraphs]

    def body_ok(s: float) -> bool:
        st = _text_style(c, s)
        return all(_need(c, ps, bw, st) <= bh * lt.vocab_fill for i in range(n) if (ps := side_paras(i, s)))

    has_text = any(side_paras(i, base_pt) for i in range(n))
    bsize, bfit = _largest(hi, lo, body_ok) if has_text else (hsize, True)
    # curved arrows first (behind the nodes): the arc of the ring between neighbours
    half = math.degrees(math.asin(min((d / 2 + ag) / r, 1.0)))
    arrow_col = th.cycle_arrow
    for i in range(n):
        a0, a1 = angles[i], angles[(i + 1) % n]
        if cw:
            s_deg, e_deg, head = a0 + half, a1 - half, "arrow"
            if e_deg <= s_deg:
                e_deg += 360
        else:
            s_deg, e_deg, head = (
                a1 + half,
                a0 - half,
                "back",
            )  # drawn clockwise from the next node, tip at its start
            if e_deg <= s_deg:
                e_deg += 360
        c.emit(
            Shape(
                shape="arc",
                attrs={
                    "shape_name": f"Cycle {i + 1} arrow" + ("" if cw else " ccw"),
                    "start": s_deg,
                    "end": e_deg,
                    "head": head,
                },
            ),
            Rect(round(ccx - r), round(ccy - r), round(2 * r), round(2 * r)),
            fast_style(fill=None, line=arrow_col, line_width=_pt(aw)),
        )
    csize = _cycle_center(c, slide, (ccx, ccy), r, d, ag + aw, (hi * ratio, lo), info)
    for i, ((h, _bd), (px, py)) in enumerate(zip(parts, pos, strict=True)):
        col = _own(bx[i], "fill") or _pick(fills, i, "primary") or "primary"
        ink = _own(bx[i], "color") or th.cycle_color or th.ink_on(col, "bg")
        paras = (
            [
                p.model_copy(update={"style": fast_style(font_size=hsize, bold=True).merged(p.style)})
                for p in h.paragraphs
            ]
            if h is not None and not icons_[i]
            else []
        )
        c.emit(
            Shape(shape="ellipse", paragraphs=paras, attrs={"shape_name": f"Cycle {i + 1}"}),
            Rect(round(px - d / 2), round(py - d / 2), d, d),
            fast_style(
                fill=col,
                line=None,
                font=th.fonts.heading,
                font_ea=th.fonts.ea,
                font_size=hsize,
                bold=True,
                color=ink,
                align="center",
                valign="middle",
                padding="2pt",
            ),
        )
        if icons_[i]:
            isz = round(d * th.cycle_icon_ratio)
            c.emit(
                Shape(shape="icon", attrs={"icon": icons_[i], "shape_name": f"Cycle {i + 1} icon"}),
                Rect(round(px - isz / 2), round(py - isz / 2), isz, isz),
                fast_style(fill=th.cycle_icon_color or th.ink_on(col, "bg"), line=None),
            )
        ps = side_paras(i, bsize)
        if ps:
            right = side[i] == "r"
            x = round(px + d / 2 + sg) if right else round(px - d / 2 - sg - bw)
            sin = math.sin(math.radians(angles[i]))
            if sin < -0.3:  # upper half: the text hangs from the top of its node
                rect, va = Rect(x, round(py - d / 2), bw, bh), "top"
            elif sin > 0.3:  # lower half: it stands on the bottom of its node
                rect, va = Rect(x, round(py + d / 2 - bh), bw, bh), "bottom"
            else:
                rect, va = Rect(x, round(py - bh / 2), bw, bh), "middle"
            _emit_text(
                c,
                f"Cycle {i + 1} text",
                ps,
                rect,
                _text_style(c, bsize, align="left" if right else "right", valign=va),
            )
    info.update(
        n=n,
        dir="cw" if cw else "ccw",
        size=bsize,
        head=hsize if text_nodes else None,
        fit=hfit and bfit,
        icons=sum(1 for ic in icons_ if ic),
        center=csize,
    )
    if not (hfit and bfit):
        c.over.append("@cycle text")
    return True


def _cycle_center(
    c, slide: Slide, centre: tuple[int, int], r: float, d: int, clear: int, sizes: tuple[float, float], info
) -> float | None:
    """The label at the ring's centre (``center="..."`` on the ``@`` line, else ``cycle.center``): the largest
    size the free disc holds. Returns its size in pt (``None`` = no label)."""
    th, lt = c.theme, c.lt
    text = str(slide.attrs.get("center") or th.cycle_center or "").strip()
    if not text:
        return None
    free = round(2 * (r - d / 2 - clear))  # the disc between the arrows
    if free < _emu("0.5in"):
        c.diag(
            "cycle-center",
            "the ring is too small for a centre label",
            "shorten the nodes' text, drop a node, or write cycle.node.size=0.8in",
        )
        return None
    w = round(free * lt.cycle_node_inner * 1.1)
    h = round(free * lt.cycle_node_inner)
    top, lo = sizes
    pin = th.cycle_center_size
    para = Paragraph(runs=[Run(text=text, bold=True)])

    def ok(s: float) -> bool:
        st = _text_style(c, s, bold=True)
        return _word_em(Text(role="body", paragraphs=[para])) * s * EMU_PER_PT <= w and (
            _need(c, [para.model_copy(update={"style": fast_style(font_size=s, bold=True)})], w, st)
            <= h * lt.vocab_fill
        )

    size, fit = (pin, True) if pin else _largest(min(top, h / EMU_PER_PT * 0.5), lo, ok)
    if not fit:
        c.over.append("@cycle centre label")
    fill = th.cycle_center_fill
    if th.cycle_center_color:
        ink = th.cycle_center_color
    else:
        ink = th.ink_on(fill, "bg") if fill else th.legible("primary")
    paras = [para.model_copy(update={"style": fast_style(font_size=size, bold=True)})]
    cx, cy = centre
    if fill:
        c.emit(
            Shape(shape="ellipse", paragraphs=paras, attrs={"shape_name": "Cycle center"}),
            Rect(cx - free // 2, cy - free // 2, free, free),
            fast_style(
                fill=fill,
                line=None,
                font=th.fonts.heading,
                font_ea=th.fonts.ea,
                font_size=size,
                bold=True,
                color=ink,
                align="center",
                valign="middle",
                padding="4pt",
            ),
        )
    else:
        _emit_text(
            c,
            "Cycle center",
            paras,
            Rect(cx - w // 2, cy - h // 2, w, h),
            _text_style(c, size, bold=True, align="center", valign="middle", color=ink),
        )
    return size


# --------------------------------------------------------------------------- @agenda


def _agenda(c, slide: Slide, body: Rect, sg: int, info: dict) -> bool:
    th, lt = c.theme, c.lt
    items = forms.agenda_items(slide) or []
    n = len(items)
    base, ratio, hi, lo, pinned = _sizes(c, slide)
    el_size, el_color = _own(slide.elements[0], "font_size"), _own(slide.elements[0], "color")
    if el_size:
        base, hi, lo, pinned = el_size, el_size, el_size, True
    row_h = min(body.h // n, _emu(lt.agenda_row_max))
    used = row_h * n
    top = _block_top(body, used, lt.vocab_top)
    num_pt = th.agenda_num_size or max(_pt(row_h) * lt.agenda_num_ratio, base)
    num_w = round(num_pt * lt.agenda_num_w * EMU_PER_PT)
    ws = _weights(c, slide, 2, "agenda")
    if ws:
        num_w = round(body.w * ws[0] / sum(ws))
    gutter = max(sg, 1)
    tx = body.x + num_w + gutter
    tw = max(body.right - tx, 1)
    now_any = any(now for _t, _s, now in items)
    fills = _colors(slide, None)
    subs = [list(sub) for _t, sub, _n in items]

    def paras_for(i: int, s: float, color: str | None) -> list[Paragraph]:
        src = items_text[i]
        runs = _trim_runs(src, items[i][2])
        head = Paragraph(
            runs=runs, style=fast_style(font_size=s * ratio, bold=True, **({"color": color} if color else {}))
        )
        rest = [
            p.model_copy(update={"style": fast_style(font_size=s * 0.85).merged(p.style)}) for p in subs[i]
        ]
        return [head, *rest]

    items_text = _item_runs(slide)

    def ok(s: float) -> bool:
        st = _text_style(c, s)
        return all(_need(c, paras_for(i, s, None), tw, st) <= row_h * lt.vocab_fill for i in range(n))

    size, fit = _largest(hi if not pinned else hi, lo, ok)
    rule_col = th.agenda_rule
    rule_w = _pt(_emu(th.agenda_rule_w))
    for i in range(n):
        y = top + i * row_h
        now = items[i][2]
        dim = bool(now_any and not now and th.agenda_dim)
        ink = (
            th.legible(th.agenda_now if now else (th.agenda_dim if dim else None))
            if (now or dim)
            else el_color
        )
        num_col = th.legible(th.agenda_now if now else (th.agenda_dim if dim else th.agenda_num_color))
        row_fill = _pick(fills, i)
        label = f"Agenda {i + 1}" + (" now" if now else "")
        if row_fill:
            c.emit(
                Shape(shape="rect", attrs={"shape_name": f"Agenda {i + 1} fill"}),
                Rect(body.x, y, body.w, row_h),
                fast_style(fill=row_fill, line=None),
            )
        _emit_text(
            c,
            f"{label} num",
            [Paragraph(runs=[Run(text=th.agenda_num_text.replace("{n}", str(i + 1)), bold=True)])],
            Rect(body.x, y, num_w, row_h),
            _text_style(c, num_pt, color=num_col, align="left", valign="middle", bold=True),
        )
        _emit_text(
            c,
            label,
            paras_for(i, size, ink),
            Rect(tx, y, tw, row_h),
            _text_style(c, size, align="left", valign="middle"),
        )
        if rule_col and i < n - 1:
            _line(c, f"Agenda {i + 1} rule", body.x, y + row_h, body.right, y + row_h, rule_col, rule_w)
    if rule_col:
        _line(c, "Agenda 0 rule", body.x, top, body.right, top, rule_col, rule_w)
    info.update(n=n, size=size, num=num_pt, fit=fit, now=now_any)
    if not fit:
        c.over.append("@agenda text")
    return True


def _item_runs(slide: Slide) -> list[list[Run]]:
    return [list(p.runs) for p in slide.elements[0].paragraphs if p.marker == "number" and p.level == 0]  # type: ignore[union-attr]


def _trim_runs(runs: list[Run], now: bool) -> list[Run]:
    """The item's runs without the trailing ``{.accent}`` marker."""
    if not now or not runs:
        return runs
    out = list(runs)
    last = out[-1]
    text = re.sub(r"\s*\{\.accent\}\s*$", "", last.text)
    if text:
        out[-1] = last.model_copy(update={"text": text})
    else:
        out.pop()
    return out


# --------------------------------------------------------------------------- @statement


def _statement(c, slide: Slide, body: Rect, sg: int, info: dict) -> bool:
    th, lt = c.theme, c.lt
    big, rest = forms.statement_lines(slide) or (None, [])
    if big is None:
        return False
    align = forms.words(slide.attrs, "statement", "align")
    valign = forms.words(slide.attrs, "statement", "valign")
    base, ratio, _hi, lo, _pinned = _sizes(c, slide)
    first = slide.elements[0]
    pin = _own(first, "font_size") or th.statement_size or forms.num(slide.attrs, "size")
    color = _own(first, "color") or th.legible(th.statement_color or "primary")
    sub_color = th.legible(th.statement_sub_color or "muted")
    width = round(body.w * 0.94)
    sub_paras = list(rest)

    def sub_size(b: float) -> float:
        if th.statement_sub_size:
            return th.statement_sub_size
        want = max(b * lt.statement_sub_ratio, base)
        probe = [p.model_copy(update={"style": None}) for p in sub_paras]
        s = want  # the largest size <= the wanted one at which the caption stays on one line
        while s > base:
            one = _need(c, probe, width, _text_style(c, s)) <= s * EMU_PER_PT * lt.line_probe
            if one:
                return s
            s -= _STEP
        return base

    def paras(b: float) -> list[Paragraph]:
        return [
            big.model_copy(
                update={"style": fast_style(font_size=b, bold=True, color=color).merged(big.style)}
            )
        ]

    def sub(b: float) -> list[Paragraph]:
        s = sub_size(b)
        return [
            p.model_copy(update={"style": fast_style(font_size=s, color=sub_color).merged(p.style)})
            for p in sub_paras
        ]

    def total(b: float) -> tuple[float, float]:
        hb = _need(c, paras(b), width, _text_style(c, b))
        hs = _need(c, sub(b), width, _text_style(c, sub_size(b))) if sub_paras else 0
        return hb, hs

    def ok(b: float) -> bool:
        hb, hs = total(b)
        return hb + hs + (sg if sub_paras else 0) <= body.h * lt.vocab_fill and hb <= b * EMU_PER_PT * 2.6

    if pin:
        size, fit = float(pin), True
    else:
        size, fit = _largest(float(lt.statement_max_pt), lo, ok)
    hb, hs = total(size)
    used = round(hb + hs + (sg if sub_paras else 0))
    y0 = {"top": body.y, "middle": body.y + (body.h - used) // 2, "bottom": body.bottom - used}[valign]
    x0 = body.x + (body.w - width) // 2
    _emit_text(
        c,
        "Statement",
        paras(size),
        Rect(x0, y0, width, round(hb)),
        _text_style(c, size, align=align, valign="middle"),
    )
    if sub_paras:
        _emit_text(
            c,
            "Statement caption",
            sub(size),
            Rect(x0, y0 + round(hb) + sg, width, round(hs)),
            _text_style(c, sub_size(size), align=align, valign="top"),
        )
    info.update(size=size, base=base, fit=fit, caption=bool(sub_paras))
    if not fit:
        c.over.append("@statement text")
    return True


_FORMS: dict[str, Callable] = {
    "timeline": _timeline,
    "vs": _vs,
    "matrix": _matrix,
    "funnel": _funnel,
    "pyramid": _pyramid,
    "cycle": _cycle,
    "agenda": _agenda,
    "statement": _statement,
}


from . import vocab4  # noqa: E402  (wave 2026-10-08 lane B: @stairs @nested @flow disc)

_FORMS.update(vocab4.FORMS)
