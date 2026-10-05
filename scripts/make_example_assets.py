"""Create the binary assets used by examples/10-template.md (a user template and a photo-like image)."""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw
from pptx import Presentation

ASSETS = Path(__file__).resolve().parent.parent / "examples" / "assets"


def template(path: Path) -> None:
    prs = Presentation()
    prs.slide_width, prs.slide_height = 12192000, 6858000
    tmp = path.with_suffix(".tmp.pptx")
    prs.save(tmp)
    with zipfile.ZipFile(tmp) as zin, zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "ppt/theme/theme1.xml":
                x = data.decode("utf-8")
                colors = (
                    ("accent1", "0F766E"),
                    ("accent2", "B45309"),
                    ("accent3", "7C3AED"),
                    ("dk2", "334155"),
                )
                for k, v in colors:
                    x = re.sub(rf"(<a:{k}>).*?(</a:{k}>)", rf'\1<a:srgbClr val="{v}"/>\2', x, flags=re.S)
                x = re.sub(r'(<a:majorFont><a:latin typeface=")[^"]*', r"\1Liberation Serif", x)
                x = re.sub(r'(<a:minorFont><a:latin typeface=")[^"]*', r"\1Liberation Sans", x)
                data = x.encode("utf-8")
            zout.writestr(item, data)
    tmp.unlink()


def photo(path: Path) -> None:
    """A synthetic landscape (sky gradient, sun, hills) so the example needs no external image."""
    w, h = 960, 540
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)], fill=(int(30 + 120 * t), int(90 + 110 * t), int(160 + 60 * t)))
    d.ellipse([650, 90, 790, 230], fill=(253, 224, 71))
    d.polygon(
        [(0, 400), (220, 300), (480, 390), (720, 310), (960, 380), (960, 540), (0, 540)], fill=(21, 128, 61)
    )
    d.polygon([(0, 470), (300, 400), (640, 470), (960, 430), (960, 540), (0, 540)], fill=(22, 101, 52))
    img.save(path, optimize=True)


if __name__ == "__main__":
    ASSETS.mkdir(parents=True, exist_ok=True)
    template(ASSETS / "corp-template.pptx")
    photo(ASSETS / "landscape.png")
    print("wrote", *sorted(p.name for p in ASSETS.iterdir()))
