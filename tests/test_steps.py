"""``@steps``: an arrow row (headings) with an outcome card under every arrow, in the same columns."""

from __future__ import annotations

import pytest
from pptx import Presentation

from slidemark import build
from slidemark.importer import import_pptx
from slidemark.parser import parse

DECK = """# 導入ステップと成果
> 3か月で全店に展開する
@4 steps
## 現状分析
- 全店の業務を棚卸し
- 課題を30件に整理
## 設計
- 標準フローを策定
## 試行
## 全店展開
- 全120店へ順次導入
- 研修を月2回実施
※ 出所: 社内PMO
"""


def _shapes(md: str, tmp_path, name: str = "a.pptx"):
    out = tmp_path / name
    build(md, out)
    return {s.name: s for s in Presentation(str(out)).slides[0].shapes}


def test_parser_makes_one_steps_group_from_the_boxes():
    deck = parse(DECK)
    sl = deck.slides[0]
    assert deck.diagnostics == [] and "steps" not in sl.classes
    (g,) = sl.elements
    assert g.classes == ["plain", "group", "steps"] and g.grid == "4"
    assert [b.title.paragraphs[0].plain for b in g.children] == ["現状分析", "設計", "試行", "全店展開"]
    assert sl.conclusion is None and len(sl.footnotes) == 1


def test_blocks_after_the_steps_stay_below_and_ratios_are_kept():
    md = "# T\n@1:2:1 steps\n## A\n- a\n## B\n- b\n## C\n- c\n@end\n```table\nx,y\n1,2\n```\n"
    sl = parse(md).slides[0]
    assert [e.type for e in sl.elements] == ["container", "table"] and sl.grid == "1x2"
    assert sl.elements[0].grid == "1:2:1"


def test_too_few_steps_warns_and_never_raises():
    for md in ("# T\n@steps\n## Only\n- a\n", "# T\n@steps\nplain text\n", "# T\n@3 steps\n"):
        deck = parse(md)
        assert [d.rule for d in deck.diagnostics] == ["steps-few"], md
        assert "## Heading" in deck.diagnostics[0].hint


def test_unusable_grid_is_replaced_with_a_note():
    deck = parse("# T\n@2x2 steps\n## A\n- a\n## B\n- b\n## C\n- c\n")
    assert [d.rule for d in deck.diagnostics] == ["steps-grid"]
    assert deck.slides[0].elements[0].grid == "3"


def test_cards_sit_under_their_arrows_in_the_same_columns(tmp_path):
    sh = _shapes(DECK, tmp_path)
    arrows = [sh[f"Step {i} arrow"] for i in range(1, 5)]
    cards = {i: sh[f"Step {i} card"] for i in (1, 2, 4)}
    assert "Step 3 card" not in sh  # a step without bullets only shows its arrow
    assert len({a.top for a in arrows}) == 1 and len({a.height for a in arrows}) == 1
    for i, card in cards.items():
        a = arrows[i - 1]
        assert (card.left, card.width) == (a.left, a.width)
        assert card.top >= a.top + a.height  # under the arrow ...
        assert card.top - (a.top + a.height) < 914400 // 2  # ... right under it
    assert len({c.height for c in cards.values()}) == 1  # cards of a row share one height
    foot = next(s for s in sh.values() if s.name.startswith("Footnote"))
    assert max(c.top + c.height for c in cards.values()) <= foot.top
    assert arrows[0].top < cards[1].top < cards[1].top + cards[1].height


def test_cards_grow_down_to_the_conclusion_bar_when_there_is_text(tmp_path):
    md = (
        "# Plan\n> Outcome per stage\n@3 steps\n"
        + "".join(
            f"## Stage {i}\n- first outcome of {i}\n- second outcome of {i}\n- third one\n" for i in (1, 2, 3)
        )
        + "@end\n> Result: 20% effort saved\n"
    )
    sh = _shapes(md, tmp_path)
    card, bar = sh["Step 1 card"], sh["Conclusion"]
    assert bar.top - (card.top + card.height) < 914400 * 0.7  # no dead band between the cards and the bar
    assert card.height > 914400 * 1.5


def test_arrow_text_is_not_smaller_than_the_card_text(tmp_path):
    sh = _shapes(DECK, tmp_path)

    def size(shape) -> float:
        runs = [r for p in shape.text_frame.paragraphs for r in p.runs if r.text.strip()]
        return max(r.font.size.pt for r in runs if r.font.size)

    assert size(sh["Step 1 arrow"]) >= max(size(sh[n]) for n in sh if n.startswith("Text"))


def test_style_tokens_change_the_arrows_and_cards(tmp_path):
    head = "style: steps-arrow.fill=#FF5A1F steps-card.fill=#EEF2FF layout.steps_gap=0.4in\n\n"
    sh = _shapes(head + DECK, tmp_path)
    assert str(sh["Step 1 arrow"].fill.fore_color.rgb) == "FF5A1F"
    assert str(sh["Step 1 card"].fill.fore_color.rgb) == "EEF2FF"
    a, c = sh["Step 1 arrow"], sh["Step 1 card"]
    assert abs((c.top - (a.top + a.height)) - 914400 * 0.4) < 914400 * 0.02


def test_dense_japanese_five_steps_fit_without_warnings(tmp_path):
    step = "## {i}. 市場調査と顧客インタビュー\n- 顧客インタビュー 20社を実施\n- 競合 8社の機能・価格を比較\n"
    md = "theme: jp-business\nlang: ja\n\n# 新規事業の立ち上げプロセスと成果物\n@5 steps\n"
    md += "".join(step.format(i=i) for i in range(1, 6))
    deck = parse(md)
    out = tmp_path / "a.pptx"
    build(md, out)
    assert [d for d in deck.diagnostics if d.level != "info"] == []
    sh = {s.name: s for s in Presentation(str(out)).slides[0].shapes}
    right = max(s.left + s.width for n, s in sh.items() if n.endswith(("arrow", "card")))
    assert right <= Presentation(str(out)).slide_width


def test_round_trip_gives_steps_back(tmp_path):
    a = tmp_path / "a.pptx"
    build(DECK, a)
    text, _ = import_pptx(a, tmp_path)
    assert "@4 steps" in text and "## 試行" in text and "- 研修を月2回実施" in text
    b = tmp_path / "b.pptx"
    build(text, b)
    n1 = {s.name for s in Presentation(str(a)).slides[0].shapes}
    n2 = {s.name for s in Presentation(str(b)).slides[0].shapes}
    assert {n for n in n1 if n.startswith("Step")} == {n for n in n2 if n.startswith("Step")}


@pytest.mark.parametrize(
    "md",
    [
        "# T\n@steps\n## A\n## B\n",
        "# T\n@steps\n## A\n- x\n## B\n- y\n@end\n@2\n## C\n- z\n## D\n- w\n",
        "# T\n@steps chevron\n## A {.danger icon=check}\n- x\n## B {.kpi}\n1\n",
        "# T\n@2 steps\n## A\n### sub\n- x\n## B\n```mermaid\ngraph LR\nA-->B\n```\n",
        "# T\n@9 steps\n## A\n- x\n## B\n- y\n",
        "# T\n@steps a>b\n## A\n- x\n## B\n- y\n",
    ],
)
def test_fuzz_never_raises(md, tmp_path):
    parse(md)
    build(md, tmp_path / "f.pptx")
