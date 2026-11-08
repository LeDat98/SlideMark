"""Composition vocabulary, wave 2026-11-08 lane C: ``@swimlane`` ``@sequence`` (editorial diagram types).

Same contract as ``vocab.py`` (which dispatches here): a composer works on the body rectangle with its own
context, names every shape it draws (``Lane 2``, ``Lane 2 head``, ``Lane 2 rule``, ``Step 4``, ``Step 4 tag``,
``Step 4 next``, ``Step 4 next label``; ``Seq Client head``, ``Seq Client tag``, ``Seq Client lifeline``,
``Seq Client act 1``, ``Seq 3 label``, ``Seq 3 msg``, ``Seq 3 msg reply``, ``Seq 3 msg self``;
``Legend ...``) so
``importer/vocab.py`` folds them back, reads every number from a token (``forms5.py``, ``forms6.py``) and
never raises on bad input (a slide that lacks what the form needs is laid out as ordinary blocks).

Diagram rules (diagram-design, see ``diagramkit.py``): compact node cards sized to their text and centred in
the body (never stretched to fill it), orthogonal connectors, hairline borders, no shadows, arrow kinds
(``>`` ``=>`` ``~>`` ``-->``) in slate / accent / link blue / dashed, mono capitals for tags and labels, a
legend strip when two or more roles or kinds are used.
"""

from __future__ import annotations

from typing import Any

from .. import forms, forms5
from ..ir import Paragraph, Run, Shape, Slide, Style, fast_style
from ..units import EMU_PER_PT
from . import diagramkit as DK
from . import vocab as V
from .grid import Rect

_K = 914400  # EMU per inch
PT = EMU_PER_PT


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
):
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
        attrs["under"] = True  # drawn under the cards; glued to them after the slide is rendered
    kw: dict[str, Any] = {"line_dash": dash} if dash and dash != "solid" else {}
    return c.emit(
        Shape(shape="line", attrs=attrs),
        Rect(min(p0[0], p1[0]), min(p0[1], p1[1]), abs(p1[0] - p0[0]), abs(p1[1] - p0[1])),
        fast_style(line=color, line_width=width_pt, **kw),
    )


def _kind_style(c, K: DK.Look, kind: str, base: str | None, base_w: Any, focal: bool = False):
    """``(colour, dash, width)`` of an arrow kind; ``base`` / ``base_w`` are the form's own default-arrow
    tokens (``swimlane.arrow`` ...), which only the plain ``>`` arrow takes."""
    col, dash, wd = DK.style_of(K, kind, focal)
    if kind == "flow" and not focal:
        col = base or col
        wd = V._pt(V._emu(base_w)) if base_w else wd
    return col, dash, wd


def _ja(slide: Slide, texts: list[str]) -> str | None:
    return "ja" if any(DK.has_wide(t) for t in texts) else None


# --------------------------------------------------------------------------- @swimlane


def _swimlane(c, slide: Slide, body: Rect, sg: int, info: dict) -> bool:
    th = c.theme
    lanes = forms5.lanes_of(slide) or []
    steps = forms5.steps_of(lanes)
    n, ncol = len(lanes), max(s.col for s in steps)
    vertical = forms.words(slide.attrs, "swimlane", "dir") == "v"
    K0 = DK.look(c, slide)
    pinned = bool(forms.num(slide.attrs, "size"))
    order = sorted(steps, key=lambda s: (s.col, s.idx))
    kind_of = {a.idx: a.kind for a in order[:-1]}
    used_kinds = sorted(set(kind_of.values()), key=DK.KINDS.index)
    roles = [r for r in DK.ROLES if any(r in s.classes for s in steps)]
    plain = any(not (set(s.classes) & set(DK.ROLES)) for s in steps)
    legend_on = DK.wants_legend(c, roles, used_kinds, slide)
    leg_h = DK.legend_height(K0) if legend_on else 0
    area = Rect(body.x, body.y, body.w, body.h - leg_h)
    heads = [x.title for x in lanes]
    head_text = [" ".join(p.plain.strip() for p in h.paragraphs) if h is not None else "" for h in heads]
    lane_pad = round(0.19 * _K)
    gap_pref = V._emu(th.swimlane_gap) if th.swimlane_gap else round(0.5 * _K)
    gap_min = min(gap_pref, round(0.3 * _K))

    def head_size(K: DK.Look) -> float:
        return th.swimlane_head_size or K.label

    def plan(k: float, wf: float, gap: int) -> dict[str, Any]:
        K = K0.scaled(k)
        tag_h = DK.tag_size(K, "X")[1]
        # every step is as wide as its text asks (a floor and a cap); the lane height / lane width is shared
        wi = {
            s.idx: max(
                round(min(max(DK.node_width(c, K, s.name, s.subs, s.tag), 1.3 * _K), 2.4 * _K) * wf),
                round(1.0 * _K),
            )
            for s in steps
        }
        if vertical:
            wi = dict.fromkeys(wi, max(wi.values()))

        def need(s) -> int:
            paras = DK.node_paras(c, K, s.name, s.subs)
            return DK.node_need(c, K, paras, wi[s.idx], bool(s.tag), tag_h, [*s.classes])

        hi = {s.idx: max(need(s), round(2.9 * K.name * PT)) for s in steps}
        if not vertical:
            hi = dict.fromkeys(hi, max(hi.values()))
        ea = {i: (hi[i] if vertical else wi[i]) for i in wi}  # extent along the flow, per step
        across = max(wi.values()) if vertical else max(hi.values())
        lp = lane_pad if vertical else min(lane_pad, max(round(0.05 * _K), (area.h // n - across) // 2))
        lane_a = across + 2 * lp
        ext: dict[int, int] = {}
        for s in steps:
            ext[s.col] = max(ext.get(s.col, 0), ea[s.idx])
        fill = sorted(ext.values())[len(ext) // 2]
        cols_ext = [ext.get(cc, fill) for cc in range(1, ncol + 1)]
        hs = head_size(K)
        cap_w = max((DK.small_w(K, t, hs, th.diagram_label_track) for t in head_text if t), default=0)
        if vertical:
            hw = V._emu(th.swimlane_head_w) if th.swimlane_head_w else round(hs * 3.4 * PT)
            hw = max(hw, round(0.4 * _K))
        else:
            hw = V._emu(th.swimlane_head_w) if th.swimlane_head_w else cap_w + round(0.3 * _K)
            hw = min(max(hw, round(0.9 * _K)), round(0.22 * body.w))
        flow = hw + sum(cols_ext) + ncol * gap
        cross = n * lane_a
        tw, tH = (cross, flow) if vertical else (flow, cross)
        ok = tw <= area.w * 1.01 and tH <= area.h * 1.01
        return {
            "K": K, "wi": wi, "hi": hi, "ea": ea, "across": across, "lane_a": lane_a, "hw": hw,
            "cols": cols_ext, "gap": gap, "tw": tw, "th": tH, "ok": ok, "tag_h": tag_h, "hs": hs,
        }  # fmt: skip

    ks = [1.0] if pinned else [1.0, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7]
    best = None
    for k in ks:
        for wf in (1.0, 0.85, 0.7, 0.6, 0.5, 0.4):
            for gap in (gap_pref, gap_min, min(gap_min, round(0.2 * _K))):
                best = plan(k, wf, gap)
                if best["ok"]:
                    break
            if best["ok"]:
                break
        if best["ok"]:
            break
    assert best is not None
    P = best
    K: DK.Look = P["K"]
    x0, y0 = DK.centred(area, P["tw"], P["th"])
    fr = _Frame(Rect(x0, y0, P["tw"], P["th"]), vertical)
    hw, L, gap = P["hw"], P["lane_a"], P["gap"]
    ea, across, cols_ext = P["ea"], P["across"], P["cols"]
    colx = [hw + gap / 2]  # frame x of each column cell
    for ext_ in cols_ext:
        colx.append(colx[-1] + ext_ + gap)
    aw_total = hw + sum(cols_ext) + ncol * gap
    n_lane_y = [i * L for i in range(n)]
    line_col, line_w = th.swimlane_line, V._pt(V._emu(th.swimlane_line_w))
    fills = V._colors(slide, th.swimlane_fill)
    # lanes: an invisible hit area each (a native, selectable lane), the hairline rules and the captions
    for i in range(n):
        c.emit(
            Shape(shape="rect", attrs={"shape_name": f"Lane {i + 1}"}),
            fr.rect(0, n_lane_y[i], aw_total, L),
            fast_style(fill=V._own(lanes[i], "fill") or V._pick(fills, i), line=None),
        )
    for i in range(n + 1):
        y = i * L
        a, b = fr.pt(0, y), fr.pt(aw_total, y)
        V._line(
            c,
            f"Lane {min(i + 1, n)} rule" if i < n else f"Lane {n} rule end",
            a[0],
            a[1],
            b[0],
            b[1],
            line_col,
            line_w,
        )
    a, b = fr.pt(hw, 0), fr.pt(hw, n * L)
    V._line(c, "Lane head rule", a[0], a[1], b[0], b[1], line_col, line_w)
    hs = P["hs"]
    for i in range(n):
        if not head_text[i]:
            continue
        ink = V._own(lanes[i], "color") or th.swimlane_head_color or K.muted
        rect = fr.rect(0, n_lane_y[i], hw, L)
        DK.emit_text(
            c,
            f"Lane {i + 1} head",
            [DK.small_para(c, K, head_text[i], hs, th.diagram_label_track, ink)],
            rect,
            V._text_style(
                c,
                hs,
                fill=th.swimlane_head_fill,
                align="center" if vertical else "left",
                valign="middle" if not vertical else "top",
                padding="4pt" if vertical else "0pt",
                **({} if vertical else {"padding_left": "9pt"}),
            ),
        )
    # steps: positions now, the cards after the arrows (which run under them)
    rect_of: dict[int, Rect] = {}
    frame_of: dict[int, tuple[float, float]] = {}
    for s in steps:
        cell = cols_ext[s.col - 1]
        fx = colx[s.col - 1] + (cell - ea[s.idx]) / 2
        fy = n_lane_y[s.lane] + (L - across) / 2
        frame_of[s.idx] = (fx, fy)
        rect_of[s.idx] = fr.rect(fx, fy, ea[s.idx], across)

    def draw_steps() -> None:
        for s in steps:
            extra = fast_style()
            if th.swimlane_step_fill:
                extra = extra.merged(fast_style(fill=th.swimlane_step_fill))
            if th.swimlane_step_line:
                extra = extra.merged(fast_style(line=th.swimlane_step_line))
            if th.swimlane_step_line_w:
                extra = extra.merged(fast_style(line_width=V._pt(V._emu(th.swimlane_step_line_w))))
            if th.swimlane_step_radius:
                extra = extra.merged(fast_style(radius=V._pt(V._emu(th.swimlane_step_radius))))
            DK.node(
                c, K, f"Step {s.idx}", f"Step {s.idx} tag", rect_of[s.idx],
                DK.node_paras(c, K, s.name, s.subs), s.tag, [*s.classes], extra=extra,
            )  # fmt: skip
            if th.swimlane_step_color:
                i = -2 if s.tag else -1
                c.out[i].style = c.out[i].style.merged(fast_style(color=th.swimlane_step_color))

    # arrows: consecutive steps in column order (ties: written order)
    taken = {(s.lane, s.col) for s in steps}
    margin = (L - across) / 2
    obstacles = list(rect_of.values())
    area_box = Rect(fr.body.x, fr.body.y, fr.body.w, fr.body.h)
    label_jobs: list[tuple[str, list[tuple[float, float]], str, str | None]] = []
    for a, b in zip(order, order[1:], strict=False):
        ax, ay = frame_of[a.idx]
        bx, by = frame_of[b.idx]
        acy, bcy = ay + across / 2, by + across / 2
        dc = b.col - a.col
        name = f"Step {a.idx} next"
        if a.lane == b.lane:
            if dc >= 1:
                p0, p1 = (ax + ea[a.idx], acy), (bx, bcy)
            else:
                p0, p1 = (ax, acy), (bx + ea[b.idx], bcy)
            route, adj = "h", 0.5
        elif dc >= 1:
            p0, p1 = (ax + ea[a.idx], acy), (bx, bcy)
            route = "h"
            dx = p1[0] - p0[0]
            # the horizontal run goes where no step is in the way: along a's lane, else along b's lane
            clear_a = not any((a.lane, k) in taken for k in range(a.col + 1, b.col))
            clear_b = not any((b.lane, k) in taken for k in range(a.col + 1, b.col))
            adj = 0.5 if dc == 1 else ((1 - (gap / 2) / dx) if clear_a or not clear_b else (gap / 2) / dx)
        elif dc == 0:
            down = b.lane > a.lane
            p0 = (ax + ea[a.idx] / 2, ay + across if down else ay)
            p1 = (bx + ea[b.idx] / 2, by if down else by + across)
            route, adj = "v", 0.5
        else:  # backwards: leave through the margin of a's lane, then along it to b
            down = b.lane > a.lane
            p0 = (ax + ea[a.idx] / 2, ay + across if down else ay)
            p1 = (bx + ea[b.idx] / 2, by if down else by + across)
            route = "v"
            adj = min((margin / 2) / max(abs(p1[1] - p0[1]), 1), 0.5)
        kind = kind_of[a.idx]
        col, dash, wd = _kind_style(c, K, kind, th.swimlane_arrow, th.swimlane_arrow_w)
        pl = _conn(
            c,
            name,
            fr.pt(*p0),
            fr.pt(*p1),
            ("v" if vertical else "h") if route == "h" else ("h" if vertical else "v"),
            adj,
            col,
            wd,
            "arrow",
            rect_of[a.idx],
            rect_of[b.idx],
            dash,
        )
        if a.label:
            label_jobs.append((name + " label", DK.polyline(pl), a.label, col if kind != "flow" else None))
    draw_steps()
    for nm_, poly_, text_, col_ in label_jobs:
        obstacles.append(DK.edge_label(c, K, nm_, poly_, text_, col_, obstacles, area_box))
    if legend_on:
        entries = DK.legend_entries(
            c, roles, used_kinds, plain and bool(roles), _ja(slide, [s.name for s in steps])
        )
        lw_ = min(max(P["tw"], DK.legend_width(K, entries)), body.w)
        lx = min(max(x0, body.x), body.right - lw_)
        DK.legend(c, K, lx, body.bottom - leg_h + round(6 * PT), lw_, entries)
    ok = P["ok"]
    info.update(n=len(steps), lanes=n, dir="v" if vertical else "h", size=K.name, head=hs, fit=ok)
    if not ok:
        c.over.append("@swimlane text")
    return True


# --------------------------------------------------------------------------- @sequence


def _sequence(c, slide: Slide, body: Rect, sg: int, info: dict) -> bool:
    th = c.theme
    parts, msgs = forms5.sequence_model(slide) or ([], [])
    n, m = len(parts), len(msgs)
    names = [p.name for p in parts]
    col = {nm: k for k, nm in enumerate(names)}
    K0 = DK.look(c, slide)
    pinned = bool(forms.num(slide.attrs, "size")) or bool(th.sequence_size)
    if th.sequence_size:
        K0 = DK.Look(th, th.sequence_size, K0.sub, K0.tag, K0.label, K0.legend)
    kinds = [("primary" if "focal" in x.classes else x.kind) for x in msgs]
    used_kinds = sorted(set(kinds), key=DK.KINDS.index)
    roles = [r for r in DK.ROLES if any(r in p.classes for p in parts)]
    plain = any(not (set(p.classes) & set(DK.ROLES)) for p in parts)
    # activation: a participant is busy from a request it receives to its reply to that sender
    acts: list[tuple[int, int, int]] = []  # (participant, first message row, last message row)
    closing: set[int] = set()  # rows that answer a request: they never open a bar of their own
    for j, x in enumerate(msgs):
        if x.is_self or x.kind == "return" or j in closing:
            continue
        dst = col[x.dst]
        end = next(
            (
                i
                for i in range(j + 1, m)
                if msgs[i].src == x.dst and msgs[i].dst == x.src and not msgs[i].is_self
            ),
            None,
        )
        if end is not None:
            closing.add(end)
        elif j + 1 < m and msgs[j + 1].src == x.dst:  # no reply, but the receiver goes on working
            end = j + 1
        else:
            continue
        acts.append((dst, j, end))
    legend_on = DK.wants_legend(c, roles, used_kinds + (["act"] if acts else []), slide)
    leg_h = DK.legend_height(K0) if legend_on else 0
    area = Rect(body.x, body.y, body.w, body.h - leg_h)
    act_w = V._emu(th.diagram_act_w)
    wts = [1.5 if x.is_self else 1.0 for x in msgs]

    def plan(k: float) -> dict[str, Any]:
        K = K0.scaled(k)
        tag_h = DK.tag_size(K, "X")[1]
        nat = max(DK.node_width(c, K, p.name, p.sub, p.tag) for p in parts)
        hw = round(min(max(nat, 1.4 * _K), 2.4 * _K))
        hh = max(
            DK.node_need(c, K, DK.node_paras(c, K, p.name, p.sub), hw, bool(p.tag), tag_h, p.classes)
            for p in parts
        )
        hh = max(hh, round(2.9 * K.name * PT))
        pitch = hw + round(0.45 * _K)
        for x in msgs:
            if x.label and not x.is_self:
                span = abs(col[x.dst] - col[x.src])
                need = DK.small_w(K, x.label, K.label, th.diagram_label_track) + round(0.5 * _K)
                pitch = max(pitch, need // max(span, 1))
        pitch = min(pitch, round(3.6 * _K))
        gap = V._emu(th.sequence_gap) if th.sequence_gap else 0
        if gap:
            pitch = hw + gap
        tw = (n - 1) * pitch + hw
        if tw > area.w:
            pitch = (area.w - hw) // max(n - 1, 1)
            tw = (n - 1) * pitch + hw
        top_gap = round(0.28 * _K)
        free = area.h - hh - top_gap - round(0.2 * _K)
        u = free / sum(wts)
        u = min(u, 0.72 * _K)
        u_min = max(round(K.label * 1.6 * PT) + round(16 * PT), round(0.36 * _K))
        ok = u >= u_min and pitch >= hw * 0.9
        th_ = hh + top_gap + sum(wts) * u + round(0.2 * _K)
        return {
            "K": K,
            "hw": hw,
            "hh": hh,
            "pitch": pitch,
            "tw": tw,
            "u": u,
            "ok": ok,
            "th": th_,
            "tag_h": tag_h,
        }

    ks = [1.0] if pinned else [1.0, 0.95, 0.9, 0.85, 0.8, 0.75]
    best = None
    for k in ks:
        best = plan(k)
        if best["ok"]:
            break
    assert best is not None
    P = best
    K = P["K"]
    hw, hh, pitch, u = P["hw"], P["hh"], P["pitch"], P["u"]
    x0, y0 = DK.centred(area, P["tw"], round(P["th"]))
    cx = [x0 + hw // 2 + k * pitch for k in range(n)]
    life_top = y0 + hh
    rows_top = y0 + hh + round(0.28 * _K)
    life_bot = round(rows_top + sum(wts) * u + 0.12 * _K)
    ys: list[float] = []  # the arrow y of every message (a self-message: the top of its loop)
    t = rows_top
    for x, w in zip(msgs, wts, strict=True):
        ys.append(t + (0.3 if x.is_self else 0.64) * u)
        t += u * w
    # lifelines first (behind everything), then the heads, then the activation bars
    ll_w = V._pt(V._emu(th.sequence_lifeline_w))
    for k, p in enumerate(parts):
        _conn(
            c,
            f"Seq {p.name} lifeline",
            (cx[k], life_top),
            (cx[k], life_bot),
            "v",
            0.5,
            th.sequence_lifeline,
            ll_w,
            "none",
            dash="dash",
        )
    for k, p in enumerate(parts):
        extra = fast_style()
        if th.sequence_head_fill:
            extra = extra.merged(fast_style(fill=th.sequence_head_fill))
        if th.sequence_head_line:
            extra = extra.merged(fast_style(line=th.sequence_head_line))
        DK.node(
            c, K, f"Seq {p.name} head", f"Seq {p.name} tag", Rect(cx[k] - hw // 2, y0, hw, hh),
            DK.node_paras(c, K, p.name, p.sub), p.tag, p.classes, extra=extra,
        )  # fmt: skip
        if th.sequence_head_color:
            i = -2 if p.tag else -1
            c.out[i].style = c.out[i].style.merged(fast_style(color=th.sequence_head_color))
    busy: dict[int, list[tuple[float, float]]] = {}
    for k, a, b in acts:
        y_a, y_b = ys[a] - 3 * PT, ys[b] + 4 * PT
        if b == a:
            y_b = y_a + 0.5 * u
        busy.setdefault(k, []).append((y_a, y_b))
        c.emit(
            Shape(shape="rect", attrs={"shape_name": f"Seq {names[k]} act {len(busy[k])}"}),
            Rect(cx[k] - act_w // 2, round(y_a), act_w, round(y_b - y_a)),
            fast_style(fill=th.diagram_act_fill, line=th.diagram_act_line, line_width=DK.hairline(c)),
        )

    def on_bar(k: int, y: float) -> bool:
        return any(a - 1 <= y <= b + 1 for a, b in busy.get(k, []))

    # messages: arrows, then the labels
    obstacles: list[Rect] = []
    area_box = Rect(x0 - round(0.2 * _K), y0, P["tw"] + round(0.4 * _K), life_bot - y0)
    lh = round(K.label * 1.6 * PT)
    for x, y in zip(msgs, ys, strict=True):
        k0, k1 = col[x.src], col[x.dst]
        focal = "focal" in x.classes
        colr, dash, wd = _kind_style(c, K, x.kind, th.sequence_arrow, th.sequence_arrow_w, focal)
        label_col = colr if (x.kind != "flow" or focal) else None
        yy = round(y)
        if x.is_self:
            loop_w = round(0.42 * _K)
            xl = cx[k0] + (act_w // 2 if on_bar(k0, y) else 0)
            xr = xl + loop_w
            ybot = round(y + 0.7 * u)
            nm = f"Seq {x.idx} msg self"
            _conn(c, nm, (xl, yy), (xr, yy), "h", 0.5, colr, wd, "none", dash=dash)
            _conn(c, nm + " 2", (xr, yy), (xr, ybot), "v", 0.5, colr, wd, "none", dash=dash)
            _conn(c, nm + " 3", (xr, ybot), (xl, ybot), "h", 0.5, colr, wd, "arrow", dash=dash)
            if x.label:
                tw_ = DK.small_w(K, x.label, K.label, th.diagram_label_track) + round(6 * PT)
                rect = Rect(xr + round(6 * PT), (yy + ybot) // 2 - lh // 2, tw_, lh)
                DK.emit_text(
                    c,
                    f"Seq {x.idx} label self",
                    [DK.small_para(c, K, x.label, K.label, th.diagram_label_track, label_col)],
                    rect,
                    V._text_style(c, K.label, align="left", valign="middle", padding="0pt"),
                    nowrap=True,
                )
                obstacles.append(rect)
            continue
        sgn = 1 if k1 > k0 else -1
        xa = cx[k0] + (sgn * act_w // 2 if on_bar(k0, y) else 0)
        xb = cx[k1] - (sgn * act_w // 2 if on_bar(k1, y) else 0)
        nm = f"Seq {x.idx} msg" + (" reply" if x.reply else "")
        pl = _conn(c, nm, (xa, yy), (xb, yy), "h", 0.5, colr, wd, "arrow", dash=dash)
        if x.label:
            r = DK.edge_label(
                c,
                K,
                f"Seq {x.idx} label" + (" reply" if x.reply else ""),
                DK.polyline(pl),
                x.label,
                label_col,
                obstacles,
                area_box,
            )
            obstacles.append(r)
    if legend_on:
        entries = DK.legend_entries(
            c, roles, used_kinds, plain and bool(roles), _ja(slide, names), act=bool(acts)
        )
        lw_ = min(max(P["tw"], DK.legend_width(K, entries)), body.w)
        lx = min(max(x0, body.x), body.right - lw_)
        DK.legend(c, K, lx, body.bottom - leg_h + round(6 * PT), lw_, entries)
    ok = P["ok"]
    info.update(n=m, parts=n, size=K.name, head=K.name, fit=ok)
    if not ok:
        c.over.append("@sequence text")
    return True


FORMS = {"swimlane": _swimlane, "sequence": _sequence}

_ = (Paragraph, Run)
