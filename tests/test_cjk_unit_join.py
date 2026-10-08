"""Japanese numbers stay with their units (U+2060); bool tokens parse off/on."""

from __future__ import annotations

import zipfile

import pytest

from slidemark import build
from slidemark.importer import import_pptx
from slidemark.layout import measure
from slidemark.theme import LayoutTokens, RenderTokens

WJ = "⁠"


@pytest.mark.parametrize(
    ("src", "want"),
    [
        ("平均38万円", f"平均38{WJ}万{WJ}円"),
        ("54歳", f"54{WJ}歳"),
        ("12億円", f"12{WJ}億{WJ}円"),
        ("▲8%", f"▲{WJ}8%"),
        ("+3.5％増", f"+{WJ}3.5{WJ}％増"),
        ("¥1,200万", f"¥{WJ}1,200{WJ}万"),
        ("年", "年"),
        ("38万円", f"38{WJ}万{WJ}円"),
    ],
)
def test_join_cjk_units(src, want):
    assert measure.join_cjk_units(src) == want


def test_group_is_one_unbreakable_unit():
    t = measure.join_cjk_units("あ" * 6 + "38万円")
    units = measure._units([(t, False, False)])
    assert len(units) == 7  # six characters + one glued group
    assert units[-1][0] == pytest.approx(measure.text_em("38") + 2.0)
    plain = measure._units([("あ" * 6 + "38万円", False, False)])
    assert len(plain) == 9
    # the group wraps whole: 6 + 3.1 em does not fit 8 em, the unit does not split
    assert measure.count_lines([(t, False, False)], 8 * 10, 10) == 2


def test_bound_texts_skips_code_links_non_cjk_and_switch():
    from slidemark.ir import Run

    assert measure.bound_texts([Run(text="Total 38 units, $5")]) == ["Total 38 units,\u00a0$5"]
    assert measure.bound_texts([Run(text="38万円", code=True)]) == ["38万円"]
    assert measure.bound_texts([Run(text="38万円", link="https://x.jp/38万円")]) == ["38万円"]
    assert measure.bound_texts([Run(text="売上38万円")]) == [f"売上38{WJ}万{WJ}円"]
    old = measure.tokens()
    try:
        measure.set_tokens(LayoutTokens(cjk_unit_join=False))
        assert measure.bound_texts([Run(text="売上38万円")]) == ["売上38万円"]
    finally:
        measure.set_tokens(old)


def _xml(tmp_path, md):
    src = tmp_path / "d.md"
    src.write_text(md, encoding="utf-8")
    out = tmp_path / "d.pptx"
    build(str(src), str(out))
    return out, zipfile.ZipFile(out).read("ppt/slides/slide1.xml").decode()


def test_render_joins_and_import_strips(tmp_path):
    out, xml = _xml(tmp_path, "# 実績\n- 1件あたり平均38万円\n- 若手の採用は年▲8%\n- 54歳\n")
    assert f"38{WJ}万{WJ}円" in xml and f"▲{WJ}8%" in xml and f"54{WJ}歳" in xml
    md, _ = import_pptx(str(out))
    assert WJ not in md and "38万円" in md and "▲8%" in md


def test_render_switch_off(tmp_path):
    md = "---\nstyle: layout.cjk_unit_join=off\n---\n# 実績\n- 平均38万円\n"
    _, xml = _xml(tmp_path, md)
    assert "38万円" in xml


def test_bool_tokens_parse_off_on():
    for v in (None, "off", "no", "false", "False"):
        assert LayoutTokens(grow=v).grow is False
        assert RenderTokens(ink_auto=v).ink_auto is False
    for v in ("on", "yes", "true"):
        assert LayoutTokens(grow=v).grow is True
    assert LayoutTokens(card_spread_rules=None).card_spread_rules is False
    assert LayoutTokens().grow is True


def test_bool_token_off_from_deck_has_no_diagnostic(tmp_path):
    from slidemark import parse

    deck = parse("---\nstyle: layout.grow=off\n---\n# T\n- a\n")
    from slidemark.theme import apply_tokens, get_theme

    _, diags = apply_tokens(get_theme("default"), deck.tokens)
    assert not [d for d in diags if "token" in d.code]
