"""Native video/audio (``![demo](a.mp4)``): poster frame, movie part, playback timing.

PowerPoint-specific XML (``p:video``/``p:audio`` media nodes, the ``playFrom(0.0)`` autoplay call, looping via
``repeatCount``) follows what PowerPoint itself writes but is not verified in real PowerPoint.
"""

from __future__ import annotations

import io
from pathlib import Path

from lxml import etree
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches

from ..ir import Media, Placed
from .objects import resolve_image
from .util import RenderCtx

_NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
_RT_VIDEO = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/video"
_RT_AUDIO = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/audio"
MIME = {
    ".mp4": "video/mp4",
    ".m4v": "video/mp4",
    ".mov": "video/quicktime",
    ".wmv": "video/x-ms-wmv",
    ".avi": "video/x-msvideo",
    ".webm": "video/webm",
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".wav": "audio/wav",
    ".aac": "audio/aac",
    ".wma": "audio/x-ms-wma",
}
AUDIO_SIDE = Inches(1.2)


def _specs(rc: RenderCtx) -> list:
    return rc.__dict__.setdefault("_media_specs", [])


def poster_png(kind: str, w: int, h: int) -> bytes:
    """Neutral poster: dark gray frame with a white play triangle (video) or speaker (audio)."""
    from PIL import Image, ImageDraw

    px = (960, round(960 * h / w)) if w >= h else (round(960 * w / h), 960)
    px = (max(px[0], 16), max(px[1], 16))
    im = Image.new("RGB", px, (45, 45, 48))
    d = ImageDraw.Draw(im)
    cx, cy, r = px[0] / 2, px[1] / 2, min(px) * 0.17
    if kind == "video":
        d.polygon([(cx - r * 0.75, cy - r), (cx - r * 0.75, cy + r), (cx + r * 1.1, cy)], fill="white")
    else:
        d.polygon(
            [
                (cx - r, cy - r * 0.4),
                (cx - r * 0.4, cy - r * 0.4),
                (cx + r * 0.3, cy - r),
                (cx + r * 0.3, cy + r),
            ]
            + [(cx - r * 0.4, cy + r * 0.4), (cx - r, cy + r * 0.4)],
            fill="white",
        )
        d.arc((cx, cy - r * 0.6, cx + r * 0.9, cy + r * 0.6), -60, 60, fill="white", width=max(2, int(r / 6)))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def add_media(rc: RenderCtx, slide, pl: Placed, name: str) -> bool:
    """Add the movie shape; False when the file is unusable (caller draws a labeled placeholder)."""
    m: Media = pl.element  # type: ignore[assignment]
    path = resolve_image(rc, m.src)
    if path is None:
        hint = (
            "download it and use a local path"
            if "://" in m.src
            else "check the path, relative to the .md file"
        )
        rc.diag("missing-media", f"{m.kind} file not found: {m.src}", hint, line=m.line)
        return False
    try:
        x, y, w, h = pl.x, pl.y, pl.w, pl.h
        if m.kind == "audio":
            side = min(AUDIO_SIDE, w, h)
            x, y, w, h = x + (w - side) // 2, y + (h - side) // 2, side, side
        else:  # 16:9 contained in the box
            dw, dh = (w, round(w * 9 / 16)) if w * 9 <= h * 16 else (round(h * 16 / 9), h)
            x, y, w, h = x + (w - dw) // 2, y + (h - dh) // 2, dw, dh
        poster = None
        if m.poster:
            pp = resolve_image(rc, m.poster)
            if pp is not None:
                poster = str(pp)
            else:
                rc.diag(
                    "missing-media", f"poster not found: {m.poster}", "check the poster path", line=m.line
                )
        if poster is None:
            poster = io.BytesIO(poster_png(m.kind, w, h))
        mime = MIME.get(Path(m.src.split("?", 1)[0]).suffix.lower(), "video/unknown")
        gf = slide.shapes.add_movie(str(path), Emu(x), Emu(y), Emu(w), Emu(h), poster, mime)
        el = gf._element
        sld = slide._element
        for t in sld.findall(qn("p:timing")):  # python-pptx's own node; rebuilt in finish_timing
            sld.remove(t)
        el.nvPicPr.cNvPr.set("name", name)
        el.nvPicPr.cNvPr.set("descr", m.alt or "")
        if m.kind == "audio":
            vf = el.find(f".//{qn('a:videoFile')}")
            if vf is not None:
                vf.tag = qn("a:audioFile")
            for rel in slide.part.rels.values():
                if rel.reltype == _RT_VIDEO:
                    rel._reltype = _RT_AUDIO
                    rel.__dict__.pop("reltype", None)  # lazyproperty cache
        _specs(rc).append((el.nvPicPr.cNvPr.get("id"), m.kind, m.autoplay, m.loop))
        return True
    except Exception as e:
        rc.diag(
            "media-unreadable",
            f"cannot embed {m.src}: {type(e).__name__}",
            "use a readable local .mp4/.mp3 file",
            line=m.line,
        )
        return False


def _skeleton() -> etree._Element:
    return etree.fromstring(
        f'<p:timing xmlns:p="{_NS_P}"><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" '
        'nodeType="tmRoot"><p:childTnLst><p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" '
        'nodeType="mainSeq"><p:childTnLst/></p:cTn><p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl>'
        '<p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst><p:nextCondLst><p:cond evt="onNext" delay="0">'
        "<p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst></p:seq></p:childTnLst></p:cTn></p:par>"
        "</p:tnLst></p:timing>"
    )


def finish_timing(rc: RenderCtx, slide) -> None:
    """Add the media nodes (and autoplay calls) for this slide's movies to ``p:timing``; clears the specs."""
    specs = _specs(rc)
    if not specs:
        return
    items = list(specs)
    specs.clear()
    sld = slide._element
    timing = sld.find(qn("p:timing"))
    if timing is None:
        timing = _skeleton()
        anchor = None
        for tag in ("p:transition", "p:clrMapOvr", "p:cSld"):
            anchor = sld.find(qn(tag))
            if anchor is not None:
                break
        anchor.addnext(timing)
    ns = {"p": _NS_P}
    root = timing.xpath("./p:tnLst/p:par/p:cTn/p:childTnLst", namespaces=ns)[0]
    main = timing.xpath(".//p:cTn[@nodeType='mainSeq']", namespaces=ns)
    nxt = max(int(i) for i in timing.xpath(".//p:cTn/@id", namespaces=ns)) + 1
    auto: list[str] = []
    for spid, kind, autoplay, loop in items:
        rep = ' repeatCount="indefinite"' if loop else ""
        root.append(
            etree.fromstring(
                f'<p:{kind} xmlns:p="{_NS_P}"><p:cMediaNode vol="80000"><p:cTn id="{nxt}" fill="hold" '
                f'display="0"{rep}><p:stCondLst><p:cond delay="indefinite"/></p:stCondLst></p:cTn>'
                f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl></p:cMediaNode></p:{kind}>'
            )
        )
        nxt += 1
        if autoplay and main:
            auto.append(
                f'<p:par xmlns:p="{_NS_P}"><p:cTn id="{nxt}" fill="hold">'
                f'<p:stCondLst><p:cond delay="indefinite"/>'
                f'<p:cond evt="onBegin" delay="0"><p:tn val="{main[0].get("id")}"/></p:cond></p:stCondLst>'
                f'<p:childTnLst><p:par><p:cTn id="{nxt + 1}" fill="hold"><p:stCondLst><p:cond delay="0"/>'
                f'</p:stCondLst><p:childTnLst><p:par><p:cTn id="{nxt + 2}" presetID="1" '
                f'presetClass="mediacall" '
                f'presetSubtype="0" fill="hold" nodeType="afterEffect"><p:stCondLst><p:cond delay="0"/>'
                f'</p:stCondLst><p:childTnLst><p:cmd type="call" cmd="playFrom(0.0)"><p:cBhvr>'
                f'<p:cTn id="{nxt + 3}" dur="1" fill="hold"/><p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl>'
                "</p:cBhvr></p:cmd></p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par>"
                "</p:childTnLst></p:cTn></p:par>"
            )
            nxt += 4
    if auto:
        seq = main[0].find(qn("p:childTnLst"))
        for k, xml in enumerate(auto):
            seq.insert(k, etree.fromstring(xml))
    # an empty main sequence (no autoplay, no build animations) is a schema error: drop it and renumber
    for cTn in timing.xpath(".//p:cTn[@nodeType='mainSeq']", namespaces=ns):
        if len(cTn.find(qn("p:childTnLst"))) == 0:
            seq = cTn.getparent()
            seq.getparent().remove(seq)
            for k, node in enumerate(timing.xpath(".//p:cTn", namespaces=ns), start=1):
                node.set("id", str(k))
