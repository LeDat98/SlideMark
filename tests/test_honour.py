"""``attr-ignored``: every documented attribute is honoured or listed as ignored on each element kind (no
third state), the table is true (each cell is probed against the real layout and renderer), and the warning
names a form that works. Also the honoured one-liners: ``y=`` / ``h=`` on a lone KPI row."""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

import pytest
from PIL import Image

from slidemark.build import build
from slidemark.honour import ATTRS, HONOURED, IGNORED, LABEL, STYLE_NEEDS, audit, honoured
from slidemark.parser import parse
from slidemark.template import deck_theme

DOCS = Path(__file__).resolve().parent.parent / "docs" / "SYNTAX.md"
HEAD = "theme: jp-business\nlang: ja\n"

# One probe deck per element kind; `{A}` is where the attribute goes (`<A>` inside an existing `{}`).
PROBES: dict[str, str] = {
    "title": "# T {A}\n## a\n- x\n## b\n- y\n## c\n- z\n",
    "cover": "# T {A}\n## sub\n",
    "box": "# T\n> lead\n## a {<A>}\n- x\n- y\n## b\n- y\n## c\n- z\n",
    "kpi": "# T\n> lead\n## L1 {.kpi <A>}\n12\ncap\n## L2 {.kpi}\n34\ncap\n## L3 {.kpi}\n56\ncap\n",
    "kpi-row": "# T\n> lead\n## L1 {.kpi <A>}\n12\ncap\n## L2 {.kpi}\n34\ncap\n@end\n- text\n- text\n",
    "step": "# T\n@3 steps\n## a {<A>}\n- x\n## b\n- y\n## c\n- z\n",
    "chevron": "# T\n@3 chevron\n## a {<A>}\n- x\n## b\n- y\n## c\n- z\n",
    "text": "# T\n> lead\n{A}\nParagraph one\n\nParagraph two\n",
    "callout": "# T\n> lead\n{A}\n> [!note] hello\n",
    "image": "# T\n> lead\n![alt](img.png){A}\n",
    "table": "# T\n> lead\n{A}\n```table\na,b\n1,2\n3,4\n```\n",
    "chart": "# T\n> lead\n{A}\n```column\n,a,b\nS,1,2\n```\n",
    "code": "# T\n> lead\n{A}\n```python\nprint(1)\n```\n",
    "rows": "# T\n@rows\n{A}\n1. one\n2. two\n3. three\n",
}
EXTRA_HEAD = {"chevron": "style: layout.chevron_steps=off\n"}
# values that change the output (any of them differing from the baseline counts as honoured)
VALUES: dict[str, list[str]] = {
    "x": ["x=10%"],
    "y": ["y=10%"],
    "w": ["w=60%"],
    "h": ["h=50%"],
    "size": ["size=20"],
    "color": ["color=#FF0000"],
    "fill": ["fill=#00FF00", "fill=primary"],
    "line": ["line=#0000FF"],
    "font": ["font=Arial"],
    "align": ["align=right", "align=center", "align=left"],
    "valign": ["valign=bottom", "valign=middle", "valign=top"],
    "bold": ["bold=true", "bold=false"],
    "italic": ["italic=true"],
    "radius": ["radius=20"],
    "opacity": ["opacity=0.5"],
    "pad": ["pad=20pt"],
    "fit": ["fit=cover"],
    "icon": ["icon=chart"],
}
TABLE_ALIGN = ["align=lr", "align=rl"]  # a table's align is one letter per column


def _deck(kind: str, attrs: str | None) -> str:
    tpl = PROBES[kind]
    if attrs is None:
        out = tpl.replace("{A}", "").replace(" <A>}", "}").replace("{<A>}", "")
    elif "<A>" in tpl:
        out = tpl.replace("<A>", attrs)
    else:
        out = tpl.replace("{A}", "{" + attrs + "}")
    return HEAD + EXTRA_HEAD.get(kind, "") + out


def _slide_xml(text: str, tmp: Path):
    out = tmp / "x.pptx"
    deck = build(text, out, base_dir=tmp)
    with zipfile.ZipFile(out) as z:
        names = sorted(n for n in z.namelist() if re.match(r"ppt/(slides/slide|charts/chart)\d+\.xml", n))
        blob = b"".join(z.read(n) for n in names)
    return re.sub(rb"\{[0-9A-F-]{36}\}", b"{GUID}", blob), deck


def _diags(text: str, tmp: Path):
    """Parse + layout + lint (what ``check`` runs): the diagnostics without writing a .pptx."""
    from slidemark.cli import _add_layout_diagnostics

    deck = parse(text)
    _add_layout_diagnostics(deck, str(tmp / "d.md"))
    return deck.diagnostics


@pytest.fixture(scope="module")
def tmp_probe(tmp_path_factory):
    d = tmp_path_factory.mktemp("honour")
    Image.new("RGB", (40, 30), (200, 50, 50)).save(d / "img.png")
    return d


# --------------------------------------------------------------------------- the table is total


def test_every_kind_decides_every_attribute():
    assert set(HONOURED) == set(IGNORED) == set(LABEL) == set(PROBES)
    for kind in HONOURED:
        yes = set(HONOURED[kind].split())
        no = set(IGNORED[kind])
        assert not yes & no, (kind, yes & no)
        assert yes | no == set(ATTRS), (kind, set(ATTRS) - (yes | no), (yes | no) - set(ATTRS))
        assert all(h and len(h) < 130 for h in IGNORED[kind].values()), kind


def test_documented_attributes_are_in_the_table():
    """The `Keys` table of docs/SYNTAX.md names the attributes; each must be decided on every kind."""
    text = DOCS.read_text(encoding="utf-8")
    keys = text.split("Keys:", 1)[1].split("\n\n", 2)[1]
    documented: set[str] = set()
    for row in keys.splitlines():
        cells = row.split("|")
        if len(cells) < 3:
            continue
        group, cell = cells[1].strip(), re.sub(r"\([^)]*\)", "", cells[2])
        if group == "Position":
            documented |= set(re.findall(r"`([a-z ]+)`", cell)[0].split())
        elif group == "Style":
            documented |= set(re.findall(r"`([a-z]+)`", cell))
        elif group == "Image":
            documented |= {re.findall(r"`([a-z]+)=", cell)[0]}
    assert documented == {
        *"xywh",
        "size",
        "color",
        "fill",
        "line",
        "align",
        "valign",
        "bold",
        "radius",
        "pad",
        "fit",
    }
    assert documented <= set(ATTRS), documented - set(ATTRS)
    assert "icon=" in text and "icon" in ATTRS  # `icon=name` is documented under Components


def test_style_needs_patterns_compile_and_carry_hints():
    for pat, need, hint in STYLE_NEEDS:
        assert pat.pattern and callable(need) and len(hint) < 130


# --------------------------------------------------------------------------- the table is true


@pytest.mark.parametrize("kind", sorted(PROBES))
def test_table_matches_layout_and_renderer(kind, tmp_probe):
    base, _ = _slide_xml(_deck(kind, None), tmp_probe)
    wrong = []
    for attr in ATTRS:
        values = TABLE_ALIGN if (kind == "table" and attr == "align") else VALUES[attr]
        changed = False
        for v in values:
            xml, deck = _slide_xml(_deck(kind, v), tmp_probe)
            changed = changed or xml != base
        expect = honoured(kind, attr)
        if kind == "table" and attr == "align":
            expect = True
        if changed != expect:
            wrong.append(
                f"{kind}.{attr}: table says {'honoured' if expect else 'ignored'}, "
                f"output {'changed' if changed else 'is the same'}"
            )
    assert not wrong, wrong


@pytest.mark.parametrize("kind", sorted(PROBES))
def test_ignored_attribute_warns_with_a_hint(kind, tmp_probe):
    for attr, hint in IGNORED[kind].items():
        v = VALUES[attr][0]
        hits = [
            d
            for d in _diags(_deck(kind, v), tmp_probe)
            if d.rule == "attr-ignored" and d.message.startswith(f"{attr}=")
        ]
        assert hits, f"{kind}.{attr} is ignored but not reported"
        assert hits[0].hint == hint
        assert LABEL[kind] in hits[0].message


@pytest.mark.parametrize("kind", sorted(PROBES))
def test_honoured_attribute_is_silent(kind, tmp_probe):
    for attr in HONOURED[kind].split():
        v = VALUES[attr][0]
        assert not [d for d in _diags(_deck(kind, v), tmp_probe) if d.rule == "attr-ignored"], (
            f"{kind}.{attr}"
        )


# --------------------------------------------------------------------------- context rules


def _warn(md: str, tmp: Path):
    return [d for d in _diags(HEAD + md, tmp) if d.rule == "attr-ignored"]


def test_free_slides_honour_geometry_on_every_kind(tmp_probe):
    md = (
        "# T {x=5% y=2% w=50% h=10%}\n@free\n## a {x=5% y=20% w=40% h=40%}\n- x\n"
        "{x=55% y=20% w=40% h=40%}\ntext\n"
    )
    assert not _warn(md, tmp_probe)


def test_size_on_a_box_without_text_is_ignored(tmp_probe):
    got = _warn("# T\n> lead\n## a {size=40}\n## b\n## c\n", tmp_probe)
    assert [d.message for d in got] == ["size= on a box is not honoured"]
    assert "sizes: heading=" in got[0].hint
    assert not _warn("# T\n> lead\n## a {size=40}\n- x\n## b\n- y\n## c\n- z\n", tmp_probe)


def test_kpi_pins_need_the_cards_alone(tmp_probe):
    beside = _warn("# T\n> lead\n## a {.kpi h=55% y=24%}\n1\nc\n## b {.kpi}\n2\nc\n@end\n- x\n", tmp_probe)
    assert sorted(d.message for d in beside) == [
        "h= on a KPI card beside other content is not honoured",
        "y= on a KPI card beside other content is not honoured",
    ]
    assert all("layout.kpi_to_body_h=0.55" in d.hint and "alone" in d.hint for d in beside)
    icon = _warn("# T\n> lead\n## a {.kpi h=55% icon=yen}\n1\nc\n## b {.kpi}\n2\nc\n", tmp_probe)
    assert [d.message for d in icon] == ["h= on a KPI card beside other content is not honoured"]
    assert not _warn("# T\n> lead\n## a {.kpi h=55% y=24%}\n1\nc\n## b {.kpi}\n2\nc\n", tmp_probe)


# --------------------------------------------------------------------------- the honoured one-liners


def _cards(md: str, tmp: Path):
    from slidemark.layout import layout_slide, measure

    deck = parse(HEAD + md)
    theme, _ = deck_theme(deck, str(tmp))
    measure.set_tokens(theme.layout)
    items = layout_slide(deck.slides[0], deck, theme, 0)
    cards = [p for p in items if "kpi" in getattr(p.element, "classes", [])]
    body = deck.attrs["_fit"][0]["body"]
    return cards, body


KPIS = "## a {.kpi%s}\n12\ncap\n## b {.kpi}\n34\ncap\n## c {.kpi}\n56\ncap\n"


def test_kpi_row_takes_h_from_the_first_card(tmp_probe):
    cards, body = _cards("# T\n> lead\n" + KPIS % " h=40%", tmp_probe)
    assert len(cards) == 3
    assert {c.h for c in cards} == {cards[0].h}  # every card of the row is as tall as the first
    assert cards[0].h == pytest.approx(0.4 * body[3], abs=3)
    cards2, _ = _cards("# T\n> lead\n" + KPIS % " h=55%", tmp_probe)
    assert cards2[0].h > cards[0].h


def test_kpi_row_takes_y_from_the_first_card(tmp_probe):
    cards, body = _cards("# T\n> lead\n" + KPIS % " h=30% y=10%", tmp_probe)
    assert {c.y for c in cards} == {cards[0].y}
    assert cards[0].y == pytest.approx(body[1] + 0.1 * body[3], abs=3)
    assert len({c.x for c in cards}) == 3  # still a row, not a pile


def test_kpi_pins_are_dropped_beside_other_content(tmp_probe):
    plain, _ = _cards("# T\n> lead\n" + KPIS % "" + "@end\n- x\n", tmp_probe)
    pinned, _ = _cards("# T\n> lead\n" + KPIS % " h=30% y=10%" + "@end\n- x\n", tmp_probe)
    assert [(c.x, c.y, c.w, c.h) for c in plain] == [(c.x, c.y, c.w, c.h) for c in pinned]


def test_audit_reports_honoured_cells_too(tmp_probe):
    deck = parse(HEAD + "# T\n> lead\n" + KPIS % " h=40% size=30")
    theme, _ = deck_theme(deck, str(tmp_probe))
    got = {(kind, attr): hint for _, kind, attr, hint in audit(deck.slides[0], theme)}
    assert got == {("kpi", "h"): None, ("kpi", "size"): None}


def test_check_reports_it_too(tmp_probe):
    """lint_deck gets ``attr-ignored`` from ``check`` / ``review`` too (no .pptx written)."""
    got = _diags(HEAD + "# T\n> lead\n## a {.kpi h=50%}\n1\nc\n## b {.kpi}\n2\nc\n@end\n- x\n", tmp_probe)
    assert any(d.rule == "attr-ignored" for d in got)


# --------------------------------------------------------------------------- style: tokens

SHEAD = (
    "theme: jp-business\nlang: ja\nfooter: ACME\nnum: on\nstyle: top.bar_h=0.1in"  # tokens on = derived inks
)
COVER = "# Title\n## sub\n\n# Body\n- x\n"
CHEV = "# T\n@3 chevron\n## a\n- x\n## b\n- y\n## c\n- z\n"
STEPS = "# T\n@3 steps\n## a\n- x\n## b\n- y\n## c\n- z\n"
KPI = "# T\n## a {.kpi}\n12\ncap\n## b {.kpi}\n3\ncap\n"
LIST = "# T\n> lead\n- a\n- b\n"
BOXES = "# T\n## a\n- x\n## b\n- y\n"
TABLE = "# T\n```table\na,b\n1,2\n3,4\n```\n"
CHART = "# T\n```column\n,a,b\nS,1,2\n```\n"
ROWS = "# T\n@rows\n1. a\n2. b\n"

# (token, a deck that lacks what it styles, a deck that has it)
STYLE_CASES = [
    ("cover.rule=#FF0000", LIST, COVER),
    ("cover.bar=#FF0000", LIST, COVER),
    ("cover.band_h=70%", LIST, COVER),
    ("kpi.stripe=#FF0000", BOXES, KPI),
    ("kpi.value.size=30", BOXES, KPI),
    ("layout.kpi_to_body_h=0.5", BOXES, KPI),
    ("steps-arrow.fill=#FF0000", LIST, STEPS),
    ("steps.caption=STEP", LIST, STEPS),
    ("rows-num.fill=#FF0000", LIST, ROWS),
    ("table.header.fill=#FF0000", BOXES, TABLE),
    ("palette=#FF0000,#00FF00", TABLE, CHART),
    ("render.chart_grid=#FF0000", TABLE, CHART),
    ("bullet=■", TABLE, LIST),
    ("heading.band=#FF0000", LIST, BOXES),
    ("card.fill=#FF0000", LIST, BOXES),
    ("lead.bold=on", BOXES, LIST),
]


def _styled(token: str, deck_md: str, tmp: Path):
    return _slide_xml(f"{SHEAD} {token}\n{deck_md}", tmp)


@pytest.mark.parametrize(("token", "lacks", "has"), STYLE_CASES)
def test_style_token_needs_its_element(token, lacks, has, tmp_probe):
    base, _ = _slide_xml(f"{SHEAD}\n{lacks}", tmp_probe)
    xml, deck = _styled(token, lacks, tmp_probe)
    assert xml == base, f"{token} changed a deck that has nothing to style"
    hits = [d for d in deck.diagnostics if d.rule == "attr-ignored"]
    key = token.split("=")[0]
    assert [d.message for d in hits] == [f"style: {key}= has no effect here"], hits
    assert hits[0].hint and hits[0].line  # the header line to edit

    base, _ = _slide_xml(f"{SHEAD}\n{has}", tmp_probe)
    xml, deck = _styled(token, has, tmp_probe)
    assert xml != base, f"{token} is silent but changes nothing on a deck that has the element"
    assert not [d for d in deck.diagnostics if d.rule == "attr-ignored"]


def test_chevron_class_fill_never_colours_the_row(tmp_probe):
    """`chevron.fill` is accepted by the token parser (a new class name is legal) yet draws nothing."""
    for md in (CHEV, STEPS):
        base, _ = _slide_xml(f"{SHEAD}\n{md}", tmp_probe)
        xml, deck = _styled("chevron.fill=#FF0000", md, tmp_probe)
        assert xml == base
        got = [d for d in deck.diagnostics if d.rule == "attr-ignored"]
        assert got and "steps-arrow.fill" in got[0].hint


def test_cover_tokens_need_the_anchored_cover(tmp_probe):
    """A `{size=}` on the cover title keeps the old centred look: the rule is not drawn."""
    sized = "# Title {size=44}\n## sub\n\n# Body\n- x\n"
    base, _ = _slide_xml(f"{SHEAD}\n{sized}", tmp_probe)
    xml, deck = _styled("cover.rule=#FF0000", sized, tmp_probe)
    assert xml == base
    assert any("anchored cover" in (d.hint or "") for d in deck.diagnostics if d.rule == "attr-ignored")
    flat = _diags(f"{SHEAD} cover.band_h=0 cover.rule=#FF0000\n{COVER}", tmp_probe)
    assert any(d.rule == "attr-ignored" and "cover.rule" in d.message for d in flat)


def test_style_tokens_judge_the_deck_not_the_slide(tmp_probe):
    """One slide with the element is enough; every token is reported once, on its header line."""
    both = f"{LIST}\n{KPI}"
    assert not [
        d for d in _diags(f"{SHEAD} kpi.stripe=#FF0000\n{both}", tmp_probe) if d.rule == "attr-ignored"
    ]
    twice = _diags(f"{SHEAD} kpi.stripe=#FF0000 kpi.fill=#FF0000 kpi.stripe=#FF0000\n{LIST}", tmp_probe)
    assert sorted(d.message for d in twice if d.rule == "attr-ignored") == [
        "style: kpi.fill= has no effect here",
        "style: kpi.stripe= has no effect here",
    ]


def test_syntax_doc_lists_the_ignored_table():
    """docs/SYNTAX.md "Build output" prints IGNORED row by row: the doc cannot drift from the code."""
    text = DOCS.read_text(encoding="utf-8").split("### `attr-ignored`", 1)[1]
    rows = [r.split("|") for r in text.splitlines() if r.startswith("| `")]
    for kind, ignored in IGNORED.items():
        row = next(r for r in rows if f"`{kind}`" in r[1])
        assert set(re.findall(r"`([a-z]+)`", row[2])) == set(ignored), kind


def test_short_chevron_row_is_judged_as_steps(tmp_probe):
    """The layout builds `@chevron` with short bodies as `@steps`: step boxes take no `h=`."""
    short = _warn("# T\n@3 chevron\n## a {h=30%}\n- x\n## b\n- y\n## c\n- z\n", tmp_probe)
    assert [d.message for d in short] == ["h= on an @steps box is not honoured"]
    compact = _warn("# T\n@3 chevron\n## a {h=30%}\n- x\n## b\n- y\n## c\n- z\n", tmp_probe)
    assert compact  # (without chevron_steps=off the row is steps)
    off = _diags(
        HEAD + "style: layout.chevron_steps=off\n# T\n@3 chevron\n## a {h=30%}\n- x\n## b\n- y\n## c\n- z\n",
        tmp_probe,
    )
    assert [d.message for d in off if d.rule == "attr-ignored"] == [
        "h= on a compact @chevron box is not honoured"
    ]


def test_cover_tokens_see_css_on_the_cover_title(tmp_probe):
    css = "```css\nh1 { font-size: 40pt }\n```\n"
    got = _diags(f"{SHEAD} cover.rule=#FF0000\n{css}\n{COVER}", tmp_probe)
    assert any(d.rule == "attr-ignored" and "cover.rule" in d.message for d in got)
    plain = "```css\n.lead { font-weight: bold }\n```\n"
    got = _diags(f"{SHEAD} cover.rule=#FF0000\n{plain}\n{COVER}", tmp_probe)
    assert not [d for d in got if d.rule == "attr-ignored"]
