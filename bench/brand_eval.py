"""DF6 design-freedom check on brand-brief answers (tasks tagged `brand`, 101-140).

For each answer deck: first-pass clean (same rule as eval.py: no warning/error besides missing assets), and
the resolved palette (bg, fg, primary, accent after preset + inline tokens + css :root vars).
Two decks "share a palette" when bg and primary are both equal.
The gate: >= 90% first-pass clean and no shared palettes.

Usage: ``python bench/brand_eval.py bench/answers/<run> [--record]``
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSET_RULES = {"image-missing", "missing-media", "asset-missing"}


def palette(md: Path) -> tuple[dict, list[str]]:
    import tempfile

    from slidemark.build import build

    with tempfile.TemporaryDirectory() as tmp:
        deck = build(md.read_text(encoding="utf-8"), Path(tmp) / "out.pptx", base_dir=tmp)
    from slidemark.template import deck_theme

    theme, _ = deck_theme(deck, md.parent)
    bad = [
        str(d)
        for d in deck.diagnostics
        if d.level in ("warning", "error") and d.rule not in ASSET_RULES and "file not found" not in d.message
    ]
    cols = {k: (theme.color(k) or "").upper() for k in ("bg", "fg", "primary", "accent")}
    cols["theme"] = deck.theme
    return cols, bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("answers", type=Path)
    ap.add_argument("--record", action="store_true")
    args = ap.parse_args()
    rows = []
    for md in sorted(args.answers.glob("1[0-4][0-9]-*.md")):
        if not (101 <= int(md.name[:3]) <= 140):
            continue
        cols, bad = palette(md)
        task = ROOT / "bench" / "tasks" / md.name
        brief = set(re.findall(r"#[0-9A-Fa-f]{6}", task.read_text(encoding="utf-8")) if task.exists() else [])
        brief = {c.upper() for c in brief}
        used = {cols[k] for k in ("bg", "fg", "primary", "accent")}
        follows = not brief or bool(brief & used)
        row = {"task": md.stem, "clean": not bad, "follows": follows, "palette": cols, "problems": bad[:3]}
        rows.append(row)
        if not follows:
            bad = bad + [f"palette {sorted(used)} uses none of the brief colors {sorted(brief)}"]
        print(f"{md.stem:<28} {'ok ' if not bad else 'BAD'} bg={cols['bg']} primary={cols['primary']}")
        for b in bad[:3]:
            print("    ", b)
    seen: dict[tuple[str, str], str] = {}
    shared = []
    for r in rows:
        key = (r["palette"]["bg"], r["palette"]["primary"])
        if key in seen:
            shared.append([seen[key], r["task"]])
        seen.setdefault(key, r["task"])
    clean = sum(r["clean"] for r in rows)
    summary = {
        "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "metric": "brand_eval",
        "run": args.answers.name,
        "tasks": len(rows),
        "first_pass": round(clean / max(len(rows), 1), 3),
        "follows_brief": round(sum(r["follows"] for r in rows) / max(len(rows), 1), 3),
        "shared_palettes": shared,
        "value": round(clean / max(len(rows), 1), 3),
    }
    print(json.dumps(summary, ensure_ascii=False))
    if args.record:
        with (ROOT / "bench" / "eval_history.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(summary, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
