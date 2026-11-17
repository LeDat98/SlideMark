"""Measured facts of a .pptx for the gate KPIs (protocol step 3 of docs/DESIGN_RUBRIC.md).

    python bench/rubric/measure.py deck.pptx --deck <id> [--dense-ja] [-o measured-<id>.json]

For every slide it reads the file (no rendering, no judge):

* the smallest text size per role: ``body`` (text boxes, placeholders, long shape text, table cells), ``node``
  (short text inside a shape: a diagram node, a card title), ``label`` (diagram labels, tags, legend, eyebrow),
  ``footnote`` (footers, sources, page numbers) and ``chart`` (axis, legend and data-label text of a chart);
* text contrast: the run colour against the fill behind it (the shape's own solid fill, else the nearest filled
  shape under it, else the slide background); semi-transparent colours are blended;
* non-text contrast (WCAG 1.4.11): chart series fills and strokes, arrows / connectors and legend swatches against
  what is behind them (a card's hairline border is not judged: its text is what identifies it);
* empty space (G-05): the share of the body (under the title, above the footer, between the title's margins)
  taken by full-width or full-height bands (each >= 10% of the body) that meet no content box; >= 40% is weak (level 2), >= 65% fails
  (level 1). Framing slides (cover, section, closing) are skipped; only a failure is written;
* defects: text frames whose estimated text height (``slidemark.layout.measure``) exceeds the frame, shapes
  outside the slide, two text shapes that overlap without one holding the other.

Output (the format ``bench/rubric/score.py`` reads, see ``--measured``)::

    {"slides": {"3": {"G-06": 2, "G-09": 3}}, "facts": {"3": "min body 12 pt (floor 14); ..."}}

Mapping (floors from the KPI checks): body >= 14 pt (dense JA >= 10 pt), below 12 pt (dense JA: below 10 pt) is a
clear failure; node text >= 10 pt, below 8 pt a clear failure; labels, footnotes and chart text >= 8 pt, below 7 pt a
clear failure. Text contrast >= 4.5:1 (large text, >= 18 pt or bold >= 14 pt: 3:1); under 3:1 is a clear failure.
Non-text >= 3:1; under 1.5:1 is a clear failure. A clear failure writes level 1, a borderline one level 2, a pass
level 3 (``score.py`` lets a pass lift a judge level below 3, never lower a higher one). G-12 is written only for a
measured defect: a missing defect proves nothing about arrows through boxes or an awkward break.
"""

# ruff: noqa: E501
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "src"))

from pptx import Presentation  # noqa: E402
from pptx.enum.shapes import MSO_SHAPE_TYPE, PP_PLACEHOLDER  # noqa: E402
from pptx.oxml.ns import qn  # noqa: E402

from slidemark.contrast import ratio as _ratio  # noqa: E402
from slidemark.ir import Paragraph, Run, Style  # noqa: E402
from slidemark.layout import measure  # noqa: E402
from slidemark.theme import LayoutTokens  # noqa: E402

EMU_PT = 12700
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
C = "http://schemas.openxmlformats.org/drawingml/2006/chart"

# role -> (floor pt, clear-failure pt); the body floor of a dense JA deck is 10 pt
FLOORS = {
    "body": (14.0, 12.0),
    "node": (10.0, 8.0),
    "label": (8.0, 7.0),
    "footnote": (8.0, 7.0),
    "chart": (8.0, 7.0),
}
DENSE_BODY = (10.0, 10.0)
LABEL_NAME = re.compile(
    r"label|head\b|lane \d|legend|caption|tag\b|eyebrow|axis|badge|swatch|tier|gloss|kicker|pill|tick|note\b|stage",
    re.I,
)
FOOT_NAME = re.compile(r"foot|source|slide number|page|date", re.I)
ARROW_NAME = re.compile(r"edge|arrow|connector|bone|link|flow", re.I)
MARK_NAME = re.compile(r"swatch|dot|marker|icon", re.I)
DIAGRAM_NAME = re.compile(
    r"(Arch|Seq|Step|Venn|Lane|Legend|Swimlane|Cycle|Funnel|Pyramid|Matrix|Gantt)\b", re.I
)
CONTAIN_TOL = 3 * EMU_PT


# --------------------------------------------------------------------------- colours


def _hex(c: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*c)


def _blend(fg: tuple[int, int, int], alpha: float, bg: tuple[int, int, int]) -> tuple[int, int, int]:
    return tuple(round(f * alpha + b * (1 - alpha)) for f, b in zip(fg, bg, strict=True))  # type: ignore[return-value]


class Theme:
    """Scheme colours of the deck's first master (for ``schemeClr`` fills)."""

    def __init__(self, prs) -> None:
        self.map: dict[str, tuple[int, int, int]] = {}
        try:
            master = prs.slide_master
            for rel in master.part.rels.values():
                if rel.reltype.endswith("/theme"):
                    from lxml import etree

                    root = etree.fromstring(rel.target_part.blob)
                    scheme = root.find(f".//{{{A}}}clrScheme")
                    for el in scheme:
                        name = etree.QName(el).localname
                        ch = el[0]
                        val = ch.get("val") if etree.QName(ch).localname == "srgbClr" else ch.get("lastClr")
                        if val:
                            self.map[name] = (int(val[0:2], 16), int(val[2:4], 16), int(val[4:6], 16))
        except Exception:  # an odd theme part: scheme colours stay unknown
            self.map = {}
        self.map.setdefault("bg1", self.map.get("lt1", (255, 255, 255)))
        self.map.setdefault("tx1", self.map.get("dk1", (0, 0, 0)))
        self.map.setdefault("bg2", self.map.get("lt2", (255, 255, 255)))
        self.map.setdefault("tx2", self.map.get("dk2", (0, 0, 0)))


def _clr(el, theme: Theme) -> tuple[tuple[int, int, int], float] | None:
    """(rgb, alpha) of a colour element (srgbClr / schemeClr / prstClr child of a fill), else None."""
    if el is None:
        return None
    rgb = None
    tag = el.tag.split("}")[1]
    if tag == "srgbClr":
        v = el.get("val", "")
        if len(v) == 6:
            rgb = (int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16))
    elif tag == "schemeClr":
        rgb = theme.map.get(el.get("val", ""))
    elif tag == "prstClr":
        rgb = {"black": (0, 0, 0), "white": (255, 255, 255)}.get(el.get("val", ""))
    if rgb is None:
        return None
    alpha = 1.0
    for ch in el:
        if ch.tag == f"{{{A}}}alpha":
            alpha = int(ch.get("val", "100000")) / 100000
    return rgb, alpha


def _solid(parent, theme: Theme):
    """(rgb, alpha) of ``parent/a:solidFill``, else None (no fill, gradient, picture, noFill)."""
    if parent is None:
        return None
    sf = parent.find(f"{{{A}}}solidFill")
    if sf is None or not len(sf):
        return None
    return _clr(sf[0], theme)


def _sppr(sh):
    el = getattr(sh, "_element", None)
    if el is None:
        return None
    return el.find(qn("p:spPr"))


def _line_of(sh, theme: Theme):
    sp = _sppr(sh)
    if sp is None:
        return None, 0.0
    ln = sp.find(f"{{{A}}}ln")
    if ln is None:
        return None, 0.0
    return _solid(ln, theme), int(ln.get("w", "0")) / EMU_PT


# --------------------------------------------------------------------------- shapes


class Item:
    """One flattened shape with its box (EMU) and z-order."""

    def __init__(self, sh, z: int) -> None:
        self.sh, self.z = sh, z
        self.x, self.y = sh.left or 0, sh.top or 0
        self.w, self.h = sh.width or 0, sh.height or 0
        self.name = sh.name or ""

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2

    def contains(self, o: Item, tol: float = CONTAIN_TOL) -> bool:
        return (
            o.x >= self.x - tol
            and o.y >= self.y - tol
            and o.x + o.w <= self.x + self.w + tol
            and o.y + o.h <= self.y + self.h + tol
        )


def _flatten(shapes, out: list[Item]) -> None:
    for sh in shapes:
        if sh.shape_type == MSO_SHAPE_TYPE.GROUP:
            _flatten(sh.shapes, out)
        else:
            out.append(Item(sh, len(out)))


def _slide_bg(slide, theme: Theme) -> tuple[int, int, int]:
    for holder in (slide, slide.slide_layout, slide.slide_layout.slide_master):
        try:
            bg = holder._element.find(f".//{qn('p:bg')}")
        except Exception:
            bg = None
        if bg is not None:
            sp = bg.find(qn("p:bgPr"))
            c = _solid(sp, theme)
            if c:
                return c[0]
    return (255, 255, 255)


def _fill_rgb(it: Item, theme: Theme):
    """(rgb, alpha) of the shape's own solid fill, or None."""
    return _solid(_sppr(it.sh), theme)


def _backdrop(items: list[Item], below: int, x: float, y: float, bg: tuple[int, int, int], theme: Theme):
    """The colour under point (x, y) of the shape at z ``below``: the nearest solid fill under it, else the slide."""
    for it in reversed(items[:below]):
        if not (it.x <= x <= it.x + it.w and it.y <= y <= it.y + it.h) or it.w * it.h <= 0:
            continue
        if (
            it.sh.shape_type == MSO_SHAPE_TYPE.LINE
            or getattr(it.sh, "is_placeholder", False)
            and not it.sh.has_text_frame
        ):
            continue
        f = _fill_rgb(it, theme)
        if f is None or f[1] <= 0.02:
            continue
        under = _backdrop(items, it.z, x, y, bg, theme) if f[1] < 1 else bg
        return _blend(f[0], f[1], under)
    return bg


def _own_back(items: list[Item], it: Item, bg, theme: Theme):
    f = _fill_rgb(it, theme)
    under = _backdrop(items, it.z, it.cx, it.cy, bg, theme)
    if f is None or f[1] <= 0.02:
        return under
    return _blend(f[0], f[1], under)


# --------------------------------------------------------------------------- text


def _scale(tf) -> float:
    na = tf._txBody.find(f"{{{A}}}bodyPr/{{{A}}}normAutofit")
    if na is not None and na.get("fontScale"):
        return int(na.get("fontScale")) / 100000
    return 1.0


def _runs(tf, theme: Theme):
    """Yield (paragraph, run, size pt or None, rgb/alpha or None, bold) for every run with text."""
    for p in tf.paragraphs:
        d = p._p.find(f"{{{A}}}pPr/{{{A}}}defRPr")
        dsz = int(d.get("sz")) / 100 if d is not None and d.get("sz") else None
        dcol = _solid(d, theme) if d is not None else None
        for r in p.runs:
            if not r.text.strip():
                continue
            rpr = r._r.find(f"{{{A}}}rPr")
            sz = r.font.size.pt if r.font.size else dsz
            col = _solid(rpr, theme) if rpr is not None else None
            yield p, r, sz, col or dcol, bool(r.font.bold)


def _role(it: Item, tf, diagram: bool = False, is_table: bool = False) -> str:
    sh = it.sh
    if is_table:
        return "body"
    if getattr(sh, "is_placeholder", False):
        t = sh.placeholder_format.type
        if t in (PP_PLACEHOLDER.TITLE, PP_PLACEHOLDER.CENTER_TITLE):
            return "heading"
        if t in (PP_PLACEHOLDER.FOOTER, PP_PLACEHOLDER.SLIDE_NUMBER, PP_PLACEHOLDER.DATE):
            return "footnote"
    if FOOT_NAME.search(it.name) and not LABEL_NAME.search(it.name.replace("Footnote", "")):
        return "footnote"
    if re.search(r"foot ?note|footnote", it.name, re.I):
        return "footnote"
    if LABEL_NAME.search(it.name):
        return "label"
    text = tf.text.strip()
    if (diagram or sh.shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE) and len(text) <= 60 and text.count("\n") <= 2:
        return "node"  # short text of a diagram or a shape: a node name, a card title; prose stays body
    return "body"


def _frame_overflow(it: Item, tf) -> float:
    """Estimated text height / available height of a text frame (0 when not measurable)."""
    bp = tf._txBody.find(f"{{{A}}}bodyPr")
    if bp is None or it.w <= 0 or it.h <= 0:
        return 0.0
    if bp.find(f"{{{A}}}spAutoFit") is not None:
        return 0.0
    l_, t_, r_, b_ = (
        int(bp.get(k, d)) for k, d in (("lIns", 91440), ("tIns", 45720), ("rIns", 91440), ("bIns", 45720))
    )
    width, height = it.w - l_ - r_, it.h - t_ - b_
    if width <= 0 or height <= 0:
        return 0.0
    scale = _scale(tf)
    paras: list[Paragraph] = []
    for p in tf.paragraphs:
        runs, base = [], None
        for r in p.runs:
            rpr = r._r.find(f"{{{A}}}rPr")
            sz = r.font.size.pt if r.font.size else None
            if sz is not None:
                base = base or sz
            txt = r.text.upper() if rpr is not None and rpr.get("cap") == "all" else r.text
            runs.append(Run(text=txt, bold=bool(r.font.bold), size=None))
        if not runs:
            d = p._p.find(f"{{{A}}}endParaRPr")
            base = base or (int(d.get("sz")) / 100 if d is not None and d.get("sz") else None)
            paras.append(Paragraph(runs=[Run(text=" ")], style=Style(font_size=(base or 18) * scale)))
            continue
        first = p.runs[0]
        rpr = first._r.find(f"{{{A}}}rPr")
        spc = int(rpr.get("spc", "0")) / 100 if rpr is not None else 0.0
        font = first.font.name
        st = Style(font_size=(base or 18) * scale, font=font, letter_spacing=spc or None)
        paras.append(Paragraph(runs=runs, style=st))
    if not paras:
        return 0.0
    if bp.get("wrap") == "none":
        width = 10**12
    first_font = next((r.font.name for p in tf.paragraphs for r in p.runs if r.font.name), None)
    base_size = next((r.font.size.pt for p in tf.paragraphs for r in p.runs if r.font.size), 18) * scale
    need = measure.paragraphs_height(
        paras, width, Style(font_size=base_size, font=first_font), default_size=base_size
    )
    return need / height


# --------------------------------------------------------------------------- charts


def _chart_facts(
    it: Item, items: list[Item], bg, theme: Theme, sizes: list[float], contrast: list, nontext: list
) -> None:
    try:
        cs = it.sh.chart._chartSpace
    except Exception:
        return
    back = _backdrop(items, it.z, it.cx, it.cy, bg, theme)
    cfill = _solid(cs.find(f"{{{C}}}spPr"), theme)
    if cfill and cfill[1] > 0.02:
        back = _blend(cfill[0], cfill[1], back)
    for node in cs.iter(f"{{{A}}}defRPr", f"{{{A}}}rPr"):
        if node.get("sz"):
            sizes.append(int(node.get("sz")) / 100)
    for tx in cs.iter(f"{{{C}}}txPr"):  # axis, legend, title and label text with an explicit ink
        host = tx.getparent().tag.split("}")[1]
        if host == "dLbls" or host == "dLbl":
            continue  # a data label sits on its bar or beside it: not judged against the page
        d = tx.find(f".//{{{A}}}defRPr")
        c = _solid(d, theme) if d is not None else None
        if c is not None and d.get("sz"):
            sz = int(d.get("sz")) / 100
            contrast.append(
                (
                    _ratio(_hex(_blend(c[0], c[1], back)), _hex(back)),
                    sz,
                    bool(d.get("b") == "1"),
                    f"chart {host} text",
                )
            )
    for plot in cs.find(f".//{{{C}}}plotArea"):
        tag = plot.tag.split("}")[1]
        if tag in ("pieChart", "doughnutChart", "pie3DChart"):
            continue  # slices are told apart by their neighbours and labels, not by the page
        for ser in plot.iter(f"{{{C}}}ser"):
            name = "".join(ser.xpath("string(c:tx//c:v)")) or "series"
            for sp in [
                ser.find(f"{{{C}}}spPr"),
                *[d.find(f"{{{C}}}spPr") for d in ser.findall(f"{{{C}}}dPt")],
            ]:
                if sp is None:
                    continue
                f = _solid(sp, theme)
                ln = sp.find(f"{{{A}}}ln")
                lc = _solid(ln, theme) if ln is not None else None
                best = 0.0
                for c in (f, lc):
                    if c is not None:
                        best = max(best, _ratio(_hex(_blend(c[0], c[1], back)), _hex(back)))
                if f is not None or lc is not None:
                    nontext.append((best, f"chart series '{name}'"))


# --------------------------------------------------------------------------- slide


def _level_text(ratio: float, size: float, bold: bool) -> int:
    large = size >= 18 or (bold and size >= 14)
    need = 3.0 if large else 4.5
    if ratio >= need:
        return 3
    return 2 if ratio >= 3.0 else 1


def _level_floor(role: str, mn: float, dense: bool) -> int:
    floor, hard = DENSE_BODY if (dense and role == "body") else FLOORS[role]
    if mn >= floor - 0.25:  # px -> pt conversions of the html kit land a hair under a round number
        return 3
    return 1 if mn < hard - 1e-6 else 2


EMPTY_WEAK, EMPTY_FAIL = (
    0.40,
    0.65,
)  # G-05: share of the body with no content in a full-width / full-height band
DECOR_NAME = re.compile(r"^(Eyebrow|Cover art|Background|band\b)", re.I)


BAND_MIN = 0.10  # a gap narrower than this share of the body is a gutter between blocks, not dead space
HERO_PT = 54  # a slide whose largest non-title text is this big is a statement slide: sparse on purpose
SIDE_WEIGHT = 0.5  # empty side columns count half: a tall figure centred on a wide slide is often the design


def _empty(pairs: list[tuple[float, float]], lo: float, hi: float) -> float:
    """Share of ``[lo, hi]`` in gaps between the ``pairs`` (and the ends) at least ``BAND_MIN`` of it wide."""
    gaps, end = [], lo
    for a, b in sorted((max(a, lo), min(b, hi)) for a, b in pairs if min(b, hi) > max(a, lo)):
        if a > end:
            gaps.append(a - end)
        end = max(end, b)
    gaps.append(hi - end)
    span = hi - lo
    return sum(g for g in gaps if g >= BAND_MIN * span) / span


def _largest_pt(it: Item) -> float:
    tf = it.sh.text_frame if getattr(it.sh, "has_text_frame", False) and it.sh.has_text_frame else None
    if tf is None:
        return 0.0
    sizes = [r.font.size.pt for p in tf.paragraphs for r in p.runs if r.font.size and r.text.strip()]
    return max(sizes, default=0.0) * _scale(tf)


def space_facts(items: list[Item], sw: int, sh_: int) -> tuple[int, float, float, float, str] | None:
    """G-05 measured: the body is the area under the title (and eyebrow) and above the footer zone, between the
    title's side margins. A full-width (full-height) band of the body that meets no content box and is at least
    ``BAND_MIN`` of the body high (wide) is dead space; gutters between blocks are not. The empty share is the
    larger of the row share and half the column share (side margins around a figure that fills the height are
    often the design, the judge scores them as chosen space), so a small block floating in the middle (dead bands above and below, or
    on both sides) shows as a large share while a slide whose content spans the body does not. A statement slide
    (text of ``HERO_PT`` or more) is skipped. ``None`` when the slide has no title (a cover, a free-form slide).

    Returns (level, empty share, empty rows, empty columns, fact): level 1 at >= ``EMPTY_FAIL``, 2 at >= ``EMPTY_WEAK``,
    else 3."""
    title = next(
        (
            i
            for i in items
            if getattr(i.sh, "is_placeholder", False)
            and i.sh.placeholder_format.type in (PP_PLACEHOLDER.TITLE, PP_PLACEHOLDER.CENTER_TITLE)
        ),
        None,
    ) or next((i for i in items if i.name == "Title"), None)
    if title is None or title.w <= 0:
        return None
    feet = [
        i
        for i in items
        if i.y > 0.6 * sh_
        and (
            FOOT_NAME.search(i.name)
            or (
                getattr(i.sh, "is_placeholder", False)
                and i.sh.placeholder_format.type
                in (PP_PLACEHOLDER.FOOTER, PP_PLACEHOLDER.SLIDE_NUMBER, PP_PLACEHOLDER.DATE)
            )
        )
    ]
    top = max(
        [title.y + title.h] + [i.y + i.h for i in items if i.name == "Eyebrow" and i.y < title.y + title.h]
    )
    bottom = min([sh_] + [i.y for i in feet])
    left, right = title.x, title.x + title.w
    if bottom - top <= 0.15 * sh_ or right - left <= 0.3 * sw:
        return None
    boxes, hero = [], False
    for i in items:
        if i is title or i in feet or DECOR_NAME.match(i.name):
            continue
        if i.w >= 0.9 * sw and i.h >= 0.8 * sh_:
            continue  # a full-slide background
        x0, y0, x1, y1 = i.x, i.y, i.x + max(i.w, EMU_PT), i.y + max(i.h, EMU_PT)
        if x1 <= left or x0 >= right or y1 <= top or y0 >= bottom:
            continue
        boxes.append((x0, y0, x1, y1))
        hero = hero or _largest_pt(i) >= HERO_PT
    if hero and len(boxes) <= 3:
        return None  # a statement slide (one huge number or line and a caption) is sparse on purpose
    if not boxes:
        return 1, 1.0, 1.0, 1.0, "body empty"
    rows = _empty([(b[1], b[3]) for b in boxes], top, bottom)
    cols = _empty([(b[0], b[2]) for b in boxes], left, right)
    share = max(rows, SIDE_WEIGHT * cols)
    level = 1 if share >= EMPTY_FAIL else 2 if share >= EMPTY_WEAK else 3
    fact = f"empty body {share:.0%} (rows {rows:.0%}, columns {cols:.0%}; weak >= {EMPTY_WEAK:.0%})"
    return level, share, rows, cols, fact


def measure_slide(
    slide, theme: Theme, dense: bool, sw: int, sh_: int, space: bool = True
) -> tuple[dict, str]:
    items: list[Item] = []
    _flatten(slide.shapes, items)
    bg = _slide_bg(slide, theme)
    arrows = sum(1 for i in items if i.sh.shape_type == MSO_SHAPE_TYPE.LINE and _has_arrow(i.sh))
    html_native = (
        sum(1 for i in items if re.fullmatch(r"(Text|Shape) \d+", i.name)) >= 6
    )  # a converted ```html block
    diagram = arrows >= 3 or html_native or any(DIAGRAM_NAME.match(i.name) for i in items)
    role_min: dict[str, tuple[float, str]] = {}
    contrast: list[tuple[float, float, bool, str]] = []  # ratio, size, bold, where
    nontext: list[tuple[float, str]] = []
    chart_sizes: list[float] = []
    defects: list[tuple[int, str]] = []
    heading_min = None

    def note_size(role: str, sz: float, where: str) -> None:
        nonlocal heading_min
        if role == "heading":
            heading_min = sz if heading_min is None else min(heading_min, sz)
        elif role not in role_min or sz < role_min[role][0]:
            role_min[role] = (sz, where)

    for it in items:
        sh = it.sh
        if getattr(sh, "has_chart", False) and sh.has_chart:
            _chart_facts(it, items, bg, theme, chart_sizes, contrast, nontext)
            continue
        if getattr(sh, "has_table", False) and sh.has_table:
            tbl = sh.table
            for row in tbl.rows:
                for cell in row.cells:
                    f = _solid(cell._tc.find(f"{{{A}}}tcPr"), theme)
                    back = _backdrop(items, it.z, it.cx, it.cy, bg, theme)
                    if f and f[1] > 0.02:
                        back = _blend(f[0], f[1], back)
                    sc = _scale(cell.text_frame)
                    for _p, r, sz, col, bold in _runs(cell.text_frame, theme):
                        if sz:
                            note_size("body", sz * sc, f"table '{r.text.strip()[:18]}'")
                        if sz and col:
                            contrast.append(
                                (
                                    _ratio(_hex(_blend(col[0], col[1], back)), _hex(back)),
                                    sz * sc,
                                    bold,
                                    f"table '{r.text.strip()[:18]}'",
                                )
                            )
            continue
        if sh.shape_type == MSO_SHAPE_TYPE.LINE or (
            sh.shape_type == MSO_SHAPE_TYPE.FREEFORM and not sh.has_text_frame
        ):
            c, wd = _line_of(sh, theme)
            if c and wd >= 0.5 and (ARROW_NAME.search(it.name) or _has_arrow(sh)):
                back = _backdrop(items, it.z, it.cx, it.cy, bg, theme)
                nontext.append((_ratio(_hex(_blend(c[0], c[1], back)), _hex(back)), f"arrow '{it.name}'"))
            continue
        has_text = getattr(sh, "has_text_frame", False) and sh.has_text_frame and sh.text_frame.text.strip()
        if MARK_NAME.search(it.name) and not has_text and it.w * it.h > 0:
            f = _fill_rgb(it, theme)
            if (
                "disc" in it.name.lower()
            ):  # a disc holding an icon is its container: the glyph must read on the disc
                glyph = next(
                    (
                        o
                        for o in items
                        if o is not it
                        and o.name.lower().startswith("icon ")
                        and "disc" not in o.name.lower()
                        and abs(o.cx - it.cx) < it.w / 2
                        and abs(o.cy - it.cy) < it.h / 2
                    ),
                    None,
                )
                if glyph is not None and f:
                    g = _fill_rgb(glyph, theme)
                    disc = _blend(f[0], f[1], _backdrop(items, it.z, it.cx, it.cy, bg, theme))
                    if g:
                        nontext.append(
                            (_ratio(_hex(_blend(g[0], g[1], disc)), _hex(disc)), f"icon on '{it.name}'")
                        )
                continue
            c, _wd = _line_of(sh, theme)
            back = _backdrop(items, it.z, it.cx, it.cy, bg, theme)
            best = 0.0
            for col in (f, c):
                if col and col[1] > 0.02:
                    best = max(best, _ratio(_hex(_blend(col[0], col[1], back)), _hex(back)))
            if f or c:
                nontext.append((best, f"swatch '{it.name}'"))
        if not has_text:
            continue
        tf = sh.text_frame
        role = _role(it, tf, diagram)
        back = _own_back(items, it, bg, theme)
        sc = _scale(tf)
        runs = list(_runs(tf, theme))
        top = max((x[2] for x in runs if x[2]), default=0.0)
        for _p, r, sz, col, bold in runs:
            if sz:  # a run well under the biggest one of its shape is that shape's sub-label or gloss
                r_role = "label" if role in ("body", "node") and sz < 0.85 * top else role
                note_size(r_role, sz * sc, f"'{it.name}'")
            if sz and col:
                contrast.append(
                    (
                        _ratio(_hex(_blend(col[0], col[1], back)), _hex(back)),
                        sz * sc,
                        bold,
                        f"'{it.name}' {r.text.strip()[:18]!r}",
                    )
                )
        ov = _frame_overflow(it, tf)
        if re.fullmatch(
            r"Text \d+", it.name
        ):  # an html text run was measured by Chromium: only a gross miss counts
            ov = ov / 1.25 * 1.0 if ov > 1.5 else 0.0
        if ov > 1.3:
            defects.append((1, f"text overflows '{it.name}' (about {ov:.1f}x its height)"))
        elif ov > 1.12:
            defects.append((2, f"text nearly overflows '{it.name}' ({ov:.2f}x its height)"))
        if it.w > 0 and (
            it.x < -EMU_PT * 2
            or it.y < -EMU_PT * 2
            or it.x + it.w > sw + EMU_PT * 2
            or it.y + it.h > sh_ + EMU_PT * 2
        ):
            defects.append((1, f"'{it.name}' extends past the slide edge"))
    # shapes with text that overlap without one holding the other
    texted = [
        it
        for it in items
        if getattr(it.sh, "has_text_frame", False)
        and it.sh.has_text_frame
        and it.sh.text_frame.text.strip()
        and it.w * it.h > 0
    ]
    for i, a in enumerate(texted):
        for b in texted[i + 1 :]:
            ix = min(a.x + a.w, b.x + b.w) - max(a.x, b.x)
            iy = min(a.y + a.h, b.y + b.h) - max(a.y, b.y)
            if ix <= 0 or iy <= 0 or a.contains(b) or b.contains(a):
                continue
            share = ix * iy / min(a.w * a.h, b.w * b.h)
            if share > 0.4:
                defects.append((1, f"'{a.name}' and '{b.name}' overlap ({share:.0%} of the smaller)"))
            elif share > 0.2:
                defects.append((2, f"'{a.name}' and '{b.name}' overlap ({share:.0%} of the smaller)"))
    if chart_sizes:
        role_min["chart"] = (min(chart_sizes), "chart text")
    # ---- levels
    out: dict[str, int] = {}
    facts: list[str] = []
    g06 = [(_level_floor(role, mn, dense), role, mn, where) for role, (mn, where) in role_min.items()]
    for role in ("body", "node", "label", "footnote", "chart"):
        if role in role_min:
            mn, where = role_min[role]
            floor = (DENSE_BODY if dense and role == "body" else FLOORS[role])[0]
            facts.append(f"min {role} {mn:g} pt (floor {floor:g})")
    if g06:
        out["G-06"] = min(g[0] for g in g06)
    g09 = []
    if contrast:
        worst = min(contrast, key=lambda t: t[0] - (3.0 if t[1] >= 18 or (t[2] and t[1] >= 14) else 4.5))
        lv = min(_level_text(r, s, b) for r, s, b, _w in contrast)
        g09.append(lv)
        facts.append(f"min text contrast {worst[0]:.1f}:1 ({worst[3]})")
    if nontext:
        worst_n = min(nontext, key=lambda t: t[0])
        lv = 3 if worst_n[0] >= 3.0 else (2 if worst_n[0] >= 1.5 else 1)
        g09.append(lv)
        facts.append(f"min non-text contrast {worst_n[0]:.1f}:1 ({worst_n[1]})")
    if g09:
        out["G-09"] = min(g09)
    if defects:
        out["G-12"] = min(d[0] for d in defects)
        facts += [d[1] for d in dict.fromkeys(defects)][:3]
    if space and (sp := space_facts(items, sw, sh_)):
        facts.append(sp[4])
        if sp[0] < 3:
            out["G-05"] = sp[
                0
            ]  # only a failure is written: an even spread proves nothing about a cramped slide
    if heading_min is not None:
        facts.insert(0, f"title {heading_min:g} pt")
    return out, "; ".join(facts)


def _has_arrow(sh) -> bool:
    sp = _sppr(sh)
    if sp is None:
        return False
    ln = sp.find(f"{{{A}}}ln")
    if ln is None:
        return False
    for tag in ("headEnd", "tailEnd"):
        e = ln.find(f"{{{A}}}{tag}")
        if e is not None and e.get("type") not in (None, "none"):
            return True
    return False


def measure_deck(
    path: Path,
    dense_ja: bool = False,
    dense_slides: set[int] | None = None,
    sparse_ok: set[int] | None = None,
) -> dict:
    """``{"slides": {"3": {"G-06": 2, ...}}, "facts": {"3": "..."}}`` of a .pptx (slide numbers from 1).

    ``dense_ja`` applies the dense-JA body floor to every slide, ``dense_slides`` to those slide numbers only;
    ``sparse_ok`` slides (framing: cover, section, closing) are not measured for empty space (G-05)."""
    measure.set_tokens(LayoutTokens())
    prs = Presentation(str(path))
    theme = Theme(prs)
    res: dict = {"slides": {}, "facts": {}}
    for i, slide in enumerate(prs.slides, 1):
        levels, facts = measure_slide(
            slide,
            theme,
            dense_ja or i in (dense_slides or ()),
            prs.slide_width,
            prs.slide_height,
            space=i not in (sparse_ok or ()),
        )
        if levels:
            res["slides"][str(i)] = levels
        if facts:
            res["facts"][str(i)] = facts
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("pptx", type=Path)
    ap.add_argument("--deck", help="deck id (names the default output measured-<id>.json)")
    ap.add_argument("--dense-ja", action="store_true", help="dense Japanese business deck: body floor 10 pt")
    ap.add_argument("-o", "--out", type=Path)
    a = ap.parse_args(argv)
    res = measure_deck(a.pptx, a.dense_ja)
    out = a.out or (a.pptx.with_name(f"measured-{a.deck}.json") if a.deck else None)
    text = json.dumps(res, ensure_ascii=False, indent=1)
    if out:
        out.write_text(text + "\n", encoding="utf-8")
    else:
        sys.stdout.write(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
