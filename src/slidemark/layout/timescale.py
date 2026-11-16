"""``@timeline`` time scale: parse the ``##`` headings as dates and place the marks proportionally to time.

``parse_when`` reads one heading (``1956``, ``2026-03``, ``Q3 2026``, ``FY2025``, ``2026年4月``, ``Mar 2026``;
a range such as ``2024-2026`` reads as its start) into fractional years or ``None``. ``place`` turns values
into offsets along an axis with a minimum gap between neighbours, and says which gaps were
stretched beyond their true length (the caller draws an axis break there). Never raises.
"""

from __future__ import annotations

import re

_MONTHS = {
    m: i + 1
    for i, m in enumerate(
        ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
    )
}
_Y = r"(\d{4})"
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(rf"^{_Y}$"), "y"),
    (re.compile(rf"^{_Y}\s*年$"), "y"),
    (re.compile(rf"^{_Y}\s*[-/.]\s*(\d{{1,2}})$"), "ym"),
    (re.compile(rf"^{_Y}\s*年\s*(\d{{1,2}})\s*月$"), "ym"),
    (re.compile(rf"^{_Y}\s*[-/.]\s*(\d{{1,2}})\s*[-/.]\s*(\d{{1,2}})$"), "ymd"),
    (re.compile(rf"^{_Y}\s*年\s*(\d{{1,2}})\s*月\s*(\d{{1,2}})\s*日$"), "ymd"),
    (re.compile(r"^(\d{1,2})\s*[-/.]\s*" + _Y + r"$"), "my"),
    (re.compile(rf"^(?:q|quý\s*|quarter\s*)([1-4])\s*[-/ ]?\s*(?:fy\s*)?{_Y}$", re.I), "qy"),
    (re.compile(rf"^{_Y}\s*[-/ ]?\s*q([1-4])$", re.I), "yq"),
    (re.compile(rf"^{_Y}\s*年\s*第?([1-4])\s*四半期$"), "yq"),
    (re.compile(r"^h([12])\s*[-/ ]?\s*" + _Y + "$", re.I), "hy"),
    (re.compile(rf"^{_Y}\s*[-/ ]?\s*h([12])$", re.I), "yh"),
    (re.compile(r"^fy\s*'?(\d{4}|\d{2})$", re.I), "fy"),
    (re.compile(rf"^([a-z]{{3,9}})\.?,?\s+{_Y}$", re.I), "my_name"),
    (re.compile(rf"^(?:tháng|thang)\s*(\d{{1,2}})\s*[-/,]?\s*{_Y}$", re.I), "my"),
]
_RANGE = re.compile(r"\s*(?:–|—|~|〜|→|\s-\s|\sto\s)\s*")
_RANGE_YEARS = re.compile(rf"^{_Y}\s*[-–—]\s*{_Y}$")


def _one(text: str) -> float | None:
    s = text.strip().strip("*_`").strip()
    for rx, kind in _PATTERNS:
        m = rx.match(s)
        if not m:
            continue
        g = m.groups()
        try:
            if kind == "y":
                return float(g[0])
            if kind == "ym":
                mo = int(g[1])
                return int(g[0]) + (mo - 1) / 12 if 1 <= mo <= 12 else None
            if kind == "ymd":
                mo, d = int(g[1]), int(g[2])
                return int(g[0]) + (mo - 1) / 12 + (d - 1) / 365 if 1 <= mo <= 12 and 1 <= d <= 31 else None
            if kind == "my":
                mo = int(g[0])
                return int(g[1]) + (mo - 1) / 12 if 1 <= mo <= 12 else None
            if kind == "qy":
                return int(g[1]) + (int(g[0]) - 1) / 4
            if kind == "yq":
                return int(g[0]) + (int(g[1]) - 1) / 4
            if kind == "hy":
                return int(g[1]) + (int(g[0]) - 1) / 2
            if kind == "yh":
                return int(g[0]) + (int(g[1]) - 1) / 2
            if kind == "fy":
                y = int(g[0])
                return float(y if y > 99 else 2000 + y)
            if kind == "my_name":
                mo = _MONTHS.get(g[0][:3].lower())
                return int(g[1]) + (mo - 1) / 12 if mo else None
        except (ValueError, OverflowError):
            return None
    return None


def parse_when(text: str) -> float | None:
    """Fractional year of a heading that is a date (or the start of a range), else ``None``."""
    s = (text or "").strip()
    if not s or len(s) > 40:
        return None
    v = _one(s)
    if v is not None:
        return v
    if _RANGE_YEARS.match(s):
        return float(_RANGE_YEARS.match(s).group(1))  # type: ignore[union-attr]
    parts = _RANGE.split(s, maxsplit=1)
    if len(parts) == 2 and parts[0]:
        return _one(parts[0])
    return None


def parse_all(texts: list[str]) -> list[float] | None:
    """Every heading as a date, in non-decreasing order with a real span, else ``None`` (equal spacing)."""
    if len(texts) < 2:
        return None
    vals = [parse_when(t) for t in texts]
    if any(v is None for v in vals):
        return None
    vs = [float(v) for v in vals if v is not None]
    if any(b < a for a, b in zip(vs, vs[1:], strict=False)) or vs[-1] - vs[0] <= 0:
        return None
    return vs


def place(vals: list[float], span: float, min_gap: float) -> tuple[list[float], list[bool]]:
    """Offsets (``0..span``) of marks at ``vals`` with each gap at least ``min_gap``.

    Gaps are true-to-scale at one common factor ``k``; a gap under ``min_gap`` is stretched to it and ``k``
    shrinks until the whole fits; the flags say which gaps do not match the scale (stretched, or squeezed when
    the minimum alone leaves no room and every gap is set to the equal share)."""
    n = len(vals)
    gaps = [max(b - a, 0.0) for a, b in zip(vals, vals[1:], strict=False)]
    if n < 2:
        return [0.0] * n, []
    if min_gap * (n - 1) >= span:  # no room for the minimum: equal spacing, all gaps off scale
        step = span / (n - 1)
        return [step * i for i in range(n)], [True] * (n - 1)
    lo, hi = 0.0, span / max(min(g for g in gaps if g > 0) if any(g > 0 for g in gaps) else 1.0, 1e-9)
    for _ in range(60):  # the largest k whose gaps (floored at min_gap) still fit the span
        k = (lo + hi) / 2
        if sum(max(k * g, min_gap) for g in gaps) > span:
            hi = k
        else:
            lo = k
    drawn = [max(lo * g, min_gap) for g in gaps]
    total = sum(drawn)
    if total > 0:
        drawn = [d * span / total for d in drawn]  # absorb the bisection slack so the last mark sits at span
    off = [0.0]
    for d in drawn:
        off.append(off[-1] + d)
    flags = [g > 0 and abs(d - lo * g) > 0.12 * d for d, g in zip(drawn, gaps, strict=True)]
    return off, flags
