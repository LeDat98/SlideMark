"""Card groups without dead space (rubric G-05): hug, grow within grow_max, centre; a small @arch grows."""

from __future__ import annotations

from pptx import Presentation

from slidemark import build

HEAD = "---\ntitle: t\nsizes: title=34 heading=20 body=16\n{style}---\n"
CARDS_2X2 = (
    "\n# Many modes\n@2x2\n"
    "## Text {icon=list}\nWrite and translate.\n## Image {icon=eye}\nRecognise and draw.\n"
    "## Audio {icon=microphone}\nHear and speak.\n## Video {icon=video}\nWatch and cut.\n"
)
CARDS_ROW = (
    "\n# Plan\n@4 num\n## One\n- pick a task\n- measure\n## Two\n- widen\n- integrate\n"
    "## Three\n- rules\n- review\n## Four\n- watch\n- improve\n"
)


def make(tmp_path, body: str, style: str = "", name: str = "d"):
    head = HEAD.format(style=f"style: {style}\n" if style else "")
    deck = build(head + body, tmp_path / f"{name}.pptx")
    return deck, Presentation(str(tmp_path / f"{name}.pptx"))


def shapes(prs, pattern: str):
    return [s for s in prs.slides[0].shapes if s.name.startswith(pattern)]


def card_geometry(prs):
    cards = shapes(prs, "Card ")
    return min(c.top for c in cards), max(c.top + c.height for c in cards), cards


def test_cards_hug_their_content_and_the_group_is_centred(tmp_path):
    _d, off = make(tmp_path, CARDS_2X2, "layout.card_balance=off", "off")
    _d, on = make(tmp_path, CARDS_2X2, name="on")
    top0, bottom0, c0 = card_geometry(off)
    top1, bottom1, c1 = card_geometry(on)
    assert len(c1) == 4
    assert (bottom1 - top1) < (bottom0 - top0)  # no longer stretched over the body
    heights = {c.height for c in c1}
    assert max(heights) - min(heights) <= 2  # all cards equal
    for c in c1:  # the content ends close to the card bottom: no half-empty card
        inner = [
            s
            for s in on.slides[0].shapes
            if s.has_text_frame
            and s.text_frame.text
            and s.top >= c.top
            and s.top + s.height <= c.top + c.height + 1
            and s.left >= c.left
            and s.name.startswith("Text")
        ]
        assert inner
        assert c.top + c.height - max(s.top + s.height for s in inner) < 0.35 * c.height
    body_top = min(s.top for s in shapes(on, "Title")) + shapes(on, "Title")[0].height
    foot = shapes(on, "Footer") or shapes(on, "Slide Number")
    low = foot[0].top if foot else on.slide_height
    above, below = top1 - body_top, low - bottom1
    assert abs(above - below) < 0.25 * (above + below)  # centred, optical top share 0.45


def test_text_grows_within_grow_max(tmp_path):
    _d, off = make(tmp_path, CARDS_2X2, "layout.card_balance=off", "off")
    _d, on = make(tmp_path, CARDS_2X2, name="on")

    def size(prs):
        return max(
            r.font.size.pt for s in shapes(prs, "Text 1") for p in s.text_frame.paragraphs for r in p.runs
        )

    assert size(on) >= size(off)
    assert size(on) <= 16 * 1.5 + 0.01  # layout.grow_max x the role size
    _d, flat = make(tmp_path, CARDS_2X2, "layout.grow_max=1", "flat")
    assert size(flat) <= 16 + 0.01  # no growth under grow_max=1, the cards still hug
    assert size(on) > size(flat)


def test_pinned_body_size_stays(tmp_path):
    head = HEAD.format(style="").replace("body=16", "body=16!")
    build(head + CARDS_2X2, tmp_path / "p.pptx")
    prs = Presentation(str(tmp_path / "p.pptx"))
    sizes = {r.font.size.pt for s in shapes(prs, "Text") for p in s.text_frame.paragraphs for r in p.runs}
    assert sizes == {16.0}


def test_numbered_cards_line_up_and_are_equal(tmp_path):
    _d, off = make(tmp_path, CARDS_ROW, "layout.card_balance=off", "off")
    _d, on = make(tmp_path, CARDS_ROW, name="on")
    t0, b0, _ = card_geometry(off)
    t1, b1, cards = card_geometry(on)
    assert (b1 - t1) <= (b0 - t0)  # hugging never makes the group taller than the stretched one
    nums = shapes(on, "Num ")
    assert len({n.top for n in nums}) == 1  # numbers line up across cards
    assert len({c.height for c in cards}) == 1


def test_a_spanning_area_grid_is_left_alone(tmp_path):
    text = "\n# Areas\n@areas a b/a c\n## A\nlong\n- one\n- two\n- three\n## B\nx\n## C\ny\n"
    _d, off = make(tmp_path, text, "layout.card_balance=off", "off")
    _d, on = make(tmp_path, text, name="on")
    assert [(c.top, c.height) for c in shapes(off, "Card ")] == [
        (c.top, c.height) for c in shapes(on, "Card ")
    ]


def test_a_small_arch_diagram_grows_its_gaps(tmp_path):
    body = "\n# Flow\n@arch\n## Client\n- Web\n## Platform\n- API\n- DB\n> Web > API, API > DB\n"
    _d, small = make(tmp_path, body, "arch.grow=1", "small")
    _d, grown = make(tmp_path, body, name="grown")

    def node_height(prs):
        nodes = [s for s in prs.slides[0].shapes if s.name.startswith("Arch node ")]
        return max(s.height for s in nodes), max(s.top + s.height for s in nodes) - min(s.top for s in nodes)

    (h0, spread0), (h1, spread1) = node_height(small), node_height(grown)
    assert h1 > h0 and spread1 > spread0  # taller nodes and more air between the tiers
    assert h1 <= h0 * 1.6  # nodes grow by half as much as the gaps: arch.grow=1.6 -> 1.3x
