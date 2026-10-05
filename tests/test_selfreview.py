"""`slidemark review --fix`: each source edit (split / dense / contrast / long title), the loop, the CLI."""

import json
import random
import re
from pathlib import Path

from slidemark import redesign
from slidemark.build import build
from slidemark.cli import main
from slidemark.parser import parse
from slidemark.selfreview import analyze, self_review, too_dense

from .helpers import needs_soffice

EXAMPLES = Path(__file__).parent.parent / "examples"


def items(n: int, k: int = 0) -> str:
    return "\n".join(f"- 施策{k}-{i + 1}について担当と期限を決めて進める" for i in range(n))


def rules(text: str) -> list[str]:
    return [d.rule for d in analyze(text).diags if d.level != "info"]


def titles(text: str) -> list[str]:
    return [s.title.paragraphs[0].plain for s in parse(text).slides if s.title]


def split_all(src: str, idx: int = 0) -> str:
    """The first split candidate of slide ``idx`` as a whole deck."""
    head, regs = redesign.regions(src)  # type: ignore[misc]
    _what, lines = next(redesign.split_candidates(regs[idx]))
    parts = [list(r.lines) for r in regs]
    parts[idx] = lines
    return "\n".join([*head, *[x for p in parts for x in p]])


# --------------------------------------------------------------------------- split: source in -> source out


def test_split_list_keeps_every_item_lead_first_footnote_last():
    src = f"# 長いリスト\n> 要点\n{items(22)}\n※ 出所: 社内\n"
    out = split_all(src)
    assert titles(out) == ["長いリスト (1/2)", "長いリスト (2/2)"]
    first, second = out.split("# 長いリスト (2/2)")
    assert "> 要点" in first and "※" not in first
    assert "※ 出所: 社内" in second and "> 要点" not in second
    assert re.findall(r"^- .*$", out, re.M) == re.findall(r"^- .*$", src, re.M)  # same items, same order


def test_split_boxes_at_box_boundaries():
    boxes = "\n".join(f"## 箱{i}\n{items(8, i)}" for i in range(1, 7))
    src = f"# 6 boxes\n@3\n> lead\n{boxes}\n> 結論\n"
    out = split_all(src)
    decks = parse(out)
    assert len(decks.slides) == 2
    assert [len([e for e in s.elements if e.type == "container"]) for s in decks.slides] == [3, 3]
    assert "@3" not in out  # the grid no longer fits
    assert decks.slides[1].conclusion is not None and decks.slides[0].conclusion is None
    assert decks.slides[0].lead is not None


def test_split_single_box_repeats_the_heading():
    src = f"# T\n## 一覧\n{items(20)}\n"
    out = split_all(src)
    assert out.count("## 一覧") == 2 and titles(out) == ["T (1/2)", "T (2/2)"]
    assert re.findall(r"^- .*$", out, re.M) == re.findall(r"^- .*$", src, re.M)


def test_split_gfm_table_repeats_header():
    rows = "\n".join(f"| 行{i} | {i} | {i * 2} |" for i in range(1, 13))
    src = f"# 表\n| 項目 | A | B |\n|-|-|-|\n{rows}\n"
    out = split_all(src)
    assert out.count("| 項目 | A | B |") == 2 and out.count("|-|-|-|") == 2
    assert [len(s.elements[0].rows) for s in parse(out).slides] == [7, 7]  # header + 6 rows each
    assert re.findall(r"^\| 行.*$", out, re.M) == re.findall(r"^\| 行.*$", src, re.M)


def test_split_csv_table_fence_and_attr_line():
    rows = "\n".join(f"行{i},{i},{i * 2}" for i in range(1, 11))
    src = f"# 表\n{{.zebra}}\n```table\n項目,A,B\n{rows}\n```\n"
    out = split_all(src)
    assert out.count("```table") == 2 and out.count("{.zebra}") == 2 and out.count("項目,A,B") == 2
    assert not [d for d in parse(out).diagnostics if d.level != "info"]


def test_split_never_cuts_before_a_merge_cell():
    rows = "\n".join(f"| 行{i} | {i} |" for i in range(1, 9)) + "\n| 計 | ^ |\n"
    src = f"# 表\n| 項目 | A |\n|-|-|\n{rows}"
    for _what, lines in redesign.split_candidates(redesign.regions(src)[1][0]):  # type: ignore[index]
        assert not any(
            re.match(r"^\| 計 \| \^ \|$", ln) and prev.startswith("|-")
            for prev, ln in zip(lines, lines[1:], strict=False)
        )


def test_split_list_block_attr_repeats():
    src = f"# T\n## 一覧\n{{color=#222222}}\n{items(14)}\n"
    out = split_all(src)
    assert out.count("{color=#222222}") == 2


def test_split_keeps_class_tokens_drops_grid_and_links():
    boxes = "\n".join(f"## B{i}\n{items(8, i)}" for i in range(1, 7))
    src = f"# T\n@3 dense a>b bg=#FFFFFF\n{boxes}\n"
    out = split_all(src)
    assert out.count("@dense bg=#FFFFFF") == 2 and "a>b" not in out


def test_split_slide_without_title_uses_separators():
    src = f"# Cover\n---\n{items(24)}\n"
    out = split_all(src, 1)
    assert len(parse(out).slides) == 3


def test_split_leaves_other_slides_and_speaker_notes():
    src = f"# A\n- a\n\n# B\n{items(24)}\n??? note\nsecond line\n\n# C\n- c\n"
    out = split_all(src, 1)
    assert titles(out) == ["A", "B (1/2)", "B (2/2)", "C"]
    assert parse(out).slides[1].notes and parse(out).slides[2].notes is None


# --------------------------------------------------------------------------- dense / title / contrast


def test_add_dense_is_idempotent():
    reg = redesign.regions("# T\n- a\n")[1][0]  # type: ignore[index]
    once = redesign.add_dense(reg)
    assert once == ["# T", "@dense", "- a", ""] or once[:2] == ["# T", "@dense"]
    reg2 = redesign.Region(once, [False] * len(once), 0)
    assert redesign.add_dense(reg2) is None
    reg3 = redesign.regions("# T\n@3 flow\n## A\n- a\n")[1][0]  # type: ignore[index]
    assert redesign.add_dense(reg3)[1] == "@3 flow dense"  # type: ignore[index]


def test_title_candidates_move_the_tail_into_the_lead():
    reg = redesign.regions("# Customer onboarding: what changed, why it matters and what we measure\n- a\n")[
        1
    ][0]  # type: ignore[index]
    cand = next(redesign.title_candidates(reg))
    assert cand[0].startswith("# ") and cand[1].startswith("> ")
    joined = (cand[0][2:] + " " + cand[1][2:]).replace(":", "")
    assert "what we measure" in joined
    reg = redesign.regions("# A long title that goes on and on, and on\n> existing lead\n- a\n")[1][0]  # type: ignore[index]
    cand = next(redesign.title_candidates(reg))
    assert cand[1].endswith("existing lead") and cand[1].startswith("> ")


def test_contrast_candidates_attr_css_and_fill():
    reg = redesign.regions("# T\n{color=#EEEEEE}\ntext\n")[1][0]  # type: ignore[index]
    assert "{color=#111111}" in next(redesign.contrast_candidates(reg, 1, ["#111111"]))
    reg = redesign.regions("# T\n## B {fill=#111111}\n- x\n")[1][0]  # type: ignore[index]
    assert "## B {fill=#111111 color=#FFFFFF}" in next(redesign.contrast_candidates(reg, 1, ["#FFFFFF"]))
    reg = redesign.regions("# T\n```css\nh2 { color: #EEE }\n```\n## B\n- x\n")[1][0]  # type: ignore[index]
    assert "h2 { color: #123456 }" in next(redesign.contrast_candidates(reg, None, ["#123456"]))
    reg = redesign.regions("# T\n```python\ncolor: red\n```\n- x\n")[1][0]  # type: ignore[index]
    assert list(redesign.contrast_candidates(reg, None, ["#123456"])) == []  # code is never edited


# --------------------------------------------------------------------------- the loop


def test_loop_splits_an_overfull_list_and_builds_clean(tmp_path):
    src = f"# 長いリスト\n> 要点\n{items(22)}\n"
    assert "design-wall-of-text" in rules(src)
    res = self_review(src)
    assert [f.rule for f in res.fixed] == ["split-slide"]
    assert "design-wall-of-text" not in rules(res.text) and res.after.score > res.before.score
    out = tmp_path / "o.pptx"
    deck = build(res.text, out)
    assert len(deck.slides) == len(res.after.deck.slides) >= 2 and out.exists()
    from pptx import Presentation

    assert len(Presentation(str(out)).slides) == len(deck.slides)  # reopened: every part is a slide


def test_loop_table_over_eight_rows_is_split_by_rows():
    rows = "\n".join(f"| 行{i} | {i} |" for i in range(1, 12))
    src = f"# 表\n| 項目 | A |\n|-|-|\n{rows}\n"
    assert too_dense(parse(src).slides[0])
    res = self_review(src)
    assert [f.rule for f in res.fixed] == ["split-slide"]
    assert not any(too_dense(s) for s in parse(res.text).slides) and rules(res.text) == []


def test_loop_six_boxes_of_eight_bullets_are_split():
    boxes = "\n".join(f"## B{i}\n{items(8, i)}" for i in range(1, 7))
    src = f"# T\n> m\n{boxes}\n"
    res = self_review(src)
    assert "split-slide" in [f.rule for f in res.fixed]
    assert not any(too_dense(s) for s in parse(res.text).slides) and res.after.warnings == 0


def test_loop_prefers_dense_when_it_clears_the_slide():
    path = Path(__file__).parent.parent / "bench" / "answers" / "run-5-sonnet" / "21-jp-quarterly-4col.md"
    src = path.read_text(encoding="utf-8")
    assert "design-too-many-blocks" in rules(src)  # 8 boxes on one slide
    res = self_review(src, path.parent)
    assert [f.rule for f in res.fixed] == ["dense"] and "@dense" in res.text
    assert len(parse(res.text).slides) == len(parse(src).slides) and res.after.warnings == 0


def test_loop_swaps_a_failing_declared_color():
    src = "# T\n> m\n## A\n{color=#EEEEEE}\n- light grey on white\n- b\n## B\n- ok\n## C\n- ok\n> concl\n"
    assert "contrast" in rules(src)
    res = self_review(src)
    assert [f.rule for f in res.fixed] == ["contrast-color"]
    assert "contrast" not in rules(res.text) and "{color=#1F2937}" in res.text
    assert res.text.count("\n") == src.count("\n")  # no other line changed


def test_loop_gives_light_ink_on_a_dark_declared_fill():
    src = "# T\n> m\n## A {fill=#111111}\n- default text color\n- b\n## B\n- ok\n## C\n- ok\n> concl\n"
    res = self_review(src)
    assert any(f.rule == "contrast-color" for f in res.fixed)
    assert "color=#FFFFFF" in res.text


def test_loop_never_touches_an_undeclared_color():
    src = "# T\n> m\n- plain text, no color declared\n"
    assert self_review(src).text == src


def test_loop_moves_a_long_title_tail_into_the_lead():
    t = "The quarterly review of revenue, churn, hiring and the security roadmap for the company"
    src = f"# {t}\n## A\n- one\n## B\n- two\n## C\n- three\n> concl\n"
    assert "design-long-title" in rules(src)
    res = self_review(src)
    assert [f.rule for f in res.fixed] == ["long-title"]
    assert "design-long-title" not in rules(res.text)
    deck = parse(res.text)
    assert deck.slides[0].lead is not None
    words = lambda s: re.findall(r"\w+", s)  # noqa: E731
    assert words(
        deck.slides[0].title.paragraphs[0].plain + " " + deck.slides[0].lead.paragraphs[0].plain
    ) == words(t)


def test_loop_runs_the_mechanical_fixes_too():
    src = "# T\n@3 flwo\n## A\n- a\n## B\n- b\n## C\n- c\n> concl\n"
    res = self_review(src)
    assert [f.rule for f in res.fixed] == ["unknown-token"] and "@3 flow" in res.text


def test_loop_is_idempotent_and_leaves_good_decks_alone():
    src = f"# 長いリスト\n> 要点\n{items(22)}\n"
    once = self_review(src)
    again = self_review(once.text)
    assert again.text == once.text and again.fixed == []
    for name in ("01-basics.md", "03-vi-report.md", "06-jp-market.md"):
        text = (EXAMPLES / name).read_text(encoding="utf-8")
        assert self_review(text, EXAMPLES).text == text


def test_loop_keeps_crlf():
    src = f"# 長い\r\n> 要点\r\n{items(22).replace(chr(10), chr(13) + chr(10))}\r\n"
    res = self_review(src)
    assert res.changed and "\r\n" in res.text and "\n" not in res.text.replace("\r\n", "")


def test_loop_stops_after_three_rounds():
    boxes = "\n".join(f"## B{i}\n{items(8, i)}" for i in range(1, 7))
    res = self_review(f"# T\n{boxes}\n", max_rounds=1)
    assert res.rounds <= 1


def test_loop_is_fuzz_safe():
    rnd = random.Random(7)
    base = (EXAMPLES / "02-jp-dense.md").read_text(encoding="utf-8").splitlines()
    extra = [
        "@3 flwo",
        "{color=#EEE}",
        "## 箱",
        "- x" * 3,
        "| a | b |",
        "|-|-|",
        "```",
        "> q",
        "※ n",
        "???",
        "@end",
        "---",
    ]
    for _ in range(12):
        lines = list(base)
        for _ in range(rnd.randint(1, 6)):
            lines.insert(rnd.randrange(len(lines) + 1), rnd.choice(extra))
        if rnd.random() < 0.3:
            del lines[rnd.randrange(len(lines)) :]
        res = self_review("\n".join(lines), EXAMPLES, max_rounds=2)
        assert isinstance(res.text, str) and res.after.score >= 0


def test_loop_on_empty_and_html_input():
    assert self_review("").text == ""
    html = "<section><h1>T</h1><p>x</p></section>"
    assert self_review(html).text == html


# --------------------------------------------------------------------------- CLI


def run(capsys, *argv: str) -> tuple[int, str]:
    code = main(["review", *argv])
    return code, capsys.readouterr().out


def test_cli_review_fix_writes_output_and_leaves_input(tmp_path, capsys):
    f = tmp_path / "a.md"
    src = f"# 長いリスト\n> 要点\n{items(22)}\n"
    f.write_text(src, encoding="utf-8")
    out = tmp_path / "fixed.md"
    code, text = run(capsys, str(f), "--fix", "-o", str(out))
    assert code == 0 and f.read_text(encoding="utf-8") == src
    assert "fixed L1 split-slide" in text and re.search(r"score: \d+ -> \d+/100 \(\d rounds?\)", text)
    assert "(1/" in out.read_text(encoding="utf-8")


def test_cli_review_fix_in_place_and_json(tmp_path, capsys):
    f = tmp_path / "a.md"
    f.write_text(f"# 長いリスト\n> 要点\n{items(22)}\n", encoding="utf-8")
    code, text = run(capsys, str(f), "--fix", "--format", "json")
    data = json.loads(text)
    assert code == 0 and data["score"] > data["score_before"] and data["rounds"] >= 1
    assert data["fixed"][0]["rule"] == "split-slide" and "(1/" in f.read_text(encoding="utf-8")


def test_cli_review_fix_leaves_a_good_deck_byte_identical(tmp_path, capsys):
    f = tmp_path / "a.md"
    f.write_text("# A\n> m\n- x\n- y\n", encoding="utf-8")
    before = f.read_bytes()
    code, text = run(capsys, str(f), "--fix")
    assert code == 0 and f.read_bytes() == before
    assert re.search(r"^score: \d+/100$", text, re.M) and not re.search(r"score: \d+ ->", text)


def test_cli_review_output_needs_fix(tmp_path, capsys):
    f = tmp_path / "a.md"
    f.write_text("# A\n- x\n", encoding="utf-8")
    assert main(["review", str(f), "-o", str(tmp_path / "b.md")]) == 2
    assert main(["review", str(tmp_path / "missing.md"), "--fix"]) == 2


def test_cli_review_fix_on_json_only_notes(tmp_path, capsys):
    f = tmp_path / "a.json"
    f.write_text(json.dumps({"slides": []}), encoding="utf-8")
    assert main(["review", str(f), "--fix"]) == 0
    assert "Markdown decks only" in capsys.readouterr().err


def test_cli_review_plain_still_works(tmp_path, capsys):
    f = tmp_path / "a.md"
    f.write_text("# A\n> m\n- x\n", encoding="utf-8")
    code, text = run(capsys, str(f))
    assert code == 0 and re.search(r"score: \d+/100", text)


# --------------------------------------------------------------------------- pixels (LibreOffice)


@needs_soffice
def test_pixel_contrast_on_a_picture_background_and_its_fix(tmp_path, capsys):
    import shutil

    shutil.copy(EXAMPLES / "assets" / "landscape.png", tmp_path / "bg.png")
    f = tmp_path / "a.md"
    f.write_text(
        "# Picture\n@bg=bg.png\n> m\n{color=#CCCCCC}\nLight grey text over a landscape.\n- two\n- three\n",
        encoding="utf-8",
    )
    png = tmp_path / "png"
    code, text = run(capsys, str(f), "--png", str(png))
    assert code == 0 and "pixel-contrast" in text and (png / "slide-01.png").exists()
    code, text = run(capsys, str(f), "--png", str(png), "--fix", "-o", str(tmp_path / "o.md"))
    assert "pixel-contrast: declared color" in text
    assert "{color=#CCCCCC}" not in (tmp_path / "o.md").read_text(encoding="utf-8")
