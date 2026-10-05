"""Theme model: design tokens shared by layout (sizes, spacing) and renderer (colors, fonts)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .ir import Length, Style


class Fonts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    heading: str = "Calibri"
    body: str = "Calibri"
    mono: str = "Consolas"
    ea: str = "Yu Gothic"  # East Asian typeface for ja/zh/ko text (written to <a:ea>)


class Theme(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    colors: dict[str, str] = Field(
        default_factory=lambda: {
            "bg": "#FFFFFF",
            "fg": "#1F2937",
            "primary": "#1D4ED8",
            "secondary": "#0F766E",
            "accent": "#F59E0B",
            "muted": "#6B7280",
            "border": "#D1D5DB",
            "surface": "#F3F4F6",  # card / table header background
            "danger": "#DC2626",
            "success": "#16A34A",
        }
    )
    fonts: Fonts = Field(default_factory=Fonts)
    # font sizes in pt, by text role
    sizes: dict[str, float] = Field(
        default_factory=lambda: {
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
    )
    min_font_size: float = 8  # autofit never shrinks below this
    margin_x: Length = "0.5in"
    margin_y: Length = "0.4in"
    gap: Length = "0.25in"
    title_height: Length = "0.9in"
    # named styles used by `{.name}` and `::: name`, e.g. "card", "callout", "kpi"
    classes: dict[str, Style] = Field(default_factory=dict)
    # --- additive tokens (all optional, defaults reproduce the original look) ---
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
    dense_scale: float = 0.8  # body/table/code size factor for `density: dense` / `.dense` slides
    palette: list[str] = Field(
        default_factory=lambda: ["primary", "secondary", "accent", "danger", "success", "muted"]
    )

    def color(self, value: str | None) -> str | None:
        """Resolve a theme color name ("primary") or pass a hex value through."""
        if value is None:
            return None
        return self.colors.get(value, value)


DEFAULT = Theme(
    name="default",
    classes={
        "card": Style(fill="surface", line="border", line_width=0.75, radius=6, padding="10pt"),
        "callout": Style(fill="#EFF6FF", line="primary", line_width=1, padding="10pt"),
        "muted": Style(color="muted"),
        "dense": Style(font_size=11),
        "kpi": Style(font_size=36, bold=True, color="primary", align="center", valign="middle"),
    },
)

MIDNIGHT = Theme(
    name="midnight",
    colors={
        "bg": "#0F172A",
        "fg": "#E2E8F0",
        "primary": "#38BDF8",
        "secondary": "#2DD4BF",
        "accent": "#FBBF24",
        "muted": "#94A3B8",
        "border": "#334155",
        "surface": "#1E293B",
        "danger": "#F87171",
        "success": "#4ADE80",
    },
    title_color="primary",
    table_header_fill="#334155",
    classes={
        "card": Style(fill="surface", line="border", line_width=0.75, radius=8, padding="10pt"),
        "callout": Style(fill="surface", line="primary", line_width=1.25, padding="10pt"),
        "muted": Style(color="muted"),
        "dense": Style(font_size=11),
        "kpi": Style(font_size=36, bold=True, color="primary", align="center", valign="middle"),
    },
)

JP_BUSINESS = Theme(
    name="jp-business",
    colors={
        "bg": "#FFFFFF",
        "fg": "#1F2937",
        "primary": "#1E3A5F",
        "secondary": "#2F6B9A",
        "accent": "#C00000",
        "muted": "#5B6573",
        "border": "#BFC7D1",
        "surface": "#F1F4F8",
        "danger": "#C00000",
        "success": "#2E7D32",
    },
    fonts=Fonts(heading="Yu Gothic", body="Yu Gothic", mono="Consolas", ea="Yu Gothic"),
    sizes={
        "title": 24,
        "subtitle": 16,
        "heading": 13,
        "body": 11,
        "lead": 13,
        "quote": 11,
        "caption": 9,
        "footnote": 9,
        "code": 10,
        "table": 10.5,
        "cover-title": 34,
        "cover-subtitle": 18,
    },
    min_font_size=7,
    margin_x="0.45in",
    margin_y="0.3in",
    gap="0.15in",
    title_height="0.75in",
    title_band="primary",
    title_band_color="#FFFFFF",
    heading_color="primary",
    table_header_fill="primary",
    table_header_color="#FFFFFF",
    dense_scale=0.9,
    classes={
        "card": Style(fill="surface", line="border", line_width=0.5, radius=0, padding="7pt"),
        "callout": Style(fill="#FDF2F2", line="danger", line_width=1, padding="7pt"),
        "muted": Style(color="muted"),
        "dense": Style(font_size=10.5),
        "kpi": Style(font_size=26, bold=True, color="primary", align="center", valign="middle"),
    },
)

_REGISTRY: dict[str, Theme] = {"default": DEFAULT, "midnight": MIDNIGHT, "jp-business": JP_BUSINESS}


def register(theme: Theme) -> None:
    _REGISTRY[theme.name] = theme


def get_theme(name: str) -> Theme:
    try:
        return _REGISTRY[name]
    except KeyError:
        raise KeyError(f"unknown theme {name!r}; available: {', '.join(sorted(_REGISTRY))}") from None


def available() -> list[str]:
    return sorted(_REGISTRY)
