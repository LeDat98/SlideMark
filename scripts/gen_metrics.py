"""Generate src/slidemark/layout/metrics/widths.json from installed fonts (run once; the output is committed).

Advance widths are stored per 1000 em units as integers, grouped by contiguous codepoint runs:
``{"font": {"regular": {"<start hex>": [w, ...]}, "bold": {...}}}``. Carlito stands in for Calibri (metric
compatible), Liberation Sans for Arial, IPAPGothic for Yu Gothic / Meiryo (Latin + half-width kana) and
Liberation Mono for Consolas. Combining marks (U+0300-036F) are not stored: measure.py gives them width 0.

    .venv/bin/python scripts/gen_metrics.py
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import ImageFont

OUT = Path(__file__).resolve().parent.parent / "src/slidemark/layout/metrics/widths.json"
SIZE = 1000

RANGES = [
    (0x20, 0x7E),  # ASCII
    (0xA0, 0x24F),  # Latin-1, Latin Extended-A/B
    (0x1EA0, 0x1EF9),  # Vietnamese precomposed
    (0x2000, 0x206F),  # general punctuation
    (0x20A0, 0x20BF),  # currency (dong, euro, yen)
    (0x2190, 0x21FF),  # arrows
    (0x2200, 0x22FF),  # math operators
    (0x25A0, 0x25FF),  # geometric shapes
]
JP_EXTRA = [(0xFF61, 0xFF9F)]  # half-width kana (full-width kana / CJK punctuation stay 1em: no table)

FONTS = {
    "calibri": {
        "regular": "/usr/share/fonts/truetype/crosextra/Carlito-Regular.ttf",
        "bold": "/usr/share/fonts/truetype/crosextra/Carlito-Bold.ttf",
    },
    "arial": {
        "regular": "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "bold": "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    },
    "jp": {"regular": "/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf"},
    "mono": {
        "regular": "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        "bold": "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
    },
}


def table(path: str, ranges: list[tuple[int, int]]) -> dict[str, list[int]]:
    font = ImageFont.truetype(path, SIZE)
    notdef = font.getlength("￿")
    runs: dict[str, list[int]] = {}
    start: int | None = None
    cur: list[int] = []
    for lo, hi in ranges:
        for cp in range(lo, hi + 1):
            ch = chr(cp)
            w = round(font.getlength(ch))
            blank = ch.isspace() or cp in range(0x200B, 0x2010)
            has = font.getmask(ch).getbbox() is not None or (blank and w != round(notdef))
            if has and w > 0:
                if start is None:
                    start = cp
                    cur = []
                if start + len(cur) != cp:  # contiguity break (should not happen inside a run)
                    runs[f"{start:x}"] = cur
                    start, cur = cp, []
                cur.append(w)
            elif start is not None:
                runs[f"{start:x}"] = cur
                start, cur = None, []
        if start is not None:
            runs[f"{start:x}"] = cur
            start, cur = None, []
    return runs


def main() -> None:
    data: dict[str, dict[str, dict[str, list[int]]]] = {}
    for name, kinds in FONTS.items():
        data[name] = {}
        for kind, path in kinds.items():
            ranges = RANGES + (JP_EXTRA if name == "jp" else [])
            data[name][kind] = table(path, ranges)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    print(f"{OUT} {OUT.stat().st_size} bytes")


if __name__ == "__main__":
    main()
