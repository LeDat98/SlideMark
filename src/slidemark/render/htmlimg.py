"""Raw HTML block -> PNG through headless Chromium (optional extra ``slidemark[html]``). Never raises.

One browser is launched lazily per render and reused for every HTML block of the deck. JavaScript is off
and every request that is not ``data:`` / ``about:`` is aborted, so untrusted HTML cannot fetch anything.
"""

from __future__ import annotations

import glob
import os
import re
from contextlib import contextmanager
from io import BytesIO

from pptx.util import Emu

from ..ir import Placed, Raw
from ..theme import DEFAULT_SIZES, Theme
from .util import RenderCtx, hex6

__all__ = ["HtmlRenderer", "add_html_image", "add_html_native", "close_html", "render_html_png"]

SCALE = 2
TIMEOUT_MS = 15_000
EMU_PER_PX = 9525
ALT = "HTML block (image fallback)"
HINT = "pip install slidemark[html] (Playwright + Chromium) to render HTML blocks as images"


# metric-compatible stand-ins, tried right after the theme font (what PowerPoint/LibreOffice would use)
_ALIASES = {
    "calibri": "Carlito",
    "arial": "Liberation Sans",
    "helvetica": "Liberation Sans",
    "times new roman": "Liberation Serif",
    "yu gothic": "IPAPGothic",
    "meiryo": "IPAPGothic",
    "ms pgothic": "IPAPGothic",
}


def _family(theme: Theme) -> str:
    names: list[str] = []
    for f in (theme.fonts.body, theme.fonts.ea):
        f = re.sub(r"[^\w .-]", "", f or "").strip()
        if f:
            names += [f, _ALIASES.get(f.lower(), "")]
    return ", ".join(f"'{n}'" for n in names if n) + ", sans-serif"


def _page(source: str, theme: Theme) -> str:
    fg, bg = hex6(theme, "fg"), hex6(theme, "bg", theme.render.slide_bg)
    size = theme.sizes.get("body", DEFAULT_SIZES["body"]) * 96 / 72
    return (
        '<!doctype html><html><head><meta charset="utf-8">'
        f"<style>*{{box-sizing:border-box}}html,body{{margin:0;padding:0;background:#{bg};}}"
        f"body{{font-family:{_family(theme)};font-size:{size:.1f}px;color:#{fg};overflow:hidden}}"
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

    @contextmanager
    def _session(self, source: str, width_px: int, height_px: int, theme: Theme, scale: int = SCALE):
        """A loaded page (JS off, only data:/about: requests), or None when Chromium is unavailable."""
        browser = self._launch()
        if browser is None:
            yield None
            return
        ctx = page = None
        try:
            ctx = browser.new_context(
                viewport={"width": max(int(width_px), 1), "height": max(int(height_px), 1)},
                device_scale_factor=scale,
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
        except Exception:
            page = None
        try:
            yield page
        finally:
            if ctx is not None:
                try:
                    ctx.close()
                except Exception:
                    pass

    def render(self, source: str, width_px: int, height_px: int, theme: Theme) -> bytes | None:
        width_px, height_px = max(int(width_px), 1), max(int(height_px), 1)
        with self._session(source, width_px, height_px, theme) as page:
            if page is None:
                return None
            try:
                return page.screenshot(
                    type="png",
                    clip={"x": 0, "y": 0, "width": width_px, "height": height_px},
                    timeout=TIMEOUT_MS,
                )
            except Exception:
                return None

    def evaluate(self, source: str, width_px: int, height_px: int, theme: Theme, script: str):
        """Lay the HTML out at the given size and return ``script``'s JSON result (None on any failure)."""
        with self._session(source, width_px, height_px, theme, scale=1) as page:
            if page is None:
                return None
            try:
                return page.evaluate(script)
            except Exception:
                return None

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


def add_html_native(rc: RenderCtx, pl: Placed, draw) -> bool:
    """Try the native-shape path for an HTML block: ``draw(placed)`` renders each item. False = use the image.

    ``{render=image}`` skips it; ``{render=native}`` skips the ``convertible`` check. Never raises.
    """
    from ..htmlnative import convertible, html_to_placed

    el: Raw = pl.element  # type: ignore[assignment]
    mode = str(el.attrs.get("render", "")).lower()
    if mode == "image" or (mode != "native" and not convertible(el.source)):
        return False
    renderer = getattr(rc, "html_renderer", None)
    if renderer is None:
        renderer = rc.html_renderer = HtmlRenderer()  # type: ignore[attr-defined]
    res = html_to_placed(el.source, pl.x, pl.y, pl.w, pl.h, rc.theme, rc.base_dir, renderer=renderer)
    if res is None:
        return False
    items, diags = res
    for d in diags:
        rc.diag(d.rule or "html-native", d.message, d.hint or "", d.level, line=el.line)
    for item in items:
        draw(item)
    return True
