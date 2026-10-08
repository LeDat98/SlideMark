"""``attr-ignored``: author choices the layout does not honour (docs/DESIGN_REQUIRED.md, AC7).

An agent that decides ``{h=55%}`` on a KPI card and gets no warning opens an image to find out whether it took
effect. Every ``{key=value}`` attribute and every ``style:`` token that has no effect where it was written
becomes one ``attr-ignored`` warning with a one-line hint naming the form that works.

The detection is a table, not a second layout:

- ``HONOURED[kind]`` / ``IGNORED[kind]``: for each element kind (``title`` ``box`` ``kpi`` ``step`` ``chart``
  ...) the attributes of ``ATTRS`` the layout and renderer honour, and the ones they do not (with the hint).
  Every attribute of ``ATTRS`` is in exactly one of the two (``tests/test_honour.py`` checks it, and probes
  each cell against the real layout / renderer). ``@free`` honours ``x y w h`` on every kind.
- ``STYLE_NEEDS``: ``style:`` tokens that only act where an element kind exists (``kpi.stripe`` needs a KPI
  card, ``cover.rule`` an anchored cover, ``steps-arrow.fill`` an ``@steps`` slide).

Kinds are decided from the parsed IR (and the chevron rewrite the layout applies), never from the output.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from typing import Any

from . import forms, forms2, forms4
from .ir import Chart, Code, Container, Deck, Diagnostic, Image, Media, Placed, Shape, Slide, Table, Text

# The documented attribute keys (docs/SYNTAX.md "Attributes"): position, style, image, `icon` on boxes and the
# element-control keys `shadow rotate shape z` (DL3: every element kind takes the full set).
ATTRS = (
    *("x", "y", "w", "h"),
    *("size", "color", "fill", "line", "font", "align", "valign", "bold", "italic"),
    *("radius", "opacity", "pad", "fit", "icon"),
    *("shadow", "rotate", "shape", "z"),
)
GEOMETRY = ("x", "y", "w", "h")

# Fields of Style / Box that carry an attribute, by the attribute's name
_STYLE_FIELDS = {
    "font_size": "size",
    "color": "color",
    "fill": "fill",
    "line": "line",
    "font": "font",
    "align": "align",
    "valign": "valign",
    "bold": "bold",
    "italic": "italic",
    "radius": "radius",
    "opacity": "opacity",
    "padding": "pad",
    "shadow": "shadow",
    "rotation": "rotate",
    "shape": "shape",
    "z": "z",
}

LABEL = {
    "title": "a slide title",
    "cover": "a cover title",
    "box": "a box",
    "item": "an item card",
    "kpi": "a KPI card",
    "step": "an @steps box",
    "chevron": "a compact @chevron box",
    "text": "a text block",
    "callout": "a callout",
    "image": "an image",
    "table": "a table",
    "chart": "a chart",
    "code": "a code block",
    "rows": "an @rows list",
    "row": "a row of an @rows list",
    "list item": "a list item",
    "stage": "a form box",
    "formtext": "a form's text",
    "shape": "a drawn shape",
}

_FIT = "fit= is for images: ![alt](a.png){fit=cover|contain|stretch}"
_ICON = "icon= goes on a box heading: ## Label {icon=chart}"
_STEP_GEO = "step boxes follow the row: @1:2:1 steps sets column ratios, @free places blocks"
_CHART = "charts take colors=a,b (series) and size= (text); this does not apply"
_IMAGE = "an image has no text: x y w h size fill line radius opacity pad align valign fit apply"
_ROTATE_FRAME = "PowerPoint cannot rotate tables and charts: rotate the box around them ## b {rotate=5}"
_ITEM_GEO = "a list item is a line of text: {color= size= bold= italic= font= align=} style it"
_ITEM_BOX = "a list item has no box: put the list in a box (##) to give it fill, border, radius"
_STAGE_GEO = (
    "a form places its shapes: @1:2 ratios, gap= and its own tokens set the geometry, @free places blocks"
)
_STAGE_TEXT = "size= on the @ line sizes the form's text; fill= and color= go on the box, the rest are tokens"
_SHAPE_TEXT = (
    "a text-less shape has no text: size color font align valign bold italic pad apply to a box or text"
)
_STAGE_DECO = (
    "a form draws its own shapes: shadow= rotate= shape= z= apply to ordinary boxes, not to the form"
)


def _ig(attrs: str, hint: str) -> dict[str, str]:
    return dict.fromkeys(attrs.split(), hint)


# kind -> attributes honoured; every other attribute of ATTRS is in IGNORED[kind] (with the hint).
_FULL = "x y w h size color font align valign bold italic fill line radius opacity pad shadow rotate shape z"
HONOURED: dict[str, str] = {
    "title": _FULL,
    "cover": _FULL,
    "box": f"{_FULL} icon",
    "item": _FULL,
    "kpi": f"{_FULL} icon",
    "step": "size color font align valign bold italic fill line radius opacity pad "
    "shadow rotate shape z icon",
    "chevron": "x y w h size color font align valign bold italic fill line opacity pad "
    "shadow rotate shape z icon",
    "text": _FULL,
    "callout": _FULL,
    "image": "x y w h size fill line radius opacity pad align valign fit shadow rotate shape z",
    "table": "x y w h size color font align valign bold italic fill line opacity pad shadow z",
    "chart": "x y w h size color font align valign bold italic fill line radius opacity pad shadow shape z",
    "code": _FULL,
    "rows": _FULL,
    "row": "size color font align bold italic fill line",
    "list item": "size color font align bold italic",
    "stage": "fill color",
    "formtext": "size color",
    "shape": "x y w h fill line radius opacity shadow rotate shape z",
}
IGNORED: dict[str, dict[str, str]] = {
    "title": {"fit": _FIT, "icon": _ICON},
    "cover": {"fit": _FIT, "icon": _ICON},
    "box": {"fit": _FIT},
    "item": {"icon": "an item card has no icon slot: put icon= on the ## box heading", "fit": _FIT},
    "kpi": {"fit": _FIT},
    "step": {
        **_ig("x y w h", _STEP_GEO),
        "fit": _FIT,
    },
    "chevron": {
        "radius": "chevron points are fixed: shape=pill|rounded|pentagon redraws the box",
        "fit": _FIT,
    },
    "text": {"fit": _FIT, "icon": _ICON},
    "callout": {"fit": _FIT, "icon": _ICON},
    "image": {**_ig("color font bold italic", _IMAGE), "icon": _ICON},
    "table": {
        "radius": "PowerPoint tables have square corners: put the table in a box ## t {radius=12}",
        "rotate": _ROTATE_FRAME,
        "shape": "a table is a grid of cells: shape= is for boxes, text, images and charts",
        "fit": _FIT,
        "icon": _ICON,
    },
    "chart": {"rotate": _ROTATE_FRAME, "fit": _FIT, "icon": _ICON},
    "code": {"fit": _FIT, "icon": _ICON},
    "rows": {"fit": _FIT, "icon": _ICON},
    "row": {
        **_ig("x y w h", "rows are laid out one under the other: {x= y= w= h=} place the whole list"),
        **_ig(
            "valign radius opacity pad shadow rotate shape z",
            "a row takes size color font bold italic align fill line",
        ),
        "fit": _FIT,
        "icon": _ICON,
    },
    "list item": {
        **_ig("x y w h", _ITEM_GEO),
        **_ig("fill line radius opacity pad valign shadow rotate shape z", _ITEM_BOX),
        "fit": _FIT,
        "icon": _ICON,
    },
    "stage": {
        **_ig("x y w h", _STAGE_GEO),
        **_ig("size font bold italic align valign radius opacity pad", _STAGE_TEXT),
        **_ig("shadow rotate shape z", _STAGE_DECO),
        "line": "a form draws its own outline: fill= and color= apply, its tokens set the rest",
        "fit": _FIT,
        "icon": _ICON,
    },
    "shape": {**_ig("size color font align valign bold italic pad", _SHAPE_TEXT), "fit": _FIT, "icon": _ICON},
    "formtext": {
        **_ig("x y w h", _STAGE_GEO),
        **_ig("font bold italic align valign fill line radius opacity pad", _STAGE_TEXT),
        **_ig("shadow rotate shape z", _STAGE_DECO),
        "fit": _FIT,
        "icon": _ICON,
    },
}

# Honoured only with a companion: (kind, attr) -> the attributes of which one must be written beside it
# (a corner radius or a preset shape needs something to draw: a fill or a border).
NEEDS: dict[tuple[str, str], tuple[str, ...]] = {
    ("text", "radius"): ("fill", "line"),
    ("text", "shape"): ("fill", "line"),
    ("chart", "radius"): ("fill", "line"),
    ("chart", "shape"): ("fill", "line"),
    ("chart", "opacity"): ("fill",),
    ("chart", "align"): ("w",),  # a chart that fills its cell has nowhere to move
    ("chart", "valign"): ("h",),
    ("image", "valign"): ("size",),  # a picture that fills the height has nowhere to move
}


STRIPE_KINDS = (
    "box",
    "item",
    "kpi",
)  # `{stripe=teal}`: the stripe on a card edge (not in ATTRS: a card look)


def honoured(kind: str, attr: str) -> bool:
    return attr in HONOURED[kind].split()


# --------------------------------------------------------------------------- element kinds


def _slide_kind(slide: Slide, index: int, has_body: bool) -> str:
    """cover / section / content / ...: the layout's own inference."""
    kind = slide.layout
    if kind in ("cover", "section", "blank", "center", "content", "free"):
        return kind
    if slide.title and not slide.elements and not slide.conclusion and not has_body:
        return "cover" if index == 0 else "section"
    return "content"


class _Item:
    """A list item (or a row of an ``@rows`` list) seen as an element: its own text style and the keys it
    cannot honour (``Paragraph.attrs``)."""

    def __init__(self, p: Any, line: int | None) -> None:
        self.box, self.style, self.attrs, self.line = None, p.style, p.attrs, line


def _walk(slide: Slide, theme: Any, index: int) -> Iterator[tuple[Any, str]]:
    """``(element, kind)`` for every element that can carry attributes."""
    from .layout.engine import _chevron_steps

    shaped = _chevron_steps(slide, theme.layout)  # a short-bodied @chevron row is built as @steps
    covered = _slide_kind(slide, index, bool(slide.lead)) in ("cover", "section")
    if slide.title is not None:
        yield slide.title, "cover" if covered else "title"
    if slide.subtitle is not None and covered:
        yield slide.subtitle, "cover"
    rows = "rows" in slide.classes or bool(theme.layout.rows)
    form = forms.form_of(slide)
    if form and forms.fits(form, slide) is not None:
        form = None  # not composed: ordinary blocks
    drawn = form in ("timeline", "funnel", "pyramid", "cycle", "stairs", "nested", "flowdisc")

    def rec(el: Any, parent: Container | None) -> Iterator[tuple[Any, str]]:
        if isinstance(el, Container) and drawn and parent is None:
            yield el, "stage"
            return
        if isinstance(el, Text) and form in ("agenda", "statement") and parent is None and el.role == "body":
            yield el, "formtext"
            return
        if isinstance(el, Container):
            if "kpi" in el.classes:  # `y h w` place the row (layout.kpirow), `x` makes the card absolute
                yield el, "kpi"
            elif parent is not None and "steps" in parent.classes:
                yield el, "step"
            elif "diagram" in el.classes or "group" in el.classes and "steps" in el.classes:
                pass  # generated containers: nothing the author wrote
            elif "chevron" in shaped.classes and parent is None and "steps" not in shaped.classes:
                yield el, "chevron"
            elif "item" in el.classes:  # `### text {.item}`: an item card
                yield el, "item"
            else:
                yield el, "box"
            for c in el.children:
                yield from rec(c, el)
        elif isinstance(el, Text):
            if el.role == "body":
                kind = "callout" if "callout" in el.classes else "rows" if rows and _is_list(el) else "text"
                yield el, kind
                for p in el.paragraphs:  # `- item {color=red}`
                    if p.marker and (p.style is not None or p.attrs):
                        yield _Item(p, el.line), "row" if kind == "rows" else "list item"
        elif isinstance(el, (Image, Media)):
            yield el, "image"
        elif isinstance(el, Table):
            yield el, "table"
        elif isinstance(el, Chart):
            yield el, "chart"
        elif isinstance(el, Code):
            yield el, "code"
        elif isinstance(el, Shape):  # `{x= y= w= h= shape= fill=}` with no content: a drawn shape
            yield el, "shape"

    for el in shaped.elements:
        yield from rec(el, None)


def _is_list(el: Text) -> bool:
    return bool(el.paragraphs) and all(p.marker for p in el.paragraphs)


def _authored(el: Any) -> list[str]:
    """The attributes the author wrote on ``el`` (a subset of ATTRS), in the order of ATTRS."""
    got: set[str] = set()
    if el.box is not None:
        got |= {k for k in GEOMETRY if getattr(el.box, k) is not None}
    if el.style is not None:
        for field, attr in _STYLE_FIELDS.items():
            if getattr(el.style, field, None) is not None:
                got.add(attr)
    extra = {**el.attrs, **(el.options if isinstance(el, Chart) else {})}  # keys no handler consumed
    if isinstance(el, _Item):
        got |= {k for k in ATTRS if k in el.attrs}
    if isinstance(el, Image):
        if el.fit != "contain":
            got.add("fit")
    elif "fit" in extra:
        got.add("fit")
    if "icon" in extra:
        got.add("icon")
    return [a for a in ATTRS if a in got]


def _has_text(el: Any) -> bool:
    return any(isinstance(c, Text) and c.paragraphs for c in el.children)


# forms whose `##` boxes take `icon=`: the glyph sits in the node (`@cycle`) or the list beside the rings
ICON_FORMS = ("cycle", "nested", "flowdisc")


def audit(slide: Slide, theme: Any, index: int = 0) -> list[tuple[Any, str, str, str | None]]:
    """``(element, kind, attr, hint)`` for every attribute written on the slide; hint ``None`` = honoured."""
    free = slide.layout == "free"
    form = forms.form_of(slide)
    out = []
    for el, kind in _walk(slide, theme, index):
        authored = _authored(el)
        for attr in authored:
            if free and attr in GEOMETRY and kind not in ("row", "list item"):
                out.append((el, kind, attr, None))
            elif honoured(kind, attr) or (kind == "stage" and attr == "icon" and form in ICON_FORMS):
                needs = NEEDS.get((kind, attr))
                if needs and not any(n in authored for n in needs):
                    hint = f"{attr}= shows with {' or '.join(f'{n}=<c>' for n in needs)}: write one beside it"
                    out.append((el, kind, attr, hint))
                elif (
                    attr == "size"
                    and isinstance(el, Container)
                    and not _has_text(el)
                    and "kpi" not in el.classes
                    and "item" not in el.classes  # an item card: `size=` sizes its text
                ):
                    hint = "size= sizes the box text, not its heading: sizes: heading=NN or h2.size=NN"
                    out.append((el, kind, attr, hint))
                else:
                    out.append((el, kind, attr, None))
            else:
                out.append((el, kind, attr, IGNORED[kind][attr]))
        if "stripe" in getattr(el, "attrs", {}) and kind not in STRIPE_KINDS:
            out.append(
                (
                    el,
                    kind,
                    "stripe",
                    "stripe=<color> draws on a card edge: put it on a ## box, an item card or a KPI card",
                )
            )
    return out


# --------------------------------------------------------------------------- style: tokens


class _Facts:
    """What the deck contains, for the ``style:`` tokens that only act on one element kind."""

    def __init__(self, deck: Deck, theme: Any) -> None:
        self.deck, self.theme = deck, theme
        self.els = [e for s in deck.slides for e in _flat(s.elements)]
        self.covers = [s for i, s in enumerate(deck.slides) if _slide_kind(s, i, bool(s.lead)) == "cover"]

    def any(self, pred: Callable[[Any], bool]) -> bool:
        return any(pred(e) for e in self.els)

    def kpi(self) -> bool:
        return self.any(lambda e: isinstance(e, Container) and "kpi" in e.classes)

    def steps(self) -> bool:
        return any({"steps", "chevron"} & set(s.classes) for s in self.deck.slides) or self.any(
            lambda e: isinstance(e, Container) and "steps" in e.classes
        )

    def rows(self) -> bool:
        return bool(self.theme.layout.rows) or any("rows" in s.classes for s in self.deck.slides)

    def table(self) -> bool:
        return self.any(lambda e: isinstance(e, Table))

    def chart(self) -> bool:
        return self.any(lambda e: isinstance(e, Chart))

    def bullets(self) -> bool:
        return self.any(lambda e: isinstance(e, Text) and any(p.marker for p in e.paragraphs))

    def boxes(self) -> bool:
        return self.any(lambda e: isinstance(e, Container) and "kpi" not in e.classes)

    def cover(self) -> bool:
        return bool(self.covers)

    def anchored_cover(self) -> bool:
        """The composed cover (band, rule, bar) is on: ``cover.band_h`` > 0 and some cover title with
        no style of its own (``{size=}``, a pinned size, CSS on the title keeps the old centred look)."""
        if self.theme.cover_band_h <= 0:
            return False
        return any(not self._styled(s) for s in self.covers)

    def _styled(self, cover: Slide) -> bool:
        pinned = set(self.theme.pinned)
        for el in (cover.title, cover.subtitle or cover.lead):
            if el is None:
                continue
            if getattr(el.style, "font_size", None) is not None or el.role in pinned:
                return True
        names = ["h1", "slide", r"\.cover", r"\.title"]
        # (the cover subtitle is a `p.subtitle` node: `h2 { }` styles box headings, not the subtitle)
        names += [r"\.subtitle"] if cover.subtitle is not None else [r"\.lead"] if cover.lead else []
        pattern = re.compile(r"(" + "|".join(names) + r")\b")

        def reaches_cover(selector: str) -> bool:
            """The rule's subject (its last compound) is a cover element and nothing narrows it to another
            ancestor: ``.kpi h2`` styles the KPI labels, not the cover subtitle."""
            parts = re.split(r"\s*[>\s]\s*", selector.strip())
            return bool(pattern.match(parts[-1])) and all(
                re.match(r"(slide|\.cover)\b", a) for a in parts[:-1]
            )

        return any(
            reaches_cover(r.selector)
            and any(v is not None for k, v in r.style.__dict__.items() if k != "color")
            for r in [*self.deck.css, *cover.css]
        )

    def items(self) -> bool:
        """`@items` / `box.items=cards` on a deck with boxes, or a `### x {.item}` sub-box."""
        return (
            (self.theme.box_items == "cards" and self.boxes())
            or any("items" in s.classes for s in self.deck.slides)
            or self.any(lambda e: isinstance(e, Container) and "item" in e.classes)
        )

    def num(self) -> bool:
        """`@num` on a slide of boxes (on `@steps` it is the caption flag, `@rows` has its own badges)."""

        def steps(s: Slide) -> bool:  # `@steps` is expanded into a group at parse time
            return bool({"steps", "chevron", "rows"} & set(s.classes)) or any(
                isinstance(e, Container) and "steps" in e.classes for e in s.elements
            )

        return any("num" in s.classes and not steps(s) for s in self.deck.slides) or self.any(
            lambda e: (
                isinstance(e, Container) and "num" in e.classes
            )  # `## 01 {.num}`: the heading is the number
        )

    def has_form(self, name: str) -> bool:
        """A slide with the composition form ``@name`` (``@timeline`` ...)."""
        return any(forms.form_of(s) == name for s in self.deck.slides)

    def plain_rows(self) -> bool:
        return any({"rows", "plain"} <= set(s.classes) for s in self.deck.slides)

    def cover_rule(self) -> bool:
        return bool(self.theme.cover_rule)

    def footer(self) -> bool:
        return bool(self.deck.footer or self.deck.slide_number)

    def lead(self) -> bool:
        return any(s.lead is not None for s in self.deck.slides)

    def conclusion(self) -> bool:
        return any(s.conclusion is not None and bool(s.conclusion.paragraphs) for s in self.deck.slides)

    def never(self) -> bool:
        return False


def _flat(els: list[Any]) -> Iterator[Any]:
    for e in els:
        yield e
        if isinstance(e, Container):
            yield from _flat(e.children)


# (pattern over the lower-cased token key, what the deck needs, hint)
STYLE_NEEDS: list[tuple[re.Pattern[str], Callable[[_Facts], bool], str]] = [
    (
        re.compile(r"^chevron\."),
        _Facts.never,
        "`chevron.*` styles nothing: arrows follow primary (compact) or steps-arrow.fill=<c> (@steps)",
    ),
    (
        re.compile(r"^cover\.rule_(w|pos)$"),
        _Facts.cover_rule,
        "needs a rule to shorten: cover.rule=<color> (cover.rule_w / rule_pos place it)",
    ),
    (
        re.compile(r"^cover\.bottom\."),
        _Facts.cover,
        "no cover slide: slide 1 with only a title (+ subtitle) or @cover",
    ),
    (
        re.compile(r"^cover\.art"),  # wave 2026-10-08 lane D: the motif needs a cover, not the anchored one
        _Facts.cover,
        "no cover slide: slide 1 with only a title (+ subtitle) or @cover",
    ),
    (
        re.compile(r"^cover\.band_h$"),
        _Facts.cover,
        "no cover slide: slide 1 with only a title (+ subtitle) or @cover",
    ),
    (
        re.compile(r"^cover\."),
        _Facts.anchored_cover,
        "needs the anchored cover: cover.band_h=60% and no {size=} on the cover title (keeps the old look)",
    ),
    (
        re.compile(r"^(kpi[.-]|layout\.kpi)"),
        _Facts.kpi,
        "no `.kpi` card in the deck: ## Label {.kpi} + value line + caption line",
    ),
    (
        re.compile(r"^conclusion\.h$"),
        _Facts.conclusion,
        "no `>` conclusion bar in the deck: end a slide with `> text` (the bar is conclusion.h tall)",
    ),
    (
        re.compile(r"^(steps?[.-]|layout\.steps)"),
        _Facts.steps,
        "no @steps slide in the deck: write `@4 steps` before the boxes",
    ),
    (
        re.compile(r"^rows\.glyph"),
        _Facts.plain_rows,
        "no `@rows plain` slide in the deck: the glyph marks the bars of unnumbered rows",
    ),
    (
        re.compile(r"^(rows?[.-]|layout\.rows)"),
        _Facts.rows,
        "no @rows slide in the deck: write `@rows` before a 1. list",
    ),
    (re.compile(r"^(table\.|layout\.table)"), _Facts.table, "no table in the deck"),
    (re.compile(r"^(palette|render\.chart_)"), _Facts.chart, "no chart in the deck"),
    (re.compile(r"^bullet"), _Facts.bullets, "no bullet list in the deck"),
    (
        re.compile(r"^box\.num\."),
        _Facts.num,
        "no `@num` slide in the deck: write `@4 num` before the boxes (not on @steps)",
    ),
    (
        re.compile(r"^item\."),
        _Facts.items,
        "no item cards in the deck: `@4 items` before the boxes, box.items=cards, or `### x {.item}`",
    ),
    (
        re.compile(r"^render\.chevron_shape$"),
        _Facts.steps,
        "no @steps / @chevron slide in the deck: the shape is the arrows' own",
    ),
    *(
        (
            re.compile(rf"^{name}[.-]"),
            lambda f, name=name: f.has_form(name),
            f"no @{name} slide in the deck: write `@{name}` under the title of the slide",
        )
        for name in forms.FORMS
    ),
    (
        re.compile(r"^box\.(h|anchor)$"),
        _Facts.boxes,
        "no ## box in the deck: box.h and box.anchor size and place `##` box cards (KPI cards: kpi.h)",
    ),
    (re.compile(r"^(heading\.|card\.|box\.)"), _Facts.boxes, "no ## box in the deck"),
    (re.compile(r"^(footer|num)\."), _Facts.footer, "no footer: set `footer:` or `num: on`"),
    (re.compile(r"^lead\."), _Facts.lead, "no `>` lead line under a title"),
]


STYLE_NEEDS.extend(forms2.STYLE_NEEDS)  # DL3b part 2: iconlist.* quote.* split.* proscons.* progress.* ...
STYLE_NEEDS.extend(forms4.STYLE_NEEDS)  # wave 2026-10-08 lane B: flow.disc.* flow.line


def style_diagnostics(deck: Deck, theme: Any) -> list[Diagnostic]:
    """``attr-ignored`` for ``style:`` tokens whose element kind the deck does not contain."""
    out: list[Diagnostic] = []
    facts = _Facts(deck, theme)
    seen: set[str] = set()
    for key, line in deck.attrs.get("style_keys") or []:
        low = key.lower()
        if low in seen:
            continue
        for pat, need, hint in STYLE_NEEDS:
            if pat.search(low):
                if not need(facts):
                    seen.add(low)
                    out.append(
                        Diagnostic(
                            level="warning",
                            message=f"style: {key}= has no effect here",
                            line=line,
                            rule="attr-ignored",
                            hint=hint,
                        )
                    )
                break
    return out


def honour_diagnostics(deck: Deck, placed: list[list[Placed]], theme: Any) -> list[Diagnostic]:
    """One ``attr-ignored`` warning per (slide, kind, attribute) the layout does not honour. Never raises."""
    out: list[Diagnostic] = []
    try:
        for i, slide in enumerate(deck.slides):
            if slide.html is not None:
                continue
            seen: set[tuple[str, str]] = set()
            for el, kind, attr, hint in audit(slide, theme, i):
                if hint is None or (kind, attr) in seen:
                    continue
                seen.add((kind, attr))
                out.append(
                    Diagnostic(
                        level="warning",
                        message=f"{attr}= on {LABEL[kind]} is not honoured",
                        line=getattr(el, "line", None),
                        slide=i + 1,
                        rule="attr-ignored",
                        hint=hint,
                    )
                )
        out += style_diagnostics(deck, theme)
    except Exception:  # feedback must never break a build
        return out
    return out


__all__ = ["ATTRS", "HONOURED", "IGNORED", "STYLE_NEEDS", "audit", "honour_diagnostics", "honoured"]
