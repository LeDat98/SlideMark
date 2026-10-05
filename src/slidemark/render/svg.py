"""SVG pictures -> native Office SVG (``a:blip`` PNG fallback + ``asvg:svgBlip`` extension). Never raises.

PowerPoint 2016+ shows the crisp SVG (and offers "Convert to Shape"); older apps and LibreOffice show the PNG.
The SVG is untrusted: scripts, event attributes, ``foreignObject`` and external references are stripped
before it is embedded and before it is rasterized (Chromium: JS off, network blocked, see ``htmlimg``).
The ``svg`` fence reaches the renderer as an ``Image`` whose ``src`` is a ``data:image/svg+xml`` URI.
"""

from __future__ import annotations

import base64
import re
from io import BytesIO
from urllib.parse import unquote

from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.opc.package import Part
from pptx.oxml import parse_xml
from pptx.util import Emu

from ..ir import Image, Placed
from .htmlimg import EMU_PER_PX, TIMEOUT_MS, HtmlRenderer
from .util import RenderCtx

__all__ = ["add_svg", "is_svg_src", "sanitize_svg", "svg_size"]

MAX_BYTES = 2 * 1024 * 1024
SVG_NS = "http://www.w3.org/2000/svg"
SVG_EXT_URI = "{96DAC541-7B7A-43D3-8B79-37D633B846F1}"
ASVG_NS = "http://schemas.microsoft.com/office/drawing/2016/SVG/main"
_DROP = {"script", "foreignobject", "iframe", "embed", "object"}
_URL = re.compile(r"url\(\s*(['\"]?)(?!#|data:)[^)]*\)", re.I)
_IMPORT = re.compile(r"@import[^;]*;?", re.I)


def is_svg_src(src: str) -> bool:
    s = src.strip().lower()
    return (
        s.startswith("data:image/svg+xml")
        or re.search(r"\.svgz?$", s.split("?", 1)[0].split("#", 1)[0]) is not None
    )


def _local(tag) -> str:
    return tag.rsplit("}", 1)[-1].lower() if isinstance(tag, str) else ""


def _clean_css(text: str) -> str:
    return _URL.sub("none", _IMPORT.sub("", text))


def sanitize_svg(text: str) -> tuple[str | None, str]:
    """(clean SVG text, "") or (None, reason). Strips script/foreignObject/on*/external references."""
    from lxml import etree

    if not re.search(r"xmlns\s*=\s*[\"']" + re.escape(SVG_NS), text):
        text = re.sub(r"<svg\b", f'<svg xmlns="{SVG_NS}"', text, count=1)
    try:
        parser = etree.XMLParser(
            resolve_entities=False, no_network=True, load_dtd=False, remove_comments=True, remove_pis=True
        )
        root = etree.fromstring(text.encode("utf-8"), parser)
    except Exception:
        return None, "not well-formed XML"
    if _local(root.tag) != "svg":
        return None, "the root element is not <svg>"
    for el in list(root.iter()):
        if not isinstance(el.tag, str):
            continue
        name = _local(el.tag)
        if el is not root and (
            name in _DROP
            or (name in ("set", "animate") and "href" in (el.get("attributeName") or "").lower())
        ):
            if el.getparent() is not None:
                el.getparent().remove(el)
            continue
        for k in list(el.attrib):
            key, val = _local(k), el.attrib[k].strip()
            if key.startswith("on"):
                del el.attrib[k]
            elif key == "href" and not (val.startswith("#") or val.lower().startswith("data:image/")):
                del el.attrib[k]
            elif key == "style":
                el.attrib[k] = _clean_css(el.attrib[k])
        if name == "style" and el.text:
            el.text = _clean_css(el.text)
    return etree.tostring(root, encoding="unicode"), ""


def _num(v: str | None) -> float | None:
    m = re.match(r"\s*([0-9]*\.?[0-9]+)\s*(px|pt|mm|cm|in|em)?\s*$", v or "")
    return float(m.group(1)) if m else None  # percentages and unknown units: use the viewBox


def svg_size(svg: str) -> tuple[float, float]:
    """Intrinsic (width, height) from viewBox, else width/height, else 300x150. Only the ratio matters."""
    m = re.search(r"<svg\b[^>]*>", svg)
    head = m.group(0) if m else ""

    def attr(n: str) -> str | None:
        a = re.search(r"\s" + n + r"\s*=\s*(\"([^\"]*)\"|'([^']*)')", head)
        return (a.group(2) or a.group(3)) if a else None

    vb = [_num(p) for p in re.split(r"[\s,]+", (attr("viewBox") or "").strip())]
    if len(vb) == 4 and vb[2] and vb[3]:
        return vb[2], vb[3]
    w, h = _num(attr("width")), _num(attr("height"))
    return (w, h) if w and h else (300.0, 150.0)


def _load(rc: RenderCtx, im: Image) -> str | None:
    """The SVG text of ``im.src`` (data URI or file); a diagnostic is added and None returned on failure."""
    from .objects import resolve_image

    src = im.src
    try:
        if src.lower().startswith("data:"):
            head, _, body = src.partition(",")
            raw = base64.b64decode(body) if ";base64" in head.lower() else unquote(body).encode("utf-8")
        else:
            path = resolve_image(rc, src)
            if path is None:
                hint = (
                    "download it and use a local path"
                    if "://" in src
                    else "check the path, relative to the .md file"
                )
                rc.diag("image-missing", f"image not found: {src}", hint, line=im.line)
                return None
            if path.stat().st_size > MAX_BYTES:
                raise OverflowError
            raw = path.read_bytes()
        if len(raw) > MAX_BYTES:
            raise OverflowError
        return raw.decode("utf-8-sig", errors="replace")
    except OverflowError:
        rc.diag(
            "svg-too-large", f"SVG larger than {MAX_BYTES >> 20} MB", "simplify or rasterize it", line=im.line
        )
    except Exception as e:
        rc.diag("image-unreadable", f"cannot read SVG: {type(e).__name__}", "check the file", line=im.line)
    return None


def _placeholder_png(w: int, h: int, label: str) -> bytes:
    from PIL import Image as PILImage
    from PIL import ImageDraw

    img = PILImage.new("RGB", (max(w, 32), max(h, 32)), (241, 245, 249))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, img.width - 1, img.height - 1], outline=(148, 163, 184))
    d.text((8, 8), f"[svg] {label}"[:80], fill=(100, 116, 139))
    buf = BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def _rasterize(rc: RenderCtx, svg: str, w_px: int, h_px: int) -> bytes | None:
    renderer = getattr(rc, "html_renderer", None)
    if renderer is None:
        renderer = rc.html_renderer = HtmlRenderer()  # type: ignore[attr-defined]
    uri = "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")
    html = (
        "<style>html,body{background:transparent!important;overflow:hidden}"
        "img{display:block;width:100vw;height:100vh}</style>" + f'<img src="{uri}">'
    )
    with renderer._session(html, w_px, h_px, rc.theme) as page:
        if page is None:
            return None
        try:
            return page.screenshot(
                type="png",
                omit_background=True,
                clip={"x": 0, "y": 0, "width": w_px, "height": h_px},
                timeout=TIMEOUT_MS,
            )
        except Exception:
            return None


def add_svg(rc: RenderCtx, slide, pl: Placed, name: str) -> bool:
    """Insert the SVG picture; False when it cannot be used (the caller draws a placeholder)."""
    im: Image = pl.element  # type: ignore[assignment]
    raw = _load(rc, im)
    if raw is None:
        return False
    svg, why = sanitize_svg(raw)
    if svg is None:
        rc.diag(
            "svg-invalid", f"cannot use SVG: {why}", "write well-formed SVG with an <svg> root", line=im.line
        )
        return False
    try:
        iw, ih = svg_size(svg)
        x, y, w, h = pl.x, pl.y, pl.w, pl.h
        if im.fit != "stretch" and w and h:
            s = min(w / iw, h / ih)
            dw, dh = round(iw * s), round(ih * s)
            top = pl.style.valign == "top"
            x, y, w, h = x + (w - dw) // 2, y + (0 if top else (h - dh) // 2), dw, dh
        w_px, h_px = max(round(w / EMU_PER_PX), 1), max(round(h / EMU_PER_PX), 1)
        png = _rasterize(rc, svg, w_px, h_px)
        if not png:
            if not getattr(rc, "svg_warned", False):
                rc.svg_warned = True  # type: ignore[attr-defined]
                rc.diag(
                    "svg-fallback",
                    "SVG kept; its PNG fallback is a placeholder",
                    "pip install slidemark[html] (Playwright + Chromium) for a real PNG fallback",
                    "info",
                    line=im.line,
                )
            png = _placeholder_png(w_px, h_px, im.alt)
        pic = slide.shapes.add_picture(BytesIO(png), Emu(x), Emu(y), Emu(w), Emu(h))
        pic.name = name
        pic._element.nvPicPr.cNvPr.set("descr", im.alt or "")
        part_ = slide.part
        partname = part_.package.next_partname("/ppt/media/svg%d.svg")
        svg_part = Part(partname, "image/svg+xml", part_.package, svg.encode("utf-8"))
        rid = part_.relate_to(svg_part, RT.IMAGE)
        blip = pic._element.blipFill.blip
        blip.append(
            parse_xml(
                '<a:extLst xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
                f'<a:ext uri="{SVG_EXT_URI}">'
                f'<asvg:svgBlip xmlns:asvg="{ASVG_NS}" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
                f'r:embed="{rid}"/>'
                "</a:ext></a:extLst>"
            )
        )
        return True
    except Exception as e:
        rc.diag("svg-invalid", f"cannot embed SVG: {type(e).__name__}", "check the SVG source", line=im.line)
        return False
