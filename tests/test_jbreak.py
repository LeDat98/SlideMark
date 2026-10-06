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


CHEVRON_MD = """# 工程

@4 chevron
## 現場の課題を把握する
点検技術者の平均年齢が上昇している
## 施策の優先順位を決める
投資対効果の高い順に実行する
## 全社展開を進める
標準化した手順を拠点へ広げる
## 定着状況を確認する
月次で稼働データを振り返る
"""

GANTT_MD = """theme: jp-business
lang: ja

# 実行スケジュール
{.gantt header=2}
| 施策 | 2027年度 | < | 2028年度 | < | 2029年度 |
|-|-|-|-|-|-|
| ^ | 上期 | 下期 | 上期 | 下期 | 通期 |
| 店舗網再編 | 先行店舗で検証と評価を実施する | 近接店の統合を進める | 売場面積を半分に縮小する | 薬局併設へ業態を転換する | 継続改善を行う |
"""  # noqa: E501


def _shape_brs(path, preset):
    out = []
    for sl in Presentation(str(path)).slides:
        for sh in sl.shapes:
            g = sh._element.find(".//" + qn("a:prstGeom"))
            if g is not None and g.get("prst") == preset:
                out.append((sh, sh._element.findall(".//" + qn("a:br"))))
    return out


@pytest.mark.parametrize(("md", "preset"), [(CHEVRON_MD, "chevron"), (GANTT_MD, "roundRect")])
def test_chevron_and_gantt_text_gets_phrase_breaks(tmp_path, md, preset):
    path = tmp_path / "d.pptx"
    build(md, path)
    shapes = _shape_brs(path, preset)
    assert shapes
    total = 0
    for sh, brs in shapes:
        for br in brs:
            assert br.find(qn("a:rPr")).get("bmk") == jbreak.SOFT_BREAK_MARK
        total += len(brs)
        assert len(sh.text_frame.text.replace("\x0b", "")) == len(sh.text_frame.text) - len(brs)
    assert total, "wrapped CJK text in a chevron/gantt bar should get a phrase break"
    text, _ = import_pptx(path)
    assert "\x0b" not in text and "<br>" not in text


def test_number_unit_stays_together():
    out = measure.bound_texts([Run(text="Non-volatile, 2 ns access")])[0]
    assert "2\u00a0ns" in out
    assert "2\u00a0of" not in measure.bound_texts([Run(text="Take 2 of them")])[0]


def test_binding_wider_than_the_line_is_undone():
    runs = [Run(text="Runs today's models unchanged")]
    bound = measure.bound_texts(runs)
    assert "models\u00a0unchanged" in bound[0]
    narrow = measure.loosen_wide_bindings([r.text for r in runs], bound, 150, 24)
    assert "\u00a0" not in narrow[0]
    wide = measure.loosen_wide_bindings([r.text for r in runs], bound, 900, 24)
    assert wide == bound
    assert measure.loosen_wide_bindings(["a b"], ["a b"], 0, 12) == ["a b"]
