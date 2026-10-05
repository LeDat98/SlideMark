"""Render a .pptx to PNG images with LibreOffice (soffice -> PDF) and pypdfium2."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def have_soffice() -> bool:
    return shutil.which("soffice") is not None


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


def pptx_to_pdf(pptx: str | Path, out_dir: str | Path, timeout: int = 180) -> Path:
    """Convert with an isolated LibreOffice profile so parallel runs and stale locks cannot interfere."""
    pptx, out_dir = Path(pptx), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="slidemark-lo-") as profile:
        cmd = [
            "soffice",
            f"-env:UserInstallation=file://{profile}",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(out_dir),
            str(pptx),
        ]
        env = dict(os.environ, FONTCONFIG_FILE=_fonts_conf(profile))
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
