"""Info rule `diagram-budget`: nodes, arrows, label length and accent shapes of one diagram slide."""

from __future__ import annotations

import pytest

from slidemark.build import build_deck
from slidemark.cli import main
from slidemark.layout import layout_slide
from slidemark.lint import lint_deck
from slidemark.parser import parse
from slidemark.template import deck_theme


def _mermaid(nodes: int, edges: int | None = None, label: str = "") -> str:
    names = [f"N{i}" for i in range(nodes)]
    edges = nodes - 1 if edges is None else edges
    lines = ["flowchart LR"]
    pairs = [(i, j) for d in range(1, nodes) for i in range(nodes) for j in [i + d] if j < nodes]
    for k, (i, j) in enumerate(pairs[:edges]):
        lab = f"|{label}|" if label and k == 0 else ""
        lines.append(f"  {names[i]} -->{lab} {names[j]}")
    if nodes == 1:
        lines.append("  N0")
    return "```mermaid\n" + "\n".join(lines) + "\n```\n"


def _budget(text: str, header: str = "") -> list:
    deck = parse(header + "# S\n" + text)
    theme, _ = deck_theme(deck, ".")

    placed = [layout_slide(s, deck, theme, i) for i, s in enumerate(deck.slides)]
    return [d for d in lint_deck(deck, placed, theme) if d.rule == "diagram-budget"]


def test_mermaid_nodes_over_budget_fire():
    got = _budget(_mermaid(11))
    assert len(got) == 1 and got[0].level == "info" and got[0].slide == 1
    assert got[0].message.startswith("11 nodes (keep <= 9: split into two diagrams)")
    assert got[0].hint


def test_mermaid_nodes_within_budget_quiet():
    assert not _budget(_mermaid(9))


def test_mermaid_edges_over_budget_fire():
    got = _budget(_mermaid(6, edges=13))
    assert len(got) == 1 and "13 arrows (keep <= 12)" in got[0].message
    assert not _budget(_mermaid(6, edges=12))


def test_edge_label_length():
    got = _budget(_mermaid(3, label="x" * 15))
    assert len(got) == 1 and "15 characters (keep <= 14)" in got[0].message
    assert not _budget(_mermaid(3, label="x" * 14))


def test_reasons_are_combined_in_one_diagnostic():
    got = _budget(_mermaid(11, edges=13, label="y" * 20))
    assert len(got) == 1
    assert got[0].message.count(";") == 2 and "nodes" in got[0].message and "arrows" in got[0].message


def _boxes(n: int, label: str = "") -> str:
    links = " ".join(f"{i}>{i + 1}" for i in range(1, n))
    body = "".join(f"## B{i}\n- x\n" for i in range(n))
    return f"@{n} noemph defaults {links}\n{body}"


def test_connector_nodes_over_budget_fire():
    # connector links are not part of the `@N` grid syntax: use the parsed Slide.links directly
    deck = parse("# S\n" + _boxes(3))
    assert deck.slides[0].links  # the a>b form parses
    from slidemark.budget import _graphs

    assert _graphs(deck.slides[0])[0][0] == 3


def test_connector_nodes_counts_joined_blocks():
    got = _budget(_boxes(11))
    assert len(got) == 1 and got[0].message.startswith("11 nodes")
    assert not _budget(_boxes(9))


def test_accent_shapes_over_budget():
    boxes = "".join(f"## B{i} {{fill=accent}}\n- x\n" for i in range(4))
    got = _budget("@4 noemph defaults 1>2 2>3 3>4\n" + boxes)
    assert len(got) == 1 and "4 accent shapes (keep <= 2)" in got[0].message


def test_accent_shapes_within_budget_quiet():
    boxes = "".join(f"## B{i} {{fill=accent}}\n- x\n" for i in range(2)) + "## C\n- x\n"
    assert not _budget("@3 noemph defaults 1>2 2>3\n" + boxes)


def test_no_diagram_no_diagnostic():
    boxes = "".join(f"## B{i} {{fill=accent}}\n- x\n" for i in range(4))
    assert not _budget("@4 noemph defaults\n" + boxes)


def test_threshold_override_in_style_line():
    assert not _budget(_mermaid(11), header="style: lint.diagram_nodes=12\n\n")
    assert not _budget(_mermaid(11), header="style: layout.diagram-nodes=12\n\n")
    assert _budget(_mermaid(5), header="style: lint.diagram_nodes=4\n\n")
    assert not _budget(_mermaid(11), header="style: lint.diagram_nodes=0\n\n")  # 0 = off


@pytest.mark.parametrize(
    "garbage",
    [
        "```mermaid\n-->|\n```\n",
        "```mermaid\nflowchart\n  A -->|" + "z" * 50 + "| \n```\n",
        "```mermaid\n\x00\x01 ---> ---> ]]\n```\n",
        "@>> a>b>c>\n## A\n- x\n",
        "@9>0 0>9 1>1\n## A\n- x\n",
        "```mermaid\n```\n",
    ],
)
def test_garbage_never_raises(garbage):
    _budget(garbage)


def test_info_does_not_count_as_a_warning(tmp_path, capsys):
    f = tmp_path / "d.md"
    f.write_text(
        "theme: default\nsizes: title=30\n\n# S\n@noemph defaults\n" + _mermaid(11), encoding="utf-8"
    )
    assert main(["build", str(f), "-o", str(tmp_path / "d.pptx")]) == 0
    out = capsys.readouterr()
    text = out.out + out.err
    assert "diagram-budget" in text and "11 nodes" in text
    assert "0 warnings" in text.splitlines()[-1]


def test_build_deck_carries_the_info(tmp_path):
    deck = parse("# S\n" + _mermaid(11))
    build_deck(deck, tmp_path / "x.pptx")
    assert any(d.rule == "diagram-budget" and d.level == "info" for d in deck.diagnostics)
