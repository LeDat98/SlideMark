"""DL3d gate: foreign-deck round trip. Import a .pptx made elsewhere, rebuild it, compare slide by slide.

    python bench/roundtrip_compare.py ORIG.pptx [--out DIR] [--regen]

Steps: ``slidemark import`` ORIG -> deck.md -> ``build`` -> imported.pptx; both decks are rendered with
``slidemark.preview.pptx_to_pngs``. Writes to DIR (default ``roundtrip-<stem>`` in the current directory):

    deck.md        the imported text
    compare-N.png  side-by-side sheets, 8 pairs per sheet, labelled (left original, right import -> build)
    report.json    per-slide mean pixel difference (tests/test_golden.py measure: 320x180 grayscale, mean of
                   |a - b| over 255 levels), deck mean, token counts, import warnings, slides over tolerance

``--regen`` rebuilds ORIG from the ``build.py`` next to it when the .pptx is absent (python-pptx run
with ``$PPTX_PYTHON`` or the current interpreter). Gate (docs/TARGETS.md DL3d): deck mean <= 8, no slide over
the tolerance that is "broken", imported deck.md <= 40% of the tokens of build.py.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

TOLERANCE = 8.0  # tests/test_golden.py MAX_MEAN_DIFF
THUMB = (320, 180)  # tests/test_golden.py THUMB
PER_SHEET = 8


def _tokens(text: str) -> int:
    import tiktoken

    return len(tiktoken.get_encoding("o200k_base").encode(text))


def _thumb(path: Path):
    from PIL import Image

    with Image.open(path) as im:
        return im.convert("L").resize(THUMB)


def slide_diff(a: Path | None, b: Path | None) -> float:
    """Mean pixel difference of two renders (0-255); a missing slide counts as a blank page."""
    from PIL import Image, ImageChops, ImageStat

    blank = Image.new("L", THUMB, 255)
    ia = _thumb(a) if a else blank
    ib = _thumb(b) if b else blank
    return float(ImageStat.Stat(ImageChops.difference(ia, ib)).mean[0])


def sheets(left: list[Path], right: list[Path], diffs: list[float], out: Path, tile: int = 560) -> list[Path]:
    """Side-by-side sheets: one row per slide pair, labelled with the slide number and its difference."""
    from PIL import Image, ImageDraw

    gap, lab = 10, 16
    n = max(len(left), len(right))
    paths = []
    for s in range(0, n, PER_SHEET):
        idx = list(range(s, min(n, s + PER_SHEET)))
        tiles = []
        for i in idx:
            row = []
            for src in (left, right):
                if i < len(src):
                    with Image.open(src[i]) as im:
                        im = im.convert("RGB")
                        row.append(im.resize((tile, max(1, round(im.height * tile / im.width)))))
                else:
                    row.append(Image.new("RGB", (tile, round(tile * 9 / 16)), (255, 255, 255)))
            tiles.append(row)
        rh = [max(t.height for t in row) for row in tiles]
        sheet = Image.new(
            "RGB",
            (2 * tile + 3 * gap, sum(rh) + (lab + gap) * len(idx) + gap),
            (235, 235, 235),
        )
        d = ImageDraw.Draw(sheet)
        y = gap
        for k, i in enumerate(idx):
            diff = f"  diff {diffs[i]:.1f}" if i < len(diffs) else ""
            d.text((gap, y), f"slide {i + 1} original", fill=(30, 30, 30))
            d.text((2 * gap + tile, y), f"slide {i + 1} import -> build (SlideMark){diff}", fill=(30, 30, 30))
            sheet.paste(tiles[k][0], (gap, y + lab))
            sheet.paste(tiles[k][1], (2 * gap + tile, y + lab))
            y += lab + rh[k] + gap
        p = out / f"compare-{s // PER_SHEET + 1}.png"
        sheet.save(p, optimize=True)
        paths.append(p)
    return paths


def regen(pptx: Path, out: Path) -> Path:
    """Run ``build.py`` next to ``pptx`` (cwd = a scratch folder) and return the deck it wrote."""
    script = pptx.parent / "build.py"
    if not script.is_file():
        raise FileNotFoundError(f"{pptx} is absent and there is no {script} to regenerate it")
    work = out / "regen"
    work.mkdir(parents=True, exist_ok=True)
    py = os.environ.get("PPTX_PYTHON") or sys.executable
    subprocess.run([py, str(script.resolve())], cwd=work, check=True, capture_output=True, timeout=300)
    made = sorted(work.glob("*.pptx"))
    if not made:
        raise RuntimeError(f"{script} wrote no .pptx into {work}")
    return made[0]


def compare(orig: Path, out: Path, do_regen: bool = False) -> dict:
    """Run the whole measurement; returns the report (also written to ``out/report.json``)."""
    from slidemark.build import build
    from slidemark.importer import import_pptx
    from slidemark.preview import pptx_to_pngs

    orig = Path(orig)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    src_dir = orig.parent
    if not orig.is_file():
        if not do_regen:
            raise FileNotFoundError(f"{orig}: no such file (pass --regen to rebuild it from build.py)")
        orig = regen(orig, out)
    text, diags = import_pptx(orig, out, slim=True)
    (out / "deck.md").write_text(text, encoding="utf-8")
    imported = out / "imported.pptx"
    build(text, imported, base_dir=out)
    left = pptx_to_pngs(orig, out / "png-original")
    right = pptx_to_pngs(imported, out / "png-import")
    n = max(len(left), len(right))
    diffs = [
        round(slide_diff(left[i] if i < len(left) else None, right[i] if i < len(right) else None), 2)
        for i in range(n)
    ]
    sheet_paths = sheets(left, right, diffs, out)
    script = src_dir / "build.py"
    py_tokens = _tokens(script.read_text(encoding="utf-8")) if script.is_file() else None
    md_tokens = _tokens(text)
    warnings = [d for d in diags if d.level == "warning"]
    report = {
        "original": orig.name,
        "slides": len(left),
        "slides_imported": len(right),
        "per_slide": diffs,
        "mean": round(sum(diffs) / len(diffs), 2) if diffs else None,
        "max": max(diffs, default=None),
        "tolerance": TOLERANCE,
        "over_tolerance": [i + 1 for i, v in enumerate(diffs) if v > TOLERANCE],
        "md_tokens": md_tokens,
        "build_py_tokens": py_tokens,
        "token_ratio": round(md_tokens / py_tokens, 3) if py_tokens else None,
        "import_warnings": len(warnings),
        "warnings": [str(d) for d in warnings],
        "sheets": [p.name for p in sheet_paths],
    }
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    return report


def summary(r: dict) -> str:
    ratio = (
        f"{r['token_ratio']:.0%} of build.py ({r['md_tokens']}/{r['build_py_tokens']})"
        if r["token_ratio"]
        else (f"{r['md_tokens']} tokens")
    )
    over = ",".join(map(str, r["over_tolerance"])) or "-"
    return (
        f"{r['original']}: {r['slides']} slides, mean diff {r['mean']} (tolerance {r['tolerance']:g}), "
        f"over tolerance: {over}, deck.md {ratio}, import warnings {r['import_warnings']}"
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("pptx", type=Path)
    ap.add_argument("--out", type=Path, default=None, help="output folder (default roundtrip-<stem>)")
    ap.add_argument(
        "--regen", action="store_true", help="rebuild the original from build.py when it is absent"
    )
    args = ap.parse_args(argv)
    out = args.out or Path(f"roundtrip-{args.pptx.stem}")
    try:
        report = compare(args.pptx, out, args.regen)
    except (FileNotFoundError, RuntimeError, subprocess.CalledProcessError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(summary(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
