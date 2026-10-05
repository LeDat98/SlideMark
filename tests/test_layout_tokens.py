"""Layout constants come from ``theme.layout`` / ``theme.render``: changing a token changes the output."""

from __future__ import annotations

from slidemark.ir import Container, Deck, Paragraph, Run, Slide, Style, Text
from slidemark.layout import layout_slide, measure
from slidemark.theme import LayoutTokens, get_theme


def T(s, role="body"):
    return Text(role=role, paragraphs=[Paragraph(runs=[Run(text=s)])])


def themed(name="default", **layout):
    th = get_theme(name)
    return th.model_copy(update={"layout": LayoutTokens(**layout)})


def sparse_box_slide():
    return Slide(
        title=T("Title", "title"),
        grid="2",
        elements=[
            Container(title=T("A", "heading"), children=[T("short")]),
            Container(title=T("B", "heading"), children=[T("short")]),
        ],
    )


def scales(theme):
    s = sparse_box_slide()
    placed = layout_slide(s, Deck(slides=[s]), theme, 0)
    return [p.font_scale for p in placed if isinstance(p.element, Text) and p.element.role == "body"]


def test_grow_true_grows_sparse_text():
    assert max(scales(themed())) > 1.0


def test_grow_false_keeps_nominal_sizes():
    got = scales(themed(grow=False))
    assert got and all(abs(f - 1.0) < 1e-9 for f in got)


def test_grow_false_text_slide_and_dense_theme():
    s = Slide(title=T("Title", "title"), elements=[T("one short line")])
    for name in ("default", "jp-business"):
        th = themed(name, grow=False)
        placed = layout_slide(s, Deck(slides=[s]), th, 0)
        body = [p for p in placed if isinstance(p.element, Text) and p.element.role == "body"]
        assert all(abs(p.font_scale - 1.0) < 1e-9 for p in body)


def test_top_gap_token_moves_the_body():
    s = Slide(title=T("Title", "title"), elements=[T("line")])

    def body_y(**kw):
        placed = layout_slide(s, Deck(slides=[s]), themed(grow=False, **kw), 0)
        return min(p.y for p in placed if isinstance(p.element, Text) and p.element.role == "body")

    assert body_y(top_gap="1in") - body_y(top_gap="0.25in") == round(0.75 * 914400)


def test_line_height_token_changes_measured_height():
    paras = [Paragraph(runs=[Run(text="hello")])]
    try:
        measure.set_tokens(LayoutTokens(line_latin=1.2))
        a = measure.paragraphs_height(paras, 5_000_000, Style())
        measure.set_tokens(LayoutTokens(line_latin=2.4))
        b = measure.paragraphs_height(paras, 5_000_000, Style())
    finally:
        measure.set_tokens(LayoutTokens())
    assert abs(b / a - 2.0) < 1e-6
