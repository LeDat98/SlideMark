"""python-pptx shapes -> flat ``Item`` lists (absolute EMU boxes, parsed text); no layout decisions."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from lxml import etree
from pptx.oxml.ns import qn

from ..ir import Diagnostic

MONO = ("consolas", "courier", "menlo", "monaco", "mono", "source code")


@dataclass
class RunT:
    text: str
    bold: bool = False
    italic: bool = False
    strike: bool = False
    sup: bool = False
    sub: bool = False
    code: bool = False
    color: str | None = None  # RRGGBB upper
    badge: str | None = None  # highlight color RRGGBB when the run is a badge
    link: str | None = None
    size: float | None = None


@dataclass
class ParaT:
    runs: list[RunT] = field(default_factory=list)
    marker: str | None = None  # "bullet" | "number"
    level: int = 0
    size: float | None = None
    marl: int | None = None
    lvl_attr: int | None = None

    @property
    def plain(self) -> str:
        return "".join(r.text for r in self.runs)

    @property
    def all_bold(self) -> bool:
        txt = [r for r in self.runs if r.text.strip()]
        return bool(txt) and all(r.bold for r in txt)


@dataclass
class CellT:
    paras: list[ParaT] = field(default_factory=list)
    hmerge: bool = False
    vmerge: bool = False


@dataclass
class ChartT:
    kind: str
    title: str | None
    categories: list[str]
    series: list[tuple[str, list[float | None]]]
    options: dict[str, str]


@dataclass
class Item:
    kind: str  # text | shape | table | chart | image | line
    x: int
    y: int
    w: int
    h: int
    name: str = ""
    ph: str | None = None  # placeholder type (title, ctrTitle, subTitle, body, ftr, sldNum, dt, obj)
    fill: str | None = None  # RRGGBB, "x" (non-solid / theme style) or None
    line: bool = False
    prst: str | None = None
    paras: list[ParaT] = field(default_factory=list)
    rows: list[list[CellT]] = field(default_factory=list)
    chart: ChartT | None = None
    img: tuple[bytes, str] | None = None
    alt: str = ""
    has_slidenum: bool = False
    role: str | None = None  # set by structure: title/lead/conclusion/footnote/footer/decor/callout:<kind>
    uid: int = 0
    radius: float | None = None  # corner radius in pt of a rounded rectangle
    sid: int = 0  # shape id in the slide (what ``a:stCxn``/``a:endCxn`` point at)

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2

    @property
    def area(self) -> int:
        return max(self.w, 0) * max(self.h, 0)

    @property
    def text(self) -> str:
        return "\n".join(p.plain for p in self.paras).strip()

    @property
    def max_size(self) -> float | None:
        sizes = [p.size for p in self.paras if p.size]
        return max(sizes) if sizes else None


@dataclass
class ConnT:
    """A connector: start/end point in slide EMU, the shape ids it is glued to and its arrowheads."""

    x0: float
    y0: float
    x1: float
    y1: float
    st: int | None = None  # a:stCxn id
    en: int | None = None  # a:endCxn id
    arrow_end: bool = False  # a:tailEnd (the end of the line; what the renderer draws for ``a>b``)
    arrow_start: bool = False  # a:headEnd
    order: int = 0


@dataclass
class SlideData:
    items: list[Item] = field(default_factory=list)
    conns: list[ConnT] = field(default_factory=list)
    notes: str | None = None
    hidden: bool = False
    connectors: int = 0
    num_field: bool = False


@dataclass
class ReadCtx:
    accent: str  # theme accent RRGGBB
    diags: list[Diagnostic] = field(default_factory=list)
    slide_no: int = 0
    slide_index: dict[Any, int] = field(default_factory=dict)  # slide part -> 1-based number
    next_uid: int = 0

    def skip(self, what: str, hint: str = "rebuild it as native shapes, text or a picture") -> None:
        self.diags.append(
            Diagnostic(
                level="info",
                message=f"skipped {what}",
                slide=self.slide_no,
                rule="import-skipped",
                hint=hint,
            )
        )


# --------------------------------------------------------------------------- text


def _hex(el) -> str | None:
    if el is None:
        return None
    clr = el.find(qn("a:srgbClr"))
    if clr is not None and clr.get("val"):
        return clr.get("val").upper()
    return None


def _read_run(r, ctx: ReadCtx, part) -> RunT:
    t = r.find(qn("a:t"))
    text = (t.text or "") if t is not None else ""
    run = RunT(text=text)
    rpr = r.find(qn("a:rPr"))
    if rpr is None:
        return run
    run.bold = rpr.get("b") in ("1", "true")
    run.italic = rpr.get("i") in ("1", "true")
    run.strike = (rpr.get("strike") or "noStrike") != "noStrike"
    base = rpr.get("baseline")
    if base and base.lstrip("-").isdigit():
        run.sup = int(base) > 0
        run.sub = int(base) < 0
    if rpr.get("sz", "").isdigit():
        run.size = int(rpr.get("sz")) / 100
    fill = rpr.find(qn("a:solidFill"))
    run.color = _hex(fill)
    hl = rpr.find(qn("a:highlight"))
    if hl is not None:
        run.badge = _hex(hl) or "x"
        run.text = text.strip("　")
    latin = rpr.find(qn("a:latin"))
    if latin is not None and any(m in (latin.get("typeface") or "").lower() for m in MONO):
        run.code = True
    link = rpr.find(qn("a:hlinkClick"))
    if link is not None:
        run.link = _link_target(link, ctx, part)
    return run


def _link_target(link, ctx: ReadCtx, part) -> str | None:
    rid = link.get(qn("r:id"))
    if not rid or part is None:
        return None
    try:
        rel = part.rels[rid]
    except KeyError:
        return None
    if rel.is_external:
        return rel.target_ref
    n = ctx.slide_index.get(getattr(rel, "target_part", None))
    return f"#{n}" if n else None


def read_paras(
    txbody, ctx: ReadCtx, part, default_bullets: bool = False, keep_empty: bool = False
) -> tuple[list[ParaT], bool]:
    """Paragraphs of a txBody; the flag says a slide-number field was seen."""
    out: list[ParaT] = []
    slidenum = False
    if txbody is None:
        return out, slidenum
    for p in txbody.findall(qn("a:p")):
        ppr = p.find(qn("a:pPr"))
        marker = "bullet" if default_bullets else None
        lvl_attr = marl = None
        if ppr is not None:
            if ppr.find(qn("a:buNone")) is not None:
                marker = None
            elif ppr.find(qn("a:buAutoNum")) is not None:
                marker = "number"
            elif ppr.find(qn("a:buChar")) is not None or ppr.find(qn("a:buBlip")) is not None:
                marker = "bullet"
            if ppr.get("lvl", "").isdigit():
                lvl_attr = int(ppr.get("lvl"))
            if ppr.get("marL", "").lstrip("-").isdigit():
                marl = int(ppr.get("marL"))
        runs: list[RunT] = []
        for ch in p:
            tag = etree.QName(ch).localname
            if tag == "r":
                runs.append(_read_run(ch, ctx, part))
            elif tag == "br":
                runs.append(RunT(text="\n"))
            elif tag == "fld":
                if (ch.get("type") or "").startswith("slidenum"):
                    slidenum = True
                else:
                    runs.append(_read_run(ch, ctx, part))
        while runs and runs[-1].text == "\n":
            runs.pop()
        if not "".join(r.text for r in runs).strip() and not keep_empty:
            continue
        size = next((r.size for r in runs if r.size), None)
        if size is None:
            end = p.find(qn("a:endParaRPr"))
            if end is not None and end.get("sz", "").isdigit():
                size = int(end.get("sz")) / 100
        out.append(ParaT(runs=runs, marker=marker, size=size, marl=marl, lvl_attr=lvl_attr))
    _levels(out)
    return out, slidenum


def _levels(paras: list[ParaT]) -> None:
    if any(p.lvl_attr for p in paras):
        for p in paras:
            p.level = p.lvl_attr or 0
        return
    marls = sorted({p.marl for p in paras if p.marker and p.marl is not None})
    for p in paras:
        if p.marker and p.marl is not None:
            p.level = marls.index(p.marl)


# --------------------------------------------------------------------------- geometry / style


def _fill_of(el) -> tuple[str | None, bool]:
    sppr = el.find(qn("p:spPr"))
    style = el.find(qn("p:style"))
    fill: str | None = None
    line = False
    if sppr is not None:
        if sppr.find(qn("a:noFill")) is not None:
            fill = None
        elif sppr.find(qn("a:solidFill")) is not None:
            fill = _hex(sppr.find(qn("a:solidFill"))) or "x"
        elif any(sppr.find(qn(t)) is not None for t in ("a:gradFill", "a:blipFill", "a:pattFill")):
            fill = "x"
        elif style is not None and _ref_idx(style, "a:fillRef"):
            fill = "x"
        ln = sppr.find(qn("a:ln"))
        if ln is not None:
            line = ln.find(qn("a:noFill")) is None and (
                ln.find(qn("a:solidFill")) is not None or (style is not None and _ref_idx(style, "a:lnRef"))
            )
        elif style is not None and _ref_idx(style, "a:lnRef"):
            line = True
    return fill, line


def _ref_idx(style, tag: str) -> bool:
    ref = style.find(qn(tag))
    return ref is not None and (ref.get("idx") or "0") != "0"


class Tf:
    """Affine map from a group's child space to slide EMU: ``abs = a + b * local`` per axis."""

    def __init__(self, ax=0.0, bx=1.0, ay=0.0, by=1.0):
        self.ax, self.bx, self.ay, self.by = ax, bx, ay, by

    def box(self, x, y, w, h) -> tuple[int, int, int, int]:
        return (
            round(self.ax + self.bx * x),
            round(self.ay + self.by * y),
            round(self.bx * w),
            round(self.by * h),
        )

    def child(self, el) -> Tf:
        xf = el.find(qn("p:grpSpPr") + "/" + qn("a:xfrm"))
        if xf is None:
            return self
        try:
            off, ext = xf.find(qn("a:off")), xf.find(qn("a:ext"))
            choff, chext = xf.find(qn("a:chOff")), xf.find(qn("a:chExt"))
            ox, oy, cx, cy = int(off.get("x")), int(off.get("y")), int(ext.get("cx")), int(ext.get("cy"))
            qx, qy = int(choff.get("x")), int(choff.get("y"))
            qw, qh = int(chext.get("cx")) or cx or 1, int(chext.get("cy")) or cy or 1
        except (AttributeError, TypeError, ValueError):
            return self
        sx, sy = cx / qw, cy / qh
        # local -> group space: ox + (x - qx) * sx ; then self
        gx_a, gx_b = ox - qx * sx, sx
        gy_a, gy_b = oy - qy * sy, sy
        return Tf(
            self.ax + self.bx * gx_a,
            self.bx * gx_b,
            self.ay + self.by * gy_a,
            self.by * gy_b,
        )


# --------------------------------------------------------------------------- charts

_KINDS = (
    ("DOUGHNUT", "doughnut"),
    ("PIE", "pie"),
    ("RADAR", "radar"),
    ("XY_SCATTER", "scatter"),
    ("BUBBLE", "scatter"),
    ("LINE", "line"),
    ("AREA", "area"),
)


def chart_kind(name: str) -> str | None:
    for key, kind in _KINDS:
        if key in name:
            return kind
    if "COL" in name or "BAR" in name:
        horiz = "COL" not in name
        stacked = "STACKED" in name
        return ("stacked-" if stacked else "") + ("bar" if horiz else "column")
    return None


def _num(v) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f and abs(f) != float("inf") else None


def _xtext(t: str) -> str:
    f = _num(t)
    if f is None:
        return t
    return str(int(f)) if f == int(f) else repr(f)


def read_chart(shape, ctx: ReadCtx) -> ChartT | None:
    chart = shape.chart
    try:
        ct = chart.chart_type
        name = ct.name if hasattr(ct, "name") else str(ct)
    except Exception:
        ctx.skip("a chart of unknown type")
        return None
    kind = chart_kind(name)
    if kind is None:
        ctx.skip(f"chart type {name.lower()}", "use one of the 10 chart kinds: bar, column, line, pie, ...")
        return None
    if len(chart.plots) > 1:
        ctx.diags.append(
            Diagnostic(
                level="info",
                message="combo chart: only the first plot was imported",
                slide=ctx.slide_no,
                rule="import-skipped",
                hint="split the chart if both plots matter",
            )
        )
    plot = chart.plots[0]
    series = list(plot.series)
    if kind == "scatter":
        xs: list[str] = []
        if series:
            xs = [
                _xtext(v.text or "")
                for v in series[0]._element.xpath("./c:xVal//c:pt/c:v")  # type: ignore[attr-defined]
            ]
        cats = xs
    else:
        cats = [str(c) for c in plot.categories]
    data = [(s.name or "", [_num(v) for v in s.values]) for s in series]
    opts: dict[str, str] = {}
    title = None
    try:
        if chart.has_title:
            title = chart.chart_title.text_frame.text.strip() or None
    except Exception:
        title = None
    try:
        nser = len(data)
        pie = kind in ("pie", "doughnut")
        default = None if (nser <= 1 and not pie) else ("right" if pie else "bottom")
        if nser > 1:
            default = "bottom"
        elif pie:
            default = None  # documented default: none for a single series
        if chart.has_legend:
            pos = {1: "bottom", -4107: "bottom", -4131: "left", -4152: "right", -4160: "top"}.get(
                int(chart.legend.position), "right"
            )
            if pos != default:
                opts["legend"] = pos
        elif default is not None:
            opts["legend"] = "none"
    except Exception:
        pass
    fmt = None
    try:
        if plot.has_data_labels:
            dl = plot.data_labels
            if kind in ("pie", "doughnut") and dl.show_percentage:
                opts["labels"] = "percent"
            elif dl.show_value:
                opts["labels"] = "on"
            if "labels" in opts and not dl.number_format_is_linked and dl.number_format != "General":
                fmt = dl.number_format
    except Exception:
        pass
    try:
        va = chart.value_axis
        if not va.visible:
            opts["axis"] = "off"
        if fmt is None and not va.tick_labels.number_format_is_linked:
            nf = va.tick_labels.number_format
            if nf and nf != "General":
                fmt = nf
        if va.minimum_scale is not None:
            opts["min"] = f"{va.minimum_scale:g}"
        if va.maximum_scale is not None:
            opts["max"] = f"{va.maximum_scale:g}"
    except Exception:
        pass
    if fmt:
        opts["fmt"] = fmt
    return ChartT(kind=kind, title=title, categories=cats, series=data, options=opts)


# --------------------------------------------------------------------------- shapes


def _alt(el, name: str) -> str:
    for c in el.iter(qn("p:cNvPr")):
        return c.get("descr") or ""
    return ""


def read_slide(slide, ctx: ReadCtx) -> SlideData:
    data = SlideData()
    data.hidden = slide._element.get("show") in ("0", "false")
    part = slide.part
    _walk(slide.shapes, Tf(), data, ctx, part)
    try:
        if slide.has_notes_slide:
            txt = (slide.notes_slide.notes_text_frame.text or "").strip()
            data.notes = txt or None
    except Exception:
        data.notes = None
    return data


def _walk(shapes, tf: Tf, data: SlideData, ctx: ReadCtx, part) -> None:
    for sh in shapes:
        try:
            _one(sh, tf, data, ctx, part)
        except Exception as e:  # never raise: a shape we cannot read is skipped
            ctx.skip(f"shape {getattr(sh, 'name', '?')!r} ({type(e).__name__})")


def _new(ctx: ReadCtx, kind: str, box, sid: int = 0, **kw) -> Item:
    ctx.next_uid += 1
    return Item(kind=kind, x=box[0], y=box[1], w=box[2], h=box[3], uid=ctx.next_uid, sid=sid, **kw)


def _radius(geom, box) -> float | None:
    """Corner radius (pt) from the ``adj`` guide of a ``roundRect``; None when the guide is absent."""
    for gd in geom.iter(qn("a:gd")):
        m = (gd.get("fmla") or "").split()
        if gd.get("name") == "adj" and len(m) == 2 and m[1].lstrip("-").isdigit():
            return int(m[1]) / 100000 * min(box[2], box[3]) / 12700
    return None


def _int(v) -> int | None:
    return int(v) if isinstance(v, str) and v.lstrip("-").isdigit() else None


def _arrow(ln, tag: str) -> bool:
    end = ln.find(qn(tag)) if ln is not None else None
    return end is not None and (end.get("type") or "none") != "none"


def _read_conn(el, tf: Tf, order: int) -> ConnT | None:
    """Endpoints of a ``p:cxnSp`` (path start = top-left of its box, flips and rotation applied)."""
    xf = el.find(qn("p:spPr") + "/" + qn("a:xfrm"))
    if xf is None or xf.find(qn("a:off")) is None or xf.find(qn("a:ext")) is None:
        return None
    try:
        x, y = int(xf.find(qn("a:off")).get("x")), int(xf.find(qn("a:off")).get("y"))
        w, h = int(xf.find(qn("a:ext")).get("cx")), int(xf.find(qn("a:ext")).get("cy"))
        rot = (int(xf.get("rot") or 0) / 60000) % 360
    except (TypeError, ValueError):
        return None
    mx, my = x + w / 2, y + h / 2
    pts = []
    for px, py in ((x, y), (x + w, y + h)):
        if xf.get("flipH") in ("1", "true"):
            px = 2 * mx - px
        if xf.get("flipV") in ("1", "true"):
            py = 2 * my - py
        if rot:
            c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
            dx, dy = px - mx, py - my
            px, py = mx + dx * c - dy * s, my + dx * s + dy * c
        pts.append((tf.ax + tf.bx * px, tf.ay + tf.by * py))
    cnv = el.find(qn("p:nvCxnSpPr") + "/" + qn("p:cNvCxnSpPr"))
    st = en = None
    if cnv is not None:
        a, b = cnv.find(qn("a:stCxn")), cnv.find(qn("a:endCxn"))
        st = _int(a.get("id")) if a is not None else None
        en = _int(b.get("id")) if b is not None else None
    ln = el.find(qn("p:spPr") + "/" + qn("a:ln"))
    return ConnT(
        pts[0][0],
        pts[0][1],
        pts[1][0],
        pts[1][1],
        st,
        en,
        _arrow(ln, "a:tailEnd"),
        _arrow(ln, "a:headEnd"),
        order,
    )


def _one(sh, tf: Tf, data: SlideData, ctx: ReadCtx, part) -> None:
    el = sh._element
    tag = etree.QName(el).localname
    name = sh.name or ""
    if tag == "grpSp":
        _walk(sh.shapes, tf.child(el), data, ctx, part)
        return
    if tag == "cxnSp":
        data.connectors += 1
        conn = _read_conn(el, tf, len(data.conns))
        if conn is not None:
            data.conns.append(conn)
        return
    try:
        box = tf.box(sh.left or 0, sh.top or 0, sh.width or 0, sh.height or 0)
    except Exception:
        box = (0, 0, 0, 0)
    if tag == "sp":
        ph = el.find(qn("p:nvSpPr") + "/" + qn("p:nvPr") + "/" + qn("p:ph"))
        ph_type = (ph.get("type") or "obj") if ph is not None else None
        if el.xpath(".//*[local-name()='oMath']"):
            ctx.skip(f"equation {name!r}", "write the formula as text or an image")
            return
        fill, line = _fill_of(el)
        geom = el.find(qn("p:spPr") + "/" + qn("a:prstGeom"))
        prst = geom.get("prst") if geom is not None else None
        radius = _radius(geom, box) if prst == "roundRect" else None
        default_bullets = ph_type in ("body", "obj")
        paras, num = read_paras(
            el.find(qn("p:txBody")), ctx, part, default_bullets, keep_empty=name.lower().startswith("code")
        )
        while paras and not paras[-1].plain.strip():
            paras.pop()
        data.num_field = data.num_field or num
        it = _new(
            ctx,
            "text" if paras else "shape",
            box,
            sid=sh.shape_id,
            name=name,
            ph=ph_type,
            fill=fill,
            line=line,
            prst=prst,
            radius=radius,
            paras=paras,
            has_slidenum=num,
        )
        data.items.append(it)
    elif tag == "pic":
        if el.xpath(".//*[local-name()='videoFile' or local-name()='audioFile']"):
            ctx.skip(f"media {name!r}", "media cannot be imported")
            return
        img = sh.image
        it = _new(ctx, "image", box, sid=sh.shape_id, name=name, img=(img.blob, img.ext), alt=_alt(el, name))
        data.items.append(it)
    elif tag == "graphicFrame":
        if sh.has_table:
            rows: list[list[CellT]] = []
            for tr in sh.table._tbl.tr_lst:
                row = []
                for tc in tr.tc_lst:
                    paras, _ = read_paras(tc.find(qn("a:txBody")), ctx, part)
                    row.append(
                        CellT(
                            paras=paras,
                            hmerge=tc.get("hMerge") in ("1", "true"),
                            vmerge=tc.get("vMerge") in ("1", "true"),
                        )
                    )
                rows.append(row)
            data.items.append(_new(ctx, "table", box, sid=sh.shape_id, name=name, rows=rows))
        elif sh.has_chart:
            ch = read_chart(sh, ctx)
            if ch is not None:
                data.items.append(_new(ctx, "chart", box, sid=sh.shape_id, name=name, chart=ch))
        else:
            ctx.skip(f"object {name!r} (SmartArt, OLE or other)")
    else:
        ctx.skip(f"{tag} {name!r}")
