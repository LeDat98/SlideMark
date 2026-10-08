"""The build's look: line says where the accent colour shows, so agents need not open slides to find it."""

from __future__ import annotations

from slidemark.cli import _look_line
from slidemark.parser import parse

HEAD = "theme: none\ncolors: bg=#FFFFFF fg=#222222 primary=#1E3A5F accent=#C8102E\n\n"


def test_accent_on_marks_and_charts():
    deck = parse(HEAD + "# A\n- ==key== point\n\n# B\n```column\n,a,b\nX,1,2\nY,2,3\nZ,3,4\n```\n")
    line = _look_line(deck)
    assert "accent on 1 chart, 1 mark" in line


def test_accent_unused_is_said():
    line = _look_line(parse(HEAD + "# A\n- plain point\n"))
    assert "accent unused" in line


def test_plain_deck_has_no_look_line():
    assert _look_line(parse("# A\n- x\n")) is None
