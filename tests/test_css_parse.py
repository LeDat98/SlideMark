"""```css fences: placement, selectors, every property mapping, diagnostics."""

import pytest

from slidemark.ir import Code
from slidemark.parser import parse


def fence(css: str) -> str:
    return "```css\n" + css + "\n```\n"


def one(decl: str):
    """Style of the `h1` rule parsed from `h1 { <decl> }` in slide 1, and the css diagnostics."""
    deck = parse("# A\n" + fence(f"h1 {{ {decl} }}"))
    rules = deck.slides[0].css
    css_diags = [d for d in deck.diagnostics if (d.rule or "").startswith("css")]
    return (rules[0].style if rules else None), css_diags


def st(decl: str):
    s, diags = one(decl)
    assert not diags, diags
    assert s is not None
    return s


# --------------------------------------------------------------------------- placement


def test_header_fence_goes_to_deck_css_and_is_not_drawn():
    deck = parse("title: T\n" + fence("h1 { color: red }") + "\n# A\n- x\n")
    assert [r.selector for r in deck.css] == ["h1"]
    assert deck.title == "T"
    assert deck.slides[0].css == []
    assert deck.slides[0].elements and not any(isinstance(e, Code) for e in deck.slides[0].elements)
    assert not deck.diagnostics


def test_slide_fence_goes_to_slide_css():
    deck = parse("# A\n- x\n" + fence("p { color: blue }") + "# B\n- y\n")
    assert [r.selector for r in deck.slides[0].css] == ["p"]
    assert deck.slides[1].css == []
    assert deck.css == []
    assert not any(isinstance(e, Code) for s in deck.slides for e in s.elements)


def test_fence_inside_box_belongs_to_slide():
    deck = parse("# A\n## Box\n- x\n" + fence(".box { color: red }") + "## Two\n- y\n")
    assert [r.selector for r in deck.slides[0].css] == [".box"]
    assert not any(isinstance(e, Code) for e in deck.slides[0].elements)


def test_css_fence_line_numbers():
    deck = parse("# A\n" + fence("h1 { color: red }\nh2 { colour: red }"))
    d = [x for x in deck.diagnostics if x.rule == "css-property"][0]
    assert d.line == 4
    assert deck.slides[0].css[0].line == 3
    assert d.slide == 1


def test_other_fences_untouched():
    deck = parse("# A\n```python\nprint(1)\n```\n")
    assert any(isinstance(e, Code) for e in deck.slides[0].elements)


# --------------------------------------------------------------------------- selectors


def sels(css: str):
    deck = parse("# A\n" + fence(css))
    return [r.selector for r in deck.slides[0].css], [d for d in deck.diagnostics if d.rule == "css-selector"]


@pytest.mark.parametrize(
    "src,norm",
    [
        ("slide", "slide"),
        ("h1", "h1"),
        (".box", ".box"),
        ("#hero", "#hero"),
        ("slide.cover", "slide.cover"),
        ("td:nth-child(even)", "td:nth-child(even)"),
        ("tr:nth-child( odd )", "tr:nth-child(odd)"),
        ("li:nth-child(3)", "li:nth-child(3)"),
        ("p:first-child", "p:first-child"),
        ("p:last-child", "p:last-child"),
        (".box   h2", ".box h2"),
        (".box>h2", ".box > h2"),
        (".box  >   h2.x", ".box > h2.x"),
        ("tr:nth-child(even) td", "tr:nth-child(even) td"),
        ("table.zebra > tr > td", "table.zebra > tr > td"),
    ],
)
def test_valid_selectors(src, norm):
    got, diags = sels(f"{src} {{ color: red }}")
    assert got == [norm] and not diags


def test_comma_list_split_with_same_style():
    deck = parse("# A\n" + fence("h1, h2 ,p { color: red }"))
    rules = deck.slides[0].css
    assert [r.selector for r in rules] == ["h1", "h2", "p"]
    assert all(r.style.color == "#FF0000" for r in rules)


@pytest.mark.parametrize(
    "bad",
    [
        "a[href]",
        "h1 + p",
        "h1 ~ p",
        "p::before",
        "a:hover",
        "*",
        "body",
        "h1 >",
        "> h1",
        "div",
        "h7",
        ".a:not(.b)",
    ],
)
def test_invalid_selectors_warn_and_skip(bad):
    got, diags = sels(f"{bad} {{ color: red }}\nh2 {{ color: blue }}")
    assert got == ["h2"]
    assert len(diags) == 1 and diags[0].hint and "\n" not in diags[0].hint


def test_partly_invalid_comma_list_keeps_valid_part():
    got, diags = sels("h1, a:hover { color: red }")
    assert got == ["h1"] and len(diags) == 1


# --------------------------------------------------------------------------- colors and fill


def test_color():
    assert st("color: #7c5cff").color == "#7C5CFF"


@pytest.mark.parametrize(
    "val,out",
    [
        ("#abc", "#AABBCC"),
        ("#abcd", "#AABBCCDD"),
        ("#aabbcc", "#AABBCC"),
        ("#aabbcc80", "#AABBCC80"),
        ("rgb(255, 0, 0)", "#FF0000"),
        ("rgb(255 0 0)", "#FF0000"),
        ("rgba(0, 0, 0, 0.5)", "#00000080"),
        ("rgba(0,0,0,1)", "#000000"),
        ("rgb(0 0 0 / 50%)", "#00000080"),
        ("orange", "#FFA500"),
        ("White", "#FFFFFF"),
        ("transparent", "#00000000"),
        ("primary", "primary"),
        ("var(--brand)", "brand"),
        ("var(--brand, #fff)", "brand"),
    ],
)
def test_color_forms(val, out):
    assert st(f"color: {val}").color == out


def test_background_color_and_shorthand():
    assert st("background-color: #F6F7FB").fill == "#F6F7FB"
    assert st("background: #f6f7fb").fill == "#F6F7FB"
    assert st("background: rgb(1,2,3) no-repeat").fill == "#010203"


def test_background_gradient_kept_with_normalized_colors():
    s = st("background: linear-gradient(135deg, #141a2e, rgba(0,0,0,.5) 50%, primary)")
    assert s.fill == "linear-gradient(135deg, #141A2E, #00000080 50%, primary)"
    s = st("background: radial-gradient(circle, #fff, #000)")
    assert s.fill == "radial-gradient(circle, #FFFFFF, #000000)"


def test_background_url_kept():
    assert st("background: url('img/bg.png') center").fill == "url(img/bg.png)"
    assert st("background: url(a.png)").fill == "url(a.png)"


# --------------------------------------------------------------------------- border


def test_border_shorthand():
    s = st("border: 2px dashed #00d1b2")
    assert (s.line, s.line_width, s.line_dash) == ("#00D1B2", 1.5, "dash")
    s = st("border: 1pt dotted red")
    assert (s.line_width, s.line_dash) == (1.0, "dot")
    assert st("border: none").line_width == 0.0


def test_border_sides_canonical():
    s = st(
        "border-bottom: 2px solid #00D1B2; border-top: 1pt dashed red; "
        "border-left: none; border-right: 4px dotted"
    )
    assert s.border_bottom == "1.5pt solid #00D1B2"
    assert s.border_top == "1pt dash #FF0000"
    assert s.border_left == "none"
    assert s.border_right == "3pt dot fg"


def test_border_color_width_style():
    assert st("border-color: #abc").line == "#AABBCC"
    assert st("border-width: 4px").line_width == 3.0
    assert st("border-width: thin").line_width == 0.75
    assert st("border-style: dashed").line_dash == "dash"
    assert st("border-style: dotted").line_dash == "dot"
    assert st("border-style: none").line_width == 0.0


def test_border_multi_value_distinct_warns():
    s, diags = one("border-color: red blue")
    assert s is None and diags[0].rule == "css-value" and "border-top" in diags[0].hint


def test_border_radius():
    assert st("border-radius: 14px").radius == 10.5
    assert st("border-radius: 8pt").radius == 8.0
    s, diags = one("border-radius: 50%")
    assert s is None and diags[0].rule == "css-value"


# --------------------------------------------------------------------------- effects


def test_box_shadow():
    assert st("box-shadow: 0 8px 24px #0006").shadow == "0 6 18 #00000066"
    assert st("box-shadow: 0 4px 12px 2px rgba(0,0,0,.3)").shadow == "0 3 9 1.5 #0000004C"
    assert st("box-shadow: #112233 2px 2px").shadow == "1.5 1.5 0 #112233FF"
    assert st("box-shadow: none").shadow is False


def test_box_shadow_inset_and_layers():
    s, diags = one("box-shadow: inset 0 0 4px red")
    assert s is None and diags[0].rule == "css-value"
    s, diags = one("box-shadow: 0 1px 2px red, 0 4px 8px blue")
    assert s.shadow == "0 0.75 1.5 #FF0000FF" and len(diags) == 1


def test_opacity():
    assert st("opacity: 0.8").opacity == 0.8
    assert st("opacity: 80%").opacity == 0.8
    assert st("opacity: 3").opacity == 1.0
    s, diags = one("opacity: lots")
    assert s is None and diags[0].rule == "css-value"


# --------------------------------------------------------------------------- font and text


def test_font_family_first_unquoted():
    assert st("font-family: 'Noto Sans JP', Arial, sans-serif").font == "Noto Sans JP"
    assert st('font-family: "Yu Gothic"').font == "Yu Gothic"
    assert st("font-family: Inter").font == "Inter"


def test_font_size_units():
    assert st("font-size: 16px").font_size == 12.0
    assert st("font-size: 14pt").font_size == 14.0
    assert st("font-size: 1.5em").font_size == 18.0
    assert st("font-size: 0.5in").font_size == 36.0
    assert st("font-size: 1cm").font_size == pytest.approx(28.346, abs=1e-3)
    assert st("font-size: 10mm").font_size == pytest.approx(28.346, abs=1e-3)


@pytest.mark.parametrize(
    "v,b", [("bold", True), ("700", True), ("600", True), ("500", False), ("normal", False)]
)
def test_font_weight(v, b):
    assert st(f"font-weight: {v}").bold is b


def test_font_style():
    assert st("font-style: italic").italic is True
    assert st("font-style: normal").italic is False


def test_letter_spacing():
    assert st("letter-spacing: 1pt").letter_spacing == 1.0
    assert st("letter-spacing: 2px").letter_spacing == 1.5
    assert st("letter-spacing: 0.1em; font-size: 20pt").letter_spacing == 2.0
    assert st("letter-spacing: normal").letter_spacing == 0.0


def test_line_height():
    assert st("line-height: 1.4").line_spacing == 1.4
    assert st("line-height: 150%").line_spacing == 1.5
    assert st("line-height: 1.2em").line_spacing == 1.2
    assert st("line-height: 24px; font-size: 12pt").line_spacing == 1.5
    s, diags = one("line-height: 24px")
    assert s is None and diags[0].rule == "css-value" and "unitless" in diags[0].hint


@pytest.mark.parametrize(
    "v,o",
    [("left", "left"), ("center", "center"), ("right", "right"), ("justify", "justify"), ("end", "right")],
)
def test_text_align(v, o):
    assert st(f"text-align: {v}").align == o


@pytest.mark.parametrize("v", ["top", "middle", "bottom"])
def test_vertical_align(v):
    assert st(f"vertical-align: {v}").valign == v


@pytest.mark.parametrize(
    "v,o", [("uppercase", "upper"), ("lowercase", "lower"), ("capitalize", "capitalize"), ("none", "none")]
)
def test_text_transform(v, o):
    assert st(f"text-transform: {v}").text_transform == o


def test_text_decoration():
    s = st("text-decoration: underline")
    assert (s.underline, s.strike) == (True, None)
    s = st("text-decoration: line-through")
    assert (s.underline, s.strike) == (None, True)
    s = st("text-decoration: underline line-through red")
    assert (s.underline, s.strike) == (True, True)
    s = st("text-decoration: none")
    assert (s.underline, s.strike) == (False, False)


# --------------------------------------------------------------------------- box


def test_padding_shorthand_forms():
    s = st("padding: 8px")
    assert (s.padding, s.padding_top, s.padding_right, s.padding_bottom, s.padding_left) == (6, 6, 6, 6, 6)
    s = st("padding: 8px 16px")
    assert (s.padding_top, s.padding_right, s.padding_bottom, s.padding_left) == (6, 12, 6, 12)
    assert s.padding is None
    s = st("padding: 4px 8px 12px")
    assert (s.padding_top, s.padding_right, s.padding_bottom, s.padding_left) == (3, 6, 9, 6)
    s = st("padding: 4px 8px 12px 16px")
    assert (s.padding_top, s.padding_right, s.padding_bottom, s.padding_left) == (3, 6, 9, 12)


def test_padding_sides():
    s = st("padding-top: 4pt; padding-right: 8pt; padding-bottom: 0; padding-left: 1in")
    assert (s.padding_top, s.padding_right, s.padding_bottom, s.padding_left) == (4, 8, 0, 72)


def test_padding_too_many_values():
    s, diags = one("padding: 1px 2px 3px 4px 5px")
    assert s is None and diags[0].rule == "css-value"


def test_margin_and_gap():
    assert st("margin: 8px").margin == 6.0
    assert st("gap: 16px").gap == 12.0
    assert st("gap: 12px 12px").gap == 9.0
    s, diags = one("margin: 1px 2px")
    assert s is None and diags[0].rule == "css-value"


def test_grid_columns():
    assert st("grid-template-columns: 1fr 2fr").grid == "1:2"
    assert st("grid-template-columns: repeat(3, 1fr)").grid == "3"
    assert st("grid-template-columns: 1fr 1fr").grid == "2"
    assert st("grid-template-columns: 2fr 1fr 1fr").grid == "2:1:1"
    assert st("grid-template-columns: repeat(2, 1fr 2fr)").grid == "1:2:1:2"
    assert st("grid-template-columns: 0.5fr 1fr").grid == "0.5:1"
    s, diags = one("grid-template-columns: 100px auto")
    assert s is None and diags[0].rule == "css-value" and "fr" in diags[0].hint


def test_grid_areas():
    assert st('grid-template-areas: "a a b" "a a c"').grid == "aab/aac"
    assert st("grid-template-areas: 'x .' 'x y'").grid == "a./ab"
    s, diags = one('grid-template-areas: "a b" "a"')
    assert s is None and diags[0].rule == "css-value"


def test_transform_rotate():
    assert st("transform: rotate(-2deg)").rotation == -2.0
    assert st("transform: rotate(0.25turn)").rotation == 90.0
    s, diags = one("transform: rotate(5deg) scale(2)")
    assert s.rotation == 5.0 and len(diags) == 1 and "rotate" in diags[0].hint
    s, diags = one("transform: translate(5px)")
    assert s is None and diags[0].rule == "css-value"


# --------------------------------------------------------------------------- syntax and diagnostics


def test_comments_and_important_and_multiple_rules():
    deck = parse(
        "# A\n" + fence("/* c */ h1 { color: red !important; /* x */ }\n/* y\n z */ p { color: blue }")
    )
    r = deck.slides[0].css
    assert [x.selector for x in r] == ["h1", "p"]
    assert r[0].style.color == "#FF0000" and r[1].style.color == "#0000FF"
    assert not deck.diagnostics
    assert r[1].line == 5


def test_later_declaration_wins_in_rule():
    assert st("color: red; color: blue").color == "#0000FF"


def test_at_rules_warn_and_skip():
    deck = parse(
        "# A\n"
        + fence("@import url(x.css);\n@media (min-width: 1px) { h1 { color: red } }\nh2 { color: blue }")
    )
    assert [r.selector for r in deck.slides[0].css] == ["h2"]
    assert [d.rule for d in deck.diagnostics].count("css-at-rule") == 2


def test_unknown_property_suggests_closest():
    s, diags = one("colour: red; font-sise: 12px; wobble: 1")
    assert s is None
    assert [d.rule for d in diags] == ["css-property"] * 3
    assert "'color'" in diags[0].hint and "'font-size'" in diags[1].hint
    assert all(d.line == 3 for d in diags)


@pytest.mark.parametrize(
    "decl",
    [
        "color: notacolor",
        "color: #12",
        "color:",
        "font-size: big",
        "font-size: 12",
        "text-align: middle",
        "color red",
    ],
)
def test_bad_values_never_silent(decl):
    s, diags = one(decl)
    assert s is None
    assert len(diags) == 1 and diags[0].hint


def test_valid_decls_kept_when_others_fail():
    s, diags = one("color: red; wobble: 1; font-size: 10pt")
    assert s.color == "#FF0000" and s.font_size == 10.0 and len(diags) == 1


def test_unbalanced_and_garbage_never_raise():
    for css in [
        "h1 { color: red",
        "h1 color: red }",
        "}}}{{{",
        "h1 {{ a { } }",
        "/* open",
        "@",
        "{ }",
        ":",
        "h1 { ; ; }",
    ]:
        deck = parse("# A\n" + fence(css) + "- x\n")
        assert deck.slides


def test_unclosed_brace_still_maps_rule():
    deck = parse("# A\n" + fence("h1 { color: red"))
    assert deck.slides[0].css[0].style.color == "#FF0000"
    assert any(d.rule == "css-syntax" for d in deck.diagnostics)


# --------------------------------------------------------------------------- custom properties


def test_root_vars_become_color_tokens_and_var_resolves():
    deck = parse(
        "```css\n:root { --primary: #7c5cff; --brand-2: rgb(0,209,178) }\n"
        "h1 { color: var(--primary) }\n```\n# A\n"
    )
    assert deck.tokens["colors.primary"] == "#7C5CFF"
    assert deck.tokens["colors.brand-2"] == "#00D1B2"
    assert deck.css[0].style.color == "primary"
    assert [r.selector for r in deck.css] == ["h1"]
    assert not deck.diagnostics


def test_root_var_in_slide_fence_warns():
    deck = parse("# A\n" + fence(":root { --x: #fff }"))
    assert "colors.x" not in deck.tokens
    assert any(d.rule == "css-property" for d in deck.diagnostics)


def test_slide_rule_custom_property_warns():
    s, diags = one("--x: #fff")
    assert s is None and diags[0].rule == "css-property"


def test_theme_names_pass_and_unknown_names_warn():
    assert st("color: primary").color == "primary"
    s, diags = one("color: primry")
    assert s is None and "primary" in diags[0].hint


def test_property_count():
    from slidemark.parser.css import SUPPORTED

    assert len(SUPPORTED) >= 30
