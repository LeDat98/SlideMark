"""Theme model: the public design-token schema shared by layout (sizes, spacing) and renderer (colors, fonts).

Design freedom (docs/DESIGN_FREEDOM.md): SlideMark ships mechanisms, not looks. Every visual decision is a
token in this schema. Built-in themes are YAML presets in ``presets/`` written in the same schema an agent can
write (``theme: ./brand.yaml``) or override inline with header lines (``colors:``, ``fonts:``, ``sizes:``,
``style:``, see :func:`apply_tokens`). ``theme: none`` is the bare schema defaults (a neutral canvas).
"""

from __future__ import annotations

import copy
import difflib
import re
from functools import cache
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .contrast import best_ink, nearest_passing, ratio
from .ir import Diagnostic, Length, Style

PRESET_DIR = Path(__file__).parent / "presets"


class Fonts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    heading: str = "Calibri"
    body: str = "Calibri"
    mono: str = "Consolas"
    ea: str = "Yu Gothic"  # East Asian typeface for ja/zh/ko text (written to <a:ea>)


class LayoutTokens(BaseModel):
    """Layout constants that change the look (gaps, line heights, component sizes, growth limits).

    Lengths are ``Length`` strings (bare numbers = pt); ratios are plain floats. Defaults reproduce the
    original look. Algorithm internals (search weights, step lists, tolerances) are not tokens.
    """

    model_config = ConfigDict(extra="forbid")

    top_gap: Length = "0.25in"  # title band (or lead) -> body, the same on every slide
    line_latin: float = 1.2  # line height / font size for Latin text
    line_cjk: float = 1.3  # ... for CJK text
    para_gap: float = 0.25  # space before every paragraph but the first, x font size
    cell_pad_x: Length = "0.1in"  # table cell margins
    cell_pad_y: Length = "0.05in"
    dense_tight: float = 0.7  # gap / padding factor on dense slides
    kpi_min_h: Length = "1.1in"
    icon_head: float = 1.2  # icon side / heading font size
    icon_kpi: float = 2.0  # icon side / kpi label font size
    icon_gap: float = 0.4  # gap between icon and text, in icon sides
    chevron_adj: float = 0.3  # chevron point depth / shorter side
    chevron_adj_min: float = 0.16  # flattest point depth the layout may choose to widen the text area
    chevron_text_share: float = 0.6  # text area >= this share of the chevron width
    chevron_adj_step: float = 0.02  # step of that search
    chevron_word_slack: float = 1.08  # a word must fit this much narrower (wider fonts)
    chevron_pad: Length = "4pt"
    chevron_min_h: Length = "0.7in"
    chevron_max_h: Length = "1.3in"
    chevron_vpad: Length = "0.17in"
    footnote_max: float = 0.2  # footnotes never take more than this share of the slide height
    math_grow: float = 1.6  # an equation alone in its cell is this much larger than body text
    grow: bool = True  # sparse slides grow text / cards to fill the body (False = keep nominal sizes)
    box_pad: Length = "10pt"  # inner padding of a box whose style has none
    # --- icons and chevrons
    chevron_max_alone: Length = "2.0in"  # a chevron row that is all the slide holds may be this tall ...
    chevron_alone_share: float = 0.28  # ... aiming at this share of the body height
    # --- growth of sparse slides (ratios of the nominal size)
    code_grow: float = 1.25  # code text grows up to this factor
    table_grow: float = 1.4  # rows of a table with spare room grow up to this factor
    table_font_grow: float = 1.2  # table text grows up to this factor
    table_alone_grow: float = 2.6  # a table alone on a normal slide: rows grow up to this factor ...
    table_alone_font_grow: float = 1.45  # ... and its text up to this factor
    kpi_text_grow: bool = True  # free text under a KPI row grows with the sparse-slide growth (box-text size)
    kpi_grow_max: float = 1.7  # a KPI card beside free text grows its text up to this factor (1 = never)
    table_fill_width: bool = True  # a lone body table spans the full width
    table_row_max_em: float = 3.6  # grown table rows <= this x the text size (0 = off)
    table_grow_roomy: float = 2.0  # table rows grow up to this factor when a quarter of the body stays empty
    tree_slack_roomy: float = 1.15  # org-tree boxes may be this much taller than their content (roomy slides)
    tree_slack: float = 1.15  # org-tree boxes are at most this much taller than their content
    html_fit: bool = False  # True: a lone HTML block fills the body height (stretch, else center)
    html_zoom_max: float = 1.5  # a short HTML block renders zoomed up to this factor (1 = off)
    roomy_left: float = 0.25  # share of the body left empty that triggers the roomy pass
    roomy_grow: float = 1.2  # the roomy pass grows box / tree text by up to this factor more
    roomy_grow_dense: float = 1.6  # dense slides: sparse cards may grow text this much more
    dense_roomy_body: float = 1.25  # dense slides: body text stays at most this multiple of the body size
    roomy_row: float = 0.86  # a lone row of boxes reaches this share of the body height
    roomy_row_air: float = 1.9  # ... but never taller than this multiple of the natural height
    balance_air: float = (
        1.15  # normal density: a lone row of boxes may grow to this multiple of its height (0 = off)
    )
    balance_text_air: float = 1.15  # ... while its text still grows, cards stay within this multiple
    balance_max_pt: float = 36  # ... but body text never beyond this size (pt)
    balance_grow: float = 1.25  # ... its text may also grow by up to this factor (no new wrapped lines)
    balance_row: float = 0.85  # ... but never beyond this share of the body
    balance_shift: float = 0.0  # ... and the part of the rest above the 20% band that moves the block down
    balance_left: float = 0.2  # ... when more than this share of the body would stay empty
    roomy_row_air_dense: float = 1.15  # ... dense slides
    peer_step: float = 1.12  # table text is at most this much smaller than the box text on the same slide
    beside_min: float = 0.5  # a box beside a chart / image is at least this share of the visual height
    beside_fill: float = 0.6  # ... a shorter one grows by this share of the way to that minimum
    beside_slack: float = 1.12  # ... headroom over the natural height
    full_width: float = 0.6  # a table wider than this share of the slide width is a full-width table
    row_slack: float = 1.35  # a grid row is at most this much taller than its tallest content
    row_min_tail: float = 0.12  # min row height share of the body when blocks follow the grid
    stack_min: float = 0.4  # stacked boxes beside a tall block: min share of the natural total each
    row_min_dense: float = 0.3  # dense slides: a lone row of boxes is at least this share of the body
    row_min: float = 0.3  # any other row is at least this share of the body
    grow_small: float = (
        1.35  # sparse slides: text grows up to this factor when the body size <= grow_small_pt
    )
    grow_small_pt: float = 14
    grow_big: float = 1.15  # ... and up to this factor for larger themes
    grow_very_sparse: float = 1.4  # very sparse boxes grow up to this factor ...
    grow_very_sparse_pt: float = 16  # ... when the theme body size is at least this
    grow_very_sparse_max_pt: float = 26  # ... but never beyond this body size
    grow_head: float = 1.25  # box headings grow along with the body text, up to this factor
    head_body: float = 1.05  # a box heading is at least this much x the (grown) body text of its box
    room_free: float = 0.35  # a card with more than this share of its inner height free spreads paragraphs
    room_use: float = 0.6  # ... using this share of the free height
    room_gap_max: float = 0.6  # ... up to this space-before (em) per paragraph
    room_gap_max_dense: float = 0.9  # ... dense slides
    slide_peer_step: float = 1.12  # slide-level text is at most this much smaller than the box text beside it
    grow_fill: float = 0.85  # growth stops when the content would fill more than this share of the grid
    grow_box_fill: float = 0.92  # ... or more than this share of a box
    left_keep: float = 0.12  # rows of a sparse slide expand until at most this share of the body is left
    very_sparse_fill: float = 0.4  # content below this share of the body is "very sparse" and may move down
    left_shift: float = 1 / 3  # ... by at most this share of the leftover (boxes)
    left_shift_table: float = 0.2  # ... or this share (slides without boxes)
    dense_grow_body: float = 1.25  # dense slides: text may grow up to this multiple of the body size
    diagram_grow: float = 1.6  # a diagram on a sparse slide grows its nodes up to this factor
    diagram_fill: float = 0.85  # ... while it fills at most this share of the height it has
    # --- hugging cards (consulting / dense slides)
    row_slack_hug: float = (
        1.1  # consulting / dense slides: a grid row is at most this much taller than its content
    )
    row_min_hug: float = 0.12  # consulting / dense slides: a grid row is at least this share of the body
    beside_align: float = (
        0.4  # a box beside a chart / image whose content fills this share of the visual is as tall as it
    )
    hug_shift: float = (
        0.0  # share of the leftover body (beyond left_keep) that moves a card block down (0 = off)
    )
    grow_max: float = (
        1.3  # normal-density slides: body text never grows beyond this factor (dense: dense_*_body)
    )
    center_beside: bool = (
        False  # True: a card as tall as the chart / image beside it centers its content vertically
    )
    hug_cards: bool = True  # cards are as tall as their content (row_slack_hug)
    # --- sparse step: a slide whose content fills less than sparse_fill of the body takes ONE step up
    sparse_fill: float = (
        0.55  # content fills less than this share of the body: the slide sets the deck's step
    )
    sparse_fill_soft: float = 0.65  # ... below this share it takes the deck's step when that fits
    sparse_step: float = 1.25  # text, paddings, chevrons and table text of such a slide grow by this factor
    sparse_step_min: float = 1.15  # ... or this one when the larger step overflows / wraps more lines
    sparse_max_pt: float = 20  # ... but body text never beyond this size (pt)
    sparse_para_gap: float = 0.6  # paragraph gap (em) of a card at the sparse step
    callout_pad_min: Length = "6pt"  # a callout / note box has at least this padding on every side
    footnote_gap: Length = "0.14in"  # min air between a chart (legend included) and the footnote band
    body_size_unify: bool = True  # table text on a slide with boxes is never smaller than the box body text
    unify_max: float = 1.3  # ... lifting a table by more than this factor is refused
    reserve_lead: Literal["auto", "on", "off"] = (
        "auto"  # slides without a lead keep its slot (auto: >= half have one)
    )
    # --- vertical balance of the body (consulting rhythm)
    body_free_max: float = 0.2  # more than this share of the body free: spread it, then center the block
    body_valign: Literal["top", "center", "auto"] = (
        "auto"  # auto: center while free space above body_free_max
    )
    body_spread_max: float = 0.4  # table rows, chevron rows and row gaps grow by at most this share first
    center_min_fill: float = 0.6  # a block filling less than this share of the body is never centered
    card_stretch: bool = False  # ... its cards may stretch (off: tails over a quarter of the card; see tests)
    card_stretch_share: float = (
        0.5  # ... by at most this share of body_spread_max (stretched cards look empty)
    )
    card_pad_share: float = (
        0.25  # ... cards of such a block stretch; this share of the growth moves the body down
    )
    sparse_step_max: float = 1.5  # ... it first tries steps up to this factor (text, nodes, paddings)
    sparse_low_max_pt: float = 24  # ... body text of such a slide may reach this size (pt)
    # --- sparse completion: a slide that still leaves more than sparse_left_max of the body empty
    sparse_left_max: float = 0.35  # ... grows text / cards / chevrons, then moves the block down (0 = off)
    sparse_left_target: float = 0.3  # ... the band below the block is brought down to this share of the body
    sparse_text_max_pt: float = (
        28  # ... body text may reach this size (pt), at most sparse_step_max x the theme body
    )
    sparse_row_gap_max: Length = "0.5in"  # ... rows of blocks move apart by at most this much per gap, first
    sparse_air: float = 1.0  # ... paragraph gap (em) of plain body text, at most (lists on a sparse slide)
    sparse_card_air: float = 1.15  # ... a lone row of cards may reach this multiple of its natural height
    sparse_kpi_air: float = 1.15  # ... KPI cards may be this much taller than their content
    chevron_alone_share_sparse: float = (
        0.4  # ... a chevron row alone aims at this share of the body height ...
    )
    chevron_max_alone_sparse: Length = "2.8in"  # ... up to this height


class RenderTokens(BaseModel):
    """Renderer defaults that change the look (line widths, readable ink colors, chart text scales)."""

    model_config = ConfigDict(extra="forbid")

    line_width: float = 0.75  # pt, a bordered shape without its own line width
    connector_width: float = 1.5  # pt, connectors / arrows between blocks
    chart_line_width: float = 2.25  # pt, line chart series
    chart_title_scale: float = 1.2  # chart title size / chart text size
    chart_label_scale: float = 0.9  # data label size / chart text size
    ink_dark: str = "#1F2937"  # text on light fills when the color is chosen for contrast (badges, labels)
    ink_light: str = "#FFFFFF"  # text on dark fills
    highlight: str = "#FFFF00"  # default ==highlight== color
    code_style: str = "default"  # pygments style for code blocks
    shadow: str = "0 2 6 #00000040"  # `shadow: true`: CSS-like "x y blur [spread] color" (pt)
    slide_bg: str = "#FFFFFF"  # slide background when neither the slide nor the theme has `bg`
    ink_auto: bool = True  # derive readable text colors the deck did not set (`style: ink.auto=off` disables)
    contrast_min: float = 4.5  # contrast ratio auto ink aims for (normal text)
    contrast_large: float = 3.0  # ... for large text (>= `large_pt`, e.g. KPI numbers)
    large_pt: float = 24  # text at least this size counts as large


_BASE_COLORS = ("bg", "fg", "surface", "border", "muted")  # never moved by auto ink (muted has its own rule)


@cache
def _shade(color: str, backs: tuple[str, ...], need: float) -> str:
    return nearest_passing(color, list(backs), need)


NEUTRAL_COLORS = {
    "bg": "#FFFFFF",
    "fg": "#111827",
    "primary": "#111827",
    "secondary": "#4B5563",
    "accent": "#6B7280",
    "muted": "#6B7280",
    "border": "#D1D5DB",
    "surface": "#F3F4F6",  # card / table header background
    "danger": "#B91C1C",
    "success": "#15803D",
}

DEFAULT_SIZES = {
    "title": 32,
    "subtitle": 20,
    "heading": 20,
    "body": 18,
    "lead": 18,
    "quote": 20,
    "caption": 12,
    "footnote": 10,
    "code": 14,
    "table": 14,
    "cover-title": 44,
    "cover-subtitle": 24,
}


def _base_classes() -> dict[str, Style]:
    """Mechanism classes every theme has (components need them); presets restyle them."""
    return {
        "card": Style(fill="surface", line="border", line_width=0.75, radius=6, padding="10pt"),
        "callout": Style(fill="surface", line="primary", line_width=1, padding="10pt"),
        "muted": Style(color="muted"),
        "dense": Style(font_size=11),
        "kpi": Style(font_size=36, bold=True, color="primary", align="center", valign="middle"),
        # callout kinds (`> [!note]` ...): border color. Badges: `[x]{.badge}`.
        "note": Style(line="primary"),
        "tip": Style(line="success"),
        "warn": Style(line="accent"),
        "caution": Style(line="danger"),
        "badge": Style(fill="primary", color="bg", bold=True),
        # mermaid flowchart nodes
        "node": Style(
            fill="surface", line="primary", line_width=1, padding="6pt", align="center", valign="middle"
        ),
        "round": Style(radius=12),
        "decision": Style(fill="bg", line="accent"),
    }


class Theme(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    colors: dict[str, str] = Field(default_factory=lambda: dict(NEUTRAL_COLORS))
    fonts: Fonts = Field(default_factory=Fonts)
    # font sizes in pt, by text role
    sizes: dict[str, float] = Field(default_factory=lambda: dict(DEFAULT_SIZES))
    min_font_size: float = 8  # autofit never shrinks below this
    margin_x: Length = "0.5in"
    margin_y: Length = "0.4in"
    gap: Length = "0.25in"
    title_height: Length = "0.9in"
    # named styles used by `{.name}`, e.g. "card", "callout", "kpi"; tokens may add new ones (`hero.fill=`)
    classes: dict[str, Style] = Field(default_factory=_base_classes)
    heading_color: str = "fg"
    title_color: str = "fg"
    lead_color: str = "muted"
    title_band: str | None = None  # full-width band color behind the slide title (None = no band)
    title_band_color: str = "bg"  # title text color when a band is drawn
    conclusion_fill: str = "primary"
    conclusion_color: str = "bg"
    table_header_fill: str = "surface"
    table_header_color: str = "fg"
    table_body_fill: str = "bg"
    table_border: str = "border"
    table_zebra_fill: str | None = None  # alternate body row fill for `.zebra` tables (None = derived)
    heading_band: str | None = None  # fill of a full-width band behind `##` box headings (None = plain)
    heading_band_color: str = "bg"  # heading text color on the band
    template: str | None = None  # path of a user .pptx/.potx used as the base presentation (masters, layouts)
    columns: int = 12  # layout track grid: ratio/area columns snap to multiples of width/columns
    dense_scale: float = 0.8  # body/table/code size factor for `density: dense` / `.dense` slides
    palette: list[str] = Field(
        default_factory=lambda: ["primary", "secondary", "accent", "danger", "success", "muted"]
    )
    layout: LayoutTokens = Field(default_factory=LayoutTokens)
    render: RenderTokens = Field(default_factory=RenderTokens)

    def color(self, value: str | None) -> str | None:
        """Resolve a theme color name ("primary") or pass a hex value through."""
        if value is None:
            return None
        return self.colors.get(value, value)

    def hexval(self, value: str | None) -> str | None:
        """``#RRGGBB`` (upper case) of a theme color name or 3/6-digit hex; None for anything else."""
        v = self.colors.get(value, value) if isinstance(value, str) else None
        if not isinstance(v, str) or not re.fullmatch(r"#?([0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})", v.strip()):
            return None
        h = v.strip().lstrip("#")
        h = "".join(ch * 2 for ch in h) if len(h) == 3 else h
        return "#" + h.upper()

    def need_for(self, size_pt: float | None) -> float:
        """Contrast ratio text of this size should reach (3:1 for large text, else 4.5:1)."""
        rt = self.render
        big = size_pt is not None and size_pt >= rt.large_pt
        return rt.contrast_large if big else rt.contrast_min

    def surface_backs(self) -> list[str]:
        """Colors text may sit on without a fill of its own: the slide background and card surface."""
        return [h for h in (self.hexval("bg"), self.hexval("surface")) if h]

    def legible(self, value: str | None, size_pt: float | None = None, backs: list[str] | None = None):
        """A theme color *name* made readable on ``backs`` (default bg + surface) by moving its lightness.

        Hex values (set by the deck) and names of the base colors pass through unchanged, and so does
        everything when ``render.ink_auto`` is off. The name is returned when it already passes.
        """
        if not self.render.ink_auto or not isinstance(value, str) or value not in self.colors:
            return value
        if value in _BASE_COLORS:
            return value
        hx = self.hexval(value)
        use = backs or self.surface_backs()
        if not hx or not use:
            return value
        got = _shade(hx, tuple(use), self.need_for(size_pt))
        return value if got == hx else got

    def ink_candidates(self) -> list[str]:
        rt = self.render
        raw = ["fg", "bg", rt.ink_light, rt.ink_dark, "#000000", "#FFFFFF"]
        return [h for h in dict.fromkeys(self.hexval(c) for c in raw) if h]

    def ink_on(self, fill: str | None, prefer: str | None = None, need: float | None = None) -> str:
        """Ink on ``fill``: ``prefer`` when it reaches 4.5:1, else the best of fg/bg/white/black.

        Returns ``prefer`` untouched when ``render.ink_auto`` is off or the fill is not a plain color.
        """
        fh = self.hexval(fill)
        if not self.render.ink_auto or fh is None:
            return prefer or "fg"
        need = need or self.render.contrast_min
        ph = self.hexval(prefer)
        cands = ([ph] if ph else []) + self.ink_candidates()
        if ph and ratio(ph, fh) >= need:
            return prefer  # type: ignore[return-value]
        return best_ink(fh, cands, need)

    def badge_ink(self, highlight: str | None) -> str:
        """Ink of a run on a badge highlight (the badge class color when it is the same fill)."""
        hh = self.hexval(highlight) or self.hexval(self.render.highlight) or "#FFFF00"
        badge = self.classes.get("badge")
        if badge and badge.color and self.hexval(badge.fill) == hh:
            return badge.color
        r, g, b = (int(hh[i : i + 2], 16) for i in (1, 3, 5))
        rt = self.render
        prefer = rt.ink_dark if 0.299 * r + 0.587 * g + 0.114 * b > 160 else rt.ink_light
        return self.ink_on(hh, prefer)

    def run_color(
        self,
        run_color: str | None,
        highlight: str | None,
        style_color: str | None,
        size_pt: float | None = None,
        fill: str | None = None,
    ) -> str | None:
        """The color a run is drawn in (renderer and lint share this)."""
        if highlight and run_color in (None, "bg"):  # the parser gives badges `bg`: the ink is chosen here
            return self.badge_ink(highlight)
        if run_color:
            fh = self.hexval(fill)
            return self.legible(run_color, size_pt, [fh] if fh else None)
        return style_color


# --------------------------------------------------------------------------- presets (YAML data)


def merge_data(base: dict, over: dict) -> dict:
    """Deep merge of plain token mappings (``over`` wins; nested mappings merge)."""
    out = dict(base)
    for k, v in over.items():
        out[k] = merge_data(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def theme_from_data(data: dict, name: str) -> Theme:
    """A Theme from a token mapping. ``extends: <preset>`` starts from that preset, else schema defaults."""
    data = dict(data)
    parent = data.pop("extends", None)
    base = get_theme(str(parent)).model_dump() if parent else Theme(name=name).model_dump()
    base["name"] = name
    merged = merge_data(base, data)
    merged["name"] = name
    return Theme.model_validate(merged)


@cache
def _preset(name: str) -> Theme:
    import yaml

    data = yaml.safe_load((PRESET_DIR / f"{name}.yaml").read_text(encoding="utf-8")) or {}
    return theme_from_data(data, name)


def _preset_names() -> list[str]:
    return sorted(p.stem for p in PRESET_DIR.glob("*.yaml"))


_REGISTRY: dict[str, Theme] = {"none": Theme(name="none")}


def register(theme: Theme) -> None:
    _REGISTRY[theme.name] = theme


def get_theme(name: str) -> Theme:
    if name in _REGISTRY:
        return _REGISTRY[name]
    if name in _preset_names():
        return _preset(name)
    raise KeyError(f"unknown theme {name!r}; available: {', '.join(available())}")


def available() -> list[str]:
    return sorted(set(_REGISTRY) | set(_preset_names()))


DEFAULT = _preset("default")
MIDNIGHT = _preset("midnight")
JP_BUSINESS = _preset("jp-business")


# --------------------------------------------------------------------------- inline tokens

TOKEN_GROUPS = ("colors", "fonts", "sizes", "style")
# short `style:` keys -> canonical token paths
STYLE_ALIASES = {
    "radius": "classes.card.radius",
    "padding": "classes.card.padding",
    "shadow": "classes.card.shadow",
    "border": "classes.card.line",
    "border-width": "classes.card.line_width",
    "card": "classes.card.fill",
    "bg": "colors.bg",
    "fg": "colors.fg",
    "margin": "margin_x",
    "ink.auto": "render.ink_auto",
}
_STYLE_FIELDS = tuple(Style.model_fields)
_NUM = re.compile(r"^-?\d+(?:\.\d+)?$")


def _norm(key: str) -> str:
    return key.strip().replace("-", "_")


def token_paths(theme: Theme | None = None) -> list[str]:
    """Every settable canonical token path (for did-you-mean hints and ``slidemark tokens``)."""
    th = theme or Theme(name="none")
    out: list[str] = []
    for f in Theme.model_fields:
        if f == "name":
            continue
        if f == "colors":
            out += [f"colors.{k}" for k in th.colors]
        elif f == "sizes":
            out += [f"sizes.{k}" for k in th.sizes]
        elif f == "fonts":
            out += [f"fonts.{k}" for k in Fonts.model_fields]
        elif f in ("layout", "render"):
            model = LayoutTokens if f == "layout" else RenderTokens
            out += [f"{f}.{k}" for k in model.model_fields]
        elif f == "classes":
            out += [f"classes.{c}.{k}" for c in th.classes for k in _STYLE_FIELDS]
        else:
            out.append(f)
    return out


def canonical_token(group: str, key: str) -> tuple[str | None, str]:
    """Map a header token (``group`` line, ``key``) to a canonical path, or (None, hint).

    ``colors:`` accepts any color name (new names become theme colors usable everywhere). ``sizes:`` takes
    text roles. ``style:`` takes any other path: a Theme field (``gap``, ``title.band`` = ``title_band``),
    ``<class>.<style field>`` (``card.fill``, ``hero.color``: unknown classes are created),
    ``layout.<x>``, ``render.<x>``, a full path (``colors.bg``) or a short alias (``radius``).
    """
    g = group.lower()
    k = key.strip()
    if not k:
        return None, "write key=value pairs, e.g. 'colors: primary=#7C5CFF'"
    if g == "colors":
        if not re.fullmatch(r"[A-Za-z][\w-]*", k):
            return None, "color names are words, e.g. primary, brand-2"
        return f"colors.{k}", ""
    if g == "fonts":
        if k in Fonts.model_fields:
            return f"fonts.{k}", ""
        return None, _did_you_mean(k, list(Fonts.model_fields))
    if g == "sizes":
        if k in DEFAULT_SIZES or k in ("kpi",):
            return f"sizes.{k}", ""
        return None, _did_you_mean(k, list(DEFAULT_SIZES))
    # style: generic path
    if k in STYLE_ALIASES:
        return STYLE_ALIASES[k], ""
    parts = k.split(".")
    head = parts[0]
    if head in ("colors", "fonts", "sizes") and len(parts) == 2:
        return canonical_token(head, parts[1])
    if head in ("layout", "render") and len(parts) == 2:
        model = LayoutTokens if head == "layout" else RenderTokens
        f = _norm(parts[1])
        if f in model.model_fields:
            return f"{head}.{f}", ""
        return None, _did_you_mean(f, [f"{head}.{x}" for x in model.model_fields], prefix=f"{head}.")
    joined = _norm("_".join(parts))
    if len(parts) > 1 and joined in Theme.model_fields and joined not in ("classes", "layout", "render"):
        return joined, ""  # title.band -> title_band, table.header.fill -> table_header_fill
    if head == "classes" and len(parts) == 3:
        parts = parts[1:]
    if len(parts) == 2:
        cls, field = parts[0], _norm(parts[1])
        field = {"border": "line", "border_width": "line_width", "size": "font_size"}.get(field, field)
        if field in _STYLE_FIELDS and re.fullmatch(r"[A-Za-z][\w-]*", cls):
            return f"classes.{cls}.{field}", ""
        return None, _did_you_mean(field, list(_STYLE_FIELDS), prefix=f"{cls}.")
    f = _norm(k)
    if len(parts) == 1 and f in Theme.model_fields and f not in ("name", "classes", "layout", "render"):
        return f, ""
    cands = [p for p in token_paths() if not p.startswith("classes.")] + list(STYLE_ALIASES)
    return None, _did_you_mean(k, cands)


def _did_you_mean(key: str, cands: list[str], prefix: str = "") -> str:
    near = difflib.get_close_matches(key, [c.removeprefix(prefix) for c in cands], n=1, cutoff=0.6)
    tip = "`slidemark tokens` lists every token"
    return f"did you mean '{prefix}{near[0]}'? {tip}" if near else tip


def _value(raw: str) -> Any:
    v = raw.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    if v.lower() in ("none", "null", "off"):
        return None
    if v.lower() in ("true", "on", "yes"):
        return True
    if v.lower() in ("false", "no"):
        return False
    if _NUM.match(v):
        return float(v) if "." in v else int(v)
    return v


def apply_tokens(theme: Theme, tokens: dict[str, str]) -> tuple[Theme, list[Diagnostic]]:
    """Apply canonical ``path -> raw value`` tokens (``Deck.tokens``) on top of ``theme``.

    Values are checked by field type and CSS-like shorthands are mapped (:func:`normalize_token`). Never
    raises: a token that does not validate is skipped with a ``bad-token`` diagnostic.
    """
    diags: list[Diagnostic] = []
    data = theme.model_dump()
    names = set(theme.colors) | {p.split(".", 1)[1] for p in tokens if p.startswith("colors.")}
    for path, raw in tokens.items():
        trial = copy.deepcopy(data)
        try:
            pairs = normalize_token(path, raw, names) if isinstance(raw, str) else [(path, raw)]
            for p, v in pairs:
                _set_path(trial, p.split("."), v)
            Theme.model_validate(trial)
        except TokenValueError as e:
            diags.append(_bad_token(path, raw, str(e), e.hint))
            continue
        except (ValidationError, ValueError, TypeError, KeyError) as e:
            why = e.errors()[0]["msg"] if isinstance(e, ValidationError) else str(e) or type(e).__name__
            diags.append(_bad_token(path, raw, why, _HINT_GENERIC))
            continue
        data = trial
    _derive_muted(data, tokens)
    _derive_surface(data, tokens)
    return Theme.model_validate(data), diags


def _hex_rgb(v: Any) -> tuple[float, float, float] | None:
    if not isinstance(v, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?", v):
        return None
    return tuple(int(v[i : i + 2], 16) / 255 for i in (1, 3, 5))  # type: ignore[return-value]


def _rel_lum(c: tuple[float, float, float]) -> float:
    lin = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _derive_muted(data: dict, tokens: dict[str, str]) -> None:
    """A deck that sets its own bg/fg but no ``muted`` gets a muted color between them that stays readable.

    The preset's grey is made for its own background: on a dark brand ``bg`` it fails contrast (lead lines,
    captions). Muted = fg mixed 35% toward bg, which keeps ≥ 4.5:1 on any bg/fg pair with ≥ 10:1.
    """
    if "colors.muted" in tokens or not ({"colors.bg", "colors.fg"} & set(tokens)):
        return
    cols = data.get("colors") or {}
    bg, fg, muted = (_hex_rgb(cols.get(k)) for k in ("bg", "fg", "muted"))
    if not (bg and fg and muted):
        return
    lo, hi = sorted((_rel_lum(muted), _rel_lum(bg)))
    if (hi + 0.05) / (lo + 0.05) >= 4.5:
        return
    mix = [f + (b - f) * 0.35 for f, b in zip(fg, bg, strict=True)]
    cols["muted"] = "#" + "".join(f"{round(x * 255):02X}" for x in mix)


def _mix_hex(a: tuple[float, ...], b: tuple[float, ...], t: float) -> str:
    return "#" + "".join(f"{round((x + (y - x) * t) * 255):02X}" for x, y in zip(a, b, strict=True))


def _derive_surface(data: dict, tokens: dict[str, str]) -> None:
    """A deck that sets its own bg/fg but no ``surface`` / ``border`` gets cards that stand out from the bg.

    The preset's light grey surface would be a white card on a dark brand bg (white text on it is unreadable)
    and its border would vanish. A preset value is kept while it still works (fg reads on the surface at 4.5:1
    and the surface differs from bg); otherwise surface = bg mixed toward fg until the two differ (>= 1.1:1,
    6% to start), border = bg mixed 25% toward fg.
    """
    if not ({"colors.bg", "colors.fg"} & set(tokens)):
        return
    cols = data.get("colors") or {}
    bg, fg = _hex_rgb(cols.get("bg")), _hex_rgb(cols.get("fg"))
    if not (bg and fg):
        return

    def rat(a: tuple[float, ...], b: tuple[float, ...]) -> float:
        lo, hi = sorted((_rel_lum(a), _rel_lum(b)))
        return (hi + 0.05) / (lo + 0.05)

    surface = _hex_rgb(cols.get("surface"))
    if "colors.surface" not in tokens and not (
        surface and rat(fg, surface) >= 4.5 and rat(bg, surface) >= 1.03
    ):
        t = 0.06
        while t < 0.3 and rat(bg, tuple(b + (f - b) * t for b, f in zip(bg, fg, strict=True))) < 1.1:
            t += 0.02
        cols["surface"] = _mix_hex(bg, fg, t)
    border = _hex_rgb(cols.get("border"))
    if "colors.border" not in tokens and not (border and rat(bg, border) >= 1.2):
        cols["border"] = _mix_hex(bg, fg, 0.25)


def derive_ink(theme: Theme, explicit: set[str] | frozenset[str] = frozenset()) -> Theme:
    """Make the theme's default text colors readable (``render.ink_auto``), never touching the deck's own.

    ``explicit`` holds the canonical token paths the deck set (``Deck.tokens`` keys): those fields are kept
    and left for lint to report. Text drawn on a theme fill (conclusion bar, title / heading band, table
    header, badge, any class with a fill and a color) keeps its color while it reaches
    ``render.contrast_min``,
    else becomes the best of fg / bg / white / black. Text in a theme color on the bg / card surface (KPI
    numbers, heading and lead colors, color-only classes) keeps it while it reaches 4.5:1 (3:1 at
    ``render.large_pt`` and above), else becomes the nearest passing shade of the same hue. Fills never
    change.
    Presets that already read are returned unchanged.
    """
    if not theme.render.ink_auto:
        return theme
    upd: dict[str, Any] = {}
    classes = {k: v.model_copy() for k, v in theme.classes.items()}

    def on_fill(path: str, color: str | None, fill: str | None) -> str | None:
        if path in explicit or not color or not fill or theme.hexval(fill) is None:
            return None
        ink = theme.ink_on(fill, color)
        return None if ink == color else ink

    for field, fill in (
        ("conclusion_color", theme.conclusion_fill),
        ("title_band_color", theme.title_band),
        ("heading_band_color", theme.heading_band),
        ("table_header_color", theme.table_header_fill),
    ):
        if (new := on_fill(field, getattr(theme, field), fill)) is not None:
            upd[field] = new

    def in_color(path: str, color: str | None, size: float | None, backs: list[str]) -> str | None:
        hx = theme.hexval(color)
        if path in explicit or not hx or color in _BASE_COLORS or not backs:
            return None
        got = _shade(hx, tuple(backs), theme.need_for(size))
        return None if got == hx else got

    cards = theme.surface_backs()
    plain = [b for b in (theme.hexval("bg"),) if b]
    for field, backs in (("heading_color", cards), ("lead_color", plain)):
        if (
            new := in_color(field, getattr(theme, field), theme.sizes.get(field.split("_")[0]), backs)
        ) is not None:
            upd[field] = new
    for name, st in theme.classes.items():
        path = f"classes.{name}.color"
        if st.fill:
            new = on_fill(path, st.color, st.fill)
        else:
            size = st.font_size or theme.sizes.get(name) or theme.sizes.get("body")
            new = in_color(path, st.color, size, cards)
        if new is not None:
            classes[name] = st.model_copy(update={"color": new})
    if not upd and all(classes[k] == v for k, v in theme.classes.items()):
        return theme
    return theme.model_copy(update={**upd, "classes": classes})


def _bad_token(path: str, raw: Any, why: str, hint: str) -> Diagnostic:
    return Diagnostic(
        level="warning",
        message=f"token {path}={raw!s}: {why[:100]}",
        rule="bad-token",
        hint=hint.replace("\n", " "),
    )


# --------------------------------------------------------------------------- token value types


class TokenValueError(ValueError):
    """A token value of the wrong type; ``hint`` is a one-line fix with a valid example."""

    def __init__(self, message: str, hint: str):
        super().__init__(message)
        self.hint = hint


_HINT_GENERIC = "check the value type (color #RRGGBB or name, number, length like 12pt/0.3in)"
_HINT_COLOR = "use #RRGGBB, rgb(...), a CSS color name, a theme color name, or none, e.g. #B08D57"
_HINT_FILL = "use a color, none, linear-gradient(135deg, #AAA, #BBB) or url(path), e.g. #F3F4F6"
_HINT_LEN = "use a number (pt) or a length like 12pt, 0.3in, 8px, 1cm"
_HINT_BORDER = (
    "write '<width> <solid|dashed|dotted> <color>' in any order, e.g. 0.75pt solid #B08D57, or none"
)
_HINT_SHADOW = "write none, on, or '<x> <y> <blur> <color>' in pt, e.g. 0 2 6 #00000040"
_IDENT = re.compile(r"[A-Za-z][\w-]*")
_KEYWORDS = {"none", "hidden", "solid", "dashed", "dotted", "double", "thin", "medium", "thick"}
_PT_FIELDS = {"font_size", "line_width", "radius", "letter_spacing"}
_PT_PATHS = {"min_font_size", "render.line_width", "render.connector_width", "render.chart_line_width"}
_THEME_COLOR_SUFFIX = ("_fill", "_color", "_band", "_border")
_OPTIONAL_COLORS = {"title_band", "heading_band", "table_zebra_fill"}
_MEDIUM_PT = 2.25  # CSS `medium` border width (3px)


def _is_length_type(annotation: Any) -> bool:
    return {a for a in getattr(annotation, "__args__", ()) if a is not type(None)} == {str, float, int}


@cache
def _length_fields() -> frozenset[str]:
    out = {f"layout.{k}" for k, f in LayoutTokens.model_fields.items() if _is_length_type(f.annotation)}
    out |= {k for k, f in Theme.model_fields.items() if _is_length_type(f.annotation)}
    return frozenset(out)


def _unquote(v: str) -> str:
    v = v.strip()
    return v[1:-1] if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'" else v


def _color_value(raw: str, names: set[str] | None, hint: str = _HINT_COLOR) -> str:
    """Normalized color; ``names=None`` (parse time) accepts any bare word: it may be declared later."""
    from .parser.css import parse_color

    v = _unquote(raw)
    if v.lower() in ("none", "null", "off"):
        return "#00000000"
    c = parse_color(v, names or set())
    if c is None and names is None and _IDENT.fullmatch(v):
        return v
    if c is None:
        raise TokenValueError(f"'{v}' is not a color", hint)
    return c


def _pt_value(raw: str) -> float:
    """A length as a pt number: bare numbers are pt, units convert (``0.3in`` -> 21.6)."""
    from .units import to_emu

    v = _unquote(raw)
    if _NUM.match(v):
        return float(v)
    try:
        return round(to_emu(v) / 12700, 3)
    except (ValueError, KeyError):
        raise TokenValueError(f"'{v}' is not a length", _HINT_LEN) from None


def _length_value(raw: str) -> str | float | int:
    from .units import to_emu

    v = _unquote(raw)
    if _NUM.match(v):
        return float(v) if "." in v else int(v)
    try:
        to_emu(v, 100)
    except (ValueError, KeyError):
        raise TokenValueError(f"'{v}' is not a length", _HINT_LEN) from None
    return v


def _border_parts(raw: str, names: set[str] | None) -> tuple[float | None, str | None, str | None, bool]:
    """(width pt, dash, color, none) of a border shorthand, like the css parser's ``border``."""
    from .parser.css import BadValue, Maps, split_tokens

    toks = [f"{t}pt" if _NUM.match(t) else t for t in split_tokens(_unquote(raw))]
    if not toks:
        raise TokenValueError("empty border", _HINT_BORDER)
    if names is None:  # parse time: a bare word may be a color declared later
        toks = ["#000" if _IDENT.fullmatch(t) and t.lower() not in _KEYWORDS else t for t in toks]
    try:
        return Maps(names or set(), None)._border_parts(" ".join(toks))
    except BadValue as e:
        raise TokenValueError(str(e), _HINT_BORDER) from None


def _side_value(raw: str, names: set[str] | None) -> str:
    from .parser.css import fmt

    width, dash, color, none = _border_parts(raw, names)
    if none:
        return "none"
    return f"{fmt(_MEDIUM_PT if width is None else width)}pt {dash or 'solid'} {color or 'fg'}"


def _shadow_value(raw: str, names: set[str] | None) -> bool | str:
    from .parser.css import fmt, parse_color, split_tokens

    v = _unquote(raw)
    low = v.lower()
    if low in ("none", "off", "false", "no"):
        return False
    if low in ("on", "true", "yes"):
        return True
    lens: list[float] = []
    color: str | None = None
    for t in split_tokens(v):
        if _NUM.match(t) or re.fullmatch(r"-?[\d.]+(pt|px|in|cm|mm)", t):
            lens.append(_pt_value(t))
            continue
        c = parse_color(t, names or set())
        if c is None and names is None and _IDENT.fullmatch(t):
            c = t
        if c is None:
            raise TokenValueError(f"'{t}' is not a number or color in shadow", _HINT_SHADOW)
        color = c
    if not 2 <= len(lens) <= 4:
        raise TokenValueError("a shadow needs x, y [, blur [, spread]]", _HINT_SHADOW)
    while len(lens) < 3:
        lens.append(0.0)
    if color is None:
        color = "#00000040"
    elif re.fullmatch(r"#[0-9A-F]{6}", color):
        color += "FF"
    return " ".join([*(fmt(x) for x in lens), color])


def _line_pairs(base: str, raw: str, names: set[str] | None) -> list[tuple[str, Any]]:
    """``<class>.line`` (``border``): a color, or a CSS border shorthand (width, style, color, none)."""
    width, dash, color, none = _border_parts(raw, names)
    if none:
        return [(f"{base}.line_width", 0.0)]
    out: list[tuple[str, Any]] = []
    if color:
        out.append((f"{base}.line", color))
    if width is not None:
        out.append((f"{base}.line_width", round(width, 3)))
    if dash:
        out.append((f"{base}.line_dash", dash))
    return out


def _fill_value(path: str, raw: str, names: set[str] | None) -> list[tuple[str, Any]]:
    from .parser.css import BadValue, gradient, is_gradient

    v = _unquote(raw)
    if is_gradient(v):
        try:
            return [(path, gradient(v, names or set()))]
        except BadValue as e:
            raise TokenValueError(str(e), _HINT_FILL) from None
    if re.fullmatch(r"url\(.*\)", v, re.I | re.S):
        return [(path, v)]
    return [(path, _color_value(v, names, _HINT_FILL))]


def normalize_token(path: str, raw: str, names: set[str] | None) -> list[tuple[str, Any]]:
    """Validate a raw token value by its field type and map CSS-like shorthands.

    Returns the ``(canonical path, typed value)`` pairs to set (a border shorthand sets up to three).
    ``names`` are the known theme color names; ``None`` is the lenient parse-time mode where any bare word
    passes as a possibly later-declared color. Raises :class:`TokenValueError` (message + one-line hint).
    """
    parts = path.split(".")
    leaf = parts[-1]
    in_class = len(parts) == 3 and parts[0] == "classes"
    if in_class and leaf == "line":
        return _line_pairs(".".join(parts[:2]), raw, names)
    if in_class and leaf == "fill":
        return _fill_value(path, raw, names)
    if in_class and leaf == "color":
        return [(path, _color_value(raw, names))]
    if in_class and leaf.startswith("border_"):
        return [(path, _side_value(raw, names))]
    if (in_class and leaf == "shadow") or path == "render.shadow":
        val = _shadow_value(raw, names)
        if path == "render.shadow" and not isinstance(val, str):
            raise TokenValueError("render.shadow needs x y blur color", _HINT_SHADOW)
        return [(path, val)]
    if path == "render.ink_auto":
        flag = _unquote(raw).lower()
        if flag in ("on", "true", "yes", "1"):
            return [(path, True)]
        if flag in ("off", "false", "no", "0", "none"):
            return [(path, False)]
        raise TokenValueError("ink.auto is on or off", "write 'style: ink.auto=off' (or on)")
    if path == "palette":
        items = [p.strip() for p in _unquote(raw).split(",") if p.strip()]
        return [(path, [_color_value(p, names) for p in items])]
    if parts[0] == "colors" or path in ("render.ink_dark", "render.ink_light", "render.highlight"):
        return [(path, _color_value(raw, names))]
    if len(parts) == 1 and leaf.endswith(_THEME_COLOR_SUFFIX) and leaf in Theme.model_fields:
        if leaf in _OPTIONAL_COLORS and _unquote(raw).lower() in ("none", "null", "off"):
            return [(path, None)]
        return [(path, _color_value(raw, names))]
    if (in_class and leaf in _PT_FIELDS) or path in _PT_PATHS or parts[0] == "sizes":
        return [(path, _pt_value(raw))]
    if path in _length_fields() or (
        in_class and leaf in Style.model_fields and _is_length_type(Style.model_fields[leaf].annotation)
    ):
        return [(path, _length_value(raw))]
    return [(path, _value(raw))]


def _set_path(data: dict, parts: list[str], value: Any) -> None:
    head, rest = parts[0], parts[1:]
    if not rest:
        if head == "palette" and isinstance(value, str):
            value = [p.strip() for p in value.split(",") if p.strip()]
        data[head] = value
        return
    node = data.get(head)
    if node is None:
        node = {}
        data[head] = node
    if not isinstance(node, dict):
        raise ValueError(f"{head} is not a group")
    if head == "classes" and len(rest) == 2 and rest[0] not in node:
        node[rest[0]] = {}
    if head == "classes" and len(rest) == 2 and node[rest[0]] is None:
        node[rest[0]] = {}
    _set_path(node, rest, value)


def schema_table(theme: Theme | None = None) -> list[tuple[str, str]]:
    """``(path, current value)`` rows for every token, for ``slidemark tokens``."""
    th = theme or Theme(name="none")
    data = th.model_dump()
    rows: list[tuple[str, str]] = []
    for path in token_paths(th):
        node: Any = data
        for p in path.split("."):
            node = node.get(p) if isinstance(node, dict) else None
        if path.startswith("classes.") and node is None:
            continue
        text = ",".join(node) if isinstance(node, list) else str(node)
        rows.append((path, "none" if node is None else text))
    return rows


# --------------------------------------------------------------------------- slide ink (dark backgrounds)

# Text that sits directly on the slide background (cards and tables keep their own colors).
_INK_SELECTORS = ("h1", "slide > p", ".plain > p", ".plain > h2")
_MUTED_SELECTORS = (".lead", ".subtitle", ".footnote")
_INK_MARK = -1  # CssRule.line of the rules this module adds (so a second call replaces them)


def _hex_str(rgb: tuple[float, ...]) -> str:
    return "#" + "".join(f"{round(min(max(x, 0.0), 1.0) * 255):02X}" for x in rgb)


def slide_ink(theme: Theme, bg: str | None, classes: list[str] | tuple[str, ...] = ()) -> dict[str, str]:
    """Text colors a slide needs on its own background: ``{"color": ink, "muted": softer ink}`` or ``{}``.

    ``dark`` always means light ink (``render.ink_light``), ``light`` dark ink (``render.ink_dark``), on
    whatever background (unless the theme defines that class itself). Without a class, a slide ``bg``
    (color, token name or gradient: every stop is judged) that gives the theme ``fg`` less than 4.5:1 switches
    to whichever ink contrasts more. Pure: it only reads ``theme`` and the arguments.
    """
    from .lint import _backs, _hex, contrast_ratio  # lint imports this module: import lazily

    rt = theme.render
    backs = _backs(bg, theme, None) if bg else []
    ref = backs or ([b] if (b := _hex("bg", theme)) else [])

    def worst(ink: str) -> float:
        c = _hex(ink, theme)
        return min((contrast_ratio(c, b) for b in ref), default=0.0) if c and ref else 0.0

    names = [c for c in classes if c in ("dark", "light") and c not in theme.classes]
    if names:
        ink = rt.ink_light if names[-1] == "dark" else rt.ink_dark
    elif backs:
        fg = worst("fg")
        ink = max((rt.ink_light, rt.ink_dark), key=worst)
        if fg >= 4.5 or worst(ink) <= fg:
            return {}
    else:
        return {}
    out = {"color": ink, "muted": ink}
    rgb = _hex(ink, theme)
    if rgb and ref:
        mean = tuple(sum(b[k] for b in ref) / len(ref) for k in range(3))
        soft = _hex_str(tuple(c + (m - c) * 0.22 for c, m in zip(rgb, mean, strict=True)))
        if worst(soft) >= 4.5:
            out["muted"] = soft
    return out


def apply_slide_ink(deck: Any, theme: Theme) -> None:
    """Give every slide that needs it the CSS rules of :func:`slide_ink` (idempotent, never raises).

    Colors declared for the slide win: a slide-scoped CSS rule (a fence inside the slide, or a deck rule
    naming ``slide``) that sets ``color`` on ``slide`` skips the slide, one on ``h1`` / ``p`` / ``.lead`` ...
    skips just that target; element ``{color=}`` attrs and ``@html`` slides are never touched.
    """
    from .ir import CssRule
    from .layout.css import slide_style

    try:
        for i, slide in enumerate(deck.slides):
            slide.css = [r for r in slide.css if r.line != _INK_MARK]
            if slide.html:
                continue
            fill = slide.background or slide_style(deck, slide, i).fill
            ink = slide_ink(theme, fill, slide.classes)
            if not ink:
                continue
            declared: set[str] = set()
            # Declarations for this slide always win. A deck-wide `h1 { color }` was chosen for the default
            # background: it yields to a slide's own `bg=` / `dark` / `light`, but not to a deck-wide
            # `slide { background }` (the deck painted both).
            local = slide.background or any(r.style.fill for r in slide.css) or "dark" in slide.classes
            local = local or "light" in slide.classes
            for r in [*(r for r in deck.css if not local or "slide" in r.selector), *slide.css]:
                if r.style.color is None:
                    continue
                last = re.split(r"\s*>\s*|\s+", r.selector.strip())[-1]
                declared |= set(re.findall(r"[.#]?[\w-]+", last))
            if "slide" in declared:
                continue
            rules = []
            for sels, color in ((_INK_SELECTORS, ink["color"]), (_MUTED_SELECTORS, ink["muted"])):
                for sel in sels:
                    key = re.split(r"\s*>\s*", sel)[-1]
                    if key not in declared:
                        rules.append(CssRule(selector=sel, style=Style(color=color), line=_INK_MARK))
            slide.css = [*rules, *slide.css]
    except Exception:  # never raise on user input: the slide keeps the theme colors
        return
