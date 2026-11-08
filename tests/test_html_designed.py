"""A designed ```html fence under a title: run sizes follow Chromium, CJK text, svg tokens, overflow guard."""

from __future__ import annotations

import pytest
from pptx import Presentation

from slidemark.build import build
from slidemark.ir import Deck, Paragraph, Placed, Run, Slide, Style, Text
from slidemark.lint import lint_slide
from slidemark.render.htmlimg import HtmlRenderer
from slidemark.theme import Theme

CARD = (
    '<div style="font-size:20px;width:420px"><div style="border:1px solid #999;padding:12px">'
    '<b>One-page checkout</b><br><span style="font-size:16px">blocks the Q4 target</span></div></div>'
)
SVG = (
    '<svg width="100%" height="100%" viewBox="0 0 600 200">'
    '<defs><marker id="a" markerWidth="10" markerHeight="10" refX="9" refY="5" orient="auto">'
    '<path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"/></marker></defs>'
    '<line x1="20" y1="40" x2="500" y2="40" stroke="var(--primary)" stroke-width="3" marker-end="url(#a)"/>'
    '<line x1="20" y1="100" x2="500" y2="100" stroke="var(--accent)" stroke-width="3"/>'
    '<rect x="20" y="130" width="200" height="40" fill="var(--secondary)" stroke="var(--border)"/>'
    '<text x="30" y="160" font-size="20" font-weight="700" fill="var(--accent)">要因分析ラベル</text></svg>'
)


@pytest.fixture(scope="module")
def chromium():
    pytest.importorskip("playwright.sync_api")
    r = HtmlRenderer()
    try:
        ok = r.render("<p>x</p>", 40, 20, Theme(name="t")) is not None
    finally:
        r.close()
    if not ok:
        pytest.skip("Chromium cannot be launched")


def _deck(html: str, tmp_path, zoom: str = ""):
    attr = f"{{zoom={zoom}}}\n" if zoom else ""
    out = tmp_path / "o.pptx"
    deck = build(f"# Board\n{attr}```html\n{html}\n```\n", out)
    return deck, Presentation(str(out))


def _runs(prs):
    return [
        (r.text, r.font.size.pt, r.font.bold)
        for sh in prs.slides[0].shapes
        if sh.has_text_frame
        for para in sh.text_frame.paragraphs
        for r in para.runs
        if r.font.size
    ]


def test_run_sizes_follow_chromium_at_zoom_1(chromium, tmp_path):
    _, prs = _deck(CARD, tmp_path, zoom="1")
    sizes = {t: s for t, s, _ in _runs(prs) if t.startswith(("One", "blocks"))}
    assert sizes["One-page checkout"] == pytest.approx(15.0)  # 20px
    assert sizes["blocks the Q4\xa0target"] == pytest.approx(12.0)  # 16px


def test_run_sizes_scale_with_zoom(chromium, tmp_path):
    _, prs = _deck(CARD, tmp_path, zoom="1.5")
    sizes = {t: s for t, s, _ in _runs(prs) if t.startswith(("One", "blocks"))}
    assert sizes["One-page checkout"] == pytest.approx(22.5)
    assert sizes["blocks the Q4\xa0target"] == pytest.approx(18.0)  # 16px * 1.5, same zoom as the widths


def test_larger_run_after_smaller_is_not_capped(chromium, tmp_path):
    html = (
        '<div style="font-size:16px;width:500px;border:1px solid #999">'
        'small <span style="font-size:32px">big</span></div>'
    )
    _, prs = _deck(html, tmp_path, zoom="1")
    sizes = {t.strip(): s for t, s, _ in _runs(prs)}
    assert sizes["big"] == pytest.approx(24.0)


def test_converted_cjk_text_keeps_ea_font_bold_and_no_squeeze(chromium, tmp_path):
    html = (
        '<div style="border:1px solid #999;width:300px;font:700 14px sans-serif;padding:6px">'
        "材料の品質不良が発生しています</div>"
    )
    _, prs = _deck(html, tmp_path, zoom="1")
    xml = "".join(
        sh._element.xml for sh in prs.slides[0].shapes if sh.has_text_frame and "材料" in sh.text_frame.text
    )
    assert 'b="1"' in xml and "<a:ea typeface=" in xml
    assert "spc=" not in xml  # Chromium fixed the breaks; no CJK tracking squeeze


def test_svg_var_tokens_resolve_to_theme_colours(chromium):
    from slidemark.htmlnative import html_to_placed

    theme = Theme(
        name="t",
        colors={
            "bg": "#FFFFFF",
            "fg": "#111111",
            "primary": "#123456",
            "accent": "#BF4520",
            "secondary": "#4F5D75",
        },
    )
    renderer = HtmlRenderer()
    try:
        res = html_to_placed(SVG, 0, 0, 900 * 9525, 400 * 9525, theme, ".", renderer=renderer, zoom=1)
    finally:
        renderer.close()
    assert res is not None
    items = res[0]
    fills = {str(p.style.fill).upper() for p in items if p.style.fill}
    lines = {str(p.style.line).upper() for p in items if p.style.line}
    texts = {str(p.element.paragraphs[0].runs[0].color).upper() for p in items if isinstance(p.element, Text)}
    assert "#BF4520" in texts or "BF4520" in texts
    blob = " ".join(fills | lines)
    assert "123456" in blob and "BF4520" in blob and "4F5D75" in blob


def _frame(h_pt: float, runs: list[Run]) -> Placed:
    el = Text(role="body", paragraphs=[Paragraph(runs=runs)], attrs={"measured": "html"})
    return Placed(
        element=el, x=0, y=0, w=int(2 * 914400), h=int(h_pt * 12700), style=Style(font_size=20, padding=0)
    )


def _lint(*frames: Placed):
    deck = Deck(slides=[Slide()])
    return [d for d in lint_slide(list(frames), deck, Theme(name="t"), 0) if d.rule == "html-native-overflow"]


def test_overflow_guard_one_warning_per_slide():
    long = Run(text="word " * 80)
    assert len(_lint(_frame(30, [long]), _frame(30, [long]))) == 1


def test_overflow_guard_quiet_when_it_fits():
    assert not _lint(_frame(60, [Run(text="two short lines")]))
    # within Chromium's 25% slack: one 20pt line in a box a little short of its height
    assert not _lint(_frame(23, [Run(text="short")]))
