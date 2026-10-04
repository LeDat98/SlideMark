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
    },
)

_REGISTRY: dict[str, Theme] = {"default": DEFAULT}


def register(theme: Theme) -> None:
    _REGISTRY[theme.name] = theme


def get_theme(name: str) -> Theme:
    try:
        return _REGISTRY[name]
    except KeyError:
        raise KeyError(f"unknown theme {name!r}; available: {', '.join(sorted(_REGISTRY))}") from None


def available() -> list[str]:
    return sorted(_REGISTRY)
