"""Lane J: round-2 UI review of the diagram routing and forms.

Mermaid flowcharts (heads at the middle of a side, 12 px from every border, no shared trunk, a straight run
before the head, knockout labels), minimum arrow length in ``@arch`` / ``@swimlane``, separate corridors for
labelled parallel arrows, the vertical swimlane, mono labels of ``@venn`` on one line, distinct store / input
roles and the legend / eyebrow margins. Geometry is read back from the rebuilt .pptx."""

from __future__ import annotations

import re

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn

from slidemark import build
from slidemark.layout import diagramkit as DK
from slidemark.theme import get_theme

from .test_diagram_fixes import HEAD, PX, build_example, named, poly

CLR = 12 * PX - 2 * PX  # 12 px, less the rounding of the shapes
FANOUT = (
    "# Where the data goes\n```mermaid\nflowchart LR\n  A[Checkout]:::input --> B{Fraud check}\n"
    "  B -->|yes| C[Orders DB]:::store\n  B -->|no| D[Stripe]:::external\n  B --> E[Key vault]:::optional\n"
    "  C --> F[Reports]:::focal\n```\n@noemph defaults\n"
)
DECISION = (
    "# Decision tree\n```mermaid\nflowchart TD\n  A[Start] --> B{Valid?}\n  B -->|yes| C[Process]\n"
    "  B -->|no| D[Reject]\n  C --> E{Paid?}\n  E -->|yes| F[Ship]\n  E -->|no| G[Remind]\n  G --> E\n```\n"
    "@noemph defaults\n"
)


def _nodes(sl):
    return [
        s
        for s in sl.shapes
        if s.shape_type == 1
        and s.auto_shape_type in (MSO_SHAPE.ROUNDED_RECTANGLE, MSO_SHAPE.DIAMOND)
        and not s.name.startswith("Legend")
    ]


def _lines(sl):
    return [s for s in sl.shapes if s._element.tag == qn("p:cxnSp") and not s.name.startswith("Legend")]


def _segs(shp):
    pts = poly(shp)
    return list(zip(pts, pts[1:], strict=False))


def _site_centres(n):
    return [
        (n.left + n.width // 2, n.top),
        (n.left, n.top + n.height // 2),
        (n.left + n.width // 2, n.top + n.height),
        (n.left + n.width, n.top + n.height // 2),
    ]


def _dist(p, n):
    dx = max(n.left - p[0], 0, p[0] - (n.left + n.width))
    dy = max(n.top - p[1], 0, p[1] - (n.top + n.height))
    return max(dx, dy)


def _flow_slide(tmp_path, text):
    build(HEAD + text, tmp_path / "f.pptx")
    return Presentation(str(tmp_path / "f.pptx")).slides[0]


def test_flowchart_heads_land_at_the_middle_of_a_side(tmp_path):
    for text in (FANOUT, DECISION):
        sl = _flow_slide(tmp_path, text)
        nodes = _nodes(sl)
        heads = [c for c in _lines(sl) if c._element.spPr.find(qn("a:ln")).find(qn("a:tailEnd")) is not None]
        assert len(heads) >= 5
        for c in heads:
            end = poly(c)[-1]
            assert any(
                abs(end[0] - s[0]) <= 2 * PX and abs(end[1] - s[1]) <= 2 * PX
                for n in nodes
                for s in _site_centres(n)
            ), (
                text[:20],
                end,
            )


def test_flowchart_connectors_keep_12px_from_nodes_they_pass(tmp_path):
    for text in (FANOUT, DECISION):
        sl = _flow_slide(tmp_path, text)
        nodes = _nodes(sl)
        for c in _lines(sl):
            for a, b in _segs(c):
                for n in nodes:
                    touches = _dist(a, n) <= 2 * PX or _dist(b, n) <= 2 * PX  # leaves / enters this node
                    if touches:
                        continue
                    lo_x, hi_x = sorted((a[0], b[0]))
                    lo_y, hi_y = sorted((a[1], b[1]))
                    gap = max(
                        n.left - hi_x, lo_x - (n.left + n.width), n.top - hi_y, lo_y - (n.top + n.height)
                    )
                    assert gap >= CLR, (text[:20], n.name, gap / PX)


def test_flowchart_fan_out_has_no_shared_trunk(tmp_path):
    sl = _flow_slide(tmp_path, FANOUT)
    segs = [(i, s) for i, c in enumerate(_lines(sl)) for s in _segs(c)]
    for i, (ci, (a, b)) in enumerate(segs):
        for cj, (c, d) in segs[i + 1 :]:
            if ci == cj:
                continue
            horiz = a[1] == b[1] and c[1] == d[1] and abs(a[1] - c[1]) < 12 * PX
            vert = a[0] == b[0] and c[0] == d[0] and abs(a[0] - c[0]) < 12 * PX
            if horiz:
                overlap = min(max(a[0], b[0]), max(c[0], d[0])) - max(min(a[0], b[0]), min(c[0], d[0]))
            elif vert:
                overlap = min(max(a[1], b[1]), max(c[1], d[1])) - max(min(a[1], b[1]), min(c[1], d[1]))
            else:
                continue
            assert overlap <= 2 * PX, "two connectors run side by side"


def test_flowchart_head_has_a_straight_run_and_branch_labels_are_mono_knockouts(tmp_path):
    sl = _flow_slide(tmp_path, FANOUT)
    for c in _lines(sl):
        if c._element.spPr.find(qn("a:ln")).find(qn("a:tailEnd")) is None:
            continue
        (a, b) = _segs(c)[-1]
        assert abs(b[0] - a[0]) + abs(b[1] - a[1]) >= 0.2 * 914400 - 2 * PX  # a run before the head
    labs = [s for s in sl.shapes if re.fullmatch(r"Flow edge \d+ label", s.name)]
    assert sorted(s.text_frame.text for s in labs) == ["no", "yes"]
    for s in labs:
        r = s.text_frame.paragraphs[0].runs[0]
        assert r.font.size.pt == 8 and r.font.name in ("Consolas", "Liberation Mono")
        assert s.fill.type is not None  # a knockout of the slide colour


def test_decision_back_edge_enters_a_free_vertex(tmp_path):
    sl = _flow_slide(tmp_path, DECISION)
    paid = next(n for n in _nodes(sl) if n.text_frame.text.startswith("Paid"))
    ends = []
    for c in _lines(sl):
        pts = poly(c)
        ends += [p for p in (pts[0], pts[-1]) if _dist(p, paid) <= 2 * PX]
    # top: in from Process; bottom: yes; right: no; the loop back takes the fourth vertex: all four distinct
    assert len({(round(x / (4 * PX)), round(y / (4 * PX))) for x, y in ends}) == 4


# --------------------------------------------------------------------------- arrows of @arch / @swimlane


def test_no_stub_arrows_in_swimlanes_and_arch(tmp_path):
    _deck, prs = build_example(tmp_path, "28-swimlane-sequence.md")
    for i in (0, 1, 4):
        for c in named(prs.slides[i], r"Step \d+ next"):
            segs = _segs(c)
            length = sum(abs(b[0] - a[0]) + abs(b[1] - a[1]) for a, b in segs)
            assert length >= 0.22 * 914400, (i, c.name, length / PX)
    _deck, prs = build_example(tmp_path, "29-arch-venn.md")
    for c in named(prs.slides[1], r"Arch edge \d+"):
        length = sum(abs(b[0] - a[0]) + abs(b[1] - a[1]) for a, b in _segs(c))
        assert length >= 0.22 * 914400, (c.name, length / PX)


def test_labelled_parallel_arrows_leave_in_separate_corridors(tmp_path):
    _deck, prs = build_example(tmp_path, "29-arch-venn.md")
    sl = prs.slides[1]
    dwh = next(s for s in sl.shapes if s.name == "Arch node DWH")
    starts = sorted(
        poly(c)[0][1]
        for c in named(sl, r"Arch edge \d+")
        if abs(poly(c)[0][0] - (dwh.left + dwh.width)) <= PX
    )
    assert len(starts) == 2 and starts[1] - starts[0] >= 22 * PX  # 参照 and 集計: 24 px apart (labelled)


def test_vertical_swimlane_runs_clear_of_the_cards_and_uses_the_lane(tmp_path):
    _deck, prs = build_example(tmp_path, "28-swimlane-sequence.md")
    sl = prs.slides[4]
    steps = named(sl, r"Step \d+")
    assert len(steps) == 5 and all("\n" in s.text_frame.text for s in steps)  # name + mono sublabel
    for c in named(sl, r"Step \d+ next"):
        pts = poly(c)
        for a, b in zip(pts, pts[1:], strict=False):
            if a[1] == b[1] and a[0] != b[0]:  # a horizontal run: 12 px below / above every card it passes
                for s in steps:
                    if s.left < max(a[0], b[0]) and s.left + s.width > min(a[0], b[0]):
                        assert min(abs(a[1] - s.top), abs(a[1] - (s.top + s.height))) >= 11 * PX
    lanes = named(sl, r"Lane \d+")
    used = max(s.top + s.height for s in steps) - min(s.top for s in steps)
    assert used >= 0.8 * lanes[0].height  # the steps spread over the lane


def test_swimlane_step_names_are_one_size_and_not_larger_than_12pt(tmp_path):
    _deck, prs = build_example(tmp_path, "28-swimlane-sequence.md")
    for i in (0, 4):
        sizes = {
            r.font.size.pt
            for s in named(prs.slides[i], r"Step \d+")
            for r in s.text_frame.paragraphs[0].runs
            if r.font.size
        }
        assert len(sizes) == 1 and max(sizes) <= 12.0


# --------------------------------------------------------------------------- venn


def test_venn_mono_labels_stay_on_one_line_and_siblings_share_a_line(tmp_path):
    _deck, prs = build_example(tmp_path, "29-arch-venn.md")
    th = get_theme("editorial")
    for i in (2, 3):
        sl = prs.slides[i]
        for s in named(sl, r"Venn \d+ name"):
            paras = s.text_frame.paragraphs
            assert len(paras) == 2
            r = paras[1].runs[0]
            need = DK.mono_w(r.text, r.font.size.pt, th.diagram_label_track)
            assert s.width >= need, (s.name, r.text, s.width / PX, need / PX)
        core = named(sl, "Venn overlap")[0]
        assert len(core.text_frame.paragraphs) <= 2 and len(core.text_frame.text.split("\n")) <= 2
    names = named(prs.slides[2], r"Venn \d+ name")
    low = [s for s in names if s.text_frame.text.startswith(("Feasible", "Viable"))]
    assert len(low) == 2 and low[0].top == low[1].top and low[0].height == low[1].height
    two = named(prs.slides[3], r"Venn \d+ name")
    assert len({s.top for s in two}) == 1
    sets = named(prs.slides[2], r"Venn \d+ set")
    bottom = max(s.top + s.height for s in sets)
    assert prs.slide_height - bottom >= 0.55 * 914400  # clear of the page number


# --------------------------------------------------------------------------- roles, legend, eyebrow


def test_store_and_input_are_distinct_in_every_preset():
    for name in ("editorial", "default", "jp-business", "midnight"):
        th = get_theme(name)
        store, inp = th.classes["store"], th.classes["input"]
        assert store.fill != inp.fill, name
        assert inp.border_left and not store.border_left, name


def test_store_and_input_swatches_differ_in_the_legend(tmp_path):
    _deck, prs = build_example(tmp_path, "28-swimlane-sequence.md")
    sl = prs.slides[3]
    store = named(sl, "Legend store swatch")[0]
    inp = named(sl, "Legend input swatch")[0]
    assert str(store.fill.fore_color.rgb) != str(inp.fill.fore_color.rgb) or store.fill.fore_color.rgb is None
    assert named(sl, "Legend input swatch stripe") and not named(sl, "Legend store swatch stripe")


def test_legend_starts_at_the_title_margin_on_every_form(tmp_path):
    for example, slides in (("28-swimlane-sequence.md", range(5)), ("29-arch-venn.md", (0, 1))):
        _deck, prs = build_example(tmp_path, example)
        for i in slides:
            sl = prs.slides[i]
            title = next(s for s in sl.shapes if s.name == "Title")
            cap = named(sl, "Legend caption")
            assert cap and cap[0].left == title.left, (example, i, cap[0].left, title.left)


def test_every_slide_of_the_arch_venn_example_has_an_eyebrow(tmp_path):
    _deck, prs = build_example(tmp_path, "29-arch-venn.md")
    for sl in prs.slides:
        eb = [s for s in sl.shapes if s.name == "Eyebrow"]
        assert eb and eb[0].text_frame.text.strip()
    sl = prs.slides[0]
    for nm in ("Web app", "Mobile app", "Orders", "Billing", "Queue", "Stripe"):
        node = next(s for s in sl.shapes if s.name == f"Arch node {nm}")
        assert len(node.text_frame.paragraphs) == 2, nm  # name + mono sublabel
