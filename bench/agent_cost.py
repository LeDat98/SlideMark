"""Agent run cost from Claude Code subagent transcripts (AC1, spec in docs/AGENT_COST.md, Appendix B).

    python bench/agent_cost.py RUN.jsonl [...] [--arm skill-only] [--brief b01] [--folder DIR] [--record]
    python bench/agent_cost.py --report          # medians per arm and ratios vs the python-pptx arm

One model call = one unique ``requestId``. Per call the context is input + cache write + cache read (exact).
Output tokens (thinking included): the last transcript line of a request carries the final ``output_tokens``
in this harness (lines that also carry ``iterations``); when only the stream-start snapshot exists, the output
is reconstructed from context growth: ``ctx_(k+1) - ctx_k - 1.45 * tool_text_k - image_px_k / 750 - 29``.

Cost units (fresh-input-token equivalents): fresh + 1.25 * cache write + 0.10 * cache read + 5 * output.
Cost above common start = cost minus the input cost of the first call (system prompt + tools + brief), which
every arm pays the same.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HISTORY = ROOT / "agent_cost.jsonl"
W_WRITE, W_READ, W_OUT = 1.25, 0.10, 5.0
TOOL_FACTOR, IMG_DIV, CALL_OVERHEAD = 1.45, 750, 29


def _o200k(text: str) -> int:
    try:
        import tiktoken

        return len(tiktoken.get_encoding("o200k_base").encode(text))
    except Exception:  # tiktoken missing: ~4 chars per token
        return len(text) // 4


def _result_parts(content) -> tuple[str, int]:
    """Text and image pixels inside a tool_result content."""
    if isinstance(content, str):
        return content, 0
    text, px = [], 0
    for c in content or []:
        if c.get("type") == "text":
            text.append(c.get("text", ""))
        elif c.get("type") == "image":
            px += 1280 * 720  # the harness does not record the size; slide PNGs are 1280x720
    return "\n".join(text), px


def analyze(path: str | Path, folder: str | None = None) -> dict:
    """One transcript -> calls, tokens, cost and behaviour counts."""
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    calls: dict[str, dict] = {}
    order: list[str] = []
    tool_after: dict[str, list] = {}  # requestId -> tool results that came back after it
    last_req = None
    docs = builds = images = reads_png = 0
    outside: list[str] = []
    for r in rows:
        if r.get("type") == "assistant":
            m = r["message"]
            rid = r.get("requestId") or m.get("id")
            u = m.get("usage") or {}
            if rid not in calls:
                calls[rid] = {"usage": u, "final": False, "visible": [], "thinking": 0}
                order.append(rid)
                tool_after[rid] = []
            c = calls[rid]
            if "iterations" in u or u.get("output_tokens", 0) >= c["usage"].get("output_tokens", 0):
                c["usage"] = u
                c["final"] = c["final"] or "iterations" in u
            for part in m.get("content") or []:
                if part.get("type") == "text":
                    c["visible"].append(part.get("text", ""))
                elif part.get("type") == "tool_use":
                    inp = part.get("input") or {}
                    c["visible"].append(json.dumps(inp, ensure_ascii=False))
                    cmd = str(inp.get("command", ""))
                    if re.search(r"\bslidemark\s+docs\b", cmd):
                        docs += 1
                    if re.search(r"\bslidemark\s+build\b", cmd) or "build.py" in cmd:
                        builds += 1
                    fp = str(inp.get("file_path", ""))
                    if fp.lower().endswith(".png"):
                        reads_png += 1
                    if folder and fp and not fp.startswith(folder) and not fp.endswith("SKILL.md"):
                        outside.append(fp)
            last_req = rid
        elif r.get("type") == "user" and last_req:
            cont = r["message"].get("content")
            if isinstance(cont, list):
                for part in cont:
                    if part.get("type") == "tool_result":
                        text, px = _result_parts(part.get("content"))
                        images += px // (1280 * 720)
                        tool_after[last_req].append((text, px))
    ctx = []
    for rid in order:
        u = calls[rid]["usage"]
        ctx.append(
            u.get("input_tokens", 0)
            + u.get("cache_creation_input_tokens", 0)
            + u.get("cache_read_input_tokens", 0)
        )
    outs, thinking = [], 0
    for k, rid in enumerate(order):
        c = calls[rid]
        u = c["usage"]
        thinking += (u.get("output_tokens_details") or {}).get("thinking_tokens", 0)
        if c["final"]:
            outs.append(u.get("output_tokens", 0))
        elif k + 1 < len(order) and k > 0:
            tool_tok = sum(_o200k(t) for t, _ in tool_after[rid])
            px = sum(p for _, p in tool_after[rid])
            outs.append(
                max(0, round(ctx[k + 1] - ctx[k] - TOOL_FACTOR * tool_tok - px / IMG_DIV - CALL_OVERHEAD))
            )
        else:  # first call (harness adds ~5.2k between calls 1 and 2) or last call: visible content only
            outs.append(round(1.53 * _o200k("\n".join(c["visible"]))))
    fresh = sum(calls[r]["usage"].get("input_tokens", 0) for r in order)
    write = sum(calls[r]["usage"].get("cache_creation_input_tokens", 0) for r in order)
    read = sum(calls[r]["usage"].get("cache_read_input_tokens", 0) for r in order)
    out = sum(outs)
    cost = fresh + W_WRITE * write + W_READ * read + W_OUT * out
    u0 = calls[order[0]]["usage"] if order else {}
    start = (
        u0.get("input_tokens", 0)
        + W_WRITE * u0.get("cache_creation_input_tokens", 0)
        + W_READ * u0.get("cache_read_input_tokens", 0)
    )
    return {
        "transcript": str(path),
        "calls": len(order),
        "first_ctx": ctx[0] if ctx else 0,
        "last_ctx": ctx[-1] if ctx else 0,
        "output": out,
        "thinking": thinking,
        "cost": round(cost),
        "cost_above_start": round(cost - start),
        "images": images,
        "png_reads": reads_png,
        "docs_attempts": docs,
        "builds": builds,
        "outside_reads": outside,
    }


COLS = ["calls", "output", "thinking", "cost", "cost_above_start", "images", "docs_attempts", "builds"]


def _table(rows: list[dict]) -> None:
    head = ["arm", "brief", *COLS]
    print(" | ".join(head))
    for r in rows:
        print(" | ".join(str(r.get(k, "")) for k in head))


def report(rows: list[dict]) -> None:
    """Median per arm, and per-brief ratios of the SlideMark arms to the python-pptx arm."""
    arms: dict[str, list[dict]] = {}
    for r in rows:
        arms.setdefault(r.get("arm", "?"), []).append(r)
    print("arm | runs | " + " | ".join(f"median {c}" for c in COLS))
    for arm, rs in sorted(arms.items()):
        meds = [statistics.median(r[c] for r in rs) for c in COLS]
        print(f"{arm} | {len(rs)} | " + " | ".join(f"{m:g}" for m in meds))
    base = {}
    for r in arms.get("python-pptx", []):
        base.setdefault(r["brief"], []).append(r)
    for arm, rs in sorted(arms.items()):
        if arm == "python-pptx" or not base:
            continue
        ratios = {"cost_above_start": [], "output": [], "calls": []}
        for r in rs:
            b = base.get(r.get("brief"))
            if not b:
                continue
            for k in ratios:
                den = statistics.median(x[k] for x in b)
                if den:
                    ratios[k].append(r[k] / den)
        if ratios["calls"]:
            print(
                f"{arm} vs python-pptx (median per run): "
                + ", ".join(f"{k} {statistics.median(v):.0%}" for k, v in ratios.items() if v)
            )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("transcripts", nargs="*")
    ap.add_argument("--arm", default="skill-only", help="skill-only | skill-open | python-pptx")
    ap.add_argument("--brief", help="brief id (default: the transcript's parent folder name)")
    ap.add_argument("--folder", help="the run folder: reads outside it (except SKILL.md) are listed")
    ap.add_argument("--accepted", choices=["yes", "no"], help="acceptance result to store with the row")
    ap.add_argument("--note", default="")
    ap.add_argument("--record", action="store_true", help=f"append rows to {HISTORY.name}")
    ap.add_argument("--report", action="store_true", help=f"summarise {HISTORY.name}")
    args = ap.parse_args(argv)
    if args.report:
        rows = [json.loads(x) for x in HISTORY.read_text(encoding="utf-8").splitlines() if x.strip()]
        report([r for r in rows if not r.get("note", "").startswith("INVALID")])
        return 0
    if not args.transcripts:
        ap.error("give transcript paths or --report")
    rows = []
    for t in args.transcripts:
        r = analyze(t, args.folder)
        r.update(arm=args.arm, brief=args.brief or Path(t).parent.name, note=args.note)
        if args.accepted:
            r["accepted"] = args.accepted == "yes"
        rows.append(r)
    _table(rows)
    for r in rows:
        if r["outside_reads"]:
            print(f"warning: {r['brief']} read outside its folder: {r['outside_reads'][:3]}", file=sys.stderr)
    if args.record:
        import datetime

        stamp = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
        with HISTORY.open("a", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps({"date": stamp, **r}, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
