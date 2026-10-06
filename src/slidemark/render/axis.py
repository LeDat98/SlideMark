"""Nice value-axis maximum for bar/column/area charts (pure arithmetic, no pptx)."""

from __future__ import annotations

import math

from ..theme import RenderTokens
from ..units import EMU_PER_PT

_STEPS = (1.0, 2.0, 2.5, 5.0)


def _num(v) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def data_top(kind: str, series_values: list[list]) -> float | None:
    """Largest category sum (stacked kinds) or largest value; None without usable data or with negatives."""
    cols = [[_num(v) for v in vals] for vals in series_values]
    flat = [v for c in cols for v in c if v is not None]
    if not flat or min(flat) < 0:
        return None
    if kind.startswith("stacked"):
        n = max(len(c) for c in cols)
        top = max(sum(c[i] or 0.0 for c in cols if i < len(c)) for i in range(n))
    else:
        top = max(flat)
    return top if top > 0 else None


def nice_axis(top: float, rt: RenderTokens) -> tuple[float, float] | None:
    """(max, major unit): max just above ``top`` plus headroom, 1/2/2.5/5 x 10^k steps, few gridlines."""
    if not (top > 0 and math.isfinite(top)):
        return None
    want = top * (1 + rt.chart_axis_headroom)
    exp = math.floor(math.log10(want)) - 1
    fallback = None
    for k in range(exp, exp + 4):
        for s in _STEPS:
            step = s * 10.0**k
            n = math.ceil(want / step - 1e-9)
            if n > rt.chart_axis_lines_max:
                continue
            cand = (round(n * step, 10), round(step, 10))
            if n >= rt.chart_axis_lines_min:
                return cand
            fallback = fallback or cand
    return fallback


def axis_from(lo: float, top: float, rt: RenderTokens) -> tuple[float, float] | None:
    """(max, major unit) for an axis that starts at the author's ``min`` (``lo``) below the data top: the nice
    steps are chosen over the visible span, so ``min=100`` with a top of 142 ends at 150, not 200."""
    if not (math.isfinite(lo) and math.isfinite(top)) or top <= lo:
        return None
    span = nice_axis(top - lo, rt)
    if not span:
        return None
    unit = span[1]
    hi = lo + math.ceil((top * (1 + rt.chart_axis_headroom) - lo) / unit - 1e-9) * unit
    return round(hi, 10), unit


def auto_axis(kind: str, series_values: list[list], rt: RenderTokens) -> tuple[float, float] | None:
    top = data_top(kind, series_values)
    return nice_axis(top, rt) if top else None


def neg_axis(kind: str, series_values: list[list], rt: RenderTokens) -> tuple[float, float, float] | None:
    """(min, max, major unit) for bars / columns with a negative value: room on both sides for the outside-end
    labels (the lowest label would hit the category labels at ``tickLblPos=low``). None without negatives."""
    if kind not in ("bar", "column"):
        return None
    flat = [v for vals in series_values for v in (_num(x) for x in vals) if v is not None]
    if not flat or min(flat) >= 0:
        return None
    top, bot = max(max(flat), 0.0), min(flat)
    span = top - bot
    want_hi = top + span * rt.chart_axis_headroom if top > 0 else 0.0
    want_lo = bot - span * rt.chart_neg_pad
    exp = math.floor(math.log10(span)) - 1
    fallback = None
    for k in range(exp, exp + 4):
        for s in _STEPS:
            step = s * 10.0**k
            n_hi = math.ceil(want_hi / step - 1e-9)
            n_lo = math.ceil(-want_lo / step - 1e-9)
            n = n_hi + n_lo
            if n > rt.chart_axis_lines_max + 2:
                continue
            cand = (round(-n_lo * step, 10), round(n_hi * step, 10), round(step, 10))
            if n >= rt.chart_axis_lines_min:
                return cand
            fallback = fallback or cand
    return fallback


BAR_KINDS = ("column", "bar", "stacked-column", "stacked-bar")


def axis_shown(opts: dict, kind: str, ncat: int, labels_on: bool, rt: RenderTokens) -> bool:
    """Whether the value axis (and its gridlines) is drawn: ``axis=on`` / ``off`` decide, else a bar chart
    whose labels carry the numbers drops it when it has few categories (``chart_axis_off_cats``)."""
    v = str(opts.get("axis", "auto")).strip().lower()
    if v in ("off", "false", "no", "0"):
        return False
    if v in ("on", "true", "yes", "1"):
        return True
    return not (labels_on and kind in BAR_KINDS and 0 < ncat <= rt.chart_axis_off_cats)


def chart_text_pt(base: float, w_emu: float, h_emu: float, rt: RenderTokens) -> float:
    """Chart text size (pt): ``base``, grown for a big chart frame to ``chart_text_ratio`` x its shorter side,
    at most ``chart_text_max_pt`` and never below ``base``."""
    if rt.chart_text_ratio <= 0:
        return base
    big = min(rt.chart_text_ratio * min(w_emu, h_emu) / EMU_PER_PT, rt.chart_text_max_pt)
    return max(base, big)


def legend_pt(size: float, rt: RenderTokens) -> float:
    """Legend text size (pt) of a chart whose text is ``size`` pt."""
    return size * rt.chart_legend_scale


def pie_label_pt(size: float, rt: RenderTokens) -> float:
    """Wedge label size (pt) of a pie / doughnut: ``chart_pie_label_scale`` x chart text, never below the
    plain data label size and at most ``chart_pie_label_max_pt``."""
    plain = size * rt.chart_label_scale
    return max(plain, min(size * rt.chart_pie_label_scale, rt.chart_pie_label_max_pt))


def pie_percent(labels, nf: str | None, rt: RenderTokens) -> bool:
    """Do the labels of a pie / doughnut show each wedge's share?

    ``labels=percent`` always does and ``labels=value`` never does. ``labels=on`` follows
    ``chart_pie_labels``, unless the chart sets its own number format (`fmt=` / `percent=on`): that formats
    the raw values, so a deck whose values already are percentages reads `36%` once, never `36%` twice.
    """
    word = labels.strip().lower() if isinstance(labels, str) else ""
    if word == "percent":
        return True
    if word == "value":
        return False
    return rt.chart_pie_labels == "percent" and not nf


def label_pt(kind: str, ncat: int, size: float, rt: RenderTokens) -> float:
    """Data label size (pt) of a chart whose text is ``size`` pt: bigger inside stacked segments (never below
    the chart text) and on a sparse bar chart, else ``chart_label_scale``."""
    if kind in ("pie", "doughnut"):
        return pie_label_pt(size, rt)
    if kind.startswith("stacked"):
        return size * max(rt.chart_seg_label_scale, 1.0)
    if kind in ("bar", "column") and ncat <= rt.chart_gap_few_cats:
        return size * rt.chart_label_scale_few
    return size * rt.chart_label_scale


def label_collisions(
    series_values: list[list],
    lo: float | None,
    hi: float | None,
    label_size: float,
    chart_h_pt: float,
    rt: RenderTokens,
) -> dict[int, list[int]]:
    """``{series: [category, ...]}`` of line-chart points whose label goes below the point.

    In a category, series whose values are closer than ``chart_collide_em`` label heights (at the plot's
    scale: ``chart_plot_share`` of the chart height spans the value axis) form a cluster; it alternates
    above / below, highest first, so the labels of two close lines (60 and 55) no longer overprint.
    """
    cols = [[_num(v) for v in vals] for vals in series_values]
    flat = [v for c in cols for v in c if v is not None]
    if rt.chart_collide_em <= 0 or len(cols) < 2 or not flat:
        return {}
    lo = min(0.0, min(flat)) if lo is None else lo  # an automatic axis starts at zero
    hi = max(flat) if hi is None else hi
    span = hi - lo
    plot_h = chart_h_pt * rt.chart_plot_share
    if span <= 0 or plot_h <= 0:
        return {}
    near = span * rt.chart_collide_em * label_size / plot_h
    below: dict[int, list[int]] = {}
    for ci in range(max(len(c) for c in cols)):
        pts = sorted(
            ((c[ci], si) for si, c in enumerate(cols) if ci < len(c) and c[ci] is not None),
            key=lambda p: (-p[0], p[1]),
        )
        rank = 0
        for k, (v, si) in enumerate(pts):
            rank = rank + 1 if k and pts[k - 1][0] - v < near else 0
            if rank % 2:
                below.setdefault(si, []).append(ci)
    return below


ZERO_BASE = ("column", "bar", "stacked-column", "stacked-bar", "area")


def resolve_axis(
    kind: str,
    series_values: list[list],
    rt: RenderTokens,
    lo: float | None,
    hi: float | None,
    wf_axis: tuple[float, float, float] | None,
    all_nonneg: bool,
    wf_top: float | None = None,
    ncat: int | None = None,
    tight: bool = False,
) -> tuple[float | None, float | None, float | None]:
    """(min, max, major unit) the renderer sets on the value axis; ``None`` leaves the auto value.

    ``tight``: the axis is hidden, so the max hugs the data (no nice round-up).
    ``lo`` / ``hi`` are the author's ``min`` / ``max``; ``wf_axis`` the waterfall's own axis (None otherwise).
    """
    unit: float | None = None
    if ncat is not None and ncat <= rt.chart_gap_few_cats:  # a sparse chart needs fewer gridlines
        rt = rt.model_copy(
            update={"chart_axis_lines_min": min(rt.chart_axis_lines_min, rt.chart_axis_lines_min_few)}
        )
    if lo is not None and lo > 0 and hi is None:  # `min=100`: nice steps over the visible span
        top = wf_top if wf_axis else data_top(kind, series_values)
        above = axis_from(lo, top, rt) if top else None
        if above:
            return lo, above[0], above[1]
    if wf_axis:
        lo = lo if lo is not None else wf_axis[0]
        hi = hi if hi is not None else wf_axis[1]
        if wf_axis[2]:
            unit = wf_axis[2]
    neg = neg_axis(kind, series_values, rt) if not wf_axis else None
    if neg:  # room for the outside-end label of the lowest bar
        lo = neg[0] if lo is None else lo
        if hi is None:
            hi = neg[1]
        if lo == neg[0] and hi == neg[1]:
            unit = neg[2]
    if lo is None and kind in ZERO_BASE and all_nonneg:
        lo = 0.0  # bars start at zero: an auto axis from 3.45 would exaggerate 3.6 vs 3.9
    if (
        hi is None
        and kind in ("bar", "column", "stacked-column", "stacked-bar", "area")
        and lo in (None, 0.0)
    ):
        top = data_top(kind, series_values) if tight else None
        auto = (top * (1 + rt.chart_axis_headroom), 0.0) if top else auto_axis(kind, series_values, rt)
        if auto:  # LibreOffice / PowerPoint round the auto max far up (117 -> 140)
            hi, unit = auto
            unit = unit or None
    return lo, hi, unit


def line_axis(series_values: list[list], rt: RenderTokens) -> tuple[float, float, float] | None:
    """(min, max, major unit) of a line chart whose axis is pinned (a ``note=`` needs known plot geometry).

    Zero based unless the data sits far above it; ``chart_axis_headroom`` above the highest point."""
    flat = [v for vals in series_values for v in (_num(x) for x in vals) if v is not None]
    if not flat:
        return None
    top, bot = max(flat), min(flat)
    base = 0.0 if bot >= 0 and bot <= rt.chart_line_zero_max * top else bot
    span = (top - base) or abs(top) or 1.0
    want_hi = top + span * rt.chart_axis_headroom
    want_lo = base - span * rt.chart_neg_pad if base < 0 or base == bot else base
    exp = math.floor(math.log10(span)) - 1
    fallback = None
    for k in range(exp, exp + 4):
        for s in _STEPS:
            step = s * 10.0**k
            lo = math.floor(want_lo / step + 1e-9) * step
            n = math.ceil((want_hi - lo) / step - 1e-9)
            cand = (round(lo, 10), round(lo + n * step, 10), round(step, 10))
            if n > rt.chart_axis_lines_max:
                continue
            if n >= rt.chart_axis_lines_min:
                return cand
            fallback = fallback or cand
    return fallback
