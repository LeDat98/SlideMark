"""Chart options, CSV edge cases and table attributes."""

import pytest

from slidemark.parser import parse


def _chart(fence_info: str, body: str = ",a,b\ns,1,2"):
    d = parse(f"# A\n```{fence_info}\n{body}\n```\n")
    return d.slides[0].elements[0], d


def test_chart_options_normalized():
    c, d = _chart(
        'column {title=T legend=RIGHT labels=yes fmt="#,##0.0" min=0 max=１００ '
        'colors="primary, #1D4ED8 ,accent" axis=off}'
    )
    assert c.title == "T"
    assert c.options == {
        "legend": "right",
        "labels": "on",
        "fmt": "#,##0.0",
        "min": 0.0,
        "max": 100.0,
        "colors": ["primary", "#1D4ED8", "accent"],
        "axis": "off",
    }
    assert not d.diagnostics


def test_chart_options_labels_variants():
    assert _chart("pie {labels=percent}")[0].options["labels"] == "percent"
    assert _chart("pie {labels=false}")[0].options["labels"] == "off"


@pytest.mark.parametrize(
    "info",
    ["legend=up", "labels=maybe", "min=abc", "max=x", "colors=red", "colors=#12", "axis=2", "fmt=''"],
)
def test_chart_bad_option_dropped_with_hint(info):
    c, d = _chart(f"column {{{info}}}")
    assert info.split("=")[0] not in c.options
    w = [x for x in d.diagnostics if x.rule == "bad-chart-option"]
    assert w and w[0].level == "warning" and w[0].hint and "\n" not in w[0].hint


def test_chart_unknown_option_did_you_mean():
    _, d = _chart("column {legnd=top}")
    w = [x for x in d.diagnostics if x.rule == "bad-chart-option"]
    assert w and "legend" in w[0].hint


def test_chart_csv_quotes_thousands_fullwidth_and_jp_minus():
    c, d = _chart("column", ',a,b,c,d,e\ns,"1,240",１２．５,－3,▲3,')
    assert c.series[0].values == [1240.0, 12.5, -3.0, -3.0, None]
    assert not d.diagnostics


def test_chart_percent_flag():
    c, _ = _chart("pie", ",a,b\ns,12%,88%")
    assert c.series[0].values == [12.0, 88.0] and c.options["percent"] is True
    c, _ = _chart("pie", ",a,b\ns,12%,88")
    assert "percent" not in c.options


def test_chart_bad_number_and_ragged():
    c, d = _chart("bar", ",a,b\ns,x,2,3\nt,1")
    rules = [x.rule for x in d.diagnostics]
    assert "bad-number" in rules and rules.count("chart-ragged") == 2
    assert c.series[0].values == [None, 2.0] and c.series[1].values == [1.0, None]
    assert all(x.hint for x in d.diagnostics)


def test_chart_csv_delimiters_bom_blank_lines():
    c, _ = _chart("column", "﻿;a;b\n\n\ns;1;2\n")
    assert c.categories == ["a", "b"] and c.series[0].values == [1.0, 2.0]
    c, _ = _chart("column", "\ta\tb\n\ns\t3\t4\n")
    assert c.series[0].values == [3.0, 4.0]
    c, _ = _chart("column", "x;a;b\ns;5;6")
    assert c.series[0].values == [5.0, 6.0]


def test_table_csv_edge_cases():
    d = parse('# A\n```table\n﻿name;qty\n"a,b";1\n\nc\n```\n')
    t = d.slides[0].elements[0]
    assert [[c.paragraphs[0].plain if c.paragraphs else "" for c in r] for r in t.rows] == [
        ["name", "qty"],
        ["a,b", "1"],
        ["c", ""],
    ]
    assert any(x.rule == "table-ragged" for x in d.diagnostics)


def test_table_attrs_on_fence():
    d = parse("# A\n```table {widths=3:1:1 align=lcr header=0 hcol=1}\na,b,c\n1,2,3\n```\n")
    t = d.slides[0].elements[0]
    assert t.col_widths == [3.0, 1.0, 1.0] and t.header_rows == 0 and t.header_cols == 1
    assert [c.style.align for c in t.rows[0]] == ["left", "center", "right"]
    assert [c.style.align for c in t.rows[1]] == ["left", "center", "right"]
    assert not d.diagnostics


def test_table_attrs_before_gfm_table():
    d = parse("# A\n{widths=2:1 align=lr header=2}\n| a | b |\n|-|-|\n| 1 | 2 |\n| 3 | 4 |\n")
    t = d.slides[0].elements[0]
    assert t.col_widths == [2.0, 1.0] and t.header_rows == 2
    assert t.rows[2][1].style.align == "right"
    assert not d.diagnostics


def test_table_attr_count_mismatch_warns_and_applies():
    d = parse("# A\n```table {widths=1:2 align=lcrr}\na,b,c\n1,2,3\n```\n")
    t = d.slides[0].elements[0]
    assert len(t.col_widths) == 3 and t.col_widths[:2] == [1.0, 2.0]
    assert [c.style.align for c in t.rows[0]] == ["left", "center", "right"]
    w = [x for x in d.diagnostics if x.rule == "bad-table-option"]
    assert len(w) == 2 and all(x.hint for x in w)


@pytest.mark.parametrize("info", ["widths=a:b", "widths=0:1", "align=lx", "header=-1", "header=x", "hcol=y"])
def test_table_bad_attrs_never_raise(info):
    d = parse(f"# A\n```table {{{info}}}\na,b\n1,2\n```\n")
    assert any(x.rule == "bad-table-option" for x in d.diagnostics)
