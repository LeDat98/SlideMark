"""A judging campaign: every run file of several decks -> one report per deck plus a cross-deck summary.

    python bench/rubric/campaign.py <folder> [--out-dir <dir>]

The folder holds judge runs named ``run<N>-<deck>.json`` (format: ``bench/rubric/score.py``). Writes
``<deck>.md`` for each deck and ``SUMMARY.md`` (deck scores and bands, the weakest KPIs across all slides, gate
failures and unstable KPIs) into ``--out-dir`` (default: the folder).
"""

# ruff: noqa: E501  (report lines are long f-strings)
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _score_module():
    spec = importlib.util.spec_from_file_location("rubric_score", HERE / "score.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def campaign(folder: Path, out_dir: Path | None = None) -> str:
    S = _score_module()
    rub = S.load_rubric(HERE)
    out_dir = out_dir or folder
    out_dir.mkdir(parents=True, exist_ok=True)
    runs: dict[str, list[dict]] = defaultdict(list)
    for p in sorted(folder.glob("run*-*.json")):
        m = re.fullmatch(r"run(\d+)-(.+)\.json", p.name)
        if m:
            runs[m.group(2)].append(json.loads(p.read_text(encoding="utf-8")))
    names = {**{k.id: k.name for k in rub.general.values()}, **{k.id: k.name for k in rub.deck.values()}}
    for t in rub.topics.values():
        names.update({k.id: k.name for k in t.values()})
    rows, kpi_levels, gate_fails, unstable = [], defaultdict(list), [], []
    for deck, rs in sorted(runs.items()):
        res = S.score_runs(rs, rub)
        (out_dir / f"{deck}.md").write_text(S.report(res, rub), encoding="utf-8")
        d = res["deck"]
        rows.append((deck, len(res["slides"]), len(rs), d, res))
        for s in res["slides"]:
            for kid, lv in s["levels"].items():
                if lv is not None:
                    kpi_levels[kid].append(lv)
            if s["cap"] is not None:
                gate_fails.append(f"{deck} slide {s['slide']}: capped at {s['cap']} ({s['cap_why']})")
            unstable += [f"{deck} slide {s['slide']} {k}" for k in s["unstable"]]
        for kid, lv in d["levels"].items():
            if lv is not None:
                kpi_levels[kid].append(lv)
    lines = [
        "# Rubric campaign summary",
        "",
        "Scores 0-100 (median over runs, range = min-max of the single-run scores). Method: docs/DESIGN_RUBRIC.md.",
        "",
        "| deck | slides | runs | deck score (range) | band | slides | bottom quartile | deck KPIs | cap |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for deck, n, r, d, _res in rows:
        lo, hi = d["range"]
        dk = "-" if d["deck_kpis"] is None else str(round(d["deck_kpis"]))
        cap = f"{d['cap']} ({d['cap_why']})" if d["cap"] is not None and d["raw"] > d["cap"] else "-"
        lines.append(
            f"| {deck} | {n} | {r} | {round(d['score'])} ({round(lo)}-{round(hi)}) | {S._band_label(d['score'], lo, hi)} "
            f"| {round(d['slides'])} | {round(d['bottom'])} | {dk} | {cap} |"
        )
    lines += [
        "",
        "## Weakest KPIs across all slides (mean level, number of slides scored)",
        "",
        "| KPI | name | mean level | slides | at level <= 2 |",
        "|---|---|---|---|---|",
    ]
    stats = sorted(
        ((statistics.fmean(v), k, len(v), sum(1 for x in v if x <= 2)) for k, v in kpi_levels.items() if v),
        key=lambda t: (t[0], -t[2]),
    )
    for mean, kid, n, low in stats[:15]:
        lines.append(f"| {kid} | {names.get(kid, kid)} | {mean:.2f} | {n} | {low} |")
    lines += ["", "## Gate caps", ""] + ([f"- {g}" for g in gate_fails] or ["- none"])
    lines += ["", "## Unstable KPIs (runs 2+ levels apart)", ""] + (
        [f"- {u}" for u in unstable] or ["- none"]
    )
    text = "\n".join(lines) + "\n"
    (out_dir / "SUMMARY.md").write_text(text, encoding="utf-8")
    return text


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("folder", type=Path)
    ap.add_argument("--out-dir", type=Path)
    a = ap.parse_args(argv)
    sys.stdout.write(campaign(a.folder, a.out_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
