"""A row of >= 5 chevrons: a bold heading wraps at a space (<= 2 lines), never inside a word."""

from __future__ import annotations

import re

from pptx import Presentation

from slidemark import build
from slidemark.ir import Paragraph, Run
from slidemark.layout import measure
from slidemark.theme import LayoutTokens

SRC = """theme: none
colors: bg=#FFF7ED fg=#431407 primary=#EA580C accent=#C2410C
fonts: heading="Lora" body="Inter"
lang: vi

# Lộ trình ra mắt
@chevron
## Tháng 11
- Thử nghiệm vị
## Tháng 12
- Sản xuất lô đầu
## Tháng 1
- Ra mắt tại TP.HCM
## Tháng 3
- Mở rộng toàn quốc
## Tháng 6
- Đánh giá kết quả
"""

THREE = "\n".join(SRC.splitlines()[:14]) + "\n"  # the same deck with its first three steps

JA = """theme: jp-business
lang: ja

# 新規事業の進め方
@chevron
## マーケティング
- 市場調査
## プロトタイプ
- 試作と検証
## パイロット運用
- 現場での試行
## 本格展開
- 全社へ拡大
## 効果測定
- KPI確認
"""

_KATAKANA = re.compile(r"[゠-ヿ]+")


def _chevrons(tmp_path, src, first):
    f = tmp_path / "c.md"
    f.write_text(src, encoding="utf-8")
    build(f, tmp_path / "c.pptx")
    shapes = [s for s in Presentation(tmp_path / "c.pptx").slides[0].shapes if s.has_text_frame]
    return [s for s in shapes if s.text_frame.text.startswith(first)]


def _text_w(s) -> float:
    adj = s.adjustments[0] if len(s.adjustments) else 0.3
    return (s.width - 2 * adj * min(s.width, s.height)) / 12700  # pt, both point depths removed


def _words(text: str) -> list[str]:
    out = []
    for chunk in text.split():
        out += _KATAKANA.findall(chunk) if measure.has_cjk(chunk) else [chunk]
    return out


def _check_heading(s, size_floor: float) -> float:
    para = s.text_frame.paragraphs[0]
    size = para.runs[0].font.size.pt
    w = _text_w(s)
    assert size >= size_floor, (para.text, size)
    for word in _words(para.text):  # no word is broken: every word fits one line
        assert measure.text_em(word, bold=True) * size * 1.05 <= w, (word, size, w)
    segs = measure.para_segments(Paragraph(runs=[Run(text=para.text, bold=True)]), True)
    lines = measure.count_lines(segs, w / 1.05, size)
    assert lines <= LayoutTokens().chevron_head_lines, (para.text, lines)
    return size


def _body_words_fit(s) -> None:
    size = s.text_frame.paragraphs[1].runs[0].font.size.pt
    for word in _words(s.text_frame.paragraphs[1].text):
        assert measure.text_em(word) * size * 1.05 <= _text_w(s), (word, size)


def test_five_chevrons_wrap_headings_at_a_space_and_keep_the_text_large(tmp_path):
    three = _chevrons(tmp_path, THREE, "Tháng")
    base3 = three[0].text_frame.paragraphs[0].runs[0].font.size.pt
    five = _chevrons(tmp_path, SRC, "Tháng")
    assert len(five) == 5
    sizes = set()
    for s in five:
        sizes.add(_check_heading(s, base3 * 0.78))
        _body_words_fit(s)
    assert len(sizes) == 1  # one text size for the whole row
    assert min(sizes) >= 18  # never below the theme body size (it used to shrink to ~17pt)


def test_five_japanese_chevrons_never_split_a_katakana_word(tmp_path):
    chev = (
        _chevrons(tmp_path, JA, "マーケ")
        + _chevrons(tmp_path, JA, "プロト")
        + _chevrons(tmp_path, JA, "パイロ")
    )
    assert len(chev) == 3
    for s in chev:
        _check_heading(s, 12.0)
        assert s.text_frame.paragraphs[0].text.count("\n") == 0  # a katakana heading is one line
