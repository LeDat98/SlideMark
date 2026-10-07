"""Layout linter: checks the placed items of every slide and returns one-line ``Diagnostic``s.

Rules (all warnings, cheap to read for an agent):

- ``overflow``: text needs more height than its box, even at the autofit scale.
- ``off-slide``: an item extends past the slide edge.
- ``overlap``: two items overlap (one fully inside another, e.g. a heading in its card, is fine).
- ``contrast``: the drawn text color (paragraph, run, badge ink) vs the fill behind it is below WCAG 3:1;
  the hint names the token to change and a passing value.
  Table cells (header, first column, body, banded rows) and chart text (title, legend, axis and data
  labels) are judged at 4.5:1 (3:1 for large text), one warning per table / chart and kind.
- ``tiny-text``: text renders below the theme's minimum font size.
- ``alt``: an image without alt text.
- ``connector-crosses``: a connector runs through a block that is not one of its ends.
- ``design-none`` / ``design-slide``: header lines not stated / slides short of a form, one emphasis or values
  (deck-level, see ``design.py``; added by ``lint_deck``, not by ``lint``).
- ``attr-ignored``: an attribute or ``style:`` token the layout does not honour where it was written
  (``honour.py``; added by ``lint_deck``).
"""

from __future__ import annotations

import re

from .contrast import nearest_passing
from .contrast import ratio as _ratio
from .design import design_diagnostics
from .honour import honour_diagnostics
from .ir import Chart, Container, Deck, Diagnostic, Image, Media, Placed, Shape, Table, Text
from .layout import css, measure
from .layout.chartnote import chart_size, opt_pt
from .layout.tablehl import hl_cell, hl_rows
from .layout.tables import table_grid
from .theme import Theme, slide_theme
from .units import EMU_PER_PT, slide_size, to_emu

_TOL = int(EMU_PER_PT)  # 1pt slack for rounding
_OVERFLOW_TOL = 1.08  # measurement is an estimate: report only clear overflows


RGB = tuple[float, float, float]
_GRADIENT = re.compile(r"^\s*(?:repeating-)?(?:linear|radial)-gradient\(", re.I)
_RGBFN = re.compile(r"rgba?\(\s*([\d.]+%?)[\s,]+([\d.]+%?)[\s,]+([\d.]+%?)(?:[\s,/]+([\d.]+%?))?\s*\)", re.I)


def _rgba(color: str | None, theme: Theme) -> tuple[RGB, float] | None:
    """(rgb 0..1, alpha) of a theme color name, #hex (3-8 digits) or rgb()/rgba(); None if unknown."""
    c = (theme.color(color) if color else None) or ""
    c = c.strip()
    try:
        if c.startswith("#"):
            h = c[1:]
            if len(h) in (3, 4):
                h = "".join(ch * 2 for ch in h)
            if len(h) not in (6, 8):
                return None
            rgb = tuple(int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))
            return rgb, (int(h[6:8], 16) / 255 if len(h) == 8 else 1.0)  # type: ignore[return-value]
        if m := _RGBFN.fullmatch(c):

            def ch(v: str) -> float:
                return min(max(float(v[:-1]) * 2.55 if v.endswith("%") else float(v), 0), 255) / 255

            a = m.group(4)
            alpha = (float(a[:-1]) / 100 if a.endswith("%") else float(a)) if a else 1.0
            return (ch(m.group(1)), ch(m.group(2)), ch(m.group(3))), min(max(alpha, 0.0), 1.0)
    except ValueError:
        return None
    return None


def _hex(color: str | None, theme: Theme) -> RGB | None:
    got = _rgba(color, theme)
    return got[0] if got else None


def _top_commas(text: str) -> list[str]:
    out, depth, cur = [], 0, []
    for ch in text:
        depth += (ch == "(") - (ch == ")")
        if ch == "," and depth == 0:
            out.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    out.append("".join(cur).strip())
    return [p for p in out if p]


def _blend(top: tuple[RGB, float], behind: RGB | None) -> RGB:
    rgb, a = top
    if a >= 1.0 or behind is None:
        return rgb
    return tuple(r * a + b * (1 - a) for r, b in zip(rgb, behind, strict=True))  # type: ignore[return-value]


def _backs(fill: str | None, theme: Theme, behind: RGB | None) -> list[RGB]:
    """Colors a fill puts behind text: one for a solid color, one per gradient stop (alpha blended over
    ``behind``). Empty when it cannot be judged (an image, an unknown value) or the fill is transparent."""
    if not fill:
        return []
    if _GRADIENT.match(fill):
        inner = fill.strip()[fill.index("(") + 1 :].rstrip().removesuffix(")")
        stops = []
        for part in _top_commas(inner):
            if re.match(
                r"^(-?[\d.]+(deg|rad|turn|grad)|to\s|circle|ellipse|closest|farthest|at\s)", part, re.I
            ):
                continue
            got = _rgba(re.sub(r"\s+-?[\d.]+(%|px|pt)$", "", part), theme)
            if got:
                stops.append(_blend(got, behind))
        return stops
    got = _rgba(fill, theme)
    if got is None or got[1] <= 0:
        return []
    return [_blend(got, behind)]


def _luminance(rgb: tuple[float, float, float]) -> float:
    def ch(v: float) -> float:
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = (ch(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _hexs(rgb: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{round(min(max(v, 0.0), 1.0) * 255):02X}" for v in rgb)


# Text role -> the selector of its color token (`style: <selector>.color=#RRGGBB`)
_COLOR_SELECTOR = {
    "title": "title",
    "heading": "heading",
    "lead": "lead",
    "conclusion": "conclusion",
    "subtitle": "subtitle",
    "footnote": "footnote",
    "caption": "footnote",
    "body": "p",
    "quote": "p",
}


def _in_class(items: list[Placed], i: int, name: str) -> bool:
    """True when item ``i`` sits inside a container with class ``name`` (e.g. the KPI card)."""
    p = items[i]
    cx, cy = p.x + p.w // 2, p.y + p.h // 2
    return any(
        isinstance(q.element, Container)
        and name in q.element.classes
        and q.x <= cx <= q.x + q.w
        and q.y <= cy <= q.y + q.h
        for q in items[:i]
    )


def _fix_hint(
    items: list[Placed],
    i: int,
    p: Placed,
    run,
    color: str | None,
    backs: list[RGB],
    theme: Theme,
    size: float,
    base: str | None,
) -> str:
    """One-line, paste-ready fix: names the token to change and a value that passes."""
    el = p.element
    need = theme.need_for(size)
    back_hex = [_hexs(b) for b in backs]
    band = bool(theme.title_band) and isinstance(el, Text) and el.role in ("title", "subtitle")
    band = band and theme.hexval(theme.title_band) == back_hex[0]
    on_fill = (
        bool(run.highlight) or band or (p.style.fill is not None and _hex(p.style.fill, theme) is not None)
    )
    if on_fill:
        fill = run.highlight or (theme.title_band if band else p.style.fill)
        fh = back_hex[0] if len(back_hex) == 1 else (theme.hexval(fill) or back_hex[0])
        cands = theme.ink_candidates()
        ink = max(cands, key=lambda c: min(_ratio(c, h) for h in back_hex))
        ink = next((c for c in cands if min(_ratio(c, h) for h in back_hex) >= need), ink)
        name = fill if fill in theme.colors else "fill"
        label = f"text on {name} {fh}"
    else:
        ch = theme.hexval(color) or _hexs(_hex("fg", theme) or (0, 0, 0))
        ink = nearest_passing(ch, back_hex, need)
        label = f"set the color to {ink} (passes {need:g}:1 on {back_hex[0]})"
    if run.highlight:
        token = "badge.color"
    elif run.size and run.color and _in_class(items, i, "kpi"):
        token = "kpi.unit.color"  # the unit run of a KPI value
    elif run.color:
        return f"{label}: change the run's color to {{color={ink}}}"
    elif isinstance(el, Text) and base in ("muted", "fg") and not on_fill:
        token = f"colors.{base}"  # one shared color: fix it once for every role, at the stricter 4.5:1
        ink = nearest_passing(theme.hexval(color) or ink, back_hex, theme.render.contrast_min)
        label = f"set the color to {ink} (passes {theme.render.contrast_min:g}:1 on {back_hex[0]})"
    elif _in_class(items, i, "kpi"):
        token = "kpi.color"
    elif band:
        token = "title.band.color"
    elif isinstance(el, Text) and el.role in ("footnote", "caption", "subtitle", "quote"):
        token = "p.color"  # no per-role color token
    elif isinstance(el, Text):
        sel = _COLOR_SELECTOR.get(el.role, "p")
        token = f"{sel}.band.color" if p.style.fill and sel in ("title", "heading") else f"{sel}.color"
    else:
        return f"{label}: add {{color={ink}}} to this block"
    if (
        token.endswith(".color")
        and not on_fill
        and token not in ("kpi.color", "kpi.unit.color")
        and not token.startswith("colors.")
    ):
        # a selector colors text of every size on bg and on cards: suggest one value that passes everywhere
        every = list(dict.fromkeys([*back_hex, *(h for h in theme.surface_backs() if h)]))
        ink = nearest_passing(theme.hexval(color) or ink, every, theme.render.contrast_min)
        label = f"set the color to {ink} (passes {theme.render.contrast_min:g}:1 on {back_hex[0]})"
    return f"{label}: style: {token}={ink}"


def _contrast_findings(
    items: list[Placed], i: int, p: Placed, backs: list[RGB], theme: Theme
) -> list[tuple[str, str]]:
    """(message, hint) per distinct drawn color of the text item that is unreadable (< 3:1) on its back."""
    out: list[tuple[str, str]] = []
    seen: set[tuple[str | None, str | None]] = set()
    for q in p.element.paragraphs:  # type: ignore[attr-defined]
        pst = p.style.merged(q.style) if q.style else p.style
        size = (pst.font_size or theme.sizes.get("body", 18)) * p.font_scale
        for r in q.runs:
            if not r.text.strip():
                continue
            col = theme.run_color(r.color, r.highlight, pst.color or "fg", size, p.style.fill)
            if (col, r.highlight) in seen:
                continue
            seen.add((col, r.highlight))
            use = _backs(r.highlight, theme, None) if r.highlight else backs
            fg_c = _rgba(col, theme)
            if not fg_c or not use:
                continue
            alpha = fg_c[1] * (p.style.opacity if p.style.fill is None and p.style.opacity is not None else 1)
            ratios = [contrast_ratio(_blend((fg_c[0], alpha), b), b) for b in use]
            ratio = min(ratios)
            bad = all(x < 3.0 for x in ratios)
            if len(use) > 1:
                mean = tuple(sum(b[k] for b in use) / len(use) for k in range(3))
                ratio = contrast_ratio(_blend((fg_c[0], alpha), mean), mean)  # type: ignore[arg-type]
                bad = bad or ratio < 3.0
            if bad:
                hint = _fix_hint(items, i, p, r, col, use, theme, size, pst.color)
                out.append((f"{_label(p)} has low contrast {ratio:.1f}:1", hint))
    return out


def _table_findings(p: Placed, theme: Theme, behind: list[RGB]) -> list[tuple[str, str]]:
    """(message, hint) per table cell kind (header, first column, body, banded rows) with unreadable text.

    Fills and text styles come from the renderer's own resolvers (``Theme.table_cell_fill`` /
    ``table_cell_style`` / ``run_color``); a cell's own CSS fill and opacity paint over them.
    """
    from .render.objects import flag  # lazy: render pulls in python-pptx

    t: Table = p.element  # type: ignore[assignment]
    _rows, _cols, anchors = table_grid(t)
    zebra = "zebra" in t.classes or flag(t.attrs.get("zebra"))
    body_fill = theme.table_body_fill_of(p.style.fill)
    hl = hl_cell(t)
    rows_hl = hl_rows(t)
    top = behind[0] if behind else None
    # per kind: (ratio, need, ink, backs, explicit run color, explicit cell color)
    groups: dict[str, list[tuple[float, float, str, list[str], bool, bool]]] = {}
    for r, c, ct in anchors:
        hdr, fcol = r < t.header_rows, c < t.header_cols
        kind = "header" if hdr else "first column" if fcol else "body"
        if kind != "header" and hl(r, c):
            kind = "emphasised rows" if r in rows_hl else "emphasised columns"
        elif kind == "body" and zebra and (r - t.header_rows) % 2 == 1:
            kind = "banded rows"
        fill = theme.table_cell_fill(r, c, t.header_rows, t.header_cols, body_fill, zebra, hl(r, c))
        cst = ct.style
        if cst and cst.fill:
            fill = cst.fill
        if _is_image(fill, theme):
            continue
        backs = _backs(fill, theme, top)
        if cst and cst.opacity is not None and 0 <= cst.opacity < 1:
            backs = [_blend((b, cst.opacity), top) for b in backs]
        st = theme.table_cell_style(
            p.style, hdr, fcol, ct.colspan, cst, theme.table_hl_fill_of(body_fill) if hl(r, c) else None
        )
        for q in ct.paragraphs:
            pst = st.merged(q.style)
            size = (pst.font_size or 18) * p.font_scale
            for run in q.runs:
                if not run.text.strip():
                    continue
                col = theme.run_color(run.color, run.highlight, pst.color, size, pst.fill) or "fg"
                use = _backs(run.highlight, theme, None) if run.highlight else backs
                fg_c = _rgba(col, theme)
                if not fg_c or not use:
                    continue
                need = theme.need_for_text(size, bool(run.bold or pst.bold or run.highlight))
                got = min(contrast_ratio(_blend(fg_c, b), b) for b in use)
                groups.setdefault(kind, []).append(
                    (
                        got,
                        need,
                        _hexs(fg_c[0]),
                        [_hexs(b) for b in use],
                        bool(run.color),
                        bool(cst and cst.color),
                    )
                )
    out = []
    for kind, cells in groups.items():
        bad = [x for x in cells if x[0] < x[1]]
        if not bad:
            continue
        worst = min(bad, key=lambda x: x[0] - x[1])
        # `td.color` colors every non-header kind: one value must pass on all of them
        scope = cells if kind == "header" else [x for k, v in groups.items() if k != "header" for x in v]
        need = max(x[1] for x in scope)
        every = list(dict.fromkeys(h for x in scope for h in x[3]))
        if worst[4]:  # an explicit run color cannot be reached by a token
            ink = nearest_passing(worst[2], worst[3], worst[1])
            fix, where = f"change the run's color to {{color={ink}}}", worst[3]
        else:
            ink = nearest_passing(worst[2], every, need)
            token = ("th.color" if worst[5] else "table.header.color") if kind == "header" else "td.color"
            fix, where = f"style: {token}={ink}", every
        out.append(
            (
                f"table {kind} text has low contrast {worst[0]:.1f}:1 (< {worst[1]:g}:1) on {worst[3][0]}",
                f"{fix} (passes {need:g}:1 on {', '.join(where)})",
            )
        )
    return out


def _chart_findings(p: Placed, theme: Theme, behind: list[RGB]) -> list[tuple[str, str]]:
    """(message, hint) per kind of chart text (title, legend, axis labels, data labels) that is unreadable.

    Colors come from the renderer's own resolvers (``Theme.chart_palette`` / ``chart_label_ink``).
    """
    from .render.axis import label_pt, legend_pt
    from .render.objects import _legend_pos, flag
    from .render.util import hex6

    ch: Chart = p.element  # type: ignore[assignment]
    if not behind:
        return []
    back_hex = [_hexs(b) for b in behind]
    opts = {str(k).lower().replace("-", "_"): v for k, v in ch.options.items()}
    kind = ch.kind
    pie = kind in ("pie", "doughnut")
    rt = theme.render
    size = chart_size(p, theme)
    base = "#" + hex6(theme, p.style.color or "fg")
    series = ch.series
    ncat = max([len(ch.categories), *(len(s.values) for s in series)])
    if pie and len(series) > 1 and len(ch.categories) <= 1 and all(len(s.values) == 1 for s in series):
        ncat = len(series)
    # (label, ink, size, bold, backs it must read on, how the hint fixes it)
    checks: list[tuple[str, str, float, bool, list[str], str]] = []
    if ch.title:
        checks.append(("title", "#" + hex6(theme, "fg"), size * rt.chart_title_scale, True, back_hex, "fg"))
    if _legend_pos(opts, pie, len(series)) is not None:
        checks.append(
            ("legend", base, legend_pt(size, rt, opt_pt(p, "legend_size")), False, back_hex, "chart")
        )
    if not pie:
        checks.append(("axis labels", base, size, False, back_hex, "chart"))
    labels = opts.get("labels", opts.get("data_labels"))
    lab_on = (isinstance(labels, str) and labels.strip().lower() in ("percent", "value")) or flag(labels)
    lexact = opt_pt(p, "label_size")
    lsize = label_pt(kind, ncat, size, rt, lexact) if pie else lexact or size * rt.chart_label_scale
    pal = theme.chart_palette(opts.get("colors"))
    lab_ink = "#" + hex6(theme, opts["label_color"]) if opts.get("label_color") else None  # `labels.color=`
    lab_bold = opts.get("label_bold")  # `labels.bold=`; None = the chart's own default
    if lab_on and kind != "scatter":
        if pie:
            bg = hex6(theme, "bg")
            both = kind == "pie" and str(rt.chart_pie_label_pos).strip().lower() in ("best_fit", "best-fit")
            for i in range(ncat):
                fill = pal[i % len(pal)]
                ink = lab_ink or "#" + theme.chart_label_ink(fill, *([bg] if both else []))
                # Judged on the slice only: a pie label may also land outside it (best fit), where no single
                # ink reads on both a mid-tone slice and the page; the renderer then favors the slice.
                bold = rt.chart_pie_label_bold if lab_bold is None else bool(lab_bold)
                checks.append(("data labels", ink, lsize, bold, ["#" + fill], "labels"))
        elif kind in ("stacked-bar", "stacked-column"):
            for i in range(len(series)):
                fill = pal[i % len(pal)]
                ink = lab_ink or "#" + theme.chart_label_ink(fill)
                checks.append(("data labels", ink, lsize, bool(lab_bold), ["#" + fill], "labels"))
        elif kind in ("column", "bar", "line", "waterfall"):
            checks.append(
                (
                    "data labels",
                    lab_ink or base,
                    lsize,
                    bool(lab_bold),
                    back_hex,
                    "labels" if lab_ink else "chart",
                )
            )
    groups: dict[str, list[tuple[float, float, str, list[str], str]]] = {}
    for label, ink, sz, bold, backs, fix in checks:
        got = min(_ratio(ink, b) for b in backs)
        groups.setdefault(label, []).append((got, theme.need_for_text(sz, bold), ink, backs, fix))
    out = []
    for label, cells in groups.items():
        bad = [x for x in cells if x[0] < x[1]]
        if not bad:
            continue
        got, need, ink, backs, fix = min(bad, key=lambda x: x[0] - x[1])
        if fix == "labels":
            hint = (
                "add {labels=off} to the chart fence, or {colors=...} with slices the label ink can read on"
                + (" (or change labels.color=)" if lab_ink else "")
            )
        else:
            every = list(dict.fromkeys([*back_hex, *backs]))
            new = nearest_passing(ink, every, max(x[1] for x in cells))
            hint = f"colors: fg={new}" if fix == "fg" else f"add {{color={new}}} to the chart fence"
            hint += f" (passes {need:g}:1 on {', '.join(every)})"
        out.append((f"chart {label} have low contrast {got:.1f}:1 (needs {need:g}:1) on {backs[0]}", hint))
    return out


def _label(p: Placed) -> str:
    el = p.element
    paras = getattr(el, "paragraphs", None)
    if paras:
        text = " ".join(q.plain for q in paras).strip()
        if text:
            return f"'{text[:24]}…'" if len(text) > 24 else f"'{text}'"
    if isinstance(el, (Image, Media)):
        return f"{el.type} {el.src}"
    return el.type


def _inside(a: Placed, b: Placed) -> bool:
    """True when ``a`` lies within ``b`` (with tolerance)."""
    return (
        a.x >= b.x - _TOL
        and a.y >= b.y - _TOL
        and a.x + a.w <= b.x + b.w + _TOL
        and a.y + a.h <= b.y + b.h + _TOL
    )


def _overlap_area(a: Placed, b: Placed) -> int:
    w = min(a.x + a.w, b.x + b.w) - max(a.x, b.x)
    h = min(a.y + a.h, b.y + b.h) - max(a.y, b.y)
    return max(w, 0) * max(h, 0)


def _has_text(p: Placed) -> bool:
    return any(getattr(pa, "plain", "").strip() for pa in getattr(p.element, "paragraphs", None) or [])


def _is_line(p: Placed) -> bool:
    return isinstance(p.element, Shape) and p.element.shape in ("line", "arrow-right", "connector")


def _is_band(p: Placed) -> bool:
    """Decoration drawn behind other items (title band, background shapes)."""
    el = p.element
    return isinstance(el, Shape) and not el.paragraphs and el.shape in ("rect", "rounded-rect")


def _is_image(fill: str | None, theme: Theme) -> bool:
    """A fill that is neither a color nor a gradient (``url(...)``, a picture path): not judgeable."""
    return bool(fill) and not _GRADIENT.match(fill or "") and _rgba(fill, theme) is None


def _backdrop(items: list[Placed], i: int, bg: list[RGB], theme: Theme) -> list[RGB]:
    """Colors directly behind item ``i``: the topmost earlier filled item containing its center (a gradient
    gives one color per stop), else the slide background."""
    p = items[i]
    cx, cy = p.x + p.w // 2, p.y + p.h // 2
    for q in reversed(items[:i]):
        if q.style.fill and q.x <= cx <= q.x + q.w and q.y <= cy <= q.y + q.h:
            if _is_image(q.style.fill, theme):
                return []  # a picture behind the text: no verdict
            got = _backs(q.style.fill, theme, bg[0] if bg else None)
            if got:
                return got
    return bg


def _kpi_stripe_backs(items: list[Placed], i: int, p: Placed, theme: Theme) -> list[RGB]:
    """The stripe colour when a KPI card's text sits on ``kpi.stripe`` (a tall stripe is a header band behind
    the label): the card is the backdrop the lint finds, but the stripe is drawn over it by the renderer.
    One colour when the text lies inside the stripe, stripe and card when it only overlaps it."""
    if not theme.kpi_stripe or not isinstance(p.element, Text):
        return []
    card = next(
        (
            q
            for q in reversed(items[:i])
            if isinstance(q.element, Container)
            and "kpi" in q.element.classes
            and q.x <= p.x + p.w // 2 <= q.x + q.w
            and q.y <= p.y + p.h // 2 <= q.y + q.h
        ),
        None,
    )
    if card is None:
        return []
    top = card.y + min(max(to_emu(theme.kpi_stripe_h), 1), card.h)  # bottom edge of the stripe
    over = min(p.y + p.h, top) - max(p.y, card.y)
    stripe = _backs(theme.kpi_stripe, theme, None)
    if over <= 0 or not stripe:
        return []
    if over >= 0.5 * p.h:
        return stripe  # mostly on the stripe: judged against it alone
    return [*stripe, *_backs(card.style.fill, theme, None)]  # partly on it: both must carry the text


def lint_slide(items: list[Placed], deck: Deck, theme: Theme, index: int) -> list[Diagnostic]:
    out: list[Diagnostic] = []
    slide = deck.slides[index] if index < len(deck.slides) else None
    try:
        W, H = slide_size(deck.size)
    except ValueError:
        W, H = slide_size("16:9")

    def warn(rule: str, msg: str, hint: str, p: Placed | None = None) -> None:
        line = getattr(p.element, "line", None) if p else None
        out.append(Diagnostic(level="warning", message=msg, slide=index + 1, line=line, rule=rule, hint=hint))

    base = _hex("bg", theme)
    bg: list[RGB] = []
    if slide:
        fill = slide.background or css.slide_style(deck, slide, index).fill
        bg = _backs(fill, theme, base)
        if _is_image(fill, theme):
            base = None  # a picture background: no verdict for text straight on it
    if not bg and base:
        bg = [base]

    for i, p in enumerate(items):
        el = p.element
        # off-slide
        if p.x < -_TOL or p.y < -_TOL or p.x + p.w > W + _TOL or p.y + p.h > H + _TOL:
            warn(
                "off-slide",
                f"{_label(p)} extends past the slide edge",
                "check its {x y w h} or remove them",
                p,
            )
        # alt text
        if isinstance(el, (Image, Media)) and not el.alt.strip():
            what = "image" if isinstance(el, Image) else el.kind
            warn("alt", f"{what} {el.src} has no alt text", "write ![what it shows](path)", p)
        if isinstance(el, (Table, Chart)):
            find = _table_findings if isinstance(el, Table) else _chart_findings
            for msg, hint in find(p, theme, _backdrop(items, i, bg, theme)):
                warn("contrast", msg, hint, p)
            continue
        paras = getattr(el, "paragraphs", None)
        if not paras or not any(q.plain.strip() for q in paras):
            continue
        size = (p.style.font_size or theme.sizes.get("body", 18)) * p.font_scale
        if size < theme.min_font_size - 0.05:
            warn(
                "tiny-text",
                f"{_label(p)} renders at {size:.1f}pt (< {theme.min_font_size:g}pt)",
                "shorten the text or split the slide",
                p,
            )
        # overflow (text frames only; shapes like chevrons carry short labels)
        if isinstance(el, Text) and p.h > 0 and el.attrs.get("measured") != "html":  # Chromium measured it
            ph, pv = css.inset_hv(p.style)
            need = (
                measure.paragraphs_height(paras, p.w - ph, p.style, p.font_scale, gap=measure.element_gap(el))
                + pv
            )
            if need > p.h * _OVERFLOW_TOL + _TOL:
                warn(
                    "overflow",
                    f"{_label(p)} needs {need / EMU_PER_PT:.0f}pt but has {p.h / EMU_PER_PT:.0f}pt",
                    "shorten the text, split the slide, or give the block more room (@ ratios)",
                    p,
                )
        # contrast
        # Judged on the colors actually drawn (CSS, paragraph and run colors, badge ink: `Theme.run_color`).
        # A gradient is checked against every stop and reported only when the text fails on all of them or
        # on their average; custom colors are never odd, only unreadable ones are reported.
        backdrop = _backdrop(items, i, bg, theme)
        backs = _backs(p.style.fill, theme, backdrop[0] if backdrop else None) or backdrop
        if _is_image(p.style.fill, theme):
            backs = []  # a picture fill cannot be judged
        elif not p.style.fill and (stripe := _kpi_stripe_backs(items, i, p, theme)):
            backs = stripe
        if {"rows-glyph", "quote-mark"} & set(getattr(el, "classes", ())):
            continue  # the glyph of an `@rows plain` bar is a marker like a list bullet: not judged as text
        for msg, hint in _contrast_findings(items, i, p, backs, theme):
            warn("contrast", msg, hint, p)

    # overlap between items that are not nested in each other
    free = slide is not None and slide.layout == "free"
    solid = [p for p in items if not _is_line(p) and not _is_band(p) and p.w > 0 and p.h > 0]
    for a_i, a in enumerate(solid):
        for b in solid[a_i + 1 :]:
            area = _overlap_area(a, b)
            if area <= 0 or _inside(a, b) or _inside(b, a):
                continue
            if free and not (_has_text(a) and _has_text(b)):
                continue  # @free: shapes under text are a design choice
            small = min(a.w * a.h, b.w * b.h)
            if small and area / small > 0.02:
                warn(
                    "overlap",
                    f"{_label(a)} overlaps {_label(b)}",
                    "remove explicit {x y w h} or use an @ grid so blocks do not collide",
                    b,
                )
    for _line, block in _connector_crossings(items):
        warn(
            "connector-crosses",
            f"a connector runs through {_label(block)}",
            "link neighbouring blocks only, or reorder the blocks / use an @ areas grid",
            block,
        )
    return out


def _polyline(p: Placed) -> list[tuple[float, float]]:
    """Points of a connector ``Shape(shape="line")`` from its box, flips and elbow attrs."""
    a = p.element.attrs
    x0, x1 = (p.x + p.w, p.x) if a.get("flip_h") else (p.x, p.x + p.w)
    y0, y1 = (p.y + p.h, p.y) if a.get("flip_v") else (p.y, p.y + p.h)
    if not a.get("elbow"):
        return [(x0, y0), (x1, y1)]
    adj = float(a.get("adj", 0.5))
    if a.get("route") == "h":
        xm = x0 + (x1 - x0) * adj
        return [(x0, y0), (xm, y0), (xm, y1), (x1, y1)]
    ym = y0 + (y1 - y0) * adj
    return [(x0, y0), (x0, ym), (x1, ym), (x1, y1)]


def _seg_hits(u, v, r: tuple[int, int, int, int]) -> bool:
    """Liang-Barsky: does segment u-v enter the open rectangle r = (x, y, w, h)?"""
    x, y, w, h = r
    if w <= 0 or h <= 0:
        return False
    dx, dy = v[0] - u[0], v[1] - u[1]
    t0, t1 = 0.0, 1.0
    for pv, qv in ((-dx, u[0] - x), (dx, x + w - u[0]), (-dy, u[1] - y), (dy, y + h - u[1])):
        if pv == 0:
            if qv <= 0:
                return False
            continue
        t = qv / pv
        if pv < 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 >= t1:
            return False
    return True


def _connector_crossings(items: list[Placed]) -> list[tuple[Placed, Placed]]:
    inset = 3 * _TOL
    blocks = [
        q
        for q in items
        if isinstance(q.element, Container) or (isinstance(q.element, Shape) and q.element.paragraphs)
    ]
    out = []
    for p in items:
        if not (isinstance(p.element, Shape) and p.element.shape == "line"):
            continue
        pts = _polyline(p)
        for q in blocks:
            if _inside(p, q):  # the connector's own parent box (links between a box's children)
                continue
            r = (q.x + inset, q.y + inset, q.w - 2 * inset, q.h - 2 * inset)
            if any(_seg_hits(u, v, r) for u, v in zip(pts, pts[1:], strict=False)):
                out.append((p, q))
                break
    return out


def lint(deck: Deck, placed: list[list[Placed]], theme: Theme) -> list[Diagnostic]:
    """Lint every slide. ``placed[i]`` is the layout output of slide ``i``."""
    out: list[Diagnostic] = []
    measure.set_tokens(theme.layout)
    for i, items in enumerate(placed):
        try:
            slide_th = slide_theme(theme, deck.slides[i]) if i < len(deck.slides) else theme
            out.extend(lint_slide(items, deck, slide_th, i))
        except Exception as e:  # the linter must never break a build
            out.append(
                Diagnostic(
                    level="info",
                    message=f"lint skipped: {type(e).__name__}: {e}",
                    slide=i + 1,
                    rule="lint-error",
                    hint="report a bug",
                )
            )
    return out


def lint_deck(deck: Deck, placed: list[list[Placed]], theme: Theme) -> list[Diagnostic]:
    """``lint`` plus the deck-level design feedback (what ``build``, ``check`` and ``review`` report)."""
    return [*lint(deck, placed, theme), *design_diagnostics(deck), *honour_diagnostics(deck, placed, theme)]
