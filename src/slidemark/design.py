"""Design feedback: did the author make design decisions? (docs/DESIGN_REQUIRED.md, "Build feedback")

Two warnings and one facts fragment, all computed from the parsed ``Deck`` (no layout, no theme):

- ``design-none``: the deck header states none of ``colors:`` ``fonts:`` ``sizes:`` ``style:`` and has no deck
  ``css`` fence, and ``theme:`` is a built-in preset (a ``.yaml`` or ``.pptx`` theme counts as a decision).
- ``design-slide``: one line for the deck, listing the slides on which no element carries a choice.
- ``facts()``: ``design: colors fonts style footer; 12/15 slides carry choices`` for the build output.

A *choice* is anything an author writes beyond the content and its block kind: ``{attrs}`` on a heading,
image or block, an option on a table or chart, an ``@`` directive such as ``@steps`` ``@3`` ``@free`` ``@bg=``
``@dark``, a slide ``css`` fence, inline emphasis (``==x==``, ``[x]{.class}``, badges). The detection is table
driven: every field below is "a choice when it differs from its default", so a new attribute that lands in
``classes`` / ``attrs`` / ``style`` / ``box`` / ``options`` needs no new code. Only values the parser derives
itself (and ``@build``, ``@t=``, ``@hidden``, which change no look) are listed as ignored.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

from .ir import Chart, Container, Deck, Diagnostic, Slide, Table

# Deck frame ------------------------------------------------------------------------------------------------

# the decisions `design-none` asks for
DESIGN_KEYS = ("colors", "fonts", "sizes", "style", "css", "theme-file")
EXTRA_KEYS = ("footer", "num")  # shown in the facts line, not decisions on their own
THEME_FILES = (".yaml", ".yml", ".pptx", ".potx")  # `theme: ./brand.yaml` / a template is a decision
# JSON/API decks have no header record: the group is read from the token path
_TOKEN_PREFIX = {"colors.": "colors", "fonts.": "fonts", "sizes.": "sizes"}

NONE_MESSAGE = "no design stated"
NONE_HINT = "state your design: colors: fonts: sizes: style: (or a css fence)"
SLIDE_HINT = (
    "choose the form (list/cards/@steps/@cols/table/chart/@html), one emphasis ({.hero} hl= ==x==) "
    "or an override (size= fill= color= align= x y w h) per slide"
)

# Slide frame -----------------------------------------------------------------------------------------------

EXEMPT_LAYOUTS = ("cover", "section")  # titles carry no content to decide on
IGNORED_SLIDE_CLASSES = {"build"}  # animation only
IGNORED_SLIDE_ATTRS: set[str] = set()  # `@t=`, `@hidden` have their own fields and are never looked at below
# classes the parser adds for a block kind (callout, mermaid diagram, row group): not an author's choice
AUTO_CLASSES = {
    "plain",
    "group",
    "diagram",
    "node",
    "decision",
    "round",
    "callout",
    "note",
    "tip",
    "warn",
    "warning",
    "caution",
    "important",
}
IGNORED_ATTRS = {"html_src", "html_info"}  # kept by the parser for the importer
IGNORED_OPTIONS = {"totals", "percent", "grouped"}  # derived from the chart data
# per element type: extra fields that are a choice when they differ from the default shown
FIELD_DEFAULTS: dict[str, dict[str, Any]] = {
    "image": {"fit": "contain"},
    "media": {"poster": None, "autoplay": False, "loop": False},
    "table": {"col_widths": None, "header_rows": 1, "header_cols": 0},
}
# per run: a field that is set is inline emphasis (`==x==` = accent color, `[x]{.class}`, badge = highlight)
RUN_CHOICES = ("color", "highlight")


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


# One predicate per place a choice can sit; each takes an element and says whether it carries one.
ELEMENT_CHOICES: tuple[Callable[[Any], bool], ...] = (
    lambda el: any(c not in AUTO_CLASSES for c in el.classes),  # {.hero} {.zebra} @steps on a group
    lambda el: any(k not in IGNORED_ATTRS for k in el.attrs),  # {hl=...} {icon=...} {render=...}
    lambda el: _styled(el.style),  # {size= fill= color= align= ...}
    lambda el: el.box is not None and any(v is not None for v in el.box.model_dump().values()),  # {x y w h}
    lambda el: isinstance(el, Chart) and any(k not in IGNORED_OPTIONS for k in el.options),
    lambda el: any(el.__dict__.get(f, d) != d for f, d in FIELD_DEFAULTS.get(el.type, {}).items()),
    lambda el: (
        isinstance(el, Container)  # a `##` box with its own `@` line; mermaid grids are generated
        and "diagram" not in el.classes
        and bool(el.links or el.grid or el.gap is not None)
    ),
    lambda el: isinstance(el, Table) and any(_styled(c.style) for r in el.rows for c in r),  # align=
    lambda el: any(getattr(r, f) for p in _paragraphs(el) for r in p.runs for f in RUN_CHOICES),
    lambda el: any(_styled(p.style) for p in _paragraphs(el)),
)

# One predicate per slide-level place (the `@` line, a slide css fence, the `# Title {bg=...}` attributes).
SLIDE_CHOICES: tuple[Callable[[Slide], bool], ...] = (
    lambda s: s.layout is not None and s.layout not in EXEMPT_LAYOUTS,  # @blank @center @free
    lambda s: s.grid is not None,  # @3 @2x2 @1:2 @aab/aac
    lambda s: any(c not in IGNORED_SLIDE_CLASSES for c in s.classes),  # @steps @chevron @dark @dense
    lambda s: any(k not in IGNORED_SLIDE_ATTRS for k in s.attrs),  # @gap= and unknown keys
    lambda s: s.background is not None,  # @bg=
    lambda s: s.html is not None,  # @html
    lambda s: bool(s.css),  # a ```css fence in the slide
    lambda s: bool(s.links),  # @ a>b connectors
)


def carries_choice(slide: Slide) -> bool:
    return any(p(slide) for p in SLIDE_CHOICES) or any(p(el) for el in _walk(slide) for p in ELEMENT_CHOICES)


def exempt(slide: Slide) -> bool:
    """Cover and section slides, and slides with nothing but a title (and notes): nothing to decide on."""
    if slide.layout in EXEMPT_LAYOUTS:
        return True
    body = (slide.elements, slide.lead, slide.conclusion, slide.footnotes, slide.subtitle, slide.html)
    return not any(body)


def slides_without_choice(deck: Deck) -> tuple[list[int], int]:
    """(1-based numbers of the slides without any choice, number of slides that are judged)."""
    judged = [(i, s) for i, s in enumerate(deck.slides, 1) if not exempt(s)]
    return [i for i, s in judged if not carries_choice(s)], len(judged)


def _numbers(nums: list[int], limit: int = 12) -> str:
    shown = ", ".join(str(n) for n in nums[:limit])
    return shown + (f" and {len(nums) - limit} more" if len(nums) > limit else "")


def design_diagnostics(deck: Deck) -> list[Diagnostic]:
    """``design-none`` and ``design-slide`` (warnings, one each per deck). Never raises."""
    out: list[Diagnostic] = []
    try:
        if not set(stated(deck)) & set(DESIGN_KEYS):
            out.append(Diagnostic(level="warning", message=NONE_MESSAGE, rule="design-none", hint=NONE_HINT))
        bare, _ = slides_without_choice(deck)
        if bare:
            word = "slides" if len(bare) > 1 else "slide"
            verb = "carry" if len(bare) > 1 else "carries"
            out.append(
                Diagnostic(
                    level="warning",
                    message=f"{word} {_numbers(bare)} {verb} no design choice",
                    rule="design-slide",
                    hint=SLIDE_HINT,
                )
            )
    except Exception:  # feedback must never break a build
        return out
    return out


def facts(deck: Deck) -> str:
    """``design: colors fonts style footer; 12/15 slides carry choices`` (``design: none; 0/15 ...``)."""
    try:
        keys = stated(deck)
        bare, total = slides_without_choice(deck)
        return f"design: {' '.join(keys) or 'none'}; {total - len(bare)}/{total} slides carry choices"
    except Exception:
        return ""


__all__ = ["design_diagnostics", "facts", "stated", "slides_without_choice"]
