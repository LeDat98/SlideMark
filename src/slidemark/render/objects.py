"""Tables, charts, images and code -> native PowerPoint objects."""

from __future__ import annotations

from pathlib import Path

from lxml import etree
from pptx.chart.data import CategoryChartData, XyChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.oxml.ns import qn
from pptx.util import Emu, Pt
from pygments import lex
from pygments.lexers import TextLexer, get_lexer_by_name
from pygments.token import Comment, Keyword, Name, Number, Operator, String

from ..ir import Chart, Code, Image, Paragraph, Placed, Run, Style, Table
from ..layout import measure
from ..layout.tables import column_widths, table_grid
from .text import fill_text
from .util import RenderCtx, hex6, rgb

CHART_TYPES = {
    "bar": XL_CHART_TYPE.BAR_CLUSTERED,
    "column": XL_CHART_TYPE.COLUMN_CLUSTERED,
    "stacked-bar": XL_CHART_TYPE.BAR_STACKED,
    "stacked-column": XL_CHART_TYPE.COLUMN_STACKED,
    "line": XL_CHART_TYPE.LINE_MARKERS,
    "area": XL_CHART_TYPE.AREA,
    "pie": XL_CHART_TYPE.PIE,
    "doughnut": XL_CHART_TYPE.DOUGHNUT,
    "scatter": XL_CHART_TYPE.XY_SCATTER,
    "radar": XL_CHART_TYPE.RADAR_MARKERS,
}


def flag(v, default: bool = False) -> bool:
    if v is None:
        return default
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "on", "yes", "y")
    return bool(v)


# --------------------------------------------------------------------------- table


def _cell_border(tcPr, color: str, width: int = 6350) -> None:
    for i, tag in enumerate(("a:lnL", "a:lnR", "a:lnT", "a:lnB")):
        ln = etree.Element(qn(tag))
        ln.set("w", str(width))
        ln.set("cap", "flat")
        ln.set("cmpd", "sng")
        sf = etree.SubElement(ln, qn("a:solidFill"))
        etree.SubElement(sf, qn("a:srgbClr")).set("val", color)
        tcPr.insert(i, ln)


def _mix(a: str, b: str, t: float) -> str:
    """Blend two RRGGBB colors: ``t`` = share of ``b``."""
    return "".join(
        f"{round(int(a[i : i + 2], 16) * (1 - t) + int(b[i : i + 2], 16) * t):02X}" for i in (0, 2, 4)
    )


def add_table(rc: RenderCtx, slide, pl: Placed, name: str) -> None:
    t: Table = pl.element  # type: ignore[assignment]
    theme = rc.theme
    nrows, ncols, anchors = table_grid(t)
    gf = slide.shapes.add_table(nrows, ncols, Emu(pl.x), Emu(pl.y), Emu(pl.w), Emu(max(pl.h, nrows * 100000)))
    gf.name = name
    tbl = gf.table
    tblPr = tbl._tbl.tblPr
    for attr in ("firstRow", "bandRow", "firstCol", "lastRow", "lastCol", "bandCol"):
        tblPr.attrib.pop(attr, None)
    for child in list(tblPr):
        if etree.QName(child).localname == "tableStyleId":
            tblPr.remove(child)
    cw = pl.element.attrs.get("_col_w") or column_widths(t, ncols, anchors, pl.w)
    rh = pl.element.attrs.get("_row_h") or [max(pl.h // nrows, 1)] * nrows
    for i, w in enumerate(cw[:ncols]):
        tbl.columns[i].width = Emu(int(w))
    for i, h in enumerate(rh[:nrows]):
        tbl.rows[i].height = Emu(int(h))
    border = hex6(theme, theme.table_border)
    body_fill = theme.table_body_fill
    zebra = "zebra" in t.classes or flag(t.attrs.get("zebra"))
    zebra_fill = theme.table_zebra_fill or "#" + _mix(hex6(theme, body_fill), hex6(theme, "surface"), 0.6)
    # fill every grid cell first (merged-away cells included) so nothing falls back to a default style
    for r in range(nrows):
        for c in range(ncols):
            cell = tbl.cell(r, c)
            hdr = r < t.header_rows
            fill = theme.table_header_fill if hdr else ("surface" if c < t.header_cols else body_fill)
            if zebra and not hdr and c >= t.header_cols and (r - t.header_rows) % 2 == 1:
                fill = zebra_fill
            cell.fill.solid()
            cell.fill.fore_color.rgb = rgb(theme, fill)
            _cell_border(cell._tc.get_or_add_tcPr(), border)
    for r, c, ct in anchors:
        cell = tbl.cell(r, c)
        rs = min(max(ct.rowspan, 1), nrows - r)
        cs = min(max(ct.colspan, 1), ncols - c)
        if rs > 1 or cs > 1:
            try:
                cell.merge(tbl.cell(r + rs - 1, c + cs - 1))
            except Exception:
                rc.diag(
                    "table-merge",
                    f"cannot merge cell at row {r + 1}, col {c + 1}",
                    "check the < and ^ markers",
                )
        hdr = r < t.header_rows
        st = pl.style
        if hdr:
            st = st.merged(
                Style(bold=True, color=theme.table_header_color, align="center" if cs > 1 else None)
            )
        elif c < t.header_cols:
            st = st.merged(Style(bold=True))
        st = st.merged(ct.style)
        if ct.style and ct.style.fill:
            cell.fill.solid()
            cell.fill.fore_color.rgb = rgb(theme, ct.style.fill)
        fill_text(
            rc,
            cell.text_frame,
            ct.paragraphs,
            st.merged(Style(valign=st.valign or "middle")),
            pl.font_scale,
            inset=0,
        )
        cell.margin_left = cell.margin_right = Emu(measure.CELL_PAD_X)
        cell.margin_top = cell.margin_bottom = Emu(measure.CELL_PAD_Y)


# --------------------------------------------------------------------------- chart


def add_chart(rc: RenderCtx, slide, pl: Placed, name: str) -> None:
    ch: Chart = pl.element  # type: ignore[assignment]
    theme = rc.theme
    opts = {str(k).lower().replace("-", "_"): v for k, v in ch.options.items()}
    ctype = CHART_TYPES.get(ch.kind, XL_CHART_TYPE.COLUMN_CLUSTERED)
    cats = list(ch.categories) or [
        str(i + 1) for i in range(max((len(s.values) for s in ch.series), default=0))
    ]
    if ch.kind == "scatter":
        data = XyChartData()
        xs = []
        for i, c in enumerate(cats):
            try:
                xs.append(float(str(c).replace(",", "")))
            except ValueError:
                xs.append(float(i + 1))
        for s in ch.series:
            ser = data.add_series(s.name)
            for x, v in zip(xs, s.values, strict=False):
                if v is not None:
                    ser.add_data_point(x, v)
    else:
        data = CategoryChartData()
        data.categories = cats
        for s in ch.series:
            vals = list(s.values) + [None] * (len(cats) - len(s.values))
            data.add_series(s.name, vals[: len(cats)])
        if not ch.series:
            data.add_series("", [None] * len(cats))
    gf = slide.shapes.add_chart(ctype, Emu(pl.x), Emu(pl.y), Emu(pl.w), Emu(pl.h), data)
    gf.name = name
    chart = gf.chart
    size = pl.style.font_size or 12
    chart.font.size = Pt(size * pl.font_scale)
    chart.font.color.rgb = rgb(theme, pl.style.color or "fg")
    chart.font.name = pl.style.font or theme.fonts.body
    if ch.title:
        chart.has_title = True
        tf = chart.chart_title.text_frame
        tf.text = ch.title
        run = tf.paragraphs[0].runs[0]
        run.font.size = Pt(size * 1.2 * pl.font_scale)
        run.font.bold = True
        run.font.color.rgb = rgb(theme, "fg")
    else:
        chart.has_title = False
    pie = ch.kind in ("pie", "doughnut")
    legend = opts.get("legend", None)
    show_legend = pie or len(ch.series) > 1
    pos = XL_LEGEND_POSITION.BOTTOM
    if isinstance(legend, str):
        low = legend.lower()
        pos_map = {
            "bottom": XL_LEGEND_POSITION.BOTTOM,
            "top": XL_LEGEND_POSITION.TOP,
            "left": XL_LEGEND_POSITION.LEFT,
            "right": XL_LEGEND_POSITION.RIGHT,
        }
        if low in pos_map:
            show_legend, pos = True, pos_map[low]
        else:
            show_legend = flag(legend, show_legend)
    elif legend is not None:
        show_legend = bool(legend)
    chart.has_legend = show_legend
    if show_legend:
        chart.legend.position = pos
        chart.legend.include_in_layout = False
    palette = [hex6(theme, c) for c in theme.palette]
    plot = chart.plots[0]
    if flag(opts.get("labels")) or flag(opts.get("data_labels")):
        nf = opts.get("number_format") or opts.get("format")
        if ch.kind != "scatter":  # python-pptx has no data labels for XY series
            plot.has_data_labels = True
            dl = plot.data_labels
            dl.show_value = True
            if nf:
                dl.number_format = str(nf)
                dl.number_format_is_linked = False
            dl.font.size = Pt(size * 0.9 * pl.font_scale)
    for plot in chart.plots:
        for si, ser in enumerate(plot.series):
            color = palette[si % len(palette)]
            if pie:
                for pi in range(len(cats)):
                    pt = ser.points[pi]
                    pt.format.fill.solid()
                    pt.format.fill.fore_color.rgb = rgb(theme, "#" + palette[pi % len(palette)])
            elif ch.kind in ("line", "radar", "scatter"):
                if ch.kind == "scatter":
                    ser.format.line.fill.background()
                else:
                    ser.format.line.color.rgb = rgb(theme, "#" + color)
                    ser.format.line.width = Pt(2.25)
                if hasattr(ser, "smooth"):
                    ser.smooth = False
                try:
                    ser.marker.format.fill.solid()
                    ser.marker.format.fill.fore_color.rgb = rgb(theme, "#" + color)
                    ser.marker.format.line.color.rgb = rgb(theme, "#" + color)
                except Exception:
                    pass
            else:
                ser.format.fill.solid()
                ser.format.fill.fore_color.rgb = rgb(theme, "#" + color)
    if not pie:
        try:
            va = chart.value_axis
            va.has_major_gridlines = True
            va.major_gridlines.format.line.color.rgb = rgb(theme, "border")
            va.format.line.fill.background()
            nf = opts.get("axis_format") or opts.get("number_format")
            if nf:
                va.tick_labels.number_format = str(nf)
                va.tick_labels.number_format_is_linked = False
            chart.category_axis.format.line.color.rgb = rgb(theme, "border")
        except Exception:
            pass  # radar / scatter axes differ; defaults are fine


# --------------------------------------------------------------------------- image


def resolve_image(rc: RenderCtx, src: str) -> Path | None:
    if "://" in src or src.startswith("data:"):
        return None
    p = Path(src).expanduser()
    if not p.is_absolute():
        p = Path(rc.base_dir) / p
    return p if p.is_file() else None


def add_image(rc: RenderCtx, slide, pl: Placed, name: str) -> bool:
    """Add the picture; returns False when the image cannot be used (caller draws a placeholder)."""
    im: Image = pl.element  # type: ignore[assignment]
    path = resolve_image(rc, im.src)
    if path is None:
        hint = (
            "download it and use a local path"
            if "://" in im.src
            else "check the path, relative to the .md file"
        )
        rc.diag("image-missing", f"image not found: {im.src}", hint, line=im.line)
        return False
    try:
        from PIL import Image as PILImage

        with PILImage.open(path) as pil:
            iw, ih = pil.size
        x, y, w, h = pl.x, pl.y, pl.w, pl.h
        crop = None
        if im.fit == "contain" and iw and ih:
            s = min(w / iw, h / ih)
            dw, dh = round(iw * s), round(ih * s)
            x, y, w, h = x + (w - dw) // 2, y + (h - dh) // 2, dw, dh
        elif im.fit == "cover" and iw and ih:
            ia, ba = iw / ih, w / h
            crop = ((1 - ba / ia) / 2, 0.0) if ia > ba else (0.0, (1 - ia / ba) / 2)
        pic = slide.shapes.add_picture(str(path), Emu(x), Emu(y), Emu(w), Emu(h))
        if crop:
            pic.crop_left = pic.crop_right = crop[0]
            pic.crop_top = pic.crop_bottom = crop[1]
        pic.name = name
        pic._element.nvPicPr.cNvPr.set("descr", im.alt or "")
        return True
    except Exception as e:
        rc.diag(
            "image-unreadable",
            f"cannot read image {im.src}: {type(e).__name__}",
            "use PNG, JPEG or GIF",
            line=im.line,
        )
        return False


# --------------------------------------------------------------------------- code


def _token_color(ttype) -> tuple[str | None, bool]:
    if ttype in Comment:
        return "muted", True
    if ttype in Keyword:
        return "primary", False
    if ttype in String:
        return "success", False
    if ttype in Number:
        return "accent", False
    if ttype in Name.Function or ttype in Name.Class or ttype in Name.Builtin or ttype in Name.Decorator:
        return "secondary", False
    if ttype in Operator:
        return "fg", False
    return None, False


def code_paragraphs(c: Code) -> list[Paragraph]:
    try:
        lexer = get_lexer_by_name(c.lang) if c.lang else TextLexer()
    except Exception:
        lexer = TextLexer()
    text = c.text.expandtabs(4).rstrip("\n")
    lines: list[list[Run]] = [[]]
    for ttype, value in lex(text, lexer):
        color, italic = _token_color(ttype)
        parts = value.split("\n")
        for i, part in enumerate(parts):
            if i > 0:
                lines.append([])
            if part:
                lines[-1].append(Run(text=part, code=True, color=color, italic=italic))
    if len(lines) > 1 and not lines[-1]:
        lines.pop()
    return [Paragraph(runs=runs) for runs in lines]
