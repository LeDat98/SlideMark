"""Accent-mark lint: a text-less mark in the accent (dot, arrow) needs 3:1 on its backdrop (WCAG 1.4.11)."""

from __future__ import annotations

import re

from slidemark import build
from slidemark.contrast import ratio
from slidemark.ir import Deck, Placed, Shape, Slide, Style
from slidemark.lint import lint_slide
from slidemark.parser import parse
from slidemark.template import deck_theme
from slidemark.theme import get_theme

DOT = "{x=10% y=10% w=6% h=10% shape=ellipse fill=accent}"


def _contrast(src: str, tmp_path) -> list[str]:
    deck = build(src, tmp_path / "a.pptx")
    return [f"{d.message} -> {d.hint}" for d in deck.diagnostics if d.rule == "contrast"]


def test_a_pale_accent_dot_warns_with_a_passing_colour(tmp_path):
    got = _contrast(f"colors: accent=#F2A33A\n\n# Dot\n@free\n{DOT}\n", tmp_path)
    assert len(got) == 1 and "accent #F2A33A at 2.1:1" in got[0] and "needs 3:1" in got[0]
    fix = re.search(r"accent=(#[0-9A-F]{6})", got[0]).group(1)
    assert ratio(fix, "#FFFFFF") >= 3.0
    assert not _contrast(f"colors: accent={fix}\n\n# Dot\n@free\n{DOT}\n", tmp_path)  # the hint is enough


def test_the_token_turns_it_off(tmp_path):
    src = f"colors: accent=#F2A33A\nstyle: render.accent_mark_contrast=0\n\n# Dot\n@free\n{DOT}\n"
    assert not _contrast(src, tmp_path)


def test_every_preset_accent_passes_as_a_mark_on_its_background():
    for name in ("default", "midnight", "jp-business", "editorial"):
        th = get_theme(name)
        for back in ("bg", "surface"):
            got = ratio(th.hexval("accent"), th.hexval(back))
            assert got >= th.render.accent_mark_contrast, (name, back, got)


def test_a_dot_on_a_thin_track_is_judged_on_the_slide():
    th = get_theme("default")
    track = Placed(
        element=Shape(shape="rect"), x=0, y=490_000, w=9_000_000, h=20_000, style=Style(fill="#6B7280")
    )
    dot = Placed(
        element=Shape(shape="ellipse"),
        x=400_000,
        y=400_000,
        w=200_000,
        h=200_000,
        style=Style(fill="#F2A33A"),
    )
    th2 = th.model_copy(update={"colors": {**th.colors, "accent": "#F2A33A"}})
    msgs = [
        d.message for d in lint_slide([track, dot], Deck(slides=[Slide()]), th2, 0) if d.rule == "contrast"
    ]
    assert msgs and "on #FFFFFF" in msgs[0]  # not on the grey track under its centre


def test_translucent_and_cover_art_marks_are_decor(tmp_path):
    th = get_theme("default")
    th2 = th.model_copy(update={"colors": {**th.colors, "accent": "#F2A33A"}})
    soft = Placed(
        element=Shape(shape="ellipse"),
        x=0,
        y=0,
        w=200_000,
        h=200_000,
        style=Style(fill="#F2A33A", opacity=0.4),
    )
    art = Placed(
        element=Shape(shape="ellipse", attrs={"shape_name": "Cover art 3"}),
        x=0, y=0, w=200_000, h=200_000, style=Style(fill="#F2A33A"),
    )  # fmt: skip
    assert not [d for d in lint_slide([soft, art], Deck(slides=[Slide()]), th2, 0) if d.rule == "contrast"]


def test_text_on_the_accent_is_not_a_mark(tmp_path):
    src = "colors: accent=#F2A33A\n\n# Box\n@free\nGo {x=10% y=10% w=30% h=20% fill=accent}\n"
    assert not [m for m in _contrast(src, tmp_path) if "a mark needs" in m]


def test_editorial_body_text_meets_the_14pt_floor():
    deck = parse("theme: editorial\n\n# T\n")
    th, _ = deck_theme(deck, ".")
    assert th.sizes["table"] >= 14 and th.sizes["body"] >= 14
    assert th.classes["card"].font_size >= 14
