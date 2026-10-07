"""``kpi.rule=<color>``: a divider rule between the number and the caption of every ``.kpi`` card.

The layout stacks the number and the caption in ONE text frame. With the token on, a finished layout is
rewritten: that frame becomes two text boxes (``KPI value``, ``KPI caption``) with a thin ``rule`` shape
between them; the group keeps the vertical centre of the old frame. The importer folds the two boxes
back into one ``.kpi`` block and ignores the rule (``rule`` is a decor name). Never raises: anything
unexpected keeps the original frame.
"""

from __future__ import annotations

from ..ir import Container, Placed, Shape, Style, Text
from ..theme import Theme
from ..units import EMU_PER_PT, to_emu
from . import measure

VALUE, CAPTION, RULE = "KPI value", "KPI caption", "rule"


def _inside(card: Placed, p: Placed) -> bool:
    return (
        p.x >= card.x - 2
        and p.y >= card.y - 2
        and p.x + p.w <= card.x + card.w + 2
        and p.y + p.h <= card.y + card.h + 2
    )


def _height(p: Placed, paras: list, gap) -> int:
    pad = 0
    if p.style.padding is not None:
        try:
            pad = to_emu(p.style.padding)
        except ValueError:
            pad = 0
    need = measure.paragraphs_height(paras, p.w - 2 * pad, p.style, p.font_scale, gap=gap)
    return round(need) + 2 * pad


def expand_kpi_rule(out: list[Placed], theme: Theme, gap_em: float) -> list[Placed]:
    """``out`` with every ``.kpi`` card's text frame split around a rule (no token = ``out`` unchanged)."""
    if not theme.kpi_rule:
        return out
    try:
        return _expand(out, theme, gap_em)
    except Exception:  # never raise on bad input
        return out


def _expand(out: list[Placed], theme: Theme, gap_em: float) -> list[Placed]:
    found: list[tuple[Placed, Placed, int, int]] = []  # (card, text frame, value height, caption height)
    for card in (p for p in out if isinstance(p.element, Container) and "kpi" in p.element.classes):
        texts = [
            p
            for p in out
            if p is not card
            and isinstance(p.element, Text)
            and p.element.role == "body"
            and len(p.element.paragraphs) >= 2
            and _inside(card, p)
        ]
        if len(texts) == 1:
            m = texts[0]
            paras, gap = list(m.element.paragraphs), measure.element_gap(m.element)
            found.append((card, m, _height(m, paras[:1], gap), _height(m, paras[1:], gap)))
    if not found:
        return out
    rows: dict[tuple[int, int], tuple[int, int]] = {}  # cards of one row share the rule's height
    for card, _m, hv, hc in found:
        old = rows.get((card.y, card.h), (0, 0))
        rows[(card.y, card.h)] = (max(old[0], hv), max(old[1], hc))
    swap = {id(m): _split(m, card, theme, gap_em, *rows[(card.y, card.h)]) for card, m, _hv, _hc in found}
    res: list[Placed] = []
    for p in out:
        res.extend(swap.get(id(p), [p]))
    return res


def _split(
    m: Placed, card: Placed, theme: Theme, gap_em: float, h_value: int, h_caption: int
) -> list[Placed]:
    paras = list(m.element.paragraphs)
    value, caption = paras[:1], paras[1:]
    rule_h = max(round(_pt(theme.kpi_rule_h) * EMU_PER_PT), 1)
    first = caption[0].style
    cap_pt = (first.font_size if first and first.font_size else 12) * m.font_scale
    gap = round(gap_em * cap_pt * EMU_PER_PT)
    total = h_value + h_caption + rule_h + 2 * gap
    if total > m.h:  # a tight card: the air around the rule gives way first
        gap = max((m.h - h_value - h_caption - rule_h) // 2, 0)
        total = h_value + h_caption + rule_h + 2 * gap
    top = m.y + max((m.h - total) // 2, 0)
    attrs = {k: v for k, v in m.element.attrs.items() if k != "para_gap"}
    el_value = m.element.model_copy(update={"paragraphs": value, "attrs": {**attrs, "shape_name": VALUE}})
    el_caption = m.element.model_copy(
        update={"paragraphs": caption, "attrs": {**m.element.attrs, "shape_name": CAPTION}}
    )
    y_rule = top + h_value + gap
    y_cap = y_rule + rule_h + gap
    rw = _rule_w(theme, m.w)
    rule = Placed(
        element=Shape(shape="rect", attrs={"shape_name": RULE}),
        x=m.x + (m.w - rw) // 2,
        y=y_rule,
        w=rw,
        h=rule_h,
        style=Style(fill=theme.kpi_rule, line=None),
    )
    value_box = m.model_copy(
        update={"element": el_value, "y": top, "h": h_value, "style": m.style.merged(Style(valign="bottom"))}
    )
    caption_box = m.model_copy(
        update={
            "element": el_caption,
            "y": y_cap,
            "h": max(m.y + m.h - y_cap, h_caption),
            "style": m.style.merged(Style(valign="top")),
        }
    )
    return [value_box, rule, caption_box]


def _pt(value) -> float:
    return to_emu(value) / EMU_PER_PT


def _rule_w(theme: Theme, width: int) -> int:
    try:
        w = to_emu(theme.kpi_rule_w, width)
    except (ValueError, TypeError):
        w = width
    return max(min(w, width), 1)


__all__ = ["expand_kpi_rule", "VALUE", "CAPTION", "RULE"]
