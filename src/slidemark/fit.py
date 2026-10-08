"""The per-slide fit map of ``slidemark build``: how each slide came out, without opening an image (AC7).

A deciding agent that has stated its choices (``{.hero}``, ``kpi.value.size=48``, ``{size=44}``) renders the
deck to see whether they took effect, what form the slide got and how much of it is empty. One short line per
slide answers that from the layout result (the ``Placed`` items plus the few facts the layout left in
``deck.attrs["_fit"]``: the body rectangle and the sizes that were asked for). No second layout, no render.

    slide 2: lead + 4 kpi (hero) cards 46% of body, value 48->40pt (shrunk to fit), free 31% below
    slide 5: steps 4, arrows + cards fill 90%, card text 14->24pt (grown)
    slide 6: table 5x4 at 13->18pt (grown) + conclusion bar attached
    slide 11: line chart, 3 series, labels on, hl=北米

Each line says the form actually used, text sizes reached (``asked->reached`` when they differ), the free
space in the body (below / beside the content), and which author attributes took effect or were ignored
(``took size=44, ignored h y``; the ``attr-ignored`` warnings carry the hints). On by default; ``--quiet``
or the header line ``fit: off`` turns it off.

A slide whose body stays more than ``layout.sparse_note`` empty after every growth pass (text growth stops at
``layout.grow_max``) ends its line with ``sparse: 42% free`` instead of the plain free-space fact, and gets
one ``sparse`` info diagnostic (``sparse_findings``): a composition cue (merge, add a figure, change the
form), never a size cue. Both read the same number.
"""

from __future__ import annotations

from typing import Any

from .forms2 import WORDS as COMPOSED
from .forms2 import word_of
from .honour import audit
from .ir import Chart, Code, Container, Deck, Diagnostic, Image, Media, Placed, Raw, Shape, Table, Text
from .layout.forms2 import fit_part
from .theme import DEFAULT_SIZES, Theme
from .units import EMU_PER_INCH, EMU_PER_PT

FREE_MIN = 0.10  # free space below this share of the body is not worth a word
FREE_ABOVE = 0.20  # ... and the band above a centred block is named only when it is this large
SIZE_TOL = 0.04  # a text size within 4% of what was asked counts as the asked size
_CHROME_ROLES = {"title", "subtitle", "lead", "conclusion", "footnote", "caption"}
_CHROME_SHAPES = {"band", "rule"}


# --------------------------------------------------------------------------- helpers


def _chrome(p: Placed) -> bool:
    el = p.element
    if isinstance(el, Text):
        return el.role in _CHROME_ROLES
    return isinstance(el, Shape) and el.id in _CHROME_SHAPES


def _inside(a: Placed, b: Placed) -> bool:
    """``a`` lies within ``b`` (b larger)."""
    tol = round(EMU_PER_PT)
    return (
        a is not b
        and b.x - tol <= a.x
        and b.y - tol <= a.y
        and a.x + a.w <= b.x + b.w + tol
        and a.y + a.h <= b.y + b.h + tol
        and (b.w * b.h) > (a.w * a.h)
    )


def _pt(p: Placed) -> float | None:
    """The size (pt) the first paragraph with text is drawn at: merged style size x autofit / growth scale."""
    el = p.element
    for para in getattr(el, "paragraphs", None) or []:
        if para.plain.strip():
            size = (
                para.style.font_size if para.style and para.style.font_size else None
            ) or p.style.font_size
            return float(size or 18) * p.font_scale
    size = p.style.font_size
    return float(size) * p.font_scale if size else None


def _size(reached: float | None, asked: float | None = None) -> str:
    """``18pt``, or ``14->24pt (grown)`` when the layout moved the size away from what was asked."""
    if reached is None:
        return ""
    r = f"{round(reached)}pt"
    if asked and abs(reached - asked) / asked > SIZE_TOL:
        verb = "shrunk to fit" if reached < asked else "grown"
        return f"{round(asked)}->{round(reached)}pt ({verb})"
    return r


def _asked(theme: Theme, role: str, dense_k: float, explicit: float | None = None) -> float:
    return explicit or float(theme.sizes.get(role, DEFAULT_SIZES.get(role, DEFAULT_SIZES["body"]))) * dense_k


def _n(n: int, one: str, many: str | None = None) -> str:
    return f"{n} {one if n == 1 else many or one + 's'}"


def _share(x: float) -> int:
    return round(min(max(x, 0.0), 1.0) * 100)


def _free(body: list[int] | None, items: list[Placed]) -> str | None:
    """``free 31% below`` / ``free 22% right`` / ``free 18% beside``: the empty part of the body."""
    from .layout.engine import _content_bottom

    if not body or not items or body[2] <= 0 or body[3] <= 0:
        return None
    bx, by, bw, bh = body
    bottom = _content_bottom(items)
    below = (by + bh - bottom) / bh
    left = (min(p.x for p in items) - bx) / bw
    right = (bx + bw - max(p.x + p.w for p in items)) / bw
    above = (min(p.y for p in items) - by) / bh
    if below >= FREE_MIN:
        return (
            f"free {_share(above)}% above, " if above >= FREE_MIN else "free "
        ) + f"{_share(below)}% below"
    if left >= FREE_MIN and right >= FREE_MIN:
        return f"free {_share(left + right)}% beside"
    if right >= FREE_MIN:
        return f"free {_share(right)}% right"
    if left >= FREE_MIN:
        return f"free {_share(left)}% left"
    return "fills body" if below < 0.05 else None


def _free_share(body: list[int] | None, items: list[Placed]) -> float | None:
    """The share of the body rectangle outside the bounding box of the content (0..1), or ``None``."""
    from .layout.engine import _content_bottom

    if not body or not items or body[2] <= 0 or body[3] <= 0:
        return None
    bx, by, bw, bh = body
    left, right = max(min(p.x for p in items), bx), min(max(p.x + p.w for p in items), bx + bw)
    top, bottom = max(min(p.y for p in items), by), min(_content_bottom(items), by + bh)
    return 1.0 - max(right - left, 0) * max(bottom - top, 0) / (bw * bh)


# the `sparse` info: (rule, message, hint); the fit-line suffix and the diagnostic read one share
SPARSE = (
    "sparse",
    "slide {n} is sparse ({pct}% free)",
    "merge it into a neighbour, add a figure/table/chart, or change its form (@rows, @items, @steps, side by "
    "side); bigger text is capped by layout.grow_max={cap:g}",
)


def _first_text(items: list[Placed], within: list[Placed] | None = None) -> Placed | None:
    for p in items:
        if isinstance(p.element, Text) and p.element.role == "body" and p.element.paragraphs:
            if within is None or any(_inside(p, c) for c in within):
                return p
    return None


# --------------------------------------------------------------------------- chunks


def _kpi(cards: list[Placed], items: list[Placed], body: list[int] | None, asked: dict, theme: Theme):
    hero = any("hero" in c.element.classes for c in cards)
    h = max(c.h for c in cards)
    name = f"{len(cards)} kpi{' (hero)' if hero else ''} {'card' if len(cards) == 1 else 'cards'}"
    if body and body[3]:
        name += f" {_share(h / body[3])}% of body"
    facts = []
    values = [
        _pt(p)
        for p in items
        if isinstance(p.element, Text)
        and p.element.role == "body"
        and p.element.paragraphs
        and p.element.attrs.get("shape_name") != "KPI caption"  # `kpi.rule` splits the caption off
        and any(_inside(p, c) for c in cards)
    ]
    values = [v for v in values if v]
    if values:
        lo, hi = min(values), max(values)
        facts.append("value " + _size(lo, asked.get("kpi_value")))
        if hi > lo * (1 + SIZE_TOL):  # a hero card carries a bigger number than the rest of the row
            facts.append(f"hero {round(hi)}pt")
    return name, facts


def _steps(arrows: list[Placed], cards: list[Placed], items, body, theme, dense_k):
    name = f"steps {len(arrows)}"
    facts = []
    if cards and body and body[3]:
        top = min(a.y for a in arrows)
        facts.append(f"arrows + cards fill {_share((max(c.y + c.h for c in cards) - top) / body[3])}%")
    txt = _first_text(items, cards)
    if txt is not None:
        facts.append("card text " + _size(_pt(txt), _asked(theme, "body", dense_k)))
    return name, facts


def _chevron(row: list[Placed], theme: Theme):
    return f"chevron {len(row)} (compact)", [f"text {round(_pt(row[0]) or 0)}pt"]


def _boxes(cards: list[Placed], items, theme, dense_k):
    rows = len({round(c.y / max(c.h, 1) * 2) for c in cards})
    cols = len({round(c.x / max(c.w, 1) * 2) for c in cards})
    shape = "row" if rows == 1 else "stack" if cols == 1 else f"{cols}x{rows}"
    name = f"{_n(len(cards), 'box', 'boxes')} ({shape})"
    facts = []
    txt = _first_text(items, cards)
    if txt is not None:
        facts.append("text " + _size(_pt(txt), _asked(theme, "body", dense_k)))
    return name, facts


def _table(p: Placed, theme, dense_k):
    t: Table = p.element
    cols = max((sum(c.colspan for c in r) for r in t.rows), default=0)
    asked = _asked(theme, "table", dense_k, t.style.font_size if t.style is not None else None)
    base = p.style.font_size
    reached = float(base) * p.font_scale if base else None
    extra = []
    if "zebra" in t.classes:
        extra.append("zebra")
    if t.attrs.get("hl"):
        extra.append(f"hl {_n(len(t.attrs['hl']), 'row')}")
    return f"table {len(t.rows)}x{cols} at {_size(reached, asked)}", extra


def _chart(c: Chart):
    o = c.options
    facts = []
    if o.get("labels"):
        facts.append(f"labels {o['labels']}")
    hl = o.get("hl") or o.get("hl_series")
    if hl:
        facts.append("hl=" + ",".join(str(x) for x in hl))
    if o.get("note"):
        facts.append("note")
    n = len(c.series)
    return f"{c.kind} chart, {n} series{'' if n != 1 else ''}", facts


def _vocab(v: dict, theme: Theme, dense_k: float):
    """The line of a composition form (``@timeline`` ...): its name with the choices that took effect and the
    text sizes (``asked->reached`` when the layout moved them)."""
    form, n = v.get("form", "form"), v.get("n")
    asked = v.get("base") or _asked(theme, "body", dense_k)
    text = ("text " + _size(v.get("size"), asked)) if v.get("size") else "no body text"
    if form == "timeline":
        return f"timeline {n} ({v.get('dir')}, marks {v.get('marks')})", [text]
    if form == "vs":
        extra = (["verdict bar"] if v.get("verdict") else []) + (["winner marked"] if v.get("win") else [])
        return "vs 2 sides", [*extra, text]
    if form == "matrix":
        axes = v.get("axes") or 0
        return "matrix 2x2" + (f", {_n(axes, 'axis', 'axes')}" if axes else ""), [text]
    if form in ("funnel", "pyramid"):
        word = "stage" if v.get("n") == 1 else "stages"
        return f"{form} {n} {word} (narrow end {v.get('dir')})", [
            f"heading {round(v.get('head') or 0)}pt",
            text,
        ]
    if form == "cycle":
        return f"cycle {n} nodes ({v.get('dir')})", [f"node text {round(v.get('head') or 0)}pt", text]
    if form == "agenda":
        return f"agenda {n} rows" + (", current marked" if v.get("now") else ""), [
            f"numbers {round(v.get('num') or 0)}pt",
            text,
        ]
    if form == "statement":
        return "statement" + (" + caption" if v.get("caption") else ""), [
            f"big line {_size(v.get('size'), v.get('big_asked'))}"
        ]
    return form, [text]


def _list(texts: list[Placed], theme, dense_k):
    n = sum(len(p.element.paragraphs) for p in texts)
    asked = _asked(theme, "body", dense_k)
    if texts[0].element.style and texts[0].element.style.font_size:
        asked = texts[0].element.style.font_size
    return f"list {_n(n, 'item')} {_size(_pt(texts[0]), asked)}"


# --------------------------------------------------------------------------- one slide


def _set_ignored(slide, theme: Theme, index: int) -> list[str]:
    took: list[str] = []
    ignored: list[str] = []
    for el, _kind, attr, hint in audit(slide, theme, index):
        label = attr
        if attr == "size" and getattr(el, "style", None) is not None and el.style.font_size:
            label = f"size={el.style.font_size:g}"
        target = took if hint is None else ignored
        if label not in target:
            target.append(label)
    out = []
    if took:
        out.append("took " + " ".join(took))
    if ignored:
        out.append("ignored " + " ".join(ignored))
    return out


def _slide_line(deck: Deck, slide, items: list[Placed], theme: Theme, i: int) -> tuple[str, int | None]:
    """(the fit line, the percent of the body left free when the slide counts as sparse, else ``None``)."""
    n = i + 1
    if slide.html is not None:
        shapes = sum(1 for p in items if not _chrome(p))
        return f"slide {n}: html, {_n(shapes, 'shape')}", None
    fit: dict[str, Any] = deck.attrs.get("_fit", {}).get(i) or {}
    kind, body = fit.get("kind"), fit.get("body")
    asked, dense_k = fit.get("asked") or {}, float(fit.get("dense_k") or 1.0)
    if kind in ("cover", "section"):
        return _cover_line(slide, items, theme, n, kind, extra=_set_ignored(slide, theme, i)), None

    inner = [p for p in items if not _chrome(p)]
    cards = [p for p in inner if isinstance(p.element, Container)]
    tops = [c for c in cards if not any(_inside(c, o) for o in cards)]
    kpis = [c for c in tops if "kpi" in c.element.classes]
    step_cards = [c for c in cards if "steps-card" in c.element.classes]
    boxes = [
        c
        for c in tops
        if "kpi" not in c.element.classes
        and "steps-card" not in c.element.classes
        and not {"diagram", "group"} & set(c.element.classes)
    ]
    arrows = [p for p in inner if isinstance(p.element, Shape) and "steps-arrow" in p.element.classes]
    chev = [
        p
        for p in inner
        if isinstance(p.element, Shape)
        and p.element.shape == "chevron"
        and "steps-arrow" not in p.element.classes
    ]
    parts: list[tuple[str, list[str]]] = []
    if slide.lead is not None and slide.lead.paragraphs and word_of(slide.classes) != "quote":
        parts.append(("lead", []))  # (an @quote slide draws its lead as the quotation)
    if kpis:
        parts.append(_kpi(kpis, inner, body, asked, theme))
    if arrows:
        parts.append(_steps(arrows, step_cards, inner, body, theme, dense_k))
    if chev:
        parts.append(_chevron(chev, theme))
    if kind == "rows":
        bars = [p for p in inner if isinstance(p.element, Shape) and "rows" in p.element.classes]
        size = _size(_pt(bars[0]), _asked(theme, "body", dense_k)) if bars else ""
        parts.append((f"rows {_n(len(bars), 'bar')} {size}".rstrip(), []))
    if boxes and not arrows:
        parts.append(_boxes(boxes, inner, theme, dense_k))
    for p in inner:
        el = p.element
        if isinstance(el, Table):
            parts.append(_table(p, theme, dense_k))
        elif isinstance(el, Chart):
            parts.append(_chart(el))
        elif isinstance(el, (Image, Media)):
            parts.append(("video" if getattr(el, "kind", "") == "video" else "image", []))
        elif isinstance(el, Code):
            parts.append(("code", []))
        elif isinstance(el, Raw):
            parts.append((el.kind or "diagram", []))
    loose = [
        p
        for p in inner
        if isinstance(p.element, Text)
        and p.element.role == "body"
        and p.element.paragraphs
        and not p.element.attrs.get("chart_note")
        and not any(_inside(p, c) for c in cards)
    ]
    if loose and kind != "rows":
        if "callout" in loose[0].element.classes and len(loose) == 1:
            parts.append(("callout", []))
        else:
            parts.append((_list(loose, theme, dense_k), []))
    form = fit_part(slide, kind, inner, fit)  # DL3b part 2: @iconlist @quote @split @heatmap ...
    if form is not None:
        keep = [p for p in parts if p[0] == "lead"]
        parts = [*keep, form] if kind in COMPOSED else [form, *parts]
    if kind == "vocab" and fit.get("vocab"):
        parts = [p for p in parts if p[0] == "lead"] + [_vocab(fit["vocab"], theme, dense_k)]
    if kind == "free":
        pinned = sum(1 for e in slide.elements if getattr(e, "box", None) is not None and e.box.x is not None)
        drawn = sum(1 for e in slide.elements if isinstance(e, Shape))
        head = f"free {_n(len(slide.elements), 'block')}, {pinned} pinned" + (
            f", {_n(drawn, 'shape')}" if drawn else ""
        )
        area = []  # what `%` refers to: the body under the title, in inches
        if body and body[2] > 0 and body[3] > 0:
            k = EMU_PER_INCH
            area = [f"free area {body[0] / k:.1f},{body[1] / k:.1f} {body[2] / k:.1f}x{body[3] / k:.1f}in"]
        parts = [(head, area)] + [p for p in parts if p[0] == "lead"]
    bar_in: list[Placed] = []
    if slide.conclusion is not None and slide.conclusion.paragraphs and body:
        bar = next((p for p in items if isinstance(p.element, Text) and p.element.role == "conclusion"), None)
        if bar is not None and bar.y < body[1] + body[3]:  # moved up into the body (table + bar)
            parts.append(("conclusion bar attached", []))
            bar_in = [bar]
    names = " + ".join(name for name, _ in parts) or "title only"
    facts = [f for _, fs in parts for f in fs]
    seen = [*(p for p in inner if not isinstance(p.element, Shape) or p.element.shape != "line"), *bar_in]
    free = _free(body, seen)
    share = _free_share(body, seen) if inner and kind not in ("free",) else None
    sparse = round(share * 100) if share is not None and share > theme.layout.sparse_note else None
    if sparse is None and free and kind not in ("free",):
        facts.append(free)
    facts += _set_ignored(slide, theme, i)
    if sparse is not None:  # the composition cue ends the line (it replaces the plain free-space fact)
        facts.append(f"sparse: {sparse}% free")
    return f"slide {n}: " + ", ".join([names, *facts]), sparse


def _cover_line(slide, items: list[Placed], theme: Theme, n: int, kind: str, extra: list[str]) -> str:
    title = next((p for p in items if isinstance(p.element, Text) and p.element.role == "title"), None)
    sub = next(
        (p for p in items if isinstance(p.element, Text) and p.element.role in ("subtitle", "lead")), None
    )
    facts = []
    if title is not None:
        explicit = slide.title.style.font_size if slide.title and slide.title.style else None
        facts.append("title " + _size(_pt(title), explicit or _asked(theme, "cover-title", 1.0)))
    if sub is not None:
        facts.append("subtitle " + _size(_pt(sub)))
    if kind == "cover":
        anchored = theme.cover_band_h > 0 and not (
            title is not None and slide.title.style and slide.title.style.font_size
        )
        facts.append("band composed" if anchored else "centred block")
    return f"slide {n}: {kind}, " + ", ".join([*facts, *extra])


def fit_report(deck: Deck, placed: list[list[Placed]], theme: Theme) -> tuple[list[str], list[Diagnostic]]:
    """(one fit line per slide, one ``sparse`` info per slide that stays sparse). Never raises.

    A slide the map cannot read gets ``(no fit data)``. The info is level ``info`` (a composition cue must not
    cost a rebuild); its percent is the one printed at the end of the slide's fit line."""
    out: list[str] = []
    diags: list[Diagnostic] = []
    rule, msg, hint = SPARSE
    for i, (slide, items) in enumerate(zip(deck.slides, placed, strict=False)):
        try:
            line, sparse = _slide_line(deck, slide, items, theme, i)
        except Exception:
            out.append(f"slide {i + 1}: (no fit data)")
            continue
        out.append(line)
        if sparse is not None:
            diags.append(
                Diagnostic(
                    level="info",
                    message=msg.format(n=i + 1, pct=sparse),
                    slide=i + 1,
                    rule=rule,
                    hint=hint.format(cap=theme.layout.grow_max),
                )
            )
    return out, diags


def fit_lines(deck: Deck, placed: list[list[Placed]], theme: Theme) -> list[str]:
    """One line per slide (see ``fit_report``)."""
    return fit_report(deck, placed, theme)[0]


__all__ = ["fit_lines", "fit_report"]
