"""Intermediate representation (IR): the single contract between parser, layout and renderer.

Every input format (Markdown, HTML, JSON, Python API) is converted to a ``Deck``.
Layout turns each ``Slide`` into a flat list of ``Placed`` items with absolute EMU boxes,
and the renderer only ever consumes ``Placed`` items.

Lengths in the IR are kept as strings or numbers exactly as the author wrote them
(``"50%"``, ``"2in"``, ``"36pt"``, ``"3cm"``, ``"120px"``, bare numbers = pt); resolve them
with :func:`slidemark.units.to_emu`.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Length = str | float | int


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------- style


class Style(Model):
    """Visual overrides. Every field is optional; ``None`` means "inherit from theme"."""

    font: str | None = None
    font_ea: str | None = None  # East Asian (CJK) typeface, written to <a:ea>
    font_size: float | None = None  # pt
    color: str | None = None  # "#RRGGBB" or theme color name ("primary", "muted", ...)
    bold: bool | None = None
    italic: bool | None = None
    align: Literal["left", "center", "right", "justify"] | None = None
    valign: Literal["top", "middle", "bottom"] | None = None
    line_spacing: float | None = None  # multiple of font size, e.g. 1.2
    # background: a color, or a CSS gradient "linear-gradient(135deg, #7C5CFF, #00D1B2)" / radial
    fill: str | None = None
    line: str | None = None  # border color
    line_width: float | None = None  # pt
    radius: float | None = None  # corner radius in pt (rounded rectangle)
    padding: Length | None = None  # inner padding of text frames / containers
    opacity: float | None = None  # 0..1
    # True = theme default shadow; or CSS box-shadow "0 8 24 #00000055" (x y blur [spread] color, pt)
    shadow: bool | str | None = None
    # --- CSS mappings (DF3; ```css fences). All optional, None = inherit ---
    padding_top: Length | None = None  # per-side padding, overrides `padding` on that side
    padding_right: Length | None = None
    padding_bottom: Length | None = None
    padding_left: Length | None = None
    # per-side borders, canonical "<width>pt <solid|dash|dot> <color>" or "none"; override line/line_width
    border_top: str | None = None
    border_right: str | None = None
    border_bottom: str | None = None
    border_left: str | None = None
    line_dash: Literal["solid", "dash", "dot"] | None = None  # border style of `line`
    letter_spacing: float | None = None  # pt, added between characters
    text_transform: Literal["upper", "lower", "capitalize", "none"] | None = None
    underline: bool | None = None
    strike: bool | None = None
    rotation: float | None = None  # degrees clockwise (CSS transform: rotate())
    margin: Length | None = None  # outer space around a block inside its cell
    gap: Length | None = None  # gap between the children of a container / slide body
    grid: str | None = None  # `@` grid spec from grid-template-columns / -areas ("1:2", "aab/aac")
    width: str | None = (
        None  # CSS width of a block: "fit-content" (hug the text), "auto", "40%", "3in", "120pt"
    )

    def merged(self, *others: Style | None) -> Style:
        """Return a copy where later non-None fields override earlier ones."""
        data = dict(self.__dict__)
        for other in others:
            if other is None:
                continue
            data.update({k: v for k, v in other.__dict__.items() if v is not None})
        # values come from validated Styles: build the instance directly (model_construct is slow)
        out = object.__new__(Style)
        object.__setattr__(out, "__dict__", data)
        object.__setattr__(out, "__pydantic_fields_set__", set())  # never read: skip the 60-key copy
        object.__setattr__(out, "__pydantic_extra__", None)
        object.__setattr__(out, "__pydantic_private__", None)
        return out


_STYLE_BLANK: dict | None = None


def fast_style(**kw) -> Style:
    """Build a Style from trusted values without pydantic validation (layout internals, hot path)."""
    global _STYLE_BLANK
    if _STYLE_BLANK is None:
        _STYLE_BLANK = dict(Style().__dict__)
    data = dict(_STYLE_BLANK)
    data.update(kw)
    out = object.__new__(Style)
    object.__setattr__(out, "__dict__", data)
    object.__setattr__(out, "__pydantic_fields_set__", set(kw))
    object.__setattr__(out, "__pydantic_extra__", None)
    object.__setattr__(out, "__pydantic_private__", None)
    return out


class CssRule(Model):
    """One rule of a ```css fence: a single selector (comma lists are split) and its mapped declarations.

    Selector grammar (subset of CSS, matched by the layout against the IR):
    compound = [type] [.class]* [#id] [:nth-child(even|odd|N)] [:first-child] [:last-child]
    selector = compound ((" " | " > ") compound)*
    types: ``slide`` (classes = slide classes + ``cover``/``section`` layout), ``h1`` (slide title),
    ``h2`` (box heading), ``p``/``li`` (body text), ``.lead`` ``.conclusion`` ``.footnote`` ``.subtitle``
    (role classes), ``.box`` (any ``##`` box / Container), ``table`` ``tr`` ``th`` ``td``, ``code``,
    ``img``, ``.chart``, ``.kpi`` ``.chevron`` ``.callout`` and any class/id written with ``{.x}``/``{#x}``.
    Later rules and higher specificity win, like CSS; inline ``{}`` styles win over CSS.
    """

    selector: str
    style: Style
    line: int | None = None  # source line of the rule, for diagnostics


class Box(Model):
    """Explicit position/size. Any missing field is decided by the layout engine."""

    x: Length | None = None
    y: Length | None = None
    w: Length | None = None
    h: Length | None = None


# --------------------------------------------------------------------------- text


class Run(Model):
    text: str
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strike: bool = False
    code: bool = False
    sup: bool = False
    sub: bool = False
    color: str | None = None
    highlight: str | None = None
    link: str | None = None  # URL, or "#<slide-id>" / "#3" for an internal jump


class Paragraph(Model):
    runs: list[Run] = Field(default_factory=list)
    marker: Literal["bullet", "number"] | None = None  # list paragraph if set
    level: int = 0  # list nesting depth, 0-based
    style: Style | None = None

    @property
    def plain(self) -> str:
        return "".join(r.text for r in self.runs)


# --------------------------------------------------------------------------- elements


class ElementBase(Model):
    id: str | None = None
    box: Box | None = None
    style: Style | None = None
    classes: list[str] = Field(default_factory=list)  # theme classes, e.g. ["card", "dense"]
    attrs: dict[str, Any] = Field(default_factory=dict)  # unknown {key=value} attributes, kept for lint
    line: int | None = None  # 1-based source line, for diagnostics


class Text(ElementBase):
    type: Literal["text"] = "text"
    # title/subtitle are set by the parser; others come from syntax (blockquote -> "quote", ...)
    role: Literal[
        "title", "subtitle", "heading", "body", "quote", "lead", "conclusion", "caption", "footnote"
    ] = "body"
    paragraphs: list[Paragraph] = Field(default_factory=list)


class Image(ElementBase):
    type: Literal["image"] = "image"
    src: str
    alt: str = ""
    fit: Literal["contain", "cover", "stretch"] = "contain"


class Media(ElementBase):
    """Embedded video or audio. Written as an image whose path has a media extension: `![demo](a.mp4)`."""

    type: Literal["media"] = "media"
    kind: Literal["video", "audio"] = "video"
    src: str
    alt: str = ""
    poster: str | None = None  # image shown before playback; None = a generated placeholder frame
    autoplay: bool = False
    loop: bool = False


class Cell(Model):
    paragraphs: list[Paragraph] = Field(default_factory=list)
    colspan: int = 1
    rowspan: int = 1
    style: Style | None = None


class Table(ElementBase):
    type: Literal["table"] = "table"
    rows: list[list[Cell]] = Field(default_factory=list)
    header_rows: int = 1
    header_cols: int = 0
    col_widths: list[Length] | None = None  # relative weights or lengths
    rowh: list[str] | None = (
        None  # `{rowh=0.8in,1.05in}`: exact row heights ("auto" = free); the last repeats
    )


class Code(ElementBase):
    type: Literal["code"] = "code"
    lang: str | None = None
    text: str = ""


class Series(Model):
    name: str
    values: list[float | None]


class Chart(ElementBase):
    type: Literal["chart"] = "chart"
    kind: Literal[
        "bar",
        "column",
        "stacked-bar",
        "stacked-column",
        "line",
        "area",
        "pie",
        "doughnut",
        "scatter",
        "radar",
        "waterfall",  # one series: first value absolute, then deltas; "=" cells are running totals
    ] = "column"
    title: str | None = None
    categories: list[str] = Field(default_factory=list)
    series: list[Series] = Field(default_factory=list)
    options: dict[str, Any] = Field(default_factory=dict)  # legend, labels, number_format, ...


class Shape(ElementBase):
    """Auto shape with optional text: rect, rounded-rect, ellipse, arrow-right, chevron, ..."""

    type: Literal["shape"] = "shape"
    shape: str = "rect"
    paragraphs: list[Paragraph] = Field(default_factory=list)


class Raw(ElementBase):
    """Content handled by a later stage (html, mermaid, math). Renderers may skip unknown kinds."""

    type: Literal["raw"] = "raw"
    kind: str
    source: str = ""


class Link(Model):
    """A connector between two blocks of the same grid (``@`` token ``a>b`` or ``a-b``).

    ``src``/``dst`` are 0-based indices into the owner's blocks (``Slide.elements`` or ``Container.children``)
    in source order. ``arrow`` is False for a plain line (``a-b``).
    """

    src: int
    dst: int
    arrow: bool = True
    label: str | None = None


class Container(ElementBase):
    """A box that lays out its children: a ``## heading`` box, or the slide body itself.

    ``title`` is the box heading (``None`` for an untitled group). ``grid`` is the raw ``@`` layout spec
    for the children (``"3"``, ``"2x2"``, ``"1:2"``, ``"aab/aac"``); ``None`` means automatic.
    Flags such as ``flow``/``chevron`` from the ``@`` line go to ``classes``.
    """

    type: Literal["container"] = "container"
    title: Text | None = None
    grid: str | None = None
    gap: Length | None = None
    children: list[Element] = Field(default_factory=list)
    links: list[Link] = Field(default_factory=list)  # connectors between children (`@` tokens a>b)


Element = Annotated[
    Text | Image | Media | Table | Code | Chart | Shape | Raw | Container,
    Field(discriminator="type"),
]
Container.model_rebuild()


# --------------------------------------------------------------------------- slide / deck


class Slide(Model):
    id: str | None = None
    layout: str | None = None  # "cover" | "section" | "blank" | "center"; None = infer from content
    grid: str | None = None  # raw `@` grid spec for the slide's blocks; None = automatic
    title: Text | None = None
    subtitle: Text | None = None
    lead: Text | None = None  # `>` right after the title
    conclusion: Text | None = None  # `>` as the last block
    footnotes: list[Text] = Field(default_factory=list)  # `※` / `^` lines
    elements: list[Element] = Field(default_factory=list)  # the blocks, in source order
    links: list[Link] = Field(default_factory=list)  # connectors between blocks (`@` tokens a>b)
    notes: str | None = None
    background: str | None = None  # color, "linear-gradient(...)" or image path
    transition: str | None = None
    hidden: bool = False
    classes: list[str] = Field(default_factory=list)
    attrs: dict[str, Any] = Field(default_factory=dict)
    css: list[CssRule] = Field(default_factory=list)  # ```css fences inside this slide: this slide only
    # `@html` slide or a `<section>` of a deck.html: the whole slide is this HTML (laid out by Chromium at the
    # slide size, converted to native shapes). `title` is still set (outline, import); nothing else is drawn
    html: str | None = None
    line: int | None = None


class Diagnostic(Model):
    level: Literal["error", "warning", "info"]
    message: str
    line: int | None = None
    slide: int | None = None  # 1-based slide index
    rule: str | None = None
    hint: str | None = None

    def __str__(self) -> str:  # one line, cheap to read for an agent
        parts = [f"slide {self.slide}" if self.slide else "", f"L{self.line}" if self.line else ""]
        where = " ".join(p for p in parts if p)
        hint = f" -> {self.hint}" if self.hint else ""
        return f"{self.level} {where} {self.rule or ''}: {self.message}{hint}".replace("  ", " ")


class Deck(Model):
    title: str | None = None
    author: str | None = None
    theme: str = "default"
    size: str = "16:9"  # "16:9", "4:3", "A4", or "<w>x<h>" lengths
    lang: str | None = None  # e.g. "ja", "vi", "en"
    footer: str | None = None
    slide_number: bool = False
    density: Literal["normal", "dense"] = "normal"
    # inline design tokens from header lines (colors:/fonts:/sizes:/style:), canonical path -> raw value,
    # e.g. {"colors.primary": "#7C5CFF", "classes.card.radius": "14"}; applied on top of `theme`
    tokens: dict[str, str] = Field(default_factory=dict)
    css: list[CssRule] = Field(default_factory=list)  # ```css fences in the deck header: every slide
    slides: list[Slide] = Field(default_factory=list)
    attrs: dict[str, Any] = Field(default_factory=dict)
    diagnostics: list[Diagnostic] = Field(default_factory=list)


# --------------------------------------------------------------------------- layout output


class Placed(Model):
    """An element with its final absolute box (EMU) and fully merged style. Renderer input.

    Conventions between layout and renderer (z-order = list order):
    - Slide title / subtitle / lead / conclusion / footnotes are ``Text`` items with that ``role``.
    - A ``Container`` Placed is only its card (fill/line/radius from ``style``); its heading is a separate
      ``Text(role="heading")`` Placed and its children are separate Placed items, never nested.
    - Footer and slide number are ``Text(role="caption")`` with ``attrs={"field": "footer"|"slide_number"}``;
      for ``slide_number`` the renderer emits a native slide-number field.
    - ``flow`` arrows are ``Shape(shape="arrow-right")``; ``chevron`` boxes are ``Shape(shape="chevron")``
      carrying their paragraphs.
    - ``Placed.style`` is already merged (theme role -> classes -> inline); colors may still be theme names,
      resolve them with ``Theme.color``. ``font_scale`` multiplies every font size of the element.
    - Connectors (``Link``) are ``Shape(shape="line")`` with ``attrs={"head": "arrow"|"none",
      "flip_h": bool, "flip_v": bool}``: a straight line from one corner of the box to the opposite one.
      Elbow connectors add ``"elbow": True, "route": "v"|"h", "adj": 0..1`` (bend position) and
      ``"src_box"``/``"dst_box"`` ``(x, y, w, h)`` so the renderer can glue both ends to the block shapes.
    - ``.kpi`` boxes: the first paragraph is the big number (role style ``kpi``), the rest is caption text.
    - Callouts (``> [!note]``) are ``Text`` with classes ``["callout", "<kind>"]``; badges are runs with
      ``highlight`` set (theme color name) and ``color`` for the text.
    - Icons (``icon=name`` on a box) are ``Shape(shape="icon", attrs={"icon": name})`` Placed items; the
      renderer draws them as native custom geometry filled with ``style.fill`` (or ``style.color``).
    - Slide-level settings (background, notes, hidden, transition, ids) come from ``Slide``.
    """

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    element: Element
    x: int
    y: int
    w: int
    h: int
    style: Style = Field(default_factory=Style)
    font_scale: float = 1.0  # autofit shrink factor applied to all font sizes of this element
