"""Automatic arrangement v2: grids chosen without `@` tokens, diagram word fit, math / code growth."""

from __future__ import annotations

import pytest

from slidemark.ir import Chart, Code, Container, Raw, Shape, Table, Text
from slidemark.layout import layout_slide, measure
from slidemark.layout.grid import strip_grid_tokens, tree_areas
from slidemark.parser import parse
from slidemark.theme import get_theme
from slidemark.units import EMU_PER_INCH as IN

CHART = '```column {title="T"}\n,Q1,Q2\nA,1,2\n```\n'


def lay(md: str, theme: str = "default", n: int = 0):
    deck = parse(f"theme: {theme}\n\n{md}")
    s = deck.slides[n]
    return layout_slide(s, deck, get_theme(deck.theme), n), deck


def cards(placed):
    return [p for p in placed if isinstance(p.element, Container) and "diagram" not in p.element.classes]


def of(placed, cls):
    return [p for p in placed if isinstance(p.element, cls)]


def boxes(n: int, body: str = "- x") -> str:
    return "".join(f"## B{i}\n{body}\n" for i in range(n))


@pytest.mark.parametrize("n", [2, 3, 4, 5])
def test_boxes_then_visual_are_one_row(n):
    placed, _ = lay(f"# t\n{boxes(n)}@end\n{CHART}")
    cs = cards(placed)
    (ch,) = of(placed, Chart)
    assert len(cs) == n and len({c.y for c in cs}) == 1
    assert ch.y >= cs[0].y + cs[0].h and ch.x == cs[0].x
    assert ch.x + ch.w == cs[-1].x + cs[-1].w  # full width below


def test_six_boxes_then_visual_are_two_rows():
    placed, _ = lay(f"# t\n{boxes(6)}@end\n{CHART}")
    cs = cards(placed)
    assert len({c.y for c in cs}) == 2 and len({c.x for c in cs}) == 3


def test_flow_and_chevron_columns_follow_the_box_count():
    for flag in ("flow", "chevron"):
        placed, _ = lay(f"# t\n@{flag}\n{boxes(4)}@end\n{CHART}")
        row = [
            p
            for p in placed
            if isinstance(p.element, (Container, Shape)) and "diagram" not in p.element.classes
        ]
        row = [p for p in row if getattr(p.element, "shape", "") in ("", "chevron", "rect") and p.w > IN]
        (ch,) = of(placed, Chart)
        tops = {p.y for p in row if p.y < ch.y}
        assert len(tops) == 1, flag
        assert sum(1 for p in row if p.y < ch.y) == 4, flag
        assert ch.w > 0.9 * 12 * IN


def test_three_boxes_first_with_visual_is_aab_aac():
    placed, _ = lay(f"# t\n## A\n- x\n{CHART}## B\n- y\n## C\n- z\n@end")
    a, b, c = cards(placed)
    assert a.h > b.h and a.w > b.w and b.x == c.x and c.y > b.y
    assert a.x + a.w < b.x


def test_three_boxes_first_much_longer_is_aab_aac():
    long = "\n".join(f"- {'long text ' * 6}{i}" for i in range(4))
    placed, _ = lay(f"# t\n## A\n{long}\n## B\n- y\n## C\n- z\n@end")
    a, b, c = cards(placed)
    assert a.w > b.w and c.y > b.y


def test_three_similar_boxes_stay_three_columns():
    placed, _ = lay(f"# t\n{boxes(3)}@end")
    cs = cards(placed)
    assert len({c.y for c in cs}) == 1 and len({c.x for c in cs}) == 3


def test_link_tree_gets_layers():
    placed, _ = lay(f"# t\n@a>b a>c a>d\n{boxes(4)}@end")
    root, *kids = cards(placed)
    assert len({k.y for k in kids}) == 1 and kids[0].y > root.y + root.h
    assert root.x + root.w // 2 == pytest.approx(kids[1].x + kids[1].w // 2, abs=IN * 0.2)


def test_four_short_boxes_one_row_four_long_two_by_two():
    short, _ = lay(f"# t\n{boxes(4)}@end")
    assert len({c.y for c in cards(short)}) == 1
    long = "\n".join(f"- {'long sentence ' * 5}{i}" for i in range(2))
    lng, _ = lay(f"# t\n{boxes(4, long)}@end")
    assert len({c.y for c in cards(lng)}) == 2 and len({c.x for c in cards(lng)}) == 2


def test_cjk_boxes_of_two_bullets_are_two_by_two():
    body = "- 影響：大 / 発生可能性：中\n- 対応：外部パートナー2社と契約済み\n- 期限：来月末"
    placed, _ = lay(f"# t\n{boxes(4, body)}@end", "jp-business")
    assert len({c.x for c in cards(placed)}) == 2


def test_tree_areas_and_strip_tokens():
    assert tree_areas([0, 1, 2, 3], [(0, 1), (0, 2), (0, 3)]) == ".a./bcd"
    assert tree_areas([0, 1, 2], [(0, 1), (1, 2)]) is None  # a chain is not a fan-out
    assert tree_areas([0, 1, 2], [(0, 1), (0, 2)]) == ".aa./bbcc"
    assert tree_areas([0, 1, 2, 3], [(0, 1), (0, 2)]) is None  # block 3 is outside the tree
    assert strip_grid_tokens("4 chevron a>b") == "chevron a>b"
    assert strip_grid_tokens("aab/aac a>b") == "a>b"
    assert strip_grid_tokens("flow") == "flow"


# ---------------------------------------------------------------- diagrams


def test_diagram_nodes_fit_their_longest_word():
    edges = "A[Upload receipt] --> B[OCR]\nB --> C{Confident?}\nC -->|yes| D[Post]\nC -->|no| E[Human review]"
    md = f"# t\n```mermaid\ngraph LR\n{edges}\n```\n"
    placed, _ = lay(md, "midnight")
    shapes = [p for p in placed if isinstance(p.element, Shape) and p.element.paragraphs]
    assert shapes
    for p in shapes:
        words = [w for para in p.element.paragraphs for w in para.plain.split()]
        base = p.style.font_size or 18
        diamond = p.element.shape == "diamond"
        avail = (p.w / 2 if diamond else p.w) / 12700
        for w in words:
            assert measure.text_em(w) * base * p.font_scale <= avail, (w, p.w)


def test_diagram_is_centered_and_callout_hugs_it():
    md = "# t\n```mermaid\ngraph LR\nA[One] --> B[Two]\n```\n> [!tip] after\n"
    placed, _ = lay(md, "midnight")
    card = next(p for p in placed if isinstance(p.element, Container))
    call = next(p for p in placed if isinstance(p.element, Text) and "callout" in p.element.classes)
    title = next(p for p in placed if isinstance(p.element, Text) and p.element.role == "title")
    assert 0 <= call.y - (card.y + card.h) < 0.5 * IN  # right below the diagram
    assert card.y - (title.y + title.h) > 0.8 * IN  # the pair is centered, not top aligned


# ---------------------------------------------------------------- math and code


def test_math_alone_in_a_cell_is_larger():
    placed, _ = lay("# t\n```math\n\\frac{a}{b}\n```\n## Notes\n- one\n")
    (m,) = [p for p in placed if isinstance(p.element, Raw)]
    assert 1.4 <= m.font_scale <= 1.65


def test_math_scale_never_overflows_a_long_equation():
    src = " + ".join(f"x_{i}" for i in range(40))
    placed, _ = lay(f"# t\n```math\n{src}\n```\n## Notes\n- one\n")
    (m,) = [p for p in placed if isinstance(p.element, Raw)]
    assert m.font_scale < 1.6


def test_code_grows_on_a_sparse_slide_but_not_beyond_125_percent():
    placed, _ = lay("# t\n```python\nprint(1)\nprint(2)\n```\n")
    (c,) = of(placed, Code)
    assert 1.0 < c.font_scale <= 1.25 + 1e-9


def test_text_plus_code_gives_the_code_at_least_55_percent_width():
    placed, _ = lay("# t\n- one\n- two\n```python\nprint(1)\n```\n")
    (c,) = of(placed, Code)
    txt = of(placed, Text)[-1]
    assert c.x > txt.x and c.w >= 0.55 * 12.33 * IN
    wide, _ = lay(
        "# t\n- one\n```python\n" + "x = some_function(argument_one, argument_two, three)\n" * 2 + "```\n"
    )
    (c2,) = of(wide, Code)
    assert c2.w >= 0.6 * 12.33 * IN


def test_table_in_boxes_run_is_not_a_cell():
    placed, _ = lay(f"# t\n{boxes(3)}@end\n|a|b|\n|-|-|\n|1|2|\n")
    (t,) = of(placed, Table)
    assert t.y > cards(placed)[0].y
