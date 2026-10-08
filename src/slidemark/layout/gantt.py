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
from .tables import _DASHES, _para_em, column_widths, compact_header, table_grid

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


_PILL_H = 0.7  # a badge pill inside a bar is this share of the bar height
_PILL_GAP_EM = 0.6  # space between the bar text and its pill (em)


def _bar_pill(
    cell: Cell,
    paras: list[Paragraph],
    style: Style,
    theme: Theme,
    pill_style: Callable[[Cell], Style],
    w: int,
    h: int,
    scale: float,
) -> tuple[list[Paragraph], Style, Placed] | None:
    """A badge after the label of a bar becomes a native rounded pill inside the bar.

    Returns (bar paragraphs cut back to the label, bar style, pill relative to the bar origin), label + pill
    centered together; None (the badge stays a text highlight) when the bar has no label before the badge, is
    not centered / left aligned, or label + pill do not fit its width."""
    from .pills import _HEAD, _LINE, _trim, pill_run  # noqa: PLC0415 (pills imports this module)

    hit = pill_run(cell.model_copy(update={"paragraphs": paras}))
    align = style.align or "left"
    if not hit or not hit.lead or align not in ("left", "center"):
        return None
    pst = pill_style(cell)
    left, _t, right, _b = css.insets(style)
    ph, pv = css.inset_hv(pst)
    size = (style.font_size or 14) * scale
    ph_h = round(_PILL_H * h)
    psize = min(size, (ph_h - pv) / EMU_PER_PT / _LINE)
    if psize < theme.min_font_size or psize < 0.6 * size:
        return None
    bold = not measure.has_cjk(hit.text)
    em = measure.text_em(css.transform_text(hit.text, pst.text_transform), bold=bold)
    need = round(em * _HEAD * psize * EMU_PER_PT) + ph
    lead = Paragraph(runs=_trim(hit.lead))
    tx = round(_para_em(lead, bool(style.bold), style.text_transform)[0] * _HEAD * size * EMU_PER_PT)
    gap = round(_PILL_GAP_EM * size * EMU_PER_PT)
    avail = w - left - right
    if tx + gap + need > avail:
        return None
    if align == "center":
        px = left + (avail - (tx + gap + need)) // 2 + tx + gap
        bar_style = style.merged(fast_style(padding_right=f"{(right + need + gap) / EMU_PER_PT:.2f}pt"))
    else:
        px = left + tx + gap
        bar_style = style
    ink = pst.color or theme.badge_ink(hit.run.highlight)
    pill_st = pst.merged(
        fast_style(
            fill=pst.fill or hit.run.highlight, color=ink, bold=bold, font_size=psize / max(scale, 1e-6)
        )
    )
    run = hit.run.model_copy(update={"highlight": None, "color": None, "bold": False, "text": hit.text})
    pill = Placed(
        element=Shape(
            shape="rounded-rect", paragraphs=[Paragraph(runs=[run])], classes=["pill"], attrs={"pill": True}
        ),
        x=px,
        y=(h - ph_h) // 2,
        w=need,
        h=ph_h,
        style=pill_st,
        font_scale=scale,
    )
    return [hit.para.model_copy(update={"runs": _trim(hit.lead)})], bar_style, pill


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


_EVEN_ROUNDS = 8  # pin-and-redistribute passes of ``even_columns`` (each pass pins at least one column)


def _one_line(paras: list[Paragraph], style: Style, scale: float, bold: bool) -> Callable[[int], bool]:
    """``f(inner width)``: every paragraph fits one line, badges counted with their padding (the plain height
    measure does not see a badge pushed onto its own line)."""
    head = measure.tokens().badge_headroom  # fallback fonts run wider; badges more so
    em = (
        max(
            (_para_em(p, bold, style.text_transform)[0] * (head if any(r.highlight for r in p.runs) else 1.0))
            for p in paras
        )
        if paras
        else 0.0
    )
    size = (style.font_size or 14) * scale * EMU_PER_PT
    return lambda w: em * size <= w


def _split(total: int, n: int) -> list[int]:
    q, r = divmod(total, n)
    return [q + (1 if i < r else 0) for i in range(n)]


def _min_total(ok: Callable[[int], bool], hi: int) -> int:
    """Smallest width (EMU, within 1pt) at which ``ok`` holds, given that it holds at ``hi``."""
    lo, hi = 0, max(hi, 1)
    while hi - lo > EMU_PER_PT:
        mid = (lo + hi) // 2
        lo, hi = (lo, mid) if ok(mid) else (mid, hi)
    return hi


def even_columns(
    pl: Placed,
    style: Style,
    theme: Theme,
    pad_pt: float,
    bar_ratio: float,
) -> Placed:
    """``pl`` with equal period columns: label column(s) and total width stay, the rest is split evenly.

    Runs after every growth pass, so no later step re-grows text into the new columns. Every cell must still
    be as good as it was: a table cell keeps its text height (no new wrap), a bar keeps its text size. A
    column that cannot take its equal share is pinned to the width it needs and the others share the rest; if
    even that fails the widths stay. ``widths=`` of the author always wins."""
    t = pl.element
    nrows, ncols, anchors = table_grid(t)
    first = max(t.header_cols, 1)
    if t.col_widths or ncols - first < 2:
        return pl
    cw, rh = table_boxes(pl)
    cw = [int(w) for w in cw[:ncols]]
    rest = sum(cw[first:])
    n = ncols - first
    if rest <= 0 or n * EMU_PER_PT > rest:
        return pl
    pad = round(pad_pt * EMU_PER_PT)
    bars = {id(c): (r, c0, c) for r, c0, c in bar_cells(t, anchors)}
    ys = [0]
    for h in rh[:nrows]:
        ys.append(ys[-1] + int(h))
    # one check per cell group (c0, c1): ok(total width of the columns) says whether the cell is still fine
    groups: dict[tuple[int, int], list[Callable[[int], bool]]] = {}
    px, py = measure.cell_pad()
    for r, c0, cell in anchors:
        if c0 < first:
            continue
        c1 = min(c0 + max(cell.colspan, 1), ncols)
        old = sum(cw[c0:c1])
        if id(cell) in bars:
            r1 = min(r + max(cell.rowspan, 1), nrows)
            band = ys[r1] - ys[r]
            paras = _bar_paragraphs(cell, theme, style)

            def fit(w: int, paras=paras, band=band):
                return _fit_bar(paras, style, w - 2 * pad, round(band * bar_ratio), band, pl.font_scale, 0.0)

            _, k0, ok0 = fit(old)
            ph = css.inset_hv(style)[0]
            line = _one_line(paras, style, k0, False)
            was1 = line(old - 2 * pad - ph)

            def check(w: int, fit=fit, k0=k0, ok0=ok0, line=line, was1=was1, ph=ph) -> bool:
                _, k, ok = fit(w)
                return k >= k0 - 1e-6 and (ok or not ok0) and (line(w - 2 * pad - ph) or not was1)

        else:
            cl, ct, cr, cb = css.cell_insets(cell.style, px, py)
            st = pl.style.merged(cell.style)
            if r < t.header_rows or c0 < t.header_cols:
                st = st.merged(fast_style(bold=True))

            def need(w: int, cell=cell, st=st, ins=(cl, ct, cr, cb)) -> float:
                return measure.paragraphs_height(cell.paragraphs, w - ins[0] - ins[2], st, pl.font_scale)

            n0 = need(old)
            line = _one_line(cell.paragraphs, st, pl.font_scale, st.bold is True)
            was1 = line(old - cl - cr)

            def check(w: int, need=need, n0=n0, line=line, was1=was1, ins=(cl, cr)) -> bool:
                return need(w) <= n0 + 1 and (line(w - ins[0] - ins[1]) or not was1)

        groups.setdefault((c0, c1), []).append(check)

    def violated(widths: list[int]) -> list[tuple[int, int]]:
        return [g for g, fs in groups.items() if not all(f(sum(widths[g[0] : g[1]])) for f in fs)]

    pinned: dict[int, int] = {}
    widths = list(cw)
    for _ in range(_EVEN_ROUNDS):
        free = [c for c in range(first, ncols) if c not in pinned]
        if not free:
            return pl
        share = _split(rest - sum(pinned.values()), len(free))
        if min(share) <= 0:
            return pl
        widths = cw[:first] + [0] * n
        for c, w in pinned.items():
            widths[c] = w
        for c, w in zip(free, share, strict=True):
            widths[c] = w
        bad = violated(widths)
        if not bad:
            break
        for c0, c1 in bad:
            fs = groups[(c0, c1)]
            old = sum(cw[c0:c1])
            need = _min_total(lambda w, fs=fs: all(f(w) for f in fs), old)
            cols = [c for c in range(c0, c1) if c not in pinned]
            if not cols:
                continue
            each = (need - sum(widths[c] for c in range(c0, c1) if c in pinned)) // len(cols) + 1
            for c in cols:
                pinned[c] = max(each, 1)
    else:
        return pl
    if violated(widths) or sum(widths) != sum(cw) or widths == cw:
        return pl
    attrs = {**t.attrs, "_col_w": widths}
    return pl.model_copy(update={"element": t.model_copy(update={"attrs": attrs})})


def expand_gantt(
    out: list[Placed],
    theme: Theme,
    style_for: Callable[[Placed], Style],
    pad_pt: float,
    bar_ratio: float,
    diag: Callable[[str, str], None] | None = None,
    pill_style: Callable[[Placed, Cell], Style] | None = None,
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
        style = style_for(pl)
        if measure.tokens().gantt_even:
            pl = even_columns(pl, style, theme, pad_pt, bar_ratio)
            t = pl.element
        cw, rh = table_boxes(pl)
        xs = [pl.x]
        for w in cw[:ncols]:
            xs.append(xs[-1] + int(w))
        ys = [pl.y]
        for h in rh[:nrows]:
            ys.append(ys[-1] + int(h))
        pad = round(pad_pt * EMU_PER_PT)
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
            extra: list[Placed] = []
            bar_style = style
            if ok and pill_style is not None:
                got = _bar_pill(
                    cell, paras, style, theme, lambda c, pl=pl: pill_style(pl, c), x1 - x0, bh, scale
                )
                if got:
                    paras, bar_style, pill = got
                    extra = [pill.model_copy(update={"x": x0 + pill.x, "y": y0 + pill.y})]
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
                    style=bar_style,
                    font_scale=scale,
                )
            )
            bars.extend(extra)
        marks = {id(c) for r, k, c in anchors if r >= t.header_rows and k >= max(t.header_cols, 1)} - emptied

        rows = [[_tidy(c, emptied, marks) for c in row] for row in t.rows]
        res.append(pl.model_copy(update={"element": t.model_copy(update={"rows": rows})}))
        res.extend(bars)
    return res
