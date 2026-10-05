"""CSS-designed decks round-trip: build -> import -> build is stable (examples/17-editorial-css)."""

from __future__ import annotations

from pathlib import Path

import pytest

from slidemark.build import build
from slidemark.importer import import_pptx
from slidemark.ir import Style
from slidemark.parser import parse
from slidemark.parser.css import SUPPORTED, parse_declarations
from slidemark.parser.ctx import Ctx
from slidemark.render.design_part import style_to_css

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "17-editorial-css.md"

# one sample declaration per supported css property
VALUES = {
    "color": "#112233",
    "background": "#112233",
    "background-color": "#112233",
    "border": "2px solid #112233",
    "border-color": "#112233",
    "border-width": "3px",
    "border-style": "dashed",
    "border-radius": "8px",
    "box-shadow": "0 4px 12px #00000055",
    "opacity": "0.5",
    "font-family": "Georgia",
    "font-size": "12pt",
    "font-weight": "bold",
    "font-style": "italic",
    "letter-spacing": "2pt",
    "line-height": "1.4",
    "text-align": "center",
    "vertical-align": "middle",
    "text-transform": "uppercase",
    "text-decoration": "underline line-through",
    "padding": "4pt 10pt",
    "margin": "8px",
    "gap": "16px",
    "width": "fit-content",
    "display": "inline-block",
    "grid-template-columns": "1fr 2fr",
    "grid-template-areas": '"a a b" "a a c"',
    "transform": "rotate(-2deg)",
    "border-top": "3px solid #112233",
    "border-right": "none",
    "border-bottom": "1px dashed #112233",
    "border-left": "2px dotted #112233",
    "padding-top": "2pt",
    "padding-right": "3pt",
    "padding-bottom": "4pt",
    "padding-left": "5pt",
}


@pytest.mark.parametrize("prop", SUPPORTED)
def test_every_supported_property_serializes(prop):
    assert prop in VALUES, f"add a sample for the new css property {prop}"
    s1, _ = parse_declarations(f"{prop}: {VALUES[prop]}", 1, Ctx([]), set())
    assert s1 != Style(), prop
    css = style_to_css(s1)
    s2, _ = parse_declarations(css, 1, Ctx([]), set())
    assert s2 == s1, css


def test_width_fit_content_is_serialized():
    assert "width: fit-content" in style_to_css(Style(width="fit-content"))


def _roundtrip(tmp_path: Path, text: str) -> str:
    a = tmp_path / "a.pptx"
    build(text, a)
    t1, _ = import_pptx(a, tmp_path)
    b = tmp_path / "b.pptx"
    build(t1, b)
    t2, _ = import_pptx(b, tmp_path)
    assert t1 == t2
    return t1


def test_css_explained_run_style_is_not_markup(tmp_path):
    text = "```css\n.lead { color: #C2410C; font-style: italic }\n```\n\n# T\n> Slow down\n## A\n- x\n"
    t1 = _roundtrip(tmp_path, text)
    assert "\n> Slow down\n" in t1
    assert "==" not in t1 and "*Slow" not in t1


def test_uppercase_heading_recovers_source_casing(tmp_path):
    text = (
        "```css\nh1 { text-transform: uppercase }\n.box > h2 { text-transform: uppercase }\n```\n\n"
        "# Big title\n## At home\nOne sentence.\n## On the move\nAnother one.\n"
    )
    t1 = _roundtrip(tmp_path, text)
    assert "# Big title\n" in t1
    assert "## At home\n" in t1 and "## On the move\n" in t1
    assert "AT HOME" not in t1


def test_css_sized_heading_is_not_a_kpi(tmp_path):
    text = (
        "```css\n.box > h2 { font-size: 12pt }\n```\n\n# T\n"
        "## At home\nHome espresso machines sold 2.1M units, up 34% since 2023.\n"
        "## On the move\nCold brew cans grew to 18% of sales.\n"
    )
    t1 = _roundtrip(tmp_path, text)
    assert ".kpi" not in t1


def test_real_kpi_keeps_its_class_with_css_heading(tmp_path):
    text = (
        "```css\n.box > h2 { font-size: 12pt }\n.kpi { border-top: 3px solid #C2410C }\n```\n\n"
        "# T\n## Size {.kpi}\n$4.8B\nup\n"
    )
    t1 = _roundtrip(tmp_path, text)
    assert "## Size {.kpi}" in t1


def test_class_line_on_text_and_stack_token_survive():
    src = EXAMPLE.read_text(encoding="utf-8")
    # slide 4 of the example: @1 stack, widths, sticker on the text block
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        t1 = _roundtrip(Path(tmp), src)
    slide4 = t1.split("# Where the growth comes from")[1].split("# Outlook")[0]
    assert "@1\n" in slide4 and "@1x2" not in slide4
    assert "{widths=2:1:1:1}" in slide4
    assert "{.sticker}\nFastest growing: ready to drink" in slide4
    assert "width: fit-content" in t1


def test_html_slide_and_design_come_back(tmp_path):
    t1 = _roundtrip(tmp_path, EXAMPLE.read_text(encoding="utf-8"))
    assert "# Outlook\n@html\n```html\n" in t1
    d0, d1 = parse(EXAMPLE.read_text(encoding="utf-8")), parse(t1)
    assert d0.slides[4].html == d1.slides[4].html
    assert {r.selector for r in d0.css} == {r.selector for r in d1.css}
    assert [r.style.width for r in d0.css] == [r.style.width for r in d1.css]
