"""The pieces both foreign-deck recognisers share (importer/runs.py)."""

from slidemark.importer.emit import inline
from slidemark.importer.read import Item, RunT
from slidemark.importer.runs import claim, free, merge_lines, put_span, span_runs


def test_a_span_is_written_once_with_bold_inside():
    r = RunT("9,800", bold=True, size=26, color="E08A1E")
    put_span(r, ["size=26", "color=#E08A1E"])
    assert inline([r]) == "[**9,800**]{size=26 color=#E08A1E}"


def test_span_with_bold_key_has_no_double_bold():
    r = RunT("9,800", bold=True, size=40)
    put_span(r, ["size=40"], bold=True)
    assert inline([r]) == "[9,800]{size=40 bold}"


def test_two_writers_keep_the_first_value_of_a_key():
    r = RunT("x", size=20)
    put_span(r, ["size=20"])
    put_span(r, ["size=30", "color=#112233"])
    assert r.span == "size=20 color=#112233"
    assert inline([r]) == "[x]{size=20 color=#112233}"


def test_span_runs_multi_only_leaves_a_lone_run_alone():
    from slidemark.importer.read import ParaT

    lone = [ParaT(runs=[RunT("12", size=40)])]
    span_runs(lone, size_off=lambda r: True, color_of=lambda r: None, multi_only=True)
    assert lone[0].runs[0].span == ""


def test_style_and_sizes_lines_merge_into_one_each():
    got = merge_lines(
        [
            'style: s1.border-top="4pt solid #1F5FA8" kpi.fill=#EEF2F7',
            "sizes: kpi=40",
            "style: kpi.fill=#000000 steps-arrow.size=14",
            None,
            "sizes: kpi=30 body=12!",
        ]
    )
    assert got == [
        'style: s1.border-top="4pt solid #1F5FA8" kpi.fill=#EEF2F7 steps-arrow.size=14',
        "sizes: kpi=40 body=12!",
    ]


def test_claim_makes_a_shape_not_free():
    it = Item(kind="shape", x=0, y=0, w=1, h=1)
    assert free(it)
    claim(it, "steps")
    assert not free(it) and it.role is None
