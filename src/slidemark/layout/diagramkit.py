"""Shared drawing kit of the editorial diagram forms (``@arch`` ``@swimlane`` ``@sequence`` ``@venn``).

What the forms share, as native shapes and every look a token (``diagram.*`` in ``forms6.py``):

- **node anatomy**: a card (the ``node`` class and the role classes) with a bold name and a mono sublabel,
  with an optional type tag (a tiny hairline rectangle with tracked mono capitals) at its top-left;
- **arrow kinds**: ``>`` default, ``=>`` primary (accent), ``~>`` HTTP / API call (link colour), ``-->``
  return / async (dashed); :func:`style_of` maps a kind to colour, dash and width;
- **arrow labels**: mono capitals on a knockout of the slide colour, placed beside a segment of the connector
  and never on a node or another label (:func:`place_label`);
- **legend strip**: one swatch per node role and arrow kind the slide uses (:func:`legend`).

Shape names: ``<Form> ... tag`` for a tag, ``<Form> ... label`` for a label, ``Legend ...`` for the legend.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from ..forms5 import kind_of, split_sub, split_tag  # noqa: F401 (re-exported)
from ..ir import Paragraph, Run, Shape, Style, Text, fast_style
from ..units import EMU_PER_PT
from . import measure
from . import vocab as V
from .grid import Rect

PT = EMU_PER_PT
KINDS = ("flow", "primary", "http", "return")
KIND_LABEL = {
    "flow": "Flow",
    "primary": "Primary flow",
    "http": "HTTP request",
    "return": "Return / async",
}
ROLE_LABEL = {
    "focal": "Focal",
    "store": "Store",
    "external": "External",
    "input": "Input",
    "optional": "Optional",
    "security": "Security",
    "plain": "Node",
}
JA = {
    "Flow": "流れ",
    "Primary flow": "主経路",
    "HTTP request": "HTTP 呼び出し",
    "Return / async": "戻り・非同期",
    "Focal": "重点",
    "Store": "保存",
    "External": "外部",
    "Input": "入力",
    "Optional": "任意",
    "Security": "セキュリティ",
    "Node": "要素",
    "Activation": "処理中",
}
ROLES = ("focal", "store", "external", "input", "optional", "security")


# --------------------------------------------------------------------------- look (tokens resolved)


@dataclass
class Look:
    """The diagram tokens of one slide, resolved; ``k`` scales every size (a diagram that does not fit)."""

    th: Any
    name: float
    sub: float
    tag: float
    label: float
    legend: float
    k: float = 1.0

    @property
    def mono(self) -> str:
        return self.th.diagram_font or self.th.fonts.mono

    @property
    def muted(self) -> str:
        return self.th.diagram_muted

    def scaled(self, k: float) -> Look:
        """A copy at ``k`` x the sizes (names stay >= ``diagram.name.min``, small text >= the theme floor)."""
        th = self.th
        lo = th.min_font_size

        def f(v: float, floor: float) -> float:
            return round(max(v * k, min(v, floor)), 1)

        return Look(
            th,
            f(self.name, th.diagram_name_min),
            f(self.sub, lo),
            f(self.tag, lo),
            f(self.label, lo),
            f(self.legend, lo),
            k,
        )


def look(c, slide=None) -> Look:
    """The diagram sizes of the slide: ``size=N`` pins the names; else the tokens."""
    th = c.theme
    from .. import forms

    pin = forms.num(slide.attrs, "size") if slide is not None else None
    name = float(pin) if pin else th.diagram_name_size
    return Look(
        th, name, th.diagram_sub_size, th.diagram_tag_size, th.diagram_label_size, th.diagram_legend_size
    )


def known(th, name: str | None, fallback: str) -> str:
    """``name`` when it is a theme colour or a hex colour, else ``fallback`` (e.g. no ``link`` colour)."""
    if name and (name in th.colors or name.startswith("#")):
        return name
    return fallback


def style_of(K: Look, kind: str, focal: bool = False) -> tuple[str, str | None, float]:
    """``(colour, dash, width pt)`` of an arrow kind; ``focal`` (a ``{.focal}`` arrow) takes the primary
    colour and keeps the kind's own dash (a focal return stays dashed)."""
    th = K.th
    base = th.diagram_arrow or th.render.connector_color
    width = V._pt(V._emu(th.diagram_arrow_w)) if th.diagram_arrow_w else th.render.connector_width
    primary = known(th, th.diagram_arrow_primary, "accent")
    if kind == "primary":
        return primary, None, max(width, 1.25)
    if kind == "http":
        col, dash = known(th, th.diagram_arrow_http, "primary"), None
    elif kind == "return":
        col, dash = th.diagram_arrow_return or base, th.diagram_return_dash
    else:
        col, dash = base, None
    if focal:
        return primary, dash, max(width, 1.25)
    return col, dash, width


# --------------------------------------------------------------------------- text


def hairline(c) -> float:
    """The width (pt) of a hairline: tag outlines, rules, activation bars, legend swatches."""
    return V._pt(V._emu(c.theme.diagram_hairline))


def has_wide(text: str) -> bool:
    return measure.has_cjk(text)


def mono_w(text: str, size: float, track_em: float = 0.0, upper: bool = True) -> int:
    """Width (EMU) of ``text`` set in the mono face at ``size`` pt with ``track_em`` tracking, on one line."""
    t = text.upper() if upper else text
    if has_wide(t):
        em = sum(1.0 if measure.is_cjk(ch) else 0.6 for ch in t)
    else:
        em = 0.6 * len(t)
    return round((em + track_em * len(t)) * size * PT)


def sans_w(text: str, size: float, bold: bool = False) -> int:
    return round(measure.text_em(text, bold=bold) * size * PT)


def small_style(c, K: Look, size: float, track: float, color: str | None = None, **kw) -> Style:
    """Mono capitals (tags, arrow labels, captions); CJK text switches to the body face, no capitals."""
    return fast_style(
        font=K.mono,
        font_size=size,
        letter_spacing=round(track * size, 2),
        text_transform="caps",
        color=color or K.muted,
        **kw,
    )


def small_para(c, K: Look, text: str, size: float, track: float, color: str | None = None) -> Paragraph:
    """One paragraph of small text: mono capitals when Latin, the body face (no tracking) when CJK."""
    if has_wide(text):
        st = fast_style(font_size=round(size + 1.5, 1), color=color or K.muted)
    else:
        st = small_style(c, K, size, track, color)
    return Paragraph(runs=[Run(text=text)], style=st)


def small_w(K: Look, text: str, size: float, track: float) -> int:
    """Width (EMU) a small-text box needs: the wider of the mono face and the fallback sans capitals."""
    if has_wide(text):
        return sans_w(text, size + 1.5)
    sans = round((measure.text_em(text.upper()) + track * len(text)) * size * PT)
    return max(mono_w(text, size, track), sans)


def emit_text(
    c,
    name: str,
    paras: list[Paragraph],
    rect: Rect,
    st: Style,
    classes: list[str] | None = None,
    nowrap: bool = False,
) -> None:
    attrs: dict[str, Any] = {"shape_name": name}
    if nowrap:
        attrs["nowrap"] = True
    c.emit(Text(role="body", paragraphs=paras, classes=classes or [], attrs=attrs), rect, st)


def caption(
    c, K: Look, name: str, text: str, x: int, y: int, h: int, w: int | None = None, align: str = "left"
) -> int:
    """A mono capitals caption at ``(x, y)`` (height ``h``); returns its width (EMU)."""
    size, tr = K.label, c.theme.diagram_label_track
    tw = small_w(K, text, size, tr) + round(4 * PT)
    ww = w if w is not None else tw
    st = V._text_style(c, size, align=align, valign="middle", padding="0pt")
    emit_text(c, name, [small_para(c, K, text, size, tr)], Rect(x, y, ww, h), st, nowrap=True)
    return tw


# --------------------------------------------------------------------------- node anatomy


def role_style(c, classes: list[str], base: str | None = "node"):
    """The merged class styles of ``node`` + the role classes (``None`` base = the roles only)."""
    out = fast_style()
    for n in ([base] if base else []) + list(classes):
        if n in c.theme.classes:
            out = out.merged(c.theme.classes[n])
    return out


def tag_size(K: Look, tag: str) -> tuple[int, int]:
    """(width, height) EMU of a type tag rectangle."""
    w = small_w(K, tag, K.tag, K.th.diagram_tag_track) + round(8 * PT)
    return w, round(K.tag * 1.55 * PT)


def node_paras(
    c, K: Look, name: str, sub: str | list[str] = "", name_pt: float | None = None
) -> list[Paragraph]:
    """The text of a node: the bold name, then the sublabel(s) in mono."""
    nm = name_pt or K.name
    out = [Paragraph(runs=[Run(text=name)], style=fast_style(font_size=nm, bold=True))]
    for s in [sub] if isinstance(sub, str) else sub:
        if s.strip():
            if has_wide(s):
                st = fast_style(font_size=round(K.sub + 1.5, 1), color=K.muted)
            else:
                st = fast_style(font=K.mono, font_size=K.sub, color=K.muted)
            out.append(Paragraph(runs=[Run(text=s)], style=st))
    return out


def node_style(c, K: Look, classes: list[str], tagged: bool, tag_h: int) -> Style:
    """Style of a node card: the ``node`` class and the roles, text centred below the tag."""
    pad = V._emu(c.theme.diagram_node_pad)
    top = pad if not tagged else tag_h + round(10 * PT)
    st = V._text_style(c, K.name, align="center", valign="middle")
    st = st.merged(role_style(c, classes))
    return st.merged(
        fast_style(
            font_size=K.name,
            padding_left=f"{pad / PT:.1f}pt",
            padding_right=f"{pad / PT:.1f}pt",
            padding_top=f"{top / PT:.1f}pt" if tagged else f"{pad * 0.6 / PT:.1f}pt",
            padding_bottom=f"{pad * 0.6 / PT:.1f}pt",
        )
    )


def node_need(
    c, K: Look, paras: list[Paragraph], w: int, tagged: bool, tag_h: int, classes: list[str]
) -> int:
    st = node_style(c, K, classes, tagged, tag_h)
    return round(V._need(c, paras, w, st))


def node_width(c, K: Look, name: str, sub: str | list[str], tag: str, one_line: bool = True) -> int:
    """Natural width (EMU) of a node: the widest of name, sublabel and tag, plus the padding."""
    pad = V._emu(c.theme.diagram_node_pad)
    subs = [sub] if isinstance(sub, str) else sub
    parts = [sans_w(name, K.name, True)]
    parts += [
        mono_w(s, K.sub, 0, upper=False) if not has_wide(s) else sans_w(s, K.sub + 1.5) for s in subs if s
    ]
    if tag:
        parts.append(tag_size(K, tag)[0] + round(8 * PT))
    return max(parts) + 2 * pad + round(4 * PT)


def node(
    c,
    K: Look,
    shape_name: str,
    tag_name: str,
    rect: Rect,
    paras: list[Paragraph],
    tag: str,
    classes: list[str],
    emit_classes: list[str] | None = None,
    extra: Style | None = None,
) -> None:
    """Emit one node card (name + sublabel) and, when it has one, its tag at the top-left inside it."""
    tw, th_ = tag_size(K, tag) if tag else (0, 0)
    st = node_style(c, K, classes, bool(tag), th_)
    if extra is not None:
        st = st.merged(extra)
    emit_text(c, shape_name, paras, rect, st, emit_classes if emit_classes is not None else [*classes])
    if tag:
        role = role_style(c, classes, None)
        accent = role.line if role.line and role.line not in ("muted", "border") else None
        col = accent or K.muted
        line = accent or c.theme.diagram_tag_line
        pad = round(7 * PT)
        c.emit(
            Text(
                role="body",
                paragraphs=[small_para(c, K, tag, K.tag, c.theme.diagram_tag_track, col)],
                attrs={"shape_name": tag_name, "nowrap": True},
            ),
            Rect(rect.x + pad, rect.y + round(6 * PT), tw, th_),
            V._text_style(
                c,
                K.tag,
                align="center",
                valign="middle",
                padding="0pt",
                line=line,
                line_width=hairline(c),
                radius=V._pt(V._emu(c.theme.diagram_tag_radius)),
                fill="surface",
            ),
        )


# --------------------------------------------------------------------------- connectors


def polyline(pl) -> list[tuple[float, float]]:
    """The corner points of a placed connector (straight or elbow), start to end."""
    at = pl.element.attrs
    sx, ex = (pl.x + pl.w, pl.x) if at.get("flip_h") else (pl.x, pl.x + pl.w)
    sy, ey = (pl.y + pl.h, pl.y) if at.get("flip_v") else (pl.y, pl.y + pl.h)
    if not at.get("elbow"):
        return [(sx, sy), (ex, ey)]
    adj = float(at.get("adj", 0.5))
    if at.get("route") == "h":
        mx = sx + adj * (ex - sx)
        return [(sx, sy), (mx, sy), (mx, ey), (ex, ey)]
    my = sy + adj * (ey - sy)
    return [(sx, sy), (sx, my), (ex, my), (ex, ey)]


def restyle(pl, color: str, dash: str | None, width: float) -> None:
    """Give a placed connector the colour, dash and width of its arrow kind."""
    kw: dict[str, Any] = {"line": color, "line_width": width}
    if dash and dash != "solid":
        kw["line_dash"] = dash
    pl.style = pl.style.merged(fast_style(**kw))


def _hit(a: Rect, b: Rect, m: int = 0) -> bool:
    return not (a.right + m <= b.x or b.right + m <= a.x or a.bottom + m <= b.y or b.bottom + m <= a.y)


def place_label(
    poly: list[tuple[float, float]],
    w: int,
    h: int,
    obstacles: list[Rect],
    bounds: Rect | None = None,
    gap: int = round(4 * PT),
) -> tuple[Rect, bool]:
    """Where an arrow label of ``w`` x ``h`` goes: beside a segment of ``poly`` with ``gap`` air from the
    stroke (above / below a horizontal segment, right / left of a vertical one), clear of ``obstacles``.
    Returns ``(rect, clear)``; ``clear`` is False when only a knockout on the stroke was left."""
    segs = []
    for (x0, y0), (x1, y1) in zip(poly, poly[1:], strict=False):
        length = abs(x1 - x0) + abs(y1 - y0)
        if length > 0:
            segs.append((length, x0, y0, x1, y1))
    segs.sort(key=lambda s: -s[0])
    cands: list[Rect] = []
    horiz = [s for s in segs if s[2] == s[4]]
    vert = [s for s in segs if s[1] == s[3]]
    for length, x0, y0, x1, _y1 in horiz:
        if length + 1 < w + 2 * gap and len(horiz) > 1 and length < 0.5 * w:
            continue
        lo, hi = min(x0, x1), max(x0, x1)
        for t in (0.5, 0.3, 0.7, 0.15, 0.85):
            cx = lo + t * (hi - lo)
            cx = min(max(cx, lo + w / 2), max(hi - w / 2, lo + w / 2))
            for dy in (-(h + gap), gap):
                cands.append(Rect(round(cx - w / 2), round(y0 + dy), w, h))
    for _length, x0, y0, _x1, y1 in vert:
        lo, hi = min(y0, y1), max(y0, y1)
        for t in (0.5, 0.3, 0.7, 0.15, 0.85):
            cy = lo + t * (hi - lo)
            for dx in (gap, -(gap + w)):
                cands.append(Rect(round(x0 + dx), round(cy - h / 2), w, h))
    for r in cands:
        if bounds is not None and (
            r.x < bounds.x or r.right > bounds.right or r.y < bounds.y or r.bottom > bounds.bottom
        ):
            continue
        if any(_hit(r, o, round(1 * PT)) for o in obstacles):
            continue
        return r, True
    if segs:
        length, x0, y0, x1, y1 = segs[0]
        return Rect(round((x0 + x1) / 2 - w / 2), round((y0 + y1) / 2 - h / 2), w, h), False
    return Rect(0, 0, w, h), False


def edge_label(
    c,
    K: Look,
    name: str,
    poly: list[tuple[float, float]],
    text: str,
    color: str | None,
    obstacles: list[Rect],
    bounds: Rect | None = None,
) -> Rect:
    """Emit an arrow label (mono capitals on a knockout of the slide colour); returns its rect."""
    size, tr = K.label, c.theme.diagram_label_track
    w = small_w(K, text, size, tr) + round(8 * PT)
    h = round(size * 1.6 * PT)
    rect, _clear = place_label(poly, w, h, obstacles, bounds)
    st = V._text_style(c, size, align="center", valign="middle", padding="0pt", fill="bg")
    emit_text(c, name, [small_para(c, K, text, size, tr, color or K.muted)], rect, st, nowrap=True)
    return rect


# --------------------------------------------------------------------------- legend


def legend_entries(
    c, roles: list[str], kinds: list[str], plain: bool, lang: str | None, act: bool = False
) -> list[tuple[str, str]]:
    """``(key, label)`` of the legend: the plain node, the roles, then the arrow kinds actually used."""
    custom: dict[str, str] = {}
    for part in re.split(r"[,;]", c.theme.diagram_legend_text or ""):
        if "=" in part:
            k, v = part.split("=", 1)
            custom[k.strip().lower()] = v.strip()
    ja = (lang or "").lower().startswith("ja")

    def lab(key: str, base: str) -> str:
        return custom.get(key) or (JA.get(base, base) if ja else base)

    out: list[tuple[str, str]] = []
    if plain:
        out.append(("plain", lab("plain", ROLE_LABEL["plain"])))
    out += [(r, lab(r, ROLE_LABEL[r])) for r in ROLES if r in roles]
    out += [(k, lab(k, KIND_LABEL[k])) for k in KINDS if k in kinds]
    if act:
        out.append(("act", lab("act", "Activation")))
    return out


def wants_legend(c, roles: list[str], kinds: list[str], slide=None) -> bool:
    """``diagram.legend`` (auto: two or more roles / kinds) unless the slide says ``legend=on|off``."""
    mode = c.theme.diagram_legend
    own = str(slide.attrs.get("legend", "")).lower() if slide is not None else ""
    if own in ("on", "off", "auto"):
        mode = own
    if mode == "off":
        return False
    if mode == "on":
        return bool(roles or kinds)
    return len(set(roles)) + len(set(kinds)) >= 2


def legend_width(K: Look, entries: list[tuple[str, str]]) -> int:
    """The width one row of legend entries needs."""
    sw = round(24 * PT)
    return sum(sw + round(6 * PT) + sans_w(lb, K.legend) + round(26 * PT) for _k, lb in entries)


def legend_height(K: Look) -> int:
    return round((K.label * 1.6 + K.legend * 1.9) * PT) + round(44 * PT)


def legend(c, K: Look, x: int, y: int, w: int, entries: list[tuple[str, str]]) -> int:
    """The legend strip at ``(x, y)`` over width ``w``: a hairline, the ``LEGEND`` caption, then one swatch
    and label per entry. Returns the height used."""
    th = c.theme
    y += round(10 * PT)  # air between the diagram and the strip
    c.emit(
        Shape(shape="line", attrs={"head": "none", "shape_name": "Legend rule"}),
        Rect(x, y, w, 0),
        fast_style(line=th.diagram_tag_line, line_width=hairline(c)),
    )
    cap_h = round(K.label * 1.6 * PT)
    caption(c, K, "Legend caption", "Legend", x, y + round(7 * PT), cap_h)
    row_y = y + round(7 * PT) + cap_h + round(5 * PT)
    row_h = round(K.legend * 1.9 * PT)
    sw_w, sw_h = round(24 * PT), round(11 * PT)
    cx = x
    for key, label in entries:
        tw = sans_w(label, K.legend) + round(10 * PT)
        need = sw_w + round(6 * PT) + tw + round(16 * PT)
        if cx + need > x + w + round(20 * PT) and cx > x:
            cx, row_y = x, row_y + row_h
        mid = row_y + row_h // 2
        if key in KINDS:
            color, dash, width = style_of(K, key)
            c.emit(
                Shape(shape="line", attrs={"head": "arrow", "shape_name": f"Legend {key} swatch"}),
                Rect(cx, mid, sw_w, 0),
                fast_style(
                    line=color, line_width=width, **({"line_dash": dash} if dash and dash != "solid" else {})
                ),
            )
        elif key == "act":
            c.emit(
                Shape(shape="rect", attrs={"shape_name": "Legend act swatch"}),
                Rect(
                    cx + round(7 * PT), mid - sw_h // 2 - round(1 * PT), round(7 * PT), sw_h + round(2 * PT)
                ),
                fast_style(fill=th.diagram_act_fill, line=th.diagram_act_line, line_width=hairline(c)),
            )
        else:
            st = role_style(c, [] if key == "plain" else [key])
            c.emit(
                Shape(shape="rect", attrs={"shape_name": f"Legend {key} swatch"}),
                Rect(cx, mid - sw_h // 2, sw_w - round(6 * PT), sw_h),
                fast_style(
                    fill=st.fill or "surface",
                    line=st.line or th.render.connector_color,
                    line_width=hairline(c),
                    radius=2.0,
                    **({"line_dash": st.line_dash} if st.line_dash else {}),
                ),
            )
        lst = V._text_style(c, K.legend, color="fg", align="left", valign="middle", padding="0pt")
        emit_text(
            c,
            f"Legend {key} label",
            [Paragraph(runs=[Run(text=label)], style=fast_style(font_size=K.legend, color=K.muted))],
            Rect(cx + sw_w + round(4 * PT), row_y, tw, row_h),
            lst,
            nowrap=True,
        )
        cx += need
    return row_y + row_h - y + round(10 * PT)


def centred(body: Rect, w: int, h: int, top_share: float = 0.5) -> tuple[int, int]:
    """``(x, y)`` of a ``w`` x ``h`` block centred in ``body`` (``top_share`` of the free height above)."""
    return body.x + max(body.w - w, 0) // 2, body.y + round(max(body.h - h, 0) * top_share)
