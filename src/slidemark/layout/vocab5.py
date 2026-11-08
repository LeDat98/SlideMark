"""Composition vocabulary, wave 2026-11-08 lane C: ``@swimlane`` ``@sequence`` (editorial diagram types).

Same contract as ``vocab.py`` (which dispatches here): a composer works on the body rectangle with its own
context, names every shape it draws (``Lane 2``, ``Lane 2 head``, ``Step 4``, ``Step 4 next``;
``Seq Client head``, ``Seq Client lifeline``, ``Seq 3 label``, ``Seq 3 msg``, ``Seq 3 msg reply``,
``Seq 3 msg self``) so ``importer/vocab.py`` folds them back, reads every number from a token (``forms5.py``)
and never raises on bad input (a slide that lacks what the form needs is laid out as ordinary blocks).

Diagram rules (diagram-design): orthogonal connectors only, arrows in the muted connector colour, hairline
borders, no shadows, the one headline path or node in the accent (a role class such as ``{.focal}``).
"""

from __future__ import annotations

from typing import Any

from .. import forms, forms5
from ..ir import Paragraph, Run, Shape, Slide, Style, fast_style
from ..units import EMU_PER_PT
from . import vocab as V
from .grid import Rect

_K = 914400  # EMU per inch


# --------------------------------------------------------------------------- shared


class _Frame:
    """Layout runs in a horizontal frame (x along the flow, y across the lanes); ``dir=v`` transposes it."""

    def __init__(self, body: Rect, vertical: bool) -> None:
        self.body, self.vertical = body, vertical
        self.aw, self.ah = (body.h, body.w) if vertical else (body.w, body.h)

    def rect(self, x: float, y: float, w: float, h: float) -> Rect:
        b = self.body
        if self.vertical:
            return Rect(b.x + round(y), b.y + round(x), round(h), round(w))
        return Rect(b.x + round(x), b.y + round(y), round(w), round(h))

    def pt(self, x: float, y: float) -> tuple[int, int]:
        b = self.body
        return (b.x + round(y), b.y + round(x)) if self.vertical else (b.x + round(x), b.y + round(y))


def _role(c, classes: list[str]) -> Style | None:
    out: Style | None = None
    for cls in classes:
        st = c.theme.classes.get(cls)
        if st is not None:
            out = st if out is None else out.merged(st)
    return out


def _conn(
    c,
    name: str,
    p0: tuple[int, int],
    p1: tuple[int, int],
    route: str,
    adj: float,
    color: str,
    width_pt: float,
    head: str = "arrow",
    src: Rect | None = None,
    dst: Rect | None = None,
    dash: str | None = None,
) -> None:
    """A native connector from ``p0`` to ``p1``: straight when the ends line up, else an elbow whose middle
    segment sits at ``adj`` (a share of the way from the start) and starts along ``route`` (``h`` / ``v``)."""
    elbow = (route == "v" and p0[0] != p1[0]) or (route == "h" and p0[1] != p1[1])
    attrs: dict[str, Any] = {
        "head": head,
        "flip_h": p1[0] < p0[0],
        "flip_v": p1[1] < p0[1],
        "elbow": elbow,
        "route": route,
        "adj": round(adj, 4),
        "shape_name": name,
    }
    if src is not None and dst is not None:
        attrs["src_box"] = [src.x, src.y, src.w, src.h]
        attrs["dst_box"] = [dst.x, dst.y, dst.w, dst.h]
    kw: dict[str, Any] = {"line_dash": dash} if dash else {}
    c.emit(
        Shape(shape="line", attrs=attrs),
        Rect(min(p0[0], p1[0]), min(p0[1], p1[1]), abs(p1[0] - p0[0]), abs(p1[1] - p0[1])),
        fast_style(line=color, line_width=width_pt, **kw),
    )


def _arrow_style(c, color: str | None, width: Any) -> tuple[str, float]:
    rd = c.theme.render
    return (color or rd.connector_color), (V._pt(V._emu(width)) if width else rd.connector_width)


def _sized(paras: list[Paragraph], size: float, bold: bool = False) -> list[Paragraph]:
    st = fast_style(font_size=size, **({"bold": True} if bold else {}))
    return [p.model_copy(update={"style": st.merged(p.style)}) for p in paras]


# --------------------------------------------------------------------------- @swimlane


def _swimlane(c, slide: Slide, body: Rect, sg: int, info: dict) -> bool:
    th = c.theme
    lanes = forms5.lanes_of(slide) or []
    steps = forms5.steps_of(lanes)
    n, ncol = len(lanes), max(s.col for s in steps)
    vertical = forms.words(slide.attrs, "swimlane", "dir") == "v"
    fr = _Frame(body, vertical)
    aw, ah = fr.aw, fr.ah
    base, _ratio, hi, lo, pinned = V._sizes(c, slide)
    hi = hi if pinned else base  # step text never grows past the body size
    if th.swimlane_head_w:
        hw = V._emu(th.swimlane_head_w)
    elif vertical:
        hw = min(max(round(0.12 * aw), round(0.45 * _K)), round(0.9 * _K))
    else:
        hw = min(max(round(0.14 * aw), round(0.9 * _K)), round(1.8 * _K))
    hw = max(min(hw, aw // 3), 1)
    lane_h = [ah // n + (ah - ah // n * n if i == n - 1 else 0) for i in range(n)]
    lane_y = [sum(lane_h[:i]) for i in range(n)]
    lmin = min(lane_h)
    cw = aw - hw
    pitch = cw / ncol
    gap = V._emu(th.swimlane_gap) if th.swimlane_gap else max(round(0.22 * pitch), round(0.1 * _K))
    gap = min(gap, round(0.5 * pitch))
    sw = max(round(pitch - gap), 1)  # step extent along the flow
    pad_pt = 0.5 * max(base, lo)
    pad = round(pad_pt * EMU_PER_PT)
    line_pt = V._pt(V._emu(th.swimlane_step_line_w))
    radius = V._pt(V._emu(th.swimlane_step_radius))
    # across-lane extent of a step: a share of the lane; a horizontal step grows when its text needs more
    sh0 = (
        round(th.swimlane_step_ratio * lmin)
        if not vertical
        else round(max(th.swimlane_step_ratio, 0.8) * lmin)
    )
    sh_max = round(0.9 * lmin)

    def real_wh(sh: int) -> tuple[int, int]:
        return (sh, sw) if vertical else (sw, sh)

    def need(s: float, sh: int) -> list[float]:
        rw, _rh = real_wh(sh)
        st = V._text_style(c, s)
        return [V._need(c, _sized(x.paras, s), max(rw - 2 * pad, 1), st) for x in steps]

    def fits(s: float) -> bool:
        _rw, rh = real_wh(sh_max if not vertical else sh0)
        return all(h <= rh - 2 * pad for h in need(s, sh_max if not vertical else sh0))

    size, fit = V._largest(hi, lo, fits) if not pinned else (hi, fits(hi))
    sh = sh0
    if not vertical:
        sh = min(max(sh0, round(max(need(size, sh0)) + 2 * pad)), sh_max)
    margin = (lmin - sh) / 2
    line_col, line_w = th.swimlane_line, V._pt(V._emu(th.swimlane_line_w))
    fills = V._colors(slide, th.swimlane_fill)
    # lanes: one outlined band each, with its header
    heads = [x.title for x in lanes]
    head_rect = [fr.rect(0, lane_y[i], hw, lane_h[i]) for i in range(n)]

    def head_ok(s: float) -> bool:
        st = V._text_style(c, s, bold=True)
        for i, h in enumerate(heads):
            if h is None:
                continue
            r = head_rect[i]
            if (
                V._word_em(h) * s * EMU_PER_PT > r.w - 2 * pad
                or V._need(c, _sized(h.paragraphs, s, True), r.w - 2 * pad, st) > r.h - 2 * pad
            ):
                return False
        return True

    if th.swimlane_head_size:
        hsize, hfit = th.swimlane_head_size, head_ok(th.swimlane_head_size)
    else:
        hsize, hfit = V._largest(max(base, lo), lo, head_ok)
    for i in range(n):
        c.emit(
            Shape(shape="rect", attrs={"shape_name": f"Lane {i + 1}"}),
            fr.rect(0, lane_y[i], aw, lane_h[i]),
            fast_style(fill=V._own(lanes[i], "fill") or V._pick(fills, i), line=line_col, line_width=line_w),
        )
    for i in range(n):
        paras = _sized(heads[i].paragraphs, hsize, True) if heads[i] is not None else []
        head_fill = th.swimlane_head_fill
        head_ink = V._own(lanes[i], "color") or th.swimlane_head_color or th.ink_on(head_fill, "fg")
        V._emit_text(
            c,
            f"Lane {i + 1} head",
            paras,
            head_rect[i],
            V._text_style(
                c,
                hsize,
                fill=head_fill,
                line=line_col,
                line_width=line_w,
                color=head_ink,
                align="center",
                valign="middle",
                padding=f"{pad_pt:.2f}pt",
            ),
        )
    # steps
    rect_of: dict[int, Rect] = {}
    frame_of: dict[int, tuple[float, float]] = {}
    for s in steps:
        fx = hw + (s.col - 1) * pitch + gap / 2
        fy = lane_y[s.lane] + (lane_h[s.lane] - sh) / 2
        frame_of[s.idx] = (fx, fy)
        rect_of[s.idx] = fr.rect(fx, fy, sw, sh)
        role = _role(c, s.classes)
        fill = (role.fill if role and role.fill else None) or th.swimlane_step_fill
        line = (role.line if role and role.line else None) or th.swimlane_step_line
        lw = role.line_width if role and role.line_width is not None else line_pt
        ink = (
            (role.color if role and role.color else None)
            or th.swimlane_step_color
            or ("fg" if role and role.fill else th.ink_on(fill, "fg"))
        )
        V._emit_text(
            c,
            f"Step {s.idx}",
            _sized(s.paras, size),
            rect_of[s.idx],
            V._text_style(
                c,
                size,
                fill=fill,
                line=line,
                line_width=lw,
                radius=radius,
                color=ink,
                align="center",
                valign="middle",
                padding=f"{pad_pt:.2f}pt",
            ),
        )
    # arrows: consecutive steps in column order (ties: written order)
    order = sorted(steps, key=lambda s: (s.col, s.idx))
    taken = {(s.lane, s.col) for s in steps}
    acol, aw_pt = _arrow_style(c, th.swimlane_arrow, th.swimlane_arrow_w)
    for a, b in zip(order, order[1:], strict=False):
        ax, ay = frame_of[a.idx]
        bx, by = frame_of[b.idx]
        acy, bcy = ay + sh / 2, by + sh / 2
        dc = b.col - a.col
        name = f"Step {a.idx} next"
        if a.lane == b.lane:
            if dc >= 1:
                p0, p1 = (ax + sw, acy), (bx, bcy)
            else:
                p0, p1 = (ax, acy), (bx + sw, bcy)
            route, adj = "h", 0.5
        elif dc >= 1:
            p0, p1 = (ax + sw, acy), (bx, bcy)
            route = "h"
            dx = p1[0] - p0[0]
            # the horizontal run goes where no step is in the way: along a's lane, else along b's lane
            clear_a = not any((a.lane, k) in taken for k in range(a.col + 1, b.col))
            clear_b = not any((b.lane, k) in taken for k in range(a.col + 1, b.col))
            adj = 0.5 if dc == 1 else ((1 - (gap / 2) / dx) if clear_a or not clear_b else (gap / 2) / dx)
        elif dc == 0:
            down = b.lane > a.lane
            p0, p1 = (ax + sw / 2, ay + sh if down else ay), (bx + sw / 2, by if down else by + sh)
            route, adj = "v", 0.5
        else:  # backwards: leave through the margin of a's lane, then along it to b
            down = b.lane > a.lane
            p0, p1 = (ax + sw / 2, ay + sh if down else ay), (bx + sw / 2, by if down else by + sh)
            route = "v"
            adj = min((margin / 2) / max(abs(p1[1] - p0[1]), 1), 0.5)
        _conn(
            c,
            name,
            fr.pt(*p0),
            fr.pt(*p1),
            ("v" if vertical else "h") if route == "h" else ("h" if vertical else "v"),
            adj,
            acol,
            aw_pt,
            "arrow",
            rect_of[a.idx],
            rect_of[b.idx],
        )
    info.update(n=len(steps), lanes=n, dir="v" if vertical else "h", size=size, head=hsize, fit=fit and hfit)
    if not (fit and hfit):
        c.over.append("@swimlane text")
    return True


# --------------------------------------------------------------------------- @sequence


def _sequence(c, slide: Slide, body: Rect, sg: int, info: dict) -> bool:
    th = c.theme
    names, msgs = forms5.sequence_of(slide) or ([], [])
    n, m = len(names), len(msgs)
    col = {nm: k for k, nm in enumerate(names)}
    base, _ratio, hi, lo, pinned = V._sizes(c, slide)
    hi = th.sequence_size or (hi if pinned else base)
    colw = body.w / n
    gap = V._emu(th.sequence_gap) if th.sequence_gap else max(round(0.08 * colw), sg)
    hw = max(min(round(colw - gap), round(2.6 * _K)), 1)
    cx = [round(body.x + (k + 0.5) * colw) for k in range(n)]
    pad_pt = 0.5 * max(base, lo)
    pad = round(pad_pt * EMU_PER_PT)
    pt = EMU_PER_PT
    wts = [1.7 if x.is_self else 1.0 for x in msgs]
    acol, aw_pt = _arrow_style(c, th.sequence_arrow, th.sequence_arrow_w)
    loop_w = [min(round(0.45 * colw), round(0.4 * _K)) for _ in msgs]

    def head_paras(i: int, s: float) -> list[Paragraph]:
        return _sized([Paragraph(runs=[Run(text=names[i])])], s, True)

    def head_h(s: float) -> int:
        st = V._text_style(c, s, bold=True)
        return max(round(V._need(c, head_paras(i, s), hw - 2 * pad, st)) + 2 * pad for i in range(n))

    def label_w(x, s: float) -> float:
        from . import measure

        return measure.text_em(x.label, bold=False) * s * pt + 8 * pt

    def fits(s: float) -> bool:
        lh = 1.3 * s * pt
        hh = max(head_h(s), round(0.4 * _K))
        avail = body.h - hh - 0.25 * hh
        u = avail / sum(wts)
        if u < lh + 0.5 * s * pt + 3 * pt:
            return False
        st = V._text_style(c, s)
        for x in msgs:
            if not x.label:
                continue
            k0, k1 = col[x.src], col[x.dst]
            if x.is_self:
                right = (cx[k0 + 1] if k0 + 1 < n else body.right) - cx[k0] - loop_w[0] - 8 * pt
                room = right
            else:
                room = abs(cx[k1] - cx[k0]) - 6 * pt
            if room < 2 * s * pt:
                return False
            if (
                V._need(c, _sized([Paragraph(runs=[Run(text=x.label)])], s), max(room - 8 * pt, 1), st)
                > 1.5 * s * pt
            ):
                return False
        return True

    size, fit = V._largest(hi, lo, fits) if not (pinned or th.sequence_size) else (hi, fits(hi))
    hsize = min(size, max(base, lo))
    hh = max(head_h(hsize), round(0.4 * _K))
    lh = round(1.3 * size * pt)
    y0 = body.y + hh + round(0.25 * hh)
    u = max((body.bottom - y0) / sum(wts), 1)
    head_ink = th.sequence_head_color or th.ink_on(th.sequence_head_fill, "fg")
    # lifelines first (behind everything), then the heads
    ll_w = V._pt(V._emu(th.sequence_lifeline_w))
    for k, nm in enumerate(names):
        _conn(
            c,
            f"Seq {nm} lifeline",
            (cx[k], body.y + hh),
            (cx[k], body.bottom),
            "v",
            0.5,
            th.sequence_lifeline,
            ll_w,
            "none",
            dash="dash",
        )
    for k, nm in enumerate(names):
        V._emit_text(
            c,
            f"Seq {nm} head",
            head_paras(k, hsize),
            Rect(cx[k] - hw // 2, body.y, hw, hh),
            V._text_style(
                c,
                hsize,
                fill=th.sequence_head_fill,
                line=th.sequence_head_line,
                line_width=1.0,
                radius=V._pt(V._emu("4pt")),
                color=head_ink,
                align="center",
                valign="middle",
                padding=f"{pad_pt:.2f}pt",
            ),
        )
    # messages: arrows first, then the labels over them (a label masks the lifelines it crosses)
    top = y0
    labels: list[tuple[str, Rect, Style, list[Paragraph]]] = []
    for x, w in zip(msgs, wts, strict=True):
        rowh = u * w
        role = _role(c, x.classes)
        color = (role.line if role and role.line else None) or acol
        ink = (role.color if role and role.color else None) or (color if role and role.line else "fg")
        k0, k1 = col[x.src], col[x.dst]
        group = lh + 3 * pt
        paras = (
            _sized([Paragraph(runs=[Run(text=x.label)])], size, bool(role and role.line)) if x.label else []
        )
        if x.is_self:
            lw_ = loop_w[0]
            loop_h = min(round(rowh * 0.7), round(1.6 * lh))
            ytop = round(top + (rowh - loop_h) / 2)
            ybot = ytop + loop_h
            xr = cx[k0] + lw_
            nm = f"Seq {x.idx} msg self"
            _conn(c, nm, (cx[k0], ytop), (xr, ytop), "h", 0.5, color, aw_pt, "none")
            _conn(c, nm + " 2", (xr, ytop), (xr, ybot), "v", 0.5, color, aw_pt, "none")
            _conn(c, nm + " 3", (xr, ybot), (cx[k0], ybot), "h", 0.5, color, aw_pt, "arrow")
            if paras:
                room = (cx[k0 + 1] if k0 + 1 < n else body.right) - xr - 8 * pt
                labels.append(
                    (
                        f"Seq {x.idx} label self",
                        Rect(xr + 4 * pt, (ytop + ybot) // 2 - lh // 2, max(round(room), 1), lh),
                        V._text_style(c, size, color=ink, align="left", valign="middle", padding="0pt"),
                        paras,
                    )
                )
        else:
            y = round(top + (rowh - group) / 2 + lh + 3 * pt)
            nm = f"Seq {x.idx} msg" + (" reply" if x.reply else "")
            _conn(
                c,
                nm,
                (cx[k0], y),
                (cx[k1], y),
                "h",
                0.5,
                color,
                aw_pt,
                "arrow",
                dash="dash" if x.reply else None,
            )
            if paras:
                span = abs(cx[k1] - cx[k0])
                lw_ = min(round(label_w(x, size)), span - 4 * pt)
                mid = (cx[k0] + cx[k1]) // 2
                labels.append(
                    (
                        f"Seq {x.idx} label" + (" reply" if x.reply else ""),
                        Rect(mid - lw_ // 2, y - 3 * pt - lh, max(lw_, 1), lh),
                        V._text_style(
                            c, size, fill="bg", color=ink, align="center", valign="middle", padding="0pt"
                        ),
                        paras,
                    )
                )
        top += rowh
    for nm, rect, st, paras in labels:
        V._emit_text(c, nm, paras, rect, st)
    info.update(n=m, parts=n, size=size, head=hsize, fit=fit)
    if not fit:
        c.over.append("@sequence text")
    return True


FORMS = {"swimlane": _swimlane, "sequence": _sequence}
