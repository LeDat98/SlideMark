"""A short table that is the only body block grows its text first, then its rows (<= table_row_max_em)."""

from __future__ import annotations

from slidemark.ir import Table
from slidemark.layout import layout_slide
from slidemark.parser import parse
from slidemark.template import deck_theme

EMU_PT = 12700

JP = """theme: jp-business
lang: ja

# 投資対効果
> 3年で投資を回収できる
```table {align=lrrr}
項目,1年目,2年目,3年目
投資額,4.0億円,0.5億円,0.5億円
削減効果,1.2億円,2.1億円,2.4億円
累計収支,-2.8億円,-1.2億円,0.7億円
```
> 第1期として東日本センターから着手する
"""
DEFAULT = "# Plan\n```table\nItem,Q1,Q2,Q3\nA,1,2,3\nB,4,5,6\nC,7,8,9\n```\n"
FULL = "# Plan\n```table\n" + "Item,Q1,Q2,Q3\n" + "".join(f"R{i},{i},{i},{i}\n" for i in range(10)) + "```\n"


def table_item(md: str, head: str = ""):
    deck = parse(head + md)
    theme, _ = deck_theme(deck)
    items = layout_slide(deck.slides[0], deck, theme, 0)
    tabs = [p for p in items if isinstance(p.element, Table)]
    assert tabs
    p = tabs[0]
    return p, (p.style.font_size or 14) * p.font_scale, theme


def test_jp_table_text_grows_and_rows_stay_capped():
    p, size, theme = table_item(JP)
    assert size >= 14
    cap = theme.layout.table_row_max_em * size * EMU_PT
    assert max(p.element.attrs["_row_h"]) <= cap + 2


def test_default_table_text_at_least_body_size_and_rows_capped():
    p, size, theme = table_item(DEFAULT)
    assert size >= theme.sizes["body"]
    assert max(p.element.attrs["_row_h"]) <= theme.layout.table_row_max_em * size * EMU_PT + 2


def test_text_cap_follows_tokens():
    _, size, theme = table_item(JP, "style: layout.table_free=off\n\n")  # the wave-2 pass has its own cap
    assert size <= theme.sizes["body"] * theme.layout.table_text_max + 1e-6
    _, free, _ = table_item(JP)
    assert size < free <= theme.layout.table_free_text_max_pt + 1e-6
    _, off, _ = table_item(JP, "style: layout.table_text_step=0\n\n")
    assert off < size  # growth off: only the regular table growth remains


def test_explicit_sizes_table_is_kept_from_further_growth():
    _, base, _ = table_item(JP, "style: layout.table_text_step=0\n\n")
    _, size, _ = table_item(JP.replace("lang: ja", "lang: ja\nsizes: table=10.5"))
    assert size <= base + 1e-6


def test_css_font_size_is_explicit():
    p, size, _ = table_item("```css\ntd { font-size: 12pt }\nth { font-size: 12pt }\n```\n\n" + DEFAULT)
    _, base, _ = table_item(DEFAULT)
    assert size < base  # explicit cell sizes bypass table growth
    cell = p.element.rows[1][0]
    assert cell.style.font_size == 12


def test_full_table_unchanged_by_growth():
    _, on, _ = table_item(FULL)
    _, off, _ = table_item(FULL, "style: layout.table_text_step=0\n\n")
    assert abs(on - off) < 1e-6
