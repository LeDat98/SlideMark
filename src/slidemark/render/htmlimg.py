"""Raw HTML block -> PNG through headless Chromium (optional extra ``slidemark[html]``). Never raises.

One browser is launched lazily per render and reused for every HTML block of the deck. JavaScript is off
and every request that is not ``data:`` / ``about:`` is aborted, so untrusted HTML cannot fetch anything.
"""

from __future__ import annotations

import glob
import html
import os
from io import BytesIO

from pptx.util import Emu

from ..ir import Placed, Raw
from ..theme import Theme
from .util import RenderCtx, hex6

__all__ = ["HtmlRenderer", "add_html_image", "close_html", "render_html_png"]

SCALE = 2
TIMEOUT_MS = 15_000
EMU_PER_PX = 9525
ALT = "HTML block (image fallback)"
HINT = "pip install slidemark[html] (Playwright + Chromium) to render HTML blocks as images"


def _page(source: str, theme: Theme) -> str:
    fg, bg = hex6(theme, "fg"), hex6(theme, "bg", "#FFFFFF")
    fonts = theme.fonts
    family = ", ".join(f"'{f}'" for f in (fonts.body, fonts.ea)) + ", sans-serif"
    size = theme.sizes.get("body", 18) * 96 / 72
    return (
        '<!doctype html><html><head><meta charset="utf-8">'
        f"<style>*{{box-sizing:border-box}}html,body{{margin:0;padding:0;background:#{bg};}}"
        f"body{{font-family:{html.escape(family)};font-size:{size:.1f}px;color:#{fg};overflow:hidden}}"
        f"</style></head><body>{source}</body></html>"
    )


def _executable() -> str | None:
    """A Chromium binary under PLAYWRIGHT_BROWSERS_PATH when playwright's own pinned build is missing."""
    root = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")
    for pat in ("chromium-*/chrome-linux*/chrome", "chromium_headless_shell-*/chrome-linux*/headless_shell"):
        found = sorted(glob.glob(os.path.join(root, pat)))
        if found:
            return found[-1]
    return None


class HtmlRenderer:
    """Lazily launched Chromium shared by all HTML blocks of one deck."""

    def __init__(self) -> None:
        self._pw = None
        self._browser = None
        self._failed = False

    def _launch(self):
        if self._browser is not None or self._failed:
            return self._browser
        try:
            from playwright.sync_api import sync_playwright

            self._pw = sync_playwright().start()
            args = ["--no-sandbox", "--disable-gpu"]
            try:
                self._browser = self._pw.chromium.launch(headless=True, args=args, timeout=TIMEOUT_MS)
            except Exception:
                exe = _executable()
                if exe is None:
                    raise
                self._browser = self._pw.chromium.launch(
                    headless=True, args=args, executable_path=exe, timeout=TIMEOUT_MS
                )
        except Exception:
            self._failed = True
            self.close()
        return self._browser

    def render(self, source: str, width_px: int, height_px: int, theme: Theme) -> bytes | None:
        browser = self._launch()
        if browser is None:
            return None
        width_px, height_px = max(int(width_px), 1), max(int(height_px), 1)
        ctx = None
        try:
            ctx = browser.new_context(
                viewport={"width": width_px, "height": height_px},
                device_scale_factor=SCALE,
                java_script_enabled=False,
            )
            ctx.set_default_timeout(TIMEOUT_MS)

            def gate(route):
                if route.request.url.startswith(("data:", "about:")):
                    route.continue_()
                else:
                    route.abort()

            ctx.route("**/*", gate)
            page = ctx.new_page()
            page.set_content(_page(source, theme), wait_until="load", timeout=TIMEOUT_MS)
            return page.screenshot(
                type="png",
                clip={"x": 0, "y": 0, "width": width_px, "height": height_px},
                timeout=TIMEOUT_MS,
            )
        except Exception:
            return None
        finally:
            if ctx is not None:
                try:
                    ctx.close()
                except Exception:
                    pass

    def close(self) -> None:
        for obj, meth in ((self._browser, "close"), (self._pw, "stop")):
            if obj is not None:
                try:
                    getattr(obj, meth)()
                except Exception:
                    pass
        self._browser = self._pw = None


def render_html_png(source: str, width_px: int, height_px: int, theme: Theme) -> bytes | None:
    """One-shot helper (own browser). Decks use a shared :class:`HtmlRenderer` via ``add_html_image``."""
    r = HtmlRenderer()
    try:
        return r.render(source, width_px, height_px, theme)
    finally:
        r.close()


def add_html_image(rc: RenderCtx, slide, pl: Placed) -> bool:
    """Insert the rendered HTML as a picture at the Placed box; False when no image could be made."""
    el: Raw = pl.element  # type: ignore[assignment]
    renderer = getattr(rc, "html_renderer", None)
    if renderer is None:
        renderer = rc.html_renderer = HtmlRenderer()  # type: ignore[attr-defined]
    png = renderer.render(el.source, round(pl.w / EMU_PER_PX), round(pl.h / EMU_PER_PX), rc.theme)
    if not png:
        if not getattr(rc, "html_warned", False):
            rc.html_warned = True  # type: ignore[attr-defined]
            rc.diag("html-image-unavailable", "HTML block kept as a placeholder", HINT, "info", line=el.line)
        return False
    pic = slide.shapes.add_picture(BytesIO(png), Emu(pl.x), Emu(pl.y), Emu(pl.w), Emu(pl.h))
    rc.html_count = n = getattr(rc, "html_count", 0) + 1  # type: ignore[attr-defined]
    pic.name = f"html {n}"
    pic._element.nvPicPr.cNvPr.set("descr", ALT)
    return True


def close_html(rc: RenderCtx) -> None:
    renderer = getattr(rc, "html_renderer", None)
    if renderer is not None:
        renderer.close()
        rc.html_renderer = None  # type: ignore[attr-defined]
