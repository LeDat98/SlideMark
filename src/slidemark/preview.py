"""Render a .pptx to PNG images with LibreOffice (soffice -> PDF) and pypdfium2."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


def have_soffice() -> bool:
    return shutil.which("soffice") is not None


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
        subprocess.run(cmd, check=True, capture_output=True, timeout=timeout)
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
