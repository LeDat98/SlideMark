"""Defects that used to pass `slidemark check` silently (docs/AGENT_COST.md, work package 4).

Each test asserts geometry from the layout output, so a regression shows up without looking at a render.
"""

from __future__ import annotations

from slidemark.ir import Shape, Table, Text
from slidemark.layout import layout_slide
from slidemark.parser import parse_deck
from slidemark.template import deck_theme
from slidemark.units import EMU_PER_PT, slide_size, to_emu

W, _H = slide_size("16:9")


def lay(src: str, index: int = 0):
    deck = parse_deck(src)
    theme, _ = deck_theme(deck)
    placed = layout_slide(deck.slides[index], deck, theme, index)
    return deck, theme, placed


# ---- D1: title + bare `##` lines is a cover / section divider, the `##` text is the subtitle

COVER = "# Quarterly Review\n## Q3 2026 results and outlook\n\n# Revenue grew 18%\n> Growth\n- point\n"


def test_title_with_bare_heading_is_a_cover():
    deck = parse_deck(COVER)
    s = deck.slides[0]
    assert s.layout == "cover"
    assert s.elements == []
    assert s.subtitle is not None and s.subtitle.paragraphs[0].plain == "Q3 2026 results and outlook"
    assert deck.slides[1].layout is None  # the content slide is untouched


def test_bare_heading_after_the_first_slide_is_a_section_divider():
    deck = parse_deck("# A\n- x\n\n# Part two\n## Next steps\n## Owners\n")
    s = deck.slides[1]
    assert s.layout == "section" and s.elements == []
    assert s.subtitle is not None and len(s.subtitle.paragraphs) == 2


def test_cover_with_header_colors_and_no_theme():
    deck = parse_deck("theme: none\ncolors: bg=#FFFFFF fg=#1F2937 primary=#0F766E\n\n# Title\n## Sub\n")
    assert deck.slides[0].layout == "cover" and deck.slides[0].subtitle is not None


def test_heading_with_body_stays_a_box():
    deck = parse_deck("# Deck\n## Only\n- x\n- y\n")
    assert deck.slides[0].layout is None and deck.slides[0].elements


def test_cover_has_no_card_in_layout():
    _, _, placed = lay(COVER)
    assert not [p for p in placed if type(p.element).__name__ == "Container"]


# ---- D2: a table that is the only body block spans the content width

TABLE = (
    "# Revenue grew 18% year over year\n> Growth came from the enterprise segment\n"
    "```table\nSegment,Q3 2025,Q3 2026,Change\nEnterprise,4.2,5.6,+33%\nSMB,3.1,3.2,+3%\n```\n"
    "> Enterprise now drives two thirds of growth\n"
)


def _content_width(theme) -> int:
    return W - 2 * to_emu(theme.margin_x)


def test_lone_table_spans_the_content_width():
    _, theme, placed = lay(TABLE)
    (t,) = [p for p in placed if isinstance(p.element, Table)]
    assert abs(t.w - _content_width(theme)) <= 2
    assert sum(t.element.attrs["_col_w"]) == t.w
    bar = next(p for p in placed if isinstance(p.element, Text) and p.element.role == "conclusion")
    assert t.x == bar.x and t.x + t.w == bar.x + bar.w  # edges align with the conclusion bar


def test_table_rows_do_not_balloon():
    _, theme, placed = lay(TABLE)
    (t,) = [p for p in placed if isinstance(p.element, Table)]
    size = (t.style.font_size or 14) * t.font_scale * EMU_PER_PT
    spread = 1 + theme.layout.body_spread_max  # the vertical fill may still add its share on top
    assert max(t.element.attrs["_row_h"]) <= theme.layout.table_row_max_em * size * spread * 1.02


def test_explicit_column_widths_still_win():
    deck = parse_deck(TABLE)
    tb = next(e for e in deck.slides[0].elements if isinstance(e, Table))
    tb.col_widths = ["60pt", "60pt", "60pt", "60pt"]
    theme, _ = deck_theme(deck)
    placed = layout_slide(deck.slides[0], deck, theme, 0)
    (t,) = [p for p in placed if isinstance(p.element, Table)]
    assert abs(t.w - _content_width(theme)) <= 2  # explicit widths are proportions of the full width


# ---- D3: free text after a KPI row is body text under the row, not a tiny list far below it

KPI = """theme: jp-business
lang: ja

# 主要KPIサマリー
> 全指標で前年を上回る
## 売上 {.kpi}
12.4億円
前年比 +8%
## 営業利益 {.kpi}
2.1億円
前年比 +12%
## 顧客数 {.kpi}
1,240社
前年比 +15%
## 解約率 {.kpi}
2.1%
前年比 -0.3pt
@end
- 大型案件の受注が売上を牽引
- 営業利益率は17%に改善
- 解約率は目標の2.5%を下回る
"""


def test_list_after_kpi_row_is_body_size_under_the_row():
    deck, theme, placed = lay(KPI)
    body_pt = theme.sizes["body"]
    lead = next(p for p in placed if isinstance(p.element, Text) and p.element.role == "lead")
    cards = [p for p in placed if type(p.element).__name__ == "Container"]
    lst = next(p for p in placed if isinstance(p.element, Text) and p.element.paragraphs[0].marker)
    assert len(cards) == 4
    assert (lst.style.font_size or 0) * lst.font_scale >= body_pt  # never smaller than the deck body size
    assert lst.w >= 0.95 * _content_width(theme)  # a full-width row
    row_bottom = max(c.y + c.h for c in cards)
    assert lst.y >= row_bottom  # under the KPI row
    assert lst.y - row_bottom <= 0.5 * 914400  # ... directly (no dead band between the two)
    # no dead band between the lead and the KPI row
    assert min(c.y for c in cards) - (lead.y + lead.h) <= 0.6 * 914400


def test_kpi_row_and_list_fill_the_body():
    deck, theme, placed = lay(KPI)
    body_top = min(p.y for p in placed if type(p.element).__name__ == "Container")
    bottom = max(p.y + p.h for p in placed if type(p.element).__name__ in ("Container", "Text"))
    body_h = (7.5 * 914400) - body_top - 0.3 * 914400
    assert (bottom - body_top) >= 0.5 * body_h  # not half empty


def test_kpi_text_unchanged_without_free_text():
    _, _, placed = lay(KPI.split("@end")[0])
    nums = [p for p in placed if isinstance(p.element, Text) and p.element.paragraphs[0].plain[:1].isdigit()]
    assert nums and all(p.font_scale == 1.0 for p in nums)


# ---- D4: chevron text uses the chevron interior and no word breaks

CHEV = """theme: none
colors: bg=#FFFFFF fg=#1F2937 primary=#0F766E accent=#F59E0B
lang: vi

# Quy trình triển khai dự án
@chevron
## Khảo sát
- Phỏng vấn người dùng
## Thiết kế
- Kiến trúc hệ thống
## Phát triển
- Lập trình và kiểm thử
## Triển khai
- Đưa vào vận hành
## Đánh giá
- Đo lường hiệu quả
"""


def _text_w(p, theme) -> float:
    adj = p.element.attrs.get("adj", theme.layout.chevron_adj)
    return p.w - 2 * adj * min(p.w, p.h) - 2 * to_emu(theme.layout.chevron_pad)


def _longest_word_pt(p) -> float:
    from slidemark.layout import measure

    size = (p.style.font_size or 18) * p.font_scale
    words = [w for para in p.element.paragraphs for w in para.plain.split()]
    return max(measure.text_em(w, bold=True) for w in words) * size


def test_chevron_text_uses_the_interior_and_words_fit():
    deck, theme, placed = lay(CHEV)
    chevs = [p for p in placed if isinstance(p.element, Shape) and p.element.shape == "chevron"]
    assert len(chevs) == 5
    for p in chevs:
        avail = _text_w(p, theme)
        assert avail >= 0.55 * p.w  # the text frame is not half the chevron
        assert _longest_word_pt(p) * EMU_PER_PT <= avail  # no word is broken
    assert not [d for d in deck.diagnostics if d.rule == "chevron-word-break"]
    assert max(p.h for p in chevs) <= 0.33 * 6858000  # not 2/5 of the slide height


def test_chevron_word_break_is_flagged_when_nothing_fits():
    names = "\n".join(f"## Internationalizationandlocalization{i}\n- x" for i in range(5))
    deck, _, _ = lay(f"# Steps\n@chevron\n{names}\n")
    hit = [d for d in deck.diagnostics if d.rule == "chevron-word-break"]
    assert hit and "flow" in hit[0].hint


def test_katakana_run_is_one_word_for_chevrons():
    from slidemark.layout.engine import _longest_word_em
    from slidemark.parser import parse_deck as pd

    deck = pd("# T\n@chevron\n## コンテンツマネジメント基盤\n- x\n## B\n- y\n")
    box = deck.slides[0].elements[0]
    paras = [*box.title.paragraphs, *[p for c in box.children for p in c.paragraphs]]
    assert _longest_word_em(paras) >= 11.0  # the 11-character katakana run is unbreakable


def test_rendered_chevron_uses_the_layout_point_depth(tmp_path):
    from pptx import Presentation

    from slidemark import build

    src = tmp_path / "d.md"
    src.write_text(CHEV, encoding="utf-8")
    build(src, tmp_path / "d.pptx")
    shapes = [s for s in Presentation(str(tmp_path / "d.pptx")).slides[0].shapes if s.has_text_frame]
    chev = [s for s in shapes if s.shape_type is not None and "Khảo sát" in s.text_frame.text]
    assert chev and 0.1 < chev[0].adjustments[0] < 0.3  # flatter than the token default 0.3
