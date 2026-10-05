"""L7 gate "real-world .pptx import >= 95% fidelity": import foreign python-pptx decks and rebuild them.

Each script in bench/answers/run-2-python-pptx/ builds a deck with plain python-pptx. For every deck:
import -> SlideMark text -> build -> compare original vs rebuilt, per slide:
  text    share of the original's words / CJK chars present in the rebuilt deck
  objects min/max ratio of tables, charts (per kind), pictures, connectors
  layout  1 - mean centre distance (normalised by the slide diagonal) of text blocks matched by text
fidelity = mean of the three.

Usage: python bench/import_fidelity.py [--record] [--only 05] [--keep DIR]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ANSWERS = ROOT / "bench" / "answers" / "run-2-python-pptx"

_TOKEN = re.compile(r"[぀-ヿ㐀-鿿豈-﫿]|[^\W_]+", re.UNICODE)
_BULLET = re.compile(r"^[\s•・▪■□◆●○※\-–—*]+")


def tokens(text: str) -> Counter:
    """Words and single CJK chars; whitespace and bullet glyphs do not matter."""
    return Counter(t.lower() for t in _TOKEN.findall(text))


# --------------------------------------------------------------------------- extraction


def _shapes(shapes):
    for sh in shapes:
        yield sh
        if sh.shape_type == 6 or hasattr(sh, "shapes"):  # group
            try:
                yield from _shapes(sh.shapes)
            except Exception:
                pass


def slide_facts(slide, W: int, H: int) -> dict:
    """texts: [(text, cx, cy)] per text-bearing block, objects: Counter, all_text: str."""
    texts: list[tuple[str, float, float]] = []
    objs: Counter = Counter()
    for sh in _shapes(slide.shapes):
        try:
            x, y, w, h = sh.left or 0, sh.top or 0, sh.width or 0, sh.height or 0
            cx, cy = (x + w / 2) / W, (y + h / 2) / H
            el = sh._element
            tag = el.tag.split("}")[1]
            if tag == "cxnSp":
                objs["connector"] += 1
            elif tag == "pic":
                objs["picture"] += 1
            if getattr(sh, "has_table", False) and sh.has_table:
                objs["table"] += 1
                rows = [c.text_frame.text for r in sh.table.rows for c in r.cells]
                texts.append((" ".join(rows), cx, cy))
            elif getattr(sh, "has_chart", False) and sh.has_chart:
                ch = sh.chart
                name = str(ch.chart_type).split(".")[-1].split(" ")[0]
                objs["chart:" + _chart_family(name)] += 1
                parts = []
                if ch.has_title:
                    parts.append(ch.chart_title.text_frame.text)
                try:
                    parts += [str(c) for c in ch.plots[0].categories]
                except Exception:
                    pass
                parts += [s.name or "" for p in ch.plots for s in p.series]
                texts.append((" ".join(parts), cx, cy))
            elif getattr(sh, "has_text_frame", False) and sh.has_text_frame:
                t = sh.text_frame.text
                if t.strip():
                    texts.append((t, cx, cy))
        except Exception:
            continue
    return {"texts": texts, "objs": objs, "all": " ".join(t for t, _, _ in texts)}


def _chart_family(name: str) -> str:
    n = name.upper()
    for key in ("PIE", "DOUGHNUT", "LINE", "AREA", "RADAR", "XY", "BUBBLE"):
        if key in n:
            return {"DOUGHNUT": "PIE", "XY": "SCATTER", "BUBBLE": "SCATTER"}.get(key, key).lower()
    return "bar" if "BAR" in n or "COLUMN" in n else n.lower()


def deck_facts(path: Path) -> list[dict]:
    from pptx import Presentation

    prs = Presentation(str(path))
    W, H = int(prs.slide_width), int(prs.slide_height)
    return [slide_facts(s, W, H) for s in prs.slides]


# --------------------------------------------------------------------------- scoring


def text_recall(orig: Counter, new: Counter) -> float:
    total = sum(orig.values())
    if not total:
        return 1.0
    return sum(min(n, new[t]) for t, n in orig.items()) / total


def object_recall(orig: Counter, new: Counter) -> float:
    keys = set(orig) | set(new)
    if not keys:
        return 1.0
    ratios = []
    for k in keys:
        a, b = orig[k], new[k]
        ratios.append(min(a, b) / max(a, b))
    # weight by the original count so a missing table counts more than a stray connector
    wsum = sum(max(orig[k], 1) for k in keys)
    return sum(r * max(orig[k], 1) for r, k in zip(ratios, keys, strict=True)) / wsum


def layout_similarity(orig: list, new: list) -> float | None:
    """1 - mean centre distance (slide diagonal = 1) of original blocks matched to rebuilt ones by text."""
    diag = (1 + (9 / 16) ** 2) ** 0.5  # coordinates are fractions of width/height; scale y to 16:9 shape
    dists = []
    for text, cx, cy in orig:
        a = tokens(text)
        if not a:
            continue
        best, best_s = None, 0.0
        for t2, x2, y2 in new:
            b = tokens(t2)
            inter = sum((a & b).values())
            s = inter / max(sum(a.values()), 1)
            if s > best_s:
                best, best_s = (x2, y2), s
        if best is None or best_s < 0.5:
            continue
        dx, dy = cx - best[0], (cy - best[1]) * (9 / 16)
        dists.append((dx * dx + dy * dy) ** 0.5 / diag)
    if not dists:
        return None
    return max(0.0, 1 - sum(dists) / len(dists))


def score_pair(original: Path, rebuilt: Path) -> dict:
    """Fidelity of ``rebuilt`` against ``original`` (both .pptx paths)."""
    a, b = deck_facts(original), deck_facts(rebuilt)
    per = []
    for i, fa in enumerate(a):
        fb = b[i] if i < len(b) else {"texts": [], "objs": Counter(), "all": ""}
        t = text_recall(tokens(fa["all"]), tokens(fb["all"]))
        o = object_recall(fa["objs"], fb["objs"])
        lay = layout_similarity(fa["texts"], fb["texts"])
        lay = 0.0 if lay is None and fa["texts"] else (1.0 if lay is None else lay)
        per.append({"text": t, "objects": o, "layout": lay})
    n = max(len(per), 1)
    text = sum(p["text"] for p in per) / n
    objs = sum(p["objects"] for p in per) / n
    lay = sum(p["layout"] for p in per) / n
    if len(b) != len(a):  # lost or invented slides are a text/layout loss
        k = min(len(a), len(b)) / max(len(a), len(b), 1)
        text, lay = text * k, lay * k
    return {
        "text": text,
        "objects": objs,
        "layout": lay,
        "fidelity": (text + objs + lay) / 3,
        "slides": (len(a), len(b)),
    }


def roundtrip(original: Path, work: Path) -> tuple[Path | None, str]:
    """import -> build; returns the rebuilt path (None on failure) and the SlideMark text."""
    from slidemark.build import build
    from slidemark.importer import import_pptx

    text, _ = import_pptx(original, work)
    if not text.strip():
        return None, text
    out = work / (original.stem + ".rebuilt.pptx")
    build(text, out, base_dir=work)
    return out, text


# --------------------------------------------------------------------------- driver


def generate(script: Path, tmp: Path) -> Path | None:
    r = subprocess.run([sys.executable, str(script)], cwd=tmp, capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        print(f"SKIP {script.name}: {r.stderr.strip().splitlines()[-1] if r.stderr.strip() else 'failed'}")
        return None
    made = sorted(tmp.glob(script.stem + "*.pptx")) or sorted(tmp.glob("*.pptx"))
    return made[0] if made else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", action="store_true")
    ap.add_argument("--only", help="substring of the script name")
    ap.add_argument("--keep", help="directory to keep originals, rebuilt decks and .md files")
    args = ap.parse_args()
    rows = []
    with tempfile.TemporaryDirectory() as td:
        base = Path(args.keep) if args.keep else Path(td)
        base.mkdir(parents=True, exist_ok=True)
        for script in sorted(ANSWERS.glob("*.py")):
            if args.only and args.only not in script.name:
                continue
            work = base / script.stem
            work.mkdir(exist_ok=True)
            try:
                orig = generate(script, work)
                if orig is None:
                    continue
                rebuilt, text = roundtrip(orig, work)
                (work / "imported.md").write_text(text, encoding="utf-8")
                if rebuilt is None:
                    rows.append((script.stem, {"text": 0, "objects": 0, "layout": 0, "fidelity": 0.0}))
                    print(f"FAIL {script.stem}: empty import")
                    continue
                rows.append((script.stem, score_pair(orig, rebuilt)))
            except Exception as e:
                print(f"FAIL {script.stem}: {type(e).__name__}: {e}")
                rows.append((script.stem, {"text": 0, "objects": 0, "layout": 0, "fidelity": 0.0}))
    print(f"{'deck':22} {'text':>6} {'objects':>8} {'layout':>7} {'fidelity':>9}")
    for name, s in rows:
        print(f"{name:22} {s['text']:6.3f} {s['objects']:8.3f} {s['layout']:7.3f} {s['fidelity']:9.3f}")
    overall = sum(s["fidelity"] for _, s in rows) / len(rows) if rows else 0.0
    print(f"overall fidelity {overall:.3f} over {len(rows)} decks")
    if args.record:
        sha = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT
        )
        row = {
            "date": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "commit": sha.stdout.strip(),
            "metric": "import_fidelity",
            "import_fidelity": round(overall, 3),
            "value": round(overall, 3),
            "decks": len(rows),
            "worst": sorted(((n, round(s["fidelity"], 3)) for n, s in rows), key=lambda x: x[1])[:3],
        }
        with (ROOT / "bench" / "history.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
