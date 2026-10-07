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

from .ir import Chart, Code, Container, Deck, Diagnostic, Image, Media, Placed, Slide, Table, Text

# The documented attribute keys (docs/SYNTAX.md "Attributes"): position, style, image, plus `icon` on boxes.
ATTRS = (
    *("x", "y", "w", "h"),
    *("size", "color", "fill", "line", "font", "align", "valign", "bold", "italic"),
    *("radius", "opacity", "pad", "fit", "icon"),
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
}

LABEL = {
    "title": "a slide title",
    "cover": "a cover title",
    "box": "a box",
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
}

_FIT = "fit= is for images: ![alt](a.png){fit=cover|contain|stretch}"
_ICON = "icon= goes on a box heading: ## Label {icon=chart}"
_TITLE_GEO = "titles sit in the title area: @free places them, sizes: title= sizes them"
_STEP_GEO = "step boxes follow the row: @1:2:1 steps sets column ratios, @free places blocks"
_CHART = "charts take colors=a,b (series) and size= (text); this does not apply"
_IMAGE = "an image has no text: x y w h line radius opacity fit apply"


def _ig(attrs: str, hint: str) -> dict[str, str]:
    return dict.fromkeys(attrs.split(), hint)


# kind -> attributes honoured; every other attribute of ATTRS is in IGNORED[kind] (with the hint).
HONOURED: dict[str, str] = {
    "title": "size color font align valign bold italic opacity pad",
    "cover": "size color font align valign bold italic opacity pad",
    "box": "x y w h size color font align valign bold italic fill line radius opacity pad icon",
    "kpi": "x y w h size font italic fill line radius opacity pad icon",
    "step": "size color font align bold italic fill line radius opacity pad icon",
    "chevron": "x y w size color font bold italic fill line opacity icon",
    "text": "x y w h size color font align valign bold italic fill line opacity pad",
    "callout": "x w h size color font align valign bold italic fill line radius opacity pad",
    "image": "x y w h line radius opacity fit",
    "table": "x y w h size color font align valign bold italic fill line opacity",
    "chart": "x y w h size color font",
    "code": "x y w h size color align valign bold italic fill line radius opacity pad",
    "rows": "x y w h size color font bold italic fill line opacity pad",
}
IGNORED: dict[str, dict[str, str]] = {
    "title": {
        **_ig("x y w h", _TITLE_GEO),
        **_ig("fill line radius", "a title is plain text: size color font align apply"),
        "fit": _FIT,
        "icon": _ICON,
    },
    "cover": {
        **_ig("x y w h", _TITLE_GEO),
        **_ig("fill line radius", "a cover title is plain text: size color font align apply"),
        "fit": _FIT,
        "icon": _ICON,
    },
    "box": {"fit": _FIT},
    "kpi": {
        "color": "style: kpi.value.color=<c> colours the number",
        "align": "a KPI card centres its text",
        "valign": "a KPI card centres its text",
        "bold": "style: kpi.value.bold=on bolds the number",
        "fit": _FIT,
    },
    "step": {
        **_ig("x y w h", _STEP_GEO),
        "valign": "step cards keep their text at the top: @free places blocks",
        "fit": _FIT,
    },
    "chevron": {
        "h": "the compact row sets the chevron height: @steps (arrows + cards) fills the body",
        **_ig("align valign radius pad", "a compact chevron centres its text: size color fill apply"),
        "fit": _FIT,
    },
    "text": {
        "radius": "radius= applies to boxes (##), code and images: put the text in a box",
        "fit": _FIT,
        "icon": _ICON,
    },
    "callout": {"y": "a lone callout is centred in the body: @free places it", "fit": _FIT, "icon": _ICON},
    "image": {**_ig("size color fill font align valign bold italic pad", _IMAGE), "icon": _ICON},
    "table": {
        "radius": "table corners follow style: radius=",
        "pad": "cell padding follows the table text: sizes: table=NN",
        "fit": _FIT,
        "icon": _ICON,
    },
    "chart": {
        **_ig("fill line align valign bold italic radius opacity pad", _CHART),
        "fit": _FIT,
        "icon": _ICON,
    },
    "code": {"font": "code uses fonts: mono=<font>", "fit": _FIT, "icon": _ICON},
    "rows": {
        **_ig("align valign radius", "@rows bars are fixed: style: rows.fill= rows-num.fill= layout.rows_h="),
        "fit": _FIT,
        "icon": _ICON,
    },
}


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

    def rec(el: Any, parent: Container | None) -> Iterator[tuple[Any, str]]:
        if isinstance(el, Container):
            if "kpi" in el.classes:  # `y h w` place the row (layout.kpirow), `x` makes the card absolute
                yield el, "kpi"
            elif parent is not None and "steps" in parent.classes:
                yield el, "step"
            elif "diagram" in el.classes or "group" in el.classes and "steps" in el.classes:
                pass  # generated containers: nothing the author wrote
            elif "chevron" in shaped.classes and parent is None and "steps" not in shaped.classes:
                yield el, "chevron"
            else:
                yield el, "box"
            for c in el.children:
                yield from rec(c, el)
        elif isinstance(el, Text):
            if el.role == "body":
                yield (
                    el,
                    "callout" if "callout" in el.classes else "rows" if rows and _is_list(el) else "text",
                )
        elif isinstance(el, (Image, Media)):
            yield el, "image"
        elif isinstance(el, Table):
            yield el, "table"
        elif isinstance(el, Chart):
            yield el, "chart"
        elif isinstance(el, Code):
            yield el, "code"

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


def audit(slide: Slide, theme: Any, index: int = 0) -> list[tuple[Any, str, str, str | None]]:
    """``(element, kind, attr, hint)`` for every attribute written on the slide; hint ``None`` = honoured."""
    free = slide.layout == "free"
    out = []
    for el, kind in _walk(slide, theme, index):
        for attr in _authored(el):
            if free and attr in GEOMETRY:
                out.append((el, kind, attr, None))
            elif honoured(kind, attr):
                if (
                    attr == "size"
                    and isinstance(el, Container)
                    and not _has_text(el)
                    and "kpi" not in el.classes
                ):
                    hint = "size= sizes the box text, not its heading: sizes: heading=NN or h2.size=NN"
                    out.append((el, kind, attr, hint))
                else:
                    out.append((el, kind, attr, None))
            else:
                out.append((el, kind, attr, IGNORED[kind][attr]))
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
        names += [r"\.subtitle", "h2"] if cover.subtitle is not None else [r"\.lead"] if cover.lead else []
        pattern = re.compile(r"(^|[\s>,])(" + "|".join(names) + r")\b")
        return any(
            pattern.search(r.selector)
            and any(v is not None for k, v in r.style.__dict__.items() if k != "color")
            for r in [*self.deck.css, *cover.css]
        )

    def footer(self) -> bool:
        return bool(self.deck.footer or self.deck.slide_number)

    def lead(self) -> bool:
        return any(s.lead is not None for s in self.deck.slides)

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
        re.compile(r"^(steps?[.-]|layout\.steps)"),
        _Facts.steps,
        "no @steps slide in the deck: write `@4 steps` before the boxes",
    ),
    (
        re.compile(r"^(rows?[.-]|layout\.rows)"),
        _Facts.rows,
        "no @rows slide in the deck: write `@rows` before a 1. list",
    ),
    (re.compile(r"^(table\.|layout\.table)"), _Facts.table, "no table in the deck"),
    (re.compile(r"^(palette|render\.chart_)"), _Facts.chart, "no chart in the deck"),
    (re.compile(r"^bullet"), _Facts.bullets, "no bullet list in the deck"),
    (re.compile(r"^(heading\.|card\.|box\.)"), _Facts.boxes, "no ## box in the deck"),
    (re.compile(r"^(footer|num)\."), _Facts.footer, "no footer: set `footer:` or `num: on`"),
    (re.compile(r"^lead\."), _Facts.lead, "no `>` lead line under a title"),
]


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
