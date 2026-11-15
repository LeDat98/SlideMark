"""Design rubric (docs/DESIGN_RUBRIC.md): the YAML is complete, the catalogue is current, the formula matches
the worked examples of the method, and a judge run turns into a report."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
RUBRIC = ROOT / "bench" / "rubric"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"rubric_{name}", RUBRIC / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # dataclasses look the module up while the class is built
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


score = _load("score")
render = _load("render")


def _all_kpis():
    g = yaml.safe_load((RUBRIC / "general.yaml").read_text(encoding="utf-8"))
    t = yaml.safe_load((RUBRIC / "topics.yaml").read_text(encoding="utf-8"))
    out = [("general", k) for k in g["general"]] + [("deck", k) for k in g["deck"]]
    out += [(tp["id"], k) for tp in t["topics"] for k in tp["kpis"]]
    return g, t, out


def test_every_kpi_is_complete_with_five_distinct_levels():
    _g, t, kpis = _all_kpis()
    ids = [k["id"] for _, k in kpis]
    assert len(ids) == len(set(ids))
    for where, k in kpis:
        fields = (
            "id",
            "name",
            "question",
            "gate",
            "weight",
            "good_signals",
            "bad_signals",
            "levels",
            "sources",
        )
        for f in fields:
            assert k.get(f) not in (None, "", []), (where, k.get("id"), f)
        assert 1 <= k["weight"] <= 5, k["id"]
        assert sorted(k["levels"]) == [1, 2, 3, 4, 5], k["id"]
        assert len({str(v) for v in k["levels"].values()}) == 5, k["id"]  # five distinct descriptions
    for tp in t["topics"]:
        assert tp.get("recognise") and 4 <= len(tp["kpis"]) <= 8, tp["id"]
    assert [tp["id"] for tp in t["topics"] if tp.get("overlay")] == ["dense-ja-business"]


def test_the_catalogue_matches_the_yaml():
    assert render.main(["--check"]) == 0


def test_worked_example_1_chart_slide_and_its_gate_caps():
    rub = score.load_rubric(RUBRIC)
    general = {"G-01": 4, "G-02": 4, "G-03": 3, "G-04": 4, "G-05": 3, "G-06": 4, "G-07": 4, "G-08": 3}
    general |= {"G-09": 5, "G-10": 3, "G-11": 3, "G-12": 4, "G-13": 4, "G-14": None}  # G-14 N/A
    K = score.Kpi
    tk = {
        "T1": K("T1", "chart type", 5, False),
        "T2": K("T2", "takeaway", 5, False),
        "T3": K("T3", "labels", 4, False),
        "T4": K("T4", "chartjunk", 3, False),
        "T5": K("T5", "honest scale", 5, True),
        "T6": K("T6", "colour", 3, False),
    }
    topic = {"T1": 4, "T2": 2, "T3": 4, "T4": 3, "T5": 5, "T6": 4}
    r = score.slide_score(general, topic, rub, tk)
    assert r["general"] == pytest.approx(68.4, abs=0.05)
    assert r["topic"] == pytest.approx(67.0, abs=0.05)
    assert r["score"] == pytest.approx(67.8, abs=0.05) and r["cap"] is None and r["band"] == "Acceptable"
    assert score.slide_score(general | {"G-06": 2}, topic, rub, tk)["score"] == 59
    assert score.slide_score(general | {"G-06": 1}, topic, rub, tk)["score"] == 39


def test_worked_example_2_ten_slide_deck():
    rub = score.load_rubric(RUBRIC)
    slides = [72, 68, 39, 81, 74, 66, 78, 70, 85, 63]
    gates = [4, 4, 1, 4, 4, 4, 4, 4, 4, 4]
    d = score.deck_score(slides, gates, {"D-01": 4, "D-02": 3, "D-03": 3, "D-04": 2, "D-05": 4}, rub)
    assert d["slides"] == pytest.approx(66.2, abs=0.05)
    assert d["deck_kpis"] == pytest.approx(56.9, abs=0.05)
    assert d["score"] == pytest.approx(63.4, abs=0.05)
    assert d["cap"] == 84  # a slide with a failed gate: the deck cannot be Excellent (not binding here)


def _run(levels: dict[str, int], g12: int, d01: int) -> dict:
    kpis = [
        {"id": k, "level": v, "evidence": [{"sign": "+" if v >= 3 else "-", "text": f"{k} seen"}]}
        for k, v in levels.items()
    ]
    kpis.append({"id": "G-12", "level": g12, "evidence": [{"sign": "-" if g12 < 3 else "+", "text": "edge"}]})
    kpis.append({"id": "G-14", "na": True, "evidence": []})
    return {
        "deck": "demo",
        "judge": "test",
        "date": "2026-11-15",
        "slides": [{"slide": 1, "topic": "framing", "message": "m", "kpis": kpis}],
        "deck_kpis": [{"id": "D-01", "level": d01, "evidence": [{"sign": "+", "text": "story"}]}],
    }


def test_runs_become_a_report_with_medians_ranges_and_flags(tmp_path):
    rub = score.load_rubric(RUBRIC)
    t = yaml.safe_load((RUBRIC / "topics.yaml").read_text(encoding="utf-8"))
    frame = next(tp for tp in t["topics"] if tp["id"] == "framing")
    base = {k.id: 4 for k in rub.general.values() if k.id not in ("G-12", "G-14")}
    base |= {k["id"]: 4 for k in frame["kpis"]}
    runs = [_run(base, 4, 4), _run(base, 2, 4), _run(base, 4, 2)]
    res = score.score_runs(runs, rub)
    s = res["slides"][0]
    assert s["levels"]["G-12"] == 4 and "G-12" in s["unstable"]  # median 4, spread 2: unstable
    assert s["cap"] == 59 and "unstable" in s["cap_why"]  # an unstable gate is capped until a human looks
    md = score.report(res, rub)
    assert "# Design report: demo" in md and "| 1 | Framing" in md and "Unstable KPIs: G-12 (slide 1)" in md
    measured = {"slides": {"1": {"G-12": 1}}, "facts": {"1": "text cut at the right edge"}}
    m = score.score_runs(runs, rub, measured)
    # the measurement wins for a gate
    assert m["slides"][0]["score"] <= 39 and "text cut" in score.report(m, rub)
    paths = []
    for i, r in enumerate(runs):
        p = tmp_path / f"r{i}.json"
        p.write_text(json.dumps(r), encoding="utf-8")
        paths.append(str(p))
    out = tmp_path / "report.md"
    assert score.main([*paths, "--out", str(out)]) == 0
    assert out.read_text(encoding="utf-8").startswith("# Design")
