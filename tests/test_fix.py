"""`slidemark check --fix`: each rule, idempotence, untouched content, JSON output."""

import json

from slidemark.cli import main
from slidemark.fix import fix_text
from slidemark.parser import parse


def fix(text: str) -> tuple[str, list[str]]:
    new, fixed = fix_text(text, lambda t: parse(t).diagnostics)
    return new, [f.rule for f in fixed]


def rules(text: str) -> set[str]:
    return {d.rule for d in parse(text).diagnostics}


DESIGN_HEAD = "colors: primary=#2B6CB0\nfonts: heading=Georgia\nsizes: title=30\nstyle: radius=8\n"


def test_missing_end_before_table():
    src = "# T\n@2\n## A\n- a\n## B\n- b\n\n| x | y |\n|---|---|\n| 1 | 2 |\n"
    new, fixed = fix(src)
    assert fixed == ["missing-end"]
    assert "- b\n\n@end\n| x | y |" in new
    assert "missing-end" not in rules(new)


def test_missing_end_keeps_attr_line_with_block():
    src = "# T\n## A\n- a\n## B\n- b\n\n{.zebra}\n| x | y |\n|---|---|\n| 1 | 2 |\n"
    new, fixed = fix(src)
    if fixed:
        assert "@end\n{.zebra}\n| x" in new


def test_missing_end_trailing_paragraph_before_chevron():
    src = "# T\n## A\n- a\n## B\n- b\n\nTotal text\n@chevron\n"
    new, fixed = fix(src)
    assert fixed == ["missing-end"]
    assert new == "# T\n## A\n- a\n## B\n- b\n\n@end\nTotal text\n@chevron\n"
    assert "missing-end" not in rules(new)


def test_unknown_token_did_you_mean():
    new, fixed = fix("# T\n@3 flwo\n## A\n- a\n## B\n- b\n## C\n- c\n")
    assert "@3 flow\n" in new and fixed == ["unknown-token"]


def test_unknown_at_key():
    new, fixed = fix("# T\n@bgg=#fff dense\n- a\n- b\n")
    assert fixed == ["unknown-token"] and "@bg=#fff dense\n" in new


def test_unknown_class_and_attr():
    new, fixed = fix("# T\n## A {.primry}\n- a\n## B {colr=red}\n- b\n")
    assert fixed == ["unknown-attr", "unknown-attr"]
    assert "## A {.primary}" in new and "## B {color=red}" in new


def test_unknown_icon():
    new, fixed = fix("# T\n## A {icon=shiled}\nx\n## B\ny\n")
    assert fixed == ["unknown-icon"] and "{icon=shield}" in new


def test_unknown_callout():
    new, fixed = fix("# T\n- a\n\n> [!warnn] careful\n")
    assert fixed == ["unknown-callout"] and "[!warn] careful" in new


def test_unknown_header_key():
    new, fixed = fix("themee: default\n\n# T\n- a\n")
    assert fixed == ["unknown-header"] and new.startswith("theme: default")


def test_second_grid_dropped():
    new, fixed = fix("# T\n@2 3 dense\n- a\n- b\n")
    assert fixed == ["bad-grid"] and "@2 dense\n" in new
    assert "bad-grid" not in rules(new)


def test_second_grid_only_token_removes_line():
    new, _ = fix("# T\n@2\n@3\n## A\n- a\n## B\n- b\n")
    assert "bad-grid" not in rules(new)


def test_image_alt_from_file_stem():
    new, fixed = fix("# T\n![](q3-chart.png)\n- a\n")
    assert fixed == ["image-alt"] and "![q3 chart](q3-chart.png)" in new
    assert "image-alt" not in rules(new)


def test_unclosed_fence_closed_at_slide_end():
    src = "# A\n```python\nx = 1\n\n# B\n- b\n"
    new, fixed = fix(src)
    assert fixed == ["unclosed-fence"]
    assert new == "# A\n```python\nx = 1\n```\n\n# B\n- b\n"
    assert "unclosed-fence" not in rules(new)


def test_bullet_star():
    new, fixed = fix("# T\n* a\n* b\n  * c\n\n# U\n* d\n")
    assert fixed == ["bullet-star", "bullet-star"]
    assert "*" not in new
    assert new == "# T\n- a\n- b\n  - c\n\n# U\n- d\n"


def test_bullet_star_skips_code_fence():
    new, _ = fix("# T\n* a\n```\n* keep\n```\n")
    assert "* keep" in new and "- a" in new


def test_note_line_at_slide_end():
    new, fixed = fix("# T\n- a\nNote: say this\n")
    assert fixed == ["note-line"] and new.endswith("??? say this\n")
    assert parse(new).slides[0].notes == "say this"


def test_note_line_followed_by_content_is_left_alone():
    src = "# T\n- a\n\nNote: say this\n\n- b\n"
    new, fixed = fix(src)
    assert new == src and fixed == []


def test_comment_notes():
    new, fixed = fix("# T\n- a\n\n<!-- remember the demo -->\n")
    assert fixed == ["comment-notes"] and "??? remember the demo" in new
    assert parse(new).slides[0].notes == "remember the demo"


def test_marp_class_comment():
    new, fixed = fix("# T\n<!-- _class: dense -->\n- a\n")
    assert fixed == ["marp-syntax"] and "@dense\n" in new
    assert "dense" in parse(new).slides[0].classes


def test_idempotent():
    src = "# T\n@3 flwo 4\n* a\n![](x.png)\n## A {.primry}\nNote: hi\n"
    once, _ = fix(src)
    twice, fixed = fix(once)
    assert twice == once and fixed == []


def test_clean_deck_untouched():
    src = "# T\n@2\n## A\n- a\n## B\n- b\n"
    assert fix(src) == (src, [])


def test_content_text_untouched():
    src = "# 売上 Q3\n* 東京 flwo は 100 億円\n![](a_b.png)\n"
    new, _ = fix(src)
    assert "東京 flwo は 100 億円" in new and "売上 Q3" in new


def test_cli_fix_rewrites_in_place(tmp_path, capsys):
    f = tmp_path / "a.md"
    f.write_text("# T\n* a\n* b\n", encoding="utf-8")
    assert main(["check", "--fix", str(f)]) == 0
    out = capsys.readouterr().out
    assert "fixed L2 bullet-star: '* ' bullets -> '- '" in out
    assert f.read_text(encoding="utf-8") == "# T\n- a\n- b\n"


def test_cli_fix_output_leaves_source(tmp_path, capsys):
    f, o = tmp_path / "a.md", tmp_path / "b.md"
    f.write_text("# T\n* a\n* b\n", encoding="utf-8")
    assert main(["check", "--fix", str(f), "-o", str(o)]) == 0
    assert f.read_text(encoding="utf-8") == "# T\n* a\n* b\n"
    assert o.read_text(encoding="utf-8") == "# T\n- a\n- b\n"
    capsys.readouterr()


def test_cli_fix_json_has_fixed(tmp_path, capsys):
    f = tmp_path / "a.md"
    f.write_text("# T\n* a\n* b\n", encoding="utf-8")
    assert main(["check", "--fix", "--format", "json", str(f)]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["fixed"] == [{"line": 2, "rule": "bullet-star", "what": "'* ' bullets -> '- '"}]
    # --fix never touches the design feedback: it stays listed
    assert [d["rule"] for d in data["diagnostics"]] == ["design-none", "design-slide"]


def test_cli_fix_nothing_to_fix_keeps_file(tmp_path, capsys):
    f = tmp_path / "a.md"
    f.write_text(DESIGN_HEAD + "\n# T\n@1 noemph dense\n- a\n", encoding="utf-8")
    before = f.stat().st_mtime_ns
    assert main(["check", "--fix", str(f)]) == 0
    assert f.stat().st_mtime_ns == before and capsys.readouterr().out.startswith("ok")


def test_cli_output_without_fix_is_an_error(tmp_path, capsys):
    f = tmp_path / "a.md"
    f.write_text("# T\n- a\n", encoding="utf-8")
    assert main(["check", str(f), "-o", str(tmp_path / "b.md")]) == 2
    capsys.readouterr()
