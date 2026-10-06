"""Status pills: a badge in a table cell becomes a native rounded-rectangle shape over the cell.

LibreOffice cannot round a text highlight, so a badge in a cell reads as a flat padded rectangle. Like a
``{.gantt}`` bar, the pill is placed on the finished cell boxes (after every vertical fill) and the cell text
under it is emptied (badge-only cell) or cut back to the text before the badge (``4.2 万台 [首位]``), so the
text is drawn once. Pills of one column share the widest need; after-text pills also share one left edge.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ..ir import Cell, Paragraph, Placed, Run, Shape, Style, Table, fast_style
from ..theme import Theme
from ..units import EMU_PER_PT
from . import css, measure
from .gantt import table_boxes
from .tables import _para_em, table_grid

_ROW_MAX = 0.92  # a pill never takes more than this share of its row
_HEAD = 1.1  # width headroom: fallback fonts run a little wider than the measure
_LINE = 1.2  # text line height in em
_GAP_EM = 0.6  # space between the cell text and a pill that follows it (em)
_PAD = "　  "  # badge padding characters


@dataclass
class _Hit:
    para: Paragraph
    run: Run  # first badge run (its highlight is the fill)
    text: str  # badge text without padding
    lead: list[Run]  # runs before the badge; empty for a badge-only cell


def pill_run(cell: Cell) -> _Hit | None:
    """The badge of a cell with only a badge, or with one badge after its text (one paragraph); else None."""
    if len(cell.paragraphs) != 1:
        return None
    p = cell.paragraphs[0]
    if p.marker or any(r.link or "\n" in r.text for r in p.runs):
        return None
    runs = list(p.runs)
    while runs and not runs[-1].text.strip(_PAD) and not runs[-1].highlight:
        runs.pop()  # trailing blanks
    k = len(runs)
    while k and runs[k - 1].highlight:
        k -= 1
    lead, tail = runs[:k], runs[k:]
    if not tail or len({r.highlight for r in tail}) != 1 or any(r.highlight for r in lead):
        return None
    text = "".join(r.text for r in tail).strip(_PAD)
    if not text:
        return None
    if lead and not "".join(r.text for r in lead).strip(_PAD):
        lead = []
    return _Hit(p, tail[0], text, lead)


def has_pills(t: Table) -> bool:
    if "gantt" in t.classes:
        return False
    return any(
        r >= t.header_rows and c >= t.header_cols and pill_run(cell) for r, c, cell in table_grid(t)[2]
    )


@dataclass
class _Cand:
    r: int
    c: int
    c1: int
    cell: Cell
    st: Style
    hit: _Hit
    bold: bool
    need: int  # pill width (EMU)
    avail: int  # inner width of the cell (EMU)
    band: int
    h: int
    cl: int
    cr: int
    text_end: int = 0  # after-text pill: where the text ends, from the cell's inner left edge (EMU)


def _trim(lead: list[Run]) -> list[Run]:
    out = list(lead)
    while out and not out[-1].text.strip(_PAD):
        out.pop()
    if out:
        out[-1] = out[-1].model_copy(update={"text": out[-1].text.rstrip(_PAD)})
    return out


def expand_pills(
    out: list[Placed],
    theme: Theme,
    style_for: Callable[[Placed, Cell], Style],
    height_em: float,
) -> list[Placed]:
    """Replace the badge of every table body cell by a ``Pill`` shape over the cell.

    ``style_for(table, cell)`` is the pill's own style (table text, ``pill`` class, CSS ``.pill`` rules)."""
    res: list[Placed] = []
    for pl in out:
        t = pl.element
        if not (isinstance(t, Table) and has_pills(t)):
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
        px, py = measure.cell_pad()
        cands: list[_Cand] = []
        for r, c, cell in anchors:
            hit = pill_run(cell) if r >= t.header_rows and c >= t.header_cols else None
            c1, r1 = min(c + max(cell.colspan, 1), ncols), min(r + max(cell.rowspan, 1), nrows)
            if not hit or len(xs) <= c1 or len(ys) <= r1:
                continue
            st = style_for(pl, cell)
            cst = pl.style.merged(cell.style)
            if hit.lead and (
                c1 - c > 1 or r1 - r > 1 or (cst.align or "left") != "left" or cst.valign != "middle"
            ):
                continue  # text before the badge: only plain left-aligned, vertically centered cells
            size = (st.font_size or 14) * pl.font_scale
            bold = not measure.has_cjk(hit.text)
            ph, pv = css.inset_hv(st)
            em = measure.text_em(css.transform_text(hit.text, st.text_transform), bold=bold)
            need = round(em * _HEAD * size * EMU_PER_PT) + ph
            cl, _ct, cr, _cb = css.cell_insets(cell.style, px, py)
            avail = xs[c1] - xs[c] - cl - cr
            band = ys[r1] - ys[r]
            line = round(size * _LINE * EMU_PER_PT)
            h = min(round(height_em * line), round(band * _ROW_MAX))
            if need > avail or h < line + pv:
                continue  # does not fit: the badge stays a text highlight
            cand = _Cand(r, c, c1, cell, st, hit, bold, need, avail, band, h, cl, cr)
            if hit.lead:
                lead = Paragraph(runs=_trim(hit.lead))
                tx = _para_em(lead, bool(cst.bold), cst.text_transform)[0]
                cand.text_end = round((tx * _HEAD + _GAP_EM) * size * EMU_PER_PT)
            cands.append(cand)
        # one width per column (the widest pill) and one left edge for the pills that follow text
        while True:
            col_w: dict[int, int] = {}
            col_x: dict[int, int] = {}
            for k in cands:
                if k.c1 - k.c == 1:
                    col_w[k.c] = max(col_w.get(k.c, 0), k.need)
                    col_x[k.c] = max(col_x.get(k.c, 0), k.text_end)
            bad = [k for k in cands if k.hit.lead and col_x[k.c] + col_w[k.c] > k.avail]
            if not bad:
                break
            worst = max(bad, key=lambda k: k.text_end)
            cands.remove(worst)  # its text is too long to share the line: the badge stays a highlight
        pills: list[Placed] = []
        swapped: dict[int, Cell] = {}
        for k in cands:
            single = k.c1 - k.c == 1
            w = min(max(col_w[k.c], k.need) if single else k.need, k.avail)
            x0, x1 = xs[k.c] + k.cl, xs[k.c1] - k.cr
            al = (k.hit.para.style.align if k.hit.para.style and k.hit.para.style.align else None) or (
                pl.style.merged(k.cell.style).align or "left"
            )
            if k.hit.lead:
                x = x0 + col_x[k.c]
            else:
                x = x0 if al in ("left", "justify") else x1 - w if al == "right" else x0 + (x1 - x0 - w) // 2
            ink = k.st.color or theme.badge_ink(k.hit.run.highlight)
            style = k.st.merged(fast_style(fill=k.st.fill or k.hit.run.highlight, color=ink, bold=k.bold))
            run = k.hit.run.model_copy(
                update={"highlight": None, "color": None, "bold": False, "text": k.hit.text}
            )
            if k.hit.lead:
                para = k.hit.para.model_copy(update={"runs": _trim(k.hit.lead)})
            else:
                para = Paragraph()
            swapped[id(k.cell)] = k.cell.model_copy(update={"paragraphs": [para]})
            pills.append(
                Placed(
                    element=Shape(
                        shape="rounded-rect",
                        paragraphs=[Paragraph(runs=[run])],
                        classes=["pill"],
                        attrs={"pill": True},
                    ),
                    x=x,
                    y=ys[k.r] + (k.band - k.h) // 2,
                    w=w,
                    h=k.h,
                    style=style,
                    font_scale=pl.font_scale,
                )
            )
        if not pills:
            res.append(pl)
            continue
        rows = [[swapped.get(id(c), c) for c in row] for row in t.rows]
        res.append(pl.model_copy(update={"element": t.model_copy(update={"rows": rows})}))
        res.extend(pills)
    return res
