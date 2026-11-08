"""Editorial rhythm and focus (UI review round 2): one focus look, content centred with air, quiet type."""

from __future__ import annotations

from pathlib import Path

import pytest
from pptx import Presentation
from pptx.oxml.ns import qn

from slidemark import build
from slidemark.layout.engine import layout_slide
from slidemark.parser import parse
from slidemark.template import deck_theme
from slidemark.units import EMU_PER_PT

ROOT = Path(__file__).resolve().parent.parent
EX = ROOT / "examples"
IN = 914400


def _placed(src: str, n: int):
    deck = parse(src)
    theme, _ = deck_theme(deck, EX)
    return deck, theme, layout_slide(deck.slides[n - 1], deck, theme, n - 1)


def _body(items):
    return [
        p for p in items if getattr(p.element, "role", None) not in ("title", "lead", "caption", "footnote")
    ]


def test_chart_hl_is_a_tint_with_a_hairline_and_quiet_bars(tmp_path):
    out = tmp_path / "c.pptx"
    build(EX / "27-editorial.md", out)
    chart = next(sh for sh in Presentation(out).slides[3].shapes if sh.has_chart).chart
    ser = chart.plots[0].series[0]
    pts = ser._element.findall(qn("c:dPt"))
    assert len(pts) == 1  # only the highlighted category
    sp = pts[0].find(qn("c:spPr"))
    fill = sp.find(qn("a:solidFill")).find(qn("a:srgbClr")).get("val")
    line = sp.find(qn("a:ln")).find(qn("a:solidFill")).find(qn("a:srgbClr")).get("val")
    assert line == "BF4520" and fill != "BF4520"  # accent hairline, tinted (never solid accent) fill
    r, g, b = (int(fill[i : i + 2], 16) for i in (0, 2, 4))
    assert r > g > 0 and r > 200  # a warm light tint
    quiet = ser.format.fill.fore_color.rgb
    assert str(quiet) not in ("2D3142",)  # the other bars are not heavy ink
    assert sum(int(str(quiet)[i : i + 2], 16) for i in (0, 2, 4)) > 3 * 100


def test_chart_note_has_no_arrow_stub_and_no_box(tmp_path):
    out = tmp_path / "n.pptx"
    build(EX / "27-editorial.md", out)
    names = [sh.name for sh in Presentation(out).slides[3].shapes]
    assert "ChartNote" in names and not any(n.startswith("ChartNoteLine") for n in names)
    note = next(sh for sh in Presentation(out).slides[3].shapes if sh.name == "ChartNote")
    run = note.text_frame.paragraphs[0].runs[0]
    assert not run.font.italic and str(run.font.color.rgb) == "BF4520"


def test_treemap_focus_tile_is_a_tint_with_a_hairline(tmp_path):
    pytest.importorskip("playwright.sync_api")
    out = tmp_path / "t.pptx"
    build(EX / "30-html-diagrams.md", out)
    tiles = [sh for sh in Presentation(out).slides[3].shapes if sh.name.startswith("Shape")]
    assert len(tiles) == 4
    alphas = []
    for sh in tiles:
        clr = sh._element.spPr.find(qn("a:solidFill")).find(qn("a:srgbClr"))
        a = clr.find(qn("a:alpha"))
        alphas.append((clr.get("val"), int(a.get("val")) if a is not None else 100000))
        assert str(sh.line.color.rgb) in ("4F5D75", "BF4520")  # hairline borders on every tile
    focal = [x for x in alphas if x[0] == "BF4520"]
    assert len(focal) == 1 and focal[0][1] <= 20000  # accent tint, not a solid accent fill


def test_table_hugs_content_and_is_centred_with_air():
    deck, theme, items = _placed((EX / "27-editorial.md").read_text(encoding="utf-8"), 5)
    from slidemark.ir import Table

    tab = next(p for p in items if isinstance(p.element, Table))
    foot = next(p for p in items if getattr(p.element, "attrs", {}).get("field") == "footer")
    assert (
        tab.w < 0.85 * 12192000 and abs((tab.x + tab.w / 2) - 12192000 / 2) < 3 * EMU_PER_PT
    )  # hugs, centred
    assert foot.y - (tab.y + tab.h) >= 0.3 * IN  # air above the footer
    title = next(p for p in items if getattr(p.element, "role", None) == "title")
    above, below = tab.y - (title.y + title.h), foot.y - (tab.y + tab.h)
    assert abs(above - below) < 0.5 * IN  # centred in the free body, not top-hugging


def test_card_row_is_not_stretched_and_is_centred():
    src = (EX / "27-editorial.md").read_text(encoding="utf-8")
    deck, theme, items = _placed(src, 6)
    from slidemark.ir import Container

    cards = [p for p in items if isinstance(p.element, Container)]
    assert len(cards) == 4 and len({c.h for c in cards}) == 1
    texts = [p for p in items if getattr(p.element, "role", None) == "body"]
    # the card ends within ~1 inset of its tallest text: no stretched, half-empty cards
    assert cards[0].y + cards[0].h - max(t.y + t.h for t in texts) <= 0.3 * IN
    foot = next(p for p in items if getattr(p.element, "role", None) == "footnote")
    assert foot.y - (cards[0].y + cards[0].h) >= 0.3 * IN


def test_cjk_eyebrow_has_no_tracking():
    pytest.importorskip("playwright.sync_api")
    src = (
        'theme: editorial\n\n# 品質の分析 {eyebrow="特性要因図 · 品質"}\n- 本文\n\n'
        '# Latin {eyebrow="Root cause"}\n- body\n'
    )
    deck, theme, items = _placed(src, 1)
    eb = next(p for p in items if p.element.attrs.get("field") == "eyebrow")
    assert not eb.style.letter_spacing
    deck, theme, items = _placed(src, 2)
    eb = next(p for p in items if p.element.attrs.get("field") == "eyebrow")
    assert eb.style.letter_spacing  # Latin keeps its tracking


def test_cover_subtitle_uses_the_body_face():
    deck, theme, items = _placed((EX / "27-editorial.md").read_text(encoding="utf-8"), 1)
    sub = next(p for p in items if getattr(p.element, "role", None) == "subtitle")
    title = next(p for p in items if getattr(p.element, "role", None) == "title")
    assert sub.style.font == theme.fonts.body and title.style.font == theme.fonts.heading
