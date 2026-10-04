"""Table geometry shared by layout (row heights) and renderer (merges)."""

from __future__ import annotations

from ..ir import Cell, Style, Table
from ..units import to_emu
from . import measure


def table_grid(t: Table) -> tuple[int, int, list[tuple[int, int, Cell]]]:
    """Resolve spans. ``t.rows`` holds anchor cells only (spanned positions are omitted).

    Returns ``(n_rows, n_cols, [(row, col, cell), ...])`` with spans clipped to the grid.
    """
    nrows = len(t.rows)
    occupied: set[tuple[int, int]] = set()
    anchors: list[tuple[int, int, Cell]] = []
    ncols = 0
    for r, row in enumerate(t.rows):
        c = 0
        for cell in row:
            while (r, c) in occupied:
                c += 1
            rs, cs = max(cell.rowspan, 1), max(cell.colspan, 1)
            rs = min(rs, nrows - r)
            for dr in range(rs):
                for dc in range(cs):
                    occupied.add((r + dr, c + dc))
            anchors.append((r, c, cell))
            c += cs
            ncols = max(ncols, c)
    return nrows, max(ncols, 1), anchors


def column_widths(t: Table, ncols: int, anchors: list[tuple[int, int, Cell]], total: int) -> list[int]:
    """Column widths in EMU summing to ``total``."""
    weights: list[float] = []
    if t.col_widths:
        for v in t.col_widths[:ncols]:
            try:
                weights.append(
                    float(v)
                    if not isinstance(v, str) or v.replace(".", "", 1).isdigit()
                    else to_emu(v, total)
                )
            except (ValueError, TypeError):
                weights.append(1.0)
    if len(weights) != ncols or any(w <= 0 for w in weights):
        weights = [4.0] * ncols
        for _r, c, cell in anchors:
            if cell.colspan == 1:
                n = sum(measure.text_em(p.plain) for p in cell.paragraphs[:1])
                text = max((p.plain for p in cell.paragraphs), key=len, default="")
                n = max(n, measure.text_em(text))
                weights[c] = max(weights[c], min(n, 30.0))
    s = sum(weights)
    widths = [round(total * w / s) for w in weights]
    widths[-1] += total - sum(widths)
    return widths


def row_heights(
    t: Table, anchors: list[tuple[int, int, Cell]], widths: list[int], base: Style, scale: float
) -> list[int]:
    """Natural row heights in EMU at the given autofit ``scale``."""
    nrows = len(t.rows)
    size = (base.font_size or 14) * scale
    heights = [round((size * measure.LINE_LATIN * 12700) * 1.0 + 2 * measure.CELL_PAD_Y)] * nrows
    for r, c, cell in anchors:
        if cell.rowspan > 1:
            continue
        w = sum(widths[c : c + max(cell.colspan, 1)]) - 2 * measure.CELL_PAD_X
        st = base.merged(cell.style)
        if r < t.header_rows or c < t.header_cols:
            st = st.merged(Style(bold=True))
        need = measure.paragraphs_height(cell.paragraphs, w, st, scale) + 2 * measure.CELL_PAD_Y
        heights[r] = max(heights[r], round(need))
    return heights
