"""Per-card looks decided by the order of the cards: stripe colours, big-number headings, KPI tiles.

``box.stripe=a,b,c`` (and ``item.stripe`` / ``kpi.stripe``) cycle over the cards in reading order, like
``steps-arrow.fill=a,b``; ``{stripe=teal}`` on one card wins. ``@4 num=text`` writes ``01`` ``02`` ... as big
coloured text above every box heading, ``## 01 {.num}`` draws the heading text itself as the number, and
``@kpi tile`` turns a ``## 2.1T`` + description card into number + caption. All of it runs on the copy of the
slide that ``engine._slide_items`` makes (the parsed IR stays as written); the renderer draws the stripes from
the final card rectangle (``render._stripe``), so cards that later passes stretch or move keep them.
Never raises: a card the helpers cannot read is returned unchanged.
"""

from __future__ import annotations

from typing import Any

from ..ir import Container, Paragraph, Run, Style, Text
from ..theme import DEFAULT_SIZES, Theme


def colors(spec: str | None) -> list[str]:
    """``"a, b,c"`` -> ``["a", "b", "c"]`` (empty for ``None`` / blank)."""
    return [x.strip() for x in spec.split(",") if x.strip()] if spec else []


def pick(spec: str | None, i: int) -> str | None:
    """The ``i``-th colour of a cycling list (``None`` when there is none)."""
    cols = colors(spec)
    return cols[i % len(cols)] if cols else None


def stamp(c: Container, **attrs: Any) -> Container:
    """``c`` with ``attrs`` added (an attribute the author wrote on the card is kept)."""
    new = {k: v for k, v in attrs.items() if v is not None and k not in c.attrs}
    return c.model_copy(update={"attrs": {**c.attrs, **new}}) if new else c


def num_size(theme: Theme) -> float:
    """Size (pt) of a number text: ``box.num.size`` or ``layout.num_text_ratio`` x the heading size."""
    if theme.box_num_size:
        return theme.box_num_size
    return theme.sizes.get("heading", DEFAULT_SIZES["heading"]) * theme.layout.num_text_ratio


def number_text(theme: Theme, n: int) -> str:
    """``box.num.text`` with ``{nn}`` = 01 and ``{n}`` = 1 filled in."""
    return (theme.box_num_text or "{nn}").replace("{nn}", f"{n:02d}").replace("{n}", str(n))


def num_look(theme: Theme, idx: int, stripe: str | None) -> Style:
    """The look of a number text: ``box.num.size`` / ``box.num.color`` (a list cycles), else the card's own
    stripe colour, else ``primary``."""
    color = pick(theme.box_num_color, idx) or stripe or "primary"
    return Style(font_size=num_size(theme), color=color, bold=True)


def number_heading(c: Container, theme: Theme, idx: int, stripe: str | None, auto: int | None) -> Container:
    """Box ``c`` with its heading drawn as a big number.

    ``auto`` (the box number) writes ``01`` as a first heading paragraph above the heading (``num=text``);
    ``None`` styles the heading text itself (``{.num}``: ``## 01 {.num}`` / ``## 2.1兆円 {.num}``)."""
    if c.title is None or not c.title.paragraphs:
        return c
    look = num_look(theme, idx, stripe)
    if auto is None:
        paras = [p.model_copy(update={"style": look.merged(p.style)}) for p in c.title.paragraphs]
    else:
        head = Paragraph(runs=[Run(text=number_text(theme, auto))], style=look)
        paras = [head, *c.title.paragraphs]
    name = "Number heading" if auto is None else "Number text"  # the importer folds these names back
    attrs = {**c.title.attrs, "shape_name": name}
    return c.model_copy(update={"title": c.title.model_copy(update={"paragraphs": paras, "attrs": attrs})})


def kpi_tile(c: Container, stripe: str | None) -> Container:
    """A ``## 2.1兆円`` + description KPI card as number + caption: the heading becomes the value line (in the
    card's stripe colour), the body text the caption; text is left-aligned unless the card says otherwise."""
    if c.title is None or not c.title.paragraphs:
        return c
    value = [
        p.model_copy(update={"style": (Style(color=stripe) if stripe else Style()).merged(p.style)})
        for p in c.title.paragraphs
    ]
    kids = list(c.children)
    first = next((i for i, k in enumerate(kids) if isinstance(k, Text) and k.role == "body"), None)
    name = {"shape_name": "Tile"}  # the importer folds this name back to `{.kpi .tile}`
    if first is None:
        kids.insert(0, Text(role="body", paragraphs=value, attrs=name))
    else:
        k = kids[first]
        kids[first] = k.model_copy(
            update={"paragraphs": [*value, *k.paragraphs], "attrs": {**k.attrs, **name}}
        )
    own = c.style or Style()
    style = own if own.align is not None else own.merged(Style(align="left"))
    return c.model_copy(
        update={"title": None, "children": kids, "style": style, "attrs": {**c.attrs, "tile": True}}
    )


def pin_spans(slide, theme: Theme, dense_k: float = 1.0):
    """A copy of ``slide`` where every body text and box heading that holds a pinned span (``[x]{size=28}``)
    carries its role size as an explicit size: the author sized part of the line, so no growth pass (list,
    card, sparse step ...) touches the rest of it, like ``{size=14}`` on the block. KPI card texts keep
    their own number sizing. Returns ``slide`` itself when nothing holds a pinned span. Never raises."""
    from . import measure  # (layout/__init__ imports the engine, which imports this module)

    def pinned(t: Text) -> bool:
        return any(measure.has_exact(p) for p in t.paragraphs)

    def size_of(role: str) -> float:
        return theme.sizes.get(role, DEFAULT_SIZES[role]) * dense_k

    def fix(t: Text, role: str) -> Text:
        if t.style is not None and t.style.font_size is not None:
            return t
        return t.model_copy(update={"style": (t.style or Style()).merged(Style(font_size=size_of(role)))})

    def walk(els: list, kpi: bool = False) -> tuple[list, bool]:
        out, changed = [], False
        for e in els:
            new = e
            if isinstance(e, Container):
                upd: dict[str, Any] = {}
                inside = kpi or "kpi" in e.classes
                if e.title is not None and not inside and pinned(e.title):
                    upd["title"] = fix(e.title, "heading")
                kids, kid_changed = walk(e.children, inside)
                if kid_changed:
                    upd["children"] = kids
                if upd:
                    new = e.model_copy(update=upd)
            elif isinstance(e, Text) and e.role == "body" and not kpi and "callout" not in e.classes:
                if pinned(e):
                    new = fix(e, "body")
            changed = changed or new is not e
            out.append(new)
        return out, changed

    try:
        els, changed = walk(slide.elements)
    except Exception:  # never raise on user input
        return slide
    return slide.model_copy(update={"elements": els}) if changed else slide
