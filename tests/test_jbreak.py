"""Phrase-aware CJK line breaks (layout/jbreak.py): segmentation, soft breaks in the .pptx, importer."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from lxml import etree
from pptx import Presentation
from pptx.oxml.ns import qn

from slidemark import build
from slidemark.importer import import_pptx
from slidemark.importer.read import read_paras
from slidemark.ir import Paragraph, Run, Style
from slidemark.layout import jbreak, measure
from slidemark.theme import LayoutTokens

TEXT = "点検技術者の平均年齢 54歳"


@pytest.fixture(autouse=True)
def _tokens():
    measure.set_tokens(LayoutTokens())
    measure.set_default_font(None)
    yield
    measure.set_tokens(LayoutTokens())
    measure.set_default_font(None)


def _plan(text: str, width: float, size: float = 24):
    return jbreak.plan_breaks(Paragraph(runs=[Run(text=text)]), Style(), width, size, 0.0)


def test_phrase_cuts_are_bunsetsu():
    assert jbreak.phrase_cuts("点検技術者の平均年齢") == [6]
    assert jbreak.phrase_cuts("") == []


def test_plan_moves_the_break_to_a_phrase_boundary():
    plan = _plan(TEXT, 210)  # 8.75 em: the viewer would cut 平均年|齢
    assert plan is not None and plan[0] == {0: [6]}
    plan = _plan(TEXT, 170)  # 7 em: it would cut 点検技術者の平|均
    assert plan is not None and plan[0] == {0: [6]}


def test_no_plan_for_one_line():
    assert _plan("点検技術者の平均", 1000) is None


def test_no_plan_when_lines_would_increase():
    # a phrase longer than the line cannot be packed: no break, lines unchanged
    assert _plan("点検技術者の平均年齢調査結果報告書", 100) is None


def test_non_cjk_badges_and_off_switch():
    assert _plan("plain latin text that wraps in a narrow box", 100) is None
    p = Paragraph(runs=[Run(text="点検技術者の"), Run(text="平均年齢 54歳", highlight="x")])
    assert jbreak.plan_breaks(p, Style(), 210, 24, 0.0) is None
    measure.set_tokens(LayoutTokens(cjk_phrase_break=False))
    assert _plan(TEXT, 210) is None


def test_fuzz_never_raises():
    for t in ("", "あ", "（）", "A" * 80, "日本語" * 40, "x⁠年⁠齢 " * 9, "" * 5 + "年", " 年 "):
        for w in (10, 40, 120, 300):
            _plan(t, w)


MD = """# 課題

## 人手不足
- 点検技術者の平均年齢 54歳
- 若手の採用は年▲8%

## コスト
- 足場・交通規制が費用の 6割

## 品質
- 判定の一致率は 71%
"""


def _slide_brs(path):
    out = []
    for slide in Presentation(str(path)).slides:
        out += slide._element.findall(".//" + qn("a:br"))
    return out


def test_pptx_has_marked_soft_breaks(tmp_path):
    path = tmp_path / "d.pptx"
    build(MD, path)
    brs = _slide_brs(path)
    assert brs, "the narrow cards should get phrase breaks"
    for br in brs:
        assert br.find(qn("a:rPr")).get("bmk") == jbreak.SOFT_BREAK_MARK
    shapes = [sh for sl in Presentation(str(path)).slides for sh in sl.shapes if sh.has_text_frame]
    paras = [
        p.text.replace("\u2060", "").replace("\x0b", "") for sh in shapes for p in sh.text_frame.paragraphs
    ]
    assert TEXT in paras  # a break adds no text


def test_import_strips_inserted_breaks_and_is_stable(tmp_path):
    path = tmp_path / "d.pptx"
    build(MD, path)
    text, _ = import_pptx(path)
    assert "\\\n" not in text and "<br>" not in text
    again = tmp_path / "again.pptx"
    build(text, again)
    text2, _ = import_pptx(again)
    assert text == text2
    assert len(_slide_brs(again)) == len(_slide_brs(path))


def test_import_keeps_user_breaks_drops_ours():
    xml = (
        '<p:txBody xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:p>'
        "<a:r><a:t>一行目</a:t></a:r><a:br/><a:r><a:t>二行目</a:t></a:r>"
        '<a:br><a:rPr bmk="sm"/></a:br><a:r><a:t>三行目</a:t></a:r></a:p></p:txBody>'
    )
    paras, _ = read_paras(etree.fromstring(xml), SimpleNamespace(slide_index={}), None)
    assert [r.text for r in paras[0].runs] == ["一行目", "\n", "二行目", "三行目"]
