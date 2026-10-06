from pathlib import Path

import pytest

from slidemark.ir import Chart, Code, Container, Image, Raw, Table, Text
from slidemark.parser import parse

CORPUS = Path(__file__).parent.parent / "bench" / "corpus"


def runs(text: Text):
    return [r for p in text.paragraphs for r in p.runs]


def errors(deck):
    return [d for d in deck.diagnostics if d.level == "error"]


# --------------------------------------------------------------------------- header / slides


def test_header_keys():
    d = parse(
        "theme: jp-business\nsize: 4:3\nlang: ja\nauthor: Ann\nfooter: ACME\nnum: on\ndensity: dense\n\n# A\n"
    )
    assert (d.theme, d.size, d.lang, d.author, d.footer) == ("jp-business", "4:3", "ja", "Ann", "ACME")
    assert d.slide_number is True and d.density == "dense"
    assert d.title == "A"


def test_front_matter_yaml_keeps_strings():
    d = parse("---\ntheme: midnight\nsize: 16:9\nnum: on\ntitle: Deck\n---\n# A\n")
    assert (d.theme, d.size, d.slide_number, d.title) == ("midnight", "16:9", True, "Deck")
    assert len(d.slides) == 1


def test_leading_hr_is_not_front_matter():
    d = parse("---\n# A\ntext\n---\n# B\n")
    assert [s.title.paragraphs[0].plain for s in d.slides] == ["A", "B"]


def test_unknown_header_key_warns():
    d = parse("colour: red\n# A\n")
    assert d.attrs["colour"] == "red"
    assert d.diagnostics[0].rule == "unknown-header" and d.diagnostics[0].hint


def test_hash_in_code_fence_is_not_a_slide():
    d = parse("# A\n```python\n# comment\n--- \n```\n# B\n")
    assert len(d.slides) == 2
    code = d.slides[0].elements[0]
    assert isinstance(code, Code) and code.lang == "python" and "# comment" in code.text


def test_hr_starts_untitled_slide_and_blank_slides_dropped():
    d = parse("# A\nx\n\n---\nsecond\n\n---\n---\n# C\nz\n")
    assert [s.title is None for s in d.slides] == [False, True, False]
    assert d.slides[1].elements[0].paragraphs[0].plain == "second"


def test_setext_is_not_a_heading():
    d = parse("# A\ntext\n---\nmore\n")
    assert len(d.slides) == 2


def test_unclosed_fence_recovers():
    d = parse("# A\n```python\nx\n# B\ny\n")
    assert len(d.slides) == 2
    assert any(x.rule == "unclosed-fence" and x.hint for x in d.diagnostics)


def test_cover_and_section_inference():
    d = parse("# Title\nSub line\n\n# Part 2\nsmall\n\n# Real\n- a\n- b\n- c\n")
    assert d.slides[0].layout == "cover" and d.slides[0].subtitle.paragraphs[0].plain == "Sub line"
    assert d.slides[0].elements == []
    assert d.slides[1].layout == "section" and d.slides[1].subtitle is not None
    assert d.slides[2].layout is None and d.slides[2].subtitle is None


def test_long_text_is_not_a_subtitle():
    d = parse("# T\n" + "x" * 200 + "\n")
    assert d.slides[0].subtitle is None and len(d.slides[0].elements) == 1


def test_first_slide_long_tagline_is_a_cover():
    tag = "FY2027 rollout of 24 partner clinics · Board review, October 2026"  # 66 chars
    d = parse(f"# Plan\n{tag}\n\n# Part\n{tag}\n")
    assert d.slides[0].layout == "cover" and d.slides[0].subtitle.paragraphs[0].plain == tag
    assert d.slides[1].layout is None and d.slides[1].subtitle is None  # later slides keep the short limit


def test_notes():
    d = parse("# A\ntext\n??? say hello\nsecond line\n# B\n")
    assert d.slides[0].notes == "say hello\nsecond line"
    assert d.slides[1].notes is None


# --------------------------------------------------------------------------- @ lines


def test_at_slide_grid_and_flags():
    d = parse("# A\n@aab/aac flow dense bg=#0F172A t=fade id=x gap=8 hidden\n## a\n## b\n## c\n")
    s = d.slides[0]
    assert s.grid == "aab/aac" and s.classes == ["flow", "dense"]
    assert (s.background, s.transition, s.id, s.hidden) == ("#0F172A", "fade", "x", True)
    assert s.attrs["gap"] == 8.0
    assert len(s.elements) == 3


@pytest.mark.parametrize("tok", ["3", "2x2", "1:2", "1:2:1"])
def test_at_grid_tokens(tok):
    assert parse(f"# A\n@{tok}\n## a\n").slides[0].grid == tok


def test_at_layout_words():
    assert parse("# A\n@section\n").slides[0].layout == "section"
    assert parse("# A\n@blank\n- x\n").slides[0].layout == "blank"


def test_at_bad_areas_warns():
    d = parse("# A\n@aab/aa\n## a\n")
    assert any(x.rule == "bad-grid" and x.hint for x in d.diagnostics)


def test_at_inside_box_is_box_grid_and_h3_become_boxes():
    d = parse("# A\n## Box\n@1:2\n### Left\nl\n### Right\nr\n")
    box = d.slides[0].elements[0]
    assert isinstance(box, Container) and box.grid == "1:2" and d.slides[0].grid is None
    assert [c.title.paragraphs[0].plain for c in box.children] == ["Left", "Right"]
    assert all(isinstance(c, Container) for c in box.children)


def test_h3_without_at_is_heading_text():
    d = parse("# A\n## Box\n### Sub\ntext\n")
    box = d.slides[0].elements[0]
    assert box.grid is None
    assert isinstance(box.children[0], Text) and box.children[0].role == "heading"
    assert box.children[1].role == "body"


# --------------------------------------------------------------------------- blocks


def test_boxes_and_blocks_in_source_order():
    d = parse("# A\nintro text\n![pic](a.png)\n## B1\n- x\n## B2\n- y\n")
    els = d.slides[0].elements
    assert [type(e).__name__ for e in els] == ["Text", "Image", "Container", "Container"]
    assert els[0].role == "body"


def test_lists_levels_and_markers():
    d = parse("# A\n- a\n  - b\n1. c\n")
    ps = d.slides[0].elements[0].paragraphs
    assert [(p.plain, p.marker, p.level) for p in ps] == [
        ("a", "bullet", 0),
        ("b", "bullet", 1),
        ("c", "number", 0),
    ]


def test_lead_conclusion_quote():
    d = parse("# A\n> lead\ntext\n> middle quote\nmore\n> conclusion\n※ source\n")
    s = d.slides[0]
    assert s.lead.paragraphs[0].plain == "lead" and s.lead.role == "lead"
    assert s.conclusion.paragraphs[0].plain == "conclusion"
    assert [e.role for e in s.elements] == ["body", "quote", "body"]
    assert s.footnotes[0].role == "footnote" and s.footnotes[0].paragraphs[0].plain == "※ source"


def test_conclusion_inside_last_box():
    d = parse("# A\n## B\ntext\n> done\n")
    s = d.slides[0]
    assert s.conclusion is not None and len(s.elements[0].children) == 1


def test_footnote_markers():
    # ※ is text, ^ is only a marker
    d = parse("# A\ntext\n※ one\n^ two\n")
    assert [f.paragraphs[0].plain for f in d.slides[0].footnotes] == ["※ one", "two"]


def test_attrs_on_heading_and_before_block():
    d = parse("# A\n## Box {.danger #b1 fill=#FFEEEE w=50%}\n{size=10 align=center}\n- x\n")
    box = d.slides[0].elements[0]
    assert box.classes == ["danger"] and box.id == "b1"
    assert box.style.fill == "#FFEEEE" and box.box.w == "50%"
    assert box.title.paragraphs[0].plain == "Box"
    t = box.children[0]
    assert t.style.font_size == 10 and t.style.align == "center"


def test_attr_keys_all():
    d = parse(
        "# A\n@blank\n{x=1in y=2cm w=3 h=10% color=primary line=#000 bold valign=middle radius=4 pad=6}\n"
        "text\n"
    )
    t = d.slides[0].elements[0]
    assert (t.box.x, t.box.y, t.box.w, t.box.h) == ("1in", "2cm", 3.0, "10%")
    st = t.style
    assert (st.color, st.line, st.bold, st.valign, st.radius, st.padding) == (
        "primary",
        "#000",
        True,
        "middle",
        4.0,
        6.0,
    )


def test_bad_attr_values_warn_not_raise():
    d = parse("# A\n{align=sideways size=big}\ntext\n")
    assert [x.rule for x in d.diagnostics].count("bad-attr") == 2


def test_unknown_attr_goes_to_attrs():
    d = parse('# A\n@blank\n{foo="two words"}\ntext\n')
    assert d.slides[0].elements[0].attrs == {"foo": "two words"}


# --------------------------------------------------------------------------- inline


def test_inline_styles():
    d = parse("# A\n@blank\n@blank\n**b** *i* ~~s~~ `c` [l](http://x) [go](#5) ==k==\n")
    rs = {r.text: r for r in runs(d.slides[0].elements[0])}
    assert rs["b"].bold and rs["i"].italic and rs["s"].strike and rs["c"].code
    assert rs["l"].link == "http://x" and rs["go"].link == "#5"
    assert rs["k"].color == "accent"


def test_span_color_and_sub_sup():
    d = parse("# A\n@blank\n[bad]{.danger} H~2~O x^2^ [c]{color=#f00}\n")
    rs = runs(d.slides[0].elements[0])
    by = {r.text: r for r in rs}
    assert by["bad"].color == "danger" and by["c"].color == "#f00"
    assert any(r.sub and r.text == "2" for r in rs) and any(r.sup and r.text == "2" for r in rs)
    assert "".join(r.text for r in rs) == "bad H2O x2 c"


def test_equals_with_spaces_is_not_mark():
    d = parse("# A\n@blank\na == b == c\n")
    assert runs(d.slides[0].elements[0])[0].text == "a == b == c"


def test_soft_break_starts_new_paragraph():
    d = parse("# A\n@blank\n日本語の\nテキスト\n")
    assert [p.plain for p in d.slides[0].elements[0].paragraphs] == ["日本語の", "テキスト"]


# --------------------------------------------------------------------------- images


def test_image_attrs_and_alt_warning():
    d = parse("# A\n![図](<a b/図.png>){w=40% fit=cover}\n![](x.png)\n")
    a, b = d.slides[0].elements
    assert isinstance(a, Image) and a.alt == "図" and a.box.w == "40%" and a.fit == "cover"
    assert a.src == "a%20b/図.png" or a.src.endswith("図.png")
    assert any(x.rule == "image-alt" and x.hint for x in d.diagnostics)
    assert b.alt == ""


def test_image_between_text_splits_blocks():
    d = parse("# A\nbefore ![x](a.png) after\n")
    assert [type(e).__name__ for e in d.slides[0].elements] == ["Text", "Image", "Text"]


# --------------------------------------------------------------------------- tables


def test_gfm_table_merges_and_align():
    src = "# A\n| a | b | c |\n|:-|:-:|-:|\n| x | y | z |\n| tot | < | < |\n| p | ^ | w |\n"
    t = parse(src).slides[0].elements[0]
    assert isinstance(t, Table) and t.header_rows == 1
    assert len(t.rows) == 4 and all(len(r) == 3 for r in t.rows)
    assert t.rows[2][0].colspan == 3
    assert t.rows[2][1].paragraphs == [] and t.rows[2][2].paragraphs == []
    assert t.rows[3][1].paragraphs[0].plain == "^" and any(
        d.rule == "table-merge" for d in parse(src).diagnostics
    )
    assert t.rows[0][0].style.align == "left" and t.rows[0][1].style.align == "center"
    assert t.rows[0][2].style.align == "right"


def test_rowspan_merge():
    t = parse("# A\n| a | b |\n|-|-|\n| x | y |\n| z | ^ |\n").slides[0].elements[0]
    assert t.rows[2][1].paragraphs == [] and t.rows[1][1].rowspan == 2


def test_table_right_under_list_is_a_table():
    d = parse("# A\n- item\n| a | b |\n|-|-|\n| 1 | 2 |\n")
    assert [type(e).__name__ for e in d.slides[0].elements] == ["Text", "Table"]


def test_merge_in_first_column_warns():
    d = parse("# A\n| a | b |\n|-|-|\n| < | y |\n")
    assert any(x.rule == "table-merge" for x in d.diagnostics)


def test_csv_table_fence():
    t = parse('# A\n```table\nh1,h2\n**x**,<\n"1,5",^\n```\n').slides[0].elements[0]
    assert isinstance(t, Table)
    assert t.rows[1][0].paragraphs[0].runs[0].bold
    assert t.rows[1][0].colspan == 2
    assert t.rows[2][0].paragraphs[0].plain == "1,5"


# --------------------------------------------------------------------------- charts and fences


def test_chart_fence():
    d = parse('# A\n```column {title="Sales" legend=bottom}\n,Q1,Q2,Q3\n2025,10,12,15\n2026,12,,21.5\n```\n')
    c = d.slides[0].elements[0]
    assert isinstance(c, Chart) and c.kind == "column" and c.title == "Sales"
    assert c.options == {"legend": "bottom"}
    assert c.categories == ["Q1", "Q2", "Q3"]
    assert c.series[1].values == [12.0, None, 21.5]


@pytest.mark.parametrize(
    "kind",
    ["bar", "column", "stacked-bar", "stacked-column", "line", "area", "pie", "doughnut", "scatter", "radar"],
)
def test_all_chart_kinds(kind):
    c = parse(f"# A\n```{kind}\n,a,b\ns,1,2\n```\n").slides[0].elements[0]
    assert isinstance(c, Chart) and c.kind == kind


def test_chart_problems_are_diagnostics():
    d = parse("# A\n```bar\n,a,b\ns,1,x,3\n```\n```pie\n```\n")
    rules = {x.rule for x in d.diagnostics}
    assert {"bad-number", "chart-ragged", "empty-chart"} <= rules
    assert d.slides[0].elements[0].series[0].values == [1.0, None]


def test_raw_and_code_fences():
    d = parse(
        "# A\n```mermaid\ngantt\nA->>B\n```\n```math\nx^2\n```\n```html\n<svg/>\n```\n```\nplain\n```\n"
    )
    kinds = [(type(e).__name__, getattr(e, "kind", getattr(e, "lang", None))) for e in d.slides[0].elements]
    assert kinds == [("Raw", "mermaid"), ("Raw", "math"), ("Raw", "html"), ("Code", None)]
    assert isinstance(d.slides[0].elements[0], Raw) and "A->>B" in d.slides[0].elements[0].source


# --------------------------------------------------------------------------- corpus and examples


@pytest.mark.parametrize("path", sorted(CORPUS.glob("*/slidemark.md")), ids=lambda p: p.parent.name)
def test_corpus_parses_without_errors(path):
    d = parse(path.read_text(encoding="utf-8"))
    assert d.slides
    assert errors(d) == []


def test_jp_dense_structure():
    d = parse((CORPUS / "jp-dense" / "slidemark.md").read_text(encoding="utf-8"))
    s1, s2 = d.slides
    assert s1.grid == "aab/aac" and s1.lead is not None and len(s1.footnotes) == 2
    assert [c.title.paragraphs[0].plain for c in s1.elements] == ["現状", "課題", "施策"]
    assert any(isinstance(x, Chart) for x in s1.elements[0].children)
    assert s2.grid == "4" and "chevron" in s2.classes and s2.conclusion is not None
    table = s2.elements[-1].children[-1]
    assert isinstance(table, Table) and table.rows[2][2].colspan == 3
    assert d.lang == "ja" and d.slide_number is True


def test_q3_structure():
    d = parse((CORPUS / "q3-review" / "slidemark.md").read_text(encoding="utf-8"))
    assert d.slides[0].layout == "cover" and d.slides[0].notes
    assert isinstance(d.slides[1].elements[1], Chart)
    assert isinstance(d.slides[2].elements[0], Table)


def test_empty_and_garbage_input():
    assert parse("").diagnostics[0].rule == "no-slides"
    assert parse("\x00\x01 {{{{ [[[ ``` ").slides is not None


# --- connectors, callouts, badges, kpi


def rules(deck):
    return [d.rule for d in deck.diagnostics]


def test_slide_links_letters_digits_and_areas_grid():
    d = parse("# T\n@aab/aac a>b a-c 1>3\n\n## A\nx\n## B\ny\n## C\nz\n")
    s = d.slides[0]
    assert s.grid == "aab/aac"
    assert [(link.src, link.dst, link.arrow) for link in s.links] == [
        (0, 1, True),
        (0, 2, False),
        (0, 2, True),
    ]
    assert not d.diagnostics


def test_links_on_a_box_target_its_children():
    d = parse("# T\n\n## Box\n@2 a>b\n### X\nx\n### Y\ny\n")
    box = d.slides[0].elements[0]
    assert box.grid == "2" and len(box.children) == 2
    assert [(link.src, link.dst) for link in box.links] == [(0, 1)]
    assert d.slides[0].links == []


def test_bad_links_are_dropped_with_hint():
    d = parse("# T\n@3 a>a a>z 1>9\n\n## A\nx\n## B\ny\n")
    assert d.slides[0].links == []
    bad = [x for x in d.diagnostics if x.rule == "bad-link"]
    assert len(bad) == 3
    assert "slide has 2 blocks: use letters a..b" in bad[1].hint
    assert all("\n" not in x.hint for x in bad)


def test_callout_kinds_and_marker_removed():
    for word, kind in [
        ("note", "note"),
        ("TIP", "tip"),
        ("warn", "warn"),
        ("Warning", "warn"),
        ("important", "note"),
        ("caution", "caution"),
    ]:
        d = parse(f"# T\n\ntext\n\n> [!{word}] hello **x**\n\nmore\n")
        c = [e for e in d.slides[0].elements if isinstance(e, Text) and "callout" in e.classes]
        assert len(c) == 1 and c[0].role == "body" and c[0].classes == ["callout", kind]
        assert c[0].paragraphs[0].plain == "hello x"
    assert not d.diagnostics


def test_callout_is_never_lead_or_conclusion_and_works_in_boxes():
    d = parse("# T\n> [!tip] first\n\n## Box\n> [!warn] inside\n\n> [!note] last\n")
    s = d.slides[0]
    assert s.lead is None and s.conclusion is None
    box = s.elements[-1]
    assert isinstance(box, Container) and len([c for c in box.children if "callout" in c.classes]) == 3 - 1
    d2 = parse("# T\n\nbody\n\n> [!note] last\n")
    assert d2.slides[0].conclusion is None and d2.slides[0].elements[-1].classes == ["callout", "note"]


def test_callout_only_slide_is_not_a_cover():
    d = parse("# T\n\n> [!note] x\n")
    assert d.slides[0].layout is None and len(d.slides[0].elements) == 1


def test_unknown_callout_is_note_with_hint():
    d = parse("# T\n\n> [!tpi] x\n")
    t = d.slides[0].elements[0]
    assert t.classes == ["callout", "note"]
    w = [x for x in d.diagnostics if x.rule == "unknown-callout"]
    assert w and "tip" in w[0].hint


def test_plain_quote_still_a_lead():
    assert parse("# T\n> lead\n\nbody\n").slides[0].lead is not None


def test_badge_default_and_color_class():
    t = parse("# T\n\nA [済]{.badge} B [NEW]{.badge .danger} C\n\n- x\n- y\n- z\n").slides[0].elements[0]
    rs = runs(t)
    b1 = next(r for r in rs if r.text == "済")
    b2 = next(r for r in rs if r.text == "NEW")
    assert (b1.highlight, b1.color, b1.bold) == ("primary", "bg", True)
    assert (b2.highlight, b2.color, b2.bold) == ("danger", "bg", True)
    assert all(r.highlight is None for r in rs if r.text not in ("済", "NEW"))
    # plain color span unchanged
    r = runs(parse("# T\n\n[x]{.danger}\n\n- a\n- b\n- c\n").slides[0].elements[0])[0]
    assert r.color == "danger" and r.highlight is None


def test_kpi_box_lines_are_separate_paragraphs():
    d = parse("# T\n@2\n\n## 売上 {.kpi}\n12.4億円\n前年比 +8%\n\n## 利益 {.kpi}\n- 3億円\n- 前年比 +1%\n")
    for box in d.slides[0].elements:
        assert "kpi" in box.classes
        assert len(box.children) == 1 and isinstance(box.children[0], Text)
        assert len(box.children[0].paragraphs) == 2
        assert all(p.marker is None for p in box.children[0].paragraphs)
    assert d.slides[0].elements[0].children[0].paragraphs[0].plain == "12.4億円"


def test_nested_at_in_box_builds_nested_containers():
    d = parse("# T\n@2\n\n## Left\n@2\n### a\nx\n### b\ny\n@end\n## Right\nz\n")
    left, right = d.slides[0].elements
    assert d.slides[0].grid == "2" and left.grid == "2"
    assert [type(c).__name__ for c in left.children] == ["Container", "Container"]
    assert [c.title.paragraphs[0].plain for c in left.children] == ["a", "b"]
    assert isinstance(right, Container) and right.grid is None


def test_missing_end_hint():
    src = "# T\n@3\n## A\n- a\n## B\n- b\n## C\n- c\n| x | y |\n|-|-|\n| 1 | 2 |\n"
    deck = parse(src)
    assert any(d.rule == "missing-end" for d in deck.diagnostics)
    fixed = src.replace("- c\n", "- c\n@end\n")
    assert not any(d.rule == "missing-end" for d in parse(fixed).diagnostics)


def test_closing_quote_needs_no_end():
    deck = parse("# T\n## A\n- a\n## B\n- b\n> conclusion\n")
    assert not any(d.rule == "missing-end" for d in deck.diagnostics)
    assert deck.slides[0].conclusion is not None


def test_flow_links_override_flow():
    deck = parse("# T\n@3 flow a>b b>c c>a\n## A\n- a\n## B\n- b\n## C\n- c\n")
    s = deck.slides[0]
    assert [(link.src, link.dst) for link in s.links] == [(0, 1), (1, 2), (2, 0)]
    assert "flow" not in s.classes and s.grid == "3"
    assert sum(d.rule == "flow-links" for d in deck.diagnostics) == 1


def test_flow_links_without_grid_keeps_one_row():
    deck = parse("# T\n@flow a>c\n## A\n- a\n## B\n- b\n## C\n- c\n")
    s = deck.slides[0]
    assert "flow" not in s.classes and s.grid == "3" and len(s.links) == 1


def test_flow_alone_untouched():
    s = parse("# T\n@3 flow\n## A\n- a\n## B\n- b\n## C\n- c\n").slides[0]
    assert "flow" in s.classes and not s.links


def test_box_grid_unused():
    deck = parse("# T\n@2\n## A\ntext\n@3\n## B\n- x\n- y\n")
    a = deck.slides[0].elements[0]
    assert a.grid is None
    assert [d.rule for d in deck.diagnostics if d.rule == "box-grid-unused"] == ["box-grid-unused"]


def test_box_grid_used_with_two_blocks():
    deck = parse("# T\n@2\n## A\n@2\n### X\nx\n### Y\ny\n## B\n- y\n")
    assert deck.slides[0].elements[0].grid == "2"
    assert not any(d.rule == "box-grid-unused" for d in deck.diagnostics)


def test_missing_end_paragraph_before_trailing_chevron():
    src = "# T\n## A\n- a\n## B\n- b\n\nTotal text\n@chevron\n"
    deck = parse(src)
    d = [d for d in deck.diagnostics if d.rule == "missing-end"]
    assert len(d) == 1 and d[0].line == 7


def test_icon_attr():
    deck = parse("# T\n## 売上 {.kpi icon=chart}\n12億円\n## B {icon=chrt}\n- b\n")
    a, b = deck.slides[0].elements
    assert a.attrs.get("icon") == "chart" and "icon" not in b.attrs
    d = [d for d in deck.diagnostics if d.rule == "unknown-icon"]
    assert d and "chart" in d[0].hint


def test_image_line_right_under_a_list_is_its_own_block():
    deck = parse("# T\n## 目的\n- a\n- b\n![動画](demo.mp4)\n")
    box = deck.slides[0].elements[0]
    assert [c.type for c in box.children] == ["text", "media"]
    assert [p.plain for p in box.children[0].paragraphs] == ["a", "b"]


def test_text_right_under_an_image_line_is_not_swallowed():
    deck = parse("# T\n- a\n![x](a.png)\ntext after\n")
    assert [e.type for e in deck.slides[0].elements] == ["text", "image", "text"]


def test_column_count_with_matching_ratios_is_accepted():
    deck = parse("# T\n@2 1:2\n## a\n- x\n## b\n- y\n")
    assert deck.slides[0].grid == "1:2"
    assert not [d for d in deck.diagnostics if d.rule == "bad-grid"]


def test_trailing_at_line_after_last_box_applies_to_slide():
    deck = parse("# T\n## a\nx\n## b\ny\n@chevron\n")
    s = deck.slides[0]
    assert "chevron" in s.classes
    assert not s.elements[-1].classes
    assert any(d.rule == "at-hoisted" for d in deck.diagnostics)


def test_box_at_line_with_sub_boxes_stays_in_the_box():
    deck = parse("# T\n## a\n### x\n- 1\n### y\n- 2\n@2\n")
    assert deck.slides[0].elements[0].grid == "2"


def test_chart_totals_option_is_kept():
    d = parse("# A\n```stacked-bar {labels=on totals=off}\n,Q1,Q2\na,1,2\nb,3,4\n```\n")
    c = d.slides[0].elements[0]
    assert isinstance(c, Chart) and c.options == {"labels": "on", "totals": "off"}
