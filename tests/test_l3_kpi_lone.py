"""A KPI row alone in the body keeps content-sized cards at the optical center (never full-height slabs)."""

from __future__ import annotations

import random

import pytest

from slidemark.ir import Container, Text

from .test_layout_l3_fill import EX, cards, lay, role

JA = """theme: jp-business
lang: ja

# 主要指標の推移
> 応答率は改善、解決率は横ばい
## 応答率 {.kpi}
92%
前期比 +7pt
## 平均待ち時間 {.kpi}
38秒
前期比 -22秒
## 一次解決率 {.kpi}
71%
前期比 ±0pt
## 顧客満足度 {.kpi}
3.9
前期比 +0.2
"""
EN3 = """# Q3 results
## Revenue {.kpi}
$4.2M
+12% QoQ
## Margin {.kpi}
38%
+2pt
## Churn {.kpi}
2.1%
-0.4pt
"""
EN_BAR = EN3 + "> Growth is healthy.\n"
EMU = 914400


def _value_pt(placed):
    (b,) = [p for p in role(placed, "body")][:1]
    return b.element.paragraphs[0].style.font_size * b.font_scale


@pytest.mark.parametrize("src", [JA, EN3, EN_BAR])
def test_lone_kpi_cards_are_content_sized_and_centered(src):
    placed, _, theme = lay("", 1, src=src)
    off, _, _ = lay("", 1, src=src, kpi_lone=False)
    cs = cards(placed)
    assert len(cs) >= 3 and len({c.h for c in cs}) == 1 and len({c.y for c in cs}) == 1
    body_top = max(
        p.y + p.h for p in placed if isinstance(p.element, Text) and p.element.role in ("lead", "title")
    )
    bars = role(placed, "conclusion")
    body_bottom = bars[0].y if bars else 7.5 * EMU
    assert cs[0].h < cards(off)[0].h
    assert cs[0].h <= 0.5 * (body_bottom - body_top) + 1
    assert _value_pt(placed) > _value_pt(off)
    mid = cs[0].y + cs[0].h / 2
    if bars:
        assert 0 < bars[0].y - (cs[0].y + cs[0].h) <= 0.5 * EMU  # one gutter above the bar
    else:
        assert body_top < cs[0].y and cs[0].y + cs[0].h < body_bottom
        assert abs(mid - (body_top + body_bottom) / 2) < 0.15 * (body_bottom - body_top)
    for c in cs:  # label, number and caption stay inside the card, stacked in order
        heads = [p for p in role(placed, "heading") if c.x <= p.x < c.x + c.w]
        (b,) = [p for p in role(placed, "body") if c.x <= p.x < c.x + c.w]
        assert c.y < heads[0].y < b.y and b.y + b.h <= c.y + c.h


def test_value_never_wraps_cjk():
    placed, _, _ = lay("", 1, src=JA)
    (b, *_) = role(placed, "body")
    assert _value_pt(placed) * 3.2 <= b.w / 12700  # 3.2 em covers "38秒" with margin


def test_kpi_followed_by_other_blocks_is_unchanged():
    cases = [
        ("11-jp-consulting.md", 5),
        ("16-jp-strategy.md", 7),
        ("04-jp-kpi.md", 1),
    ]
    for name, n in cases:
        if not (EX / name).exists():
            continue
        a, _, _ = lay(name, n)
        b, _, _ = lay(name, n, kpi_lone=False)
        assert [(p.x, p.y, p.w, p.h) for p in a] == [(p.x, p.y, p.w, p.h) for p in b]


def test_kpi_with_chart_unchanged():
    src = "# T\n## A {.kpi}\n12%\nup\n## B {.kpi}\n3\nflat\n\n```chart bar\nx,y\na,1\nb,2\n```\n"
    a, _, _ = lay("", 1, src=src)
    b, _, _ = lay("", 1, src=src, kpi_lone=False)
    assert [(p.x, p.y, p.w, p.h) for p in a] == [(p.x, p.y, p.w, p.h) for p in b]


def test_fuzz_never_raises():
    rnd = random.Random(7)
    vals = ["92%", "", "¥1,234,567,890,123", "売上高 前年比", "3.9", "あ" * 40]
    for _ in range(25):
        n = rnd.randint(1, 6)
        parts = [
            f"## {rnd.choice(vals)} {{.kpi}}\n{rnd.choice(vals)}\n{rnd.choice(vals)}\n" for _ in range(n)
        ]
        src = "# T\n" + "".join(parts) + rnd.choice(["", "> bar\n", "[^1]: note\n"])
        placed, _, _ = lay("", 1, src=src)
        assert all(isinstance(p.x, int) for p in placed)
    assert Container
