"""Build feedback for design decisions: `design-none`, `design-slide` and the `design:` facts line."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from slidemark import design
from slidemark.build import build_deck
from slidemark.cli import main
from slidemark.ir import Deck, Slide
from slidemark.parser import parse

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"

BODY = "# Plan\n- one\n- two\n"
CONTENT_ONLY = "# Cover\nA subtitle\n\n# Market\n- a\n- b\n\n# Costs\n- c\n- d\n"


def _rules(text: str) -> dict[str, object]:
    d = parse(text)
    return {x.rule: x for x in design.design_diagnostics(d)}


def _bare(text: str) -> list[int]:
    return design.slides_without_choice(parse(text))[0]


# --------------------------------------------------------------------------- design-none


def test_design_none_message_and_hint_exact():
    got = _rules(BODY)["design-none"]
    assert got.level == "warning"
    assert got.message == "no design stated"
    assert got.hint == "state your design: colors: fonts: sizes: style: (or a css fence)"
    assert got.slide is None and got.line is None


@pytest.mark.parametrize(
    "header",
    [
        "colors: primary=#7C5CFF",
        "fonts: heading=Georgia",
        "sizes: title=30",
        "style: radius=8",
        "style: h1.letter-spacing=2pt",  # routed to deck css, still the `style:` group
    ],
)
def test_design_none_quiet_when_a_group_is_stated(header):
    assert "design-none" not in _rules(f"{header}\n\n{BODY}")


def test_design_none_quiet_with_header_css_fence():
    assert "design-none" not in _rules("```css\nh1 { color: #C2410C }\n```\n\n" + BODY)


def test_design_none_fires_for_slide_css_fence_only():
    # a css fence inside a slide is that slide's choice, not the deck's
    assert "design-none" in _rules("# A\n- x\n```css\nh1 { color: #C2410C }\n```\n")


def test_theme_preset_alone_is_not_a_decision():
    assert "design-none" in _rules("theme: midnight\n\n" + BODY)
    assert "design-none" in _rules("footer: ACME\nnum: on\n\n" + BODY)


@pytest.mark.parametrize("theme", ["./brand.yaml", "brand.yml", "template.pptx", "corp.potx"])
def test_theme_file_counts(theme):
    assert "design-none" not in _rules(f"theme: {theme}\n\n{BODY}")


def test_design_none_in_yaml_front_matter():
    assert "design-none" not in _rules("---\ncolors:\n  primary: '#7C5CFF'\n---\n" + BODY)


def test_design_none_for_deck_built_in_python():
    deck = Deck(slides=[Slide()])
    assert "design-none" in {d.rule for d in design.design_diagnostics(deck)}
    deck = Deck(slides=[Slide()], tokens={"colors.primary": "#7C5CFF"})
    assert "design-none" not in {d.rule for d in design.design_diagnostics(deck)}


# --------------------------------------------------------------------------- design-slide


def test_design_slide_lists_bare_slides():
    got = _rules(CONTENT_ONLY)["design-slide"]
    assert got.level == "warning" and got.slide is None and got.rule == "design-slide"
    assert got.message == "slides 2, 3 carry no design choice"
    assert got.hint.startswith("choose the form (list/cards/@steps/@cols/table/chart/@html)")
    assert "({.hero} hl= ==x==)" in got.hint and "size= fill= color= align= x y w h" in got.hint
    assert len(got.message) < 160 and len(got.hint) < 160


def test_design_slide_singular():
    assert _rules(BODY)["design-slide"].message == "slide 1 carries no design choice"


def test_cover_and_section_slides_are_exempt():
    text = "# Cover\nSubtitle\n\n# Part two\n@section\n\n# Facts\n@dense\n- a\n- b\n"
    assert "design-slide" not in _rules(text)
    assert design.exempt(parse("# Cover\nSubtitle\n").slides[0])
    assert design.exempt(parse("# Part\n@section\n").slides[0])
    # exempt slides are left out of both numbers
    assert design.facts(parse(text)) == "design: none; 1/1 slides carry choices"


def test_notes_only_and_title_only_slides_are_exempt():
    text = "# Divider\n??? say the agenda out loud\n\n# Next\n@dense\n- a\n- b\n"
    assert _bare(text) == []


def test_control_slide_is_bare():
    assert _bare("# One\n- a\n- b\n") == [1]


CHOICES = {
    "heading class": "## Box {.accent}\n- a\n- b",
    "heading size": "## Box {size=18}\n- a\n- b",
    "block attrs line": "{.hero}\n- a\n- b",
    "image attrs": "![x](a.png){w=200 x=10}\n- a",
    "table option widths": "{widths=3:1}\n| a | b |\n|---|---|\n| 1 | 2 |",
    "table option hl": "{hl=1}\n| a | b |\n|---|---|\n| 1 | 2 |",
    "table option align": "{align=lr}\n| a | b |\n|---|---|\n| 1 | 2 |",
    "chart option": "```column {legend=bottom}\n,Q1,Q2\nA,1,2\n```",
    "chart hl": "```column {hl=Q1}\n,Q1,Q2\nA,1,2\n```",
    "at steps": "@steps\n## One\n- a\n## Two\n- b",
    "at chevron": "@3 chevron\n## One\n## Two\n## Three",
    "at grid": "@2\n## One\n- a\n## Two\n- b",
    "at free": "@free\n- a",
    "at bg": "@bg=#102030\n- a",
    "at dark": "@dark\n- a",
    "at light": "@light\n- a",
    "at dense": "@dense\n- a",
    "at html": "@html\n```html\n<h1>x</h1>\n```",
    "slide css fence": "- a\n```css\nh2 { color: #C2410C }\n```",
    "inline mark": "- a ==b== c",
    "inline span": "- a [b]{.danger} c",
    "inline badge": "- a [new]{.badge .success}",
    "table zebra": "{.zebra}\n| a | b |\n|---|---|\n| 1 | 2 |",
}


@pytest.mark.parametrize("name", list(CHOICES))
def test_each_choice_counts(name):
    assert _bare(f"# S\n{CHOICES[name]}\n") == [], name


def test_choice_in_title_attrs():
    assert _bare("# S {size=30}\n- a\n") == []
    assert _bare("# S {bg=#112233}\n- a\n") == []


def test_choice_inside_a_nested_box():
    assert _bare("# S\n@2\n## A\n- x ==y==\n## B\n- z\n") == []
    assert _bare("# S\n## A\n- x\n### Inner {.accent}\n- z\n@2\n") == []


def test_choice_on_lead_conclusion_footnote():
    assert _bare("# S\n- a\n> a takeaway with ==emphasis==\n") == []


@pytest.mark.parametrize("directive", ["@build", "@t=fade", "@hidden", "@build t=push hidden"])
def test_build_transition_hidden_are_not_choices(directive):
    assert _bare(f"# S\n{directive}\n- a\n- b\n") == [1]


def test_plain_markdown_emphasis_and_blocks_are_not_choices():
    # bold, italic, links, callouts, mermaid, a chart or table without options: the block kind only
    text = "# S\n- **bold** and *italic* and [link](http://x.y)\n> [!note] heads up\n"
    assert _bare(text) == [1]
    assert _bare("# T\n| a | b |\n|---|---|\n| 1 | 2 |\n") == [1]
    assert _bare("# C\n```bar\n,Q1,Q2\nA,1,2\n```\n") == [1]
    assert _bare("# M\n```mermaid\nflowchart LR\n  A --> B\n```\n") == [1]


def test_chart_title_and_derived_options_are_not_choices():
    assert _bare("# C\n```bar {title=Revenue}\n,Q1,Q2\nA,1,2\n```\n") == [1]
    assert _bare("# C\n```bar\n,Q1,Q2\nA,12%,30%\n```\n") == [1]  # percent is derived from the data


def test_detection_is_table_driven():
    """A new field that lands in classes/attrs/style/box is a choice without new code."""
    from slidemark.ir import Text

    s = Slide(elements=[Text(attrs={"brand_new_key": "1"})])
    assert design.carries_choice(s)
    assert not design.carries_choice(Slide(elements=[Text()]))
    assert design.carries_choice(Slide(elements=[Text()], classes=["whatever"]))
    assert not design.carries_choice(Slide(elements=[Text()], classes=["build"]))


# --------------------------------------------------------------------------- facts line


def test_facts_none():
    assert design.facts(parse(CONTENT_ONLY)) == "design: none; 0/2 slides carry choices"


def test_facts_lists_stated_keys_in_fixed_order():
    text = (
        "footer: ACME\nstyle: radius=8\nfonts: heading=Georgia\ncolors: primary=#7C5CFF\n\n"
        "# Cover\nsub\n\n# A\n@dense\n- a\n\n# B\n- b\n"
    )
    assert design.facts(parse(text)) == "design: colors fonts style footer; 1/2 slides carry choices"


def test_facts_css_theme_file_and_num():
    text = "theme: ./b.yaml\nnum: on\n```css\nh1 { color: red }\n```\n\n# A\n- a ==x==\n"
    assert design.facts(parse(text)) == "design: css theme-file num; 1/1 slides carry choices"


def test_facts_is_one_line_without_colour():
    line = design.facts(parse(CONTENT_ONLY))
    assert "\n" not in line and "\x1b" not in line


def test_build_prints_facts_before_look(tmp_path, capsys):
    f = tmp_path / "d.md"
    f.write_text("colors: primary=#7C5CFF\n\n# A\n@dense\n- a\n- b\n", encoding="utf-8")
    assert main(["build", str(f), "-o", str(tmp_path / "d.pptx")]) == 0
    err = capsys.readouterr()
    lines = (err.out + err.err).splitlines()
    i = next(n for n, x in enumerate(lines) if x.startswith("design: "))
    j = next(n for n, x in enumerate(lines) if x.startswith("look: "))
    assert i + 1 == j and lines[i] == "design: colors; 1/1 slides carry choices"
    assert lines[-1].startswith("wrote ")


def test_build_prints_both_warnings_and_design_none_line(tmp_path, capsys):
    f = tmp_path / "d.md"
    f.write_text(CONTENT_ONLY, encoding="utf-8")
    assert main(["build", str(f), "-o", str(tmp_path / "d.pptx")]) == 0
    text = (lambda c: c.out + c.err)(capsys.readouterr())
    assert "warning design-none: no design stated -> state your design:" in text
    assert "warning design-slide: slides 2, 3 carry no design choice -> choose the form" in text
    assert "design: none; 0/2 slides carry choices" in text
    assert "2 warnings" in text.splitlines()[-1]


# --------------------------------------------------------------------------- check, fix, JSON


def test_check_lists_them_like_other_warnings(tmp_path, capsys):
    f = tmp_path / "d.md"
    f.write_text(CONTENT_ONLY, encoding="utf-8")
    assert main(["check", str(f)]) == 0  # warnings never fail
    lines = capsys.readouterr().out.strip().splitlines()
    assert [x.split(":")[0] for x in lines] == ["warning design-none", "warning design-slide"]
    assert all("->" in x for x in lines)


def test_check_json_carries_rule_names(tmp_path, capsys):
    f = tmp_path / "d.md"
    f.write_text(CONTENT_ONLY, encoding="utf-8")
    assert main(["check", str(f), "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    by_rule = {d["rule"]: d for d in data}
    assert by_rule["design-none"]["message"] == "no design stated"
    assert by_rule["design-none"]["level"] == "warning" and by_rule["design-none"]["slide"] is None
    assert by_rule["design-slide"]["message"] == "slides 2, 3 carry no design choice"
    assert by_rule["design-slide"]["hint"].startswith("choose the form")


def test_check_fix_leaves_them_alone(tmp_path, capsys):
    f = tmp_path / "d.md"
    f.write_text(CONTENT_ONLY, encoding="utf-8")
    assert main(["check", str(f), "--fix", "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["fixed"] == []
    assert f.read_text(encoding="utf-8") == CONTENT_ONLY
    assert {d["rule"] for d in data["diagnostics"]} == {"design-none", "design-slide"}


def test_build_fix_does_not_touch_source(tmp_path):
    f = tmp_path / "d.md"
    f.write_text(CONTENT_ONLY, encoding="utf-8")
    assert main(["build", str(f), "-o", str(tmp_path / "d.pptx")]) == 0
    assert f.read_text(encoding="utf-8") == CONTENT_ONLY


def test_build_deck_diagnostics_carry_rule_names(tmp_path):
    deck = build_deck(parse(CONTENT_ONLY), tmp_path / "d.pptx", tmp_path)
    rules = [d.rule for d in deck.diagnostics]
    assert rules.count("design-none") == 1 and rules.count("design-slide") == 1


def test_json_deck_gets_the_same_feedback(tmp_path, capsys):
    deck = parse("# A\n- a\n")
    f = tmp_path / "d.json"
    f.write_text(deck.model_dump_json(exclude={"diagnostics"}), encoding="utf-8")
    assert main(["check", str(f), "--format", "json"]) == 0
    assert {d["rule"] for d in json.loads(capsys.readouterr().out)} == {"design-none", "design-slide"}


# --------------------------------------------------------------------------- the example decks


def test_examples_basics_fires_where_expected():
    text = (EXAMPLES / "01-basics.md").read_text(encoding="utf-8")
    got = _rules(text)
    assert "design-none" in got
    assert _bare(text) == [3, 4]
    assert got["design-slide"].message == "slides 3, 4 carry no design choice"


def test_examples_with_a_design_header_do_not_warn_design_none():
    for name in ("13-brand-aurora.md", "18-brand-lime.md", "19-vi-consulting-brand.md", "10-template.md"):
        assert "design-none" not in _rules((EXAMPLES / name).read_text(encoding="utf-8")), name


@pytest.mark.parametrize("path", sorted(EXAMPLES.glob("*.md")), ids=lambda p: p.name)
def test_every_example_gets_feedback_without_crashing(path):
    d = parse(path.read_text(encoding="utf-8"))
    out = design.design_diagnostics(d)
    assert {x.rule for x in out} <= {"design-none", "design-slide"}
    line = design.facts(d)
    assert line.startswith("design: ") and "slides carry choices" in line
    n, total = (int(x) for x in line.rsplit("; ", 1)[1].split(" ")[0].split("/"))
    assert 0 <= n <= total <= len(d.slides)
    assert (n < total) == any(x.rule == "design-slide" for x in out)


def test_content_only_deck_string_fires_both():
    got = _rules("# Quarterly review\n- Revenue grew\n- Costs fell\n\n# Next steps\n- Hire\n- Ship\n")
    assert set(got) == {"design-none", "design-slide"}
    assert got["design-slide"].message == "slides 1, 2 carry no design choice"


def test_review_loop_is_not_asked_about_design(tmp_path):
    from slidemark.selfreview import analyze

    ana = analyze(CONTENT_ONLY, tmp_path)
    assert not any(d.rule in ("design-none", "design-slide") for d in ana.diags)
