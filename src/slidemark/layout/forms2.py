"""Composition vocabulary, part 2 (DL3b lane K): ``@iconlist`` ``@quote`` ``@split`` ``@proscons``
``@progress`` ``@harvey`` ``@heatmap`` ``@pins``.

Same pattern as ``@steps`` / ``@rows`` / ``@items``: one ``@word`` slide directive with secondary attributes
(``forms2.py`` lists them), every look a ``<word>.*`` token, a composer that works on a copy of the slide so
the parsed Deck stays as written, and named shapes (``Iconlist N``, ``Quote text``, ``Progress N fill``,
``Harvey r,c q2``, ``Pin N`` ...) that the importer (``importer/forms2.py``) folds back into the same words.

Entry points (called from ``engine._layout``, one line each):

- ``prepare``  a copy of the slide for forms that only rewrite content (``@quote`` merges the ``>`` blocks
  into one text, ``@heatmap`` fills the cells of a table);
- ``split_layout``  ``@split``: the text side is laid out by the ordinary engine on a virtual slide of its own
  width, the image (or colour block) is placed beside it;
- ``compose``  the body shapes of the other forms (``None`` = not composable here: the slide is laid out as
  an ordinary one and a diagnostic says why).

Nothing visual is decided here: sizes grow from the theme body size up to ``layout.grow_max``, colors come
from tokens (``iconlist.icon.color`` ...), the slide attributes (``size= fill=``) or the theme palette.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .. import forms2 as F
from .. import icons
from ..ir import (
    Cell,
    Container,
    Deck,
    Diagnostic,
    Image,
    Paragraph,
    Placed,
    Run,
    Shape,
    Slide,
    Style,
    Table,
    Text,
    fast_style,
)
from ..units import EMU_PER_PT, slide_size, to_emu
from . import css, icondisc, measure
from .grid import Rect

_STEP = 0.5  # pt step of the size search


def _E():  # the engine imports this module: take its helpers lazily
    from . import engine

    return engine


# --------------------------------------------------------------------------- shared helpers


def _bad(ctx, key: str, raw: Any) -> None:
    ctx.diag(
        "bad-attr", f"{key}={raw}: not a usable value", f"{key} takes {F.VALUES.get(key, 'a valid value')}"
    )


def _paint(ctx, raw: Any, default: str | None, what: str) -> str | None:
    """A color for a Style: theme name or ``#RRGGBB``. ``None`` raw = ``default``; ``none`` = no paint."""
    if raw is None:
        return default
    v = str(raw).strip()
    if v.lower() in ("none", "off", "null"):
        return None
    if v in ctx.theme.colors:
        return v
    from ..parser.css import parse_color

    got = parse_color(v, set(ctx.theme.colors))
    if got is None:
        ctx.diag(
            "bad-attr",
            f"{what}={v}: not a color",
            "use a theme color name (primary), #RRGGBB or a CSS color name",
        )
        return default
    return got


def _parse_size(raw: Any) -> float | None:
    """A font size in pt from ``size=24`` / ``24pt``, else ``None``."""
    try:
        v = float(str(raw).strip().lower().removesuffix("pt"))
    except ValueError:
        return None
    return v if v > 0 else None


def _attr_size(ctx, slide: Slide) -> float | None:
    """``size=`` of the ``@`` line in pt (a bad value is a diagnostic: the automatic size is used)."""
    raw = slide.attrs.get("size")
    if raw is None:
        return None
    if (v := _parse_size(raw)) is not None:
        return v
    _bad(ctx, "size", raw)
    return None


def _length(ctx, raw: Any, ref: int, default: int) -> int:
    if raw is None:
        return default
    try:
        return max(to_emu(raw, ref), 0)
    except (ValueError, TypeError):
        ctx.diag("bad-length", f"invalid length {raw!r}", "use e.g. 0.5in, 36pt, 12%")
        return default


def _pt(x: float) -> int:
    return round(x * EMU_PER_PT)


def _need(paras: list[Paragraph], st: Style, w: int) -> float:
    ph, pv = css.inset_hv(st)
    return measure.paragraphs_height(paras, max(w - ph, 1), st, 1.0) + pv


def _sizes(ctx, cap: float, floor: float | None = None):
    """Sizes from ``cap`` down to the theme's smallest font in half-point steps."""
    lo = floor if floor is not None else ctx.theme.min_font_size
    s = cap
    while s > lo + 1e-9:
        yield s
        s -= _STEP
    yield lo


def _grow_cap(ctx, base_pt: float) -> float:
    """The largest size body text may reach: ``layout.grow_max`` x its role size."""
    return base_pt * measure.grow_ratio(ctx.lt, ctx.dense_k)


def _flat_texts(slide: Slide) -> list[Text]:
    return [
        e for e in slide.elements if isinstance(e, Text) and e.role == "body" and "callout" not in e.classes
    ]


def _others(ctx, slide: Slide, used: tuple[type, ...], what: str) -> None:
    """Info when the slide holds blocks the form does not draw."""
    extra = [e for e in slide.elements if not isinstance(e, used)]
    if extra:
        ctx.diag(
            "form-skipped",
            f"@{what} does not draw {len(extra)} other block(s) on this slide",
            "keep only what the form takes on the slide, or move the rest to another slide",
            level="info",
        )


def _items_of(paras: list[Paragraph]) -> list[list[Paragraph]]:
    """List items: a deeper paragraph belongs to the item above."""
    items: list[list[Paragraph]] = []
    for p in paras:
        if p.level > 0 and items:
            items[-1].append(p)
        else:
            items.append([p])
    return items


def _plain(p: Paragraph) -> str:
    return "".join(r.text for r in p.runs)


def _strip_runs(runs: list[Run], pattern: re.Pattern[str]) -> list[Run]:
    """``runs`` with the match of ``pattern`` removed from the start of the text (it may span runs)."""
    text = "".join(r.text for r in runs)
    m = pattern.match(text)
    if not m:
        return runs
    cut, out = m.end(), []
    for r in runs:
        if cut >= len(r.text):
            cut -= len(r.text)
            continue
        out.append(r.model_copy(update={"text": r.text[cut:]}) if cut else r)
        cut = 0
    return out


def _lstrip(runs: list[Run]) -> list[Run]:
    out = list(runs)
    while out and not out[0].text.strip():
        out.pop(0)
    if out:
        out[0] = out[0].model_copy(update={"text": out[0].text.lstrip()})
    return out


def _rstrip(runs: list[Run]) -> list[Run]:
    out = list(runs)
    while out and not out[-1].text.strip():
        out.pop()
    if out:
        out[-1] = out[-1].model_copy(update={"text": out[-1].text.rstrip()})
    return out


def _text_el(name: str, paras: list[Paragraph], cls: str) -> Text:
    return Text(role="body", paragraphs=paras, classes=[cls], attrs={"shape_name": name})


def _shape_el(
    name: str, cls: str, shape: str = "rect", paras: list[Paragraph] | None = None, **attrs
) -> Shape:
    return Shape(shape=shape, paragraphs=paras or [], classes=[cls], attrs={"shape_name": name, **attrs})


def _base(ctx, role: str = "body") -> Style:
    return _E()._role_style(ctx, role)


def _card(ctx) -> Style:
    return ctx.theme.classes.get("card") or fast_style()


def _pad_pt(st: Style, default: float = 10.0) -> float:
    raw = st.padding
    if raw is None:
        return default
    try:
        return to_emu(raw) / EMU_PER_PT
    except (ValueError, TypeError):
        return default


def _diag_once(deck: Deck, rule: str, message: str, hint: str, slide: int, level: str = "warning") -> None:
    if not any(d.rule == rule and d.message == message and d.slide == slide for d in deck.diagnostics):
        deck.diagnostics.append(
            Diagnostic(level=level, message=message, slide=slide, rule=rule, hint=hint)  # type: ignore[arg-type]
        )


# --------------------------------------------------------------------------- prepare (content rewrites)

_ATTRIB_START = re.compile(r"^\s*(?:[\u2014\u2015\u2013~]|--+|\u2014\u2014)\s*")
_ATTRIB_TAIL = re.compile(
    r"^(.*?[.!?\u3002\uff01\uff1f\"\u201d\u300d\u300f\u2019\u00bb\)])\s+[\u2014\u2015\u2013]\s*(\S[^\u2014\u2015\u2013]{0,80})$"
)
_CLOSERS = "\"'\u201d\u2019\u300d\u300f\u00bb)"


def _split_attribution(paras: list[Paragraph]) -> tuple[list[Paragraph], list[Run] | None]:
    """``(quote paragraphs, attribution runs)``: the last paragraph that starts with a dash, or the tail
    ``... sentence. — Name`` of a paragraph the parser joined (two ``>`` lines are one paragraph)."""
    if not paras:
        return paras, None
    last = paras[-1]
    text = _plain(last)
    if len(paras) > 1 and _ATTRIB_START.match(text):
        return paras[:-1], _lstrip(_strip_runs(last.runs, _ATTRIB_START))
    m = _ATTRIB_TAIL.match(text)
    if m:
        cut = len(m.group(1))
        head, tail, left = [], [], cut
        for r in last.runs:  # split the runs at the end of the quote text
            if left >= len(r.text):
                head.append(r)
                left -= len(r.text)
            elif left > 0:
                head.append(r.model_copy(update={"text": r.text[:left]}))
                tail.append(r.model_copy(update={"text": r.text[left:]}))
                left = 0
            else:
                tail.append(r)
        who = _lstrip(_strip_runs(tail, re.compile(r"^\s*[\u2014\u2015\u2013]\s*")))
        return [*paras[:-1], last.model_copy(update={"runs": _rstrip(head)})], who
    return paras, None


def _prepare_quote(slide: Slide) -> Slide:
    """``@quote``: the lead, subtitle, ``>`` / body text and conclusion of the slide are ONE text (the quote
    and, last, its attribution); the layout then draws it as a quotation."""
    paras: list[Paragraph] = []
    for t in (slide.lead, slide.subtitle):
        if t is not None:
            paras += t.paragraphs
    kept = []
    for e in slide.elements:
        if isinstance(e, Text) and e.role in ("body", "quote") and "callout" not in e.classes:
            paras += e.paragraphs
        else:
            kept.append(e)
    if slide.conclusion is not None:
        paras += slide.conclusion.paragraphs
    paras = [p.model_copy(update={"marker": None, "level": 0}) for p in paras if p.runs]
    if not paras:
        return slide
    el = Text(role="body", paragraphs=paras, classes=["quote"], attrs={"quote_src": True})
    layout = None if slide.layout in ("section", "cover") else slide.layout
    return slide.model_copy(
        update={"lead": None, "subtitle": None, "conclusion": None, "elements": [el, *kept], "layout": layout}
    )


_NUM = re.compile(r"[^\d\-+\u2212.]*([-+\u2212]?\d[\d,]*(?:\.\d+)?)\s*[%\uff05]?[^\d]{0,3}")


def _number(text: str) -> float | None:
    """The number in a table cell (``1,234`` ``12.5%`` ``¥300`` ``−3``), else ``None``."""
    m = _NUM.fullmatch(text.strip().replace("\u2060", ""))
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", "").replace("\u2212", "-"))
    except ValueError:
        return None


def _hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _mix(stops: list[tuple[int, int, int]], t: float) -> str:
    """The color at ``t`` (0..1) along ``stops`` (piecewise linear in RGB) as ``#RRGGBB``."""
    t = min(max(t, 0.0), 1.0)
    pos = t * (len(stops) - 1)
    i = min(int(pos), len(stops) - 2)
    f = pos - i
    a, b = stops[i], stops[i + 1]
    return "#" + "".join(f"{round(a[k] + (b[k] - a[k]) * f):02X}" for k in range(3))


def _scale_stops(theme, raw: str, deck: Deck, index: int) -> list[tuple[int, int, int]] | None:
    stops = []
    for w in (x.strip() for x in raw.split(",") if x.strip()):
        h = theme.hexval(w)
        if h is None:
            from ..parser.css import parse_color

            c = parse_color(w, set(theme.colors))
            h = theme.hexval(c) if c else None
        if h is None:
            return None
        stops.append(_hex_rgb(h))
    return stops if len(stops) >= 2 else None


def _prepare_heatmap(slide: Slide, deck: Deck, theme, index: int) -> Slide:
    """``@heatmap``: every numeric body cell of the first table gets a fill that interpolates along
    ``colors=`` (default ``heatmap.colors``) between ``min=`` and ``max=`` (default: the table's own range),
    and an ink that reads on it (``text=auto``). Row and column labels (text cells) stay as they are."""
    n = index + 1
    t_idx = next((i for i, e in enumerate(slide.elements) if isinstance(e, Table)), None)
    if t_idx is None:
        _diag_once(
            deck,
            "form-empty",
            "@heatmap needs a table",
            "write a table with a header row and a label column; the numbers become the colours",
            n,
        )
        return slide
    t: Table = slide.elements[t_idx]  # type: ignore[assignment]
    if t.attrs.get("heatmap"):  # already filled (a trial layout prepares the same slide again)
        return slide
    at = slide.attrs
    raw_colors = at.get("colors") or theme.heatmap_colors
    if "fill" in at and "colors" not in at:  # fill=<c>: the high end of the default scale
        low = theme.heatmap_colors.split(",")[0]
        raw_colors = f"{low},{at['fill']}"
    stops = _scale_stops(theme, raw_colors, deck, index)
    if stops is None:
        _diag_once(
            deck,
            "bad-attr",
            f"colors={raw_colors}: need two or more colors",
            "write colors=#F3F6FA,primary (theme names or #RRGGBB, low to high)",
            n,
        )
        stops = _scale_stops(theme, F.Forms2Tokens().heatmap_colors, deck, index) or []
    mode = str(at.get("text") or theme.heatmap_text).lower()
    if mode not in ("auto", "on", "off"):
        _diag_once(deck, "bad-attr", f"text={mode}: not a heatmap text mode", "text takes auto, on or off", n)
        mode = "auto"
    first_col = 1 if (t.header_cols >= 1 or _label_column(t)) else 0
    cells: list[tuple[int, int, float]] = []
    for r in range(t.header_rows, len(t.rows)):
        for c in range(first_col, len(t.rows[r])):
            v = _number(" ".join(p.plain for p in t.rows[r][c].paragraphs))
            if v is not None:
                cells.append((r, c, v))
    if not cells or not stops:
        _diag_once(
            deck,
            "form-empty",
            "@heatmap found no numeric cell",
            "put numbers (12, 3.5%, 1,200) in the body cells; the first column and header row may be text",
            n,
        )
        return slide
    data = [v for _r, _c, v in cells]
    lo, hi = min(data), max(data)
    for key in ("min", "max"):
        if key in at:
            try:
                val = float(str(at[key]))
            except ValueError:
                _diag_once(deck, "bad-attr", f"{key}={at[key]}: not a number", f"{key} takes a number", n)
                continue
            lo, hi = (val, hi) if key == "min" else (lo, val)
    if hi <= lo:
        _diag_once(
            deck,
            "bad-attr",
            f"min={lo:g} max={hi:g}: the scale is empty",
            "min must be below max (leave both out to use the table's own range)",
            n,
        )
        hi = lo + 1.0
    cell_pt = None
    if "size" in at:
        cell_pt = _parse_size(at["size"])
        if cell_pt is None:
            _diag_once(
                deck, "bad-attr", f"size={at['size']}: not a font size", f"size takes {F.VALUES['size']}", n
            )
    rows = [list(r) for r in t.rows]
    for r, c, v in cells:
        fill = _mix(stops, (v - lo) / (hi - lo))
        cell = rows[r][c]
        st = cell.style or Style()
        upd: dict[str, Any] = {"fill": fill, "align": st.align or "center"}
        if cell_pt:
            upd["font_size"] = cell_pt
        if mode == "auto":
            upd["color"] = theme.ink_on(fill, "fg")
        elif mode == "off":
            pass  # text=off: the number is left out (the colours carry the message)
        new_cell: Cell = cell.model_copy(update={"style": st.model_copy(update=upd)})
        if mode == "off":
            new_cell = new_cell.model_copy(update={"paragraphs": [Paragraph(runs=[Run(text="\u00a0")])]})
        rows[r][c] = new_cell
    for c in {c for _r, c, _v in cells}:  # the header above a column of numbers sits over its cells
        for r in range(min(t.header_rows, len(rows))):
            if c < len(rows[r]):
                hs = rows[r][c].style or Style()
                rows[r][c] = rows[r][c].model_copy(
                    update={"style": hs.model_copy(update={"align": hs.align or "center"})}
                )
    hexes = ",".join(f"#{r:02X}{g:02X}{b:02X}" for r, g, b in stops)
    attrs = {
        **t.attrs,
        "heatmap": f"{lo:g};{hi:g};{hexes};{mode}",
    }  # also the shape name: the importer reads it
    new_t = t.model_copy(update={"rows": rows, "attrs": attrs})
    els = list(slide.elements)
    els[t_idx] = new_t
    return slide.model_copy(update={"elements": els})


def _label_column(t: Table) -> bool:
    """The first column of the body holds text (row labels)."""
    body = [r[0] for r in t.rows[t.header_rows :] if r]
    return any(_number(" ".join(p.plain for p in c.paragraphs)) is None for c in body)


def prepare(slide: Slide, deck: Deck, theme, index: int) -> Slide:
    """A copy of the slide for the forms that only rewrite content (the parsed slide is unchanged)."""
    word = F.word_of(slide.classes)
    if word == "quote":
        return _prepare_quote(slide)
    if word == "heatmap":
        return _prepare_heatmap(slide, deck, theme, index)
    return slide


# --------------------------------------------------------------------------- @split


def _ratio(ctx_diag: Callable[[str, str, str], None], raw: str | None, default: str) -> tuple[float, float]:
    for cand, bad in ((raw, True), (default, False)):
        if cand is None:
            continue
        if F.RATIO.fullmatch(cand.strip()):
            a, b = (float(x) for x in cand.strip().split(":"))
            if a > 0 and b > 0:
                return a, b
        if bad:
            ctx_diag("ratio", cand, "")
    return 1.0, 1.0


def split_layout(
    slide: Slide, deck: Deck, theme, index: int, layout: Callable[..., list[Placed]]
) -> list[Placed] | None:
    """``@split side=left|right ratio=1:1 bleed=on fit=cover``: an image (or a ``fill=`` colour block) on one
    side, everything else on the other. The text side is laid out by the ordinary engine on a virtual slide
    that is only as wide as that side (title, lead, boxes, conclusion, footer: all the usual passes), then
    moved next to the image; ``bleed=on`` runs the image to the slide edge over the full height."""
    if F.word_of(slide.classes) != "split":
        return None
    n = index + 1
    try:
        W, H = slide_size(deck.size)
    except ValueError:
        W, H = slide_size("16:9")
    at = slide.attrs
    side = str(at.get("side", "left")).lower()
    if side not in ("left", "right"):
        _diag_once(deck, "bad-attr", f"side={side}: not a side", f"side takes {F.VALUES['side']}", n)
        side = "left"
    flag = str(at.get("bleed", "off")).lower()
    if flag not in ("on", "off", "true", "false", "yes", "no"):
        _diag_once(deck, "bad-attr", f"bleed={flag}: not on/off", f"bleed takes {F.VALUES['bleed']}", n)
        flag = "off"
    bleed = flag in ("on", "true", "yes")
    fit = str(at.get("fit", "cover")).lower()
    if fit not in ("cover", "contain", "stretch"):
        _diag_once(deck, "bad-attr", f"fit={fit}: not a fit", f"fit takes {F.VALUES['fit']}", n)
        fit = "cover"
    bad: list[tuple[str, str]] = []
    a, b = _ratio(lambda k, v, _h: bad.append((k, v)), at.get("ratio"), theme.split_ratio)
    for k, v in bad:
        _diag_once(deck, "bad-attr", f"{k}={v}: not an image:text ratio", f"{k} takes {F.VALUES['ratio']}", n)

    img_i = next((i for i, e in enumerate(slide.elements) if isinstance(e, Image)), None)
    img = slide.elements[img_i] if img_i is not None else None
    rest = [e for i, e in enumerate(slide.elements) if i != img_i]
    sub_attrs = {k: v for k, v in at.items() if k not in F.KEYS}
    sub = slide.model_copy(
        update={
            "classes": [c for c in slide.classes if c not in F.WORDS],
            "elements": rest,
            "attrs": sub_attrs,
        }
    )
    Mx, My = to_emu(theme.margin_x), to_emu(theme.margin_y)
    gap = theme.split_gap if theme.split_gap is not None else theme.gap
    try:
        g = to_emu(at["gap"] if "gap" in at else gap, W)
    except (ValueError, TypeError):
        g = to_emu(theme.gap)
    if bleed:
        iw = round(W * a / (a + b))
        img_rect = Rect(0 if side == "left" else W - iw, 0, iw, H)
        x0, vw = (iw + g - Mx, W - (iw + g - Mx)) if side == "left" else (0, W - iw - g + Mx)
    else:
        iw = round((W - 2 * Mx - g) * a / (a + b))
        img_rect = Rect(Mx if side == "left" else W - Mx - iw, My, iw, H - 2 * My)
        x0, vw = (iw + g, W - (iw + g)) if side == "left" else (0, W - iw - g)
    x0, vw = max(x0, 0), max(vw, round(0.2 * W))
    sub_deck = deck.model_copy(update={"size": f"{vw / EMU_PER_PT:.2f}ptx{H / EMU_PER_PT:.2f}pt"})
    sub_theme = theme
    if "size" in at:
        if (px := _parse_size(at["size"])) is None:
            _diag_once(
                deck, "bad-attr", f"size={at['size']}: not a font size", f"size takes {F.VALUES['size']}", n
            )
        else:  # the text side is the ordinary engine: a pinned body size never grows
            sub_theme = theme.model_copy(
                update={"sizes": {**theme.sizes, "body": px}, "pinned": [*theme.pinned, "body"]}
            )
    placed = layout(sub, sub_deck, sub_theme, index)
    shifted = [p.model_copy(update={"x": p.x + x0}) for p in placed]
    fitmap = deck.attrs.get("_fit", {}).get(index)
    if fitmap and fitmap.get("body"):
        fitmap["body"][0] += x0
    if fitmap is not None:
        fitmap["split"] = f"{side}{' bleed' if bleed else ''} {a:g}:{b:g}"

    card = theme.classes.get("card")
    radius = None if bleed else (card.radius if card is not None else None)
    first: list[Placed] = []
    fill_raw = at.get("fill")
    colour = None
    if fill_raw is not None or img is None:
        colour = theme.colors.get(str(fill_raw)) and str(fill_raw)
        if colour is None and fill_raw is not None:
            from ..parser.css import parse_color

            colour = parse_color(str(fill_raw), set(theme.colors))
            if colour is None:
                _diag_once(
                    deck, "bad-attr", f"fill={fill_raw}: not a color", f"fill takes {F.VALUES['fill']}", n
                )
        colour = colour or theme.split_fill or "surface"
        if colour.lower() == "none":
            colour = None
    if colour and (img is None or fill_raw is not None):
        first.append(
            Placed(
                element=_shape_el("Split fill", "split-fill"),
                x=img_rect.x,
                y=img_rect.y,
                w=img_rect.w,
                h=img_rect.h,
                style=fast_style(fill=colour, line=None, radius=radius),
            )
        )
    if img is None:
        if fill_raw is None:
            _diag_once(
                deck,
                "form-empty",
                "@split has no image: a colour block is drawn",
                "add ![alt](picture.png) for a picture or fill=<color> to choose the block colour",
                n,
                "info",
            )
    else:
        first.append(
            Placed(
                element=img.model_copy(update={"fit": fit}),
                x=img_rect.x,
                y=img_rect.y,
                w=img_rect.w,
                h=img_rect.h,
                style=fast_style(radius=radius) if radius else Style(),
            )
        )
    return [*first, *shifted]


# --------------------------------------------------------------------------- compose


def compose(ctx, slide: Slide, kind: str, body: Rect | None, sg: int) -> tuple[Any, str] | None:
    """The body shapes of ``@iconlist`` ``@quote`` ``@proscons`` ``@progress`` ``@harvey`` ``@pins`` into
    ``ctx.out``; ``(ctx, word)`` when composed, ``None`` when the slide is laid out the ordinary way."""
    word = F.word_of(slide.classes)
    fn = _COMPOSERS.get(word or "")
    if fn is None or kind != "content" or body is None or body.h <= 0:
        return None
    if not slide.elements:
        ctx.deck.diagnostics.append(
            Diagnostic(
                level="info",
                message=f"@{word} has no content",
                slide=ctx.index + 1,
                rule="form-empty",
                hint=f"put the content the form takes under the @{word} line (see docs/SYNTAX.md)",
            )
        )
        return None
    try:
        ok = fn(ctx, slide, body, sg)
    except Exception as e:  # a form must never take the build down: say so and fall back
        ctx.diag(
            "form-error",
            f"@{word} could not be composed: {type(e).__name__}: {e}"[:140],
            "simplify the slide or report a bug; it is laid out as an ordinary slide",
        )
        ok = False
    if not ok:  # laid out the ordinary way: what the form said must still reach the build output
        ctx.deck.diagnostics.extend(ctx.diags)
        return None
    return ctx, word  # type: ignore[return-value]


# --------------------------------------------------------------------------- @iconlist

_ICON_HEAD = re.compile(r"^\s*(?:icon=(\S+)(?:\s+disc=(\S+))?|:([A-Za-z0-9_-]+):)\s*")
_SEP = re.compile(r"^[\s:\uff1a\u2014\u2013-]+")


def _iconlist_item(ctx, group: list[Paragraph], n: int) -> dict[str, Any]:
    """``{icon, title: runs | None, text: [Paragraph]}`` of one list item."""
    first = group[0]
    text = _plain(first)
    m = _ICON_HEAD.match(text)
    name = (m.group(1) or m.group(3)) if m else None
    disc = m.group(2) if m else None  # `icon=bolt disc=accent`: this item's own disc colour
    runs = _strip_runs(first.runs, _ICON_HEAD) if m else list(first.runs)
    runs = _lstrip(runs)
    nested = [p.model_copy(update={"marker": None, "level": 0}) for p in group[1:]]
    lead = []
    for r in runs:
        if r.bold or not r.text.strip():
            lead.append(r)
        else:
            break
    while lead and not lead[-1].text.strip() and len(lead) > 0:
        lead.pop()
    title: list[Run] | None = None
    rest: list[Run] = runs
    if any(r.bold and r.text.strip() for r in lead):
        title, rest = _rstrip(lead), _lstrip(_strip_runs(runs[len(lead) :], _SEP))
    elif nested:
        title, rest = [r.model_copy(update={"bold": True}) for r in runs], []
    text = ([Paragraph(runs=rest)] if any(r.text.strip() for r in rest) else []) + nested
    if name is not None and not (icons.is_file(name) or icons.path(name.lower())):
        import difflib

        near = difflib.get_close_matches(name.lower(), icons.names(), n=1, cutoff=0.4)
        ctx.diag(
            "unknown-icon",
            f"item {n}: unknown icon '{name}'",
            f"did you mean '{near[0]}'? or icon=file.svg for your own"
            if near
            else "see 'slidemark docs icons'",
        )
        name = None
    elif name is None:
        ctx.diag(
            "iconlist-icon",
            f"item {n} has no icon",
            "start every item with icon=name (or :name:), e.g. - icon=bolt **Fast** builds in seconds",
            level="info",
        )
    return {
        "icon": name.lower() if name and not icons.is_file(name) else name,
        "disc": disc,
        "title": title,
        "text": text,
    }


def _iconlist(ctx, slide: Slide, body: Rect, sg: int) -> bool:
    E, th = _E(), ctx.theme
    texts = _flat_texts(slide)
    paras = [p for t in texts for p in t.paragraphs if p.runs]
    if not paras:
        ctx.diag("form-empty", "@iconlist has no items", "write a list: - icon=bolt **Title** text")
        return False
    _others(ctx, slide, (Text,), "iconlist")
    items = [_iconlist_item(ctx, g, i + 1) for i, g in enumerate(_items_of(paras))]
    n = len(items)
    cols = n if n < 2 else (1 if n <= 3 else 2 if n <= 8 else 3)
    cols = 1 if n == 1 else cols
    raw_cols = slide.attrs.get("cols")
    if raw_cols is not None:
        try:
            c = int(str(raw_cols))
            if not 1 <= c <= 3:
                raise ValueError
            cols = min(c, n)
        except ValueError:
            _bad(ctx, "cols", raw_cols)
    cols = max(min(cols, 3), 1)
    rows = math.ceil(n / cols)
    gutter = E._gap(ctx, slide.attrs.get("gap"), body.w)
    cw = (body.w - gutter * (cols - 1)) // cols
    base = _base(ctx)
    fill = _paint(ctx, slide.attrs.get("fill"), None, "fill")
    card = _card(ctx)
    pad = _pt(base.font_size * 0.6) if fill else 0
    radius = card.radius if fill else None
    icon_col = _paint(ctx, th.iconlist_icon_color, "primary", "iconlist.icon.color")
    discs = [icondisc.disc_color(th, {"disc": it["disc"]} if it["disc"] else None, ctx.diag) for it in items]
    pinned = _attr_size(ctx, slide)
    cap = pinned or _grow_cap(ctx, base.font_size or 18)
    rg = sg

    def paras_of(it, S: float) -> list[Paragraph]:
        out: list[Paragraph] = []
        if it["title"]:
            out.append(Paragraph(runs=[r.model_copy(update={"bold": True}) for r in it["title"]]))
        ts = fast_style(font_size=round(S * th.iconlist_text_ratio, 2)) if it["title"] else None
        out += [p.model_copy(update={"style": ts}) if ts else p for p in it["text"]]
        return out

    def geom(S: float):
        icon = (
            max(_length(ctx, th.iconlist_icon_size, body.w, 0), 1)
            if th.iconlist_icon_size is not None
            else _pt(th.iconlist_icon_ratio * S)
        )
        if any(
            discs
        ):  # a disc takes the icon slot: `icon.disc.size`, else the slot x `layout.icon_disc_list`
            icon = icondisc.diameter(th, ctx.lt, icon, ctx.lt.icon_disc_list)
        gi = _length(ctx, th.iconlist_gap, body.w, round(th.iconlist_gap_ratio * icon))
        tw = cw - icon - gi - 2 * pad
        if tw < _pt(S * 4):
            return None
        st = base.merged(fast_style(font_size=S, padding="0pt"))
        hs = [max(icon, round(_need(paras_of(it, S), st, tw))) + 2 * pad for it in items]
        row_h = [max(hs[r * cols : (r + 1) * cols]) for r in range(rows)]
        return icon, gi, tw, row_h

    S = pinned or base.font_size or 18
    got = None
    for S in [pinned] if pinned else _sizes(ctx, cap):
        got = geom(S)
        if got and sum(got[3]) + rg * (rows - 1) <= body.h:
            break
    if got is None:
        got = geom(S) or (_pt(S * 2), _pt(S), max(cw // 2, 1), [_pt(S * 3)] * rows)
    icon, gi, tw, row_h = got
    if sum(row_h) + rg * (rows - 1) > body.h * 1.01:
        ctx.over.append("icon list")
    tall = max(row_h)
    slot = min(max((body.h + rg) // rows, tall), round(tall * th.iconlist_row_air))
    used = rows * slot - rg
    y0 = body.y + max((body.h - used) // 2, 0)
    for i, it in enumerate(items):
        r, c = divmod(i, cols)
        x = body.x + c * (cw + gutter)
        y = y0 + r * slot
        h = slot - rg
        st = base.merged(
            fast_style(
                font_size=S,
                valign="middle",
                align="left",
                fill=fill,
                radius=radius,
                shadow=(card.shadow or None)
                if fill
                else None,  # `card.shadow` / `card.elevation` reach the cards
                padding_left=f"{(pad + icon + gi) / EMU_PER_PT:.2f}pt",
                padding_right=f"{pad / EMU_PER_PT:.2f}pt",
                padding_top="0pt",
                padding_bottom="0pt",
            )
        )
        ctx.emit(_text_el(f"Iconlist {i + 1}", paras_of(it, S), "iconlist"), Rect(x, y, cw, h), st)
        if it["icon"]:
            disc = discs[i]
            shape = icondisc.icon_shape(th, ctx.lt, it["icon"], disc).model_copy(
                update={"classes": ["iconlist-icon"]}
            )
            ink = icon_col if th.iconlist_icon_color else icondisc.ink(th, disc, "primary")
            ctx.emit(shape, Rect(x + pad, y + (h - icon) // 2, icon, icon), fast_style(fill=ink, line=None))
    return True


# --------------------------------------------------------------------------- @quote


def _quote(ctx, slide: Slide, body: Rect, sg: int) -> bool:
    th = ctx.theme
    src = next((e for e in slide.elements if isinstance(e, Text) and e.attrs.get("quote_src")), None)
    if src is None:
        ctx.diag("form-empty", "@quote has no text", "write the quotation as a > block, then `> — Name`")
        return False
    _others(ctx, slide, (Text,), "quote")
    quote, who = _split_attribution(list(src.paragraphs))
    align = str(slide.attrs.get("align", "left")).lower()
    if align not in ("left", "center", "right"):
        _bad(ctx, "align", align)
        align = "left"
    base = _base(ctx)
    fill = _paint(ctx, slide.attrs.get("fill"), _paint(ctx, th.quote_fill, None, "quote.fill"), "fill")
    bar = _paint(ctx, th.quote_bar, None, "quote.bar")  # `quote.bar=accent`: a bar on the card's left edge
    bar_w = _length(ctx, th.quote_bar_w, body.w, _pt(8)) if bar and fill else 0
    card = _card(ctx)
    pad = _pt((base.font_size or 18) * 1.0) if fill else 0
    width = round(body.w * th.quote_width) - 2 * pad - bar_w
    card_h = None  # `quote.h=3in` / `full`: the card has this height (None = as tall as its content)
    if fill and th.quote_h:
        full = str(th.quote_h).lower() == "full"
        card_h = body.h if full else min(_length(ctx, th.quote_h, body.h, 0), body.h)
    pinned = _attr_size(ctx, slide) or th.quote_size
    body_pt = th.sizes.get("body", 18) * ctx.dense_k
    cap = pinned or min(body_pt * th.quote_grow, _grow_cap(ctx, body_pt) * 1.6)
    ink = _paint(ctx, None, "fg", "")
    mark_col = _paint(ctx, th.quote_mark_color, "accent", "quote.mark.color")
    by_col = _paint(ctx, th.quote_by_color, "muted", "quote.by.color")
    mark = (th.quote_mark or "\u201c")[:2]
    inner = (card_h or body.h) - 2 * pad
    by_align = str(th.quote_by_align or align).lower()

    def parts(S: float):
        qst = base.merged(
            fast_style(font_size=S, align=align, valign="top", padding="0pt", color=ink, bold=False)
        )
        mark_pt = S * th.quote_mark_ratio
        mst = base.merged(
            fast_style(font_size=mark_pt, bold=True, padding="0pt", line_spacing=th.quote_mark_leading)
        )
        mark_h = round(_need([Paragraph(runs=[Run(text=mark, bold=True)])], mst, width))
        qh = round(_need(quote, qst, width))
        by_pt = max(S * th.quote_by_ratio, th.min_font_size)
        by_runs = [Run(text="\u2014 ")] + (who or []) if who else []
        by_para = [Paragraph(runs=by_runs)] if by_runs else []
        bst = qst.merged(fast_style(font_size=by_pt, color=by_col, align=by_align))
        bh = round(_need(by_para, bst, width)) if by_para else 0
        air = _length(ctx, slide.attrs.get("gap"), body.w, _pt(S * 0.5))
        return qst, bst, mark_pt, mark_h, qh, bh, by_para, air, mark_h + qh + bh + air * (2 if by_para else 1)

    S = pinned or cap
    got = None
    for S in [pinned] if pinned else _sizes(ctx, cap):
        got = parts(S)
        if got[-1] <= inner:
            break
    got = got or parts(S)
    qst, bst, mark_pt, mark_h, qh, bh, by_para, air, total = got
    if total > inner * 1.01:
        ctx.over.append("quote")
    x = (
        body.x
        + {
            "left": 0,
            "center": (body.w - width - bar_w) // 2 - pad,
            "right": body.w - width - bar_w - 2 * pad,
        }[align]
    )
    if card_h:  # a card of its own height: it sits at the top of the body, its content centred in it
        cy, ch = body.y, card_h
        y = cy + max((ch - total) // 2, 0)
    else:
        y = body.y + max((body.h - total) // 2, 0)
        cy, ch = y - pad, total + 2 * pad
    if fill:
        ctx.emit(
            _shape_el("Quote panel", "quote-panel"),
            Rect(x, cy, width + 2 * pad + bar_w, ch),
            fast_style(fill=fill, line=None, radius=card.radius),
        )
        if bar_w:
            ctx.emit(
                _shape_el("Quote bar", "quote-bar"), Rect(x, cy, bar_w, ch), fast_style(fill=bar, line=None)
            )
    tx = x + pad + bar_w
    ctx.emit(
        _text_el("Quote mark", [Paragraph(runs=[Run(text=mark, bold=True)])], "quote-mark"),
        Rect(tx, y, width, mark_h),
        base.merged(
            fast_style(
                font=base.font,
                font_size=mark_pt,
                color=mark_col,
                align=align,
                valign="top",
                padding="0pt",
                line_spacing=th.quote_mark_leading,
            )
        ),
    )
    y += mark_h
    ctx.emit(_text_el("Quote text", quote, "quote"), Rect(tx, y, width, qh), qst)
    y += qh + air
    if by_para:
        ctx.emit(_text_el("Quote by", by_para, "quote-by"), Rect(tx, y, width, bh), bst)
    return True


# --------------------------------------------------------------------------- @proscons


_GLYPH = re.compile(r"^\s*([+\u2212\u2013-]|[\u2713\u2714]|[\u2717\u2718\u00d7])\s+")
_PLUS_SET = ("+", "\u2713", "\u2714")


_MINUS_SEP = re.compile(r"\s\u2212\s")


def _split_minus(paras: list[Paragraph]) -> list[Paragraph]:
    """Markdown joins ``- a`` and a following ``\u2212 b`` line into one paragraph: a U+2212 between spaces
    starts a new item (``\u2212 b``), so ``+`` / ``\u2212`` written as glyphs both work."""
    out: list[Paragraph] = []
    for p in paras:
        text = _plain(p)
        starts = [0] + [m.start() + 1 for m in _MINUS_SEP.finditer(text)]
        if len(starts) == 1:
            out.append(p)
            continue
        ends = [m.start() for m in _MINUS_SEP.finditer(text)] + [len(text)]
        for a, b in zip(starts, ends, strict=True):
            runs, pos = [], 0
            for r in p.runs:
                lo, hi = max(a, pos), min(b, pos + len(r.text))
                if lo < hi:
                    runs.append(r.model_copy(update={"text": r.text[lo - pos : hi - pos]}))
                pos += len(r.text)
            out.append(p.model_copy(update={"runs": runs}))
    return [q for q in out if q.runs]


def _signed_items(box: Container, default_plus: bool) -> list[tuple[bool, list[Paragraph]]]:
    """``(is_plus, paragraphs)`` per item of a box: a leading ``+`` / ``−`` / ``-`` sets the sign, else the
    box's own sign (first box +, second −)."""
    paras = [p for c in box.children if isinstance(c, Text) for p in c.paragraphs if p.runs]
    out = []
    for g in _items_of(_split_minus(paras)):
        first, plus = g[0], default_plus
        m = _GLYPH.match(_plain(first))
        if m and (m.group(1) in _PLUS_SET or _plain(first).lstrip()[0] in "\u2212\u2013-\u2717\u2718\u00d7"):
            plus = m.group(1) in _PLUS_SET
            first = first.model_copy(update={"runs": _strip_runs(first.runs, _GLYPH)})
        first = first.model_copy(update={"marker": None, "level": 0})
        rest = [p.model_copy(update={"marker": None, "level": 0}) for p in g[1:]]
        out.append((plus, [first, *rest]))
    return out


def _proscons(ctx, slide: Slide, body: Rect, sg: int) -> bool:
    E, th = _E(), ctx.theme
    boxes = [e for e in slide.elements if isinstance(e, Container) and e.title is not None]
    if len(boxes) < 2:
        ctx.diag(
            "form-empty",
            "@proscons needs two ## boxes",
            "write `## Pros` + items, then `## Cons` + items (any headings); a last > line is the verdict",
        )
        return False
    if len(boxes) > 2 or len(boxes) != len(slide.elements):
        ctx.diag(
            "form-skipped",
            "@proscons draws the first two ## boxes only",
            "move other blocks to another slide",
            level="info",
        )
    boxes = boxes[:2]
    base = _base(ctx)
    plus_col = _paint(ctx, th.proscons_plus_color, "success", "proscons.plus.color")
    minus_col = _paint(ctx, th.proscons_minus_color, "danger", "proscons.minus.color")
    glyphs = {True: (th.proscons_plus or "+")[:2], False: (th.proscons_minus or "\u2212")[:2]}
    card = _card(ctx)
    fill = _paint(ctx, slide.attrs.get("fill"), card.fill, "fill")
    gap = _length(
        ctx,
        th.proscons_gap if slide.attrs.get("gap") is None else slide.attrs.get("gap"),
        body.w,
        E._gap(ctx, None, body.w),
    )
    cw = (body.w - gap) // 2
    pad = _pt(_pad_pt(card))
    data = [_signed_items(b, k == 0) for k, b in enumerate(boxes)]
    if not any(data):
        ctx.diag("form-empty", "@proscons has no items", "write `- item` lines under both headings")
        return False
    pinned = _attr_size(ctx, slide)
    cap = pinned or _grow_cap(ctx, base.font_size or 18)
    row_gap = sg
    air = th.proscons_air

    def geom(S: float):
        gl = _pt(S * 1.35)
        tw = cw - 2 * pad - gl - _pt(S * 0.5)
        if tw < _pt(S * 4):
            return None
        ist = base.merged(fast_style(font_size=S, padding="0pt"))
        hst = _head_style(ctx, S)
        cards = []
        for k, items in enumerate(data):
            hh = round(_need(boxes[k].title.paragraphs, hst, cw - 2 * pad)) + 2 * pad // 2
            hs = [max(round(_need(g, ist, tw)), gl) for _p, g in items]
            cards.append((hh, hs, hh + pad + sum(hs) + row_gap * max(len(hs) - 1, 0) + pad))
        return gl, tw, cards

    def _head_style(ctx_, S):
        return _base(ctx_, "heading").merged(
            fast_style(font_size=round(S * th.proscons_head_ratio, 2), padding="0pt", valign="middle")
        )

    S = pinned or base.font_size or 18
    got = None
    for S in [pinned] if pinned else _sizes(ctx, cap):
        got = geom(S)
        if got and max(c[2] for c in got[2]) <= body.h:
            break
    got = got or geom(S)
    if got is None:
        return False
    gl, tw, cards = got
    nat = max(c[2] for c in cards)
    if nat > body.h * 1.01:
        ctx.over.append("pros / cons")
    card_h = min(body.h, round(nat * air)) if air > 0 else nat
    y0 = body.y + max((body.h - card_h) // 2, 0)
    ist = base.merged(fast_style(font_size=S, padding="0pt", valign="middle"))
    for k, box in enumerate(boxes):
        x = body.x + k * (cw + gap)
        head_col = plus_col if k == 0 else minus_col
        hh, hs, _tot = cards[k]
        name = f"Proscons {k + 1}"
        ctx.emit(
            Container(classes=["card", "proscons"], attrs={"shape_name": name}),
            Rect(x, y0, cw, card_h),
            fast_style(fill=fill, line=card.line, line_width=card.line_width, radius=card.radius),
        )
        hink = th.ink_on(head_col, "bg") if head_col else "fg"
        ctx.emit(
            _text_el(f"{name} head", list(box.title.paragraphs), "proscons-head"),  # type: ignore[union-attr]
            Rect(x, y0, cw, hh + pad),
            _head_style(ctx, S).merged(
                fast_style(
                    fill=head_col,
                    color=hink,
                    radius=card.radius,
                    padding_left=f"{pad / EMU_PER_PT:.2f}pt",
                    padding_right=f"{pad / EMU_PER_PT:.2f}pt",
                    align="left",
                )
            ),
        )
        items = data[k]
        room = card_h - (hh + pad) - 2 * pad
        used = sum(hs) + row_gap * max(len(hs) - 1, 0)
        extra = (max(room - used, 0) // max(len(hs), 1)) if hs else 0
        extra = min(extra, round(S * EMU_PER_PT * 0.6 * (air - 1.0 if air > 1 else 0)))
        y = y0 + hh + pad + pad
        for j, ((plus, g), h) in enumerate(zip(items, hs, strict=True)):
            col = plus_col if plus else minus_col
            gx, ty = x + pad, y
            slot = h + extra
            ctx.emit(
                _shape_el(
                    f"{name} item {j + 1} glyph",
                    "proscons-glyph",
                    "ellipse",
                    [Paragraph(runs=[Run(text=glyphs[plus], bold=True)])],
                ),
                Rect(gx, ty + (slot - gl) // 2, gl, gl),
                base.merged(
                    fast_style(
                        font_size=round(S * 0.9, 2),
                        fill=col,
                        color=th.ink_on(col, "bg") if col else "fg",
                        line=None,
                        align="center",
                        valign="middle",
                        padding="0pt",
                        bold=True,
                    )
                ),
            )
            ctx.emit(
                _text_el(f"{name} item {j + 1}", g, "proscons-item"),
                Rect(gx + gl + _pt(S * 0.5), ty, tw, slot),
                ist,
            )
            y += slot + row_gap
    return True


# --------------------------------------------------------------------------- @progress

_PROG = re.compile(
    r"^(?P<label>.*?)[\s:\uff1a|\u2014-]*(?P<num>[-+]?\d+(?:[.,]\d+)?)\s*(?P<unit>%|\uff05|/\s*\d+(?:\.\d+)?)?\s*$"
)


def _progress_rows(slide: Slide) -> list[tuple[str, str]] | None:
    """``[(label, value text)]`` from a ``- label 72%`` list or a table (label, value)."""
    tab = next((e for e in slide.elements if isinstance(e, Table)), None)
    out: list[tuple[str, str]] = []
    if tab is not None:
        for r, row in enumerate(tab.rows):
            if len(row) < 2:
                continue
            lab = " ".join(p.plain for p in row[0].paragraphs).strip()
            val = " ".join(p.plain for p in row[1].paragraphs).strip()
            if r < tab.header_rows and _number(val) is None:
                continue
            out.append((lab, val))
        return out
    for t in _flat_texts(slide):
        for p in t.paragraphs:
            text = _plain(p).strip()
            if not text:
                continue
            m = _PROG.match(text)
            if m and m.group("label").strip():
                out.append((m.group("label").strip(), m.group("num") + (m.group("unit") or "")))
            else:
                out.append((text, ""))
    return out


def _fraction(val: str, mx: float) -> float | None:
    m = re.fullmatch(r"([-+]?\d+(?:[.,]\d+)?)\s*(%|\uff05|/\s*(\d+(?:\.\d+)?))?", val.strip())
    if not m:
        return None
    v = float(m.group(1).replace(",", "."))
    if m.group(2) in ("%", "\uff05"):
        return v / 100.0
    if m.group(3):
        d = float(m.group(3))
        return v / d if d else None
    return v / mx if mx else None


def _progress(ctx, slide: Slide, body: Rect, sg: int) -> bool:
    E, th = _E(), ctx.theme
    rows = _progress_rows(slide)
    if not rows:
        ctx.diag(
            "form-empty", "@progress has no rows", "write a list: - Build 72%  (or a table: label | value)"
        )
        return False
    _others(ctx, slide, (Text, Table), "progress")
    mx = 100.0
    if (raw := slide.attrs.get("max")) is not None:
        try:
            mx = float(str(raw))
            if mx <= 0:
                raise ValueError
        except ValueError:
            _bad(ctx, "max", raw)
            mx = 100.0
    drawn: list[tuple[str, str, float]] = []
    for lab, val in rows:
        f = _fraction(val, mx) if val else None
        if f is None:
            ctx.diag(
                "progress-value",
                f"'{lab[:30]}' has no usable value ({val or 'none'})",
                "end every line with a number: - Build 72%  or  - Tests 7/10  (max= sets the scale)",
            )
            continue
        if not 0 <= f <= 1:
            ctx.diag(
                "progress-range",
                f"'{lab[:30]}': {val} is outside 0..max",
                "the bar is clamped; raise max= or fix the value",
                level="info",
            )
        drawn.append((lab, val, min(max(f, 0.0), 1.0)))
    if not drawn:
        return False
    n = len(drawn)
    base = _base(ctx)
    fill = _paint(
        ctx,
        slide.attrs.get("fill") if "fill" in slide.attrs else th.progress_fill,
        "primary",
        "progress.fill",
    )
    track = _paint(ctx, th.progress_track, "surface", "progress.track")
    gutter = E._gap(ctx, slide.attrs.get("gap"), body.w)
    lw = round(body.w * th.progress_label_w)
    vw = round(body.w * th.progress_value_w)
    tw = body.w - lw - vw - 2 * gutter
    pitch0 = body.h // n
    pinned = _attr_size(ctx, slide) or th.progress_label_size
    cap = pinned or min(_grow_cap(ctx, base.font_size or 18), th.progress_max_pt)

    def need(S: float) -> float:
        st = base.merged(fast_style(font_size=S, padding="0pt"))
        return max(
            max(_need([Paragraph(runs=[Run(text=lab)])], st, lw) for lab, _v, _f in drawn),
            _need([Paragraph(runs=[Run(text="100%", bold=True)])], st, vw),
        )

    S = pinned or cap
    for S in [pinned] if pinned else _sizes(ctx, cap):
        if need(S) <= pitch0 * 0.96:
            break
    if need(S) > pitch0 * 1.01:
        ctx.over.append("progress bars")
    bar_h = _length(ctx, th.progress_h, body.h, round(_pt(S) * th.progress_h_ratio))
    bar_h = max(min(bar_h, pitch0), 1)
    pitch = min(pitch0, max(round(max(need(S), bar_h) * 1.9), 1))
    y0 = body.y + (body.h - pitch * n) // 2
    st_lab = base.merged(fast_style(font_size=S, padding="0pt", valign="middle", align="left"))
    st_val = st_lab.merged(fast_style(align="right", bold=True))
    radius = bar_h / 2 / EMU_PER_PT
    for i, (lab, val, f) in enumerate(drawn):
        y = y0 + i * pitch
        nm = f"Progress {i + 1}"
        ctx.emit(
            _text_el(f"{nm} label", [Paragraph(runs=[Run(text=lab)])], "progress-label"),
            Rect(body.x, y, lw, pitch),
            st_lab,
        )
        ty = y + (pitch - bar_h) // 2
        if track:
            ctx.emit(
                _shape_el(f"{nm} track", "progress-track", "rounded-rect"),
                Rect(body.x + lw + gutter, ty, tw, bar_h),
                fast_style(fill=track, line=None, radius=radius),
            )
        if f > 0:
            ctx.emit(
                _shape_el(f"{nm} fill", "progress-fill", "rounded-rect"),
                Rect(body.x + lw + gutter, ty, max(round(tw * f), 1), bar_h),
                fast_style(fill=fill, line=None, radius=radius),
            )
        ctx.emit(
            _text_el(f"{nm} value", [Paragraph(runs=[Run(text=val, bold=True)])], "progress-value"),
            Rect(body.x + lw + 2 * gutter + tw, y, vw, pitch),
            st_val,
        )
    ctx.asked["progress_max"] = mx
    return True


# --------------------------------------------------------------------------- @harvey


def _quarters(text: str) -> int | None:
    """0..4 from ``0``-``4`` or ``0 25 50 75 100`` (with or without ``%``), else ``None``."""
    v = _number(text)
    if v is None or v != int(v):
        return None
    v = int(v)
    if 0 <= v <= 4:
        return v
    if v in (25, 50, 75, 100):
        return v // 25
    return None


def _harvey(ctx, slide: Slide, body: Rect, sg: int) -> bool:
    th = ctx.theme
    tab = next((e for e in slide.elements if isinstance(e, Table)), None)
    if tab is None or not tab.rows:
        ctx.diag(
            "form-empty",
            "@harvey needs a table",
            "write a table: header row, label column, cells 0-4 (or 0/25/50/75/100%)",
        )
        return False
    _others(ctx, slide, (Table,), "harvey")
    nr, nc = len(tab.rows), max(len(r) for r in tab.rows)
    label_col = tab.header_cols >= 1 or _label_column(tab) or nc == 1
    c0 = 1 if label_col else 0
    base = _base(ctx)
    fill = _paint(
        ctx, slide.attrs.get("fill") if "fill" in slide.attrs else th.harvey_fill, "primary", "harvey.fill"
    )
    line = _paint(ctx, th.harvey_line, fill, "harvey.line")
    band = _paint(ctx, th.harvey_band, "surface", "harvey.band")
    cells: dict[tuple[int, int], int | str] = {}
    for r in range(tab.header_rows, nr):
        for c in range(c0, nc):
            txt = " ".join(p.plain for p in tab.rows[r][c].paragraphs).strip() if c < len(tab.rows[r]) else ""
            q = _quarters(txt)
            if q is None and txt:
                ctx.diag(
                    "harvey-value",
                    f"row {r + 1}, column {c + 1}: '{txt[:20]}' is not 0-4 or 0/25/50/75/100%",
                    "write a quarter count 0-4 or a percentage (0 25 50 75 100); the cell is left as text",
                )
            cells[(r, c)] = q if q is not None else txt
    head_w = round(body.w * th.harvey_head_w) if label_col else 0
    colw = (body.w - head_w) // max(nc - c0, 1)
    pinned = _attr_size(ctx, slide)
    cap = pinned or _grow_cap(ctx, base.font_size or 18)
    pitch0 = body.h // nr

    def need(S: float) -> float:
        st = base.merged(fast_style(font_size=S, padding="0pt"))
        worst = 0.0
        for r in range(nr):
            if label_col and tab.rows[r]:
                worst = max(worst, _need(tab.rows[r][0].paragraphs, st, head_w))
        for c in range(c0, nc):
            for r in range(tab.header_rows):
                if c < len(tab.rows[r]):
                    worst = max(worst, _need(tab.rows[r][c].paragraphs, st, colw))
        return worst

    S = pinned or cap
    for S in [pinned] if pinned else _sizes(ctx, cap):
        if need(S) <= pitch0 * 0.9:
            break
    if need(S) > pitch0 * 1.01:
        ctx.over.append("harvey table")
    ball = _length(ctx, th.harvey_size, body.w, round(min(pitch0, colw) * th.harvey_ratio))
    ball = max(min(ball, pitch0, colw), 1)
    pitch = min(pitch0, max(round(max(need(S), ball) * 2.0), 1))
    y0 = body.y + (body.h - pitch * nr) // 2
    st_head = base.merged(fast_style(font_size=S, padding="0pt", valign="middle", align="center", bold=True))
    st_lab = base.merged(fast_style(font_size=S, padding="0pt", valign="middle", align="left"))
    lw_pt = th.harvey_line_w
    for r in range(nr):
        y = y0 + r * pitch
        if band and r >= tab.header_rows and (r - tab.header_rows) % 2 == 0:
            ctx.emit(
                Shape(shape="rect", id="rule"),
                Rect(body.x, y, body.w, pitch),
                fast_style(fill=band, line=None),
            )
        row = tab.rows[r]
        if label_col and row and row[0].paragraphs:
            name = f"Harvey head {r + 1}" if r < tab.header_rows else f"Harvey row {r + 1}"
            ctx.emit(
                _text_el(
                    name, [p.model_copy(update={"marker": None}) for p in row[0].paragraphs], "harvey-label"
                ),
                Rect(body.x, y, head_w, pitch),
                st_head.merged(fast_style(align="left"))
                if r >= tab.header_rows
                else st_lab.merged(fast_style(bold=True)),
            )
        for c in range(c0, nc):
            cx = body.x + head_w + (c - c0) * colw
            if r < tab.header_rows:
                if c < len(row) and row[c].paragraphs:
                    ctx.emit(
                        _text_el(f"Harvey col {c + 1}", list(row[c].paragraphs), "harvey-head"),
                        Rect(cx, y, colw, pitch),
                        st_head,
                    )
                continue
            v = cells.get((r, c))
            rect = Rect(cx + (colw - ball) // 2, y + (pitch - ball) // 2, ball, ball)
            if isinstance(v, str):
                if v:
                    ctx.emit(
                        _text_el(
                            f"Harvey text {r + 1},{c + 1}", [Paragraph(runs=[Run(text=v)])], "harvey-text"
                        ),
                        Rect(cx, y, colw, pitch),
                        st_head.merged(fast_style(bold=False)),
                    )
                continue
            if v is None:
                continue
            q = v
            ctx.emit(
                _shape_el(f"Harvey {r + 1},{c + 1} q{q}", "harvey-ball", "ellipse"),
                rect,
                fast_style(fill=fill if q == 4 else "bg", line=line or fill, line_width=lw_pt),
            )
            if 0 < q < 4:
                start = 270.0
                ctx.emit(
                    _shape_el(
                        f"Harvey {r + 1},{c + 1} pie",
                        "harvey-pie",
                        "pie",
                        pie_start=start,
                        pie_end=(start + 90.0 * q) % 360,
                    ),
                    rect,
                    fast_style(fill=fill, line=None),
                )
    return True


# --------------------------------------------------------------------------- @pins

_PIN_KEY = re.compile(r"^\s*([xy])\s*=\s*(\d+(?:\.\d+)?)(%?)\s*")


def _pin_items(paras: list[Paragraph]) -> list[tuple[float | None, float | None, list[Run]]]:
    out = []
    for p in paras:
        runs, xy = list(p.runs), {}
        for _ in range(2):
            m = _PIN_KEY.match("".join(r.text for r in runs))
            if not m:
                break
            v = float(m.group(2))
            xy[m.group(1)] = v / 100.0 if (m.group(3) or v > 1.0 or "." not in m.group(2)) else v
            runs = _strip_runs(runs, _PIN_KEY)
        out.append((xy.get("x"), xy.get("y"), _lstrip(runs)))
    return out


def _image_size(ctx, src: str) -> tuple[int, int] | None:
    if "://" in src or src.startswith("data:") or src.lower().endswith(".svg"):
        return None
    p = Path(src).expanduser()
    if not p.is_absolute():
        p = Path(str(ctx.deck.attrs.get("base_dir", "."))) / p
    try:
        from PIL import Image as PILImage

        with PILImage.open(p) as im:
            return im.size
    except Exception:
        return None


def _pins(ctx, slide: Slide, body: Rect, sg: int) -> bool:
    E, th = _E(), ctx.theme
    img = next((e for e in slide.elements if isinstance(e, Image)), None)
    if img is None:
        ctx.diag(
            "form-empty", "@pins needs an image", "write ![map](map.png) and a list: - x=32% y=58% Tokyo"
        )
        return False
    _others(ctx, slide, (Image, Text), "pins")
    items = _pin_items([p for t in _flat_texts(slide) for p in t.paragraphs if p.runs])
    if not items:
        ctx.diag(
            "form-empty",
            "@pins has no pins",
            "write a list: - x=32% y=58% Tokyo (positions are % of the image)",
        )
    legend = str(slide.attrs.get("legend") or th.pins_legend).lower()
    if legend not in ("right", "bottom", "off"):
        _bad(ctx, "legend", legend)
        legend = "right"
    base = _base(ctx)
    gutter = E._gap(ctx, slide.attrs.get("gap"), body.w)
    n = len(items)
    pinned = _attr_size(ctx, slide)
    fill = _paint(
        ctx, slide.attrs.get("fill") if "fill" in slide.attrs else th.pins_fill, "accent", "pins.fill"
    )
    num_col = _paint(ctx, th.pins_color, None, "pins.color") or th.ink_on(fill, "bg")

    def regions(leg_w: int, leg_h: int) -> tuple[Rect, Rect | None]:
        if legend == "right" and items:
            return Rect(body.x, body.y, body.w - leg_w - gutter, body.h), Rect(
                body.right - leg_w, body.y, leg_w, body.h
            )
        if legend == "bottom" and items:
            return Rect(body.x, body.y, body.w, body.h - leg_h - gutter), Rect(
                body.x, body.bottom - leg_h, body.w, leg_h
            )
        return body, None

    cap = pinned or _grow_cap(ctx, base.font_size or 18)
    leg_w = round(body.w * th.pins_legend_w)
    S = pinned or cap
    leg_h = 0
    pin_d_for = lambda S_: _pt(S_ * 1.5)  # noqa: E731 - the legend badge follows the legend text

    def legend_need(S_: float, region_w: int, cols: int = 1) -> int:
        st = base.merged(fast_style(font_size=S_, padding="0pt"))
        bd = pin_d_for(S_)
        tw = (region_w - gutter * (cols - 1)) // cols - bd - _pt(S_ * 0.6)
        hs = [max(round(_need([Paragraph(runs=r)], st, tw)), bd) for _x, _y, r in items]
        rows_ = math.ceil(n / cols)
        return sum(max(hs[i * cols : (i + 1) * cols]) for i in range(rows_)) + sg * (rows_ - 1)

    if legend != "off" and items:
        for S in [pinned] if pinned else _sizes(ctx, cap):
            if legend == "right":
                if legend_need(S, leg_w) <= body.h:
                    break
            else:
                cols_ = min(n, 3)
                leg_h = legend_need(S, body.w, cols_)
                if leg_h <= body.h * 0.3:
                    break
        if legend == "bottom":
            leg_h = legend_need(S, body.w, min(n, 3))
    img_region, leg_region = regions(leg_w, leg_h)
    dims = _image_size(ctx, img.src)
    if dims:
        k = min(img_region.w / dims[0], img_region.h / dims[1])
        iw, ih = round(dims[0] * k), round(dims[1] * k)
    else:
        iw, ih = img_region.w, img_region.h
    ix = img_region.x + (img_region.w - iw) // 2
    iy = img_region.y + (img_region.h - ih) // 2
    ctx.emit(img.model_copy(update={"fit": "contain"}), Rect(ix, iy, iw, ih), Style())
    d = _length(ctx, th.pins_size, min(iw, ih), round(min(iw, ih) * th.pins_ratio))
    d = max(d, _pt(th.min_font_size * 1.6))
    num_st = base.merged(
        fast_style(
            font_size=max(round(d / EMU_PER_PT * 0.5, 2), th.min_font_size),
            fill=fill,
            color=num_col,
            line=None,
            bold=True,
            align="center",
            valign="middle",
            padding="0pt",
        )
    )
    for i, (fx, fy, _runs) in enumerate(items):
        if fx is None or fy is None or not (0 <= fx <= 1 and 0 <= fy <= 1):
            ctx.diag(
                "pins-position",
                f"pin {i + 1} has no valid x= y= position",
                "write both as % of the image: - x=32% y=58% Tokyo",
            )
            continue
        cx, cy = ix + round(iw * fx), iy + round(ih * fy)
        ctx.emit(
            _shape_el(
                f"Pin {i + 1}", "pins-pin", "ellipse", [Paragraph(runs=[Run(text=str(i + 1), bold=True)])]
            ),
            Rect(cx - d // 2, cy - d // 2, d, d),
            num_st,
        )
    if leg_region is not None:
        lst = base.merged(fast_style(font_size=S, padding="0pt", valign="middle", align="left"))
        bd = pin_d_for(S)
        cols_ = 1 if legend == "right" else min(n, 3)
        cw_ = (leg_region.w - gutter * (cols_ - 1)) // cols_
        tw_ = cw_ - bd - _pt(S * 0.6)
        hs = [max(round(_need([Paragraph(runs=r)], lst, tw_)), bd) for _x, _y, r in items]
        rows_ = math.ceil(n / cols_)
        rh = [max(hs[r * cols_ : (r + 1) * cols_]) for r in range(rows_)]
        total = sum(rh) + sg * (rows_ - 1)
        y = leg_region.y + max((leg_region.h - total) // 2, 0) if legend == "right" else leg_region.y
        for r in range(rows_):
            for c in range(cols_):
                i = r * cols_ + c
                if i >= n:
                    break
                x = leg_region.x + c * (cw_ + gutter)
                ctx.emit(
                    _shape_el(
                        f"Pin {i + 1} legend",
                        "pins-legend-num",
                        "ellipse",
                        [Paragraph(runs=[Run(text=str(i + 1), bold=True)])],
                    ),
                    Rect(x, y + (rh[r] - bd) // 2, bd, bd),
                    num_st.merged(fast_style(font_size=max(round(S * 0.8, 2), th.min_font_size))),
                )
                ctx.emit(
                    _text_el(f"Pins legend {i + 1}", [Paragraph(runs=items[i][2])], "pins-legend"),
                    Rect(x + bd + _pt(S * 0.6), y, tw_, rh[r]),
                    lst,
                )
            y += rh[r] + sg
        if total > leg_region.h * 1.01:
            ctx.over.append("pins legend")
    return True


_COMPOSERS: dict[str, Callable[..., bool]] = {
    "iconlist": _iconlist,
    "quote": _quote,
    "proscons": _proscons,
    "progress": _progress,
    "harvey": _harvey,
    "pins": _pins,
}


# --------------------------------------------------------------------------- fit line


def fit_part(
    slide: Slide, kind: str, inner: list[Placed], fit: dict[str, Any]
) -> tuple[str, list[str]] | None:
    """``(name, facts)`` of a composed form for the fit map, read off the placed shapes (None = not one)."""
    word = F.word_of(slide.classes)
    if word is None:
        return None

    def named(prefix: str) -> list[Placed]:
        return [
            p
            for p in inner
            if isinstance(p.element, (Text, Shape, Container))
            and str(p.element.attrs.get("shape_name", "")).startswith(prefix)
        ]

    def size(ps: list[Placed]) -> str:
        sz = [p.style.font_size * p.font_scale for p in ps if p.style.font_size]
        return f"{round(max(sz))}pt" if sz else ""

    label = F.FIT_NAMES[word]
    if word == "iconlist":
        t = [p for p in named("Iconlist ") if str(p.element.attrs["shape_name"]).count(" ") == 1]
        cols = len({p.x for p in t}) or 1
        return f"{label} {len(t)} items in {cols} col{'s' if cols != 1 else ''} {size(t)}".rstrip(), []
    if word == "quote":
        t = named("Quote text")
        return f"{label} {size(t)}".rstrip(), []
    if word == "split":
        return f"split {fit.get('split', '')}".rstrip(), []
    if word == "proscons":
        cards = [p for p in named("Proscons ") if isinstance(p.element, Container)]
        its = [
            p
            for p in named("Proscons ")
            if str(p.element.attrs["shape_name"]).split(" item ")[-1].isdigit()
            and " item " in str(p.element.attrs["shape_name"])
        ]
        return f"{label} {len(cards)} boxes, {len(its)} items {size(its)}".rstrip(), []
    if word == "progress":
        fills = named("Progress ")
        bars = [p for p in fills if str(p.element.attrs["shape_name"]).endswith(" label")]
        return f"{label} {len(bars)} bars {size(bars)}".rstrip(), []
    if word == "harvey":
        balls = [p for p in named("Harvey ") if re.search(r" q\d$", str(p.element.attrs["shape_name"]))]
        return f"{label} {len(balls)} balls", []
    if word == "heatmap":
        for p in inner:
            if isinstance(p.element, Table) and p.element.attrs.get("heatmap"):
                lo, hi = str(p.element.attrs["heatmap"]).split(";")[:2]
                return (
                    f"{label} {len(p.element.rows)}x{max(len(r) for r in p.element.rows)}, scale {lo}..{hi}",
                    [],
                )
        return None
    if word == "pins":
        pins = [p for p in named("Pin ") if str(p.element.attrs["shape_name"]).count(" ") == 1]
        return f"{label} {len(pins)} pins", []
    return None
