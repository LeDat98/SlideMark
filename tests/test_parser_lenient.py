from pathlib import Path

from slidemark.ir import Container, Image, Table, Text
from slidemark.parser import parse

EXAMPLES = Path(__file__).parent.parent / "examples"


def rules(deck):
    return [d.rule for d in deck.diagnostics]


def diag(deck, rule):
    return next(d for d in deck.diagnostics if d.rule == rule)


# --------------------------------------------------------------------------- @end


def test_end_closes_box_so_table_is_slide_level():
    d = parse("# A\n## One\n- x\n## Two\n- y\n@end\n| a | b |\n|-|-|\n| 1 | 2 |\n> done\n")
    s = d.slides[0]
    assert [type(e) for e in s.elements] == [Container, Container, Table]
    assert all(not isinstance(c, Table) for box in s.elements[:2] for c in box.children)
    assert s.conclusion is not None and s.conclusion.paragraphs[0].plain == "done"
    assert "end-outside-box" not in rules(d)


def test_without_end_table_stays_in_box():
    d = parse("# A\n## One\n- x\n| a | b |\n|-|-|\n| 1 | 2 |\n")
    assert isinstance(d.slides[0].elements[0].children[-1], Table)


def test_end_then_at_line_and_text_belong_to_slide():
    d = parse("# A\n## One\n- x\n@end\n@2\nplain text\n")
    s = d.slides[0]
    assert s.grid == "2" and isinstance(s.elements[-1], Text) and s.elements[-1].role == "body"
    assert not s.elements[0].grid


def test_end_outside_box_is_info():
    d = parse("# A\ntext\n@end\n")
    x = diag(d, "end-outside-box")
    assert x.level == "info" and x.hint and x.line == 3 and x.slide == 1
    d2 = parse("# A\n## B\n- x\n@end\n@end\n")
    assert rules(d2).count("end-outside-box") == 1


def test_end_inside_code_fence_is_code():
    d = parse("# A\n## B\n```\n@end\n```\n")
    assert "end-outside-box" not in rules(d)
    assert d.slides[0].elements[0].children[0].text == "@end"


def test_jp_dense_example_table_is_slide_level():
    d = parse((EXAMPLES / "02-jp-dense.md").read_text(encoding="utf-8"))
    s2 = d.slides[1]
    assert isinstance(s2.elements[-1], Table)
    assert len([e for e in s2.elements if isinstance(e, Container)]) == 4
    assert s2.conclusion is not None


# --------------------------------------------------------------------------- Marp


def test_marp_header_is_ignored_with_warning():
    d = parse("---\nmarp: true\ntheme: midnight\npaginate: true\n---\n# A\n- x\n")
    assert d.theme == "midnight" and d.slide_number is True
    assert rules(d).count("marp-syntax") == 2
    assert not any(x.rule == "unknown-header" for x in d.diagnostics)
    d2 = parse("marp: true\n\n# A\n")
    assert diag(d2, "marp-syntax").hint


def test_marp_class_and_paginate_comments():
    d = parse("# A\n- x\n\n---\n<!-- _class: lead invert -->\n# B\n- y\n<!-- paginate: true -->\n")
    assert d.slides[0].classes == []
    assert d.slides[1].classes == ["lead", "invert"]
    assert d.slide_number is True
    assert rules(d).count("marp-syntax") == 2
    assert all(x.hint for x in d.diagnostics)


def test_comment_before_first_slide_does_not_make_a_slide():
    d = parse("<!-- _class: lead -->\n# A\n- x\n")
    assert len(d.slides) == 1 and d.slides[0].classes == ["lead"]


def test_comments_become_notes():
    d = parse("# A\n- x\n<!-- say this first -->\n<!--\nmulti\nline\n-->\n# B\n- y\n??? old style\n")
    assert d.slides[0].notes == "say this first\nmulti\nline"
    d2 = parse("# A\n<!-- n1 -->\n- x\n??? n2\n")
    assert d2.slides[0].notes == "n1\nn2"
    assert diag(d, "comment-notes").level == "info"


def test_unclosed_comment_warns():
    d = parse("# A\n<!-- oops\n- x\n")
    assert "unclosed-comment" in rules(d) and d.slides


def test_comment_inside_code_fence_is_code():
    d = parse("# A\n```html\n<!-- keep -->\n```\n")
    assert d.slides[0].notes is None
    assert "comment-notes" not in rules(d)


def test_note_line_is_speaker_notes():
    d = parse("# A\n- x\n\nNote: remember the demo\nsecond line\n\n# B\n- y\n")
    assert d.slides[0].notes == "remember the demo\nsecond line"
    assert d.slides[1].notes is None
    assert diag(d, "note-line").hint


def test_marp_image_size():
    d = parse("# A\n![w:200](a.png)\n")
    img = d.slides[0].elements[0]
    assert isinstance(img, Image) and img.box.w == 200 and img.alt == ""
    assert "marp-syntax" in rules(d)
    d2 = parse("# A\n![w:30% h:100px a cat](a.png)\n")
    img2 = d2.slides[0].elements[0]
    assert img2.box.w == "30%" and img2.box.h == "100px" and img2.alt == "a cat"
    assert "image-alt" not in rules(d2)
    d3 = parse("# A\n![w:200 pic](a.png){w=50%}\n")
    assert d3.slides[0].elements[0].box.w == "50%"


# --------------------------------------------------------------------------- Slidev / reveal


def test_slidev_frontmatter_block():
    d = parse("# A\n- x\n\n---\nlayout: cover\nclass: text-center\n---\n# B\n- y\n")
    s = d.slides[1]
    assert s.layout == "cover" and "text-center" in s.classes
    assert d.slides[0].classes == [] and len(d.slides) == 2
    assert "slidev-syntax" in rules(d)


def test_slidev_unknown_layout_warns():
    d = parse("# A\n---\nlayout: two-cols\n---\n# B\n")
    assert any(x.rule == "slidev-syntax" and "two-cols" in x.message for x in d.diagnostics)


def test_slidev_slot_lines_ignored():
    d = parse("# A\nleft\n::right::\nright\n")
    assert "slot-syntax" in rules(d)
    assert diag(d, "slot-syntax").hint
    texts = [p.plain for e in d.slides[0].elements if isinstance(e, Text) for p in e.paragraphs]
    assert all("::" not in t for t in texts)


def test_horizontal_rule_with_text_is_not_slidev():
    d = parse("# A\n---\nfoo: bar\n---\n- x\n")
    assert "slidev-syntax" not in rules(d)


def test_star_bullets_work_and_warn_once_per_slide():
    d = parse("# A\n* one\n* two\n\n# B\n* three\n")
    assert [p.marker for p in d.slides[0].elements[0].paragraphs] == ["bullet", "bullet"]
    assert rules(d).count("bullet-star") == 2
    assert "bullet-star" not in rules(parse("# A\n- one\n**bold** text\n---\n"))


def test_h3_only_deck_uses_h3_as_slide_start():
    d = parse("### First\n- a\n### Second\n- b\n")
    assert [s.title.paragraphs[0].plain for s in d.slides] == ["First", "Second"]
    assert "h3-slides" in rules(d)
    d2 = parse("# A\n## B\n### C\n")
    assert len(d2.slides) == 1 and "h3-slides" not in rules(d2)


def test_br_is_a_line_break():
    d = parse("# A\n- x\n\nline one<br>line two<br/>three\n")
    texts = d.slides[0].elements[0].paragraphs[-1].runs
    assert [r.text for r in texts] == ["line one", "\n", "line two", "\n", "three"]
    assert "html-br" in rules(d)


def test_br_in_table_cell():
    d = parse("# A\n| a | b |\n|-|-|\n| x<br>y | z |\n")
    cell = d.slides[0].elements[0].rows[1][0]
    assert "\n" in [r.text for p in cell.paragraphs for r in p.runs]


# --------------------------------------------------------------------------- unknown tokens


def test_unknown_at_word_suggests_closest():
    d = parse("# A\n@3 chevorn\n- x\n")
    x = diag(d, "unknown-token")
    assert "chevron" in x.hint and x.line == 2
    assert "hidden" in diag(parse("# A\n@hiden\n"), "unknown-token").hint
    assert "unknown-token" not in rules(parse("# A\n@3 dense flow lead\n"))


def test_unknown_at_key_and_bad_grid():
    assert "bg=" in diag(parse("# A\n@bgg=#fff\n"), "unknown-token").hint
    assert "valid keys" in diag(parse("# A\n@zzz=1\n"), "unknown-token").hint
    assert diag(parse("# A\n@2X2\n"), "bad-grid").hint


def test_unknown_attr_key_and_class_suggest():
    d = parse("# A\n## B {colour=red .dnager}\n- x\n")
    hints = [x.hint for x in d.diagnostics if x.rule == "unknown-attr"]
    assert any("'.danger'" in h for h in hints)
    d2 = parse("# A\n## B {colour=red}\n")
    assert "'color='" in diag(d2, "unknown-attr").hint
    assert "unknown-attr" not in rules(parse("# A\n## B {.danger w=50% mykey=1}\n"))
    assert "unknown-attr" not in rules(parse('# A\n```column {title="x" legend=bottom}\n,a\nb,1\n```\n'))


def test_unknown_header_key_suggests():
    d = parse("themee: midnight\n\n# A\n")
    assert "did you mean 'theme'" in diag(d, "unknown-header").hint
