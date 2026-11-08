"""The eyebrow: a small mono UPPERCASE tracked line above the slide title."""

from __future__ import annotations

import pytest
from pptx import Presentation

from slidemark import build
from slidemark.importer import import_pptx
from slidemark.parser import parse

DECK = """theme: editorial

# Deck title

# Architecture

# Why now {eyebrow="Platform · Strategy"}
> A lead line
- one
- two

# Second
- a
"""


def _shapes(tmp_path, text):
    out = tmp_path / "d.pptx"
    build(text, out)
    return Presentation(out), out


def _by_name(slide, name):
    return next((s for s in slide.shapes if s.name == name), None)


def test_parse_title_attr():
    deck = parse(DECK)
    assert deck.slides[2].attrs["eyebrow"] == "Platform · Strategy"
    assert not [d for d in deck.diagnostics if "eyebrow" in (d.message or "")]


def test_header_line_sets_the_mode():
    deck = parse("eyebrow: section\n\n# A\n- x\n")
    from slidemark.theme import apply_tokens, get_theme

    theme, diags = apply_tokens(get_theme(deck.theme), deck.tokens)
    assert theme.eyebrow == "section" and not diags


def test_bad_mode_is_a_diagnostic_not_a_crash():
    deck = parse("eyebrow: loud\n\n# A\n- x\n")
    assert any(d.rule == "bad-token" for d in deck.diagnostics)


def test_render_mono_uppercase_above_title(tmp_path):
    prs, _ = _shapes(tmp_path, DECK)
    s = prs.slides[2]
    eb, title = _by_name(s, "Eyebrow"), _by_name(s, "Title")
    assert eb is not None and title is not None
    assert eb.text_frame.text == "PLATFORM · STRATEGY"  # uppercase in the file itself
    assert eb.top + eb.height <= title.top + 1  # above the title, never over it
    run = eb.text_frame.paragraphs[0].runs[0]
    assert run.font.name == "Consolas"  # theme mono face
    assert run.font.size.pt <= 10.5
    assert 'spc="' in run._r.xml  # tracked


def test_section_mode_uses_the_section_name(tmp_path):
    prs, _ = _shapes(tmp_path, "eyebrow: section\n" + DECK)
    texts = [(_by_name(s, "Eyebrow").text_frame.text if _by_name(s, "Eyebrow") else None) for s in prs.slides]
    assert texts[0] is None  # cover
    assert texts[1] is None  # the section slide itself
    assert texts[2] == "PLATFORM · STRATEGY"  # an own text wins
    assert texts[3] == "ARCHITECTURE"  # the section before it


def test_off_by_default_and_per_slide_off(tmp_path):
    plain = DECK.replace('{eyebrow="Platform · Strategy"}', "")
    prs, _ = _shapes(tmp_path, plain.replace("theme: editorial", "theme: default"))
    assert all(_by_name(s, "Eyebrow") is None for s in prs.slides)  # other presets: off
    prs, _ = _shapes(tmp_path, plain.replace("theme: editorial", "theme: editorial\neyebrow: off"))
    assert all(_by_name(s, "Eyebrow") is None for s in prs.slides)
    prs, _ = _shapes(tmp_path, "eyebrow: section\n" + DECK.replace('"Platform · Strategy"', "off"))
    assert _by_name(prs.slides[2], "Eyebrow") is None


def test_title_moves_down_to_make_room(tmp_path):
    with_eb, _ = _shapes(tmp_path, DECK)
    without, _ = _shapes(
        tmp_path,
        DECK.replace('{eyebrow="Platform · Strategy"}', "").replace(
            "theme: editorial", "theme: editorial\neyebrow: off"
        ),
    )
    assert _by_name(with_eb.slides[2], "Title").top > _by_name(without.slides[2], "Title").top


def test_tokens_restyle_it(tmp_path):
    text = DECK.replace(
        "# Deck title", "style: eyebrow.size=14 eyebrow.case=none eyebrow.color=accent\n\n# Deck title", 1
    )
    prs, _ = _shapes(tmp_path, text)
    eb = _by_name(prs.slides[2], "Eyebrow")
    assert eb.text_frame.text == "Platform · Strategy"  # case=none
    assert eb.text_frame.paragraphs[0].runs[0].font.size.pt == pytest.approx(14, abs=0.6)


def test_round_trip(tmp_path):
    _, out = _shapes(tmp_path, DECK)
    md, _ = import_pptx(out)
    assert '{eyebrow="PLATFORM · STRATEGY"}' in md
    again = tmp_path / "again.pptx"
    build(md, again)
    eb = _by_name(Presentation(again).slides[2], "Eyebrow")
    assert eb is not None and eb.text_frame.text == "PLATFORM · STRATEGY"


def test_cover_and_section_ignore_it(tmp_path):
    prs, _ = _shapes(tmp_path, '# Cover {eyebrow="X"}\n\n# Next\n- a\n')
    assert _by_name(prs.slides[0], "Eyebrow") is None


def _eyebrows(tmp_path, text):
    prs, _ = _shapes(tmp_path, text)
    return [(_by_name(s, "Eyebrow").text_frame.text if _by_name(s, "Eyebrow") else None) for s in prs.slides]


def test_editorial_is_automatic_with_the_deck_name_as_fallback(tmp_path):
    # no section slide before the content slides: the deck name (the cover title) stands in
    got = _eyebrows(tmp_path, "theme: editorial\n\n# Platform review\n\n# One\n- a\n\n# Two\n- b\n")
    assert got == [None, "PLATFORM REVIEW", "PLATFORM REVIEW"]
    # after a section slide the section name wins
    assert _eyebrows(tmp_path, DECK)[3] == "ARCHITECTURE"


def test_cover_takes_a_meta_eyebrow(tmp_path):
    prs, _ = _shapes(
        tmp_path, 'theme: editorial\n\n# Platform review {eyebrow="Engineering · Q3"}\n\n# One\n- a\n'
    )
    eb, title = _by_name(prs.slides[0], "Eyebrow"), _by_name(prs.slides[0], "Title")
    assert eb is not None and eb.text_frame.text == "ENGINEERING · Q3"
    assert eb.top + eb.height <= title.top + title.height  # above the title text
    # without an own text: the author (never the title itself)
    got = _eyebrows(tmp_path, "theme: editorial\nauthor: Platform team\n\n# Platform review\n\n# One\n- a\n")
    assert got[0] == "PLATFORM TEAM"


def test_editorial_fallback_never_repeats_a_content_title(tmp_path):
    # no cover: slide 1 is content, so its title is not the deck name; the footer stands in, never a title
    got = _eyebrows(tmp_path, "theme: editorial\nfooter: Process review\n\n# Order flow\n- a\n\n# Two\n- b\n")
    assert got == ["PROCESS REVIEW", "PROCESS REVIEW"]
    assert _eyebrows(tmp_path, "theme: editorial\n\n# Order flow\n- a\n\n# Two\n- b\n") == [None, None]
