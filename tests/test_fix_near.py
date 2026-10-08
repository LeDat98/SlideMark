"""A did-you-mean fix rewrites the source only for the one name within one letter (or a documented alias)."""

from __future__ import annotations

import pytest

from slidemark import icons
from slidemark.cli import main
from slidemark.fix import fix_text
from slidemark.parser import parse


def fix(text: str) -> tuple[str, list[str]]:
    new, fixed = fix_text(text, lambda t: parse(t).diagnostics)
    return new, [f.rule for f in fixed]


def _icon_deck(name: str) -> str:
    return f"# T\n## A {{icon={name}}}\nx\n## B\ny\n"


@pytest.mark.parametrize(
    ("name", "want"), [("shiled", "shield"), ("cheeck", "check"), ("rockt", "rocket"), ("brian", "brain")]
)
def test_one_letter_slip_is_fixed(name, want):
    new, fixed = fix(_icon_deck(name))
    assert fixed == ["unknown-icon"] and f"{{icon={want}}}" in new


@pytest.mark.parametrize("name", ["eyeball", "refreshh2", "rotate", "zzz", "diagram"])
def test_far_name_is_left_alone_and_warned_with_close_names(name):
    src = _icon_deck(name)
    deck = parse(src)
    warn = [d for d in deck.diagnostics if d.rule == "unknown-icon"]
    assert warn and warn[0].level == "warning"
    new, fixed = fix(src)
    assert new == src and fixed == []
    assert "icon" not in deck.slides[0].elements[0].attrs  # the icon is left out


def test_far_name_hint_lists_up_to_three_names_and_never_guesses():
    deck = parse(_icon_deck("sunrise"))
    hint = next(d.hint for d in deck.diagnostics if d.rule == "unknown-icon")
    assert "did you mean '" not in hint
    names = hint.split("did you mean one of ", 1)[1].split("?", 1)[0].split(", ")
    assert 1 <= len(names) <= 3 and all(n in icons.names() for n in names)


def test_two_names_one_letter_away_is_not_unique():
    # `chrt` is one letter from both `chart` and `chat`: a guess, so the source stays
    src = _icon_deck("chrt")
    new, fixed = fix(src)
    assert new == src and fixed == []
    hint = next(d.hint for d in parse(src).diagnostics if d.rule == "unknown-icon")
    assert "chart" in hint and "chat" in hint


@pytest.mark.parametrize(
    "name",
    [
        "eye",
        "brain",
        "robot",
        "layers",
        "tags",
        "list",
        "tool",
        "microphone",
        "image",
        "video",
        "arrow",
        "loop",
    ],
)
def test_aliases_fresh_agents_reach_for_resolve(name):
    assert icons.path(name)
    deck = parse(_icon_deck(name))
    assert not [d for d in deck.diagnostics if d.rule == "unknown-icon"]
    assert deck.slides[0].elements[0].attrs["icon"] == name


def test_far_attr_class_token_and_header_are_not_rewritten():
    for src in (
        "# T\n## A {colour=red}\n- a\n",  # `colour` -> `color` is one letter: fixed
        "# T\n## A {.prim}\n- a\n",  # `prim` is two letters from `primary`: left
        "# T\n@3 flowing\n## A\n- a\n## B\n- b\n## C\n- c\n",
        "thememe: default\n\n# T\n- a\n",
    ):
        new, fixed = fix(src)
        if "colour" in src:
            assert fixed == ["unknown-attr"] and "{color=red}" in new
        else:
            assert new == src and fixed == [], src


def test_build_leaves_a_far_icon_in_the_source(tmp_path):
    md = tmp_path / "d.md"
    md.write_text(_icon_deck("eyeball"), encoding="utf-8")
    assert main(["build", str(md), "-o", str(tmp_path / "d.pptx")]) in (0, None)
    assert "icon=eyeball" in md.read_text(encoding="utf-8")
