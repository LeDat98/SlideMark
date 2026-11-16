"""``@timeline`` time scale (rubric T-TIME-01): dated headings are placed by time, keep a gap, flag breaks."""

from __future__ import annotations

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from pptx import Presentation

from slidemark import build
from slidemark.layout import timescale

HEAD = "---\ntitle: t\n---\n"
HIST = [
    ("1956", "a"),
    ("1997", "b"),
    ("2012", "c"),
    ("2017", "d"),
    ("2022", "e"),
]


def deck_text(rows, attrs="dir=h marks=on") -> str:
    return HEAD + f"\n# T\n@timeline {attrs}\n" + "".join(f"## {h}\n{b}\n" for h, b in rows)


def build_prs(tmp_path, text, name="d"):
    deck = build(text, tmp_path / f"{name}.pptx")
    return deck, Presentation(str(tmp_path / f"{name}.pptx"))


def centres(prs, n, vertical=False):
    shapes = {s.name: s for s in prs.slides[0].shapes}
    out = []
    for i in range(1, n + 1):
        d = shapes[f"Timeline {i} dot"]
        out.append(d.top + d.height / 2 if vertical else d.left + d.width / 2)
    return out


def breaks(prs):
    return [s for s in prs.slides[0].shapes if s.name == "Timeline break"]


@pytest.mark.parametrize(
    ("text", "year"),
    [
        ("1956", 1956.0),
        ("2026-03", 2026 + 2 / 12),
        ("Q3 2026", 2026.5),
        ("2026 Q1", 2026.0),
        ("FY2025", 2025.0),
        ("2026年4月", 2026 + 3 / 12),
        ("Mar 2026", 2026 + 2 / 12),
        ("2024-2026", 2024.0),
        ("H2 2026", 2026.5),
    ],
)
def test_parse_when(text, year):
    assert timescale.parse_when(text) == pytest.approx(year)


@pytest.mark.parametrize("text", ["", "Phase 1", "Kickoff", "2026-13", "99999", "soon", "Q5 2026"])
def test_parse_when_rejects(text):
    assert timescale.parse_when(text) is None


def test_marks_are_proportional_to_time_when_there_is_room(tmp_path):
    rows = [("2020", "a"), ("2022", "b"), ("2026", "c")]
    _d, prs = build_prs(tmp_path, deck_text(rows))
    x = centres(prs, 3)
    assert (x[1] - x[0]) / (x[2] - x[1]) == pytest.approx(0.5, rel=0.05)
    assert not breaks(prs)  # honest scale: no cue needed


def test_t5_history_keeps_a_minimum_gap_and_flags_the_stretched_gaps(tmp_path):
    deck, prs = build_prs(tmp_path, deck_text(HIST))
    x = centres(prs, 5)
    gaps = [b - a for a, b in zip(x, x[1:], strict=False)]
    assert gaps[0] > gaps[1] > gaps[2]  # 41 > 15 > 5 years keep their order
    assert min(gaps) >= 0.6 * (x[-1] - x[0]) / 4 * 0.98  # layout.timeline_min_gap x the equal gap
    assert len(breaks(prs)) == 4  # two cuts, two slanted strokes each: 2012-2017 and 2017-2022
    assert not [d for d in deck.diagnostics if d.rule == "form-scale"]


def test_labels_of_neighbours_on_the_same_side_do_not_overlap(tmp_path):
    _d, prs = build_prs(tmp_path, deck_text(HIST))
    texts = [s for s in prs.slides[0].shapes if s.name.startswith("Timeline ") and s.name[9:].isdigit()]
    for a in texts:
        for b in texts:
            if a is not b and abs(a.top - b.top) < 1000:  # same side
                assert a.left + a.width <= b.left + 1 or b.left + b.width <= a.left + 1


def test_even_keeps_equal_spacing_and_time_forces_the_scale(tmp_path):
    _d, prs = build_prs(tmp_path, deck_text(HIST, "dir=h marks=on scale=even"))
    x = centres(prs, 5)
    gaps = [round(b - a) for a, b in zip(x, x[1:], strict=False)]
    assert max(gaps) - min(gaps) <= 2
    assert not breaks(prs)
    _d, prs = build_prs(tmp_path, deck_text(HIST, "dir=h marks=on scale=time"), "t")
    x = centres(prs, 5)
    assert (x[1] - x[0]) > 2 * (x[2] - x[1])


def test_non_date_headings_keep_equal_spacing(tmp_path):
    rows = [("Kickoff", "a"), ("Beta", "b"), ("GA", "c")]
    deck, prs = build_prs(tmp_path, deck_text(rows))
    x = centres(prs, 3)
    assert abs((x[1] - x[0]) - (x[2] - x[1])) <= 2
    assert not [d for d in deck.diagnostics if d.rule == "form-scale"]
    deck, _ = build_prs(tmp_path, deck_text(rows, "dir=h marks=on scale=time"), "t")
    assert [d for d in deck.diagnostics if d.rule == "form-scale"]  # asked for time but no dates


def test_out_of_order_dates_fall_back_to_equal_spacing(tmp_path):
    _d, prs = build_prs(tmp_path, deck_text([("2030", "a"), ("2020", "b"), ("2025", "c")]))
    x = centres(prs, 3)
    assert abs((x[1] - x[0]) - (x[2] - x[1])) <= 2


def test_vertical_timeline_is_proportional_with_breaks(tmp_path):
    _d, prs = build_prs(tmp_path, deck_text(HIST, "dir=v marks=on"))
    y = centres(prs, 5, vertical=True)
    gaps = [b - a for a, b in zip(y, y[1:], strict=False)]
    assert gaps[0] > gaps[1] > gaps[2] > 0
    assert breaks(prs)
    rows = [s for s in prs.slides[0].shapes if s.name in {f"Timeline {i}" for i in range(1, 6)}]
    rows.sort(key=lambda s: s.top)
    assert all(a.top + a.height <= b.top + 1 for a, b in zip(rows, rows[1:], strict=False))


def test_japanese_and_quarter_headings_scale(tmp_path):
    rows = [("2026年4月", "a"), ("2027年4月", "b"), ("2029年4月", "c")]
    _d, prs = build_prs(tmp_path, deck_text(rows))
    x = centres(prs, 3)
    assert (x[2] - x[1]) / (x[1] - x[0]) == pytest.approx(2.0, rel=0.1)


def test_place_never_leaves_the_span():
    off, flags = timescale.place([0, 1, 100], 100.0, 30.0)
    assert off[0] == 0 and off[-1] == pytest.approx(100.0)
    assert flags == [True, False]
    off, flags = timescale.place([1, 2, 3, 4], 10.0, 6.0)  # no room for the minimum
    assert off == pytest.approx([0, 10 / 3, 20 / 3, 10]) and all(flags)


@settings(max_examples=40, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    heads=st.lists(
        st.one_of(
            st.integers(-5, 12000).map(str),
            st.text(max_size=12),
            st.sampled_from(["2026-02-30", "Q9 2026", "FY99", "0000", "2026年13月", "1-1", "9999-12"]),
        ),
        min_size=2,
        max_size=8,
    ),
    attr=st.sampled_from(["", "dir=v", "scale=time", "scale=bogus", "dir=v marks=num"]),
)
def test_fuzz_odd_dates_never_raise(tmp_path_factory, heads, attr):
    tmp = tmp_path_factory.mktemp("f")
    text = (
        HEAD
        + f"\n# T\n@timeline {attr}\n"
        + "".join(f"## {h.replace(chr(10), ' ').strip() or 'x'}\nb\n" for h in heads)
    )
    build(text, tmp / "d.pptx")
