"""Render the rubric YAML (general.yaml, topics.yaml) as the readable KPI catalogue docs/DESIGN_RUBRIC_KPIS.md.

python bench/rubric/render.py            # writes docs/DESIGN_RUBRIC_KPIS.md
python bench/rubric/render.py --check    # exit 1 if the committed file is stale (used by the tests)
"""

# ruff: noqa: E501
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
OUT = HERE.parent.parent / "docs" / "DESIGN_RUBRIC_KPIS.md"


def _cell(x: object) -> str:
    return str(x).replace("|", "\\|").replace("\n", " ").strip()


def _kpi(k: dict) -> list[str]:
    gate = "**gate**" if k.get("gate") else (f"soft gate, cap {k['cap']}" if k.get("cap") else "-")
    out = [
        f"#### {k['id']} {k['name']}  (weight {k['weight']}, {gate})",
        "",
        f"{_cell(k['question'])}",
        "",
        "| Level | What the grader sees |",
        "|---|---|",
    ]
    out += [f"| {lv} | {_cell(k['levels'][lv])} |" for lv in (1, 2, 3, 4, 5)]
    out += ["", "Good signals: " + "; ".join(_cell(x) for x in k.get("good_signals") or [])]
    out += ["", "Bad signals: " + "; ".join(_cell(x) for x in k.get("bad_signals") or [])]
    if k.get("checks"):
        out += ["", "Checks: " + "; ".join(_cell(x) for x in k["checks"])]
    if k.get("sources"):
        out += ["", "Sources: " + "; ".join(_cell(x) for x in k["sources"])]
    return out + [""]


def _gate_cell(k: dict) -> str:
    return "yes" if k.get("gate") else (f"soft ({k['cap']})" if k.get("cap") else "")


def _summary(rows: list[dict]) -> list[str]:
    out = ["| id | name | weight | gate |", "|---|---|---|---|"]
    out += [f"| {k['id']} | {_cell(k['name'])} | {k['weight']} | {_gate_cell(k)} |" for k in rows]
    return out + [""]


def render(folder: Path = HERE) -> str:
    g = yaml.safe_load((folder / "general.yaml").read_text(encoding="utf-8"))
    t = yaml.safe_load((folder / "topics.yaml").read_text(encoding="utf-8"))
    lines = [
        "# Design rubric: KPI catalogue",
        "",
        "Generated from `bench/rubric/general.yaml` and `bench/rubric/topics.yaml` by `bench/rubric/render.py`; edit the",
        "YAML, then re-run the script. Method, formula and protocol: `docs/DESIGN_RUBRIC.md`.",
        "",
        "Every KPI is scored 1 to 5. Levels 1-2 describe the bad signs, 4-5 the good ones, 3 is acceptable. Weight 1 (nice",
        "to have) to 5 (critical). A **gate** KPI below level 3 caps the slide (level 2: at most 59, level 1: at most 39);",
        "a **soft gate** (`cap:`) at level 2 caps it at its cap, at level 1 at 49 (G-05 dead space: 59 / 49).",
        "",
        "## General KPIs (every slide)",
        "",
        *_summary(g["general"]),
    ]
    for k in g["general"]:
        lines += _kpi(k)
    lines += ["## Deck KPIs (once per deck)", "", *_summary(g["deck"])]
    for k in g["deck"]:
        lines += _kpi(k)
    lines += [
        "## Topics",
        "",
        "| id | name | overlay | KPIs | gates | recognise |",
        "|---|---|---|---|---|---|",
    ]
    for tp in t["topics"]:
        gates = sum(1 for k in tp["kpis"] if k.get("gate"))
        rec = "; ".join(_cell(x) for x in (tp.get("recognise") or [])[:3])
        lines.append(
            f"| {tp['id']} | {_cell(tp['name'])} | {'yes' if tp.get('overlay') else ''} | {len(tp['kpis'])} | {gates} | {rec} |"
        )
    lines.append("")
    for tp in t["topics"]:
        lines += [f"## Topic: {tp['name']} (`{tp['id']}`)", "", _cell(tp.get("covers", "")), ""]
        if tp.get("frequency"):
            lines += [f"Frequency: {_cell(tp['frequency'])}", ""]
        lines += _summary(tp["kpis"])
        for k in tp["kpis"]:
            lines += _kpi(k)
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    text = render()
    if a.check:
        ok = OUT.exists() and OUT.read_text(encoding="utf-8") == text
        if not ok:
            sys.stderr.write("docs/DESIGN_RUBRIC_KPIS.md is stale: run python bench/rubric/render.py\n")
        return 0 if ok else 1
    OUT.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
