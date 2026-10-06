"""Japanese orphan squeeze (追い込み): a CJK paragraph whose last line holds 1-2 characters gets a small
negative character spacing (a:rPr spc) when that pulls the orphan up; layout and renderer agree."""

from __future__ import annotations

from pathlib import Path

import pytest
from pptx import Presentation

from slidemark import build
from slidemark.importer import import_pptx
from slidemark.ir import Paragraph, Run, Style
from slidemark.layout import measure
from slidemark.theme import LayoutTokens

TEXT = "42店を統廃合・小型化・業態転換"
W, SIZE = 190.44, 13.761  # a dense card: the model puts "転換" on a second line
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


@pytest.fixture(autouse=True)
def _tokens():
    measure.set_tokens(LayoutTokens())
    measure.set_default_font(None)
    yield
    measure.set_tokens(LayoutTokens())
    measure.set_default_font(None)


def _p(text: str = TEXT) -> Paragraph:
    return Paragraph(runs=[Run(text=text)])


def test_orphan_is_detected():
    lines, tail = measure._lines_tail(measure.para_segments(_p()), W, SIZE, None, 0.0)
    assert lines == 2
    assert tail <= 2.0


def test_squeeze_pulls_orphan_onto_previous_line():
    p = _p()
    sq = measure.paragraph_squeeze(p, Style(), W, SIZE)
    assert sq < 0
    assert abs(sq) <= 0.1 * SIZE + 1e-9
    segs = measure.para_segments(p)
    assert measure.count_lines(segs, W, SIZE, None, 0.0) == 2
    assert measure.count_lines(segs, W * 0.99, SIZE, None, sq) == 1  # fits with the safety margin


def test_layout_height_counts_the_squeeze():
    p = _p()
    w = round(W * 12700)
    squeezed = measure.paragraphs_height([p], w, Style(font_size=SIZE), squeeze=True)
    plain = measure.paragraphs_height([p], w, Style(font_size=SIZE), squeeze=False)
    assert squeezed < plain


def test_no_squeeze_when_it_would_not_help():
    # an orphan on a short line cannot be pulled back by 0.1 em per character
    p = _p("売上高の推移を示す")
    assert measure.paragraph_squeeze(p, Style(), 8 * SIZE, SIZE) == 0.0


def test_no_squeeze_without_orphan_or_cjk():
    assert measure.paragraph_squeeze(_p("short"), Style(), W, SIZE) == 0.0
    assert measure.paragraph_squeeze(_p("a long latin paragraph " * 5), Style(), W, SIZE) == 0.0


def test_explicit_letter_spacing_wins():
    assert measure.paragraph_squeeze(_p(), Style(letter_spacing=0.5), W, SIZE) == 0.0
    p = _p()
    p.style = Style(letter_spacing=-0.2)
    assert measure.paragraph_squeeze(p, Style(), W, SIZE) == 0.0


def test_token_off_switch():
    measure.set_tokens(LayoutTokens(cjk_squeeze_max=0))
    assert measure.paragraph_squeeze(_p(), Style(), W, SIZE) == 0.0


EXAMPLE = Path(__file__).parent.parent / "examples" / "20-jp-retail-dense.md"


def _spc_by_paragraph(path, slide=1):
    out = {}
    prs = Presentation(str(path))
    for shp in prs.slides[slide].shapes:
        if not shp.has_text_frame:
            continue
        for para in shp.text_frame.paragraphs:
            out[para.text] = {r._r.find(A + "rPr").get("spc") for r in para.runs}
    return out


def test_render_writes_spc_on_squeezed_paragraphs_only(tmp_path):
    src = EXAMPLE.read_text(encoding="utf-8")
    out = tmp_path / "a.pptx"
    build(src, out)
    spc = _spc_by_paragraph(out)  # slide 2: "42店を統廃合・小型化・業態転換" wraps with one character left
    (orphan,) = [t for t in spc if "統廃合" in t]
    assert len(spc[orphan]) == 1 and int(next(iter(spc[orphan]))) < 0  # the same value on every run
    assert all(v in (set(), {None}) for t, v in spc.items() if t.startswith("PB比率"))
    off = tmp_path / "b.pptx"
    build("style: layout.cjk_squeeze_max=0\n" + src, off)
    assert all(v in (set(), {None}) for v in _spc_by_paragraph(off).values())


def test_importer_does_not_emit_letter_spacing(tmp_path):
    out = tmp_path / "d.pptx"
    build(EXAMPLE.read_text(encoding="utf-8"), out)
    assert any(v not in (set(), {None}) for v in _spc_by_paragraph(out).values())
    text, _ = import_pptx(out, tmp_path)
    assert "letter" not in text.lower()
    assert "spacing" not in text.lower()
