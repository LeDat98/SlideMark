"""Count tokens for every source file in bench/corpus and optionally record them.

Usage:
    python bench/count_tokens.py            # print a table
    python bench/count_tokens.py --record   # also append one line per file to bench/history.jsonl

Tokenizer: ``o200k_base`` (tiktoken) is a deterministic offline proxy. When
ANTHROPIC_API_KEY is set, exact Claude counts are added via the count_tokens API.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
from pathlib import Path

import tiktoken

BENCH = Path(__file__).resolve().parent
CORPUS = BENCH / "corpus"
HISTORY = BENCH / "history.jsonl"
PROXY = "o200k_base"


def claude_tokens(text: str) -> int | None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    import anthropic

    resp = anthropic.Anthropic().messages.count_tokens(
        model=os.environ.get("SLIDEMARK_BENCH_MODEL", "claude-sonnet-5-5"),
        messages=[{"role": "user", "content": text}],
    )
    return resp.input_tokens


def git_sha() -> str:
    out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=BENCH)
    return out.stdout.strip() or "unknown"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()

    enc = tiktoken.get_encoding(PROXY)
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    sha = git_sha()
    rows = []
    for path in sorted(p for p in CORPUS.rglob("*") if p.is_file()):
        text = path.read_text(encoding="utf-8")
        rows.append(
            {
                "date": now,
                "commit": sha,
                "metric": "syntax_tokens",
                "deck": path.parent.name,
                "format": path.stem,
                "tokens_proxy": len(enc.encode(text)),
                "tokens_claude": claude_tokens(text),
                "tokenizer": PROXY,
            }
        )

    for deck in sorted({r["deck"] for r in rows}):
        group = [r for r in rows if r["deck"] == deck]
        base = next((r["tokens_proxy"] for r in group if r["format"] == "python-pptx"), None)
        print(f"\n{deck}")
        for r in sorted(group, key=lambda r: r["tokens_proxy"]):
            ratio = f"{r['tokens_proxy'] / base:5.0%}" if base else ""
            print(f"  {r['format']:<20} {r['tokens_proxy']:>6}  {ratio}")

    if args.record:
        with HISTORY.open("a", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"\nappended {len(rows)} rows to {HISTORY.relative_to(BENCH.parent)}")


if __name__ == "__main__":
    main()
