"""The per-slide fit map of ``slidemark build`` (src/slidemark/fit.py): form, text sizes asked vs reached,
free space and which attributes took effect, read off the layout result (no second layout, no render)."""

from __future__ import annotations

import io
import re

import pytest

from slidemark.build import build
from slidemark.cli import main

HEAD = "theme: jp-business\nlang: ja\n"


def fit(md: str, tmp_path, head: str = HEAD) -> list[str]:
    deck = build(head + md, tmp_path / "x.pptx", base_dir=tmp_path)
    return deck.attrs["fit_map"]


def one(md: str, tmp_path, head: str = HEAD) -> str:
    (line,) = fit(md, tmp_path, head)
    assert line.startswith("slide 1: ")
    return line


# --------------------------------------------------------------------------- one test per form


def test_kpi_row_names_cards_value_size_and_free_space(tmp_path):
    md = (
        "# T\n> lead\n## 売上高 {.kpi .hero}\n1,280億円\n+8%\n## 営業利益 {.kpi}\n96億円\n+12%\n"
        "## 利益率 {.kpi}\n7.5%\n+0.3pt\n## ROE {.kpi}\n9.0%\n+0.8pt\n"
    )
    line = one(md, tmp_path, HEAD + "style: kpi.value.size=48\n")
    assert line.startswith("slide 1: lead + 4 kpi (hero) cards ")
    share = int(re.search(r"cards (\d+)% of body", line).group(1))
    assert 30 <= share <= 80
    m = re.search(r"value 48->(\d+)pt \(shrunk to fit\)", line)  # the asked size and the one reached
    assert m and int(m.group(1)) < 48
    assert re.search(r"free (\d+% above, )?\d+% below", line)


def test_kpi_value_at_the_asked_size_prints_one_size(tmp_path):
    line = one(
        "# T\n## a {.kpi}\n12\ncap\n## b {.kpi}\n34\ncap\n", tmp_path, HEAD + "style: kpi.value.size=30\n"
    )
    assert re.search(r"value \d+pt", line) and "->" not in line.split("value")[1].split(",")[0]


def test_steps_names_count_fill_and_card_text(tmp_path):
    line = one("# T\n@3 steps\n## a\n- x\n## b\n- y\n## c\n- z\n", tmp_path)
    assert line.startswith("slide 1: steps 3, arrows + cards fill ")
    assert re.search(r"fill \d+%", line)
    assert re.search(r"card text 11->\d+pt \(grown\)", line)  # jp-business body 11pt grows to fill the cards


def test_compact_chevron_row(tmp_path):
    line = one(
        "# T\n@3 chevron\n## a\n- x\n## b\n- y\n## c\n- z\n",
        tmp_path,
        HEAD + "style: layout.chevron_steps=off\n",
    )
    assert line.startswith("slide 1: chevron 3 (compact), text ")


def test_table_and_conclusion_bar_attached(tmp_path):
    line = one("# T\n```table\na,b\n1,2\n3,4\n```\n> bar\n", tmp_path)
    assert line.startswith("slide 1: table 3x2 at ")
    assert "(grown)" in line and "+ conclusion bar attached" in line


def test_table_options_took_effect(tmp_path):
    line = one("# T\n```table {.zebra hl=a}\nn,v\na,1\nb,2\n```\n", tmp_path)
    assert "zebra" in line and "hl 1 row" in line


def test_list_names_items_and_size(tmp_path):
    line = one("# T\n> lead\n- one\n- two\n- three\n", tmp_path)
    assert line.startswith("slide 1: lead + list 3 items ")
    assert re.search(r"list 3 items 11->\d+pt \(grown\)", line)
    assert re.search(r"free (\d+% above, )?\d+% below", line)


def test_chart_names_kind_series_labels_and_hl(tmp_path):
    md = '# T\n```line {labels=on hl=北米 note="北米が最大"}\n,2024,2025\nタイ,70,82\n北米,20,30\n```\n'
    line = one(md, tmp_path)
    assert line.startswith("slide 1: line chart, 2 series, labels on, hl=北米, note")


def test_boxes_name_count_and_arrangement(tmp_path):
    line = one("# T\n## a\n- x\n## b\n- y\n## c\n- z\n## d\n- w\n", tmp_path)
    assert line.startswith("slide 1: 4 boxes (2x2), text 11->")
    row = one("# T\n@3\n## a\n- x\n## b\n- y\n## c\n- z\n", tmp_path)
    assert row.startswith("slide 1: 3 boxes (row), text ")


def test_free_slide_counts_pinned_blocks(tmp_path):
    md = "# T\n@free\n## a {x=5% y=20% w=40% h=40%}\n- x\n## b {x=55% y=20% w=40% h=40%}\n- y\n"
    assert one(md, tmp_path).startswith("slide 1: free 2 blocks, 2 pinned")


def test_rows_names_bars(tmp_path):
    assert one("# T\n@rows\n1. a\n2. b\n3. c\n", tmp_path).startswith("slide 1: rows 3 bars ")


def test_html_slide(tmp_path):
    pytest.importorskip("playwright")
    md = '# T\n@html\n```html\n<div style="padding:40px"><h1>Hi</h1><p>There</p></div>\n```\n'
    try:
        line = one(md, tmp_path)
    except Exception as e:  # Chromium missing in this environment
        pytest.skip(str(e))
    assert re.fullmatch(r"slide 1: html, \d+ shapes", line) or "no fit data" in line


def test_cover_names_title_size_and_composition(tmp_path):
    line = fit("# Title\n## sub\n\n# Body\n- x\n", tmp_path)[0]
    assert re.fullmatch(r"slide 1: cover, title \d+->\d+pt \(grown\), subtitle \d+pt, band composed", line), (
        line
    )
    sized = fit("# Title {size=40}\n## sub\n\n# Body\n- x\n", tmp_path)[0]
    assert "centred block" in sized and "took size=40" in sized  # {size=} keeps the old centred look
    section = fit("# A\n- x\n\n# Part two\n## sub\n", tmp_path)[1]
    assert section.startswith("slide 2: section, title ")


# --------------------------------------------------------------------------- attributes


def test_took_and_ignored_attributes(tmp_path):
    md = "# T\n> lead\n## a {.kpi h=55% size=30 bold=true}\n1\nc\n## b {.kpi}\n2\nc\n@end\n- x\n"
    line = one(md, tmp_path)
    assert line.endswith("took h size=30, ignored bold"), line
    beside = one("# T\n> lead\n## a {.kpi h=55%}\n1\nc\n## b {.kpi}\n2\nc\n@end\n- x\n", tmp_path)
    assert "took h" in beside and "ignored" not in beside  # a pinned row beside a list took the height too
    alone = one("# T\n> lead\n## a {.kpi h=55%}\n1\nc\n## b {.kpi}\n2\nc\n", tmp_path)
    assert "took h" in alone and "ignored" not in alone
    assert "cards 55% of body" in alone  # the pin took: the card is as tall as asked


def test_a_line_per_slide_and_never_raises(tmp_path):
    md = "# A\n- x\n\n# B\n- y\n\n# C\n```table\na,b\n1,2\n```\n"
    lines = fit(md, tmp_path)
    assert [ln.split(":")[0] for ln in lines] == ["slide 1", "slide 2", "slide 3"]


def test_lines_stay_short(tmp_path):
    tiktoken = pytest.importorskip("tiktoken")
    enc = tiktoken.get_encoding("o200k_base")
    md = (
        "# T\n> lead\n## a {.kpi .hero}\n1,280億円\n+8%\n## b {.kpi}\n96億円\n+12%\n\n"
        "# S\n@3 steps\n## a\n- x\n## b\n- y\n## c\n- z\n\n# L\n> lead\n- a\n- b\n- c\n"
    )
    for line in fit(md, tmp_path):
        assert len(enc.encode(line)) <= 45, line


# --------------------------------------------------------------------------- build output


DECK = HEAD + "colors: primary=#12355B\n\n# T\n> lead\n## a {.kpi}\n12\ncap\n## b {.kpi}\n3\ncap\n"


def _build(tmp_path, monkeypatch, capsys, text: str, *flags: str) -> list[str]:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.stdin", io.StringIO(text))
    assert main(["build", "-", "-o", "d.pptx", *flags]) == 0
    return capsys.readouterr().out.splitlines()


def test_build_prints_the_map_between_diagnostics_and_design(tmp_path, monkeypatch, capsys):
    bad = DECK.replace("{.kpi}\n12", "{.kpi h=50%}\n12").replace("# T\n", "# T\n- x\n@end\n", 1)
    out = _build(tmp_path, monkeypatch, capsys, bad)
    kinds = [
        ("warning" if ln.startswith("warning") else "fit" if ln.startswith("slide ") else ln.split(":")[0])
        for ln in out
    ]
    assert "fit" in kinds and kinds.index("fit") < kinds.index("design")
    assert kinds.index("design") < kinds.index("look") < kinds.index("wrote d.pptx")
    assert all(k != "warning" or i < kinds.index("fit") for i, k in enumerate(kinds))


def test_quiet_and_header_switch_the_map_off(tmp_path, monkeypatch, capsys):
    assert not any(ln.startswith("slide ") for ln in _build(tmp_path, monkeypatch, capsys, DECK, "--quiet"))
    assert not any(ln.startswith("slide ") for ln in _build(tmp_path, monkeypatch, capsys, DECK, "-q"))
    off = DECK.replace("lang: ja\n", "lang: ja\nfit: off\n")
    assert not any(ln.startswith("slide ") for ln in _build(tmp_path, monkeypatch, capsys, off))
    assert any(ln.startswith("slide 1: ") for ln in _build(tmp_path, monkeypatch, capsys, DECK))
    on = DECK.replace("lang: ja\n", "lang: ja\nfit: on\n")
    assert any(ln.startswith("slide 1: ") for ln in _build(tmp_path, monkeypatch, capsys, on))


def test_bad_fit_header_warns(tmp_path):
    from slidemark.parser import parse

    deck = parse("fit: maybe\n\n# T\n- x\n")
    assert [d.rule for d in deck.diagnostics] == ["bad-header"]
