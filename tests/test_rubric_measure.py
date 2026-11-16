"""bench/rubric/measure.py: facts of a .pptx for the gate KPIs (G-06 floors, G-09 contrast, G-12 defects),
the score.py rule that a measured pass only lifts a judge level, the campaign hook, and the editorial fixes
(chart series >= 3:1 on the paper, the `chart_series_contrast` lint)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_AUTO_SIZE
from pptx.util import Inches, Pt

from slidemark import build
from slidemark.contrast import ratio

ROOT = Path(__file__).resolve().parent.parent
RUBRIC = ROOT / "bench" / "rubric"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"rubric_{name}", RUBRIC / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


M = _load("measure")
S = _load("score")
CAMP = _load("campaign")


def _deck(tmp_path: Path, *slides: list[dict], bg: str = "FFFFFF") -> Path:
    """One text box per dict: ``text``, ``size`` (pt), ``color`` (hex), optional ``name`` and ``box``."""
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    for boxes in slides:
        s = prs.slides.add_slide(prs.slide_layouts[6])
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = RGBColor.from_string(bg)
        for i, b in enumerate(boxes):
            x, y, w, h = b.get("box", (0.8, 0.6 + i * 1.2, 11.5, 0.9))
            tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
            tb.name = b.get("name", f"Box {i}")
            tb.text_frame.word_wrap = True
            tb.text_frame.auto_size = MSO_AUTO_SIZE.NONE
            r = tb.text_frame.paragraphs[0].add_run()
            r.text = b["text"]
            r.font.size = Pt(b.get("size", 18))
            r.font.color.rgb = RGBColor.from_string(b.get("color", "2D3142"))
    out = tmp_path / "d.pptx"
    prs.save(out)
    return out


def test_clean_slide_passes(tmp_path):
    res = M.measure_deck(_deck(tmp_path, [{"text": "Orders grew all year", "size": 18}]))
    assert res["slides"]["1"] == {"G-06": 3, "G-09": 3}
    assert "min body 18 pt (floor 14)" in res["facts"]["1"] and "min text contrast" in res["facts"]["1"]


def test_small_body_fails_g06(tmp_path):
    bad = _deck(tmp_path, [{"text": "A paragraph of running body text in nine points", "size": 9}])
    res = M.measure_deck(bad)
    assert res["slides"]["1"]["G-06"] == 1  # under 12 pt: a clear failure
    assert "min body 9 pt (floor 14)" in res["facts"]["1"]
    mid = _deck(tmp_path, [{"text": "Body text at thirteen points, a hair under the floor", "size": 13}])
    assert M.measure_deck(mid)["slides"]["1"]["G-06"] == 2  # borderline
    # a dense Japanese deck has a 10 pt floor
    ja = _deck(tmp_path, [{"text": "密度の高い日本語スライドの本文は十ポイント", "size": 10.5}])
    assert M.measure_deck(ja, dense_ja=True)["slides"]["1"]["G-06"] == 3
    assert M.measure_deck(ja)["slides"]["1"]["G-06"] == 1
    tiny_ja = _deck(tmp_path, [{"text": "密度の高い日本語スライドの本文は九ポイント", "size": 9}])
    assert M.measure_deck(tiny_ja, dense_ja=True)["slides"]["1"]["G-06"] == 1


def test_label_and_footnote_floors(tmp_path):
    ok = _deck(
        tmp_path,
        [
            {"text": "Source: internal", "size": 8, "name": "Footnote"},
            {"text": "A", "size": 8.5, "name": "Axis label"},
        ],
    )
    assert M.measure_deck(ok)["slides"]["1"]["G-06"] == 3
    low = _deck(tmp_path, [{"text": "Source: internal", "size": 6, "name": "Footnote"}])
    assert M.measure_deck(low)["slides"]["1"]["G-06"] == 1


def test_pale_text_fails_g09(tmp_path):
    pale = _deck(tmp_path, [{"text": "Faint grey sentence", "size": 18, "color": "C8C8C8"}])
    assert M.measure_deck(pale)["slides"]["1"]["G-09"] == 1  # about 1.7:1
    mid = _deck(tmp_path, [{"text": "Mid grey sentence", "size": 16, "color": "8A8A8A"}])
    res = M.measure_deck(mid)
    assert res["slides"]["1"]["G-09"] == 2  # 3.5:1 on white, under 4.5:1
    assert "min text contrast 3.5:1" in res["facts"]["1"]
    large = _deck(tmp_path, [{"text": "Large mid grey", "size": 24, "color": "8A8A8A"}])
    assert M.measure_deck(large)["slides"]["1"]["G-09"] == 3  # large text needs 3:1
    dark = _deck(tmp_path, [{"text": "Light text on dark paper", "size": 18, "color": "EEEEEE"}], bg="2D3142")
    assert M.measure_deck(dark)["slides"]["1"]["G-09"] == 3  # the slide background counts, not white


def test_text_over_a_shape_uses_that_fill(tmp_path):
    prs = Presentation()
    s = prs.slides.add_slide(prs.slide_layouts[6])
    card = s.shapes.add_shape(1, Inches(1), Inches(1), Inches(4), Inches(1.5))
    card.name = "Card"
    card.fill.solid()
    card.fill.fore_color.rgb = RGBColor.from_string("1F2937")
    card.line.fill.background()
    tf = card.text_frame
    r = tf.paragraphs[0].add_run()
    r.text = "Dark ink on a dark card"
    r.font.size = Pt(18)
    r.font.color.rgb = RGBColor.from_string("2D3142")  # fine on white, unreadable on the card
    out = tmp_path / "c.pptx"
    prs.save(out)
    assert M.measure_deck(out)["slides"]["1"]["G-09"] == 1


def test_overflow_and_off_slide_are_g12_defects(tmp_path):
    long = "A very long sentence that cannot fit into a tiny box. " * 6
    over = _deck(tmp_path, [{"text": long, "size": 18, "box": (1, 1, 2.5, 0.5)}])
    assert M.measure_deck(over)["slides"]["1"]["G-12"] == 1
    assert "overflows" in M.measure_deck(over)["facts"]["1"]
    off = _deck(tmp_path, [{"text": "Hanging off the right edge", "size": 18, "box": (12.5, 1, 3, 0.8)}])
    assert M.measure_deck(off)["slides"]["1"]["G-12"] == 1
    ok = _deck(tmp_path, [{"text": "Fits", "size": 18}])
    assert "G-12" not in M.measure_deck(ok)["slides"]["1"]  # no defect measured: nothing is claimed
    a = {"text": "Overlapping A", "size": 18, "box": (1, 1, 4, 1)}
    b = {"text": "Overlapping B", "size": 18, "box": (2, 1.2, 4, 1)}
    assert M.measure_deck(_deck(tmp_path, [a, b]))["slides"]["1"]["G-12"] == 1


def test_measured_pass_only_lifts_a_low_judge_level():
    assert S.measured_level(2, 3) == 3  # the judge was too hard: the floor is met
    assert S.measured_level(4, 3) == 4  # the pass never lowers a stronger judge level
    assert S.measured_level(4, 2) == 2  # a measured failure wins
    assert S.measured_level(None, 3) == 3
    assert S.measured_level(3, 1) == 1


def test_cli_writes_the_score_format(tmp_path):
    pp = _deck(tmp_path, [{"text": "Hello", "size": 18}])
    out = tmp_path / "measured-x.json"
    assert M.main([str(pp), "--deck", "x", "-o", str(out)]) == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert set(data) == {"slides", "facts"} and data["slides"]["1"]["G-06"] == 3


def test_campaign_measures_a_deck_with_a_pptx_and_no_measured_file(tmp_path):
    pp = _deck(tmp_path, [{"text": "A paragraph of running body text in nine points", "size": 9}])
    (tmp_path / "demo.pptx").write_bytes(pp.read_bytes())
    run = {
        "deck": "demo",
        "slides": [
            {
                "slide": 1,
                "topic": "framing",
                "message": "m",
                "kpis": [{"id": "G-06", "level": 4, "evidence": []}],
            }
        ],
    }
    (tmp_path / "run1-demo.json").write_text(json.dumps(run), encoding="utf-8")
    CAMP.campaign(tmp_path)
    meas = json.loads((tmp_path / "measured-demo.json").read_text(encoding="utf-8"))
    assert meas["slides"]["1"]["G-06"] == 1
    assert "slide 1" in (tmp_path / "demo.md").read_text(encoding="utf-8")  # the facts reach the report
    # an existing measured file is never overwritten
    (tmp_path / "measured-demo.json").write_text('{"slides": {}, "facts": {}}', encoding="utf-8")
    CAMP.campaign(tmp_path)
    assert json.loads((tmp_path / "measured-demo.json").read_text(encoding="utf-8")) == {
        "slides": {},
        "facts": {},
    }


def test_example_27_measures_clean(tmp_path):
    out = tmp_path / "e27.pptx"
    build(ROOT / "examples" / "27-editorial.md", out)
    res = M.measure_deck(out)
    assert set(res["slides"]) == {"1", "2", "3", "4", "5", "6"}
    for n, lv in res["slides"].items():
        assert lv["G-09"] == 3, (n, res["facts"][n])  # text >= 4.5:1, series and marks >= 3:1
        assert "G-12" not in lv, (n, res["facts"][n])
    assert "chart series" in res["facts"]["4"]
    assert float(res["facts"]["4"].split("min non-text contrast ")[1].split(":")[0]) >= 3.0


# ---- Fix 5: editorial chart series


def test_editorial_chart_series_reach_3_to_1_on_the_paper():
    from slidemark.theme import get_theme

    th = get_theme("editorial")
    paper = th.hexval("bg")
    for c in th.chart_palette():
        assert ratio("#" + c, paper) >= 3.0, c


def _chart_md(theme: str, colors: str = "") -> str:
    head = f"theme: {theme}\n\n# Orders\n\n```column {{hl=Q2{colors}}}\n"
    return head + ",Orders,Refunds\nQ1,120,12\nQ2,150,14\n```\n"


def test_pale_series_lint_on_editorial(tmp_path):
    src = tmp_path / "d.md"
    src.write_text(_chart_md("editorial"), encoding="utf-8")
    r = build(src, tmp_path / "d.pptx")
    assert not [d for d in r.diagnostics if d.rule == "contrast"]  # the preset passes
    src.write_text(_chart_md("editorial", " colors=#8794AB;#C2C9D6"), encoding="utf-8")
    r = build(src, tmp_path / "d.pptx")
    hits = [d for d in r.diagnostics if d.rule == "contrast" and "series" in d.message]
    assert hits and "non-text contrast" in hits[0].message
    new = hits[0].hint.split(" with ")[1].split(" ")[0]
    assert ratio(new, "#F5F5F5") >= 3.0  # the hint names a passing colour


def test_lint_is_off_where_the_token_is_not_set(tmp_path):
    src = tmp_path / "d.md"
    src.write_text(_chart_md("default", " colors=#8794AB;#C2C9D6"), encoding="utf-8")
    r = build(src, tmp_path / "d.pptx")
    assert not [d for d in r.diagnostics if d.rule == "contrast" and "series" in d.message]
