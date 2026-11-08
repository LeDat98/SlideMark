"""Wave 2026-11-08 lane C: ``@swimlane`` and ``@sequence`` (parser, fuzz, render, budget, design, import)."""

from __future__ import annotations

from pathlib import Path

import pytest
from pptx import Presentation

from slidemark import forms, forms5
from slidemark.build import build
from slidemark.importer import import_pptx
from slidemark.layout import layout_slide
from slidemark.lint import lint_deck
from slidemark.parser import parse
from slidemark.template import deck_theme

ROOT = Path(__file__).resolve().parent.parent
HEAD = "theme: editorial\nsizes: body=16\n\n"

SWIM = """# Order to cash
@swimlane
## Customer
- Place order
- 4: Pay invoice {.focal}
## Sales
- 2: Check credit
- 3: Confirm order
## Finance
- 5: Book payment
"""

SEQ = """# Checkout
@sequence
- Client > API: POST /order
- API > DB: insert
- DB >> API: ok
- API > API: retry
- API >> Client: 201 {.focal}
"""


def _diags(md: str, header: str = HEAD):
    deck = parse(header + md)
    theme, _ = deck_theme(deck, ".")
    placed = [layout_slide(s, deck, theme, i) for i, s in enumerate(deck.slides)]
    return deck, placed, lint_deck(deck, placed, theme)


def _shapes(tmp_path, md: str, header: str = HEAD, slide: int = 0):
    out = tmp_path / "d.pptx"
    build(header + md, out)
    return Presentation(str(out)).slides[slide]


def _cxn(slide):
    """name -> (prst, dash, rot) of every connector."""
    from pptx.oxml.ns import qn

    got = {}
    for el in slide.shapes._spTree.iter(qn("p:cxnSp")):
        name = el.find(qn("p:nvCxnSpPr")).find(qn("p:cNvPr")).get("name")
        sp = el.find(qn("p:spPr"))
        dash = sp.find(qn("a:ln")).find(qn("a:prstDash"))
        got[name] = (sp.find(qn("a:prstGeom")).get("prst"), dash.get("val") if dash is not None else None)
    return got


# --------------------------------------------------------------------------- parser / model


def test_forms_are_known_words():
    assert {"swimlane", "sequence"} <= set(forms.FORMS)
    deck = parse(HEAD + SWIM)
    assert deck.slides[0].classes == ["swimlane"]
    assert not [d for d in deck.diagnostics if d.level == "warning"]


def test_swimlane_columns_default_to_written_order_and_explicit_override():
    lanes = forms5.lanes_of(parse(SWIM).slides[0])
    steps = forms5.steps_of(lanes or [])
    assert [(s.idx, s.lane, s.col) for s in steps] == [(1, 0, 1), (2, 0, 4), (3, 1, 2), (4, 1, 3), (5, 2, 5)]
    assert steps[1].classes == ["focal"]
    assert steps[1].paras[0].plain == "Pay invoice"  # the prefix and the class are not text


def test_swimlane_same_lane_same_column_moves_on():
    md = "# T\n@swimlane\n## A\n- 2: x\n- 2: y\n## B\n- z\n"
    steps = forms5.steps_of(forms5.lanes_of(parse(md).slides[0]) or [])
    assert [s.col for s in steps if s.lane == 0] == [2, 3]


def test_sequence_participants_in_order_and_reply():
    names, msgs = forms5.sequence_of(parse(SEQ).slides[0]) or ([], [])
    assert names == ["Client", "API", "DB"]
    assert [(m.src, m.dst, m.reply, m.is_self) for m in msgs] == [
        ("Client", "API", False, False),
        ("API", "DB", False, False),
        ("DB", "API", True, False),
        ("API", "API", False, True),
        ("API", "Client", True, False),
    ]
    assert msgs[-1].classes == ["focal"] and msgs[-1].label == "201"


def test_sequence_declared_participants_set_the_order():
    md = "# T\n@sequence\n- DB, API, Client\n- Client > API: go\n"
    names, _ = forms5.sequence_of(parse(md).slides[0]) or ([], [])
    assert names == ["DB", "API", "Client"]


def test_message_without_label_and_colon_in_label():
    md = "# T\n@sequence\n- A > B\n- B >> A: ok: 200\n"
    _, msgs = forms5.sequence_of(parse(md).slides[0]) or ([], [])
    assert msgs[0].label == "" and msgs[1].label == "ok: 200" and msgs[1].reply


# --------------------------------------------------------------------------- degrade, never raise


@pytest.mark.parametrize(
    "md, rule",
    [
        ("# T\n@swimlane\n## Only\n- a\n- b\n", "swimlane-skipped"),  # one lane
        ("# T\n@swimlane\n", "swimlane-skipped"),  # no lanes
        ("# T\n@swimlane\n## A\n## B\n", "swimlane-skipped"),  # lanes without steps
        ("# T\n@swimlane\n## A\n- 40: far\n## B\n- b\n", "swimlane-skipped"),  # column past the limit
        ("# T\n@swimlane\ntext\n## A\n- a\n## B\n- b\n", "swimlane-skipped"),  # a stray block
        ("# T\n@sequence\n- just text\n- more\n", "sequence-skipped"),  # no message
        ("# T\n@sequence\n- A > A: loop\n", "sequence-skipped"),  # one participant
        ("# T\n@sequence\n", "sequence-skipped"),
        ("# T\n@sequence\nplain paragraph\n", "sequence-skipped"),
    ],
)
def test_lacking_input_is_a_diagnostic_with_a_hint_and_a_plain_layout(md, rule):
    deck, placed, diags = _diags(md)
    got = [d for d in deck.diagnostics if d.rule == rule]
    assert len(got) == 1 and got[0].hint and "ordinary blocks" in got[0].hint
    assert placed[0]  # laid out as plain blocks


def test_garbage_lines_never_raise():
    md = (
        "# T\n@sequence\n- >\n- > >> :\n- A >\n- > B\n- : :\n- A > B > C: x\n- ::\n- A > B: {.focal}\n"
        "- {.x}\n- 日本語 > 英語: テスト\n"
    )
    _diags(md)
    _diags("# T\n@swimlane\n## A\n- :\n- 3:\n- {.focal}\n- \n## B\n- 0: zero\n- 99\n")


def test_thirty_messages_warn_instead_of_raising(tmp_path):
    rows = "".join(f"- {'AB'[i % 2]} > {'BA'[i % 2]}: message number {i}\n" for i in range(30))
    deck = build(HEAD + "# T\n@sequence\n" + rows, tmp_path / "d.pptx")
    assert any(d.rule == "overflow" for d in deck.diagnostics)
    _, _, diags = _diags("# T\n@sequence\n" + rows)
    assert any(d.rule == "diagram-budget" and "30 arrows" in d.message for d in diags)


def test_many_steps_and_lanes_never_raise():
    lanes = "".join(f"## L{i}\n" + "".join(f"- {j * 8 + i + 1}: s\n" for j in range(1)) for i in range(8))
    _diags("# T\n@swimlane\n" + lanes)
    _diags("# T\n@swimlane dir=v\n" + lanes)


def test_bad_swimlane_dir_is_a_warning():
    deck = parse(HEAD + SWIM.replace("@swimlane", "@swimlane dir=x"))
    assert any(d.rule == "bad-attr" for d in deck.diagnostics)


# --------------------------------------------------------------------------- render


def test_swimlane_shape_names_and_connector_kinds(tmp_path):
    slide = _shapes(tmp_path, SWIM)
    names = {sh.name for sh in slide.shapes}
    assert {"Lane 1", "Lane 3", "Lane 1 head", "Lane 3 head", "Step 1", "Step 5"} <= names
    cx = _cxn(slide)
    # steps are joined in column order: 1 (col 1) -> 3 (col 2) -> 4 (col 3) -> 2 (col 4) -> 5 (col 5)
    assert set(cx) == {"Step 1 next", "Step 3 next", "Step 4 next", "Step 2 next"}
    assert cx["Step 1 next"][0] == "bentConnector3"  # Customer -> Sales: an elbow
    assert cx["Step 3 next"][0] != "bentConnector3"  # same lane: straight
    assert cx["Step 2 next"][0] == "bentConnector3"
    text = {sh.name: sh.text_frame.text for sh in slide.shapes if sh.has_text_frame}
    assert (
        text["Lane 2 head"] == "Sales"
        and text["Step 2"] == "Pay invoice"
        and text["Step 3"] == "Check credit"
    )


def test_swimlane_connectors_are_glued_to_their_steps(tmp_path):
    from pptx.oxml.ns import qn

    slide = _shapes(tmp_path, SWIM)
    ids = {sh.name: sh.shape_id for sh in slide.shapes}
    for el in slide.shapes._spTree.iter(qn("p:cxnSp")):
        name = el.find(qn("p:nvCxnSpPr")).find(qn("p:cNvPr")).get("name")
        c = el.find(qn("p:nvCxnSpPr")).find(qn("p:cNvCxnSpPr"))
        assert c.find(qn("a:stCxn")) is not None, name
        a = int(name.split()[1])
        assert int(c.find(qn("a:stCxn")).get("id")) == ids[f"Step {a}"]


def test_swimlane_focal_step_uses_the_accent_line(tmp_path):
    from pptx.oxml.ns import qn

    slide = _shapes(tmp_path, SWIM)
    sp = next(sh for sh in slide.shapes if sh.name == "Step 2")._element
    assert (
        sp.find(qn("p:spPr")).find(qn("a:ln")).find(qn("a:solidFill")).find(qn("a:srgbClr")).get("val")
        == "BF4520"
    )


def test_swimlane_steps_stay_inside_their_lane_and_do_not_overlap(tmp_path):
    slide = _shapes(tmp_path, SWIM)
    by = {sh.name: sh for sh in slide.shapes}
    for i in (1, 2, 3, 4, 5):
        st = by[f"Step {i}"]
        assert st.left >= by["Lane 1 head"].left + by["Lane 1 head"].width
    steps = [by[f"Step {i}"] for i in (1, 2, 3, 4, 5)]
    for a in steps:
        for b in steps:
            if a is not b:
                assert (
                    a.left + a.width <= b.left
                    or b.left + b.width <= a.left
                    or a.top + a.height <= b.top
                    or b.top + b.height <= a.top
                )


def test_swimlane_vertical_makes_lanes_columns(tmp_path):
    slide = _shapes(tmp_path, SWIM.replace("@swimlane", "@swimlane dir=v"))
    by = {sh.name: sh for sh in slide.shapes}
    assert by["Lane 1"].left < by["Lane 2"].left and by["Lane 1"].top == by["Lane 2"].top
    assert by["Lane 1 head"].top == by["Lane 1"].top  # the header band sits on top
    assert by["Step 3"].top > by["Step 1"].top  # column 2 is below column 1
    assert _cxn(slide)["Step 1 next"][0] == "bentConnector3"


def test_sequence_shape_names_dash_and_loop(tmp_path):
    slide = _shapes(tmp_path, SEQ)
    names = {sh.name for sh in slide.shapes}
    assert {
        "Seq Client head",
        "Seq API head",
        "Seq DB head",
        "Seq 1 label",
        "Seq 3 label reply",
        "Seq 4 label self",
    } <= names
    cx = _cxn(slide)
    assert (
        cx["Seq 1 msg"][1] is None
        and cx["Seq 3 msg reply"][1] == "dash"
        and cx["Seq 5 msg reply"][1] == "dash"
    )
    assert cx["Seq API lifeline"][1] == "dash" and cx["Seq Client lifeline"][0] != "bentConnector3"
    assert {"Seq 4 msg self", "Seq 4 msg self 2", "Seq 4 msg self 3"} <= set(cx)
    assert all(v[0] != "bentConnector3" for v in cx.values())  # orthogonal and straight: no diagonals either
    text = {sh.name: sh.text_frame.text for sh in slide.shapes if sh.has_text_frame}
    assert text["Seq 1 label"] == "POST /order" and text["Seq Client head"] == "Client"


def test_sequence_messages_run_top_to_bottom_between_lifelines(tmp_path):
    slide = _shapes(tmp_path, SEQ)
    by = {sh.name: sh for sh in slide.shapes}
    ys = [by[n].top for n in ("Seq 1 msg", "Seq 2 msg", "Seq 3 msg reply", "Seq 5 msg reply")]
    assert ys == sorted(ys) and len(set(ys)) == 4
    m1, life = by["Seq 1 msg"], by["Seq Client lifeline"]
    assert abs(m1.left - life.left) < 1000  # the arrow starts on the Client lifeline
    assert by["Seq 1 label"].top + by["Seq 1 label"].height <= m1.top  # the label sits above the arrow


def test_role_class_colours_a_message(tmp_path):
    from pptx.oxml.ns import qn

    slide = _shapes(tmp_path, SEQ)
    el = next(sh for sh in slide.shapes if sh.name == "Seq 5 msg reply")._element
    assert (
        el.find(qn("p:spPr")).find(qn("a:ln")).find(qn("a:solidFill")).find(qn("a:srgbClr")).get("val")
        == "BF4520"
    )


def test_tokens_change_the_look(tmp_path):
    from pptx.oxml.ns import qn

    hdr = HEAD + "style: swimlane.step.fill=#FFEEAA swimlane.head.w=2in swimlane.line=#112233\n\n"
    slide = _shapes(tmp_path, SWIM, header=hdr)
    by = {sh.name: sh for sh in slide.shapes}
    assert abs(by["Lane 1 head"].width - 2 * 914400) < 10
    fill = by["Step 1"]._element.find(qn("p:spPr")).find(qn("a:solidFill")).find(qn("a:srgbClr")).get("val")
    assert fill == "FFEEAA"
    hdr2 = HEAD + "style: sequence.lifeline=#445566 sequence.head.fill=#DDEEFF\n\n"
    slide2 = _shapes(tmp_path, SEQ, header=hdr2)
    head = next(sh for sh in slide2.shapes if sh.name == "Seq API head")._element
    assert head.find(qn("p:spPr")).find(qn("a:solidFill")).find(qn("a:srgbClr")).get("val") == "DDEEFF"


def test_token_without_its_form_warns():
    deck = parse(HEAD + "style: swimlane.line=#112233\n\n# T\n- a\n")
    theme, _ = deck_theme(deck, ".")
    diags = lint_deck(deck, [layout_slide(s, deck, theme, i) for i, s in enumerate(deck.slides)], theme)
    assert any(d.rule == "attr-ignored" and "swimlane" in d.hint for d in diags)


def test_example_28_builds_without_warnings():
    text = (ROOT / "examples" / "28-swimlane-sequence.md").read_text(encoding="utf-8")
    deck, _placed, diags = _diags(text, header="")
    bad = [d.message for d in [*deck.diagnostics, *diags] if d.level == "warning"]
    assert not bad, bad


# --------------------------------------------------------------------------- budget / design / honour


def test_budget_counts_nodes_arrows_and_labels():
    rows = "".join(f"- {'AB'[i % 2]} > {'BA'[i % 2]}: x\n" for i in range(13))
    _, _, diags = _diags("# T\n@sequence\n" + rows)
    got = [d for d in diags if d.rule == "diagram-budget"]
    assert len(got) == 1 and "13 arrows" in got[0].message
    long = "# T\n@sequence\n- A > B: a label that is far too long\n"
    got = [d for d in _diags(long)[2] if d.rule == "diagram-budget"]
    assert len(got) == 1 and "label" in got[0].message
    cols = "".join(f"- {i + 1}: s\n" for i in range(10))
    got = [
        d for d in _diags("# T\n@swimlane\n## A\n" + cols + "## B\n- z\n")[2] if d.rule == "diagram-budget"
    ]
    assert got and "11 nodes" in got[0].message


def test_within_budget_is_quiet():
    assert not [d for d in _diags(SWIM)[2] if d.rule == "diagram-budget"]
    assert not [d for d in _diags(SEQ)[2] if d.rule == "diagram-budget"]


@pytest.mark.parametrize("md", [SWIM, SEQ])
def test_design_slide_counts_the_form_and_the_focal_emphasis(md):
    from slidemark.design import stated_groups

    got = stated_groups(parse(HEAD + md).slides[0])
    assert got["form"] and got["emphasis"]


def test_honour_accepts_lane_fill_and_color():
    md = SWIM.replace("## Sales", "## Sales {fill=#EEF4FF color=primary}")
    _, _, diags = _diags(md)
    assert not [d for d in diags if d.rule == "attr-ignored"]


def test_honour_reports_a_geometry_key_on_a_lane():
    md = SWIM.replace("## Sales", "## Sales {x=1in}")
    _, _, diags = _diags(md)
    assert [d for d in diags if d.rule == "attr-ignored"]


def test_at_keys_check():
    deck = parse(HEAD + SEQ.replace("@sequence", "@sequence dir=v"))
    assert any(d.rule == "attr-ignored" for d in deck.diagnostics)


# --------------------------------------------------------------------------- import


def test_round_trip_rebuilds_the_same_forms(tmp_path):
    src = tmp_path / "a.pptx"
    build(HEAD + SWIM + "\n" + SEQ.replace("# Checkout", "# Checkout\n"), src)
    text, _ = import_pptx(src, tmp_path)
    d = parse(text)
    assert [s.classes[0] for s in d.slides] == ["swimlane", "sequence"]
    lanes = forms5.lanes_of(d.slides[0]) or []
    steps = forms5.steps_of(lanes)
    assert [(s.lane, s.col, s.paras[0].plain) for s in steps] == [
        (0, 1, "Place order"),
        (0, 4, "Pay invoice"),
        (1, 2, "Check credit"),
        (1, 3, "Confirm order"),
        (2, 5, "Book payment"),
    ]
    names, msgs = forms5.sequence_of(d.slides[1]) or ([], [])
    assert names == ["Client", "API", "DB"]
    assert [(m.src, m.dst, m.label, m.reply) for m in msgs] == [
        ("Client", "API", "POST /order", False),
        ("API", "DB", "insert", False),
        ("DB", "API", "ok", True),
        ("API", "API", "retry", False),
        ("API", "Client", "201", True),
    ]


def test_round_trip_vertical_swimlane(tmp_path):
    src = tmp_path / "a.pptx"
    build(HEAD + SWIM.replace("@swimlane", "@swimlane dir=v"), src)
    text, _ = import_pptx(src, tmp_path)
    assert "@swimlane dir=v" in text
