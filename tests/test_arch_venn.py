"""Wave 2026-11-08 lane D: ``@arch`` (layered architecture) and ``@venn`` (2-3 overlapping circles).

Parser (word, keys, the final ``>`` line), render (the .pptx is reopened: shape names, connector kind, role
class fills and dashes, ellipse alpha), tokens, ``diagram-budget``, design facts and fuzz-safety (a warning
with a hint, never an exception)."""

from __future__ import annotations

import re

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from pptx import Presentation
from pptx.oxml.ns import qn

from slidemark import build, forms, parse
from slidemark.design import stated_groups
from slidemark.layout import layout_slide
from slidemark.lint import lint_deck
from slidemark.template import deck_theme
from slidemark.theme import normalize_token

HEAD = "theme: editorial\nlang: en\n"

ARCH = (
    "\n# Platform\n@arch\n"
    "## Clients\n- Web app {.external}\n- Mobile app {.external}\n"
    "## Services\n- API gateway: auth, limits {.focal}\n- Orders\n- Billing\n"
    "## Data\n- Postgres: orders {.store}\n- Queue {.optional}\n- Stripe {.external}\n"
    "> Web app > API gateway, Mobile app > API gateway, API gateway > Orders: place order, "
    "Orders > Postgres: write, Orders > Queue, Billing > Stripe: charge {.focal}\n"
)
VENN3 = (
    "\n# Worth building\n@venn\n## Desirable\nPeople want it\n## Feasible\nWe can build it\n"
    "## Viable\nIt pays for itself\n> Worth building {.focal}\n"
)
VENN2 = "\n# Strategy\n@venn\n## Strategy\nWhere to play\n## Execution\nWho does what\n> A plan that ships\n"


def make(tmp_path, text: str, head: str = HEAD):
    deck = build(head + text, tmp_path / "d.pptx")
    return deck, Presentation(str(tmp_path / "d.pptx"))


def named(prs, pattern: str, i: int = 0):
    return [s for s in prs.slides[i].shapes if re.fullmatch(pattern, s.name)]


def one(prs, name: str, i: int = 0):
    got = named(prs, re.escape(name), i)
    assert len(got) == 1, (name, [s.name for s in prs.slides[i].shapes])
    return got[0]


def real(deck):
    """Warnings of the build other than the deck-wide design feedback (``design-*``)."""
    return [d for d in deck.diagnostics if d.level == "warning" and not (d.rule or "").startswith("design")]


def warns(deck, rule: str):
    return [d for d in deck.diagnostics if d.rule == rule]


def sppr(shp):
    return shp._element.find(qn("p:spPr"))


def fill_alpha(shp) -> float | None:
    clr = sppr(shp).find(qn("a:solidFill"))
    if clr is None:
        return None
    a = clr[0].find(qn("a:alpha"))
    return None if a is None else int(a.get("val")) / 100000


def line_of(shp):
    return sppr(shp).find(qn("a:ln"))


def geom(shp) -> str:
    return sppr(shp).find(qn("a:prstGeom")).get("prst")


# --------------------------------------------------------------------------- parser


def test_forms_are_known_and_the_final_line_is_lifted_not_a_conclusion_bar():
    deck = parse(HEAD + ARCH + VENN3)
    assert forms.form_of(deck.slides[0]) == "arch" and forms.form_of(deck.slides[1]) == "venn"
    assert [s.conclusion for s in deck.slides] == [None, None]
    assert deck.slides[0].attrs["form_text"].startswith("Web app > API gateway")
    assert deck.slides[1].attrs["form_text"] == "Worth building {.focal}"
    assert real(deck) == []


def test_arch_without_a_final_line_is_still_a_diagram_and_a_plain_conclusion_stays_elsewhere():
    deck = parse(HEAD + "\n# T\n@arch\n## A\n- x\n## B\n- y\n")
    assert not real(deck)
    plain = parse(HEAD + "\n# T\n## A\n- x\n> a bar\n")  # no form: the bar stays
    assert plain.slides[0].conclusion is not None


def test_dir_h_is_a_choice_and_other_keys_are_ignored_with_a_hint():
    assert not warns(parse(HEAD + ARCH.replace("@arch", "@arch dir=h size=14")), "bad-attr")
    got = warns(parse(HEAD + ARCH.replace("@arch", "@arch side=left")), "attr-ignored")
    assert got and "dir=" in (got[0].hint or "")
    assert warns(parse(HEAD + ARCH.replace("@arch", "@arch dir=x")), "bad-attr")
    got = warns(parse(HEAD + VENN3.replace("@venn", "@venn dir=h")), "attr-ignored")
    assert got and "@venn" in got[0].message


def test_design_counts_both_as_a_form_with_no_value_decision_from_the_lifted_line():
    deck = parse(HEAD + ARCH + VENN3)
    for s in deck.slides:
        got = stated_groups(s)
        assert got["form"] and not got["values"], got


def test_tokens_validate():
    assert normalize_token("arch_tier_fill", "#EEEEEE", None) == [("arch_tier_fill", "#EEEEEE")]
    assert normalize_token("arch_tier_fill", "none", None) == [("arch_tier_fill", "none")]
    assert normalize_token("venn_fill", "primary,#5E7A9B", None) == [("venn_fill", "primary,#5E7A9B")]
    assert normalize_token("venn_text", "OUT", None) == [("venn_text", "out")]
    assert normalize_token("arch_gap", "0.6in", None)[0][0] == "arch_gap"
    with pytest.raises(Exception):  # noqa: B017  (TokenValueError)
        normalize_token("venn_text", "sideways", None)


# --------------------------------------------------------------------------- @arch render


def test_arch_shapes_are_named_and_edges_are_elbow_connectors(tmp_path):
    deck, prs = make(tmp_path, ARCH)
    assert not real(deck), deck.diagnostics
    assert not named(prs, r"Arch tier \d")  # editorial: a tier is a caption, not a full-width band
    assert len(named(prs, r"Arch tier \d label")) == 3
    for name in ("Web app", "Mobile app", "API gateway", "Orders", "Billing", "Postgres", "Queue", "Stripe"):
        assert one(prs, f"Arch node {name}").has_text_frame
    edges = named(prs, r"Arch edge \d+")
    assert len(edges) == 6
    kinds = {geom(e) for e in edges}
    assert "bentConnector3" in kinds and "line" in kinds or kinds <= {"bentConnector3", "straightConnector1"}
    assert any(geom(e) == "bentConnector3" for e in edges)  # an elbow, never a diagonal
    for e in edges:
        ln = line_of(e)
        assert ln.find(qn("a:tailEnd")) is not None  # arrow head
        assert e._element.find(qn("p:nvCxnSpPr")).find(qn("p:cNvCxnSpPr")).find(qn("a:stCxn")) is not None
    # labels: <= 14 characters, as texts over the line
    labels = named(prs, r"Arch edge \d+ label")
    assert sorted(s.text_frame.text for s in labels) == ["charge", "place order", "write"]


def test_arch_no_diagonal_connector_anywhere(tmp_path):
    _deck, prs = make(tmp_path, ARCH)
    for e in named(prs, r"Arch edge \d+"):
        straight = geom(e) != "bentConnector3"
        if straight:  # a straight connector is axis-parallel: zero width or zero height
            assert e.width == 0 or e.height == 0, (e.name, e.width, e.height)


def test_arch_role_classes_fill_and_dash_and_the_one_focal_node_is_accent(tmp_path):
    _deck, prs = make(tmp_path, ARCH)
    focal = one(prs, "Arch node API gateway")
    ln = line_of(focal)
    assert str(ln.find(qn("a:solidFill"))[0].get("val")).upper() == "BF4520"
    assert fill_alpha(focal) is not None and fill_alpha(focal) < 0.2  # an accent tint, not a solid fill
    store = one(prs, "Arch node Postgres")
    assert fill_alpha(store) is not None
    assert line_of(one(prs, "Arch node Queue")).find(qn("a:prstDash")).get("val") == "dash"
    assert line_of(one(prs, "Arch node Orders")).find(qn("a:prstDash")) is None  # a plain node is solid
    # sublabel: after the colon, smaller and muted
    sizes = [r.font.size.pt for p in focal.text_frame.paragraphs for r in p.runs if r.font.size]
    assert len(sizes) == 2 and sizes[1] < sizes[0]
    assert focal.text_frame.paragraphs[1].runs[0].text == "auth, limits"
    # accent arrows: the one marked edge, every other edge in the connector colour
    cols = []
    for e in named(prs, r"Arch edge \d+"):
        cols.append(str(line_of(e).find(qn("a:solidFill"))[0].get("val")).upper())
    assert cols.count("BF4520") == 1 and len(set(cols)) == 2


BAND = HEAD + "style: arch.tier.look=band\n"


def test_arch_nodes_in_a_tier_share_one_size_and_sit_in_their_tier(tmp_path):
    _deck, prs = make(tmp_path, ARCH, BAND)
    nodes = {n: one(prs, f"Arch node {n}") for n in ("Web app", "Mobile app", "API gateway", "Orders")}
    assert len({(s.width, s.height) for s in nodes.values()}) == 1
    tier1, tier2 = one(prs, "Arch tier 1"), one(prs, "Arch tier 2")
    for n in ("Web app", "Mobile app"):
        s = nodes[n]
        assert tier1.top <= s.top and s.top + s.height <= tier1.top + tier1.height
        assert s.left >= tier1.left and s.left + s.width <= tier1.left + tier1.width
    assert tier1.top + tier1.height < tier2.top  # a gap between tiers, where the arrows run


def test_arch_dir_h_makes_columns_and_routes_horizontally(tmp_path):
    text = ARCH.replace("@arch", "@arch dir=h")
    deck, prs = make(tmp_path, text, BAND)
    assert not real(deck), deck.diagnostics
    t1, t2, t3 = (one(prs, f"Arch tier {i}") for i in (1, 2, 3))
    assert t1.left < t2.left < t3.left
    mids = [t.top + t.height / 2 for t in (t1, t2, t3)]
    assert max(mids) - min(mids) < 2000  # columns share one centre line (each as tall as its nodes)
    for e in named(prs, r"Arch edge \d+"):
        xfrm = sppr(e).find(qn("a:xfrm"))
        assert xfrm.get("rot") is None, e.name  # horizontal-vertical-horizontal elbows are not rotated


def test_arch_tier_fill_token_and_none(tmp_path):
    _d, prs = make(tmp_path, ARCH, HEAD + "style: arch.tier.fill=#DDEEFF\n")
    assert str(one(prs, "Arch tier 1").fill.fore_color.rgb) == "DDEEFF"
    _d, prs = make(tmp_path, ARCH, HEAD + "style: arch.tier.fill=none\n")
    assert not named(prs, "Arch tier 1") and named(prs, "Arch tier 1 label")  # no band, the caption stays


def test_arch_japanese_dense_keeps_text_at_the_stated_size(tmp_path):
    text = (
        "\n# 構成\n@arch size=12\n## 入力\n- 受注API: 外部ECから受信 {.external}\n- 基幹ERP\n"
        "## 処理\n- 変換バッチ: 正規化・名寄せ\n- 与信チェック {.focal}\n"
        "## 保存\n- DWH: 全履歴 {.store}\n"
        "> 受注API > 変換バッチ: 受信, 基幹ERP > 与信チェック, 変換バッチ > DWH\n"
    )
    deck, prs = make(tmp_path, text)
    assert not real(deck), deck.diagnostics
    node = one(prs, "Arch node 受注API")
    assert {r.font.size.pt for p in node.text_frame.paragraphs[:1] for r in p.runs} == {12.0}
    ea = node.text_frame.paragraphs[0].runs[0]._r.find(qn("a:rPr")).find(qn("a:ea"))
    assert ea is not None


# --------------------------------------------------------------------------- @venn render


def test_venn_circles_are_translucent_ellipses_with_names_and_a_bold_overlap(tmp_path):
    deck, prs = make(tmp_path, VENN3)
    assert not real(deck), deck.diagnostics
    sets = [one(prs, f"Venn {i} set") for i in (1, 2, 3)]
    assert all(geom(s) == "ellipse" for s in sets)
    assert all(abs((fill_alpha(s) or 0) - 0.06) < 1e-3 for s in sets)  # editorial: ink at a few percent
    assert {str(s.fill.fore_color.rgb) for s in sets} == {"2D3142"}  # neutral, not a palette colour each
    for i, (name, body) in enumerate(
        (("Desirable", "People want it"), ("Feasible", "We can build it"), ("Viable", "It pays for itself")),
        1,
    ):
        n = one(prs, f"Venn {i} name")  # name + its body as a mono sublabel, inside the circle
        ps = [p.text.replace("\u00a0", " ") for p in n.text_frame.paragraphs]
        assert ps == [name, body] and n.text_frame.paragraphs[0].runs[0].font.bold
    ov = one(prs, "Venn overlap")
    assert ov.text_frame.text == "Worth building" and ov.text_frame.paragraphs[0].runs[0].font.bold
    # `{.focal}` on the overlap: the lens (a freeform) is solid accent
    fill = one(prs, "Venn overlap fill")
    assert str(fill.fill.fore_color.rgb).upper() == "BF4520" and fill_alpha(fill) is None
    # the set circles overlap in the middle and the centre label lies inside all of them
    cx, cy = ov.left + ov.width / 2, ov.top + ov.height / 2
    for s in sets:
        r = s.width / 2
        assert (cx - (s.left + r)) ** 2 + (cy - (s.top + r)) ** 2 < r * r


def test_venn_two_sets_and_focal_set_takes_the_accent(tmp_path):
    text = VENN2.replace("## Execution", "## Execution {.focal}")
    deck, prs = make(tmp_path, text)
    assert not real(deck), deck.diagnostics
    a, b = one(prs, "Venn 1 set"), one(prs, "Venn 2 set")
    assert str(b.fill.fore_color.rgb).upper() == "BF4520" and str(a.fill.fore_color.rgb).upper() != "BF4520"
    assert str(one(prs, "Venn overlap fill").fill.fore_color.rgb) == "2D3142"  # not focal: solid ink
    assert one(prs, "Venn overlap").text_frame.text == "A plan that ships"
    assert a.left + a.width > b.left  # they overlap


def test_venn_tokens(tmp_path):
    head = HEAD + "style: venn.fill=#CC0000,#0000CC venn.alpha=0.5 venn.line=fg venn.text=out\n"
    _d, prs = make(tmp_path, VENN2, head)
    a, b = one(prs, "Venn 1 set"), one(prs, "Venn 2 set")
    assert str(a.fill.fore_color.rgb) == "CC0000" and str(b.fill.fore_color.rgb) == "0000CC"
    assert abs(fill_alpha(a) - 0.5) < 1e-3
    left = one(prs, "Venn 1 name")  # `venn.text=out`: the set text sits beside the circle, not inside
    assert left.left + left.width <= a.left


# --------------------------------------------------------------------------- budget and fuzz


def _budget(text: str):
    deck = parse(HEAD + text)
    theme, _ = deck_theme(deck, ".")
    placed = [layout_slide(s, deck, theme, i) for i, s in enumerate(deck.slides)]
    return [d for d in lint_deck(deck, placed, theme) if d.rule == "diagram-budget"]


def test_diagram_budget_counts_arch_nodes_and_arrows_and_labels():
    assert not _budget(ARCH)
    many = (
        "\n# T\n@arch\n## A\n"
        + "".join(f"- n{k}\n" for k in range(6))
        + "## B\n"
        + "".join(f"- m{k}\n" for k in range(6))
    )
    got = _budget(many + "> n0 > m0\n")
    assert len(got) == 1 and "12 nodes" in got[0].message
    edges = ", ".join(f"n{i} > m{j}" for i in range(6) for j in range(3))
    got = _budget(many + f"> {edges}\n")
    assert got and "18 arrows" in got[0].message
    got = _budget(many.replace("12 nodes", "") + "> n0 > m0: " + "x" * 15 + "\n")
    assert got and "15 characters" in got[0].message


def test_unknown_node_in_an_edge_warns_with_a_did_you_mean(tmp_path):
    text = ARCH.replace("Orders > Postgres: write", "Orders > Postgress: write")
    deck, prs = make(tmp_path, text)
    got = warns(deck, "arch-edge")
    assert got and "Postgress" in got[0].message and "did you mean 'Postgres'?" in got[0].hint
    assert len(named(prs, r"Arch edge \d+")) == 5  # the others are drawn


@pytest.mark.parametrize(
    "edges",
    [
        "",
        "garbage",
        ">",
        "A > > B",
        "Web app >",
        "> Orders",
        "Web app > Web app",
        "Orders > Orders > Billing > Zzz",
        ",,;;",
    ],
)
def test_garbage_edges_never_raise(edges, tmp_path):
    text = (
        f"\n# T\n@arch\n## A\n- Web app\n- Orders\n## B\n- Billing\n> {edges}\n"
        if edges
        else ("\n# T\n@arch\n## A\n- Web app\n## B\n- Billing\n")
    )
    deck, prs = make(tmp_path, text)
    assert named(prs, "Arch node Web app") and named(prs, "Arch node Billing")
    for d in deck.diagnostics:
        assert d.level != "error"


def test_edges_between_non_neighbours_of_one_tier_warn():
    text = "\n# T\n@arch\n## A\n- a1\n- a2\n- a3\n## B\n- b1\n> a1 > a3\n"
    got = warns(parse(HEAD + text), "arch-edge")
    assert got and "crosses the nodes" in got[0].message


def test_duplicate_node_names_warn():
    got = warns(parse(HEAD + "\n# T\n@arch\n## A\n- x\n- X\n## B\n- y\n"), "arch-node")
    assert got and "appears twice" in got[0].message


@pytest.mark.parametrize("n", [1, 4])
def test_venn_needs_two_or_three_sets(n, tmp_path):
    text = "\n# T\n@venn\n" + "".join(f"## S{k}\nx\n" for k in range(n)) + "> centre\n"
    deck, prs = make(tmp_path, text)
    got = warns(deck, "venn-skipped")
    assert got and "2-3" in got[0].message and "ordinary blocks" in got[0].hint
    assert not named(prs, r"Venn.*")
    assert deck.slides[0].conclusion is not None  # not lifted: an ordinary bar


def test_arch_with_one_tier_or_an_empty_tier_is_skipped(tmp_path):
    one_tier = "\n# T\n@arch\n## A\n- x\n"
    deck, prs = make(tmp_path, one_tier)
    assert warns(deck, "arch-skipped") and not named(prs, r"Arch.*")
    empty = "\n# T\n@arch\n## A\n- x\n## B\nplain text only\n"
    # a paragraph without a marker is a node too; a tier with nothing at all is not drawn
    deck = parse(HEAD + "\n# T\n@arch\n## A\n- x\n## B\n")
    assert warns(deck, "arch-skipped")
    assert not warns(parse(HEAD + empty), "arch-skipped")


def test_twenty_nodes_build_with_the_budget_info_and_no_exception(tmp_path):
    rows = "".join(f"## T{t}\n" + "".join(f"- node {t}-{k}\n" for k in range(7)) for t in range(3))
    text = "\n# T\n@arch\n" + rows + "> node 0-0 > node 1-0, node 1-0 > node 2-0\n"
    deck, prs = make(tmp_path, text)
    assert len(named(prs, r"Arch node .*")) == 21
    assert [d for d in deck.diagnostics if d.level == "error"] == []
    got = _budget(text)
    assert got and "21 nodes" in got[0].message


def test_overlong_text_in_a_venn_is_a_diagnostic_not_an_exception(tmp_path):
    text = (
        "\n# T\n@venn\n## A\n" + "word " * 120 + "\n## B\n" + "word " * 120 + "\n> " + "centre " * 40 + "\n"
    )
    deck, prs = make(tmp_path, text)
    assert named(prs, "Venn 1 set")
    assert [d for d in deck.diagnostics if d.level == "error"] == []


@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(st.text(alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="`\r"), max_size=80))
def test_fuzzed_edge_and_node_text_never_raises(junk):
    for form in ("@arch", "@venn"):
        text = f"# T\n{form}\n## A\n- {junk}\n- b\n## B\n- c\n> {junk} > b, b > {junk}\n"
        deck = parse(HEAD + "\n" + text)
        theme, _ = deck_theme(deck, ".")
        for i, s in enumerate(deck.slides):
            layout_slide(s, deck, theme, i)


# --------------------------------------------------------------------------- importer


def test_arch_and_venn_round_trip_through_the_importer(tmp_path):
    from slidemark.importer import import_pptx

    a = tmp_path / "a.pptx"
    build(HEAD + ARCH + VENN3.replace(" {.focal}", ""), a)  # (the accent fill is not read back)
    md, _ = import_pptx(a)
    assert "@arch" in md and "@venn" in md
    for line in ("## Clients", "- API gateway: auth, limits", "## Data", "- Postgres: orders", "## Viable"):
        assert line in md
    assert "> Web app > API gateway, Mobile app > API gateway, API gateway > Orders: place order" in md
    assert "> Worth building" in md
    b = tmp_path / "b.pptx"
    build(md, b)

    def names(p):
        return [
            s.name
            for sl in Presentation(str(p)).slides
            for s in sl.shapes
            if s.name.startswith(("Arch", "Venn"))
        ]

    assert names(a) == names(b)


def test_arch_dir_h_round_trips(tmp_path):
    from slidemark.importer import import_pptx

    a = tmp_path / "a.pptx"
    build(HEAD + ARCH.replace("@arch", "@arch dir=h"), a)
    md, _ = import_pptx(a)
    assert "@arch dir=h" in md
