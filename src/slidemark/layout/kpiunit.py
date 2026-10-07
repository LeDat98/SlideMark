"""``kpi.unit.size=22``: the trailing unit of a KPI value (億円, 名, %) drawn smaller than its digits.

The unit is the run of non-digit characters at the end of the value line (``1,280億円`` -> ``億円``,
``7.5%`` -> ``%``); a value without digits or without such a tail is left alone. The layout only splits
the paragraph into runs and gives the tail run its ``size``; the renderer scales that size with the card
and never draws it larger than the number. The importer joins the runs back into one value line.
Never raises: anything unexpected keeps the paragraph as it is.
"""

from __future__ import annotations

import re

from ..ir import Paragraph, Run

_TAIL = re.compile(r"(?<=\d)\s*([^\d\s][^\d]*)$")


def split_unit(p: Paragraph, size: float, color: str | None = None) -> Paragraph:
    """``p`` with the trailing non-digit run of its text as its own run of ``size`` pt (and ``color``)."""
    try:
        return _split(p, size, color)
    except Exception:  # never raise on bad input
        return p


def _split(p: Paragraph, size: float, color: str | None) -> Paragraph:
    plain = p.plain
    m = _TAIL.search(plain)
    if m is None or not size or size <= 0 or any(r.exact for r in p.runs):  # exact spans: the author's
        return p
    cut = m.start(1)  # characters before `cut` stay in the number's runs
    runs: list[Run] = []
    pos = 0
    for r in p.runs:
        end = pos + len(r.text)
        if end <= cut:
            runs.append(r)
        elif pos >= cut:
            runs.append(_unit(r, size, color))
        else:
            k = cut - pos
            runs.append(r.model_copy(update={"text": r.text[:k]}))
            runs.append(_unit(r.model_copy(update={"text": r.text[k:]}), size, color))
        pos = end
    return p.model_copy(update={"runs": runs})


def _unit(r: Run, size: float, color: str | None) -> Run:
    return r.model_copy(update={"size": size, **({"color": color} if color and not r.color else {})})


def value_em(p: Paragraph, size: float, unit_pt: float | None = None) -> float:
    """Em width of the value line ``p`` at ``size`` pt with its unit tail drawn at ``unit_pt`` (None: the
    run sizes ``split_unit`` already gave it, else the whole line at one size). The unit is fixed in pt, so
    its share in em shrinks as the number grows; it never counts above the number's own size."""
    from . import measure

    plain = p.plain
    if size <= 0:
        return measure.text_em(plain, bold=True)
    if any(r.exact and r.size for r in p.runs):  # `[x]{size=28}` spans are fixed in pt, like the unit
        return sum(
            measure.text_em(r.text, bold=True) * (r.size / size if r.exact and r.size else 1.0)
            for r in p.runs
        )
    tail = [r for r in p.runs if r.size]
    if tail:
        unit_pt = unit_pt or tail[0].size
        tail_text = "".join(r.text for r in tail)
    else:
        m = _TAIL.search(plain) if unit_pt else None
        tail_text = m.group(1) if m else ""
    if not tail_text or not unit_pt:
        return measure.text_em(plain, bold=True)
    head = plain[: len(plain) - len(tail_text)]
    return measure.text_em(head, bold=True) + measure.text_em(tail_text, bold=True) * min(unit_pt / size, 1.0)
