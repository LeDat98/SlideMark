"""Token cost of the three design paths for the same branded slide (DESIGN_FREEDOM rule 6).

`bench/corpus/design/`: `tokens.md` (header token lines), `css.md` (a css fence), `html.html` (hand-written
HTML/CSS). Prints o200k tokens per path and the ratio to the HTML path. ``--record`` appends to history.jsonl.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import tiktoken

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "bench" / "corpus" / "design"


def main() -> int:
    enc = tiktoken.get_encoding("o200k_base")
    counts = {p.stem: len(enc.encode(p.read_text(encoding="utf-8"))) for p in sorted(DIR.iterdir())}
    html = counts.get("html", 1)
    for k, v in counts.items():
        print(f"{k:<8} {v:>5}  {v / html:5.0%} of html")
    if "--record" in sys.argv:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True)
        row = {
            "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "commit": sha.stdout.strip(),
            "metric": "design_tokens",
            **counts,
            "value": round(counts.get("tokens", 0) / html, 3),
        }
        with (ROOT / "bench" / "history.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
