"""Nice value-axis maximum for bar/column/area charts (pure arithmetic, no pptx)."""

from __future__ import annotations

import math

from ..theme import RenderTokens

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
) -> tuple[float | None, float | None, float | None]:
    """(min, max, major unit) the renderer sets on the value axis; ``None`` leaves the auto value.

    ``lo`` / ``hi`` are the author's ``min`` / ``max``; ``wf_axis`` the waterfall's own axis (None otherwise).
    """
    unit: float | None = None
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
        auto = auto_axis(kind, series_values, rt)
        if auto:  # LibreOffice / PowerPoint round the auto max far up (117 -> 140)
            hi, unit = auto
    return lo, hi, unit


def line_axis(series_values: list[list], rt: RenderTokens) -> tuple[float, float, float] | None:
    """(min, max, major unit) of a line chart whose axis is pinned (a ``note=`` needs known plot geometry).

    Zero based unless the data sits far above it; ``chart_axis_headroom`` above the highest point."""
    flat = [v for vals in series_values for v in (_num(x) for x in vals) if v is not None]
    if not flat:
        return None
    top, bot = max(flat), min(flat)
    base = 0.0 if bot >= 0 and bot <= 0.6 * top else bot
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
