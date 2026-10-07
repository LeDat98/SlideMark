"""One deck-wide growth ceiling, ``layout.grow_max`` (default 1.5): no growth pass takes text beyond that
multiple of its role's size, on top of the pass's own absolute cap (the smaller wins). ``grow_max=1`` switches
growth off, a pinned size (``size=``) is never touched, and a slide that stays sparse says so (fit line suffix
``sparse: 42% free`` + one ``sparse`` info)."""

from __future__ import annotations

import re

import pytest

from slidemark.build import build
from slidemark.cli import _grouped
from slidemark.ir import Shape, Table, Text
from slidemark.theme import LayoutTokens

from .test_layout_l3_fill import lay
from .test_sparse_wave2 import CARDS, CHEV_PLAIN, HEAD, LIST, TABLE

STEPS = HEAD + "# 年間計画\n@3 steps\n## 4月\n- 価格改定\n## 7月\n- 工場着工\n## 10月\n- 北米発売\n"
KPI = (
    HEAD
    + "# 主要指標\n## 売上高 {.kpi}\n1,280億円\n前年比 +8%\n## 営業利益 {.kpi}\n96億円\n前年比 +12%\n"
    + "## ROE {.kpi}\n9.0%\n+0.8pt\n"
)
EPS = 0.02  # rounding of the growth steps
OFF = {"grow_max": 1}  # growth off: the sizes the slide has by role
HUGE = {"grow_max": 100}  # no ceiling: the pass's own cap is the only limit


def _sizes(placed, role: str | None = None) -> list[float]:
    """Drawn size (pt) of every paragraph of the body text (``role`` None) or of one role."""
    out = []
    for p in placed:
        el = p.element
        if isinstance(el, Text) and el.paragraphs and (role or "body") == el.role:
            for para in el.paragraphs:
                fs = (para.style.font_size if para.style else None) or p.style.font_size
                out.append((fs or 0.0) * p.font_scale)
    return out


def _shape_pt(placed) -> float:
    return max((p.style.font_size or 0) * p.font_scale for p in placed if isinstance(p.element, Shape))


def _table_pt(placed) -> float:
    (t,) = [p for p in placed if isinstance(p.element, Table)]
    return (t.style.font_size or 0) * t.font_scale


def _within(grown: float, base: float, ceiling: float = 1.5) -> bool:
    return grown <= base * ceiling * (1 + EPS)


# --------------------------------------------------------------------------- one test per growth pass


def test_token_defaults_and_style_spelling():
    lt = LayoutTokens()
    assert lt.grow_max == 1.5 and lt.sparse_note == 0.35
    from slidemark.parser import parse
    from slidemark.template import deck_theme

    d = parse("theme: none\nstyle: grow.max=1.2\n# T\n- a\n")
    theme, diags = deck_theme(d, ".")
    assert theme.layout.grow_max == 1.2 and not [x for x in diags if x.level != "info"]
    d = parse("theme: none\nstyle: layout.grow_max=1.3\n# T\n- a\n")
    assert deck_theme(d, ".")[0].layout.grow_max == 1.3


def test_list_text_stops_at_the_ceiling():
    base = max(_sizes(lay("", 1, src=LIST, **OFF)[0]))
    capped = max(_sizes(lay("", 1, src=LIST)[0]))
    free = max(_sizes(lay("", 1, src=LIST, **HUGE)[0]))
    assert free > 1.5 * base * (
        1 + EPS
    )  # without the ceiling this deck would exceed it (list_text_max_pt 28)
    assert base < capped <= base * 1.5 * (1 + EPS)


def test_card_text_stops_at_the_ceiling():
    base = max(_sizes(lay("", 1, src=CARDS, **OFF)[0]))
    capped = max(_sizes(lay("", 1, src=CARDS)[0]))
    free = max(_sizes(lay("", 1, src=CARDS, **HUGE)[0]))
    assert free > 1.5 * base * (1 + EPS)
    assert base < capped <= base * 1.5 * (1 + EPS)
    # a tighter ceiling is the same mechanism
    tight = max(_sizes(lay("", 1, src=CARDS, grow_max=1.2)[0]))
    assert tight <= base * 1.2 * (1 + EPS) < capped


def test_steps_card_text_and_arrow_label_stop_at_the_ceiling():
    off, capped, free = (lay("", 1, src=STEPS, **kw)[0] for kw in (OFF, {}, HUGE))
    assert max(_sizes(free)) > 1.5 * max(_sizes(off)) * (1 + EPS)  # steps_to_body_text_max_pt 28
    assert max(_sizes(off)) < max(_sizes(capped)) <= max(_sizes(off)) * 1.5 * (1 + EPS)
    assert _shape_pt(off) < _shape_pt(capped) <= _shape_pt(off) * 1.5 * (1 + EPS)


def test_lone_table_text_stops_at_the_ceiling_but_rows_still_stretch():
    off, capped, free = (lay("", 1, src=TABLE, **kw)[0] for kw in (OFF, {}, HUGE))
    assert _table_pt(free) > 1.5 * _table_pt(off) * (1 + EPS)  # table_free_text_max_pt 22
    assert _table_pt(off) < _table_pt(capped) <= _table_pt(off) * 1.5 * (1 + EPS)
    (t_off,), (t_cap,) = ([p for p in x if isinstance(p.element, Table)] for x in (off, capped))
    assert t_cap.h > t_off.h  # filling the body by rows is still fine


def test_kpi_value_label_and_caption_stop_at_the_ceiling():
    off, capped, free = (lay("", 1, src=KPI, **kw)[0] for kw in (OFF, {}, HUGE))
    value = lambda pl: max(s for s in _sizes(pl))  # noqa: E731
    assert value(free) > 1.5 * value(off) * (1 + EPS)  # kpi_lone_value_grow 2.4
    assert value(off) < value(capped) <= value(off) * 1.5 * (1 + EPS)
    head = lambda pl: max(_sizes(pl, "heading"))  # noqa: E731
    assert head(off) < head(capped) <= head(off) * 1.5 * (1 + EPS)
    cap_line = lambda pl: min(s for s in _sizes(pl))  # noqa: E731  (the caption lines are the smallest text)
    assert cap_line(capped) <= cap_line(off) * 1.5 * (1 + EPS)


def test_chevron_row_text_stops_at_the_ceiling():
    off, capped, free = (lay("", 1, src=CHEV_PLAIN, **kw)[0] for kw in (OFF, {}, HUGE))
    assert _shape_pt(free) > 1.5 * _shape_pt(off) * (1 + EPS)  # chevron_text_max_pt 26
    assert _shape_pt(off) < _shape_pt(capped) <= _shape_pt(off) * 1.5 * (1 + EPS)


# --------------------------------------------------------------------------- off, pinned, the author's size


@pytest.mark.parametrize("src", [LIST, CARDS, STEPS, TABLE, KPI, CHEV_PLAIN])
def test_grow_max_one_switches_growth_off(src):
    placed, _, _ = lay("", 1, src=src, grow_max=1)
    nogrow, _, _ = lay("", 1, src=src, grow_max=1, grow=False)
    sizes = lambda pl: sorted(round(s, 1) for s in _sizes(pl) + _sizes(pl, "heading"))  # noqa: E731
    assert sizes(placed) == sizes(nogrow)  # every pass is held at the role size
    if any(isinstance(p.element, Table) for p in placed):
        assert _table_pt(placed) == pytest.approx(_table_pt(nogrow))
    elif any(isinstance(p.element, Shape) and p.style.font_size for p in placed):
        assert _shape_pt(placed) == pytest.approx(_shape_pt(nogrow))


def test_a_pinned_text_size_is_untouched():
    pinned = LIST.replace("- 主力3", "{size=14}\n- 主力3")
    for kw in ({}, HUGE, OFF):
        placed, _, _ = lay("", 1, src=pinned, **kw)
        assert {round(s, 1) for s in _sizes(placed)} == {14.0}
    import tempfile
    from pathlib import Path

    bang = HEAD + "sizes: body=14!\n" + LIST.replace(HEAD, "")
    with tempfile.TemporaryDirectory() as d:  # `sizes: body=14!` is a deck token: build, do not lay out alone
        (line,) = build(bang, Path(d) / "x.pptx", base_dir=d).attrs["fit_map"]
    assert "list 4 items 14pt" in line and "grown" not in line, line


@pytest.mark.parametrize("kw", [{}, HUGE, OFF])
def test_a_table_with_the_authors_size_keeps_it(kw):
    """``{size=22}`` on a table is the author's decision, not growth (was 32pt on a sparse slide)."""
    src = TABLE.replace("{align=lrrr}", "{align=lrrr size=22}")
    placed, _, _ = lay("", 1, src=src, **kw)
    assert _table_pt(placed) == pytest.approx(22.0)


# --------------------------------------------------------------------------- the fit line and the info


def _build(md: str, tmp_path):
    return build("theme: none\n" + md, tmp_path / "x.pptx", base_dir=tmp_path)


SPARSE = "# Plan\n```table {align=lr}\nA,B\nx,1\n```\n"
FULL = "# Plan\n" + "".join(f"- point {i} with a few more words to fill the line\n" for i in range(12))


def test_a_sparse_slide_ends_its_fit_line_with_the_free_share(tmp_path):
    deck = _build("sizes: table=10\n" + SPARSE, tmp_path)
    (line,) = deck.attrs["fit_map"]
    m = re.search(r"sparse: (\d+)% free$", line)
    assert m and int(m.group(1)) > 35, line
    assert "free " not in line.replace(m.group(0), "")  # it replaces the plain free-space fact


def test_sparse_info_is_info_not_warning_and_reads_the_same_number(tmp_path):
    deck = _build("sizes: table=10\n" + SPARSE, tmp_path)
    (line,) = deck.attrs["fit_map"]
    (d,) = [x for x in deck.diagnostics if x.rule == "sparse"]
    pct = int(re.search(r"sparse: (\d+)% free", line).group(1))
    assert d.level == "info" and d.slide == 1
    assert d.message == f"slide 1 is sparse ({pct}% free)"
    assert d.hint == (
        "merge it into a neighbour, add a figure/table/chart, or change its form (@rows, @items, @steps, "
        "side by side); bigger text is capped by layout.grow_max=1.5"
    )
    assert not [x for x in deck.diagnostics if x.level in ("warning", "error")]


def test_the_hint_names_the_ceiling_of_the_deck(tmp_path):
    deck = _build("style: layout.grow_max=1.2\nsizes: table=10\n" + SPARSE, tmp_path)
    (d,) = [x for x in deck.diagnostics if x.rule == "sparse"]
    assert d.hint.endswith("layout.grow_max=1.2")


def test_a_full_slide_and_a_raised_threshold_say_nothing(tmp_path):
    deck = _build(FULL, tmp_path)
    assert not [x for x in deck.diagnostics if x.rule == "sparse"]
    assert "sparse" not in deck.attrs["fit_map"][0]
    deck = _build("style: layout.sparse_note=0.99\nsizes: table=10\n" + SPARSE, tmp_path)
    assert not [x for x in deck.diagnostics if x.rule == "sparse"]
    assert "sparse" not in deck.attrs["fit_map"][0]


def test_covers_sections_and_free_slides_are_never_sparse(tmp_path):
    deck = _build(
        "# Title\n## A subtitle\n\n# Part\n@section\n\n# F\n@free\n## a {x=5% y=20% w=20% h=20%}\n- x\n",
        tmp_path,
    )
    assert not [x for x in deck.diagnostics if x.rule == "sparse"]


def test_several_sparse_slides_print_one_line(tmp_path):
    deck = _build("sizes: table=10\n" + SPARSE + "\n" + SPARSE.replace("Plan", "Plan 2"), tmp_path)
    lines = [ln for ln in _grouped(deck.diagnostics) if " sparse: " in ln]
    assert len(lines) == 1 and lines[0].startswith("info slides 1,2 sparse: slide 1 is sparse (")
    assert lines[0].count("merge it into") == 1


def test_fit_lines_stay_short_with_the_suffix(tmp_path):
    tiktoken = pytest.importorskip("tiktoken")
    enc = tiktoken.get_encoding("o200k_base")
    deck = _build(
        "sizes: table=10\n"
        + SPARSE
        + "\n"
        + HEAD.replace("theme: jp-business\n", "")
        + LIST.replace(HEAD, ""),
        tmp_path,
    )
    for line in deck.attrs["fit_map"]:
        assert len(enc.encode(line)) <= 45, line
