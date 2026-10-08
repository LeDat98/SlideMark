"""KPI rows: ratio grids give exact widths, a wider card gets a bigger number (hero), KPI rows do not float,
and the `>` lead reads as the slide's message (size / colour per preset)."""

from __future__ import annotations

import random

import pytest
from pptx import Presentation

from slidemark.build import build_deck
from slidemark.layout import layout_slide, measure
from slidemark.layout.grid import Rect, cell_rects, parse_spec
from slidemark.parser import parse
from slidemark.template import deck_theme
from slidemark.theme import LayoutTokens
from slidemark.units import EMU_PER_PT, to_emu

JA = """theme: jp-business
lang: ja

# 2027年度の経営目標
> 売上・利益ともに過去最高を目指す
{grid}## 売上高 {{.kpi{hero}}}
1,280億円
前年比 +8%
## 営業利益 {{.kpi}}
96億円
前年比 +12%
## 営業利益率 {{.kpi}}
7.5%
+0.3pt
## ROE {{.kpi}}
9.0%
+0.8pt
{tail}"""
EN = """# Q3 results
> Revenue and margin both beat plan
{grid}## Revenue {{.kpi{hero}}}
$4.2M
+12% QoQ
## Margin {{.kpi}}
38%
+2pt
## Churn {{.kpi}}
2.1%
-0.4pt
{tail}"""


def ja(grid="", hero="", tail=""):
    return JA.format(grid=grid, hero=hero, tail=tail)


def en(grid="", hero="", tail=""):
    return EN.format(grid=grid, hero=hero, tail=tail)


def lay(md: str, **tokens):
    deck = parse(md)
    theme, _ = deck_theme(deck, ".")
    if tokens:
        theme = theme.model_copy(deep=True)
        theme.layout = theme.layout.model_copy(update=tokens)
    measure.set_tokens(theme.layout)
    placed = layout_slide(deck.slides[0], deck, theme, 0)
    return placed, deck, theme


def kpi_cards(placed):
    return [p for p in placed if "kpi" in getattr(p.element, "classes", [])]


def values(placed):
    """(x, text width, value size pt) of the number of every KPI card, left to right."""
    out = []
    cards = kpi_cards(placed)
    for p in placed:
        el = p.element
        if getattr(el, "role", None) != "body" or not el.paragraphs or not el.paragraphs[0].style:
            continue
        if any(c.x <= p.x and p.x + p.w <= c.x + c.w and c.y <= p.y <= c.y + c.h for c in cards):
            out.append((p.x, p.w, el.paragraphs[0].style.font_size * p.font_scale))
    return sorted(out)


def widths(placed):
    return [c.w for c in sorted(kpi_cards(placed), key=lambda c: c.x)]


# --------------------------------------------------------------------------- ratio grids


def test_ratio_grid_keeps_exact_ratios_when_the_track_snap_would_bend_them():
    gs = parse_spec("2:1:1:1", 4)
    ws = [r.w for r in cell_rects(gs, 4, Rect(0, 0, 12_000_000, 100), 0)]
    assert ws[0] == pytest.approx(2 * ws[1], abs=2) and ws[1] == pytest.approx(ws[2], abs=2) == pytest.approx(
        ws[3], abs=2
    )


def test_ratio_grid_still_snaps_when_the_snap_is_close():
    for spec, tracks in (("1:2", (4, 8)), ("3:2", (7, 5)), ("2:1:1", (6, 3, 3))):
        gs = parse_spec(spec, len(tracks))
        rs = cell_rects(gs, len(tracks), Rect(0, 0, 12_000_000, 100), 0)
        assert [round(r.w / 1_000_000) for r in rs] == list(tracks), spec


def test_ratio_grid_on_a_kpi_row_gives_the_first_card_twice_the_width():
    placed, deck, _ = lay(ja("@2:1:1:1\n"))
    w = widths(placed)
    assert len(w) == 4 and w[0] == pytest.approx(2 * w[1], rel=0.01) and w[1] == pytest.approx(w[3], rel=0.01)
    assert not [d for d in deck.diagnostics if d.level in ("warning", "error")]


# --------------------------------------------------------------------------- hero


def test_wider_card_gets_a_bigger_number_that_never_wraps():
    placed, _, theme = lay(ja("@2:1:1:1\n"))
    vals = values(placed)
    assert vals[0][2] > 1.3 * vals[1][2] > 0  # the hero number is clearly bigger
    assert vals[1][2] == pytest.approx(vals[2][2], rel=0.02)
    texts = {p.x: p for p in placed if getattr(p.element, "role", None) == "body" and p.element.paragraphs}
    for x, w, pt in vals:
        plain = texts[x].element.paragraphs[0].plain
        assert measure.text_em(plain, bold=True) * pt <= w / EMU_PER_PT  # one line


def test_hero_class_is_the_short_form_of_a_ratio_row():
    a, _, _ = lay(en(hero=" .hero"))
    b, _, _ = lay(en("@2:1:1\n"))
    wa = widths(a)
    assert wa[0] == pytest.approx(2 * wa[1], rel=0.05) and wa == pytest.approx(widths(b), abs=2)
    assert values(a)[0][2] > values(a)[1][2]


def test_hero_weight_is_a_layout_token_and_explicit_grids_win():
    placed, _, _ = lay(en(hero=" .hero"), kpi_hero_w=3.0)
    w = widths(placed)
    assert w[0] == pytest.approx(3 * w[1], rel=0.01)
    off, _, _ = lay(en(hero=" .hero"), kpi_hero_w=1.0)
    assert len({c for c in widths(off)}) == 1  # off: equal cards
    eq, _, _ = lay(en("@3\n", hero=" .hero"))
    assert len(set(widths(eq))) == 1  # the explicit grid wins over the class


def test_value_scale_is_a_token():
    table = "\n| a | b |\n|-|-|\n| 1 | 2 |\n"
    on, _, _ = lay(ja("@2:1:1:1\n", tail=table), kpi_grow_max=1.0)
    flat, _, _ = lay(ja("@2:1:1:1\n", tail=table), kpi_grow_max=1.0, kpi_value_exp=0.0)
    ratio = lambda p: values(p)[0][2] / values(p)[1][2]  # noqa: E731
    assert ratio(on) > ratio(flat) + 0.15


def test_hero_survives_a_list_under_the_row_and_keeps_the_ratio():
    placed, _, _ = lay(ja("@2:1:1:1\n", tail="@end\n- 海外売上が牽引\n- 原価低減で利益率が改善\n"))
    w = widths(placed)
    assert w[0] == pytest.approx(2 * w[1], rel=0.01)
    vals = values(placed)
    assert vals[0][2] > vals[1][2]


def test_explicit_sizes_are_untouched():
    css = "```css\n.kpi { font-size: 20pt }\n```\n"
    placed, _, _ = lay(en("@2:1:1\n").replace("# Q3", css + "# Q3", 1))
    assert {round(v[2], 1) for v in values(placed)} == {20.0}


# --------------------------------------------------------------------------- no floating


@pytest.mark.parametrize(
    "md",
    [
        ja(),
        ja("@2:1:1:1\n"),
        en(),
        en(tail="\n> Growth is healthy.\n"),
        ja("@2:1:1:1\n", tail="\n> 過去最高益\n"),
    ],
    ids=["ja", "ja-hero", "en", "en-bar", "ja-hero-bar"],
)
def test_kpi_row_uses_the_body_height(md):
    # the old share (kpi_to_body: test_sparse_wave2.py); no deck-wide ceiling (grow_max: test_grow_max.py)
    placed, _, theme = lay(md, kpi_to_body=False, grow_max=3.0)
    lt = theme.layout
    cs = kpi_cards(placed)
    top = max(p.y + p.h for p in placed if getattr(p.element, "role", None) in ("title", "lead"))
    bars = [p for p in placed if getattr(p.element, "role", None) == "conclusion"]
    bottom = bars[0].y - to_emu(theme.gap) if bars else 7.5 * 914400 - to_emu(theme.margin_y)
    body = bottom - top
    assert cs[0].h >= lt.kpi_lone_min_h * body * 0.95  # no longer a thin strip
    assert cs[0].h <= lt.kpi_lone_h * body + 1
    # the number is bigger than the old 1.35x cap allowed (jp-business: 26pt base, default: 36pt)
    base = 17.9 if "jp-business" in md else 36
    assert max(v[2] for v in values(placed)) > 1.5 * base * (0.65 if "jp-business" in md else 1)


def test_default_theme_three_kpis_fill_more_than_before():
    placed, _, _ = lay(en(), grow_max=3.0)  # (the deck-wide ceiling, layout.grow_max, is test_grow_max.py)
    old, _, _ = lay(
        en(), grow_max=3.0, kpi_lone_value_grow=1.35, kpi_lone_value_max_pt=66.0, kpi_lone_min_h=0.0
    )
    assert max(v[2] for v in values(placed)) > max(v[2] for v in values(old))
    assert kpi_cards(placed)[0].h > kpi_cards(old)[0].h


def test_render_reopens_with_the_planned_widths_and_sizes(tmp_path):
    deck = parse(ja("@2:1:1:1\n"))
    out = tmp_path / "o.pptx"
    build_deck(deck, out, tmp_path)
    slide = Presentation(str(out)).slides[0]
    cards = sorted((s for s in slide.shapes if s.name.startswith("Card")), key=lambda s: s.left)
    assert [round(c.width / cards[1].width, 2) for c in cards] == [2.0, 1.0, 1.0, 1.0]
    sizes = []
    for sh in slide.shapes:
        if sh.name.startswith("Text") and sh.has_text_frame:
            sizes.append(sh.text_frame.paragraphs[0].runs[0].font.size.pt)
    assert sizes[0] > 1.3 * sizes[1] and sizes[1] == pytest.approx(sizes[2], rel=0.02)


def test_fuzz_hero_never_raises():
    rnd = random.Random(11)
    vals = ["92%", "", "¥1,234,567,890,123", "売上高 前年比", "3.9", "あ" * 40, "- x"]
    for _ in range(40):
        n = rnd.randint(1, 6)
        classes = [rnd.choice([".kpi", ".kpi .hero", ".kpi .hero .danger", ".hero"]) for _ in range(n)]
        grid = rnd.choice(["", "@2:1:1\n", "@3:1\n", "@2:1:1:1:1:1\n", "@2x2\n", "@1:0\n"])
        body = "".join(
            f"## {rnd.choice(vals)} {{{c}}}\n{rnd.choice(vals)}\n{rnd.choice(vals)}\n" for c in classes
        )
        tail = rnd.choice(["", "\n> done\n", "@end\n- a\n- b\n"])
        md = f"# T\n> lead\n{grid}{body}{tail}"
        deck = parse(md)
        theme, _ = deck_theme(deck, ".")
        layout_slide(deck.slides[0], deck, theme, 0)
        assert not [d for d in deck.diagnostics if d.rule == "layout-error"], md


# --------------------------------------------------------------------------- the lead reads as the message


@pytest.mark.parametrize("name", ["default", "midnight", "jp-business"])
def test_lead_is_legible_and_secondary_only_to_the_title(name, tmp_path):
    md = f"theme: {name}\n\n# Title\n> The key message of the slide\n- a point\n- another point\n"
    deck = parse(md)
    theme, _ = deck_theme(deck, ".")
    sizes = theme.sizes
    assert theme.lead_color == "fg"  # the body ink, not muted grey
    assert sizes["lead"] > sizes["body"]  # more than body text
    assert sizes["lead"] < sizes["title"]  # but the title stays first
    out = tmp_path / "o.pptx"
    build_deck(deck, out, tmp_path)
    assert not [d for d in deck.diagnostics if d.rule == "contrast"]
    slide = Presentation(str(out)).slides[0]
    lead = next(s for s in slide.shapes if s.name == "Lead")
    run = lead.text_frame.paragraphs[0].runs[0]
    assert run.font.size.pt >= sizes["lead"] - 0.01
    assert str(run.font.color.rgb) == theme.hexval("fg").lstrip("#").upper()


def test_lead_size_and_color_stay_overridable():
    md = "theme: jp-business\nsizes: lead=20\nstyle: lead.color=primary\n\n# T\n> Key\n- a\n"
    deck = parse(md)
    theme, _ = deck_theme(deck, ".")
    assert theme.sizes["lead"] == 20
    placed = layout_slide(deck.slides[0], deck, theme, 0)
    lead = next(p for p in placed if getattr(p.element, "role", None) == "lead")
    assert lead.style.font_size * lead.font_scale >= 20 - 0.01


def test_layout_tokens_defaults_are_sane():
    lt = LayoutTokens()
    assert lt.kpi_hero_w > 1.0 and 0 < lt.kpi_value_exp <= 1.0
    assert 0 < lt.kpi_lone_min_h < lt.kpi_lone_h <= 1.0


def test_parser_keeps_kpi_and_hero_classes_and_the_ratio_grid():
    deck = parse(en("@2:1:1\n", hero=" .hero"))
    sl = deck.slides[0]
    assert sl.elements[0].classes == ["kpi", "hero"] and sl.grid == "2:1:1"
    assert not [d for d in deck.diagnostics if d.level in ("warning", "error")]
