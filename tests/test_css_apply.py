"""CSS fences applied to the IR (DF3): selector matching in layout, native mappings in the .pptx."""

from __future__ import annotations

import time

import pytest
from pptx import Presentation
from pptx.oxml.ns import qn

from slidemark.build import build_deck
from slidemark.ir import Deck, Paragraph, Run, Style
from slidemark.layout import layout_slide
from slidemark.layout.css import CssIndex, compile_selector
from slidemark.parser import parse
from slidemark.theme import get_theme

HEAD = "theme: none\ncolors: bg=#FFFFFF fg=#222222 primary=#2255CC\n\n"
EMU_PT = 12700


def css(rules: str) -> str:
    return f"```css\n{rules}\n```\n\n"


def build(md: str, tmp_path, name="o.pptx"):
    deck = parse(md)
    out = tmp_path / name
    build_deck(deck, out, tmp_path)
    return Presentation(str(out)), deck


def shapes(prs, prefix: str, slide: int = 0):
    return [s for s in prs.slides[slide].shapes if s.name.startswith(prefix)]


def one(prs, prefix: str, slide: int = 0):
    got = shapes(prs, prefix, slide)
    assert got, f"no shape named {prefix}*: {[s.name for s in prs.slides[slide].shapes]}"
    return got[0]


def by_text(prs, text: str, slide: int = 0):
    for s in prs.slides[slide].shapes:
        if s.has_text_frame and text in s.text_frame.text.replace("\u00a0", " "):
            return s
    raise AssertionError(f"no shape with text {text!r}")


def rpr(shape):
    return shape._element.xpath(".//a:rPr")[0]


def codes(deck: Deck, rule: str):
    return [d for d in deck.diagnostics if d.rule == rule]


BOXES = "# T\n@2\n## Alpha\nfirst body\n## Beta\nsecond body\n"


# --------------------------------------------------------------------------- selector matching


def parsed_index(md: str) -> tuple[Deck, CssIndex]:
    deck = parse(md)
    return deck, CssIndex(deck, deck.slides[0], 0)


def test_compile_selector_specificity():
    assert compile_selector("h1").spec == (0, 0, 1)
    assert compile_selector(".box > h2").spec == (0, 1, 1)
    assert compile_selector("#a.b:first-child").spec == (1, 2, 0)
    assert compile_selector("tr:nth-child(even) td").spec == (0, 1, 2)
    assert compile_selector("a ! b") is None


def test_h1_lead_conclusion_footnote_box_and_heading_match():
    md = HEAD + css(
        "h1 {color:#111111} .lead {color:#222222} .conclusion {color:#333333} .footnote {color:#444444}\n"
        ".box {color:#555555} .box > h2 {color:#666666}"
    )
    md += "# Title\n> the lead\n@2\n## A\nbody\n## B\nbody\n> the conclusion\n※ note\n"
    deck, ix = parsed_index(md)
    s = deck.slides[0]
    assert ix.own(s.title).color == "#111111"
    assert ix.own(s.lead).color == "#222222"
    assert ix.own(s.conclusion).color == "#333333"
    assert ix.own(s.footnotes[0]).color == "#444444"
    box = s.elements[0]
    assert ix.own(box).color == "#555555"
    assert ix.own(box.title).color == "#666666"  # h2 child of its box
    assert ix.own(box.children[0]).color == "#555555" or ix.own(box.children[0]).color is None


def test_specificity_beats_source_order_and_later_wins_on_ties():
    md = HEAD + css(".box {color:#111111}\n#x {color:#222222}\n.box {color:#333333}\n.hero {color:#444444}")
    md += "# T\n@1\n## A {#x .hero}\nbody\n"
    deck, ix = parsed_index(md)
    assert ix.own(deck.slides[0].elements[0]).color == "#222222"  # id beats classes, later .box beats earlier
    md2 = HEAD + css(".box {color:#111111}\n.hero {color:#444444}\n.box {color:#333333}")
    md2 += "# T\n@1\n## A {.hero}\nbody\n"
    deck, ix = parsed_index(md2)
    assert ix.own(deck.slides[0].elements[0]).color == "#333333"  # same specificity: the later rule wins


def test_deck_css_before_slide_css():
    md = HEAD + css("h1 {color:#111111}") + "# T\n" + css("h1 {color:#999999}") + "@1\n## A\nb\n"
    deck, ix = parsed_index(md)
    assert ix.own(deck.slides[0].title).color == "#999999"


def test_inline_style_wins_over_css():
    md = HEAD + css("h1 {color:#111111; font-weight: bold}") + "# T {color=#ABCDEF}\nbody\n"
    deck = parse(md)
    items = layout_slide(deck.slides[0], deck, get_theme("default"), 0)
    title = next(p for p in items if p.element.role == "title")
    assert title.style.color.upper() == "#ABCDEF"
    assert title.style.bold is True


def test_descendant_vs_child_combinators_and_nth_child():
    md = HEAD + css(
        ".box p {color:#111111}\n.box > p {color:#222222}\n.box > h2:first-child {color:#333333}\n"
        ".box:nth-child(3) {color:#444444}\nslide .box:last-child {color:#555555}"
    )
    md += "# T\n@2\n## A\nbody a\n## B\nbody b\n"
    deck, ix = parsed_index(md)
    a, b = deck.slides[0].elements
    assert ix.own(a.children[0]).color == "#222222"  # child rule later than descendant rule, same specificity
    assert ix.own(a.title).color == "#333333"
    assert ix.own(a).color is None
    assert (
        ix.own(b).color == "#555555"
    )  # last-child (specificity 0,1,1 + .box) beats :nth-child(even)... same box


def test_slide_classes_cover_and_section():
    md = HEAD + css(
        "slide.cover h1 {color:#111111}\nslide.section h1 {color:#222222}\nslide h1 {font-size: 40pt}"
    )
    md += "# Cover\n\n---\n# Section\n\n---\n# Body\ntext\n- x\n"
    deck = parse(md)
    got = []
    for i, sl in enumerate(deck.slides):
        ix = CssIndex(deck, sl, i)
        got.append((ix.own(sl.title).color, ix.own(sl.title).font_size))
    assert got == [("#111111", 40.0), ("#222222", 40.0), (None, 40.0)]


def test_li_and_p_types():
    md = HEAD + css("li {color:#111111}\np {color:#222222}")
    md += "# T\n- one\n- two\n\nplain paragraph\n"
    deck, ix = parsed_index(md)
    text = deck.slides[0].elements[0]
    assert any(p.marker for p in text.paragraphs)
    assert ix.own(text).color == "#222222"  # a list-and-paragraph block matches both; the later rule wins
    md = HEAD + css("li {color:#111111}") + "# T\n- one\n- two\n"
    deck, ix = parsed_index(md)
    assert ix.own(deck.slides[0].elements[0]).color == "#111111"


def test_unmatched_selector_is_silent():
    md = HEAD + css(".nothing {color:#111111}\ntd {color:#222222}") + "# T\ntext\n"
    deck = parse(md)
    from slidemark.layout import layout_slide

    layout_slide(deck.slides[0], deck, get_theme("default"), 0)
    assert not [d for d in deck.diagnostics if d.rule and d.rule.startswith("css")]


def test_index_build_is_fast():
    rules = "\n".join(
        f".c{i} {{color:#11{i:02d}11}}\n.box > h2.c{i} {{font-size: {10 + i}pt}}" for i in range(15)
    )
    md = (
        HEAD
        + css(rules)
        + "# T\n@3x3\n"
        + "\n".join(f"## Box {i} {{.c{i % 15}}}\nbody {i}\n" for i in range(9))
    )
    deck = parse(md)
    t0 = time.perf_counter()
    for _ in range(5):
        ix = CssIndex(deck, deck.slides[0], 0)
        for box in deck.slides[0].elements:
            ix.own(box)
            ix.own(box.title)
    assert (time.perf_counter() - t0) / 5 < 0.05


# --------------------------------------------------------------------------- text mappings


def test_text_properties_become_run_properties(tmp_path):
    md = HEAD + css(
        "h1 {color:#AA0000; letter-spacing: 2pt; text-transform: uppercase; font-family: Georgia;"
        " font-size: 30pt; font-style: italic; text-decoration: underline line-through}\n"
        ".lead {text-align: center; line-height: 1.5}"
    )
    md += "# Title text\n> lead text\nbody\n"
    prs, deck = build(md, tmp_path)
    t = one(prs, "Title")
    r = rpr(t)
    assert t.text_frame.text == "TITLE TEXT"  # transform_text applied to the run
    assert r.get("spc") == "200"
    assert r.get("i") == "1"
    assert r.get("u") == "sng"
    assert r.get("strike") == "sngStrike"
    assert r.xpath("./a:latin")[0].get("typeface") == "Georgia"
    assert r.xpath("./a:solidFill/a:srgbClr")[0].get("val") == "AA0000"
    lead = one(prs, "Lead")
    assert lead._element.xpath(".//a:pPr")[0].get("algn") == "ctr"
    assert lead._element.xpath(".//a:lnSpc/a:spcPct")[0].get("val") == "150000"
    assert not codes(deck, "css-unsupported")


def test_font_size_and_weight(tmp_path):
    md = HEAD + css("p {font-size: 20pt; font-weight: 700}") + "# T\n@1\n## A\nplain body\n"
    prs, _ = build(md, tmp_path)
    r = rpr(by_text(prs, "plain body"))
    assert r.get("b") == "1"
    assert float(r.get("sz")) <= 2000


def test_capitalize_and_lowercase(tmp_path):
    md = HEAD + css(".box > h2 {text-transform: capitalize}\n.box p {text-transform: lowercase}")
    md += "# T\n@1\n## the big heading\nSHOUTING Body\n"
    prs, _ = build(md, tmp_path)
    assert by_text(prs, "Big Heading").text_frame.text.replace("\u00a0", " ") == "The Big Heading"
    assert by_text(prs, "shouting").text_frame.text == "shouting body"


def test_letter_spacing_and_transform_change_measured_height():
    from slidemark.layout import measure

    para = [Paragraph(runs=[Run(text="word " * 12)])]
    plain = measure.paragraphs_height(para, 3_000_000, Style(font_size=16))
    spaced = measure.paragraphs_height(para, 3_000_000, Style(font_size=16, letter_spacing=4))
    upper = measure.paragraphs_height(para, 3_000_000, Style(font_size=16, text_transform="upper"))
    assert spaced > plain
    assert upper >= plain


def test_opacity_on_text_without_fill_is_alpha(tmp_path):
    md = HEAD + css("p {opacity: 0.5}") + "# T\n@1\n## A\nfaded text\n"
    prs, _ = build(md, tmp_path)
    clr = rpr(by_text(prs, "faded text")).xpath("./a:solidFill/a:srgbClr")[0]
    assert clr.xpath("./a:alpha")[0].get("val") == "50000"


def test_vertical_align_and_padding_per_side_on_text(tmp_path):
    md = (
        HEAD
        + css("p {vertical-align: bottom; padding: 3pt 6pt 9pt 12pt; background: #EEEEEE}")
        + "# T\n@1\n## A\npadded text\n"
    )
    prs, _ = build(md, tmp_path)
    bp = by_text(prs, "padded text")._element.xpath(".//a:bodyPr")[0]
    assert bp.get("anchor") == "b"
    assert (bp.get("tIns"), bp.get("rIns"), bp.get("bIns"), bp.get("lIns")) == tuple(
        str(v * EMU_PT) for v in (3, 6, 9, 12)
    )


# --------------------------------------------------------------------------- box mappings


def test_box_gradient_shadow_radius_border_dash(tmp_path):
    md = HEAD + css(
        ".box {background: linear-gradient(135deg, #141A2E, #1E2540); border-radius: 16px;"
        " box-shadow: 0 8px 24px #0006; border: 2px dashed #FF8800}"
    )
    prs, _ = build(md + BOXES, tmp_path)
    sp = one(prs, "Card")._element.spPr
    assert [g.get("val") for g in sp.xpath("./a:gradFill//a:srgbClr")] == ["141A2E", "1E2540"]
    assert sp.xpath("./a:prstGeom")[0].get("prst") == "roundRect"
    assert sp.xpath("./a:effectLst/a:outerShdw")
    ln = sp.xpath("./a:ln")[0]
    assert ln.get("w") == str(round(1.5 * EMU_PT))
    assert ln.xpath("./a:solidFill/a:srgbClr")[0].get("val") == "FF8800"
    assert ln.xpath("./a:prstDash")[0].get("val") == "dash"


def test_dotted_border_uses_sysdot(tmp_path):
    md = HEAD + css(".box {border: 1px dotted #112233}")
    prs, _ = build(md + BOXES, tmp_path)
    assert one(prs, "Card")._element.spPr.xpath("./a:ln/a:prstDash")[0].get("val") == "sysDot"


def test_border_none_removes_the_theme_line(tmp_path):
    md = HEAD + css(".box {border: none; background: #EEEEEE}")
    prs, _ = build(md + BOXES, tmp_path)
    sp = one(prs, "Card")._element.spPr
    assert sp.xpath("./a:ln/a:noFill")


def test_box_padding_moves_the_content(tmp_path):
    base, _ = build(HEAD + BOXES, tmp_path, "a.pptx")
    md = HEAD + css(".box {padding: 20px 40px}") + BOXES
    padded, _ = build(md, tmp_path, "b.pptx")
    b0, b1 = by_text(base, "first body"), by_text(padded, "first body")
    c = one(padded, "Card")
    assert b1.left - c.left == 30 * EMU_PT  # 40px = 30pt
    assert b1.left - c.left > b0.left - one(base, "Card").left


def test_per_side_borders_draw_lines_not_a_closed_outline(tmp_path):
    md = HEAD + css(
        ".box {background:#EEEEEE; border: none; border-left: 4px solid #CC0000;"
        " border-bottom: 2px dashed #00AA00}"
    )
    prs, _ = build(md + BOXES, tmp_path)
    card = one(prs, "Card")
    assert not card._element.spPr.xpath("./a:ln/a:solidFill")  # no closed outline
    lines = [s for s in shapes(prs, "Card 1 border")]
    assert {s.name.rsplit(" ", 1)[1] for s in lines} == {"left", "bottom"}
    left = next(s for s in lines if s.name.endswith("left"))
    ln = left._element.xpath(".//a:ln")[0]
    assert ln.get("w") == str(3 * EMU_PT)
    assert ln.xpath("./a:solidFill/a:srgbClr")[0].get("val") == "CC0000"
    assert left.width == 0 and left.height == card.height
    bottom = next(s for s in lines if s.name.endswith("bottom"))
    assert bottom._element.xpath(".//a:ln/a:prstDash")[0].get("val") == "dash"
    assert bottom.top + 1 * EMU_PT >= card.top + card.height - 2 * EMU_PT


def test_heading_bottom_border_is_a_line_under_the_heading(tmp_path):
    md = HEAD + css(".box > h2 {color:#00D1B2; border-bottom: 2px solid #00D1B2}")
    prs, _ = build(md + BOXES, tmp_path)
    head = by_text(prs, "Alpha")
    line = one(prs, "Heading 1 border bottom") if shapes(prs, "Heading 1 border") else None
    assert line is not None
    assert line.top + 2 * EMU_PT >= head.top + head.height - 2 * EMU_PT
    assert head._element.xpath(".//a:bodyPr")[0].get("bIns") == str(round(1.5 * EMU_PT))


def test_rotation_sets_xfrm_rot_and_moves_children(tmp_path):
    md = HEAD + css(".hero {transform: rotate(-3deg); background: #FFEEAA}") + "# T\n@1\n## A {.hero}\nbody\n"
    prs, _ = build(md, tmp_path)
    card = one(prs, "Card")
    assert card._element.spPr.xpath("./a:xfrm")[0].get("rot") == str(round(357 * 60000))
    body = by_text(prs, "body")
    assert body._element.spPr.xpath("./a:xfrm")[0].get("rot") == str(357 * 60000)


def test_margin_shrinks_the_box_inside_its_cell(tmp_path):
    base, _ = build(HEAD + BOXES, tmp_path, "a.pptx")
    prs, _ = build(HEAD + css(".box {margin: 12px}") + BOXES, tmp_path, "b.pptx")
    c0, c1 = one(base, "Card"), one(prs, "Card")
    assert c1.left - c0.left == 9 * EMU_PT
    assert c0.width - c1.width == 18 * EMU_PT


def test_gap_between_boxes_in_a_container_and_on_the_slide(tmp_path):
    md = "# T\n@1\n## Outer\n@2\n### A\nleft\n### B\nright\n"
    base, _ = build(HEAD + md, tmp_path, "a.pptx")
    gapped, _ = build(HEAD + css(".box {gap: 40px}") + md, tmp_path, "b.pptx")

    def gap(prs):
        cards = sorted(shapes(prs, "Card"), key=lambda s: s.left)
        inner = [c for c in cards if c.width < max(x.width for x in cards)]
        return inner[1].left - (inner[0].left + inner[0].width)

    assert gap(gapped) == 30 * EMU_PT
    assert gap(gapped) > gap(base)


def test_grid_template_columns_acts_as_the_at_spec(tmp_path):
    md = HEAD + css(".split {grid-template-columns: 1fr 3fr}")
    md += "# T\n@1\n## Outer {.split}\nleft text\n\n```\ncode here\n```\n"
    prs, _ = build(md, tmp_path)
    left, code = by_text(prs, "left text"), by_text(prs, "code here")
    assert abs(left.top - code.top) < EMU_PT  # side by side
    assert code.left > left.left
    assert code.width / left.width == pytest.approx(3, rel=0.25)


def test_slide_grid_template_areas_and_columns(tmp_path):
    md = HEAD + css('slide {grid-template-areas: "a a" "b c"}') + "# T\n## A\nx\n## B\ny\n## C\nz\n"
    prs, _ = build(md, tmp_path)
    a, b, c = sorted(shapes(prs, "Card"), key=lambda s: (s.top, s.left))
    assert a.width > b.width * 1.8 and abs(a.width - (c.left + c.width - b.left)) < 2 * EMU_PT
    assert b.top == c.top and b.top > a.top and b.left < c.left
    md = HEAD + css("slide {grid-template-columns: 1fr 3fr}") + "# T\n## A\nx\n## B\ny\n"
    prs, _ = build(md, tmp_path, "c.pptx")
    a, b = sorted(shapes(prs, "Card"), key=lambda s: s.left)
    assert b.width / a.width == pytest.approx(3, rel=0.1)


def test_slide_gap_and_grid(tmp_path):
    md = HEAD + css("slide {gap: 30px}") + BOXES
    prs, _ = build(md, tmp_path)
    cards = sorted(shapes(prs, "Card"), key=lambda s: s.left)
    assert cards[1].left - (cards[0].left + cards[0].width) == round(22.5 * EMU_PT)


def test_image_fill_url_becomes_a_picture_fill(tmp_path):
    from PIL import Image

    Image.new("RGB", (40, 20), (200, 30, 30)).save(tmp_path / "bg.png")
    md = HEAD + css(".box {background: url(bg.png)}") + BOXES
    prs, deck = build(md, tmp_path)
    sp = one(prs, "Card")._element.spPr
    blip = sp.xpath("./a:blipFill/a:blip")[0]
    rid = blip.get(qn("r:embed"))
    assert rid in one(prs, "Card").part.rels
    assert sp.xpath("./a:blipFill/a:stretch")
    assert not codes(deck, "image-missing")


def test_missing_image_fill_gives_a_diagnostic(tmp_path):
    md = HEAD + css(".box {background: url(nope.png)}") + BOXES
    prs, deck = build(md, tmp_path)
    assert codes(deck, "image-missing")
    assert not one(prs, "Card")._element.spPr.xpath("./a:blipFill")


def test_unmappable_properties_get_css_unsupported(tmp_path):
    md = HEAD + css("img {padding: 4px; background: #EEEEEE}\n.chart {border-radius: 8px}") + "# T\ntext\n"
    md2 = md + "\n![alt text](pic.png)\n"
    from PIL import Image

    Image.new("RGB", (10, 10)).save(tmp_path / "pic.png")
    _, deck = build(md2, tmp_path)
    rules = codes(deck, "css-unsupported")
    assert any("background" in d.message for d in rules)
    assert all(d.hint for d in rules)


def test_rotate_on_a_table_is_reported(tmp_path):
    md = HEAD + css("table {transform: rotate(2deg)}") + "# T\n| a | b |\n|---|---|\n| 1 | 2 |\n"
    _, deck = build(md, tmp_path)
    assert codes(deck, "css-unsupported")


# --------------------------------------------------------------------------- slide background


def test_slide_background_solid(tmp_path):
    prs, _ = build(HEAD + css("slide {background: #102030}") + "# T\ntext\n", tmp_path)
    assert str(prs.slides[0].background.fill.fore_color.rgb) == "102030"


def test_slide_background_gradient_radial_and_linear(tmp_path):
    prs, _ = build(
        HEAD
        + css("slide {background: linear-gradient(90deg, #112233, #445566 60%, #778899)}")
        + "# T\ntext\n",
        tmp_path,
    )
    bg = prs.slides[0]._element.xpath("./p:cSld/p:bg/p:bgPr")[0]
    assert [c.get("val") for c in bg.xpath("./a:gradFill//a:srgbClr")] == ["112233", "445566", "778899"]
    assert bg.xpath("./a:gradFill/a:lin")[0].get("ang") == "0"
    prs, _ = build(
        HEAD + css("slide {background: radial-gradient(#000000, #FFFFFF)}") + "# T\nx\n", tmp_path, "r.pptx"
    )
    assert prs.slides[0]._element.xpath("./p:cSld/p:bg/p:bgPr/a:gradFill/a:path")


def test_slide_background_url_and_missing(tmp_path):
    from PIL import Image

    Image.new("RGB", (16, 9), (10, 200, 10)).save(tmp_path / "wall.png")
    prs, deck = build(HEAD + css("slide {background: url('wall.png')}") + "# T\nx\n", tmp_path)
    assert any(s.name == "Background" for s in prs.slides[0].shapes)
    _, deck = build(HEAD + css("slide {background: url(gone.png)}") + "# T\nx\n", tmp_path, "m.pptx")
    assert codes(deck, "image-missing")


def test_slide_cover_background_only_on_the_cover(tmp_path):
    md = HEAD + css("slide.cover {background: #AA0000}") + "# Cover\n\n---\n# Body\ntext\n- a\n"
    prs, _ = build(md, tmp_path)
    assert str(prs.slides[0].background.fill.fore_color.rgb) == "AA0000"
    assert str(prs.slides[1].background.fill.fore_color.rgb) == "FFFFFF"


def test_slide_color_and_font_reach_all_text(tmp_path):
    md = HEAD + css("slide {color: #CCDDEE; font-family: Verdana}") + "# T\n> lead\nbody\n"
    prs, _ = build(md, tmp_path)
    for text in ("lead", "body"):
        r = rpr(by_text(prs, text))
        assert r.xpath("./a:solidFill/a:srgbClr")[0].get("val") == "CCDDEE"
        assert r.xpath("./a:latin")[0].get("typeface") == "Verdana"


# --------------------------------------------------------------------------- tables

TABLE = "# T\n| name | qty |\n|---|---|\n| a | 1 |\n| b | 2 |\n| c | 3 |\n"


def cells(prs):
    tbl = next(s for s in prs.slides[0].shapes if s.has_table).table
    return [[c for c in row.cells] for row in tbl.rows]


def cell_fill(c):
    return c._tc.tcPr.xpath("./a:solidFill/a:srgbClr")[0].get("val")


def test_table_zebra_with_nth_child(tmp_path):
    prs, _ = build(HEAD + css("tr:nth-child(even) td {background: #F6F7FB}") + TABLE, tmp_path)
    rows = cells(prs)
    assert [cell_fill(r[0]) for r in rows[1:]] == ["F6F7FB", "FFFFFF", "F6F7FB"]


def test_table_th_td_color_bold_align_fill(tmp_path):
    md = HEAD + css(
        "th {background: #003366; color: #FFFFFF; text-align: right}\n"
        "td {color: #660000; font-weight: bold; background: #EEEEEE}\n"
        "td:first-child {font-style: italic}"
    )
    prs, _ = build(md + TABLE, tmp_path)
    rows = cells(prs)
    th = rows[0][1]
    assert cell_fill(th) == "003366"
    r = th._tc.xpath(".//a:rPr")[0]
    assert r.xpath("./a:solidFill/a:srgbClr")[0].get("val") == "FFFFFF"
    assert th._tc.xpath(".//a:pPr")[0].get("algn") == "r"
    td = rows[1][0]
    assert cell_fill(td) == "EEEEEE"
    r = td._tc.xpath(".//a:rPr")[0]
    assert r.get("b") == "1" and r.get("i") == "1"
    assert r.xpath("./a:solidFill/a:srgbClr")[0].get("val") == "660000"
    assert rows[1][1]._tc.xpath(".//a:rPr")[0].get("i") is None


def test_table_cell_borders_and_padding(tmp_path):
    md = HEAD + css(
        "th {border-bottom: 3px solid #FF0000}\ntd {border: 1px dashed #00AA00; padding: 4px 12px}"
    )
    prs, _ = build(md + TABLE, tmp_path)
    rows = cells(prs)
    lnb = rows[0][0]._tc.tcPr.find(qn("a:lnB"))
    assert lnb.get("w") == str(round(2.25 * EMU_PT))
    assert lnb.find(qn("a:solidFill")).find(qn("a:srgbClr")).get("val") == "FF0000"
    td = rows[1][0]._tc.tcPr
    assert td.find(qn("a:lnL")).find(qn("a:prstDash")).get("val") == "dash"
    assert td.find(qn("a:lnT")).find(qn("a:solidFill")).find(qn("a:srgbClr")).get("val") == "00AA00"
    assert (td.get("marL"), td.get("marT")) == (str(9 * EMU_PT), str(3 * EMU_PT))


def test_table_cell_gradient_fill(tmp_path):
    prs, _ = build(HEAD + css("th {background: linear-gradient(90deg, #112233, #445566)}") + TABLE, tmp_path)
    th = cells(prs)[0][0]
    assert th._tc.tcPr.xpath("./a:gradFill")
    assert [c.get("val") for c in th._tc.tcPr.xpath("./a:gradFill//a:srgbClr")] == ["112233", "445566"]


def test_row_height_follows_cell_padding(tmp_path):
    prs0, _ = build(HEAD + TABLE, tmp_path, "a.pptx")
    prs1, _ = build(HEAD + css("td {padding: 14px}") + TABLE, tmp_path, "b.pptx")
    t0 = next(s for s in prs0.slides[0].shapes if s.has_table).table
    t1 = next(s for s in prs1.slides[0].shapes if s.has_table).table
    # a stretched table shares its height among the body rows (compact header): padding can only raise them
    assert t1.rows[1].height >= t0.rows[1].height
    assert t1.cell(1, 0)._tc.tcPr.get("marT") != t0.cell(1, 0)._tc.tcPr.get("marT")


def test_table_level_text_transform_reaches_cells(tmp_path):
    prs, _ = build(HEAD + css("table {text-transform: uppercase}") + TABLE, tmp_path)
    assert cells(prs)[0][0].text_frame.text == "NAME"


# --------------------------------------------------------------------------- images


def test_image_border_radius_shadow_opacity(tmp_path):
    from PIL import Image

    Image.new("RGB", (40, 30), (1, 2, 3)).save(tmp_path / "p.png")
    md = HEAD + css(
        "img {border: 2px solid #AA00AA; border-radius: 12px; box-shadow: 0 4px 12px #0005; opacity: .8}"
    )
    prs, deck = build(md + "# T\n![a pic](p.png)\n", tmp_path)
    pic = next(s for s in prs.slides[0].shapes if s.shape_type == 13)
    sp = pic._element.spPr
    assert sp.xpath("./a:prstGeom")[0].get("prst") == "roundRect"
    assert sp.xpath("./a:ln/a:solidFill/a:srgbClr")[0].get("val") == "AA00AA"
    assert sp.xpath("./a:effectLst/a:outerShdw")
    assert pic._element.xpath(".//a:blip/a:alphaModFix")[0].get("amt") == "80000"
    assert not codes(deck, "css-unsupported")


# --------------------------------------------------------------------------- end to end

E2E = HEAD + css(
    """slide { background: linear-gradient(135deg, #0B1020, #1B2447) }
h1 { color: #7C5CFF; letter-spacing: 2pt; text-transform: uppercase; font-family: Georgia }
.lead { color: #AAB; font-style: italic; text-align: center }
.box { background: linear-gradient(135deg, #141A2E, #1E2540); border-radius: 14px;
       box-shadow: 0 8px 24px #0006; padding: 8px 16px; border: 1px dashed #445 }
.box > h2 { color: #00D1B2; border-bottom: 2px solid #00D1B2; text-decoration: underline }
p { color: #E6E8EF; font-size: 15pt; line-height: 1.4 }
.tilt { transform: rotate(-2deg) }
th { background: #00D1B2; color: #001; font-weight: bold }
tr:nth-child(even) td { background: #F6F7FB; color: #111 }
td { border-bottom: 1px solid #CCCCCC }"""
)


def test_end_to_end_header_and_slide_css_fences(tmp_path):
    md = (
        E2E
        + "# Quarterly review\n> A calm quarter\n@2\n## Alpha\nfirst body\n## Beta {.tilt}\nsecond body\n"
        + "\n---\n# Table slide\n"
        + css("td {color: #333333}\nth {text-align: center}")
        + "| name | qty |\n|---|---|\n| a | 1 |\n| b | 2 |\n"
    )
    prs, deck = build(md, tmp_path)
    hits = 0

    def check(cond):
        nonlocal hits
        assert cond
        hits += 1

    s0 = prs.slides[0]
    bg = s0._element.xpath("./p:cSld/p:bg/p:bgPr/a:gradFill")
    check(bg and bg[0].xpath("./a:lin")[0].get("ang") == "2700000")  # 1 slide background gradient
    t = one(prs, "Title")
    r = rpr(t)
    check(t.text_frame.text == "QUARTERLY REVIEW")  # 2 text-transform
    check(r.get("spc") == "200")  # 3 letter-spacing
    check(r.xpath("./a:solidFill/a:srgbClr")[0].get("val") == "7C5CFF")  # 4 color
    check(r.xpath("./a:latin")[0].get("typeface") == "Georgia")  # 5 font-family
    lead = one(prs, "Lead")
    check(rpr(lead).get("i") == "1")  # 6 font-style
    check(lead._element.xpath(".//a:pPr")[0].get("algn") == "ctr")  # 7 text-align
    card = one(prs, "Card")
    sp = card._element.spPr
    check(sp.xpath("./a:gradFill"))  # 8 background gradient
    check(sp.xpath("./a:prstGeom")[0].get("prst") == "roundRect")  # 9 border-radius
    check(sp.xpath("./a:effectLst/a:outerShdw"))  # 10 box-shadow
    check(sp.xpath("./a:ln/a:prstDash")[0].get("val") == "dash")  # 11 border-style
    h = by_text(prs, "Alpha")
    check(h.left - card.left == 12 * EMU_PT)  # 12 padding (8px 16px -> left 12pt)
    check(rpr(h).get("u") == "sng")  # 13 text-decoration
    check(shapes(prs, "Heading 1 border bottom"))  # 14 border-bottom
    body = by_text(prs, "first body")
    check(float(rpr(body).get("sz")) <= 1500)  # 15 font-size
    check(body._element.xpath(".//a:lnSpc/a:spcPct")[0].get("val") == "140000")  # 16 line-height
    tilt = by_text(prs, "second body")
    check(tilt._element.spPr.xpath("./a:xfrm")[0].get("rot") == str(358 * 60000))  # 17 rotate
    tbl = next(s for s in prs.slides[1].shapes if s.has_table).table
    th, td_even = tbl.rows[0].cells[0], tbl.rows[1].cells[0]
    check(th._tc.tcPr.xpath("./a:solidFill/a:srgbClr")[0].get("val") == "00D1B2")  # 18 th background
    check(th._tc.xpath(".//a:pPr")[0].get("algn") == "ctr")  # 19 slide css fence: th text-align
    check(td_even._tc.tcPr.xpath("./a:solidFill/a:srgbClr")[0].get("val") == "F6F7FB")  # 20 nth-child zebra
    check(
        td_even._tc.xpath(".//a:rPr/a:solidFill/a:srgbClr")[0].get("val") == "111111"
    )  # 21 td color (tr rule)
    lnb = td_even._tc.tcPr.find(qn("a:lnB"))
    check(lnb.find(qn("a:solidFill")).find(qn("a:srgbClr")).get("val") == "CCCCCC")  # 22 cell border
    check(hits >= 15)
    assert not codes(deck, "css-unsupported")


def test_brand_example_style(tmp_path):
    md = (
        HEAD
        + css(
            """h1 { text-transform: uppercase; letter-spacing: 1pt }
.box { background: linear-gradient(135deg, #141A2E, #1E2540); box-shadow: 0 8px 24px #0006;
       border-radius: 14px }
.box > h2 { border-bottom: 2px solid #00D1B2 }
tr:nth-child(even) td { background: #F6F7FB }"""
        )
        + "# Brand deck\n@2\n## One\nalpha\n## Two\nbeta\n\n---\n# Numbers\n"
        + "| k | v |\n|---|---|\n| a | 1 |\n| b | 2 |\n"
    )
    prs, deck = build(md, tmp_path)
    assert one(prs, "Title").text_frame.text == "BRAND DECK"
    assert rpr(one(prs, "Title")).get("spc") == "100"
    for card in shapes(prs, "Card"):
        sp = card._element.spPr
        assert sp.xpath("./a:gradFill") and sp.xpath("./a:effectLst/a:outerShdw")
        assert sp.xpath("./a:prstGeom")[0].get("prst") == "roundRect"
    assert (
        len(shapes(prs, "Heading 1 border bottom")) == 1 and len(shapes(prs, "Heading 2 border bottom")) == 1
    )
    rows = [r.cells for r in next(s for s in prs.slides[1].shapes if s.has_table).table.rows]
    assert cell_fill(rows[1][0]) == "F6F7FB"
    assert cell_fill(rows[2][0]) != "F6F7FB"
    assert not codes(deck, "css-unsupported")


def test_no_css_means_no_change(tmp_path):
    prs, deck = build(HEAD + BOXES, tmp_path)
    assert not [d for d in deck.diagnostics if d.rule and d.rule.startswith("css")]
    assert not shapes(prs, "Heading 1 border")


# --------------------------------------------------------------------------- validity


def kitchen_sink(tmp_path):
    from PIL import Image

    Image.new("RGB", (64, 36), (20, 120, 200)).save(tmp_path / "tex.png")
    Image.new("RGB", (30, 30), (200, 40, 40)).save(tmp_path / "pic.png")
    rules = css(
        """slide { background: url(tex.png) }
h1 { text-transform: uppercase; letter-spacing: 3px; text-decoration: underline; opacity: .9 }
.box { background: url(tex.png); border-left: 4px solid #FF8800; border-bottom: 1px dotted #FFFFFF;
       border-radius: 10px; box-shadow: 0 4px 12px #0005; padding: 6px 14px 10px 4px; margin: 4px }
.box > h2 { border-bottom: 2px dashed #FFFFFF; color: #FFFFFF }
.tilt { transform: rotate(4deg); background: radial-gradient(#FFEEAA, #FFAA55); color: #222222 }
th { background: linear-gradient(90deg, #112233, #445566); color: #FFFFFF; border-bottom: 3px solid #FF0000 }
td { border: 1px dashed #888888; padding: 3px 9px; text-decoration: line-through }
tr:nth-child(odd) td { background: #EEF; opacity: .9 }
img { border: 2px solid #AA00AA; border-radius: 8px; box-shadow: 0 2px 6px #0004; opacity: .7 }
code { border-radius: 6px; border-top: 2px solid #00AA00 }"""
    )
    md = (
        HEAD
        + rules
        + "# Sink\n@2\n## One\nalpha\n## Two {.tilt}\nbeta\n\n---\n# Two\n@2\n"
        + "| a | b |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |\n"
        + "\n![alt](pic.png)\n\n```python\nprint(1)\n```\n"
    )
    out = tmp_path / "sink.pptx"
    deck = parse(md)
    build_deck(deck, out, tmp_path)
    return out, deck


def test_kitchen_sink_builds_without_errors(tmp_path):
    out, deck = kitchen_sink(tmp_path)
    assert out.exists()
    assert not [d for d in deck.diagnostics if d.level == "error"]
    assert not codes(deck, "css-unsupported")


def test_kitchen_sink_is_schema_valid(tmp_path):
    from slidemark.xsd import _load_schema, validate_pptx

    if _load_schema() is None:
        pytest.skip("ECMA-376 schemas not available")
    out, _ = kitchen_sink(tmp_path)
    assert validate_pptx(out) == []


def test_kitchen_sink_opens_in_libreoffice(tmp_path):
    from slidemark.preview import have_soffice, pptx_to_pngs

    if not have_soffice():
        pytest.skip("LibreOffice not installed")
    out, _ = kitchen_sink(tmp_path)
    assert len(pptx_to_pngs(out, tmp_path / "png")) == 2


# --------------------------------------------------------------------------- lint judges readability only


def lint_rules(md: str, tmp_path) -> list[str]:
    _, deck = build(md, tmp_path)
    return [d.rule for d in deck.diagnostics if d.rule in ("contrast", "overflow", "tiny-text")]


def test_contrast_uses_the_css_merged_colors(tmp_path):
    ok = HEAD + css(".box {background: #101820; color: #F0F0F0}") + BOXES
    assert "contrast" not in lint_rules(ok, tmp_path)
    bad = HEAD + css(".box {background: #101820; color: #202830}") + BOXES
    assert "contrast" in lint_rules(bad, tmp_path)


def test_contrast_gradient_is_checked_per_stop(tmp_path):
    dark = HEAD + css(".box {background: linear-gradient(90deg, #000000, #223344); color: #FFFFFF}") + BOXES
    assert "contrast" not in lint_rules(dark, tmp_path)
    # white text on a gradient that is light everywhere fails on every stop
    light = HEAD + css(".box {background: linear-gradient(90deg, #FFFFFF, #EEEEEE); color: #FFFFFF}") + BOXES
    assert "contrast" in lint_rules(light, tmp_path)
    # white text on black -> mid gray passes on most of the gradient and on average: not reported
    mixed = HEAD + css(".box {background: linear-gradient(90deg, #000000, #909090); color: #FFFFFF}") + BOXES
    assert "contrast" not in lint_rules(mixed, tmp_path)


def test_contrast_follows_the_css_slide_background(tmp_path):
    dark_bg = HEAD + css("slide {background: #000000}\nh1, p {color: #222222}") + "# T\n- one\n- two\n"
    assert "contrast" in lint_rules(dark_bg, tmp_path)  # declared dark text on black
    auto = HEAD + css("slide {background: #000000}") + "# T\n- one\n- two\n"
    assert "contrast" not in lint_rules(auto, tmp_path)  # undeclared: the ink flips by itself
    fixed = HEAD + css("slide {background: #000000; color: #FFFFFF}") + "# T\n- one\n- two\n"
    assert "contrast" not in lint_rules(fixed, tmp_path)
    grad = HEAD + css("slide {background: linear-gradient(135deg, #000000, #112233); color: #FFFFFF}")
    assert "contrast" not in lint_rules(grad + "# T\ntext\n- a\n", tmp_path)


def test_custom_design_is_never_flagged_as_odd(tmp_path):
    md = HEAD + css(
        "h1 {color: #FF00FF; font-family: 'Comic Sans MS'}\n"
        ".box {background: #00FF00; color: #002200; border: 3px dotted #FF0000; font-family: Impact}\n"
        ".box > h2 {color: #330033; font-size: 26pt}"
    )
    _, deck = build(md + BOXES, tmp_path)
    flagged = {d.rule for d in deck.diagnostics}
    assert "contrast" not in flagged
    assert not {r for r in flagged if r and ("color" in r or "font" in r or "palette" in r)}


def test_overflow_lint_uses_css_padding():
    from slidemark.ir import Placed, Slide, Text
    from slidemark.lint import lint_slide

    el = Text(paragraphs=[Paragraph(runs=[Run(text="word " * 40)])])
    deck = Deck(slides=[Slide(elements=[el])])
    theme = get_theme("default")
    tight = Placed(element=el, x=0, y=0, w=4_000_000, h=1_400_000, style=Style(font_size=14))
    padded = tight.model_copy(
        update={"style": Style(font_size=14, padding_left="60pt", padding_right="60pt")}
    )
    assert not [d for d in lint_slide([tight], deck, theme, 0) if d.rule == "overflow"]
    assert [d for d in lint_slide([padded], deck, theme, 0) if d.rule == "overflow"]
