"""``{.gantt}`` tables: each filled body cell after the first column becomes a native bar over the table.

Runs on the finished placed items of a slide (after every vertical fill moved or stretched the table), so the
bars sit on the real cell boxes. The table keeps its header rows and first column; the cells under a bar are
emptied so the text is drawn once, inside the bar.
"""

from __future__ import annotations

from collections.abc import Callable

from ..contrast import mix, ratio
from ..ir import Cell, Paragraph, Placed, Shape, Style, Table, fast_style
from ..theme import Theme
from ..units import EMU_PER_PT
from . import css, measure
from .tables import _DASHES, column_widths, compact_header, table_grid

_BAR_MAX = 0.92  # a bar never takes more than this share of its row
_MARKS = _DASHES | {"―"}  # "no value" placeholders: no bar


def is_gantt(t: Table) -> bool:
    return "gantt" in t.classes


def bar_text(cell: Cell) -> str:
    return "".join(p.plain for p in cell.paragraphs).strip()


def has_bar(cell: Cell) -> bool:
    txt = bar_text(cell)
    return bool(txt) and txt not in _MARKS


def table_boxes(pl: Placed) -> tuple[list[int], list[int]]:
    """Final (column widths, row heights) in EMU of a placed table, as the renderer draws them."""
    t = pl.element
    nrows, ncols, anchors = table_grid(t)
    cw = t.attrs.get("_col_w") or column_widths(t, ncols, anchors, pl.w)
    rh = t.attrs.get("_row_h") or [max(pl.h // nrows, 1)] * nrows
    if t.attrs.get("_row_h"):
        rh = compact_header(t, anchors, cw, pl.style, pl.font_scale, rh, measure.tokens().table_header_max)
    return list(cw), list(rh)


def bar_cells(t: Table, anchors: list[tuple[int, int, Cell]]) -> list[tuple[int, int, Cell]]:
    first = max(t.header_cols, 1)
    return [(r, c, cell) for r, c, cell in anchors if r >= t.header_rows and c >= first and has_bar(cell)]


def _bar_paragraphs(cell: Cell, theme: Theme, style: Style) -> list[Paragraph]:
    """Cell paragraphs for a bar. A badge that has the bar's own color (or hardly differs from it) would
    vanish: it becomes a pill in ``render.gantt_badge`` (default: a tint of the bar fill) with the ink chosen
    for contrast (``Theme.badge_ink``). Badges that read on the bar (success, danger...) stay."""
    fill = theme.hexval(style.fill)
    if not fill:
        return list(cell.paragraphs)
    rt = theme.render
    pill = (
        theme.hexval(rt.gantt_badge)
        if rt.gantt_badge
        else mix(fill, theme.hexval("bg") or rt.slide_bg, rt.gantt_badge_tint)
    )
    out = []
    for p in cell.paragraphs:
        runs = [
            r.model_copy(update={"highlight": pill, "color": None})
            if r.highlight and ratio(theme.hexval(r.highlight) or fill, fill) < 1.5
            else r
            for r in p.runs
        ]
        out.append(p.model_copy(update={"runs": runs}))
    return out


def _tidy(c: Cell, emptied: set[int], marks: set[int]) -> Cell:
    if id(c) in emptied:
        return c.model_copy(update={"paragraphs": [Paragraph()]})
    if id(c) in marks and bar_text(c):  # a "no value" mark sits in the middle of its period
        return c.model_copy(update={"style": (c.style or fast_style()).merged(fast_style(align="center"))})
    return c


def _fit_bar(paras: list[Paragraph], style: Style, w: int, h: int, band: int, scale: float, floor: float):
    """(height, font scale, fits) of a bar: it grows up to ``_BAR_MAX`` of its row, then the text shrinks."""
    ph, pv = css.inset_hv(style)
    size = style.font_size or 14
    lowest = max(min(floor / size, 1.0), 0.1)
    k, cap = scale, round(band * _BAR_MAX)
    while True:
        need = round(measure.paragraphs_height(paras, w - ph, style, k) + pv)
        if need <= max(h, cap):
            return max(h, min(need, cap)), k, True
        if k <= lowest * scale + 1e-6:
            return cap, k, False
        k = max(k * 0.95, lowest * scale)


def expand_gantt(
    out: list[Placed],
    theme: Theme,
    style_for: Callable[[Placed], Style],
    pad_pt: float,
    bar_ratio: float,
    diag: Callable[[str, str], None] | None = None,
) -> list[Placed]:
    """Replace every gantt table by (table with emptied bar cells, bars...) in z-order.

    A bar whose text does not fit shrinks its text (down to the theme minimum size), else it grows toward its
    row height; ``diag(message, hint)`` hears about the bars that still overflow (rule ``gantt-text``)."""
    res: list[Placed] = []
    for pl in out:
        t = pl.element
        if not (isinstance(t, Table) and is_gantt(t)):
            res.append(pl)
            continue
        nrows, ncols, anchors = table_grid(t)
        cw, rh = table_boxes(pl)
        xs = [pl.x]
        for w in cw[:ncols]:
            xs.append(xs[-1] + int(w))
        ys = [pl.y]
        for h in rh[:nrows]:
            ys.append(ys[-1] + int(h))
        pad = round(pad_pt * EMU_PER_PT)
        style = style_for(pl)
        bars: list[Placed] = []
        emptied: set[int] = set()
        for r, c, cell in bar_cells(t, anchors):
            c1 = min(c + max(cell.colspan, 1), ncols)
            r1 = min(r + max(cell.rowspan, 1), nrows)
            if len(xs) <= c1 or len(ys) <= r1:
                continue
            x0, x1 = xs[c] + pad, xs[c1] - pad
            band = ys[r1] - ys[r]
            bh = round(band * bar_ratio)
            y0 = ys[r] + (band - bh) // 2
            if x1 - x0 <= 0 or bh <= 0:
                continue
            paras = _bar_paragraphs(cell, theme, style)
            bh, scale, ok = _fit_bar(paras, style, x1 - x0, bh, band, pl.font_scale, theme.min_font_size)
            y0 = ys[r] + (band - bh) // 2
            if not ok and diag:
                diag(
                    f"gantt bar '{bar_text(cell)[:24]}' does not fit its cells",
                    "shorten the bar text or merge more period cells with <",
                )
            emptied.add(id(cell))
            bars.append(
                Placed(
                    element=Shape(
                        shape="rounded-rect",
                        paragraphs=paras,
                        classes=["gantt"],
                        attrs={"gantt": True},
                    ),
                    x=x0,
                    y=y0,
                    w=x1 - x0,
                    h=bh,
                    style=style,
                    font_scale=scale,
                )
            )
        marks = {id(c) for r, k, c in anchors if r >= t.header_rows and k >= max(t.header_cols, 1)} - emptied

        rows = [[_tidy(c, emptied, marks) for c in row] for row in t.rows]
        res.append(pl.model_copy(update={"element": t.model_copy(update={"rows": rows})}))
        res.extend(bars)
    return res
