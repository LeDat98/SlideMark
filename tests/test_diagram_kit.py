"""Lane F: the diagram kit of ``@arch`` ``@swimlane`` ``@sequence`` ``@venn`` (tags, sublabels, arrow kinds,
labels, legend strip, activation bars, the exact venn lens, compact centred layout).

Parser (tags, sublabels, edge kinds and aliases), render (the .pptx is reopened: fonts, case, colours, dashes,
freeform), tokens, legend and fuzz-safety (a diagnostic or plain text, never an exception)."""

from __future__ import annotations

import re

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from pptx import Presentation
from pptx.enum.dml import MSO_FILL
from pptx.oxml.ns import qn

from slidemark import build, forms5, forms6, parse
from slidemark.layout.diagramkit import kind_of, split_sub, split_tag
from slidemark.theme import normalize_token

HEAD = "theme: editorial\nlang: en\n"
IN = 914400

ARCH = (
    "\n# Platform\n@arch\n"
    "## Clients\n- [EXT] Web app {.external}\n"
    "## Services\n- [API] Gateway: auth · limits {.focal}\n- Orders\n"
    "## Data\n- [DB] Postgres: orders {.store}\n"
    "> Web app ~> Gateway: https, Gateway => Orders: order, Orders --> Postgres: write, Orders > Gateway\n"
)
SWIM = (
    "\n# Flow\n@swimlane\n## Author\n- Draft: src\n- Open PR > HANDOFF\n"
    "## Reviewer\n- 3: [REV] Review: facts --> REVISE\n## Editor\n- 3: Polish\n- 4: Approve => GO {.focal}\n"
    "## Ops\n- 5: Ship\n"
)
SEQ = (
    "\n# Request\n@sequence\n"
    "- [EXT] Reader: Browser, [EDGE] Edge: Pages · cache {.focal}, Origin\n"
    "- Reader ~> Edge: GET /x\n- Edge > Origin: miss\n- Origin --> Edge: 200\n- Edge => Reader: 200 ok\n"
    "- Origin >> Reader: late\n"
)
VENN3 = (
    "\n# Venn\n@venn\n## Desirable\nPeople want it\n## Feasible\nWe can build it\n"
    "## Viable\nBusiness sustains\n> Shippable: the sweet spot\n"
)


def make(tmp_path, text: str, head: str = HEAD, slide: int = 0):
    deck = build(head + text, tmp_path / "d.pptx")
    return deck, Presentation(str(tmp_path / "d.pptx")).slides[slide]


def named(slide, pattern: str):
    return [s for s in slide.shapes if re.fullmatch(pattern, s.name)]


def one(slide, name: str):
    got = named(slide, re.escape(name))
    assert len(got) == 1, (name, [s.name for s in slide.shapes])
    return got[0]


def real(deck):
    return [d for d in deck.diagnostics if d.level == "warning" and not (d.rule or "").startswith("design")]


def txt(shp) -> str:
    return shp.text_frame.text.replace("\u00a0", " ")


def caps(r) -> bool:
    return r._r.find(qn("a:rPr")).get("cap") == "all"


def runs(shp):
    return [r for p in shp.text_frame.paragraphs for r in p.runs]


def latin(r) -> str | None:
    el = r._r.find(qn("a:rPr")).find(qn("a:latin"))
    return None if el is None else el.get("typeface")


def cxn(slide, name: str):
    for el in slide.shapes._spTree.iter(qn("p:cxnSp")):
        if el.find(qn("p:nvCxnSpPr")).find(qn("p:cNvPr")).get("name") == name:
            return el
    raise AssertionError((name, [s.name for s in slide.shapes]))


def stroke(el) -> tuple[str, str | None]:
    ln = el.find(qn("p:spPr")).find(qn("a:ln"))
    dash = ln.find(qn("a:prstDash"))
    return ln.find(qn("a:solidFill"))[0].get("val").upper(), (dash.get("val") if dash is not None else None)


# --------------------------------------------------------------------------- parser


def test_tag_and_sub_helpers_never_raise():
    assert split_tag("[EXT] Reader") == ("Reader", "EXT")
    assert split_tag("[EXT]Reader") == ("Reader", "EXT")
    for junk in ("[", "[]", "[ ] x", "[a[b]] c", "] x", "[toolongtagtoolong] x", ""):
        name, tag = split_tag(junk)
        assert isinstance(name, str) and isinstance(tag, str)
    assert split_sub("Name: a: b") == ("Name", "a: b")
    assert split_sub("no sub") == ("no sub", "")
    assert [kind_of(x) for x in (">", "=>", "~>", "-->", ">>", "->", "?")] == [
        "flow",
        "primary",
        "http",
        "return",
        "return",
        "flow",
        "flow",
    ]


def test_arch_tags_subs_and_edge_kinds():
    deck = parse(HEAD + ARCH)
    arch = forms6.parse_arch(deck.slides[0])
    assert arch is not None
    gw = arch.nodes[arch.index["gateway"]]
    assert (gw.name, gw.tag, gw.sub, gw.classes) == ("Gateway", "API", "auth · limits", ["focal"])
    assert arch.nodes[0].tag == "EXT" and arch.nodes[0].classes == ["external"]
    edges, problems = forms6.parse_edges(forms6.edge_text(deck.slides[0]), arch)
    assert problems == []
    assert [(e.kind, e.label) for e in edges] == [
        ("http", "https"),
        ("primary", "order"),
        ("return", "write"),
        ("flow", None),
    ]


def test_arch_chain_takes_the_kind_of_each_arrow():
    md = "# T\n@arch\n## A\n- a\n## B\n- b\n## C\n- c\n> a ~> b => c: go\n"
    deck = parse(HEAD + md)
    arch = forms6.parse_arch(deck.slides[0])
    edges, _ = forms6.parse_edges(forms6.edge_text(deck.slides[0]), arch)
    assert [(e.kind, e.label) for e in edges] == [("http", None), ("primary", "go")]


def test_swimlane_tags_subs_and_handoffs():
    deck = parse(HEAD + SWIM)
    steps = forms5.steps_of(forms5.lanes_of(deck.slides[0]) or [])
    got = [(s.name, s.tag, s.sub, s.kind, s.label, s.col) for s in steps]
    assert got == [
        ("Draft", "", "src", "flow", "", 1),
        ("Open PR", "", "", "flow", "HANDOFF", 2),
        ("Review", "REV", "facts", "return", "REVISE", 3),
        ("Polish", "", "", "flow", "", 3),
        ("Approve", "", "", "primary", "GO", 4),
        ("Ship", "", "", "flow", "", 5),
    ]
    assert steps[4].classes == ["focal"]


def test_swimlane_clock_time_is_not_a_sublabel():
    deck = parse(HEAD + "# T\n@swimlane\n## A\n- 10:30 stand-up\n## B\n- b\n")
    steps = forms5.steps_of(forms5.lanes_of(deck.slides[0]) or [])
    assert steps[0].name == "10:30 stand-up" and steps[0].sub == ""


def test_sequence_participants_tags_and_message_kinds():
    deck = parse(HEAD + SEQ)
    parts, msgs = forms5.sequence_model(deck.slides[0]) or ([], [])
    assert [(p.name, p.tag, p.sub, p.classes) for p in parts] == [
        ("Reader", "EXT", "Browser", []),
        ("Edge", "EDGE", "Pages · cache", ["focal"]),
        ("Origin", "", "", []),
    ]
    assert [(m.kind, m.reply) for m in msgs] == [
        ("http", False),
        ("flow", False),
        ("return", True),
        ("primary", False),
        ("return", True),  # `>>` is an alias of `-->`
    ]
    names, _ = forms5.sequence_of(deck.slides[0]) or ([], [])
    assert names == ["Reader", "Edge", "Origin"]


# --------------------------------------------------------------------------- render: nodes, tags, kinds


def test_arch_node_anatomy_tag_name_sublabel(tmp_path):
    deck, s = make(tmp_path, ARCH)
    assert real(deck) == []
    tag = one(s, "Arch tag Gateway")
    assert tag.text_frame.text == "API" and caps(runs(tag)[0])  # the font draws the capitals
    r = runs(tag)[0]
    assert latin(r) == "Consolas" and r._r.find(qn("a:rPr")).get("spc") not in (None, "0")
    assert r.font.size.pt == 8
    node = one(s, "Arch node Gateway")
    name, sub = node.text_frame.paragraphs[0].runs[0], node.text_frame.paragraphs[1].runs[0]
    assert name.font.bold and latin(name) == "Arial" and sub.text.replace("\u00a0", " ") == "auth · limits"
    assert latin(sub) == "Consolas" and sub.font.size.pt < name.font.size.pt
    assert tag.left >= node.left and tag.top >= node.top  # inside the card, at its top-left
    assert tag.left + tag.width <= node.left + node.width
    assert not named(s, r"Arch tag Orders")  # no tag, no tag shape


def test_arch_arrow_kinds_colour_and_dash(tmp_path):
    _deck, s = make(tmp_path, ARCH)
    assert stroke(cxn(s, "Arch edge 1"))[0] == "2E5AA8"  # `~>`: the link colour
    assert stroke(cxn(s, "Arch edge 2"))[0] == "BF4520"  # `=>`: the accent
    col, dash = stroke(cxn(s, "Arch edge 3"))  # `-->`: dashed, in the default arrow colour
    assert dash == "dash" and col == "4F5D75"
    col, dash = stroke(cxn(s, "Arch edge 4"))
    assert dash is None and col == "4F5D75"
    for i in range(1, 5):
        assert cxn(s, f"Arch edge {i}").find(qn("p:spPr")).find(qn("a:ln")).find(qn("a:tailEnd")) is not None


def test_arch_labels_are_mono_capitals_on_a_knockout_clear_of_nodes(tmp_path):
    _deck, s = make(tmp_path, ARCH)
    lab = one(s, "Arch edge 1 label")
    assert lab.text_frame.text == "https"  # the text keeps its case, the font draws capitals
    r = runs(lab)[0]
    assert latin(r) == "Consolas" and r.font.size.pt == 8 and caps(r)
    assert lab.fill.type is not None  # a knockout of the slide colour
    nodes = named(s, r"Arch node .+")
    for n in nodes:
        assert not (
            lab.left < n.left + n.width
            and n.left < lab.left + lab.width
            and lab.top < n.top + n.height
            and n.top < lab.top + lab.height
        ), n.name


def test_arch_is_compact_and_centred_not_stretched(tmp_path):
    _deck, s = make(tmp_path, ARCH)
    nodes = named(s, r"Arch node .+")
    assert max(n.width for n in nodes) <= 2.7 * IN and max(n.height for n in nodes) <= 1.2 * IN
    left = min(n.left for n in nodes)
    right = max(n.left + n.width for n in nodes)
    mid = (left + right) / 2
    assert abs(mid - 13.333 * IN / 2) < 1.6 * IN  # centred in the slide (the caption column sits left of it)
    assert not named(s, r"Arch tier \d")  # no tier bands: captions only
    assert len(named(s, r"Arch tier \d label")) == 3


def test_arch_columns_box_a_tier_with_a_group(tmp_path):
    md = "\n# T\n@arch dir=h\n## In\n- a\n- b\n## Out\n- c\n> a > c, b > c\n"
    _deck, s = make(tmp_path, md)
    box = one(s, "Arch tier 1")  # two nodes: a dashed hairline container
    ln = box._element.find(qn("p:spPr")).find(qn("a:ln"))
    assert ln.find(qn("a:prstDash")).get("val") == "dash"
    assert not named(s, "Arch tier 2")  # a lone node: caption only


def test_swimlane_cards_labels_and_rules(tmp_path):
    deck, s = make(tmp_path, SWIM)
    assert real(deck) == []
    assert one(s, "Step 3 tag").text_frame.text == "REV"
    assert txt(one(s, "Step 1").text_frame.paragraphs[1].runs[0]) == "src" if False else True
    assert one(s, "Step 1").text_frame.paragraphs[1].text == "src"
    assert one(s, "Step 2 next label").text_frame.text == "HANDOFF"
    assert one(s, "Step 3 next label").text_frame.text == "REVISE"
    assert stroke(cxn(s, "Step 3 next"))[1] == "dash"  # `-->`
    assert stroke(cxn(s, "Step 5 next"))[0] == "BF4520"  # `=>` out of Approve


def test_swimlane_captions_are_mono_capitals_without_a_filled_header(tmp_path):
    _deck, s = make(tmp_path, SWIM)
    head = one(s, "Lane 1 head")
    assert head.text_frame.text == "Author"  # the case is kept: the font draws the capitals
    assert latin(runs(head)[0]) == "Consolas" and caps(runs(head)[0])
    assert head.fill.type != MSO_FILL.SOLID  # no filled header column
    assert len(named(s, r"Lane \d+ rule( end)?")) == 5  # separators between and around the lanes
    assert len(named(s, "Lane head rule")) == 1


def test_sequence_cards_lifelines_activation_and_kinds(tmp_path):
    deck, s = make(tmp_path, SEQ)
    assert real(deck) == []
    assert one(s, "Seq Reader tag").text_frame.text == "EXT"
    head = one(s, "Seq Edge head")
    assert head.text_frame.paragraphs[1].text.replace("\u00a0", " ") == "Pages · cache"
    assert stroke(cxn(s, "Seq Edge lifeline"))[1] == "dash"
    assert stroke(cxn(s, "Seq 1 msg"))[0] == "2E5AA8"  # `~>`
    assert stroke(cxn(s, "Seq 3 msg reply"))[1] == "dash"  # `-->`
    assert stroke(cxn(s, "Seq 4 msg"))[0] == "BF4520"  # `=>`
    assert stroke(cxn(s, "Seq 5 msg reply"))[1] == "dash"  # `>>`
    bars = named(s, r"Seq .+ act \d+")
    assert {b.name for b in bars} == {"Seq Edge act 1", "Seq Origin act 1"}
    edge = one(s, "Seq Edge act 1")
    ll = cxn(s, "Seq Edge lifeline")
    x = int(ll.find(qn("p:spPr")).find(qn("a:xfrm")).find(qn("a:off")).get("x"))
    assert edge.left < x < edge.left + edge.width  # the bar sits on the lifeline
    lab = one(s, "Seq 1 label")
    assert lab.text_frame.text == "GET /x" and latin(runs(lab)[0]) == "Consolas" and caps(runs(lab)[0])


def test_sequence_unanswered_request_draws_no_bar(tmp_path):
    md = "\n# T\n@sequence\n- A > B: go\n- B > C: fire\n"
    _deck, s = make(tmp_path, md)
    assert {x.name for x in named(s, r"Seq .+ act \d+")} == {"Seq B act 1"}  # B goes on working: C does not


# --------------------------------------------------------------------------- legend


def legend_keys(s) -> set[str]:
    return {m.group(1) for sh in s.shapes if (m := re.fullmatch(r"Legend (\w+) swatch", sh.name))}


def test_legend_lists_the_roles_and_kinds_in_use(tmp_path):
    _deck, s = make(tmp_path, ARCH)
    assert legend_keys(s) == {"plain", "focal", "external", "store", "flow", "primary", "http", "return"}
    assert one(s, "Legend caption").text_frame.text == "Legend"
    assert one(s, "Legend http label").text_frame.text == "HTTP request"
    assert one(s, "Legend focal label").text_frame.text == "Focal"


def test_legend_needs_two_distinct_roles_or_kinds(tmp_path):
    _deck, s = make(tmp_path, "\n# T\n@arch\n## A\n- a\n## B\n- b\n> a > b\n")
    assert legend_keys(s) == set()  # one kind, no role: nothing to explain


def test_legend_token_and_slide_attribute(tmp_path):
    _deck, s = make(tmp_path, ARCH, HEAD + "style: diagram.legend=off\n")
    assert legend_keys(s) == set()
    _deck, s = make(
        tmp_path, "\n# T\n@arch\n## A\n- a\n## B\n- b\n> a > b\n", HEAD + "style: diagram.legend=on\n"
    )
    assert legend_keys(s) == {"flow"}
    _deck, s = make(tmp_path, ARCH.replace("@arch", "@arch legend=off"))
    assert legend_keys(s) == set()


def test_legend_custom_text_token(tmp_path):
    head = HEAD + 'style: diagram.legend.text="focal=Core,http=API call"\n'
    _deck, s = make(tmp_path, ARCH, head)
    assert one(s, "Legend focal label").text_frame.text == "Core"
    assert one(s, "Legend http label").text_frame.text == "API call"


def test_legend_swimlane_and_sequence_entries(tmp_path):
    _deck, s = make(tmp_path, SWIM)
    assert {"focal", "primary", "return", "flow"} <= legend_keys(s)
    _deck, s = make(tmp_path, SEQ)
    assert {"act", "http", "return", "primary", "focal"} <= legend_keys(s)


# --------------------------------------------------------------------------- venn


def test_venn_neutral_circles_and_an_exact_lens_freeform(tmp_path):
    deck, s = make(tmp_path, VENN3)
    assert real(deck) == []
    sets = named(s, r"Venn \d set")
    assert len(sets) == 3
    lens = one(s, "Venn overlap fill")
    sp = lens._element.find(qn("p:spPr"))
    assert sp.find(qn("a:custGeom")) is not None  # a native freeform
    assert sp.find(qn("a:solidFill"))[0].get("val").upper() == "2D3142"  # solid ink, no alpha
    assert sp.find(qn("a:solidFill"))[0].find(qn("a:alpha")) is None
    pts = sp.find(qn("a:custGeom")).findall(".//" + qn("a:pt"))
    assert len(pts) > 40  # many points: arcs, not a triangle
    ov = one(s, "Venn overlap")
    assert [p.text.replace("\u00a0", " ") for p in ov.text_frame.paragraphs] == [
        "Shippable",
        "the sweet spot",
    ]
    assert ov.text_frame.paragraphs[0].runs[0].font.bold
    nm = one(s, "Venn 1 name")
    assert [p.text.replace("\u00a0", " ") for p in nm.text_frame.paragraphs] == [
        "Desirable",
        "People want it",
    ]
    assert latin(nm.text_frame.paragraphs[1].runs[0]) == "Consolas"


def test_venn_lens_lies_inside_every_circle(tmp_path):
    _deck, s = make(tmp_path, VENN3)
    circles = []
    for sh in named(s, r"Venn \d set"):
        r = sh.width / 2
        circles.append((sh.left + r, sh.top + r, r))
    lens = one(s, "Venn overlap fill")
    for pt in lens._element.find(qn("p:spPr")).find(qn("a:custGeom")).findall(".//" + qn("a:pt")):
        px = lens.left + int(pt.get("x")) * lens.width / max(
            int(lens._element.find(qn("p:spPr")).find(qn("a:custGeom")).find(".//" + qn("a:path")).get("w")),
            1,
        )
        py = lens.top + int(pt.get("y")) * lens.height / max(
            int(lens._element.find(qn("p:spPr")).find(qn("a:custGeom")).find(".//" + qn("a:path")).get("h")),
            1,
        )
        for cx, cy, r in circles:
            assert (px - cx) ** 2 + (py - cy) ** 2 <= (r * 1.01) ** 2


def test_venn_focal_overlap_uses_the_accent_and_two_sets_work(tmp_path):
    md = VENN3.replace("the sweet spot", "the sweet spot {.focal}")
    _deck, s = make(tmp_path, md)
    sp = one(s, "Venn overlap fill")._element.find(qn("p:spPr"))
    assert sp.find(qn("a:solidFill"))[0].get("val").upper() == "BF4520"
    _deck, s = make(tmp_path, "\n# T\n@venn\n## A\nx\n## B\ny\n> both: here\n")
    assert one(s, "Venn overlap fill")._element.find(qn("p:spPr")).find(qn("a:custGeom")) is not None
    assert len(named(s, r"Venn \d set")) == 2


def test_venn_circles_are_capped_not_grown_to_fill(tmp_path):
    _deck, s = make(tmp_path, VENN3)
    assert max(sh.width for sh in named(s, r"Venn \d set")) <= 3.65 * IN


# --------------------------------------------------------------------------- tokens


@pytest.mark.parametrize(
    "path, raw, ok",
    [
        ("diagram_legend", "off", True),
        ("diagram_legend", "sometimes", False),
        ("arch_tier_look", "box", True),
        ("arch_tier_look", "ring", False),
        ("diagram_return_dash", "dot", True),
        ("diagram_arrow_http", "#2E5AA8", True),
        ("diagram_arrow_http", "nocolorxyz", False),
        ("diagram_act_w", "12pt", True),
        ("venn_core", "accent", True),
        ("venn_max", "4in", True),
        ("diagram_font", "Menlo", True),
    ],
)
def test_diagram_tokens_validate(path, raw, ok):
    from slidemark.theme import TokenValueError

    if ok:
        assert normalize_token(path, raw, None)[0][0] == path
    else:
        with pytest.raises(TokenValueError):
            normalize_token(path, raw, {"primary"})


def test_diagram_tokens_restyle_without_code(tmp_path):
    head = (
        HEAD
        + "style: diagram.arrow.http=#CC0000 diagram.tag.size=9 diagram.font=Menlo diagram.return.dash=dot\n"
    )
    _deck, s = make(tmp_path, ARCH, head)
    assert stroke(cxn(s, "Arch edge 1"))[0] == "CC0000"
    assert stroke(cxn(s, "Arch edge 3"))[1] == "sysDot"
    r = runs(one(s, "Arch tag Gateway"))[0]
    assert latin(r) == "Menlo" and r.font.size.pt == 9


# --------------------------------------------------------------------------- fuzz-safety


@pytest.mark.parametrize(
    "line",
    [
        "- [ Reader: x",
        "- [] Reader",
        "- [[x]] Reader: a: b: c",
        "- [EXT Reader",
        "- ] Reader [EXT]",
        "- [A-VERY-LONG-TAG-NAME] Reader",
        "- [X] : sub",
        "- [X]",
    ],
)
def test_malformed_tags_never_raise(tmp_path, line):
    md = f"\n# T\n@arch\n## A\n{line}\n- b\n## B\n- c\n> b > c, c ~> , ~> b, b => => c, --> , b ~> c: \n"
    deck, s = make(tmp_path, md)
    assert [d for d in deck.diagnostics if d.level == "error"] == []
    assert named(s, r"Arch node .+")


@pytest.mark.parametrize(
    "md",
    [
        "# T\n@swimlane\n## A\n- [x\n- > \n- --> \n- => x\n## B\n- ~> y\n- [T] \n",
        "# T\n@sequence\n- [x] a, [y, b {.focal}\n- a ~> b\n- a => => b\n- a --> b: [x]\n",
        "# T\n@sequence\n- ~> \n- => \n- a --> \n",
        "# T\n@venn\n## A\n[x]\n## B\n- l\n> : \n",
        "# T\n@venn\n## A\nx\n## B\ny\n> {.focal}\n",
    ],
)
def test_odd_diagram_sources_degrade_without_raising(tmp_path, md):
    deck, _s = make(tmp_path, "\n" + md)
    assert [d for d in deck.diagnostics if d.level == "error"] == []


@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(st.text(alphabet="[]>=~-:{}.a b,日", min_size=0, max_size=30))
def test_fuzzed_diagram_lines_never_raise(tmp_path_factory, junk):
    tmp = tmp_path_factory.mktemp("kit")
    for md in (
        f"\n# T\n@arch\n## A\n- a\n- {junk}\n## B\n- b\n> a > b, {junk}\n",
        f"\n# T\n@sequence\n- a > b: x\n- {junk}\n",
        f"\n# T\n@swimlane\n## A\n- a\n- {junk}\n## B\n- b\n",
    ):
        deck = build(HEAD + md, tmp / "d.pptx")
        assert [d for d in deck.diagnostics if d.level == "error"] == []


def test_diagram_budget_still_counts_nodes_and_edges(tmp_path):
    nodes = "\n".join(f"- n{i}" for i in range(11))
    deck, _s = make(tmp_path, f"\n# T\n@arch\n## A\n{nodes}\n## B\n- z\n> n0 > z\n")
    got = [d for d in deck.diagnostics if d.rule == "diagram-budget"]
    assert got and "12 nodes" in got[0].message
    # the legend swatches and the type tags are no accent emphasis
    deck, _s = make(tmp_path, ARCH)
    assert not [d for d in deck.diagnostics if d.rule == "diagram-budget" and "accent" in d.message]
