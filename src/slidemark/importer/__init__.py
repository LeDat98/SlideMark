"""``.pptx`` -> SlideMark text (the reverse of ``build``). Never raises: problems become diagnostics."""

from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path

from ..ir import Diagnostic
from ..theme import DEFAULT, JP_BUSINESS, MIDNIGHT, Theme
from .read import ReadCtx, SlideData, read_sections, read_slide
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
    from ..units import to_emu

    deck = DeckInfo(
        width=W,
        height=H,
        accent=accent,
        colors=colors,
        footers=footers,
        sections=read_sections(prs),
        margin_x=to_emu(theme.margin_x),
        gap=to_emu(theme.gap),
    )
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
    solo_titles = False
    for n, sd in enumerate(datas, 1):
        try:
            sdiags: list[Diagnostic] = []
            info: dict = {}
            lines = build_slide(n, sd, deck, sdiags, save_image, classes, info)
            diags.extend(sdiags)
            solo_titles = solo_titles or (n > 1 and bool(info.get("title_only")))
            lines = _shorten(lines, info, sd, deck, classes, header)
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
    if solo_titles and not deck.sections:
        header.append("sections: off")
    text = ("\n".join(header) + "\n\n" if header else "") + "\n\n".join(chunks) + "\n"
    return text, diags


def _variants(tokens: list[str]) -> list[list[str]]:
    """Shorter ``@`` lines to try, shortest first: none, only the flow/chevron word, the full line."""
    words = [t for t in tokens if t in ("chevron", "flow")]
    out: list[list[str]] = [[]]
    if words:
        out.append(words)
    return out


def _shorten(lines, info, sd, deck, classes, header) -> list[str]:
    """Drop ``@`` tokens the auto-arrangement reproduces: build a trial slide and compare its grid."""
    tokens, at = info.get("tokens") or [], info.get("at")
    if at is None or not tokens or tokens == ["blank"]:
        return lines
    hidden = info.get("extra", [])
    try:
        import tempfile

        from pptx import Presentation

        from ..build import build

        for var in _variants(tokens):
            new = [*var, *info.get("links", []), *hidden]
            trial = [*lines[:at], *(["@" + " ".join(new)] if new else []), *lines[at + 1 :]]
            text = ("\n".join(header) + "\n\n" if header else "") + "\n".join(trial) + "\n"
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "t.pptx"
                build(text, path)
                prs = Presentation(str(path))
                ctx = ReadCtx(accent=deck.accent or "")
                ctx.slide_index[prs.slides[0].part] = 1
                got: dict = {}
                build_slide(1, read_slide(prs.slides[0], ctx), deck, [], lambda *a: "", classes, got)
            if got.get("tokens") == tokens:
                return trial
    except Exception:
        return lines
    return lines
