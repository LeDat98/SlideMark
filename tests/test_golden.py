"""Golden image test: examples rendered through LibreOffice must stay close to stored thumbnails.

Regenerate with ``SLIDEMARK_UPDATE_GOLDEN=1 pytest tests/test_golden.py``.
"""

import importlib.util
import os
from pathlib import Path

import pytest
from PIL import Image, ImageChops, ImageStat

from slidemark import build
from slidemark.preview import pptx_to_pngs

from .helpers import needs_soffice

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = Path(__file__).resolve().parent / "golden"
THUMB = (320, 180)
MAX_MEAN_DIFF = 8.0  # of 255; fonts differ slightly between machines


def _thumb(path: Path) -> Image.Image:
    return Image.open(path).convert("L").resize(THUMB)


@needs_soffice
@pytest.mark.parametrize("md", sorted((ROOT / "examples").glob("*.md")), ids=lambda p: p.stem)
def test_example_matches_golden(md, tmp_path):
    if "html" in md.stem and importlib.util.find_spec("playwright") is None:
        pytest.skip("needs the html extra (Playwright) for native HTML/SVG rendering")
    build(md, tmp_path / "d.pptx")
    pngs = pptx_to_pngs(tmp_path / "d.pptx", tmp_path / "png")
    gdir = GOLDEN / md.stem
    if os.environ.get("SLIDEMARK_UPDATE_GOLDEN"):
        gdir.mkdir(parents=True, exist_ok=True)
        for p in pngs:
            _thumb(p).save(gdir / p.name)
    if not gdir.exists():
        pytest.skip("no golden images yet (run with SLIDEMARK_UPDATE_GOLDEN=1)")
    golden = sorted(gdir.glob("*.png"))
    assert len(golden) == len(pngs), f"{md.stem}: {len(pngs)} slides, {len(golden)} golden (update golden?)"
    for p, g in zip(pngs, golden, strict=True):
        diff = ImageStat.Stat(ImageChops.difference(_thumb(p), Image.open(g).convert("L"))).mean[0]
        assert diff <= MAX_MEAN_DIFF, f"{md.stem}/{p.name}: mean diff {diff:.1f} > {MAX_MEAN_DIFF}"
