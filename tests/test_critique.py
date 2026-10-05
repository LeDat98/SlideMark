"""Design critic: each rule fires on a minimal bad deck and stays quiet on a good one."""

from __future__ import annotations

import json

import pytest

from slidemark.cli import main
from slidemark.critique import critique, review_score
from slidemark.ir import Diagnostic
from slidemark.layout import layout_slide
from slidemark.parser import parse
from slidemark.template import resolve_theme

WORDS = " ".join(["lorem ipsum dolor sit amet"] * 30)
GOOD = (
    "# Q3 results\n> Revenue up 8%\n## Now\n- 12 oku\n- 8% up\n"
    "## Issue\n- churn 2.1%\n- cost\n## Plan\n- onboarding\n- pricing\n> Go\n"
)


def _run(src: str, mutate=None) -> list[Diagnostic]:
    deck = parse(src)
    theme, _ = resolve_theme(deck.theme, ".")
    placed = [layout_slide(s, deck, theme, i) for i, s in enumerate(deck.slides)]
    if mutate:
        mutate(placed)
    return critique(deck, placed, theme)


def _rules(src: str, mutate=None) -> set[str]:
    return {d.rule for d in _run(src, mutate)}


def test_natural_height_counts_the_paragraph_gap():
    from slidemark.critique import _natural_height
    from slidemark.ir import Paragraph, Placed, Run, Style, Text

    paras = [Paragraph(runs=[Run(text=f"line {i}")]) for i in range(6)]
    mk = lambda **a: Placed(  # noqa: E731
        element=Text(paragraphs=paras, attrs=a), x=0, y=0, w=3_000_000, h=2_000_000, style=Style(font_size=18)
    )
    assert _natural_height(mk(para_gap=0.6)) > _natural_height(mk())


def test_good_deck_is_quiet():
    assert _run(GOOD) == []


def test_sparse_box():
    assert "design-sparse-box" in _rules("# T\n> m\n## A\nx\n## B\n" + "- one\n" * 6)


def test_wall_of_text():
    assert "design-wall-of-text" in _rules("# T\n" + WORDS + "\n\n- a\n- b\n")
    assert "design-wall-of-text" in _rules("# T\n" + "日本語の長い文章です。" * 25 + "\n\n- a\n")


def test_too_many_blocks():
    assert "design-too-many-blocks" in _rules("# T\n" + "".join(f"## B{i}\n- x\n" for i in range(8)))


def test_unbalanced():
    src = "# T\n> m\n## A\nx\n## B\n" + "".join(f"- item number {i} with some words\n" for i in range(9))
    assert "design-unbalanced" in _rules(src)


def test_empty_band():
    ds = [d for d in _run("# T\n- a\n- b\n") if d.rule == "design-empty-band"]
    assert ds and "conclusion" in (ds[0].hint or "")


def test_no_message_is_info():
    ds = [d for d in _run("# T\n## A\n- x\n## B\n- z\n> end\n") if d.rule == "design-no-message"]
    assert ds and ds[0].level == "info" and "key message" in (ds[0].hint or "")
    assert "design-no-message" not in _rules(GOOD)


def test_inconsistent_boxes():
    def shrink(placed):
        bodies = [p for p in placed[0] if getattr(p.element, "role", None) == "body"]
        bodies[0].font_scale = 0.6

    assert "design-inconsistent-boxes" in _rules(GOOD, shrink)


def test_long_title():
    src = (
        "# This is a very long slide title that surely wraps over two lines of the slide\n"
        "> m\n## A\n- x\n## B\n- y\n"
    )
    assert "design-long-title" in _rules(src)


def test_rules_are_design_prefixed_with_hint():
    for d in _run("# T\n" + WORDS + "\n\n- a\n"):
        assert d.rule.startswith("design-") and d.hint and d.level in ("info", "warning")


def test_score_bounds():
    assert review_score([]) == 100
    many = [Diagnostic(level="error", message="x", rule="bad") for _ in range(50)]
    assert review_score(many) == 0
    one = [Diagnostic(level="warning", message="x", rule="design-wall-of-text")]
    assert 0 < review_score(one) < 100
    assert review_score(one, slides=10) > review_score(one, slides=1)
    assert review_score(one, slides=0) == review_score(one, slides=1)


NASTY = [
    "",
    "# ",
    "# T\n@3\n",
    "# T\n## A\n\n## B\n\n## C\n",
    "# 😀" * 40 + "\n- x\n",
    "# T\n| a |\n|---|\n",
    "# T\n```column\n```\n",
    "---\n---\n---\n",
    "# T\n@aab/aac\n## A\n## B\n## C\n",
    "# T\n" + "あ" * 3000 + "\n",
    "theme: nope\n# T\n- x\n",
    "# T\n![](x.png)\n@1:0\n## A\n",
]


@pytest.mark.parametrize("src", NASTY)
def test_never_raises(src):
    ds = _run(src)
    assert all(isinstance(d, Diagnostic) for d in ds)
    assert 0 <= review_score(ds, 1) <= 100


def test_cli_text_and_json(tmp_path, capsys):
    f = tmp_path / "a.md"
    f.write_text("# T\n- a\n- b\n", encoding="utf-8")
    assert main(["review", str(f)]) == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert lines[-1].startswith("score: ") and lines[-1].endswith("/100")
    assert any("design-empty-band" in line and "->" in line for line in lines[:-1])
    assert main(["review", str(f), "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert 0 <= data["score"] <= 100
    assert any(d["rule"] == "design-empty-band" for d in data["diagnostics"])


def test_cli_exit_0_even_with_errors(tmp_path, capsys):
    f = tmp_path / "a.md"
    f.write_text("# A\n```pie\n```\n", encoding="utf-8")
    assert main(["review", str(f)]) == 0
    assert "score:" in capsys.readouterr().out


def test_cli_missing_file(capsys):
    assert main(["review", "/nonexistent/x.md"]) == 2


def test_cli_png_never_fails(tmp_path, capsys):
    f = tmp_path / "a.md"
    f.write_text("# T\n- a\n", encoding="utf-8")
    assert main(["review", str(f), "--png", str(tmp_path / "png")]) == 0
    assert "score:" in capsys.readouterr().out
