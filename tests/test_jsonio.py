from slidemark.jsonio import load_deck
from slidemark.parser import parse


def test_roundtrip_text():
    deck = parse("# A\n- x\n---\n# B\n- y\n")
    again = load_deck(deck.model_dump_json())
    assert len(again.slides) == 2 and not again.diagnostics


def test_bad_json_diagnostics():
    deck = load_deck('{"slides": "nope"}')
    assert deck.diagnostics and all(d.rule == "bad-json" and d.level == "error" for d in deck.diagnostics)
    assert "slides" in deck.diagnostics[0].message


def test_not_json_and_missing_file(tmp_path):
    assert load_deck("{oops").diagnostics[0].rule == "bad-json"
    assert load_deck(tmp_path / "nope.json").diagnostics[0].rule == "bad-json"
