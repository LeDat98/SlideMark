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


def auto_axis(kind: str, series_values: list[list], rt: RenderTokens) -> tuple[float, float] | None:
    top = data_top(kind, series_values)
    return nice_axis(top, rt) if top else None
