"""Render a .pptx to PNG images with LibreOffice (soffice -> PDF) and pypdfium2."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Where installers put LibreOffice when it is not on PATH (Windows never adds it; macOS ships an app bundle).
_KNOWN = [
    *(
        Path(os.environ[v]) / "LibreOffice" / "program" / "soffice.exe"
        for v in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432")
        if os.environ.get(v)
    ),
    Path("/Applications/LibreOffice.app/Contents/MacOS/soffice"),
]


def find_soffice() -> str | None:
    """The LibreOffice executable: ``$SLIDEMARK_SOFFICE``, then PATH, then the default install folders."""
    env = os.environ.get("SLIDEMARK_SOFFICE")
    if env and Path(env).is_file():
        return env
    for name in ("soffice", "soffice.exe", "libreoffice"):
        if found := shutil.which(name):
            return found
    return next((str(p) for p in _KNOWN if p.is_file()), None)


def have_soffice() -> bool:
    return find_soffice() is not None


# Office fonts are missing on Linux. Map them to metric-compatible (or same-script) fonts so previews wrap
# text like PowerPoint does: Calibri -> Carlito, Arial -> Liberation Sans, Yu Gothic/Meiryo -> IPA Gothic.
_ALIASES = {
    "Calibri": ["Carlito", "Liberation Sans"],
    "Calibri Light": ["Carlito", "Liberation Sans"],
    "Arial": ["Liberation Sans"],
    "Consolas": ["Liberation Mono", "DejaVu Sans Mono"],
    "Yu Gothic": ["IPAPGothic", "IPAGothic"],
    "Yu Gothic UI": ["IPAPGothic", "IPAGothic"],
    "Meiryo": ["IPAPGothic", "IPAGothic"],
    "MS Gothic": ["IPAGothic"],
    "MS PGothic": ["IPAPGothic"],
}


def _fonts_conf(directory: str) -> str:
    rules = "".join(
        f"<alias binding='same'><family>{name}</family><prefer>"
        + "".join(f"<family>{f}</family>" for f in fams)
        + "</prefer></alias>"
        for name, fams in _ALIASES.items()
    )
    path = Path(directory) / "fonts.conf"
    path.write_text(
        "<?xml version='1.0'?><!DOCTYPE fontconfig SYSTEM 'fonts.dtd'><fontconfig>"
        f"<include ignore_missing='yes'>/etc/fonts/fonts.conf</include>{rules}</fontconfig>",
        encoding="utf-8",
    )
    return str(path)


def _deck_locale(pptx: Path) -> str | None:
    """The text language of the deck (``vi-VN`` ...) when it writes decimal commas, else None.

    LibreOffice formats chart numbers in its own locale; previews of a Vietnamese / German deck should show
    ``3,6`` like PowerPoint does for that audience, so agents do not re-check a correct chart.
    """
    import re
    import zipfile
    from collections import Counter

    from .parser.tabular import is_decimal_comma_lang

    try:
        with zipfile.ZipFile(pptx) as z:
            names = [n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)][:20]
            langs = Counter(
                m
                for n in names
                for m in re.findall(r'\blang="([A-Za-z]{2,3}-[A-Za-z]{2})"', z.read(n).decode())
            )
    except Exception:
        return None
    for lang, _n in langs.most_common():
        if is_decimal_comma_lang(lang):
            return lang
    return None


def _locale_profile(profile: str, locale: str) -> None:
    user = Path(profile) / "user"
    user.mkdir(parents=True, exist_ok=True)
    (user / "registrymodifications.xcu").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<oor:items xmlns:oor="http://openoffice.org/2001/registry">'
        '<item oor:path="/org.openoffice.Setup/L10N"><prop oor:name="ooSetupSystemLocale" oor:op="fuse">'
        f"<value>{locale}</value></prop></item></oor:items>",
        encoding="utf-8",
    )


def pptx_to_pdf(pptx: str | Path, out_dir: str | Path, timeout: int = 180) -> Path:
    """Convert with an isolated LibreOffice profile so parallel runs and stale locks cannot interfere."""
    pptx, out_dir = Path(pptx), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="slidemark-lo-", ignore_cleanup_errors=True) as profile:
        # The profile must be a valid file URL: on Windows "file://C:\\..." makes LibreOffice refuse to
        # start with "bootstrap.ini is corrupt"; as_uri() gives "file:///C:/...".
        cmd = [
            find_soffice() or "soffice",
            f"-env:UserInstallation={Path(profile).as_uri()}",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(out_dir),
            str(pptx),
        ]
        locale = _deck_locale(pptx)
        if locale:
            _locale_profile(profile, locale)
        env = dict(os.environ)
        if sys.platform.startswith("linux"):  # fontconfig aliases only matter where Office fonts are missing
            env["FONTCONFIG_FILE"] = _fonts_conf(profile)
        subprocess.run(cmd, check=True, capture_output=True, timeout=timeout, env=env)
    pdf = out_dir / (pptx.stem + ".pdf")
    if not pdf.exists():
        raise RuntimeError(f"LibreOffice produced no PDF for {pptx}")
    return pdf


def pptx_to_pngs(
    pptx: str | Path, out_dir: str | Path, max_width: int = 1280, timeout: int = 180
) -> list[Path]:
    """Write ``slide-01.png``, ``slide-02.png``, ... to ``out_dir`` (width <= ``max_width``)."""
    import pypdfium2 as pdfium

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="slidemark-pdf-") as tmp:
        pdf = pptx_to_pdf(pptx, tmp, timeout)
        doc = pdfium.PdfDocument(str(pdf))
        paths = []
        for i in range(len(doc)):
            page = doc[i]
            scale = max_width / page.get_width()
            image = page.render(scale=scale).to_pil().convert("RGB")
            path = out_dir / f"slide-{i + 1:02d}.png"
            image.save(path, optimize=True)
            paths.append(path)
        doc.close()
    return paths


def contact_sheet(pngs: list[Path], out: str | Path, tile_width: int = 420) -> Path:
    """All slides in one PNG grid (3 columns from 5 slides, else 2), numbered, at most 1400 px wide."""
    from PIL import Image, ImageDraw

    if not pngs:
        raise ValueError("no slides to put on a contact sheet")
    cols, gap = (3 if len(pngs) >= 5 else 2), 10
    tile_width = min(tile_width, (1400 - gap * (cols + 1)) // cols)
    tiles = []
    for p in pngs:
        with Image.open(p) as im:
            im = im.convert("RGB")
            tiles.append(
                im.resize((tile_width, max(1, round(im.height * tile_width / im.width))), Image.LANCZOS)
            )
    th = max(t.height for t in tiles)
    lab = 14  # slide number strip above each tile: a label on the slide would hide a title band
    rows = -(-len(tiles) // cols)
    size = (cols * tile_width + (cols + 1) * gap, rows * (th + lab + gap) + gap)
    sheet = Image.new("RGB", size, (235, 235, 235))
    draw = ImageDraw.Draw(sheet)
    for i, t in enumerate(tiles):
        x, y = gap + (i % cols) * (tile_width + gap), gap + (i // cols) * (th + lab + gap)
        draw.text((x, y), f"slide {i + 1}", fill=(30, 30, 30))
        sheet.paste(t, (x, y + lab))
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, optimize=True)
    return out
