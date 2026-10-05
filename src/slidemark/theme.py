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
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

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
    table_grow_roomy: float = 2.0  # table rows grow up to this factor when a quarter of the body stays empty
    tree_slack_roomy: float = 1.3  # org-tree boxes may be this much taller than their content (roomy slides)
    tree_slack: float = 1.15  # org-tree boxes are at most this much taller than their content
    html_fit: bool = False  # True: a lone HTML block fills the body height (stretch, else center)
    html_zoom_max: float = (
        1.5  # an HTML block much smaller than its box renders zoomed up to this factor (1 = off)
    )
    roomy_left: float = 0.25  # share of the body left empty that triggers the roomy pass
    roomy_grow: float = 1.2  # the roomy pass grows box / tree text by up to this factor more
    roomy_grow_dense: float = 1.6  # dense slides: sparse cards may grow text this much more
    dense_roomy_body: float = 1.25  # dense slides: body text stays at most this multiple of the body size
    roomy_row: float = 0.86  # a lone row of boxes reaches this share of the body height
    roomy_row_air: float = 1.9  # ... but never taller than this multiple of the natural height
    balance_air: float = (
        1.9  # normal density: a lone row of boxes may grow to this multiple of its height (0 = off)
    )
    balance_text_air: float = 1.3  # ... while its text still grows, cards stay within this multiple
    balance_max_pt: float = 36  # ... but body text never beyond this size (pt)
    balance_grow: float = 1.9  # ... its text may also grow by up to this factor (no new wrapped lines)
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
    return Theme.model_validate(data), diags


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
