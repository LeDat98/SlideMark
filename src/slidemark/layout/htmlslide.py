"""Whole-slide HTML layout (``Slide.html``): Chromium lays the HTML out at the slide size, natively.

``layout_html_slide`` returns the Placed items of one slide. When Chromium is unavailable, nothing could be
measured, or the HTML is not :func:`slidemark.htmlnative.convertible`, the slide becomes one full-slide
picture (a ``Raw(kind="html")`` item with ``render=image``, drawn by the renderer's image fallback) plus an
info diagnostic naming the reason. One browser is shared by all HTML slides of a build; ``build_deck`` calls
:func:`close_shared` after layout (a second Playwright instance must not run while one is open).
"""

from __future__ import annotations

import atexit

from ..htmlnative import convertible, html_to_placed
from ..ir import Deck, Diagnostic, Placed, Raw, Slide, Style
from ..theme import Theme
from ..units import slide_size

__all__ = ["close_shared", "layout_html_slide"]

_shared = None


def _renderer():
    global _shared
    if _shared is None:
        from ..render.htmlimg import HtmlRenderer

        _shared = HtmlRenderer()
    return _shared


def close_shared() -> None:
    """Close the shared browser (idempotent)."""
    global _shared
    if _shared is not None:
        _shared.close()
        _shared = None


atexit.register(close_shared)


def layout_html_slide(slide: Slide, deck: Deck, theme: Theme, index: int) -> list[Placed]:
    """Native items for ``slide.html`` at the full slide size, or one full-slide picture. Never raises."""
    try:
        W, H = slide_size(deck.size)
    except ValueError:
        W, H = slide_size("16:9")
    html = slide.html or ""
    base = str(deck.attrs.get("base_dir", "."))

    def diag(level: str, msg: str, rule: str, hint: str) -> None:
        deck.diagnostics.append(
            Diagnostic(level=level, message=msg, slide=index + 1, line=slide.line, rule=rule, hint=hint)  # type: ignore[arg-type]
        )

    def picture(why: str) -> list[Placed]:
        diag(
            "info",
            f"HTML slide kept as one picture ({why})",
            "html-slide-image",
            "pip install slidemark[html] and avoid canvas/video/iframe for editable shapes",
        )
        raw = Raw(kind="html", source=html, attrs={"render": "image"}, line=slide.line)
        return [Placed(element=raw, x=0, y=0, w=W, h=H, style=Style())]

    if not convertible(html):
        return picture("canvas, video or iframe cannot be shapes")
    try:
        res = html_to_placed(html, 0, 0, W, H, theme, base, renderer=_renderer())
    except Exception:
        res = None
    if res is None:
        return picture("Chromium is unavailable or nothing was measured")
    items, diags = res
    for d in diags:
        diag(d.level, d.message, d.rule or "html-native", d.hint or "")
    if theme.layout.html_footer and (deck.footer or deck.slide_number):
        from .engine import html_footer_items

        items = [*items, *html_footer_items(slide, deck, theme, index, W, H)]
    return items
