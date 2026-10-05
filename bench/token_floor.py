"""Token floor: how close SlideMark sources are to the cost of their content alone.

For every task with both a SlideMark answer and a python-pptx answer written by the same agent model
(`bench/answers/run-2-sonnet` + `run-2-python-pptx`) and for the corpus q3 deck, this prints:

- content: tokens of the visible text alone (every format has to spend these),
- slidemark / python-pptx totals and their ratio,
- floor ratio = content / python-pptx: the best syntax ratio any text format could reach,
- markup ratio = (slidemark - content) / (python-pptx - content).

It also breaks the SlideMark markup of all answer decks (runs 4–7) down by construct, to show where the
remaining structure tokens go.

Usage:
    python bench/token_floor.py            # print tables
    python bench/token_floor.py --record   # also append a summary row to bench/history.jsonl
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from collections import Counter
from pathlib import Path

import tiktoken

BENCH = Path(__file__).resolve().parent
sys.path.insert(0, str(BENCH))
from markup_tokens import content_text  # noqa: E402

HISTORY = BENCH / "history.jsonl"
PROXY = "o200k_base"
PAIRS = [("run-2-sonnet", "run-2-python-pptx")]
MARKUP_RUNS = ["run-4-sonnet", "run-5-sonnet", "run-6-brand", "run-7-brand"]

# Construct patterns, matched per line in this order; the matched part is counted as that construct.
CONSTRUCTS = [
    ("header key", re.compile(r"^(theme|lang|footer|num|density|size|title|author|sections):\s?")),
    ("tokens/style header", re.compile(r"^(colors|fonts|sizes|style):.*")),
    ("fence line", re.compile(r"^```.*")),
    ("@ line", re.compile(r"^@.*")),
    ("slide #", re.compile(r"^# ")),
    ("box ##/###", re.compile(r"^#{2,3} ")),
    ("attrs {...}", re.compile(r"\{[.#a-z][^}]*\}")),
    ("table pipes", re.compile(r"\|[-:| ]*\|$|\|")),
    ("list marker", re.compile(r"^\s*(?:[-*]|\d+\.)\s")),
    ("quote/callout", re.compile(r"^>\s?(\[![a-z]+\]\s?)?")),
    ("footnote ※", re.compile(r"^※\s?")),
    ("notes ???", re.compile(r"^\?\?\?\s?")),
    ("inline marks", re.compile(r"\*\*|==|~~|`")),
]


def _breakdown(enc, text: str, counts: Counter) -> None:
    in_css = False
    for line in text.splitlines():
        if line.startswith("```"):
            in_css = line.startswith("```css") or line.startswith("```html")
            counts["fence line"] += len(enc.encode(line + "\n"))
            continue
        if in_css:
            counts["css/html fence body"] += len(enc.encode(line + "\n"))
            continue
        for name, pat in CONSTRUCTS:
            for m in pat.finditer(line):
                counts[name] += len(enc.encode(m.group(0)))
            if name in ("header key", "tokens/style header", "@ line") and pat.match(line):
                break


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", action="store_true")
    args = ap.parse_args()
    enc = tiktoken.get_encoding(PROXY)

    def n(text: str) -> int:
        return len(enc.encode(text))

    rows = []
    q3 = BENCH / "corpus" / "q3-review"
    pairs = [("q3-review", q3 / "slidemark.md", q3 / "python-pptx.py")]
    for sm_run, py_run in PAIRS:
        for md in sorted((BENCH / "answers" / sm_run).glob("*.md")):
            py = BENCH / "answers" / py_run / (md.stem + ".py")
            if py.exists():
                pairs.append((md.stem, md, py))
    print(f"{'task':<16}{'content':>8}{'sm':>6}{'pptx':>6}{'sm/pptx':>9}{'floor':>7}{'markup':>8}")
    for name, md, py in pairs:
        src = md.read_text(encoding="utf-8")
        content, sm, pp = n(content_text(src)), n(src), n(py.read_text(encoding="utf-8"))
        markup = (sm - content) / max(pp - content, 1)
        rows.append((name, content, sm, pp))
        print(f"{name:<16}{content:>8}{sm:>6}{pp:>6}{sm / pp:>9.0%}{content / pp:>7.0%}{markup:>8.0%}")
    tc, ts, tp = (sum(r[i] for r in rows[1:]) for i in (1, 2, 3))
    print(
        f"{'eval 01-20':<16}{tc:>8}{ts:>6}{tp:>6}{ts / tp:>9.0%}{tc / tp:>7.0%}{(ts - tc) / (tp - tc):>8.0%}"
    )

    counts: Counter = Counter()
    total = content = 0
    for run in MARKUP_RUNS:
        for md in sorted((BENCH / "answers" / run).glob("*.md")):
            src = md.read_text(encoding="utf-8")
            total += n(src)
            content += n(content_text(src))
            _breakdown(enc, src, counts)
    print(f"\nmarkup by construct ({', '.join(MARKUP_RUNS)}): total {total}, content {content}")
    for name, v in counts.most_common():
        print(f"  {name:<22}{v:>6}  {v / max(total - content, 1):>5.0%} of markup")

    if args.record:
        row = {
            "date": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "metric": "token_floor",
            "q3_ratio": round(rows[0][2] / rows[0][3], 3),
            "q3_floor": round(rows[0][1] / rows[0][3], 3),
            "eval_ratio": round(ts / tp, 3),
            "eval_floor": round(tc / tp, 3),
            "eval_markup_ratio": round((ts - tc) / (tp - tc), 3),
            "tokenizer": PROXY,
        }
        with HISTORY.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
