"""Build feedback for design decisions (docs/DESIGN_REQUIRED.md, "Tightened rules"): `design-none` names the
missing header lines, `design-slide` checks form + emphasis + values per slide, the `design:` facts line."""

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

import pytest

from slidemark import design
from slidemark.build import build_deck
from slidemark.cli import main
from slidemark.ir import Deck, Slide
from slidemark.parser import parse

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
SKILL = Path(__file__).resolve().parent.parent / "src" / "slidemark" / "skill" / "SKILL.md"

BODY = "# Plan\n- one\n- two\n"
CONTENT_ONLY = "# Cover\nA subtitle\n\n# Market\n- a\n- b\n\n# Costs\n- c\n- d\n"
FRAME = "colors: primary=#7C5CFF\nfonts: heading=Georgia\nsizes: title=30\nstyle: radius=8\n\n"
DECIDED = "@2 noemph defaults\n## A\n- a\n## B\n- b\n"  # form + emphasis + values


def _rules(text: str) -> dict[str, object]:
    d = parse(text)
    return {x.rule: x for x in design.design_diagnostics(d)}


def _got(body: str) -> set[str]:
    """The groups a one-slide deck states."""
    s = parse(f"# S\n{body}\n").slides[0]
    return {g for g, ok in design.stated_groups(s).items() if ok}


def _short(text: str) -> dict[int, list[str]]:
    return design.slide_shortfalls(parse(text))[0]


# --------------------------------------------------------------------------- design-none


def test_design_none_names_every_missing_line():
    got = _rules(BODY)["design-none"]
    assert got.level == "warning" and got.slide is None and got.line is None
    assert got.message == "design: colors: fonts: sizes: style: not stated"
    assert got.hint.startswith("add colors: fonts: sizes: style: to the header")
    assert "css fence" in got.hint and "theme file" in got.hint  # the two stand-ins for style:


@pytest.mark.parametrize(
    ("header", "missing"),
    [
        ("colors: primary=#7C5CFF", "fonts: sizes: style:"),
        ("fonts: heading=Georgia", "colors: sizes: style:"),
        ("sizes: title=30", "colors: fonts: style:"),
        ("style: radius=8", "colors: fonts: sizes:"),
        ("style: h1.letter-spacing=2pt", "colors: fonts: sizes:"),  # routed to deck css, still `style:`
        ("colors: primary=#7C5CFF\nfonts: heading=Georgia", "sizes: style:"),
        ("colors: primary=#7C5CFF\nsizes: title=30\nstyle: radius=8", "fonts:"),
    ],
)
def test_design_none_lists_only_the_missing_lines(header, missing):
    got = _rules(f"{header}\n\n{BODY}")["design-none"]
    assert got.message == f"design: {missing} not stated"
    assert got.hint.startswith(f"add {missing} to the header")


def test_design_none_quiet_when_all_four_lines_are_stated():
    assert "design-none" not in _rules(FRAME + BODY)


def test_design_none_hint_mentions_css_only_when_style_is_missing():
    got = _rules("colors: primary=#7C5CFF\nstyle: radius=8\n\n" + BODY)["design-none"]
    assert got.message == "design: fonts: sizes: not stated" and "css fence" not in got.hint


def test_header_css_fence_stands_in_for_style_only():
    got = _rules("```css\nh1 { color: #C2410C }\n```\n\n" + BODY)["design-none"]
    assert got.message == "design: colors: fonts: sizes: not stated"
    done = "colors: a=#111111\nfonts: heading=Georgia\nsizes: title=30\n"
    full = done + "```css\nh1 { color: #C2410C }\n```\n\n"
    assert "design-none" not in _rules(full + BODY)


def test_design_none_fires_for_slide_css_fence_only():
    # a css fence inside a slide is that slide's choice, not the deck's
    got = _rules("# A\n- x\n```css\nh1 { color: #C2410C }\n```\n")["design-none"]
    assert "style:" in got.message


def test_theme_preset_alone_is_not_a_decision():
    assert _rules("theme: midnight\n\n" + BODY)["design-none"].message.endswith("style: not stated")
    assert "colors:" in _rules("footer: ACME\nnum: on\n\n" + BODY)["design-none"].message


@pytest.mark.parametrize("theme", ["./brand.yaml", "brand.yml", "template.pptx", "corp.potx"])
def test_theme_file_stands_in_for_style_only(theme):
    got = _rules(f"theme: {theme}\n\n{BODY}")["design-none"]
    assert got.message == "design: colors: fonts: sizes: not stated"
    done = "colors: a=#111111\nfonts: heading=Georgia\nsizes: title=30\n"
    assert "design-none" not in _rules(f"theme: {theme}\n{done}\n{BODY}")


def test_design_none_in_yaml_front_matter():
    got = _rules("---\ncolors:\n  primary: '#7C5CFF'\n---\n" + BODY)["design-none"]
    assert got.message == "design: fonts: sizes: style: not stated"


def test_design_none_for_deck_built_in_python():
    deck = Deck(slides=[Slide()])
    assert "design-none" in {d.rule for d in design.design_diagnostics(deck)}
    deck = Deck(slides=[Slide()], tokens={"colors.primary": "#7C5CFF"})
    got = {d.rule: d for d in design.design_diagnostics(deck)}["design-none"]
    assert got.message == "design: fonts: sizes: style: not stated"


# --------------------------------------------------------------------------- the three groups

FORM = {
    "grid @N": "@2\n## A\n- a\n## B\n- b",
    "grid @AxB": "@2x2\n## A\n- a\n## B\n- b\n## C\n- c\n## D\n- d",
    "grid ratios": "@1:2\n## A\n- a\n## B\n- b",
    "grid areas": "@aab/aac\n## A\n- a\n## B\n- b\n## C\n- c",
    "@steps": "@steps\n## One\n- a\n## Two\n- b",
    "@chevron": "@3 chevron\n## One\n## Two\n## Three",
    "@rows": "@rows\n- a\n- b",
    "@items": "@items\n- a\n- b",
    "@kpi": "@kpi\n## One\n1\n## Two\n2",
    "@free": "@free\n- a",
    "@html": "@html\n```html\n<h1>x</h1>\n```",
    "@timeline (a new word)": "@timeline\n- a",
    "connectors": "@a>b\n## A\n- a\n## B\n- b",
    "table": "| a | b |\n|---|---|\n| 1 | 2 |",
    "chart": "```column\n,Q1,Q2\nA,1,2\n```",
    "image": "![x](a.png)",
    "mermaid": "```mermaid\nflowchart LR\n  A --> B\n```",
    "callout": "- a\n> [!note] heads up",
    "code": "```python\nx = 1\n```",
    "box with a heading": "## A\n- a",
    "KPI card": "## A {.kpi}\n1\ncaption",
}
NOT_FORM = {
    "bullets": "- a\n- b",
    "numbered list": "1. a\n2. b",
    "paragraph and bold": "**a** and *b*",
    "lead": "> lead\n- a",
    "conclusion": "- a\n> a takeaway",
    "@dark": "@dark\n- a",
    "@build": "@build\n- a",
}


@pytest.mark.parametrize("name", list(FORM))
def test_form_is_stated(name):
    assert "form" in _got(FORM[name]), name


@pytest.mark.parametrize("name", list(NOT_FORM))
def test_form_is_not_stated_by_the_default_list(name):
    assert "form" not in _got(NOT_FORM[name]), name


def test_form_from_a_slide_layout_word():
    for word in ("@blank", "@center"):
        assert "form" in _got(f"{word}\n- a")


EMPHASIS = {
    ".hero": "## A {.hero}\n- a",
    ".accent": "## A {.accent}\n- a",
    ".danger": "## A {.danger}\n- a",
    ".success": "## A {.success}\n- a",
    "==x==": "- the ==key number== grew",
    "span class": "- a [b]{.danger} c",
    "badge": "- a [new]{.badge .success}",
    "table hl": "{hl=a}\n| h | b |\n|---|---|\n| a | 2 |",
    "table hlcol": "{hlcol=2}\n| h | b |\n|---|---|\n| a | 2 |",
    "table note": '{note="why"}\n| h | b |\n|---|---|\n| a | 2 |',
    "chart hl": "```column {hl=Q1}\n,Q1,Q2\nA,1,2\n```",
    "chart note": '```column {note="why"}\n,Q1,Q2\nA,1,2\n```',
    "@noemph": "@noemph\n- a",
}
NOT_EMPHASIS = {
    "bullets": "- a",
    "bold and italic": "- **a** *b*",
    ".kpi": "## A {.kpi}\n1",
    ".muted": "## A {.muted}\n- a",
    ".primary": "## A {.primary}\n- a",
    "chart labels=on": "```column {labels=on}\n,Q1,Q2\nA,1,2\n```",
    "callout": "> [!note] hi",
}


@pytest.mark.parametrize("name", list(EMPHASIS))
def test_one_emphasis_is_stated(name):
    assert "emphasis" in _got(EMPHASIS[name]), name


@pytest.mark.parametrize("name", list(NOT_EMPHASIS))
def test_emphasis_is_not_stated_without_one(name):
    assert "emphasis" not in _got(NOT_EMPHASIS[name]), name


def test_a_takeaway_is_one_emphasis_however_many_marks_it_uses():
    # hl= + note= on one chart, a badge column in one table, two marks in one paragraph: one element each
    assert "emphasis" in _got('```column {hl=Q1 note="why"}\n,Q1,Q2\nA,1,2\n```')
    assert "emphasis" in _got("| a | b |\n|---|---|\n| [x]{.badge} | [y]{.badge .success} |")
    assert "emphasis" in _got("- ==x== and ==y==")


@pytest.mark.parametrize(
    "body",
    [
        "## A {.hero}\n- a\n## B {.accent}\n- b",
        "## A {.hero}\n- a ==b==",
        "@2\n## A\n- ==a==\n## B\n- ==b==",
        "{hl=a}\n| h | b |\n|---|---|\n| a | 2 |\n```column {hl=Q1}\n,Q1,Q2\nA,1,2\n```",
    ],
)
def test_two_emphases_are_not_one_decision(body):
    s = parse(f"# S\n{body}\n").slides[0]
    assert design.emphasis_count(s) == 2
    assert "emphasis" not in _got(body)


def test_noemph_wins_over_a_count():
    assert "emphasis" in _got("@noemph\n## A {.hero}\n- a\n## B {.accent}\n- b")


VALUES = {
    "size=": "{size=18}\n- a",
    "color=": "{color=#C00000}\n- a",
    "fill=": "## A {fill=#EEE}\n- a",
    "x y w h": "![x](a.png){x=1in y=1in w=2in h=1in}",
    "title size": None,  # filled below: a heading attribute
    "chart colors=": "```column {colors=#112233}\n,Q1,Q2\nA,1,2\n```",
    "chart size=": "```column {size=14}\n,Q1,Q2\nA,1,2\n```",
    "chart labels=<pos>": "```column {labels=outside}\n,Q1,Q2\nA,1,2\n```",
    "table widths=": "{widths=3:1}\n| a | b |\n|---|---|\n| 1 | 2 |",
    "table rowh=": "{rowh=0.5in}\n| a | b |\n|---|---|\n| 1 | 2 |",
    "table align=": "{align=lr}\n| a | b |\n|---|---|\n| 1 | 2 |",
    "slide sizes: line": "sizes: body=12\n- a",
    "slide style: line": "style: radius=4\n- a",
    "@defaults": "@defaults\n- a",
    "@bg=": "@bg=#102030\n- a",
    "@dense": "@dense\n- a",
    "@gap=": "@gap=0.3in\n## A\n- a\n## B\n- b",
    "slide css fence": "- a\n```css\nh2 { color: #C2410C }\n```",
    "icon=": "## A {icon=yen}\n- a",
}
NOT_VALUES = {
    "bullets": "- a",
    ".kpi": "## A {.kpi}\n1",
    ".hero": "## A {.hero}\n- a",
    "chart labels=on": "```column {labels=on}\n,Q1,Q2\nA,1,2\n```",
    "chart hl and note": '```column {hl=Q1 note="why"}\n,Q1,Q2\nA,1,2\n```',
    "chart title": "```column {title=Revenue}\n,Q1,Q2\nA,1,2\n```",
    "derived percent": "```bar\n,Q1,Q2\nA,12%,30%\n```",
    "table hl": "{hl=a}\n| h | b |\n|---|---|\n| a | 2 |",
    "@build @t @hidden": "@build t=fade hidden\n- a",
    "steps": "@steps\n## One\n- a\n## Two\n- b",
    "@noemph": "@noemph\n- a",
}


@pytest.mark.parametrize("name", [k for k in VALUES if VALUES[k]])
def test_a_chosen_value_is_stated(name):
    assert "values" in _got(VALUES[name]), name


def test_a_value_on_the_title_counts():
    assert "values" in _stated_groups(parse("# S {size=30}\n- a\n").slides[0])
    assert "values" in _stated_groups(parse("# S {bg=#112233}\n- a\n").slides[0])


@pytest.mark.parametrize("name", list(NOT_VALUES))
def test_values_are_not_stated_by_a_block_kind_or_a_switch(name):
    assert "values" not in _got(NOT_VALUES[name]), name


def test_value_inside_a_nested_box():
    assert "values" in _got("@2\n## A {size=12}\n- x\n## B\n- z")
    assert "values" in _got("## A\n- x\n### Inner {fill=#EEE}\n- z\n")


def test_detection_is_table_driven():
    """A new field that lands in classes/attrs/style/box is a choice without new code."""
    from slidemark.ir import Text

    assert "values" in _stated_groups(Slide(elements=[Text(attrs={"brand_new_key": "1"})]))
    assert "values" in _stated_groups(Slide(elements=[Text(classes=["brand"])]))  # an own css class
    assert "form" in _stated_groups(Slide(elements=[Text()], classes=["whatever"]))  # an unknown `@` word
    assert "form" in _stated_groups(Slide(elements=[Text()], classes=["timeline"]))
    assert not _stated_groups(Slide(elements=[Text()]))
    assert not _stated_groups(Slide(elements=[Text()], classes=["build"]))
    # one tuple of element predicates and one of slide predicates per group
    for group in (design.FORM_ELEMENT, design.EMPHASIS_ELEMENT, design.VALUE_ELEMENT):
        assert isinstance(group, tuple) and all(callable(p) for p in group)
    for group in (design.FORM_SLIDE, design.EMPHASIS_SLIDE, design.VALUE_SLIDE):
        assert isinstance(group, tuple) and all(callable(p) for p in group)


def _stated_groups(slide: Slide) -> set[str]:
    return {g for g, ok in design.stated_groups(slide).items() if ok}


# --------------------------------------------------------------------------- the two directives


def test_noemph_and_defaults_are_slide_directives_without_warnings():
    d = parse("# S\n@noemph defaults\n- a\n")
    assert not d.diagnostics
    assert d.slides[0].classes == ["noemph", "defaults"]
    d = parse("# S\n@2 steps noemph\n## A\n- a\n## B\n- b\n@end\n")
    assert not [x for x in d.diagnostics if x.rule == "unknown-token"]


def test_a_misspelt_directive_is_caught():
    d = parse("# S\n@noemphs\n- a\n")
    assert any(x.rule == "unknown-token" and "noemph" in (x.hint or "") for x in d.diagnostics)


def test_directives_have_no_visual_effect(tmp_path):
    def slide_xml(text: str, name: str) -> bytes:
        from slidemark import build

        out = tmp_path / f"{name}.pptx"
        build(text, out, base_dir=tmp_path)
        xml = zipfile.ZipFile(out).read("ppt/slides/slide1.xml")
        return re.sub(rb"\{[0-9A-F-]{36}\}", b"G", xml)

    plain = "# S\n- a\n- b\n"
    marked = "# S\n@noemph defaults\n- a\n- b\n"
    assert slide_xml(plain, "a") == slide_xml(marked, "b")


def test_directives_survive_an_importer_round_trip(tmp_path):
    from slidemark import build
    from slidemark.importer import import_pptx

    text = (
        "colors: primary=#123456\n\n# One\n@noemph\n## A\n- a\n## B\n- b\n\n"
        "# Two\n@3 flow defaults\n## A\n- a\n## B\n- b\n## C\n- c\n\n"
        "# Three\n@defaults noemph\n- plain\n- list\n\n# Four\n- untouched\n- slide\n"
    )
    build(text, tmp_path / "a.pptx", base_dir=tmp_path)
    back, _ = import_pptx(tmp_path / "a.pptx", tmp_path)
    slides = parse(back).slides
    assert "noemph" in slides[0].classes and "defaults" not in slides[0].classes
    assert "defaults" in slides[1].classes and "noemph" not in slides[1].classes
    assert {"noemph", "defaults"} <= set(slides[2].classes)
    assert not {"noemph", "defaults"} & set(slides[3].classes)


# --------------------------------------------------------------------------- design-slide messages


def test_design_slide_names_the_missing_groups_per_slide():
    text = FRAME + "# Cover\nsub\n\n# A\n- a ==x==\n\n# B\n@defaults\n- b\n\n# C\n" + DECIDED
    got = _rules(text)["design-slide"]
    assert got.level == "warning" and got.slide is None and got.rule == "design-slide"
    assert got.message == "slides 2 (form, values), 3 (form, emphasis) are short of a decision"
    # the worked example of the spec: slides 4 (values), 8 (form, emphasis)
    text = FRAME + "".join(f"# S{i}\n{DECIDED}\n" for i in range(1, 8))
    text = text.replace("# S3\n" + DECIDED, "# S3\n@2 noemph\n## A\n- a\n## B\n- b\n")
    text = text.replace("# S7\n" + DECIDED, "# S7\n- plain\n")
    got = _rules(text)["design-slide"]
    assert got.message == "slides 3 (values), 7 (form, emphasis, values) are short of a decision"


def test_design_slide_hint_names_the_groups_and_the_two_directives():
    got = _rules(CONTENT_ONLY)["design-slide"]
    assert got.hint == design.SLIDE_HINT
    for word in ("form", "emphasis", "value", "@noemph", "@defaults"):
        assert word in got.hint
    assert len(got.hint) <= 180


def test_design_slide_singular():
    assert _rules(BODY)["design-slide"].message == "slide 1 (form, emphasis, values) is short of a decision"


def test_two_emphases_are_reported_as_keep_one():
    text = FRAME + "# A\n@2 defaults\n## A {.hero}\n- a\n## B {.accent}\n- b\n"
    got = _rules(text)["design-slide"]
    assert got.message == "slide 1 (emphasis: 2 stated, keep one) is short of a decision"
    assert (
        "emphasis: 2 stated, keep one"
        in _rules(FRAME + "# A\n@2 defaults\n## A ==x==\n## B ==y==\n")["design-slide"].message
    )
    # the facts line keeps the plain group name
    assert design.facts(parse(text)).endswith("; short: 1 (emphasis)")


def test_design_slide_message_caps_a_long_list():
    text = FRAME + "".join(f"# S{i}\n- a\n\n" for i in range(1, 15))
    msg = _rules(text)["design-slide"].message
    assert msg.startswith("slides 1 (form, emphasis, values), 2 (form, emphasis, values)")
    assert " and 6 more are short of a decision" in msg


def test_cover_and_section_slides_are_exempt():
    text = "# Cover\nSubtitle\n\n# Part two\n@section\n\n# Facts\n" + DECIDED
    assert "design-slide" not in _rules(text)
    assert design.exempt(parse("# Cover\nSubtitle\n").slides[0])
    assert design.exempt(parse("# Part\n@section\n").slides[0])
    # exempt slides are left out of both numbers
    assert design.facts(parse(text)).endswith("1/1 slides decided form+emphasis+values")


def test_notes_only_and_title_only_slides_are_exempt():
    text = "# Divider\n??? say the agenda out loud\n\n# Next\n" + DECIDED
    assert _short(text) == {}


def test_a_content_slide_without_decisions_is_short_of_all_three():
    assert _short("# One\n- a\n- b\n") == {1: ["form", "emphasis", "values"]}


def test_the_decided_slide_passes_and_every_group_is_needed():
    assert _short("# S\n" + DECIDED) == {}
    assert _short("# S\n@2 defaults\n## A\n- a\n## B\n- b\n") == {1: ["emphasis"]}
    assert _short("# S\n@2 noemph\n## A\n- a\n## B\n- b\n") == {1: ["values"]}
    assert _short("# S\n@noemph defaults\n- a\n- b\n") == {1: ["form"]}


def test_choice_in_title_attrs_and_nested_boxes():
    assert _short("# S {size=30}\n@2 noemph\n## A\n- a\n## B\n- b\n") == {}
    assert _short("# S {bg=#112233}\n@2 noemph\n## A\n- a\n## B\n- b\n") == {}
    assert _short("# S\n@2 defaults\n## A\n- x ==y==\n## B\n- z\n") == {}
    assert _short("# S\n@defaults\n## A\n- x\n### Inner {.accent}\n- z\n") == {}


def test_choice_on_lead_conclusion_footnote():
    assert _short("# S\n@2 defaults\n## A\n- a\n## B\n- b\n> a takeaway with ==emphasis==\n") == {}


def test_plain_markdown_emphasis_does_not_count():
    # bold, italic, links and a callout without more: only the block kind
    text = "# S\n- **bold** and *italic* and [link](http://x.y)\n> [!note] heads up\n"
    assert _short(text) == {1: ["emphasis", "values"]}


# --------------------------------------------------------------------------- facts line


def test_facts_none():
    assert design.facts(parse(CONTENT_ONLY)) == (
        "design: none; 0/2 slides decided form+emphasis+values; short: 2 (form, emphasis, values), "
        "3 (form, emphasis, values)"
    )


def test_facts_text_and_short_list():
    text = (
        FRAME
        + "footer: ACME\nnum: on\n\n# Cover\nsub\n\n# A\n"
        + DECIDED
        + "\n# B\n@defaults\n- b\n\n# C\n- c\n"
    )
    assert design.facts(parse(text)) == (
        "design: colors fonts sizes style footer num; 1/3 slides decided form+emphasis+values; "
        "short: 3 (form, emphasis), 4 (form, emphasis, values)"
    )


def test_facts_all_decided_has_no_short_list():
    line = design.facts(parse(FRAME + "footer: ACME\n\n# A\n" + DECIDED))
    assert line == "design: colors fonts sizes style footer; 1/1 slides decided form+emphasis+values"


def test_facts_lists_stated_keys_in_fixed_order():
    text = "footer: ACME\nstyle: radius=8\nfonts: heading=Georgia\ncolors: primary=#7C5CFF\n\n# A\n" + DECIDED
    assert design.facts(parse(text)).startswith("design: colors fonts style footer; ")


def test_facts_css_theme_file_and_num():
    text = "theme: ./b.yaml\nnum: on\n```css\nh1 { color: red }\n```\n\n# A\n" + DECIDED
    assert design.facts(parse(text)) == "design: css theme-file num; 1/1 slides decided form+emphasis+values"


def test_facts_is_one_line_without_colour():
    line = design.facts(parse(CONTENT_ONLY))
    assert "\n" not in line and "\x1b" not in line


def test_build_prints_facts_before_look(tmp_path, capsys):
    f = tmp_path / "d.md"
    f.write_text(FRAME + "# A\n" + DECIDED, encoding="utf-8")
    assert main(["build", str(f), "-o", str(tmp_path / "d.pptx")]) == 0
    err = capsys.readouterr()
    lines = (err.out + err.err).splitlines()
    i = next(n for n, x in enumerate(lines) if x.startswith("design: "))
    j = next(n for n, x in enumerate(lines) if x.startswith("look: "))
    assert i + 1 == j
    assert lines[i] == "design: colors fonts sizes style; 1/1 slides decided form+emphasis+values"
    assert lines[-1].startswith("wrote ")
    assert not any("design-" in x for x in lines)


def test_build_prints_both_warnings_and_the_facts_line(tmp_path, capsys):
    f = tmp_path / "d.md"
    f.write_text(CONTENT_ONLY, encoding="utf-8")
    assert main(["build", str(f), "-o", str(tmp_path / "d.pptx")]) == 0
    text = (lambda c: c.out + c.err)(capsys.readouterr())
    assert "warning design-none: design: colors: fonts: sizes: style: not stated -> add colors:" in text
    assert (
        "warning design-slide: slides 2 (form, emphasis, values), 3 (form, emphasis, values) "
        "are short of a decision -> per slide state form" in text
    )
    assert "design: none; 0/2 slides decided form+emphasis+values; short: 2 (form, emphasis, values)" in text
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
    assert by_rule["design-none"]["message"] == "design: colors: fonts: sizes: style: not stated"
    assert by_rule["design-none"]["level"] == "warning" and by_rule["design-none"]["slide"] is None
    assert by_rule["design-slide"]["message"].startswith("slides 2 (form, emphasis, values)")
    assert by_rule["design-slide"]["hint"] == design.SLIDE_HINT


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


@pytest.mark.parametrize("path", sorted(EXAMPLES.glob("*.md")), ids=lambda p: p.name)
def test_examples_state_their_design(path):
    """The examples are what agents copy: each one states four header lines and three groups per slide."""
    got = _rules(path.read_text(encoding="utf-8"))
    assert not got, {k: v.message for k, v in got.items()}


@pytest.mark.parametrize("path", sorted(EXAMPLES.glob("*.md")), ids=lambda p: p.name)
def test_every_example_decides_every_slide(path):
    d = parse(path.read_text(encoding="utf-8"))
    line = design.facts(d)
    m = re.fullmatch(r"design: [a-z\- ]+; (\d+)/(\d+) slides decided form\+emphasis\+values", line)
    assert m, line
    assert m.group(1) == m.group(2) and 0 < int(m.group(2)) <= len(d.slides)


def test_skill_patterns_state_their_design():
    """Both ````markdown patterns of SKILL.md pass the tightened rules."""
    fence = re.compile(r"^(`{3,})markdown\n(.*?)^\1\s*$", re.S | re.M)
    patterns = [m.group(2) for m in fence.finditer(SKILL.read_text(encoding="utf-8"))]
    assert len(patterns) >= 2
    for body in patterns[:2]:
        got = _rules(body)
        assert not got, {k: v.message for k, v in got.items()}


@pytest.mark.parametrize("path", sorted(EXAMPLES.glob("*.md")), ids=lambda p: p.name)
def test_every_example_gets_feedback_without_crashing(path):
    d = parse(path.read_text(encoding="utf-8"))
    out = design.design_diagnostics(d)
    assert {x.rule for x in out} <= {"design-none", "design-slide"}
    assert design.facts(d).startswith("design: ")


def test_content_only_deck_string_fires_both():
    got = _rules("# Quarterly review\n- Revenue grew\n- Costs fell\n\n# Next steps\n- Hire\n- Ship\n")
    assert set(got) == {"design-none", "design-slide"}
    assert got["design-slide"].message == (
        "slides 1 (form, emphasis, values), 2 (form, emphasis, values) are short of a decision"
    )


def test_review_loop_is_not_asked_about_design(tmp_path):
    from slidemark.selfreview import analyze

    ana = analyze(CONTENT_ONLY, tmp_path)
    assert not any(d.rule in ("design-none", "design-slide") for d in ana.diags)
