from pathlib import Path

from slidemark.ir import Container, Text
from slidemark.parser import parse

ANSWER = Path(__file__).parent.parent / "bench" / "answers" / "run-2-sonnet" / "14-jp-before-after.md"

EXAMPLE = """# T
> lead
@2 flow
## A
- a
## B
- b
@end
@2 a>b
## K1 {.kpi}
-40%
## K2 {.kpi}
-70%
"""


def rules(deck):
    return [d.rule for d in deck.diagnostics]


def test_two_groups_structure():
    s = parse(EXAMPLE).slides[0]
    assert s.grid == "1x2"
    assert len(s.elements) == 2
    g1, g2 = s.elements
    assert all(isinstance(g, Container) for g in (g1, g2))
    assert g1.classes == ["plain", "group", "flow"] and g1.grid == "2"
    assert g2.classes == ["plain", "group"] and g2.grid == "2"
    assert [c.title.paragraphs[0].plain for c in g1.children] == ["A", "B"]
    assert [c.title.paragraphs[0].plain for c in g2.children] == ["K1", "K2"]
    assert [(lk.src, lk.dst) for lk in g2.links] == [(0, 1)] and g1.links == []
    assert s.lead is not None and s.links == []
    assert "bad-grid" not in rules(parse(EXAMPLE))


def test_same_section_two_grids_still_warn():
    d = parse("# T\n@2\n@3\n## A\n- a\n## B\n- b\n")
    assert "bad-grid" in rules(d)


def test_no_end_no_groups():
    d = parse("# T\n@2\n@3\n## A\n- a\n## B\n- b\n")
    s = d.slides[0]
    assert s.grid == "2" and all(isinstance(e, Container) and "group" not in e.classes for e in s.elements)
    assert "bad-grid" in rules(d)


def test_single_block_group_stays_block_and_slide_flags_apply():
    d = parse(
        "# T\n@2\n## A\n- a\n## B\n- b\n@end\n@1 dense bg=#112233 t=fade\n| a | b |\n|---|---|\n| 1 | 2 |\n"
    )
    s = d.slides[0]
    assert s.grid == "1x2" and "dense" in s.classes
    assert s.background == "#112233" and s.transition == "fade"
    assert isinstance(s.elements[0], Container) and "group" in s.elements[0].classes
    assert not isinstance(s.elements[1], Container)
    assert "bad-grid" not in rules(d)


def test_conclusion_and_footnote_unaffected():
    d = parse(EXAMPLE + "※ src\n> done\n")
    s = d.slides[0]
    assert s.conclusion is not None and isinstance(s.conclusion, Text)
    assert len(s.footnotes) == 1
    assert len(s.elements) == 2 and len(s.elements[1].children) == 2


def test_no_missing_end_hint_on_groups():
    src = "# T\n@2\n## A\n- a\n## B\n- b\n@end\n@2\n## C\n| a |\n|---|\n| 1 |\n## D\n| a |\n|---|\n| 1 |\n"
    assert "missing-end" not in rules(parse(src))


def test_three_groups_and_bad_links():
    src = (
        "# T\n@2\n## A\n- a\n## B\n- b\n@end\n@2 a>c\n## C\n- c\n## D\n- d\n@end\n"
        "@3 flow\n## E\n- e\n## F\n- f\n## G\n- g\n"
    )
    d = parse(src)
    s = d.slides[0]
    assert s.grid == "1x3" and [len(g.children) for g in s.elements] == [2, 2, 3]
    assert "flow" in s.elements[2].classes
    assert "bad-link" in rules(d)


def test_eval_answer():
    s = parse(ANSWER.read_text(encoding="utf-8")).slides[0]
    assert s.grid == "1x2" and s.lead is not None
    assert "kpi" in s.elements[1].children[0].classes


def test_soft_break_lines_are_paragraphs():
    s = parse("# T\n@2\n## K\n5,000\n24% of leads\n## L\n- item\n  more\n- two\n").slides[0]
    k, ln = s.elements
    assert [p.plain for p in k.children[0].paragraphs] == ["5,000", "24% of leads"]
    assert [p.plain for p in ln.children[0].paragraphs if p.marker] == ["item more", "two"]


def test_soft_break_callout_split_lead_stays_one():
    s = parse("# T\n> a\n> b\n@2\n## K\n> [!note]\n> x\n> y\n## L\n- l\n").slides[0]
    assert s.lead is not None and len(s.lead.paragraphs) == 1
    callout = s.elements[0].children[0]
    assert [p.plain for p in callout.paragraphs] == ["x", "y"]
