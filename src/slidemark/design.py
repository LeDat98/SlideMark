"""Design feedback: did the author make design decisions? (docs/DESIGN_REQUIRED.md, "Tightened rules")

Two warnings and one facts fragment, all computed from the parsed ``Deck`` (no layout, no theme):

- ``design-none``: one warning naming every header line that is missing among ``colors:`` ``fonts:``
  ``sizes:`` ``style:``. A deck ``css`` fence or a theme file (``theme: ./brand.yaml``, a ``.pptx``) stands
  in for ``style:``; ``theme: <preset>`` alone never counts.
- ``design-slide``: one line for the deck listing the content slides that are short of a group. Every content
  slide must state three things (cover, section and notes-only slides are exempt):

  1. **form**: a layout directive (``@3`` ``@2x2`` ``@1:2`` ``@aab/aac``, ``@steps`` ``@chevron`` ``@rows``
     ``@items`` ``@kpi`` ``@free`` ``@html`` ``@timeline`` ...) or a block that is not the default list:
     table, chart, image, code, boxes with headings, KPI cards, mermaid, callout.
  2. **emphasis**: exactly one (``.hero``, ``hl=``, ``==x==``, ``{.accent}`` / ``{.danger}`` /
     ``{.success}``, ``note=``, a badge), or ``@noemph``. Two or more are reported too
     (``emphasis: 2 stated, keep one``).
  3. **values**: at least one chosen value on the slide (``size=`` ``color=`` ``fill=`` ``x y w h``, chart
     ``colors=`` / ``size=`` / ``labels=<pos>``, table ``widths=`` / ``rowh=`` / ``align=``, a slide
     ``sizes:`` / ``style:`` line, ``@bg=``) or ``@defaults``.

- ``facts()``: ``design: colors fonts sizes style footer; 9/14 slides decided form+emphasis+values`` for the
  build output, with ``; short: 4 (values), 8 (form, emphasis)`` when some slides are short.

The detection is table driven: tuples of predicates per group and place (slide, element) say what counts, so
a new attribute that lands in ``classes`` / ``attrs`` / ``style`` / ``box`` / ``options`` needs one line, not
a new algorithm. What the parser derives itself (and ``@build``, ``@t=``, ``@hidden``, which change no look)
counts for nothing.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

from .ir import Chart, Container, Deck, Diagnostic, Slide, Table

# Deck frame ------------------------------------------------------------------------------------------------

# the header lines `design-none` asks for, in the order it names them
REQUIRED_LINES = ("colors", "fonts", "sizes", "style")
# what stands in for `style:` (a deck css fence, a theme file); `theme: <preset>` alone never counts
STYLE_STANDINS = ("css", "theme-file")
DESIGN_KEYS = (*REQUIRED_LINES, *STYLE_STANDINS)
EXTRA_KEYS = ("footer", "num")  # shown in the facts line, not decisions on their own
THEME_FILES = (".yaml", ".yml", ".pptx", ".potx")  # `theme: ./brand.yaml` / a template is a decision
# JSON/API decks have no header record: the group is read from the token path
_TOKEN_PREFIX = {"colors.": "colors", "fonts.": "fonts", "sizes.": "sizes"}

NONE_MESSAGE = "design: {lines} not stated"
NONE_HINT = "add {lines} to the header"
NONE_STYLE_HINT = " (a css fence or theme file also counts for style:)"

# Slide frame -----------------------------------------------------------------------------------------------

GROUPS = ("form", "emphasis", "values")
OPT_OUT = {"emphasis": "noemph", "values": "defaults"}  # `@noemph` / `@defaults`: the agent decided "none"
SLIDE_HINT = (
    "per slide state form (@N @steps table chart), one emphasis (.hero hl= ==x==) or @noemph, "
    "a value (size= color= fill= x y w h) or @defaults"
)
MAX_SHOWN = 8

EXEMPT_LAYOUTS = ("cover", "section")  # titles carry no content to decide on
# classes the parser adds for a block kind (callout, mermaid diagram, row group): not an author's choice
AUTO_CLASSES = {
    "plain",
    "group",
    "node",
    "decision",
    "round",
    "note",
    "tip",
    "warn",
    "warning",
    "caution",
    "important",
}
# element classes by group; any other class on an element is an author-defined CSS class = a chosen value
FORM_CLASSES = {
    "kpi",
    "card",
    "steps",
    "flow",
    "chevron",
    "rows",
    "items",
    "num",
    "timeline",
    "diagram",
    "callout",
}
EMPHASIS_CLASSES = {"hero", "accent", "danger", "success"}
# slide (`@` line) classes: words that change only the look are values, a few are neither, the rest are forms
SLIDE_VALUE_CLASSES = {"dense", "dark", "light"}
SLIDE_NEUTRAL_CLASSES = {"build", "noemph", "defaults"}  # animation / the two opt-out directives
IGNORED_ATTRS = {"html_src", "html_info"}  # kept by the parser for the importer
EMPHASIS_KEYS = {"hl", "hlcol", "hl_series", "note"}  # table attrs / chart options that mark the takeaway
# chart options that are a switch or derived from the data, not a chosen value
NEUTRAL_OPTIONS = {"totals", "percent", "grouped", "labels", "label_name", *EMPHASIS_KEYS}
FORM_TYPES = {
    "table",
    "chart",
    "image",
    "media",
    "code",
    "shape",
    "raw",
}  # blocks that are not the default list
# per element type: extra fields that are a choice when they differ from the default shown
FIELD_DEFAULTS: dict[str, dict[str, Any]] = {
    "image": {"fit": "contain"},
    "media": {"poster": None, "autoplay": False, "loop": False},
    "table": {"col_widths": None, "rowh": None},
}
# per run: a field that is set is inline emphasis (`==x==` = accent color, `[x]{.class}`, badge = highlight)
RUN_EMPHASIS = ("color", "highlight")


def stated(deck: Deck) -> list[str]:
    """What the deck header decided: colors fonts sizes style css theme-file (then footer num)."""
    got: list[str] = list(deck.attrs.get("design_stated") or [])
    if "design_stated" not in deck.attrs:  # decks built from JSON or Python carry tokens but no header record
        for path in deck.tokens:
            key = next((v for p, v in _TOKEN_PREFIX.items() if path.startswith(p)), "style")
            if key not in got:
                got.append(key)
    if deck.css and "css" not in got and "style" not in got:
        got.append("css")
    if deck.theme.strip().lower().endswith(THEME_FILES):
        got.append("theme-file")
    if deck.footer:
        got.append("footer")
    if deck.slide_number:
        got.append("num")
    order = (*DESIGN_KEYS, *EXTRA_KEYS)
    return sorted(set(got), key=lambda k: order.index(k) if k in order else len(order))


def missing_lines(deck: Deck) -> list[str]:
    """The header lines still to state among ``colors`` ``fonts`` ``sizes`` ``style`` (a css fence or a theme
    file stands in for ``style``)."""
    got = set(stated(deck))
    if got & set(STYLE_STANDINS):
        got.add("style")
    return [k for k in REQUIRED_LINES if k not in got]


def _walk(slide: Slide) -> Iterator[Any]:
    """Every element of a slide, nested ones too, with the roles the parser lifted out of the body."""

    def rec(el: Any) -> Iterator[Any]:
        yield el
        if isinstance(el, Container):
            if el.title is not None:
                yield from rec(el.title)
            for c in el.children:
                yield from rec(c)

    for el in (slide.title, slide.subtitle, slide.lead, slide.conclusion, *slide.footnotes, *slide.elements):
        if el is not None:
            yield from rec(el)


def _paragraphs(el: Any) -> Iterator[Any]:
    yield from getattr(el, "paragraphs", None) or []
    if isinstance(el, Table):
        for row in el.rows:
            for cell in row:
                yield from cell.paragraphs


def _styled(style: Any) -> bool:
    return style is not None and any(v is not None for v in style.__dict__.values())


def _value_class(c: str) -> bool:
    return c not in AUTO_CLASSES and c not in FORM_CLASSES and c not in EMPHASIS_CLASSES


def _chart_value(el: Any) -> bool:
    if not isinstance(el, Chart):
        return False
    o = el.options
    return any(k not in NEUTRAL_OPTIONS for k in o) or "label_pos" in o or "label_points" in o


# Three tuples of element predicates, one per group: each takes an element and says whether it states one.
FORM_ELEMENT: tuple[Callable[[Any], bool], ...] = (
    lambda el: el.type in FORM_TYPES,  # table, chart, image, code, ...
    lambda el: any(c in FORM_CLASSES for c in el.classes),  # kpi cards, steps, callout, mermaid diagram
    lambda el: (
        isinstance(el, Container) and (el.title is not None or bool(el.grid or el.links))
    ),  # `##` boxes
)
EMPHASIS_ELEMENT: tuple[Callable[[Any], bool], ...] = (
    lambda el: any(c in EMPHASIS_CLASSES for c in el.classes),  # {.hero} {.accent} {.danger} {.success}
    lambda el: bool(EMPHASIS_KEYS & set(el.attrs)),  # table hl= hlcol= note=
    lambda el: isinstance(el, Chart) and bool(EMPHASIS_KEYS & set(el.options)),  # chart hl= note=
)
VALUE_ELEMENT: tuple[Callable[[Any], bool], ...] = (
    lambda el: any(_value_class(c) for c in el.classes),  # {.zebra} {.primary} {.brand}
    lambda el: any(k not in IGNORED_ATTRS and k not in EMPHASIS_KEYS for k in el.attrs),  # {icon=...}
    lambda el: _styled(el.style),  # {size= fill= color= align= ...}
    lambda el: el.box is not None and any(v is not None for v in el.box.model_dump().values()),  # {x y w h}
    _chart_value,  # colors= size= labels=<pos> legend= fmt= ...
    lambda el: any(el.__dict__.get(f, d) != d for f, d in FIELD_DEFAULTS.get(el.type, {}).items()),  # widths=
    lambda el: isinstance(el, Container) and el.gap is not None,  # a box's own `@gap=`
    lambda el: isinstance(el, Table) and any(_styled(c.style) for r in el.rows for c in r),  # align=
    lambda el: any(_styled(p.style) for p in _paragraphs(el)),
)

# Three tuples of slide predicates (the `@` line, a slide css fence, `# Title {bg=...}`).
FORM_SLIDE: tuple[Callable[[Slide], bool], ...] = (
    lambda s: s.layout is not None and s.layout not in EXEMPT_LAYOUTS,  # @blank @center @free
    lambda s: s.grid is not None,  # @3 @2x2 @1:2 @aab/aac
    lambda s: any(c not in SLIDE_VALUE_CLASSES | SLIDE_NEUTRAL_CLASSES for c in s.classes),  # @steps @kpi ...
    lambda s: s.html is not None,  # @html
    lambda s: bool(s.links),  # @ a>b connectors
)
EMPHASIS_SLIDE: tuple[Callable[[Slide], bool], ...] = (lambda s: OPT_OUT["emphasis"] in s.classes,)  # @noemph
VALUE_SLIDE: tuple[Callable[[Slide], bool], ...] = (
    lambda s: OPT_OUT["values"] in s.classes,  # @defaults
    lambda s: any(c in SLIDE_VALUE_CLASSES for c in s.classes),  # @dense @dark @light
    lambda s: bool(s.attrs),  # @gap= and unknown keys
    lambda s: s.background is not None,  # @bg=
    lambda s: bool(s.css) or bool(s.tokens),  # a ```css fence or a `sizes:` / `style:` line in the slide
)


def _marked(el: Any) -> bool:
    return any(getattr(r, f) for p in _paragraphs(el) for r in p.runs for f in RUN_EMPHASIS)


def emphasis_count(slide: Slide) -> int:
    """Emphases on the slide, one per element that carries any: an attribute (``.hero`` ``hl=`` ``note=``; a
    chart's ``hl=`` + ``note=`` are one takeaway) or an inline mark (``==x==``, ``[x]{.danger}``, a badge; a
    column of status badges in one table is one emphasis)."""
    return sum(1 for el in _walk(slide) if any(p(el) for p in EMPHASIS_ELEMENT) or _marked(el))


def stated_groups(slide: Slide) -> dict[str, bool]:
    """Which of form / emphasis / values the slide states (emphasis only when exactly one, or ``@noemph``)."""
    els = list(_walk(slide))
    return {
        "form": any(p(slide) for p in FORM_SLIDE) or any(p(el) for el in els for p in FORM_ELEMENT),
        "emphasis": any(p(slide) for p in EMPHASIS_SLIDE) or emphasis_count(slide) == 1,
        "values": any(p(slide) for p in VALUE_SLIDE) or any(p(el) for el in els for p in VALUE_ELEMENT),
    }


def exempt(slide: Slide) -> bool:
    """Cover and section slides, and slides with nothing but a title (and notes): nothing to decide on."""
    if slide.layout in EXEMPT_LAYOUTS:
        return True
    body = (slide.elements, slide.lead, slide.conclusion, slide.footnotes, slide.subtitle, slide.html)
    return not any(body)


def slide_shortfalls(deck: Deck) -> tuple[dict[int, list[str]], int]:
    """({1-based slide number: groups it is short of}, number of slides judged); decided slides are absent."""
    short: dict[int, list[str]] = {}
    judged = 0
    for i, s in enumerate(deck.slides, 1):
        if exempt(s):
            continue
        judged += 1
        got = stated_groups(s)
        if lacking := [g for g in GROUPS if not got[g]]:
            short[i] = lacking
    return short, judged


def _reason(slide: Slide, group: str) -> str:
    if group == "emphasis" and (n := emphasis_count(slide)) > 1:
        return f"emphasis: {n} stated, keep one"
    return group


def _listing(entries: list[tuple[int, str]], limit: int = MAX_SHOWN) -> str:
    shown = ", ".join(f"{n} ({what})" for n, what in entries[:limit])
    return shown + (f" and {len(entries) - limit} more" if len(entries) > limit else "")


def design_diagnostics(deck: Deck) -> list[Diagnostic]:
    """``design-none`` and ``design-slide`` (warnings, one each per deck). Never raises."""
    out: list[Diagnostic] = []
    try:
        if lines := missing_lines(deck):
            names = " ".join(f"{k}:" for k in lines)
            hint = NONE_HINT.format(lines=names) + (NONE_STYLE_HINT if "style" in lines else "")
            out.append(
                Diagnostic(
                    level="warning",
                    message=NONE_MESSAGE.format(lines=names),
                    rule="design-none",
                    hint=hint,
                )
            )
        short, _ = slide_shortfalls(deck)
        if short:
            entries = [
                (n, ", ".join(_reason(deck.slides[n - 1], g) for g in groups)) for n, groups in short.items()
            ]
            word = "slides" if len(entries) > 1 else "slide"
            verb = "are" if len(entries) > 1 else "is"
            out.append(
                Diagnostic(
                    level="warning",
                    message=f"{word} {_listing(entries)} {verb} short of a decision",
                    rule="design-slide",
                    hint=SLIDE_HINT,
                )
            )
    except Exception:  # feedback must never break a build
        return out
    return out


def facts(deck: Deck) -> str:
    """``design: colors fonts style; 9/14 slides decided form+emphasis+values; short: 4 (values)``."""
    try:
        keys = stated(deck)
        short, total = slide_shortfalls(deck)
        done = f"{total - len(short)}/{total} slides decided {'+'.join(GROUPS)}"
        line = f"design: {' '.join(keys) or 'none'}; {done}"
        if short:
            line += "; short: " + _listing([(n, ", ".join(g)) for n, g in short.items()])
        return line
    except Exception:
        return ""


__all__ = ["design_diagnostics", "facts", "stated", "missing_lines", "slide_shortfalls", "stated_groups"]
