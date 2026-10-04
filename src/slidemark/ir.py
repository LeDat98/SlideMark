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
    fill: str | None = None  # background color of the shape / container
    line: str | None = None  # border color
    line_width: float | None = None  # pt
    radius: float | None = None  # corner radius in pt (rounded rectangle)
    padding: Length | None = None  # inner padding of text frames / containers
    opacity: float | None = None  # 0..1
    shadow: bool | None = None

    def merged(self, *others: Style | None) -> Style:
        """Return a copy where later non-None fields override earlier ones."""
        data = self.model_dump()
        for other in others:
            if other is None:
                continue
            for k, v in other.model_dump().items():
                if v is not None:
                    data[k] = v
        return Style(**data)


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


Element = Annotated[
    Text | Image | Table | Code | Chart | Shape | Raw | Container,
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
    notes: str | None = None
    background: str | None = None  # color, "linear-gradient(...)" or image path
    transition: str | None = None
    hidden: bool = False
    classes: list[str] = Field(default_factory=list)
    attrs: dict[str, Any] = Field(default_factory=dict)
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
    slides: list[Slide] = Field(default_factory=list)
    attrs: dict[str, Any] = Field(default_factory=dict)
    diagnostics: list[Diagnostic] = Field(default_factory=list)


# --------------------------------------------------------------------------- layout output


class Placed(Model):
    """An element with its final absolute box (EMU) and fully merged style. Renderer input."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    element: Element
    x: int
    y: int
    w: int
    h: int
    style: Style = Field(default_factory=Style)
    font_scale: float = 1.0  # autofit shrink factor applied to all font sizes of this element
