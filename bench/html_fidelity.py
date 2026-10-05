"""DF4 HTML fidelity: agent-designed HTML slides -> native shapes, measured against Chromium.

For each ``bench/html_corpus/*.html`` (one 1280x720 slide):
- ``native``: share of visible items that became native editable shapes (text, rects, tables) instead of
  pictures. A slide that the pipeline sends to the image fallback as a whole counts 0.
- ``diff``: mean absolute pixel difference (0..1, grayscale, 320x180) between the Chromium screenshot and the
  LibreOffice render of the built .pptx. Lower is better; the recorded value may only go down.

Usage: ``python bench/html_fidelity.py [--record] [--keep DIR]``. Needs Playwright + Chromium and soffice.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "bench" / "html_corpus"
W, H = 12192000, 6858000  # 16:9 slide, EMU
SMALL = (320, 180)


def _gray(png: bytes | Path):
    from PIL import Image

    img = Image.open(BytesIO(png) if isinstance(png, bytes) else png).convert("L")
    return img.resize(SMALL)


def _diff(a, b) -> float:
    pa, pb = a.tobytes(), b.tobytes()
    return sum(abs(x - y) for x, y in zip(pa, pb, strict=True)) / (255 * len(pa))


def measure(path: Path, renderer, keep: Path | None) -> dict:
    from slidemark.htmlnative import convertible, html_to_placed
    from slidemark.ir import Deck, Image, Placed, Slide
    from slidemark.preview import pptx_to_pngs
    from slidemark.render import render
    from slidemark.theme import get_theme

    theme = get_theme("none")
    html = path.read_text(encoding="utf-8")
    shot = renderer.render(html, 1280, 720, theme)
    native, total, placed = 0, 1, []
    res = None
    if convertible(html):
        res = html_to_placed(html, 0, 0, W, H, theme, str(CORPUS), renderer=renderer)
    if res:
        placed = res[0]
        total = max(len(placed), 1)
        native = sum(1 for p in placed if not isinstance(p.element, Image))
    if not placed and shot:  # whole-slide picture, like the build pipeline's fallback
        tmp = Path(tempfile.mkdtemp()) / "fallback.png"
        tmp.write_bytes(shot)
        placed = [Placed(element=Image(src=str(tmp), alt=path.stem), x=0, y=0, w=W, h=H)]
    deck = Deck(theme="none", slides=[Slide()])
    out_dir = keep or Path(tempfile.mkdtemp())
    out_dir.mkdir(parents=True, exist_ok=True)
    pptx = out_dir / f"{path.stem}.pptx"
    render(deck, [placed], theme, pptx)
    diff = None
    if shot:
        pngs = pptx_to_pngs(pptx, out_dir / path.stem)
        if pngs:
            diff = _diff(_gray(shot), _gray(pngs[0]))
            if keep:
                (out_dir / f"{path.stem}-chromium.png").write_bytes(shot)
    return {"slide": path.stem, "native": round(native / total, 3), "items": total, "diff": diff}


def commit() -> str:
    out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    return out.stdout.strip() or "unknown"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", action="store_true")
    ap.add_argument("--keep", type=Path)
    ap.add_argument("files", nargs="*")
    args = ap.parse_args()
    from slidemark.render.htmlimg import HtmlRenderer

    files = [Path(f) for f in args.files] or sorted(CORPUS.glob("*.html"))
    r = HtmlRenderer()
    rows = []
    try:
        for f in files:
            row = measure(f, r, args.keep)
            rows.append(row)
            d = "-" if row["diff"] is None else f"{row['diff']:.3f}"
            print(f"{row['slide']:<24} native {row['native']:.2f} ({row['items']} items)  diff {d}")
    finally:
        r.close()
    diffs = [x["diff"] for x in rows if x["diff"] is not None]
    summary = {
        "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "commit": commit(),
        "metric": "html_fidelity",
        "slides": len(rows),
        "native": round(sum(x["native"] for x in rows) / max(len(rows), 1), 3),
        "native_90": sum(1 for x in rows if x["native"] >= 0.9),
        "diff": round(sum(diffs) / len(diffs), 4) if diffs else None,
    }
    nat = [x["diff"] for x in rows if x["diff"] is not None and x["native"] > 0]
    summary["diff_native"] = round(sum(nat) / len(nat), 4) if nat else None  # pictures hide fidelity gaps
    summary["value"] = summary["native"]
    summary["worst"] = [[x["slide"], x["native"]] for x in sorted(rows, key=lambda x: x["native"])[:5]]
    print(json.dumps(summary, ensure_ascii=False))
    if args.record:
        with (ROOT / "bench" / "history.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(summary, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
