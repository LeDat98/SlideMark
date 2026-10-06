"""A table beside a taller chart reaches the chart bottom although its text cannot grow."""

from __future__ import annotations

from slidemark.ir import Chart, Table
from tests.test_layout_l3_fill import lay


def _parts(name: str, n: int, **tokens):
    placed, deck, theme = lay(name, n, **tokens)
    chart = next(p for p in placed if isinstance(p.element, Chart))
    table = next(p for p in placed if isinstance(p.element, Table))
    return chart, table, theme


def test_table_reaches_chart_bottom_when_text_cannot_grow():
    chart, table, _ = _parts("20-jp-retail-dense.md", 3)
    assert abs((table.y + table.h) - (chart.y + chart.h)) <= 2000
    rows = table.element.attrs["_row_h"]
    assert abs(sum(rows) - table.h) <= 2000
    assert min(rows) > 0.8 * max(rows)  # rows stay even


def test_old_cap_without_the_token():
    chart, table, _ = _parts("20-jp-retail-dense.md", 3, table_fit_row_max_em=0.0)
    assert table.y + table.h < chart.y + chart.h - 300000  # the 4.2 em row cap stops short, as before


def test_slide_8_still_fits():
    chart, table, _ = _parts("20-jp-retail-dense.md", 8)
    assert abs((table.y + table.h) - (chart.y + chart.h)) <= 40000
