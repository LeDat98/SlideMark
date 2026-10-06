"""``hl=`` on a table emphasises the rows whose first cell matches: parse, render, CSS, lint, import."""

from __future__ import annotations

from pathlib import Path

import pytest
from pptx import Presentation

from slidemark import build
from slidemark.importer import import_pptx
from slidemark.layout import layout_slide
from slidemark.layout.tablehl import hl_rows
from slidemark.lint import lint
from slidemark.parser import parse
from slidemark.template import deck_theme

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
ROWS = (
    "| 区分 | 売上 | 粗利率 |\n|-|-|-|\n| 生鮮 | 120 | 18% |\n| 冷凍食品 | 80 | 31% |\n"
    "| 日配 | 95 | 22% |\n| 海外 | 40 | 35% |\n"
)


def _table(md: str):
    deck = parse(md)
    return deck, next(e for e in deck.slides[0].elements if e.type == "table")


def _rows(pptx: Path):
    gf = next(s for s in Presentation(str(pptx)).slides[0].shapes if s.has_table)
    return gf, gf.table


def _fill(cell) -> str:
    return str(cell.fill.fore_color.rgb)


def _bold(cell) -> bool:
    return all(r.font.bold for p in cell.text_frame.paragraphs for r in p.runs if r.text.strip())


def test_names_select_first_cell_rows_and_may_be_quoted():
    deck, t = _table("# T\n{hl=冷凍食品,海外}\n" + ROWS)
    assert t.attrs["hl"] == ["冷凍食品", "海外"] and deck.diagnostics == []
    assert hl_rows(t) == {2, 4}
    _, t = _table("# T\n{hl=冷凍食品, 海外}\n" + ROWS)  # a space after the comma is read as part of the list
    assert t.attrs["hl"] == ["冷凍食品", "海外"]
    csv = '# T\n```table {hl="Metro, East",B}\nk,v\n"Metro, East",1\nB,2\nC,3\n```\n'
    _, t = _table(csv)
    assert t.attrs["hl"] == ["Metro, East", "B"]
    assert hl_rows(t) == {1, 2}


def test_unknown_row_warns_with_did_you_mean_and_never_raises():
    deck, t = _table("# T\n{hl=冷凍食物,日配}\n" + ROWS)
    w = [d for d in deck.diagnostics if d.rule == "table-hl"]
    assert len(w) == 1 and "冷凍食物" in w[0].message and "did you mean '冷凍食品'" in w[0].hint
    assert t.attrs["hl"] == ["日配"]  # the valid name still works
    deck, t = _table("# T\n{hl=nothing}\n" + ROWS)
    assert [d.rule for d in deck.diagnostics] == ["table-hl"] and "hl" not in t.attrs
    assert "first cells are" in deck.diagnostics[0].hint


def test_header_row_is_not_a_target():
    deck, t = _table("# T\n{hl=区分}\n" + ROWS)
    assert [d.rule for d in deck.diagnostics] == ["table-hl"]


def test_render_fills_and_bolds_only_the_named_rows(tmp_path):
    out = tmp_path / "a.pptx"
    build("# T\n{hl=冷凍食品,海外}\n" + ROWS, out)
    gf, tbl = _rows(out)
    body = _fill(tbl.cell(1, 1))  # plain row
    for r in (2, 4):
        fills = {_fill(tbl.cell(r, c)) for c in range(3)}
        assert len(fills) == 1 and fills != {body}
        assert all(_bold(tbl.cell(r, c)) for c in range(3))
    for r in (1, 3):
        assert _fill(tbl.cell(r, 1)) == body and not _bold(tbl.cell(r, 1))
    assert gf.name.endswith(" hl=冷凍食品,海外")


def test_tokens_override_fill_color_and_bold(tmp_path):
    out = tmp_path / "a.pptx"
    head = "style: table.hl.fill=#FFEE00 table.hl.strength=1 table.hl.color=#112233 table.hl.bold=off\n\n"
    build(head + "# T\n{hl=海外}\n" + ROWS, out)
    _, tbl = _rows(out)
    assert _fill(tbl.cell(4, 1)) == "FFEE00"
    run = tbl.cell(4, 1).text_frame.paragraphs[0].runs[0]
    assert str(run.font.color.rgb) == "112233"
    assert (
        not run.font.bold or tbl.cell(4, 0).text_frame.paragraphs[0].runs[0].font.bold
    )  # only col 0 may be bold


def test_css_tr_hl_overrides_the_default(tmp_path):
    out = tmp_path / "a.pptx"
    build("```css\ntr.hl { background: #00FF00 }\n```\n\n# T\n{hl=海外}\n" + ROWS, out)
    _, tbl = _rows(out)
    assert _fill(tbl.cell(4, 1)) == "00FF00"


def test_html_tr_class_hl():
    from slidemark.parser.html import parse_html

    html = (
        "<section><h1>T</h1><table><tr><th>a</th><th>b</th></tr>"
        '<tr class="hl"><td>x</td><td>1</td></tr><tr><td>y</td><td>2</td></tr></table></section>'
    )
    tables = [e for s in parse_html(html).slides for e in s.elements if e.type == "table"]
    assert tables[0].attrs["hl"] == ["x"]


@pytest.mark.parametrize("theme", ["default", "midnight", "jp-business"])
def test_every_preset_reads_and_passes_contrast(theme):
    deck = parse(f"theme: {theme}\n\n# T\n{{hl=冷凍食品,海外}}\n" + ROWS)
    th, _ = deck_theme(deck, EXAMPLES)
    placed = [layout_slide(s, deck, th, i) for i, s in enumerate(deck.slides)]
    assert [d for d in lint(deck, placed, th) if d.rule == "contrast"] == []
    body, hl = th.table_body_fill_of(None), th.table_hl_fill_of(th.table_body_fill_of(None))
    assert hl != body


def test_dark_text_on_a_strong_hl_fill_is_linted():
    deck = parse(
        "colors: bg=#101820 fg=#F5F5F5\n"
        "style: table.hl.fill=#FFFF99 table.hl.strength=1 table.hl.color=#FFFFFF\n\n# T\n{hl=海外}\n" + ROWS
    )
    th, _ = deck_theme(deck, EXAMPLES)
    placed = [layout_slide(s, deck, th, i) for i, s in enumerate(deck.slides)]
    got = [d for d in lint(deck, placed, th) if d.rule == "contrast" and d.message.startswith("table")]
    assert got and "emphasised rows" in got[0].message


def test_import_round_trip_gives_hl_back(tmp_path):
    a = tmp_path / "a.pptx"
    build("# T\n{hl=冷凍食品,海外}\n" + ROWS, a)
    text, _ = import_pptx(a, tmp_path)
    assert "hl=冷凍食品,海外" in text
    assert "**" not in text  # the bold of emphasised rows is not imported as markup
    b = tmp_path / "b.pptx"
    build(text, b)
    _, t1 = _rows(a)
    _, t2 = _rows(b)
    for r in range(5):
        assert _fill(t1.cell(r, 1)) == _fill(t2.cell(r, 1))


def test_import_round_trip_with_comma_name(tmp_path):
    a = tmp_path / "a.pptx"
    md = '# T\n```table {hl="Metro, East"}\nk,v\n"Metro, East",1\nB,2\n```\n'
    build(md, a)
    text, _ = import_pptx(a, tmp_path)
    b = tmp_path / "b.pptx"
    build(text, b)
    _, t2 = _rows(b)
    assert _fill(t2.cell(1, 1)) != _fill(t2.cell(2, 1))


def test_fuzz_values_never_raise():
    for val in ['""', "''", ",", ",,,", '"', "a,", ",a", '"a,b', "⁠", "0", "冷凍食品;海外"]:
        parse("# T\n{hl=" + val + "}\n" + ROWS)
        parse("# T\n```table {hl=" + val + "}\na,b\n1,2\n```\n")
