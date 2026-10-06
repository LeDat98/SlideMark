"""Chart takeaway (``note=`` / ``hl=``): where the plot area, the bars and the callout are.

One module, two users. The renderer pins the plot area of a chart with a ``note=`` (``c:manualLayout``,
layout target inner) and the value axis (explicit min / max), so every bar position is computable. The layout
turns the same numbers into native items: a ``chart-note`` text box in an empty corner of the plot and a thin
connector to the first ``hl=`` point (``expand_notes``, called at the end of the slide layout). Both call
:func:`plan`, so they can never disagree. Everything is frame-relative EMU until the items are placed.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field

from ..ir import Chart, Paragraph, Placed, Run, Shape, Text, fast_style
from ..render import waterfall as wfall
from ..render.axis import axis_shown, label_pt, line_axis, resolve_axis
from ..theme import DEFAULT_SIZES, Theme
from ..units import EMU_PER_PT
from . import css, measure

BARS = ("bar", "column", "stacked-bar", "stacked-column", "waterfall")
PLOTTED = (*BARS, "line", "area")
HORIZONTAL = ("bar", "stacked-bar")
NOTE_CLASS = "chart-note"
NOTE_ID = "ChartNote"
LINE_ID = "ChartNoteLine"
_SAMPLES = 24
_FIT_STEP = 0.5  # pt, note text shrinks in these steps

Rect = tuple[float, float, float, float]


@dataclass
class NotePlan:
    """Everything a ``note=`` needs, in absolute EMU (``items``) or as chart fractions (``plot``)."""

    plot: tuple[float, float, float, float] | None = None  # inner plot area: x, y, w, h as frame fractions
    axis: tuple[float | None, float | None, float | None] | None = None  # (min, max, major unit) to pin
    items: list[Placed] = field(default_factory=list)  # the note (+ its pointer)
    warnings: list[tuple[str, str]] = field(default_factory=list)  # (message, hint)


# --------------------------------------------------------------------------- small helpers


def _num(v) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def chart_size(pl: Placed, theme: Theme) -> float:
    """Chart text size in pt, as the renderer computes it."""
    return (pl.style.font_size or theme.sizes.get("table", DEFAULT_SIZES["table"])) * pl.font_scale


def resolve_hl(ch: Chart, cats: list[str]) -> list[int]:
    """Indexes of the ``hl=`` categories in ``cats`` (exact, else case-insensitive); others are skipped."""
    raw = ch.options.get("hl") or []
    names = [raw] if isinstance(raw, str) else list(raw)
    stripped = [str(c).strip() for c in cats]
    folded = [c.casefold() for c in stripped]
    out: list[int] = []
    for n in names:
        n = str(n).strip()
        i = (
            stripped.index(n)
            if n in stripped
            else folded.index(n.casefold())
            if n.casefold() in folded
            else -1
        )
        if i >= 0 and i not in out:
            out.append(i)
    return out


def _flag(v) -> bool:
    return str(v).strip().lower() in ("1", "true", "on", "yes", "y")


def _legend(opts: dict, nseries: int) -> str | None:
    leg = opts.get("legend")
    if isinstance(leg, str) and leg.strip().lower() in ("bottom", "top", "left", "right"):
        return leg.strip().lower()
    if isinstance(leg, str) and leg.strip().lower() in ("none", "off", "false", "no", "0"):
        return None
    if leg is not None:
        return "bottom"
    return "bottom" if nseries > 1 else None


# --------------------------------------------------------------------------- data of a plotted chart


@dataclass
class _Data:
    kind: str
    cats: list[str]
    ext: list[tuple[float, float] | None]  # per category: value interval the mark covers (None: no mark)
    above: list[bool]  # a label sits beyond the high end of the interval
    below: list[bool]  # ... beyond the low end
    nser: int  # series drawn side by side in a category (1 for stacked kinds and waterfalls)
    axis: tuple[float | None, float | None, float | None]
    labels: bool
    fmt: str | None
    nlegend: int


def _data(ch: Chart, theme: Theme) -> _Data | None:
    from ..render.objects import flag, stack_totals  # lazy: the renderer imports this module

    rt = theme.render
    kind = ch.kind
    opts = {str(k).lower().replace("-", "_"): v for k, v in ch.options.items()}
    labels = opts.get("labels", opts.get("data_labels"))
    lab_on = flag(labels) and not (isinstance(labels, str) and labels.strip().lower() == "percent")
    fmt = opts.get("fmt") or opts.get("number_format") or opts.get("format")
    fmt = str(fmt) if fmt else None
    cats = [str(c) for c in ch.categories]
    series = list(ch.series)
    n = max([len(cats), *(len(s.values) for s in series)], default=0)
    if n == 0 or not series:
        return None
    cats += [str(i + 1) for i in range(len(cats), n)]
    lo, hi = _num(opts.get("min")), _num(opts.get("max"))
    ext: list[tuple[float, float] | None] = [None] * n
    above, below = [False] * n, [False] * n
    nser = 1
    if kind == "waterfall":
        totals = [int(i) for i in ch.options.get("totals", []) if isinstance(i, (int, float))]
        bs = wfall.bars([_num(v) for v in series[0].values], totals)
        wf_axis = wfall.axis(bs, rt)
        for i, (bk, blo, bhi, _shown) in enumerate(bs[:n]):
            if bk == "gap":
                continue
            ext[i] = (blo, bhi)
            neg = bhi <= 0 and blo < 0
            above[i], below[i] = lab_on and not neg, lab_on and neg
        axis = resolve_axis(kind, [], rt, lo, hi, wf_axis, True, ncat=n)
        return _Data(kind, cats, ext, above, below, 1, axis, lab_on, fmt, 1)
    drawn = stack_totals(ch, series, lab_on, opts, rt) if kind.startswith("stacked") else series
    vals = [[_num(v) for v in s.values] + [None] * (n - len(s.values)) for s in series]
    stacked = kind.startswith("stacked")
    for i in range(n):
        col = [v[i] for v in vals if v[i] is not None]
        if not col:
            continue
        if stacked:
            ext[i] = (sum(v for v in col if v < 0), sum(v for v in col if v > 0))
            above[i] = lab_on and len(drawn) > len(series)  # the hidden carrier labels the stack total
        elif kind == "line":
            near = [col[0]]
            for j in (i - 1, i + 1):
                if 0 <= j < n:
                    other = [v[j] for v in vals if v[j] is not None]
                    near += [(c + o) / 2 for c in col for o in other]
            ext[i] = (min(near), max(near))
            above[i] = lab_on
        else:
            ext[i] = (min(0.0, min(col)), max(0.0, max(col)))
            above[i], below[i] = lab_on and max(col) > 0, lab_on and min(col) < 0
    if not stacked and kind != "area":
        nser = len(series)
    nonneg = all(v is None or v >= 0 for s in vals for v in s)
    tight = not axis_shown(opts, kind, n, lab_on, rt)
    axis = resolve_axis(kind, [s.values for s in drawn], rt, lo, hi, None, nonneg and bool(vals), n, tight)
    if kind == "line" and (axis[0] is None or axis[1] is None):
        la = line_axis(vals, rt)
        if la:
            axis = (lo if lo is not None else la[0], hi if hi is not None else la[1], la[2])
    return _Data(kind, cats, ext, above, below, nser, axis, lab_on, fmt, len(series))


# --------------------------------------------------------------------------- plot area


def _text_w(text: str, size_pt: float, bold: bool = False) -> float:
    return measure.text_em(text, bold=bold) * size_pt * EMU_PER_PT


def _num_text(v: float, fmt: str | None) -> str:
    return wfall.fmt_num(v, fmt, sign=False)


def plot_fractions(
    ch: Chart, d: _Data, W: int, H: int, size: float, theme: Theme
) -> tuple[float, float, float, float]:
    """The inner plot area as fractions of the chart frame, from text sizes alone (no renderer feedback)."""
    lt = theme.layout
    em = size * EMU_PER_PT
    top = (lt.chart_note_title_em if ch.title else lt.chart_note_top_em) * em
    bottom = lt.chart_note_axis_em * em
    left = right = lt.chart_note_edge_em * em
    axis_on = axis_shown(ch.options, d.kind, len(d.cats), d.labels, theme.render)
    lo, hi, _ = d.axis
    ticks = [_num_text(v, d.fmt) for v in (lo, hi) if v is not None]
    tick_w = max((_text_w(t, size) for t in ticks), default=0.0)
    if d.kind in HORIZONTAL:
        cat_w = max((_text_w(c, size) for c in d.cats), default=0.0)
        left = min(cat_w + lt.chart_note_val_em * em, 0.4 * W)
        if not axis_on:
            bottom = lt.chart_note_edge_em * em
    elif axis_on:
        left = tick_w + lt.chart_note_val_em * em
    leg = _legend(ch.options, d.nlegend)
    if leg in ("top", "bottom"):
        top, bottom = (
            (top + lt.chart_note_legend_em * em, bottom)
            if leg == "top"
            else (
                top,
                bottom + lt.chart_note_legend_em * em,
            )
        )
    elif leg in ("left", "right"):
        names = [s.name for s in ch.series]
        w = max((_text_w(n, size) for n in names), default=0.0) + 3 * em
        left, right = (left + w, right) if leg == "left" else (left, right + w)
    x, y = left / W, top / H
    return x, y, max(1 - x - right / W, 0.1), max(1 - y - bottom / H, 0.1)


# --------------------------------------------------------------------------- geometry of marks


@dataclass
class _Marks:
    plot: Rect
    rects: list[Rect | None]  # per category: what is drawn there (label included)
    target: list[tuple[float, float] | None]  # per category: where a pointer ends (edge facing the note)
    edges: list[
        tuple[tuple[float, float], tuple[float, float]] | None
    ]  # horizontal bars: (top, bottom) points
    x_of: Callable[[float], float]
    y_of: Callable[[float], float]


def _marks(ch: Chart, d: _Data, frac, W: int, H: int, size: float, theme: Theme) -> _Marks | None:
    rt = theme.render
    lo, hi, _ = d.axis
    if lo is None or hi is None or hi <= lo:
        return None
    px, py, pw, ph = frac[0] * W, frac[1] * H, frac[2] * W, frac[3] * H
    n = len(d.cats)
    lab = label_pt(d.kind, n, size, rt)
    lab_h = lab * 1.45 * EMU_PER_PT
    lab_w = [
        _text_w(_num_text(max(abs(e[0]), abs(e[1])), d.fmt), lab) + 0.8 * lab * EMU_PER_PT if e else 0.0
        for e in d.ext
    ]
    gw = ch.options.get("gap_width")
    gap = (
        _num(gw)
        if _num(gw) is not None
        else (rt.chart_gap_few if n <= rt.chart_gap_few_cats else rt.chart_gap)
    )
    share = d.nser / (d.nser + gap / 100) if d.kind in BARS else 1.0
    air = 0.2 * size * EMU_PER_PT
    rects: list[Rect | None] = []
    target: list[tuple[float, float] | None] = []
    edges: list[tuple[tuple[float, float], tuple[float, float]] | None] = []
    if d.kind in HORIZONTAL:

        def vx(v: float) -> float:
            return px + pw * (v - lo) / (hi - lo)

        def vy(v: float) -> float:
            return 0.0

        slot = ph / n
        for i, e in enumerate(d.ext):
            if e is None:
                rects.append(None)
                target.append(None)
                edges.append(None)
                continue
            cy = py + (i + 0.5) * slot
            half = max(slot * share / 2, lab_h / 2)
            xl = vx(e[0]) - (lab_w[i] if d.below[i] else 0)
            xr = vx(e[1]) + (lab_w[i] if d.above[i] else 0)
            rects.append((xl, cy - half, xr, cy + half))
            target.append((xr + air, cy))
            if d.nser == 1:  # a pointer from above or below lands on the bar edge, near the bar's end
                bar_h = slot * share / 2
                neg = e[1] <= 0 and e[0] < 0
                end, root = (vx(e[0]), vx(e[1])) if neg else (vx(e[1]), vx(e[0]))
                inset = min(theme.layout.chart_note_land_em * size * EMU_PER_PT, abs(end - root) / 2)
                x = end + inset if neg else end - inset
                edges.append(((x, cy - bar_h), (x, cy + bar_h)))
            else:
                edges.append(None)
        return _Marks((px, py, px + pw, py + ph), rects, target, edges, vx, vy)

    def vy2(v: float) -> float:
        return py + ph * (1 - (v - lo) / (hi - lo))

    slot = pw / n
    for i, e in enumerate(d.ext):
        if e is None:
            rects.append(None)
            target.append(None)
            continue
        cx = px + (i + 0.5) * slot
        half = max(slot * share / 2, lab_w[i] / 2 if d.above[i] or d.below[i] else 0)
        yt = vy2(e[1]) - (lab_h if d.above[i] else 0)
        yb = vy2(e[0]) + (lab_h if d.below[i] else 0)
        if d.kind == "line":
            yb = max(yb, vy2(e[0]) + 0.4 * size * EMU_PER_PT)
        rects.append((cx - half, yt, cx + half, yb))
        target.append((cx, yt - air))
    return _Marks((px, py, px + pw, py + ph), rects, target, [None] * n, lambda v: 0.0, vy2)


# --------------------------------------------------------------------------- segment labels


def seg_fits(ch: Chart, pl: Placed, theme: Theme, pt: float) -> dict[tuple[int, int], bool]:
    """(series, category) -> whether a ``pt`` label fits inside its segment of a stacked chart (estimated
    from the same plot geometry as the note). Absent keys: no segment (missing or zero value)."""
    out: dict[tuple[int, int], bool] = {}
    d = _data(ch, theme)
    if d is None or not ch.kind.startswith("stacked") or pl.w <= 0 or pl.h <= 0:
        return out
    lo, hi, _ = d.axis
    if lo is None or hi is None or hi <= lo:
        return out
    rt = theme.render
    size = chart_size(pl, theme)
    px, py, pw, ph = plot_fractions(ch, d, pl.w, pl.h, size, theme)
    px, py, pw, ph = px * pl.w, py * pl.h, pw * pl.w, ph * pl.h
    n = len(d.cats)
    gw = ch.options.get("gap_width")
    gap = (
        _num(gw)
        if _num(gw) is not None
        else (rt.chart_gap_few if n <= rt.chart_gap_few_cats else rt.chart_gap)
    )
    thick = (ph if ch.kind in HORIZONTAL else pw) / max(n, 1) / (1 + gap / 100)
    along = pw if ch.kind in HORIZONTAL else ph
    lab_h = pt * rt.chart_seg_pad * EMU_PER_PT
    for si, s in enumerate(ch.series):
        for ci, v in enumerate(s.values):
            f = _num(v)
            if not f:
                continue
            seg = abs(f) / (hi - lo) * along
            text_w = _text_w(_num_text(f, d.fmt), pt) + 0.6 * pt * EMU_PER_PT
            if ch.kind in HORIZONTAL:
                out[(si, ci)] = seg >= text_w and thick >= lab_h
            else:
                out[(si, ci)] = seg >= lab_h and thick >= text_w
    return out


# --------------------------------------------------------------------------- the note itself


def _variants(text: str, size0: float, floor: float, maxw: float, style, theme: Theme):
    """(font size, width, height, fits) candidates: full size, shrinking to the floor, then two lines."""
    pad_h, pad_v = css.inset_hv(style)
    slack = measure.SAFETY * theme.layout.chart_note_slack
    cjk = measure.has_cjk(text)
    lt = measure.tokens()
    lh = lt.line_cjk if cjk else lt.line_latin
    s = size0
    sizes = []
    while s > floor + 1e-6:
        sizes.append(s)
        s -= _FIT_STEP
    sizes.append(floor)
    for s in sizes:
        w = _text_w(text, s, bold=True) * slack + pad_h
        if w <= maxw:
            yield s, w, s * lh * EMU_PER_PT + pad_v, True
    paras = [Paragraph(runs=[Run(text=text)])]
    st2 = style.merged(fast_style(font_size=floor))
    w = max((_text_w(text, floor, bold=True) / 2) * slack + pad_h, pad_h * 2)
    while w <= maxw + 1:
        h = measure.paragraphs_height(paras, w - pad_h, st2, 1.0)
        if h <= 2 * floor * lh * EMU_PER_PT * measure.SAFETY * 1.02:
            yield floor, w, 2 * floor * lh * EMU_PER_PT + pad_v, True
            return
        w += max(floor * EMU_PER_PT, 1)
    yield floor, maxw, 3 * floor * lh * EMU_PER_PT + pad_v, False  # too long: reported, drawn anyway


def _hit(a: Rect, b: Rect, m: float = 0.0) -> bool:
    return a[0] < b[2] + m and b[0] < a[2] + m and a[1] < b[3] + m and b[1] < a[3] + m


def _crosses(p: tuple[float, float], q: tuple[float, float], rects: list[Rect]) -> bool:
    for k in range(1, _SAMPLES):
        t = k / _SAMPLES
        x, y = p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t
        if any(r[0] < x < r[2] and r[1] < y < r[3] for r in rects):
            return True
    return False


def _start(rect: Rect, to: tuple[float, float]) -> tuple[float, float]:
    """The point of the note's outline that faces ``to``."""
    x = min(max(to[0], rect[0]), rect[2])
    y = min(max(to[1], rect[1]), rect[3])
    if rect[0] < to[0] < rect[2] and rect[1] < to[1] < rect[3]:
        return to
    return x, y


def _candidates(
    horizontal: bool, plot: Rect, w: float, h: float, tgt, step: float, room: float, lead: float = 0.0
):
    """Note rectangles in order of preference (the first free one wins)."""
    px0, py0, px1, py1 = plot
    out: list[Rect] = []
    right = px1 - room - w
    if horizontal:
        ys = [py0 + room + k * step for k in range(int(max(py1 - py0 - 2 * room - h, 0) / step) + 1)]
        if tgt:
            ys.sort(key=lambda y: abs(y + h / 2 - tgt[1]))
        left = px0 + room
        xs0 = [right]
        k = 1
        while right - k * w / 4 >= left and k < 16:  # slide the note left, towards the bars it may sit beside
            xs0.append(right - k * w / 4)
            k += 1
        for y in ys:
            xs = list(xs0)
            if tgt and tgt[0] + room + 0 < right:
                xs.insert(0, tgt[0] + room)
            out += [(x, y, x + w, y + h) for x in xs]
        return out
    xs = [px0 + room + k * step for k in range(int(max(px1 - px0 - 2 * room - w, 0) / step) + 1)]
    xs.sort(key=lambda x: abs(x + w / 2 - tgt[0]) if tgt else -x)
    xs = [right, *[x for x in xs if abs(x - right) > 1]]
    for k in range(int(max(py1 - py0 - 2 * room - h, 0) / (step)) + 1):
        y = py0 + room + k * step
        out += [(x, y, x + w, y + h) for x in xs]
    return out


def plan(ch: Chart, pl: Placed, theme: Theme) -> NotePlan | None:
    """The takeaway of ``ch`` (placed as ``pl``), or ``None`` without a ``note=``. Never raises."""
    note = str(ch.options.get("note") or "").strip()
    if not note or pl.w <= 0 or pl.h <= 0:
        return None
    try:
        return _plan(ch, pl, theme, note)
    except Exception as e:  # never break a build over a callout
        res = NotePlan()
        res.warnings.append(
            (f"chart note could not be placed ({type(e).__name__})", "shorten the note or drop hl=")
        )
        return res


def _plan(ch: Chart, pl: Placed, theme: Theme, note: str) -> NotePlan:
    rt, lt = theme.render, theme.layout
    size = chart_size(pl, theme)
    W, H = pl.w, pl.h
    res = NotePlan()
    em = size * EMU_PER_PT
    base = theme.classes.get(NOTE_CLASS) or fast_style()
    font = pl.style.font
    note_style = base.merged(fast_style(font=font)) if font else base
    floor = size  # never smaller than the category / axis labels (they use the chart text size)
    size0 = max(size * rt.chart_label_scale + rt.chart_note_size_add, floor)
    d = _data(ch, theme) if ch.kind in PLOTTED else None
    frac = plot_fractions(ch, d, W, H, size, theme) if d else None
    marks = _marks(ch, d, frac, W, H, size, theme) if d and frac else None
    if d and frac and marks:
        res.plot = frac
        res.axis = d.axis
    horizontal = ch.kind in HORIZONTAL
    if marks:
        plot = marks.plot
    else:  # pie, scatter ...: the frame below the title
        top = (lt.chart_note_title_em if ch.title else lt.chart_note_top_em) * em
        edge = lt.chart_note_edge_em * em
        plot = (edge, top, W - edge, H - edge)
    room = 0.3 * em
    maxw = min(lt.chart_note_max_w * (plot[2] - plot[0]), plot[2] - plot[0] - 2 * room)
    lift = max(lt.chart_note_inset_em * em - room, 0.0)  # clear of the title / top axis line
    right = W - room if horizontal and marks else plot[2]  # horizontal bars may use the right margin
    area = (plot[0], plot[1] + lift, right, plot[3])
    hl = resolve_hl(ch, d.cats if d else [str(c) for c in ch.categories])
    hi_ = hl[0] if hl else None
    tgt = marks.target[hi_] if marks and hi_ is not None and marks.target[hi_] else None
    obstacles = [(i, r) for i, r in enumerate(marks.rects) if r] if marks else []
    margin = lt.chart_note_gap_em * em
    lead = lt.chart_note_line_em * em * 0.6 + 1
    solid = [r for _, r in obstacles]
    solid_other = [r for i, r in obstacles if i != hi_]
    options: list[tuple[str, tuple[float, float]]] = []
    if tgt:
        options.append(("end", tgt))
    if horizontal and marks and hi_ is not None and marks.edges[hi_]:
        top, bottom = marks.edges[hi_]
        options += [("top", top), ("bottom", bottom)]
    chosen = None
    first = None
    fits = True
    line_to = tgt
    best = math.inf  # pointer length of ``chosen``
    for s, w, h, ok in _variants(note, size0, floor, maxw, note_style, theme):
        if chosen and s < chosen[0] - lt.chart_note_shrink_pt:
            break  # a smaller note is only worth it for a clearly nearer spot
        step = max(h / 2, 1.0)
        stop = False  # a pointer along the bar, or a note without bars: the first spot wins
        for kind, aim in options or [("none", None)]:
            for rect in _candidates(horizontal, area, w, h, aim, step, room, lead):
                if first is None:
                    first, fits = (s, rect), ok
                if rect[2] > area[2] - room + 1 or rect[3] > area[3] - room + 1:
                    continue
                if any(_hit(rect, r, margin) for r in solid):
                    continue
                length = 0.0
                if aim:
                    if (
                        horizontal
                        and kind == "end"
                        and not (rect[1] <= aim[1] <= rect[3] and rect[0] > aim[0])
                    ):
                        continue  # beside the value label, pointing along the bar
                    if kind == "top" and not (
                        rect[3] < aim[1] and rect[0] + room <= aim[0] <= rect[2] - room
                    ):
                        continue  # above the bar, the pointer drops straight onto it
                    if kind == "bottom" and not (
                        rect[1] > aim[1] and rect[0] + room <= aim[0] <= rect[2] - room
                    ):
                        continue
                    st = _start(rect, aim)
                    length = math.hypot(aim[0] - st[0], aim[1] - st[1])
                    if length < lt.chart_note_line_em * em * 0.5:
                        continue
                    if _crosses(st, aim, solid_other):
                        continue
                if chosen is None or length < best - 2 * em:
                    chosen, line_to, best = (s, rect, ok), aim, length
                stop = kind in ("end", "none")
                break
            if stop:
                break
        if chosen and (stop or best <= 2 * em):
            break
    if chosen is None and tgt:
        line_to = tgt
    if chosen is None and first is not None:
        chosen = (first[0], first[1], fits)
        if marks:
            res.warnings.append(
                (
                    "chart note covers part of the chart",
                    "shorten the note, or lower the data (max= on the axis)",
                )
            )
    if chosen is None:
        return res
    s, rect, ok = chosen
    if not ok:
        res.warnings.append(
            (f"chart note is too long for the chart: '{note[:24]}...'", "shorten note= to one short sentence")
        )
    st_note = note_style.merged(fast_style(font_size=s))
    x0, y0 = pl.x + round(rect[0]), pl.y + round(rect[1])
    nw, nh = round(rect[2] - rect[0]), round(rect[3] - rect[1])
    res.items.append(
        Placed(
            element=Text(
                id=NOTE_ID,
                role="body",
                classes=[NOTE_CLASS],
                paragraphs=[Paragraph(runs=[Run(text=note)])],
                attrs={"chart_note": True},
            ),
            x=x0,
            y=y0,
            w=nw,
            h=nh,
            style=st_note,
        )
    )
    if line_to:
        tgt = line_to
        a = _start(rect, tgt)
        if math.hypot(tgt[0] - a[0], tgt[1] - a[1]) > 1:
            lx, ly = pl.x + round(min(a[0], tgt[0])), pl.y + round(min(a[1], tgt[1]))
            res.items.append(
                Placed(
                    element=Shape(
                        id=LINE_ID,
                        shape="line",
                        attrs={
                            "head": "arrow",
                            "flip_h": a[0] > tgt[0],
                            "flip_v": a[1] > tgt[1],
                            "chart_note": True,
                        },
                    ),
                    x=lx,
                    y=ly,
                    w=round(abs(tgt[0] - a[0])),
                    h=round(abs(tgt[1] - a[1])),
                    style=fast_style(line=note_style.line, line_width=rt.chart_note_line_width),
                )
            )
    return res


# --------------------------------------------------------------------------- layout hook


def expand_notes(
    out: list[Placed], theme: Theme, diag: Callable[[str, str], None] | None = None
) -> list[Placed]:
    """Add the note (and pointer) of every chart that has a ``note=`` right after the chart."""
    res: list[Placed] = []
    count = 0
    for pl in out:
        res.append(pl)
        if not (isinstance(pl.element, Chart) and pl.element.options.get("note")):
            continue
        got = plan(pl.element, pl, theme)
        if got is None:
            continue
        if diag:
            for msg, hint in got.warnings:
                diag(msg, hint)
        count += 1
        for it in got.items:
            if count > 1:  # unique shape names (the importer matches the prefix)
                it = it.model_copy(
                    update={"element": it.element.model_copy(update={"id": f"{it.element.id} {count}"})}
                )
            res.append(it)
    return res
