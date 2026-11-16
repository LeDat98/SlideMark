"""Design rubric scorer: judge runs (JSON) -> slide / deck scores, bands, caps and a Markdown report.

Method: docs/DESIGN_RUBRIC.md (sections "Scoring" and "Report"). The judge only gives levels and evidence; every number
here is computed, never written by the judge.

Usage:
    python bench/rubric/score.py run1.json run2.json run3.json [--measured measured.json] [--rubric bench/rubric]
                                 [--out report.md] [--json scores.json]

A run file (one judge run over one deck):
    {"deck": "t5 editorial", "judge": "opus", "date": "2026-11-15",
     "slides": [{"slide": 1, "topic": "framing", "message": "...",
                 "kpis": [{"id": "G-01", "level": 4, "na": false,
                           "evidence": [{"sign": "+", "text": "title states the takeaway"}]}]}],
     "deck_kpis": [{"id": "D-01", "level": 4, "evidence": [...]}]}

A measured file (facts read from the .pptx, written by bench/rubric/measure.py; a failure below level 3 overrides the
judge for gate KPIs, a pass only lifts a judge level below 3):
    {"slides": {"3": {"G-06": 2, "G-12": 1}}, "facts": {"3": "min font 8.5pt; text cut at the right edge"}}
"""

# ruff: noqa: E501  (report lines are long f-strings)
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

HERE = Path(__file__).resolve().parent

GENERAL_SHARE = 0.6  # a: Slide = 100 * (a * S_general + (1 - a) * S_topic)
DECK_SLIDE_SHARE = 0.7  # Deck = 0.7 * slides + 0.3 * deck KPIs
SLIDE_MEAN_SHARE = 0.75  # slides = 0.75 * mean + 0.25 * bottom-quartile mean
CAP_GATE_2 = 59  # a gate KPI at level 2 caps the slide (cannot reach Good)
CAP_GATE_1 = 39  # a gate KPI at level 1 caps the slide (always Fail)
DECK_CAP_ANY_GATE = 84  # any slide with a failed gate: the deck cannot be Excellent
DECK_CAP_GATE1_SHARE, DECK_CAP_GATE1 = 0.2, 49  # >= 20% of slides with a gate at 1: Fail
DECK_CAP_FAIL_SHARE, DECK_CAP_FAIL = 0.4, 59  # >= 40% of slides in Fail: at most Acceptable
BANDS = ((85, "Excellent"), (70, "Good"), (50, "Acceptable"), (0, "Fail"))
UNSTABLE_SPREAD = 2  # levels between runs that flag a KPI as unstable


# --------------------------------------------------------------------------- rubric


@dataclass
class Kpi:
    id: str
    name: str
    weight: float
    gate: bool


@dataclass
class Rubric:
    general: dict[str, Kpi]
    deck: dict[str, Kpi]
    topics: dict[str, dict[str, Kpi]]
    topic_names: dict[str, str] = field(default_factory=dict)


def _kpis(items: list[dict[str, Any]]) -> dict[str, Kpi]:
    return {k["id"]: Kpi(k["id"], k["name"], float(k["weight"]), bool(k["gate"])) for k in items or []}


def load_rubric(folder: Path = HERE) -> Rubric:
    g = yaml.safe_load((folder / "general.yaml").read_text(encoding="utf-8"))
    t = yaml.safe_load((folder / "topics.yaml").read_text(encoding="utf-8"))
    topics = {tp["id"]: _kpis(tp["kpis"]) for tp in t["topics"]}
    names = {tp["id"]: tp["name"] for tp in t["topics"]}
    return Rubric(_kpis(g["general"]), _kpis(g["deck"]), topics, names)


# --------------------------------------------------------------------------- arithmetic


def norm(s: float) -> float:
    """Level 1..5 -> 0..1."""
    return (s - 1) / 4


def set_score(levels: dict[str, float | None], kpis: dict[str, Kpi]) -> float | None:
    """sum(w * n) / sum(w) over the applicable KPIs (None = N/A, removed from both sums); None if nothing applies."""
    num = den = 0.0
    for kid, k in kpis.items():
        s = levels.get(kid)
        if s is None:
            continue
        num += k.weight * norm(s)
        den += k.weight
    return num / den if den else None


def band(score: float) -> str:
    return next(name for floor, name in BANDS if score >= floor)


def topic_kpis(rub: Rubric, topics: list[str]) -> dict[str, Kpi]:
    """The topic set of a slide: its primary topic plus any overlay topic (``dense-ja-business``)."""
    out: dict[str, Kpi] = {}
    for t in topics:
        out.update(rub.topics.get(t, {}))
    return out


def topic_list(raw: Any) -> list[str]:
    """``"data-chart"``, ``"data-chart+dense-ja-business"`` or a list -> topic ids."""
    if not raw:
        return []
    items = raw if isinstance(raw, list) else str(raw).split("+")
    return [str(t).strip() for t in items if str(t).strip()]


def slide_score(
    general: dict[str, float | None],
    topic: dict[str, float | None] | None,
    rub: Rubric,
    tk: dict[str, Kpi],
    unstable_gates: set[str] = frozenset(),  # type: ignore[assignment]
) -> dict[str, Any]:
    """One slide from its KPI levels: set scores, raw, gate cap, final score and band."""
    sg = set_score(general, rub.general)
    st = set_score(topic or {}, tk) if tk else None
    if sg is None:
        raw = 0.0
    elif st is None:
        raw = 100 * sg
    else:
        raw = 100 * (GENERAL_SHARE * sg + (1 - GENERAL_SHARE) * st)
    gates = {
        kid: s for kid, s in {**general, **(topic or {})}.items() if s is not None and _is_gate(kid, rub, tk)
    }
    g_min = min(gates.values()) if gates else None
    cap, why = None, ""
    if g_min is not None and g_min < 2:
        cap, why = CAP_GATE_1, f"{min(gates, key=gates.get)}={_fmt(g_min)}"  # type: ignore[arg-type]
    elif g_min is not None and g_min < 3:
        cap, why = CAP_GATE_2, f"{min(gates, key=gates.get)}={_fmt(g_min)}"  # type: ignore[arg-type]
    elif unstable_gates:  # a gate whose runs disagree by 2+ levels is capped as failed until a human looks
        cap, why = CAP_GATE_2, "unstable " + ",".join(sorted(unstable_gates))
    score = min(raw, cap) if cap is not None else raw
    return {
        "general": None if sg is None else 100 * sg,
        "topic": None if st is None else 100 * st,
        "raw": raw,
        "cap": cap,
        "cap_why": why,
        "g_min": g_min,
        "score": score,
        "band": band(score),
    }


def _is_gate(kid: str, rub: Rubric, topic_kpis: dict[str, Kpi]) -> bool:
    k = rub.general.get(kid) or topic_kpis.get(kid)
    return bool(k and k.gate)


def deck_score(
    slide_scores: list[float], gate_mins: list[float | None], deck_levels: dict, rub: Rubric
) -> dict:
    """Deck = 0.7 * (0.75 * mean + 0.25 * bottom-quartile mean) + 0.3 * deck KPIs, then the deck caps."""
    if not slide_scores:
        return {
            "slides": 0.0,
            "bottom": 0.0,
            "deck_kpis": None,
            "raw": 0.0,
            "cap": None,
            "cap_why": "",
            "score": 0.0,
        }
    mean = statistics.fmean(slide_scores)
    low = sorted(slide_scores)[: max(1, math.ceil(len(slide_scores) / 4))]
    bottom = statistics.fmean(low)
    slides = SLIDE_MEAN_SHARE * mean + (1 - SLIDE_MEAN_SHARE) * bottom
    d = set_score(deck_levels, rub.deck)
    raw = slides if d is None else DECK_SLIDE_SHARE * slides + (1 - DECK_SLIDE_SHARE) * 100 * d
    k = len(slide_scores)
    caps: list[tuple[float, str]] = []
    if sum(1 for g in gate_mins if g is not None and g < 2) / k >= DECK_CAP_GATE1_SHARE:
        caps.append((DECK_CAP_GATE1, "20%+ of slides have a gate at level 1"))
    if sum(1 for s in slide_scores if s < 50) / k >= DECK_CAP_FAIL_SHARE:
        caps.append((DECK_CAP_FAIL, "40%+ of slides are in Fail"))
    if any(g is not None and g < 3 for g in gate_mins):
        caps.append((DECK_CAP_ANY_GATE, "a slide has a failed gate"))
    cap, why = min(caps) if caps else (None, "")
    score = min(raw, cap) if cap is not None else raw
    return {
        "slides": slides,
        "mean": mean,
        "bottom": bottom,
        "deck_kpis": None if d is None else 100 * d,
        "raw": raw,
        "cap": cap,
        "cap_why": why,
        "score": score,
    }


# --------------------------------------------------------------------------- runs -> medians


def _levels(items: list[dict]) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    for it in items or []:
        if it.get("na"):
            out[it["id"]] = None
        elif it.get("level") is not None:
            out[it["id"]] = float(it["level"])
    return out


def _median_levels(per_run: list[dict[str, float | None]]) -> tuple[dict[str, float | None], dict[str, list]]:
    ids = {k for r in per_run for k in r}
    med: dict[str, float | None] = {}
    vals: dict[str, list] = {}
    for kid in ids:
        xs = [r[kid] for r in per_run if r.get(kid) is not None]
        vals[kid] = xs
        med[kid] = statistics.median(xs) if xs else None
    return med, vals


def measured_level(judged: float | None, measured: float) -> float:
    """The level a gate KPI takes once the .pptx was measured: a measured failure (below 3) always wins; a measured
    pass (3 or more) only lifts a judge level below 3 (it proves the floor is met, not that the design is strong)."""
    if measured < 3 or judged is None or judged < 3:
        return measured
    return judged


def score_runs(runs: list[dict], rub: Rubric, measured: dict | None = None) -> dict:
    """All runs of one deck -> per slide and per deck results with run ranges, flags and evidence."""
    measured = measured or {}
    over = {str(k): v for k, v in (measured.get("slides") or {}).items()}
    by_slide: dict[int, list[dict]] = {}
    for run in runs:
        for sl in run.get("slides", []):
            by_slide.setdefault(int(sl["slide"]), []).append(sl)
    slides_out = []
    for n in sorted(by_slide):
        reps = by_slide[n]
        named = [tuple(topic_list(r.get("topic"))) for r in reps]
        topic_ids = [t for t in statistics.mode(named) if t in rub.topics] if named else []
        topic_id = "+".join(topic_ids) or None
        tk = topic_kpis(rub, topic_ids)
        per_run = [_levels(r.get("kpis", [])) for r in reps]
        for lv in per_run:  # measured facts win for gate KPIs
            for kid, s in (over.get(str(n)) or {}).items():
                if _is_gate(kid, rub, tk):
                    lv[kid] = measured_level(lv.get(kid), float(s))
        med, vals = _median_levels(per_run)
        for kid, s in (over.get(str(n)) or {}).items():
            if _is_gate(kid, rub, tk):
                med[kid] = measured_level(med.get(kid), float(s))
                vals[kid] = [med[kid]]
        unstable = {k for k, xs in vals.items() if xs and max(xs) - min(xs) >= UNSTABLE_SPREAD}
        unstable_gates = {k for k in unstable if _is_gate(k, rub, tk) and (med.get(k) or 0) >= 3}
        gen = {k: v for k, v in med.items() if k in rub.general}
        top = {k: v for k, v in med.items() if k in tk}
        res = slide_score(gen, top, rub, tk, unstable_gates)
        run_scores = []
        for lv in per_run:
            r = slide_score(
                {k: v for k, v in lv.items() if k in rub.general}, {k: v for k, v in lv.items() if k in tk}, rub, tk
            )  # fmt: skip
            run_scores.append(r["score"])
        missing = sorted(k for k in [*rub.general, *tk] if k not in med and k != "G-14")
        losses = sorted(
            (
                ((rub.general.get(k) or tk[k]).weight * (1 - norm(s)), k)
                for k, s in med.items()
                if s is not None and (k in rub.general or k in tk) and s < 5
            ),
            reverse=True,
        )
        slides_out.append(
            {
                "slide": n,
                "topic_id": topic_id if tk else None,
                "topic_given": "+".join(str(t) for t in (named[0] if named else ())),
                "message": reps[0].get("message", ""),
                "levels": med,
                "runs": vals,
                "unstable": sorted(unstable),
                "missing": missing,
                "losses": losses,
                "evidence": _evidence(reps, med),
                "range": (min(run_scores), max(run_scores)) if run_scores else (res["score"], res["score"]),
                **res,
            }
        )
    deck_runs = [_levels(r.get("deck_kpis", [])) for r in runs]
    dmed, dvals = _median_levels(deck_runs)
    deck = deck_score([s["score"] for s in slides_out], [s["g_min"] for s in slides_out], dmed, rub)
    deck_range = []
    for i, run in enumerate(runs):  # the deck score of each run alone, for the range
        one = score_runs([run], rub, measured)["deck"]["score"] if len(runs) > 1 else None
        if one is not None:
            deck_range.append(one)
        del i
    deck["range"] = (min(deck_range), max(deck_range)) if deck_range else (deck["score"], deck["score"])
    deck["band"] = band(deck["score"])
    deck["levels"], deck["runs"] = dmed, dvals
    deck["evidence"] = _evidence([{"kpis": r.get("deck_kpis", [])} for r in runs], dmed)
    deck["unstable"] = sorted(k for k, xs in dvals.items() if xs and max(xs) - min(xs) >= UNSTABLE_SPREAD)
    meta = runs[0] if runs else {}
    return {
        "deck_name": meta.get("deck", "deck"),
        "judge": meta.get("judge", "?"),
        "date": meta.get("date", ""),
        "runs": len(runs),
        "slides": slides_out,
        "deck": deck,
        "facts": measured.get("facts") or {},
    }


def _evidence(reps: list[dict], med: dict) -> dict[str, list[dict]]:
    """Evidence per KPI from the run whose level is closest to the median (the first such run)."""
    out: dict[str, list[dict]] = {}
    for kid, m in med.items():
        best = None
        for r in reps:
            for it in r.get("kpis", []):
                if it.get("id") != kid:
                    continue
                lv = it.get("level")
                d = abs((lv or 0) - (m or 0)) if lv is not None and m is not None else 9
                if best is None or d < best[0]:
                    best = (d, it.get("evidence") or [])
        out[kid] = best[1] if best else []
    return out


# --------------------------------------------------------------------------- report


def _fmt(x: float | None) -> str:
    if x is None:
        return "N/A"
    return str(int(x)) if float(x).is_integer() else f"{x:.1f}"


def _band_label(score: float, lo: float, hi: float) -> str:
    b = band(score)
    lo_b, hi_b = band(lo), band(hi)
    if lo_b != hi_b:
        return f"{lo_b} / {hi_b} (borderline)"
    return b


def report(res: dict, rub: Rubric) -> str:
    d = res["deck"]
    lo, hi = d["range"]
    gated = [s for s in res["slides"] if s["cap"] is not None]
    lines = [
        f"# Design report: {res['deck_name']}  (rubric v1, judge {res['judge']}, R={res['runs']} runs, {res['date']})",
        "",
        "## Summary",
        f"Deck **{round(d['score'])}** ({round(lo)}-{round(hi)})  {_band_label(d['score'], lo, hi)}  ·  "
        f"Slides {round(d['slides'])} (bottom quartile {round(d['bottom'])})  ·  "
        f"Deck KPIs {_fmt(None if d['deck_kpis'] is None else round(d['deck_kpis']))}"
        + (
            f"  ·  deck cap {d['cap']} ({d['cap_why']})"
            if d["cap"] is not None and d["raw"] > d["cap"]
            else ""
        ),
        "Gates: "
        + (
            "; ".join(f"slide {s['slide']} capped at {s['cap']} ({s['cap_why']})" for s in gated)
            if gated
            else "all pass"
        )
        + ". Unstable KPIs: "
        + (", ".join(f"{k} (slide {s['slide']})" for s in res["slides"] for k in s["unstable"]) or "none")
        + (f", deck {', '.join(d['unstable'])}" if d["unstable"] else "")
        + ".",
        "",
        "## Deck KPIs",
        "| id | name | w | s (runs) | evidence (+/-) |",
        "|---|---|---|---|---|",
    ]
    for kid, k in rub.deck.items():
        ev = "; ".join(f"{e.get('sign', '')} {e.get('text', '')}" for e in d["evidence"].get(kid, []))
        lines.append(
            f"| {kid} | {k.name} | {_fmt(k.weight)} | {_fmt(d['levels'].get(kid))} {_runs(d['runs'], kid)} | {ev} |"
        )
    lines += [
        "",
        "## Slides",
        "| # | topic | general | topic | raw | cap | score (range) | band | weakest KPIs (loss) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for s in res["slides"]:
        weak = ", ".join(f"{k} ({w:.1f})" for w, k in s["losses"][:3])
        tname = " + ".join(rub.topic_names.get(t, t) for t in topic_list(s["topic_id"])) or (
            (s["topic_given"] or "") + " (no-topic)"
        )
        lines.append(
            f"| {s['slide']} | {tname} | {_fmt(_r(s['general']))} | {_fmt(_r(s['topic']))} | {round(s['raw'])} | "
            f"{(str(s['cap']) + ' (' + s['cap_why'] + ')') if s['cap'] is not None else '-'} | "
            f"{round(s['score'])} ({round(s['range'][0])}-{round(s['range'][1])}) | "
            f"{_band_label(s['score'], *s['range'])} | {weak} |"
        )
    lines += ["", "## Top fixes (gates first, then by weighted loss)"]
    fixes = []
    for s in res["slides"]:
        tk = topic_kpis(rub, topic_list(s["topic_id"]))
        for w, kid in s["losses"]:
            k = rub.general.get(kid) or tk.get(kid)
            lv = s["levels"].get(kid)
            gate_fail = bool(k and k.gate and lv is not None and lv < 3)
            neg = next((e.get("text", "") for e in s["evidence"].get(kid, []) if e.get("sign") == "-"), "")
            fixes.append((0 if gate_fail else 1, -w, s["slide"], kid, k.name if k else kid, lv, neg))
    for i, (_g, w, n, kid, name, lv, neg) in enumerate(sorted(fixes)[:5], 1):
        lines.append(
            f"{i}. Slide {n}, {kid} {name} (level {_fmt(lv)}, loss {-w:.1f}): {neg or 'see evidence'}"
        )
    lines += ["", "## Evidence lines", "slide | KPI | s (runs) | sign | what is seen"]
    problems = []
    for s in res["slides"]:
        for kid in sorted(s["levels"]):
            lv = s["levels"][kid]
            ev = s["evidence"].get(kid, [])
            for e in ev or [{"sign": "?", "text": "(no evidence given)"}]:
                lines.append(
                    f"S{s['slide']} | {kid} | {_fmt(lv)} {_runs(s['runs'], kid)} | {e.get('sign', '?')} | {e.get('text', '')}"
                )
            signs = {e.get("sign") for e in ev}
            if lv is not None and ((lv >= 4 and "+" not in signs) or (lv <= 2 and "-" not in signs)):
                problems.append(f"S{s['slide']} {kid}: level {_fmt(lv)} without a matching evidence sign")
        if s["missing"]:
            problems.append(f"S{s['slide']}: no score for {', '.join(s['missing'])}")
    if res["facts"]:
        lines += ["", "## Measured facts"] + [f"- slide {k}: {v}" for k, v in sorted(res["facts"].items())]
    if problems:
        lines += ["", "## Judge output problems (fix the run or re-run these KPIs)"] + [
            f"- {p}" for p in problems
        ]
    return "\n".join(lines) + "\n"


def _r(x: float | None) -> float | None:
    return None if x is None else round(x)


def _runs(vals: dict, kid: str) -> str:
    xs = vals.get(kid) or []
    return f"({','.join(_fmt(x) for x in xs)})" if len(xs) > 1 else ""


# --------------------------------------------------------------------------- cli


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("runs", nargs="+", type=Path, help="judge run JSON files of one deck")
    ap.add_argument("--rubric", type=Path, default=HERE)
    ap.add_argument("--measured", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--json", type=Path)
    a = ap.parse_args(argv)
    rub = load_rubric(a.rubric)
    runs = [json.loads(p.read_text(encoding="utf-8")) for p in a.runs]
    measured = json.loads(a.measured.read_text(encoding="utf-8")) if a.measured else None
    res = score_runs(runs, rub, measured)
    md = report(res, rub)
    if a.out:
        a.out.write_text(md, encoding="utf-8")
    else:
        sys.stdout.write(md)
    if a.json:
        a.json.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
