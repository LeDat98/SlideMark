"""Paragraphs and runs -> DrawingML text, with native bullets, fonts (latin + ea) and hyperlinks."""

from __future__ import annotations

import uuid

from lxml import etree
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Pt

from ..ir import Paragraph, Run, Style
from ..layout import measure
from ..layout.css import insets, transform_text
from ..theme import Theme
from .util import RenderCtx, hex6, rgb

_RPR_ORDER = [
    "ln",
    "noFill",
    "solidFill",
    "gradFill",
    "blipFill",
    "pattFill",
    "grpFill",
    "effectLst",
    "effectDag",
    "highlight",
    "uLnTx",
    "uLn",
    "uFillTx",
    "uFill",
    "latin",
    "ea",
    "cs",
    "sym",
    "hlinkClick",
    "hlinkMouseOver",
    "rtl",
    "extLst",
]
_ALIGN = {
    "left": PP_ALIGN.LEFT,
    "center": PP_ALIGN.CENTER,
    "right": PP_ALIGN.RIGHT,
    "justify": PP_ALIGN.JUSTIFY,
}
_ANCHOR = {"top": MSO_ANCHOR.TOP, "middle": MSO_ANCHOR.MIDDLE, "bottom": MSO_ANCHOR.BOTTOM}
_LANG = {
    "ja": "ja-JP",
    "vi": "vi-VN",
    "en": "en-US",
    "zh": "zh-CN",
    "ko": "ko-KR",
    "fr": "fr-FR",
    "de": "de-DE",
}
_BADGE_PAD = "\u3000"  # full-width space: renders flush inside the highlight (Latin spaces leave a gap)
_BULLETS = ["•", "–", "•", "–"]
_NUMBERING = ["arabicPeriod", "alphaLcParenR", "romanLcPeriod", "arabicPeriod"]


def insert_rpr_child(rpr, child) -> None:
    """Insert ``child`` into an rPr honoring the schema sequence."""
    name = etree.QName(child).localname
    idx = _RPR_ORDER.index(name)
    for existing in list(rpr):
        en = etree.QName(existing).localname
        if en in _RPR_ORDER and _RPR_ORDER.index(en) > idx:
            existing.addprevious(child)
            return
    rpr.append(child)


def _lang_for(text: str, deck_lang: str | None) -> str:
    if deck_lang:
        return _LANG.get(deck_lang.lower().split("-")[0], deck_lang)
    for ch in text:
        o = ord(ch)
        if 0x3040 <= o <= 0x30FF:
            return "ja-JP"
        if 0xAC00 <= o <= 0xD7AF:
            return "ko-KR"
        if 0x4E00 <= o <= 0x9FFF:
            return "ja-JP"
    return "en-US"


def _contrast(hex_color: str, theme: Theme | None = None) -> str:
    """``render.ink_dark`` or ``render.ink_light``, whichever reads better on ``hex_color`` ('RRGGBB')."""
    tok = (theme or Theme(name="none")).render
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    return tok.ink_dark if 0.299 * r + 0.587 * g + 0.114 * b > 160 else tok.ink_light


def _format_run(
    rc: RenderCtx, r, run: Run, style: Style, size_pt: float, text: str, scale: float = 1.0
) -> None:
    theme = rc.theme
    f = r.font
    f.size = Pt(size_pt)
    bold = bool(run.bold or style.bold or run.highlight)
    italic = bool(run.italic or style.italic)
    f.bold = True if bold else None
    f.italic = True if italic else None
    if run.underline or style.underline:
        f.underline = True
    color = run.color or style.color
    if run.highlight and not run.color:  # badge: readable text on the highlight
        color = _contrast(hex6(theme, run.highlight, theme.render.highlight), theme)
    f.color.rgb = rgb(theme, color, "fg")
    rpr = r._r.get_or_add_rPr()
    if style.opacity is not None and 0 <= style.opacity < 1 and not style.fill:
        clr = rpr.find(qn("a:solidFill")).find(qn("a:srgbClr"))  # CSS opacity on text without a fill
        etree.SubElement(clr, qn("a:alpha")).set("val", str(round(style.opacity * 100000)))
    if run.strike or style.strike:
        rpr.set("strike", "sngStrike")
    if style.letter_spacing:
        rpr.set("spc", str(round(style.letter_spacing * scale * 100)))  # 1/100 pt
    if run.sup:
        rpr.set("baseline", "30000")
    elif run.sub:
        rpr.set("baseline", "-25000")
    lang = _lang_for(text, rc.deck.lang)
    rpr.set("lang", lang)
    rpr.set("altLang", "en-US")
    if run.highlight:
        hl = etree.SubElement(rpr, qn("a:highlight"))
        etree.SubElement(hl, qn("a:srgbClr")).set("val", hex6(theme, run.highlight, theme.render.highlight))
        rpr.remove(hl)
        insert_rpr_child(rpr, hl)
    latin = theme.fonts.mono if run.code else (style.font or theme.fonts.body)
    ea = style.font_ea or theme.fonts.ea
    for tag, face in (("a:latin", latin), ("a:ea", ea)):
        el = etree.Element(qn(tag))
        el.set("typeface", face)
        insert_rpr_child(rpr, el)
    if run.link:
        if run.link.startswith("#"):
            rc.links.append((r._r, rpr, run.link[1:], rc.slide_index))
        else:
            r.hyperlink.address = run.link


def _set_bullet(para, p: Paragraph, size_pt: float) -> None:
    pPr = para._p.get_or_add_pPr()
    pPr.set("eaLnBrk", "1")  # kinsoku line breaking, no hanging punctuation: matches layout.measure
    pPr.set("hangingPunct", "0")
    if p.marker:
        marL, indent = measure.list_indent(size_pt, p.level)
        pPr.set("marL", str(marL))
        pPr.set("indent", str(indent))
        lvl = min(p.level, 3)
        if p.marker == "bullet":
            bf = etree.SubElement(pPr, qn("a:buFont"))
            bf.set("typeface", "Arial")
            etree.SubElement(pPr, qn("a:buChar")).set("char", _BULLETS[lvl])
        else:
            etree.SubElement(pPr, qn("a:buFont")).set("typeface", "+mj-lt")
            etree.SubElement(pPr, qn("a:buAutoNum")).set("type", _NUMBERING[lvl])
    else:
        pPr.set("marL", "0")
        pPr.set("indent", "0")
        etree.SubElement(pPr, qn("a:buNone"))


def fill_text(
    rc: RenderCtx,
    tf,
    paragraphs: list[Paragraph],
    style: Style,
    scale: float = 1.0,
    *,
    para_gap: bool = True,
    field: str | None = None,
    inset: int | None = None,
    gap_em: float | None = None,
) -> None:
    """Write ``paragraphs`` into text frame ``tf`` using the (already merged) ``style``.

    ``gap_em`` is the space before every paragraph but the first, x font size (default ``measure.para_gap()``;
    the layout passes a larger value for roomy cards, as ``attrs["para_gap"]`` of the text).
    """
    gap = measure.para_gap() if gap_em is None else gap_em
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    if inset is not None:
        pl = pt = pr = pb = inset
    else:  # padding + per-side padding_* + per-side border widths (CSS box model)
        pl, pt, pr, pb = insets(style)
    tf.margin_left, tf.margin_top, tf.margin_right, tf.margin_bottom = (Emu(pl), Emu(pt), Emu(pr), Emu(pb))
    tf.vertical_anchor = _ANCHOR.get(style.valign or "top", MSO_ANCHOR.TOP)
    paras = paragraphs or [Paragraph()]
    for i, p in enumerate(paras):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        pst = style.merged(p.style)
        size = (pst.font_size or 18) * scale
        para.alignment = _ALIGN.get(pst.align or "left", PP_ALIGN.LEFT)
        if pst.line_spacing:
            para.line_spacing = pst.line_spacing
        para.space_before = Pt(size * gap) if (i > 0 and para_gap) else Pt(0)
        para.space_after = Pt(0)
        _set_bullet(para, p, size)
        first_text = ""
        for run in p.runs:
            segs = run.text.replace("\r", "").replace("\v", "\n").split("\n")
            for k, seg in enumerate(segs):
                if k > 0:
                    para.add_line_break()
                if seg == "" and len(segs) > 1:
                    continue
                seg = transform_text(seg, pst.text_transform)
                r = para.add_run()
                # badge: padding keeps bold CJK glyphs inside the highlight (LibreOffice clips them otherwise)
                pad = _BADGE_PAD if run.highlight and measure.has_cjk(seg) else ""
                r.text = f"{pad}{seg}{pad}"
                _format_run(rc, r, run, pst, size, seg, scale)
                first_text = first_text or seg
                if field == "slide_number":
                    fld = r._r
                    fld.tag = qn("a:fld")
                    fld.set("id", "{" + str(uuid.uuid4()).upper() + "}")
                    fld.set("type", "slidenum")
        end = etree.SubElement(para._p, qn("a:endParaRPr"))
        end.set("lang", _lang_for(first_text, rc.deck.lang))
        end.set("sz", str(round(size * 100)))
