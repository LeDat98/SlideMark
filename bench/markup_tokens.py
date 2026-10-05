"""Markup-only token cost: tokens a format spends on structure, not on the slide content itself.

For each corpus deck, the content is taken from the SlideMark source's IR (every visible string: titles,
text runs, table cells, chart title/categories/series names and values, notes). Both formats of the same
deck carry that same content, so ``markup = tokens(file) - tokens(content)`` compares structure cost fairly.

Usage:
    python bench/markup_tokens.py            # print a table
    python bench/markup_tokens.py --record   # also append rows to bench/history.jsonl
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import tiktoken

from slidemark import parse

BENCH = Path(__file__).resolve().parent
CORPUS = BENCH / "corpus"
HISTORY = BENCH / "history.jsonl"
PROXY = "o200k_base"


def _num(v: float | None) -> str:
    if v is None:
        return ""
    return str(int(v)) if float(v).is_integer() else str(v)


def _walk(node, out: list[str]) -> None:
    if node is None:
        return
    if isinstance(node, list):
        for n in node:
            _walk(n, out)
        return
    for attr in ("title", "subtitle", "lead", "conclusion"):
        value = getattr(node, attr, None)
        if isinstance(value, str):
            out.append(value)
        else:
            _walk(value, out)
    for p in getattr(node, "paragraphs", None) or []:
        out.append(p.plain)
    for row in getattr(node, "rows", None) or []:
        for cell in row:
            out.extend(p.plain for p in cell.paragraphs)
    if getattr(node, "type", None) == "chart":
        out.extend(node.categories)
        for s in node.series:
            out.append(s.name)
            out.extend(_num(v) for v in s.values)
    if getattr(node, "type", None) in ("code", "raw"):
        out.append(getattr(node, "text", None) or getattr(node, "source", ""))
    _walk(getattr(node, "footnotes", None), out)
    _walk(getattr(node, "elements", None), out)
    _walk(getattr(node, "children", None), out)


def content_text(source: str) -> str:
    deck = parse(source)
    out: list[str] = []
    for slide in deck.slides:
        _walk(slide, out)
        if slide.notes:
            out.append(slide.notes)
    if deck.footer:
        out.append(deck.footer)
    return "\n".join(s for s in out if s)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", action="store_true")
    args = ap.parse_args()
    enc = tiktoken.get_encoding(PROXY)
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    rows = []
    for deck_dir in sorted(p for p in CORPUS.iterdir() if p.is_dir()):
        sm, html = deck_dir / "slidemark.md", deck_dir / "html.html"
        if not (sm.exists() and html.exists()):
            continue
        content = len(enc.encode(content_text(sm.read_text(encoding="utf-8"))))
        sm_t = len(enc.encode(sm.read_text(encoding="utf-8")))
        html_t = len(enc.encode(html.read_text(encoding="utf-8")))
        sm_m, html_m = max(sm_t - content, 0), max(html_t - content, 0)
        ratio = sm_m / html_m if html_m else 0.0
        rows.append(
            {
                "date": now,
                "metric": "markup_tokens",
                "deck": deck_dir.name,
                "content": content,
                "slidemark_markup": sm_m,
                "html_markup": html_m,
                "ratio": round(ratio, 3),
                "tokenizer": PROXY,
            }
        )
        print(
            f"{deck_dir.name:<12} content {content:>4}  slidemark {sm_t:>4} (markup {sm_m:>4})  "
            f"html {html_t:>4} (markup {html_m:>4})  markup ratio {ratio:.0%}"
        )
    if args.record:
        with HISTORY.open("a", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
