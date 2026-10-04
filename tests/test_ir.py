from slidemark.ir import Container, Deck, Diagnostic, Paragraph, Run, Slide, Style, Text
from slidemark.units import slide_size, to_emu


def test_deck_json_roundtrip_with_nested_containers():
    inner = Text(paragraphs=[Paragraph(runs=[Run(text="日本語")], marker="bullet")])
    box = Container(title=Text(role="heading"), grid="aab/aac", children=[Container(children=[inner])])
    deck = Deck(slides=[Slide(elements=[box])])
    again = Deck.model_validate_json(deck.model_dump_json())
    assert again.slides[0].elements[0].children[0].children[0].paragraphs[0].plain == "日本語"


def test_style_merge_later_wins_and_none_inherits():
    s = Style(font_size=18, color="fg").merged(Style(color="primary"), None, Style(bold=True))
    assert (s.font_size, s.color, s.bold) == (18, "primary", True)


def test_units():
    assert to_emu("1in") == 914400
    assert to_emu(12) == 12 * 12700
    assert to_emu("50%", 1000) == 500
    assert slide_size("16:9") == (12192000, 6858000)


def test_diagnostic_is_one_line():
    d = Diagnostic(level="warning", message="overflow", slide=2, line=10, rule="overflow", hint="use .dense")
    assert str(d) == "warning slide 2 L10 overflow: overflow -> use .dense"
