"""Waterfall (bridge) chart maths: bars, native stacked-column series, nice axis, label text (no pptx).

A waterfall is drawn as a stacked column chart with six series (``SERIES``): an invisible ``base``, the
visible ``up`` / ``down`` / ``total`` bars, ``cross`` (the below-zero part of a bar that crosses zero) and a
``label`` carrier whose data labels hold the delta text. The importer reads the same layout back.
"""

from __future__ import annotations

import math
import re

from ..theme import RenderTokens
from .axis import nice_axis

BASE, UP, DOWN, TOTAL, CROSS, PAD = range(6)
# the first name marks a SlideMark waterfall for the importer; the last series carries the original name
SERIES = ("base (hidden)", "up", "down", "total", "below zero", "label")


def _r(v: float) -> float:
    return round(v, 10)


def bars(values: list[float | None], totals: list[int]) -> list[tuple[str, float, float, float]]:
    """(kind, lo, hi, shown) per category; kind is total | up | down | gap, ``shown`` the label number."""
    out: list[tuple[str, float, float, float]] = []
    run = 0.0
    marks = set(totals)
    for i, v in enumerate(values):
        if i == 0 and v is None:
            out.append(("gap", 0.0, 0.0, 0.0))
        elif i == 0 or i in marks:
            if i == 0:
                run = v or 0.0
            out.append(("total", min(run, 0.0), max(run, 0.0), run))
        elif v is None:
            out.append(("gap", run, run, 0.0))
        else:
            new = _r(run + v)
            out.append(("up" if v >= 0 else "down", min(run, new), max(run, new), v))
            run = new
    return out


def axis(bs, rt: RenderTokens) -> tuple[float, float, float] | None:
    """(min, max, major unit): zero based unless a bar goes below zero; headroom above the highest bar."""
    live = [b for b in bs if b[0] != "gap"]
    if not live:
        return None
    top = max(b[2] for b in live)
    bot = -min(b[1] for b in live)
    big = max(top, bot)
    nice = nice_axis(big, rt) if big > 0 else None
    if not nice:
        return None
    unit = nice[1]
    head = 1 + rt.chart_axis_headroom
    hi = math.ceil(top * head / unit - 1e-9) * unit if top > 0 else 0.0
    lo = -math.ceil(bot * head / unit - 1e-9) * unit if bot > 0 else 0.0
    return _r(lo), _r(hi), unit


def fmt_num(v: float, nf: str | None, sign: bool) -> str:
    """Label text for ``v``: a small subset of Excel formats (decimals, thousands, quoted prefix/suffix)."""
    pre = suf = ""
    dec: int | None = None
    group = pct = False
    if nf:
        sect = nf.split(";")[0]
        lits = iter(re.findall(r'"([^"]*)"', sect))
        bare = re.sub(r'"[^"]*"', "\1", sect)
        m = re.search(r"[#0,]+(?:\.([0#]+))?", bare)
        if m:
            dec = len(m.group(1)) if m.group(1) else 0
            group = "," in m.group(0)
            pct = "%" in bare
            fill = lambda s: re.sub("\1", lambda _: next(lits, ""), s).replace("%", "")  # noqa: E731
            pre, suf = fill(bare[: m.start()]), fill(bare[m.end() :])
    if pct:
        v *= 100
    if dec is None:
        dec = 0 if v == int(v) else min(len(repr(float(v)).split(".")[-1]), 6)
    body = f"{abs(v):,.{dec}f}" if group else f"{abs(v):.{dec}f}"
    if pct:
        suf = "%" + suf
    neg = v < 0 and float(body.replace(",", "")) != 0
    s = "-" if neg else ("+" if sign and v > 0 else "")
    return f"{s}{pre}{body}{suf}"


def columns(bs, pad: float) -> list[list[float | None]]:
    """Per series (``SERIES`` order) one value per category."""
    cols: list[list[float | None]] = [[] for _ in SERIES]
    for kind, lo, hi, _ in bs:
        row: list[float | None] = [0.0, None, None, None, None, None]
        if kind != "gap":
            vi = {"up": UP, "down": DOWN, "total": TOTAL}[kind]
            if lo >= 0:
                row[BASE], row[vi] = lo, _r(hi - lo)
            elif hi <= 0:
                row[BASE], row[vi] = hi, _r(lo - hi)
            else:
                row[vi], row[CROSS] = hi, lo
            row[PAD] = -pad if (hi <= 0 and lo < 0) else pad
        for c, v in zip(cols, row, strict=True):
            c.append(v)
    return cols


def decode(cols: list[list[float | None]]) -> tuple[list[float | None], list[int]]:
    """Inverse of ``columns``: (values, total marker indexes) of the one-series CSV."""

    def get(s: int, i: int) -> float | None:
        return cols[s][i] if s < len(cols) and i < len(cols[s]) else None

    values: list[float | None] = []
    totals: list[int] = []
    for i in range(max((len(c) for c in cols), default=0)):
        main = next((s for s in (UP, DOWN, TOTAL) if get(s, i) is not None), None)
        if main is None:
            values.append(None)
            continue
        b, v, c = get(BASE, i) or 0.0, get(main, i) or 0.0, get(CROSS, i)
        if c:
            lo, hi = c, v
        elif v < 0 or b < 0:
            hi, lo = b, b + v
        else:
            lo, hi = b, b + v
        if main == TOTAL:
            values.append(_r(hi if abs(hi) >= abs(lo) else lo))
            if i:
                totals.append(i)
        else:
            values.append(_r(hi - lo) if main == UP else _r(lo - hi))
    return values, totals
