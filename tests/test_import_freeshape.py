"""A text-less preset shape of a foreign deck becomes a `{x= y= w= h= shape=}` block on a `@free` slide."""

from __future__ import annotations

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches, Pt

from slidemark.build import build
from slidemark.importer import import_pptx
from slidemark.parser import parse


def _deck():
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    return prs, prs.slides.add_slide(prs.slide_layouts[6])


def _text(slide, x, y, w, h, lines, size=16, bold=False):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    for i, line in enumerate(lines if isinstance(lines, list) else [lines]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        r = p.add_run()
        r.text = line
        r.font.size = Pt(size)
        r.font.bold = bold


def _shape(slide, kind, x, y, w, h, rgb):
    s = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    s.fill.solid()
    s.fill.fore_color.rgb = RGBColor.from_string(rgb)
    s.line.fill.background()
    return s


def _flow_deck(tmp_path):
    prs, s = _deck()
    _text(s, 0.6, 0.3, 12, 0.8, "RAG", size=30, bold=True)
    cards = [("Ask", "A question"), ("Search", "Find the text"), ("Answer", "With sources")]
    for i, (h, body) in enumerate(cards):
        x = 0.6 + i * 4.2
        _shape(s, MSO_SHAPE.RECTANGLE, x, 1.9, 3.6, 2.6, "F1F4F9")
        _text(s, x + 0.2, 2.1, 3.2, 0.6, h, size=22, bold=True)
        _text(s, x + 0.2, 2.9, 3.2, 1.2, body, size=16)
    for i in range(2):
        _shape(s, MSO_SHAPE.CHEVRON, 4.3 + i * 4.2, 2.9, 0.4, 0.6, "F2A33A")
    path = tmp_path / "flow.pptx"
    prs.save(path)
    return path


def test_textless_chevrons_between_cards_become_shape_blocks_on_a_free_slide(tmp_path):
    text, diags = import_pptx(_flow_deck(tmp_path))
    assert not [d for d in diags if d.level == "error"]
    assert "@free" in text
    blocks = [ln for ln in text.splitlines() if "shape=chevron" in ln]
    assert len(blocks) == 2, text
    assert all(ln.startswith("{x=") and "fill=#F2A33A" in ln for ln in blocks)
    deck = parse(text)
    sl = deck.slides[0]
    assert sl.layout == "free"
    assert sum(1 for e in sl.elements if e.type == "shape") == 2
    assert sum(1 for e in sl.elements if e.type == "container") == 3  # the three cards stay boxes
    assert all(e.box is not None and e.box.x is not None for e in sl.elements)


def test_the_rebuilt_deck_draws_the_chevrons(tmp_path):
    text, _ = import_pptx(_flow_deck(tmp_path))
    out = tmp_path / "back.pptx"
    build(text, out)
    prs = Presentation(out)
    chev = [
        sh for sh in prs.slides[0].shapes if sh.shape_type == 1 and sh.auto_shape_type == MSO_SHAPE.CHEVRON
    ]
    assert len(chev) == 2
    assert all(sh.name.startswith("Shape ") for sh in chev)


def test_a_plain_rectangle_or_an_arrow_of_a_foreign_deck_is_not_a_shape_block(tmp_path):
    prs, s = _deck()
    _text(s, 0.6, 0.3, 12, 0.8, "Plan", size=30, bold=True)
    _text(s, 0.8, 2.0, 4, 1, "Left", size=18)
    _shape(s, MSO_SHAPE.RECTANGLE, 0.6, 1.2, 12, 0.05, "1F2A44")
    path = tmp_path / "plain.pptx"
    prs.save(path)
    text, _ = import_pptx(path)
    assert "@free" not in text


def test_a_shape_block_round_trips_as_a_shape_block(tmp_path):
    src = (
        "# T\n@free\n{x=1in y=2in w=1in h=1in shape=hexagon fill=accent}\n"
        "{x=3in y=2in w=4in h=2in}\nbody text\n"
    )
    out = tmp_path / "a.pptx"
    build(src, out)
    text, _ = import_pptx(out)
    assert "shape=hexagon" in text and "@free" in text
