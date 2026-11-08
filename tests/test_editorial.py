"""The `editorial` preset (diagram-design palette) and the diagram role classes of every built-in preset."""

from __future__ import annotations

import pytest
from pptx import Presentation
from pptx.util import Emu

from slidemark.build import build
from slidemark.ir import Container, Text
from slidemark.parser import parse
from slidemark.theme import get_theme

ROLES = ("focal", "store", "external", "input", "optional", "security")
PRESETS = ("default", "midnight", "jp-business", "editorial")


def test_editorial_tokens():
    th = get_theme("editorial")
    assert th.colors["bg"] == "#F5F5F5"
    assert th.colors["fg"] == "#2D3142"
    assert th.colors["accent"] == "#BF4520"
    assert th.colors["border"] == "#BFC0C0"
    assert th.colors["link"] == "#2E5AA8"
    assert th.fonts.heading == "Georgia" and th.fonts.body == "Arial" and th.fonts.ea == "Yu Gothic"
    assert th.title_band is None and th.title_rule is None and th.title_bold is False
    card = th.classes["card"]
    assert card.fill == "#FFFFFF" and card.line == "border" and not card.shadow
    assert all(not st.shadow for st in th.classes.values())
    assert th.render.connector_color == "secondary" and th.render.connector_width == 1
    assert th.palette[0] == "primary" and "accent" not in th.palette


@pytest.mark.parametrize("name", PRESETS)
def test_every_preset_has_the_role_classes(name):
    th = get_theme(name)
    for role in ROLES:
        assert role in th.classes, f"{name} lacks .{role}"
    assert th.classes["optional"].line_dash == "dash" and th.classes["optional"].fill is None
    assert th.classes["security"].line_dash == "dash"
    assert th.classes["focal"].line == "accent"


def test_title_bold_is_a_token(tmp_path):
    def title_bold(src: str) -> bool | None:
        build(src, tmp_path / "t.pptx")
        slide = Presentation(tmp_path / "t.pptx").slides[0]
        shape = next(s for s in slide.shapes if s.has_text_frame and "Hello" in s.text_frame.text)
        return shape.text_frame.paragraphs[0].runs[0].font.bold

    assert not title_bold("theme: editorial\n\n# Hello\n- a\n")
    assert title_bold("theme: default\n\n# Hello\n- a\n")
    assert title_bold("theme: editorial\nstyle: title.bold=on\n\n# Hello\n- a\n")


def test_role_classes_render(tmp_path):
    src = "theme: editorial\n\n# Roles\n@2\n## Gateway {.focal}\nroutes\n## Cache {.optional}\nredis\n"
    d = build(src, tmp_path / "r.pptx")
    assert not [x for x in d.diagnostics if x.level == "warning" and not x.rule.startswith("design")]
    slide = Presentation(tmp_path / "r.pptx").slides[0]
    cards = [s for s in slide.shapes if s.name.startswith("Card")]
    focal, opt = cards
    sp = focal._element.spPr.xml
    assert 'srgbClr val="BF4520"' in sp and "<a:alpha" in sp  # accent tint fill (alpha) + accent line
    assert str(focal.line.color.rgb) == "BF4520" and "prstDash" not in sp
    assert "<a:effectLst/>" in sp  # no shadow
    spo = opt._element.spPr.xml
    assert str(opt.line.color.rgb) == "5A6580"
    assert 'prstDash val="dash"' in spo
    assert 'srgbClr val="FFFFFF"' in spo  # `.optional` keeps the card fill
    assert opt.line.width == Emu(9525)  # the card's hairline (0.75pt)


def test_mermaid_classes_render(tmp_path):
    src = (
        "theme: editorial\n\n# Flow\n```mermaid\nflowchart LR\n"
        "  A[Input]:::input --> B[DB]:::store\n  B --> C[Vault]:::security\n  class A,C focal\n```\n"
    )
    deck = parse(src)
    c = deck.slides[0].elements[0]
    assert isinstance(c, Container)
    cls = [t.classes for t in c.children if isinstance(t, Text)]
    assert "store" in cls[1] and "node" in cls[1]
    assert "focal" in cls[0] and "input" in cls[0]  # `:::` plus a `class` line
    assert "focal" in cls[2] and "security" in cls[2]
    d = build(src, tmp_path / "m.pptx")
    assert not [x for x in d.diagnostics if x.level == "warning" and not x.rule.startswith("design")]
    slide = Presentation(tmp_path / "m.pptx").slides[0]
    dashed = [s for s in slide.shapes if 'prstDash val="dash"' in s._element.xml]
    assert len(dashed) == 1  # only the `.security` node


def test_mermaid_unknown_class_never_raises(tmp_path):
    deck = parse("# T\n```mermaid\nflowchart TD\n  A[x]:::focl --> B[y]:::nosuchrole\n  class Z store\n```\n")
    assert isinstance(deck.slides[0].elements[0], Container)
    msgs = [d for d in deck.diagnostics if d.rule == "unknown-attr"]
    assert msgs and "focal" in msgs[0].hint
    # a name nobody defines is a plain class: the build still succeeds
    build("# T\n```mermaid\nflowchart TD\n  A[x]:::nosuchrole --> B[y]\n```\n", tmp_path / "x.pptx")


def test_connector_color_token(tmp_path):
    src = "style: render.connector_color=accent\n\n# C\n@2 a>b\n## A\nx\n## B\ny\n"
    build(src, tmp_path / "c.pptx")
    slide = Presentation(tmp_path / "c.pptx").slides[0]
    cons = [s for s in slide.shapes if s.shape_type is not None and "Connector" in s.name]
    cons = cons or [s for s in slide.shapes if s._element.tag.endswith("}cxnSp")]
    assert cons and str(cons[0].line.color.rgb) == "F59E0B"
