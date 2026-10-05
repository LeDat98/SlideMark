"""``.pptx`` -> SlideMark text (the reverse of ``build``). Never raises: problems become diagnostics."""

from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path

from ..ir import Diagnostic
from ..theme import DEFAULT, JP_BUSINESS, MIDNIGHT, Theme
from .read import ReadCtx, SlideData, read_slide
from .structure import DeckInfo, build_slide

__all__ = ["import_pptx"]

_THEMES = (JP_BUSINESS, MIDNIGHT)
_JA = re.compile(r"[぀-ヿ㐀-鿿]")
_LATIN = re.compile(r"[A-Za-z]")


def detect_theme(prs) -> Theme:
    """A SlideMark theme when its signature colors appear in the slides, else the default."""
    blob = ""
    for s in prs.slides:
        try:
            blob += s.part.blob.decode("utf-8", "ignore").upper()
        except Exception:
            continue
    for th in _THEMES:
        sig = {th.colors["primary"].lstrip("#").upper()}
        if th.name == "midnight":
            sig.add(th.colors["bg"].lstrip("#").upper())
        if all(f'"{c}"' in blob for c in sig):
            return th
    return DEFAULT


def _size_token(w: int, h: int) -> str | None:
    r = w / h if h else 16 / 9
    if abs(r - 16 / 9) < 0.01:
        return None
    for name, ratio in (("4:3", 4 / 3), ("16:10", 16 / 10), ("A4", 297 / 210)):
        if abs(r - ratio) < 0.01:
            return name
    return f"{round(w / 914400, 2):g}inx{round(h / 914400, 2):g}in"


def _footers(slides: list[SlideData], H: int) -> tuple[str | None, set[str]]:
    n = len(slides)
    raw: dict[str, str] = {}
    named: Counter[str] = Counter()
    bottom: Counter[str] = Counter()
    for sd in slides:
        seen_named, seen_bottom = set(), set()
        for it in sd.items:
            if it.kind != "text":
                continue
            txt = re.sub(r"\s+", " ", it.text).strip()
            raw[txt] = it.text.strip()
            if it.ph == "ftr" or it.name.lower() == "footer":
                seen_named.add(txt)
            elif it.ph is None and it.y >= 0.9 * H and it.h <= 0.08 * H:
                seen_bottom.add(txt)
        named.update(seen_named)
        bottom.update(seen_bottom)
    need = max(1, math.ceil(n / 2))
    texts = {t for t, c in named.items() if c >= need and t}
    texts |= {t for t, c in bottom.items() if c >= max(2, need) and t}
    if not texts:
        return None, set()
    best = max(texts, key=lambda t: (named[t] + bottom[t], -len(t)))
    return raw.get(best, best), {best}


def _lang(slides: list[SlideData]) -> str | None:
    ja = lat = 0
    for sd in slides:
        for it in sd.items:
            for p in it.paras:
                ja += len(_JA.findall(p.plain))
                lat += len(_LATIN.findall(p.plain))
            for row in it.rows:
                for c in row:
                    for p in c.paras:
                        ja += len(_JA.findall(p.plain))
                        lat += len(_LATIN.findall(p.plain))
    return "ja" if ja and ja >= 0.3 * (ja + lat) else None


def import_pptx(path: str | Path, out_dir: str | Path | None = None) -> tuple[str, list[Diagnostic]]:
    """Read ``path`` and return (SlideMark text, diagnostics).

    With ``out_dir`` the pictures are written to ``out_dir/images/`` and referenced as
    ``images/<slide>-<n>.<ext>``; without it only the names are referenced (info diagnostic ``import-image``).
    """
    diags: list[Diagnostic] = []
    try:
        from pptx import Presentation

        prs = Presentation(str(path))
    except Exception as e:
        diags.append(
            Diagnostic(
                level="error",
                message=f"cannot read {path}: {type(e).__name__}: {e}",
                rule="import-unreadable",
                hint="pass a valid .pptx (not .ppt or .key)",
            )
        )
        return "", diags
    try:
        return _import(prs, out_dir, diags)
    except Exception as e:  # last-resort guard
        diags.append(
            Diagnostic(
                level="error",
                message=f"import failed: {type(e).__name__}: {e}",
                rule="import-internal",
                hint="report this deck as a bug",
            )
        )
        return "", diags


def _import(prs, out_dir, diags: list[Diagnostic]) -> tuple[str, list[Diagnostic]]:
    W, H = int(prs.slide_width), int(prs.slide_height)
    theme = detect_theme(prs)
    accent = theme.colors["accent"].lstrip("#").upper()
    ctx = ReadCtx(accent=accent)
    for i, s in enumerate(prs.slides, 1):
        ctx.slide_index[s.part] = i
    datas: list[SlideData] = []
    for i, s in enumerate(prs.slides, 1):
        ctx.slide_no = i
        try:
            datas.append(read_slide(s, ctx))
        except Exception as e:
            datas.append(SlideData())
            ctx.skip(f"slide ({type(e).__name__}: {e})")
    diags.extend(ctx.diags)
    footer, footers = _footers(datas, H)
    colors = {k: v.lstrip("#").upper() for k, v in theme.colors.items()}
    deck = DeckInfo(width=W, height=H, accent=accent, colors=colors, footers=footers)
    classes = {}
    for cname in ("success", "danger", "muted", "accent"):
        classes.setdefault(colors[cname], cname)
    out_path = Path(out_dir) if out_dir else None

    def save_image(slide_no: int, k: int, blob: bytes, ext: str) -> str:
        ext = {"jpeg": "jpg"}.get(ext.lower(), ext.lower())
        ref = f"images/{slide_no}-{k}.{ext}"
        if out_path is None:
            diags.append(
                Diagnostic(
                    level="info",
                    message=f"picture referenced as {ref} but not exported",
                    slide=slide_no,
                    rule="import-image",
                    hint="use -o to write the image files next to the output",
                )
            )
            return ref
        try:
            target = out_path / ref
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(blob)
        except OSError as e:
            diags.append(
                Diagnostic(
                    level="warning",
                    message=f"cannot write {ref}: {e}",
                    slide=slide_no,
                    rule="import-image",
                    hint="check the output directory",
                )
            )
        return ref

    header: list[str] = []
    if theme is not DEFAULT:
        header.append(f"theme: {theme.name}")
    size = _size_token(W, H)
    if size:
        header.append(f"size: {size}")
    lang = _lang(datas)
    if lang:
        header.append(f"lang: {lang}")
    if footer:
        header.append(f"footer: {footer}")
    if any(
        sd.num_field or any(i.ph == "sldNum" or i.name.lower() == "slide number" for i in sd.items)
        for sd in datas
    ):
        header.append("num: on")
    chunks: list[str] = []
    for n, sd in enumerate(datas, 1):
        try:
            sdiags: list[Diagnostic] = []
            lines = build_slide(n, sd, deck, sdiags, save_image, classes)
            diags.extend(sdiags)
        except Exception as e:
            diags.append(
                Diagnostic(
                    level="warning",
                    message=f"slide could not be imported: {type(e).__name__}: {e}",
                    slide=n,
                    rule="import-skipped",
                    hint="the slide was left out; rebuild it by hand",
                )
            )
            lines = ["---"]
        chunks.append("\n".join(lines))
    text = ("\n".join(header) + "\n\n" if header else "") + "\n\n".join(chunks) + "\n"
    return text, diags
