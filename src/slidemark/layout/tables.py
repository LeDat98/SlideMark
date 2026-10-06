"""Table geometry shared by layout (row heights) and renderer (merges)."""

from __future__ import annotations

import re

from ..ir import Cell, Style, Table, fast_style
from ..units import EMU_PER_PT, to_emu
from . import css, measure
from .tablehl import hl_rows


def table_grid(t: Table) -> tuple[int, int, list[tuple[int, int, Cell]]]:
    """Resolve spans. ``t.rows`` holds anchor cells only (spanned positions are omitted).

    Returns ``(n_rows, n_cols, [(row, col, cell), ...])`` with spans clipped to the grid.
    """
    nrows = len(t.rows)
    # The parser emits rectangular rows (covered cells = empty placeholders); hand-built tables may omit them.
    rect = len({len(row) for row in t.rows}) == 1
    occupied: set[tuple[int, int]] = set()
    anchors: list[tuple[int, int, Cell]] = []
    ncols = 0
    for r, row in enumerate(t.rows):
        c = 0
        for cell in row:
            if rect and (r, c) in occupied:
                c += 1  # placeholder of a merged cell
                continue
            while (r, c) in occupied:
                c += 1
            rs, cs = max(cell.rowspan, 1), max(cell.colspan, 1)
            rs = min(rs, nrows - r)
            for dr in range(rs):
                for dc in range(cs):
                    occupied.add((r + dr, c + dc))
            anchors.append((r, c, cell))
            ncols = max(ncols, c + cs)
            # rectangular input: covered positions follow as placeholders and are skipped above
            c += 1 if rect else cs
    return nrows, max(ncols, 1), anchors


def _min_em(text: str) -> float:
    """Width in em below which ``text`` would wrap awkwardly: short CJK strings stay on one line."""
    if measure.has_cjk(text):
        return min(measure.text_em(text), 8.0)
    return min(max((measure.text_em(w) for w in text.split()), default=0.0), 12.0)


def _badge_em(text: str) -> float:
    """Width in em of a badge as rendered: bold text plus the padding render/text.py adds around it."""
    tk = measure.tokens()
    if measure.has_cjk(text):
        return measure.text_em(text, bold=True) + 2.0 * tk.badge_pad_cjk
    return measure.text_em(text, bold=True) + 2 * tk.badge_pad * measure.text_em("\u00a0")


def _badge_unit_em(text: str, lead: str, bold: bool) -> float:
    """Width in em that a badge and the word before it must keep together (with headroom for wider fonts)."""
    em = _badge_em(text) + (measure.text_em(lead, bold=bold) + measure.text_em(" ") if lead else 0.0)
    return em * measure.tokens().badge_headroom


def _para_em(p, bold: bool, tf: str | None) -> tuple[float, float]:
    """(full width, width that must stay on one line) in em of a paragraph with its badges padded.

    The second figure is the widest unit that may not break: a word, or the word before a badge together with
    the whole badge (a badge never sits alone on a line while the column can be widened).
    """
    runs = p.runs
    if not any(r.highlight for r in runs):
        return measure.text_em(css.transform_text(p.plain, tf), bold=bold), _min_em(p.plain)
    total = 0.0
    keep = _min_em("".join(r.text for r in runs if not r.highlight))
    prev = ""
    for r in runs:
        txt = css.transform_text(r.text, tf)
        if r.highlight:
            b = _badge_em(txt)
            if measure.tokens().badge_gap and prev and not prev.endswith((" ", "\u00a0", "\u3000")):
                total += measure.text_em(" ", bold=bold)
            lead = prev.split()[-1] if prev.split() else ""
            keep = max(keep, _badge_unit_em(txt, lead, bold))
            total += b
        else:
            total += measure.text_em(txt, bold=bold or r.bold)
        prev = txt
    return total, min(keep, 20.0)


def _measured_em(
    t: Table, ncols: int, anchors: list[tuple[int, int, Cell]], size_pt: float
) -> tuple[list[float], list[float]]:
    """(longest-text width, minimum sensible width) per column, in em, cell padding included."""
    weights = [3.0] * ncols
    mins = [2.0] * ncols
    hl = hl_rows(t)  # emphasised rows are bold (measured so even with `table.hl.bold=off`: a little headroom)
    for r, c, cell in anchors:
        if cell.colspan != 1:
            continue
        bold = r < t.header_rows or c < t.header_cols or r in hl
        tf = cell.style.text_transform if cell.style else None
        ems = [_para_em(p, bold, tf) for p in cell.paragraphs]
        weights[c] = max(weights[c], min(max((e[0] for e in ems), default=0.0), 30.0))
        mins[c] = max(mins[c], *(e[1] for e in ems), 0.0)
    pad_em = 2 * measure.cell_pad()[0] / EMU_PER_PT / max(size_pt, 1.0)
    weights = [w + pad_em for w in weights]
    min_w = [(m + pad_em) * 1.08 for m in mins]  # a little headroom: fallback fonts run wider
    return weights, min_w


TABLE_MAX_COLS = 5  # a table with at most this many columns ...
TABLE_NARROW = 0.6  # ... whose natural width is below this share of the area ...
TABLE_KEEP_FULL = 0.85  # (the cap only applies when it saves at least this much of the area's width)
TABLE_WIDTH_CAP = 1.6  # ... is at most this many times its natural width (left-aligned in the area)


def capped_width(
    t: Table, ncols: int, anchors: list[tuple[int, int, Cell]], total: int, size_pt: float = 14.0
) -> int:
    """Total width of a table in an area of ``total`` EMU: a few short columns do not stretch over the area.

    Without explicit ``col_widths``, a table with figures and at most ``TABLE_MAX_COLS`` columns whose natural
    width is under ``TABLE_NARROW`` of the area takes ``TABLE_WIDTH_CAP`` x its natural width, so numbers stay
    next to their labels. Everything else uses the whole area.
    """
    if t.col_widths or ncols > TABLE_MAX_COLS:
        return total
    if not numeric_columns(t, ncols, anchors):  # text-only grids (Gantt dots, matrices) keep the full width
        return total
    weights, min_w = _measured_em(t, ncols, anchors, size_pt)
    nat = sum(max(w, m) for w, m in zip(weights, min_w, strict=True)) * size_pt * EMU_PER_PT
    if nat >= TABLE_NARROW * total:
        return total
    capped = round(nat * TABLE_WIDTH_CAP)
    return total if capped >= TABLE_KEEP_FULL * total else capped  # a small gain is not worth a ragged edge


TEXT_FAVOUR = 3.0  # a text column takes this many times the share of spare width of a numeric column


def column_widths(
    t: Table, ncols: int, anchors: list[tuple[int, int, Cell]], total: int, size_pt: float = 14.0
) -> list[int]:
    """Column widths in EMU summing to ``total``.

    Without explicit ``col_widths`` the widths follow the measured longest cell text of each column (header
    included), and no column drops below the width of its shortest sensible line (``_min_em``).
    """
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
    if len(weights) == ncols and all(w > 0 for w in weights):
        s = sum(weights)
        widths = [round(total * w / s) for w in weights]
        widths[-1] += total - sum(widths)
        return widths
    weights, min_w = _measured_em(t, ncols, anchors, size_pt)
    em_total = total / EMU_PER_PT / max(size_pt, 1.0)
    nat = [max(w, m) for w, m in zip(weights, min_w, strict=True)]
    if sum(nat) < em_total:  # room to spare: natural widths first, the extra favours text columns
        num = numeric_columns(t, ncols, anchors)
        share = [1.0 if c in num else TEXT_FAVOUR for c in range(ncols)]
        ssum = sum(share)
        extra = em_total - sum(nat)
        ems = [nat[c] + extra * share[c] / ssum for c in range(ncols)]
        widths = [round(total * e / em_total) for e in ems]
        widths[-1] += total - sum(widths)
        return widths
    # water-filling: columns below their minimum are pinned to it, the rest share what is left by weight
    pinned: dict[int, float] = {}
    for _ in range(ncols):
        rest = em_total - sum(pinned.values())
        free = [i for i in range(ncols) if i not in pinned]
        wsum = sum(weights[i] for i in free) or 1.0
        bad = [i for i in free if rest * weights[i] / wsum < min_w[i]]
        if not bad:
            break
        for i in bad:
            pinned[i] = min_w[i]
    rest = max(em_total - sum(pinned.values()), 0.0)
    free = [i for i in range(ncols) if i not in pinned]
    wsum = sum(weights[i] for i in free) or 1.0
    ems = [pinned[i] if i in pinned else rest * weights[i] / wsum for i in range(ncols)]
    s = sum(ems) or 1.0
    widths = [round(total * e / s) for e in ems]
    widths[-1] += total - sum(widths)
    return widths


_NUM = re.compile(
    r"^[\s+\-\u2212\uff0b\uff0d\u25b2\u25b3\u25bc\u25bd\u00a5\uffe5$\u20ac\u00b1(]*"
    r"[\d][\d.,\uff0c\s]*"
    r"(?:%|\uff05|\u5104\u5186|\u4e07\u5186|\u5343\u5186|\u5146\u5186|\u5186|\u5104|\u4e07|\u5343|"
    r"\u793e|\u4ef6|\u540d|\u4eba|\u500d|\u30f6\u6708|\u304b\u6708|\u30ab\u6708|\u30dd\u30a4\u30f3\u30c8|"
    r"pt|pts|x|k|m|b|bn|M|K|B)?[\s)]*[\u301c~]?$"
)


_DASHES = {"-", "\u2013", "\u2014", "\uff0d", "\u2212", "\u2015"}  # "no value" placeholders


def is_numeric(text: str) -> bool:
    """True for figures such as ``38.2``, ``+14%``, ``▲8.0``, ``62.4億円``, ``5万円〜``."""
    t = text.strip()
    return bool(t) and (bool(_NUM.match(t)) or t in _DASHES)


NUMERIC_SHARE = (
    0.8  # a column is right-aligned when at least this share of its non-empty body cells are figures
)


def numeric_columns(t: Table, ncols: int, anchors: list[tuple[int, int, Cell]]) -> set[int]:
    """Columns where >= ``NUMERIC_SHARE`` of the non-empty body cells are figures."""
    body: dict[int, list[str]] = {c: [] for c in range(ncols)}
    for r, c, cell in anchors:
        txt = "".join(p.plain for p in cell.paragraphs).strip()
        if r >= t.header_rows and c >= t.header_cols and cell.colspan == 1 and txt:
            body[c].append(txt)
    return {
        c
        for c, items in body.items()
        if items and sum(is_numeric(x) for x in items) >= NUMERIC_SHARE * len(items)
    }


def right_align_numbers(t: Table) -> Table:
    """Copy of ``t`` where mostly numeric body columns (and their headers) are right-aligned as a whole.

    A column counts as numeric when >= ``NUMERIC_SHARE`` of its non-empty body cells are figures; every other
    column stays left-aligned, so mixed columns do not look jagged. Cells with an explicit alignment (cell or
    paragraph style) are left alone.
    """
    _, ncols, anchors = table_grid(t)
    col_of = {id(cell): c for _r, c, cell in anchors}
    num_cols = numeric_columns(t, ncols, anchors)

    def text(cell: Cell) -> str:
        return "".join(p.plain for p in cell.paragraphs).strip()

    rows = [list(row) for row in t.rows]
    changed = False
    for ri, row in enumerate(t.rows):
        for ci, cell in enumerate(row):
            col = col_of.get(id(cell))
            if col is None or cell.colspan != 1 or col not in num_cols or not text(cell):
                continue
            if col < t.header_cols or (cell.style and cell.style.align):
                continue
            if any(p.style and p.style.align for p in cell.paragraphs):
                continue
            rows[ri][ci] = cell.model_copy(
                update={"style": (cell.style or fast_style()).merged(fast_style(align="right"))}
            )
            changed = True
    return t.model_copy(update={"rows": rows}) if changed else t


def row_heights(
    t: Table, anchors: list[tuple[int, int, Cell]], widths: list[int], base: Style, scale: float
) -> list[int]:
    """Natural row heights in EMU at the given autofit ``scale``."""
    nrows = len(t.rows)
    size = (base.font_size or 14) * scale
    heights = [round((size * measure.tokens().line_latin * 12700) * 1.0 + 2 * measure.cell_pad()[1])] * nrows
    hl = hl_rows(t)
    for r, c, cell in anchors:
        if cell.rowspan > 1:
            continue
        px, py = measure.cell_pad()
        cl, ct, cr, cb = css.cell_insets(cell.style, px, py)
        w = sum(widths[c : c + max(cell.colspan, 1)]) - cl - cr
        st = base.merged(cell.style)
        if r < t.header_rows or c < t.header_cols or r in hl:
            st = st.merged(fast_style(bold=True))
        need = measure.paragraphs_height(cell.paragraphs, w, st, scale) + ct + cb
        heights[r] = max(heights[r], round(need))
    return heights


def compact_header(
    t: Table,
    anchors: list[tuple[int, int, Cell]],
    widths: list[int],
    base: Style,
    scale: float,
    heights: list[int],
    max_ratio: float,
) -> list[int]:
    """Stretched row heights with compact header rows: the slack goes to the body rows.

    A header row never exceeds ``max_ratio`` x its natural height (text + padding); what it gives back is
    shared by the body rows in proportion to their heights. No header, no body or ``max_ratio <= 0`` keeps
    ``heights``. The total height is unchanged.
    """
    nh = min(max(t.header_rows, 0), len(heights))
    if max_ratio <= 0 or nh == 0 or nh >= len(heights):
        return heights
    nat = row_heights(t, anchors, widths, base, scale)
    out = list(heights)
    freed = 0
    for r in range(nh):
        cap = max(round(nat[r] * max_ratio), 1)
        if out[r] > cap:
            freed += out[r] - cap
            out[r] = cap
    if freed <= 0:
        return heights
    body = sum(out[nh:]) or 1
    add = [round(freed * h / body) for h in out[nh:]]
    add[-1] += freed - sum(add)
    for i, a in enumerate(add):
        out[nh + i] += a
    return out
