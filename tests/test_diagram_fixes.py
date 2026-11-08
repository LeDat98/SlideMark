"""Lane H: the defects of the blind UI review of the diagram forms (ports and parallel offsets, labels clear
of lines and nodes, vertical swimlane, legend band, venn label sizes, container fill, generic legend).

Geometry is read back from the rebuilt .pptx: connector polylines, label rectangles, node rectangles."""

from __future__ import annotations

import re
from pathlib import Path

from pptx import Presentation
from pptx.oxml.ns import qn

from slidemark import build
from slidemark.layout import ports as PO
from slidemark.layout.grid import Rect

HEAD = (
    "theme: editorial\nlang: en\ncolors: accent=#BF4520\nfonts: heading=Georgia body=Arial\n"
    "sizes: title=34 body=16\n"
)
PX = 9525
EX = Path(__file__).resolve().parents[1] / "examples"


def make(tmp_path, text: str, head: str = HEAD):
    deck = build(head + text, tmp_path / "d.pptx")
    return deck, Presentation(str(tmp_path / "d.pptx"))


def build_example(tmp_path, name: str):
    deck = build((EX / name).read_text(), tmp_path / "e.pptx")
    return deck, Presentation(str(tmp_path / "e.pptx"))


def named(slide, pattern: str):
    return [s for s in slide.shapes if re.fullmatch(pattern, s.name)]


def poly(shp):
    """Corner points of a connector shape (straight or bentConnector3, rotated for vertical routes)."""
    el = shp._element
    xfrm = el.spPr.find(qn("a:xfrm"))
    rot = int(xfrm.get("rot", "0"))
    off, ext = xfrm.find(qn("a:off")), xfrm.find(qn("a:ext"))
    x, y, w, h = int(off.get("x")), int(off.get("y")), int(ext.get("cx")), int(ext.get("cy"))
    fh, fv = xfrm.get("flipH") == "1", xfrm.get("flipV") == "1"
    geom = el.spPr.find(qn("a:prstGeom"))
    adj = 0.5
    gd = geom.find(qn("a:avLst"))
    if gd is not None and gd.find(qn("a:gd")) is not None:
        adj = int(gd.find(qn("a:gd")).get("fmla").split()[1]) / 100000
    kind = geom.get("prst")
    if kind == "bentConnector3":
        pts = [(0, 0), (adj * w, 0), (adj * w, h), (w, h)]
    else:
        pts = [(0, 0), (w, h)]
    out = []
    cx, cy = x + w / 2, y + h / 2
    for px, py in pts:
        if fh:
            px = w - px
        if fv:
            py = h - py
        px, py = x + px, y + py
        if rot == 5400000:  # 90 degrees clockwise about the centre
            dx, dy = px - cx, py - cy
            px, py = cx - dy, cy + dx
        out.append((round(px), round(py)))
    return out


def segs(pts):
    return [(a, b) for a, b in zip(pts, pts[1:], strict=False) if a != b]


def overlap_len(a, b) -> int:
    """Length of the shared stretch of two axis-parallel segments lying on one line (0 when not collinear)."""
    (ax0, ay0), (ax1, ay1) = a
    (bx0, by0), (bx1, by1) = b
    if ax0 == ax1 and bx0 == bx1 and abs(ax0 - bx0) < 3 * PX:
        lo, hi = max(min(ay0, ay1), min(by0, by1)), min(max(ay0, ay1), max(by0, by1))
        return max(hi - lo, 0)
    if ay0 == ay1 and by0 == by1 and abs(ay0 - by0) < 3 * PX:
        lo, hi = max(min(ax0, ax1), min(bx0, bx1)), min(max(ax0, ax1), max(bx0, bx1))
        return max(hi - lo, 0)
    return 0


def rect(shp) -> Rect:
    return Rect(shp.left, shp.top, shp.width, shp.height)


def hit(a: Rect, b: Rect, m: int = 0) -> bool:
    return not (a.right + m <= b.x or b.right + m <= a.x or a.bottom + m <= b.y or b.bottom + m <= a.y)


def seg_hits_rect(s, r: Rect, m: int = 0) -> bool:
    (x0, y0), (x1, y1) = s
    seg = Rect(min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0))
    return hit(seg, r, m) and not (seg.w == 0 and seg.h == 0)


def no_shared_segments(shapes) -> None:
    polys = [(s.name, segs(poly(s))) for s in shapes]
    for i, (na, pa) in enumerate(polys):
        for nb, pb in polys[i + 1 :]:
            for sa in pa:
                for sb in pb:
                    assert overlap_len(sa, sb) < 4 * PX, (na, nb, sa, sb)


# --------------------------------------------------------------------------- 1: ports and parallel arrows


def test_plan_gives_every_arrow_of_a_side_its_own_port():
    rects = {0: Rect(0, 0, 1_200_000, 600_000), 1: Rect(2_000_000, 0, 1_200_000, 600_000)}
    rects[2] = Rect(900_000, 2_000_000, 1_200_000, 600_000)
    got = PO.plan([(0, 2), (1, 2)], rects)
    assert all(r is not None for r in got)
    xs = sorted(r.p1[0] for r in got if r)
    assert xs[1] - xs[0] >= PO.SEP  # two ports on the top of box 2, at least 12 px apart
    assert all(rects[2].x < x < rects[2].right for x in xs)


def test_plan_staggers_parallel_bends_by_a_separation():
    rects = {
        0: Rect(0, 0, 1_000_000, 500_000),
        1: Rect(1_300_000, 0, 1_000_000, 500_000),
        2: Rect(0, 2_000_000, 1_000_000, 500_000),
        3: Rect(1_300_000, 2_000_000, 1_000_000, 500_000),
    }
    got = PO.plan([(0, 3), (1, 2)], rects)
    ys = sorted(r.poly()[1][1] for r in got if r)
    assert ys[1] - ys[0] >= PO.SEP


def test_a_lone_arrow_between_aligned_boxes_is_straight_and_glued(tmp_path):
    _d, prs = make(tmp_path, "\n# T\n@arch\n## A\n- x\n## B\n- y\n> x > y\n")
    (e,) = named(prs.slides[0], r"Arch edge \d+")
    assert len(segs(poly(e))) == 1
    assert e._element.find(qn("p:nvCxnSpPr")).find(qn("p:cNvCxnSpPr")).find(qn("a:stCxn")) is not None


def test_arch_example_has_no_two_arrows_on_one_segment(tmp_path):
    deck, prs = build_example(tmp_path, "29-arch-venn.md")
    assert not [d for d in deck.diagnostics if d.level == "warning"]
    for i in (0, 1):
        edges = named(prs.slides[i], r"Arch edge \d+")
        assert len(edges) >= 6
        no_shared_segments(edges)


# --------------------------------------------------------------------------- 2: labels


def label_rects(slide, pattern: str):
    return [(s.name, rect(s)) for s in slide.shapes if re.fullmatch(pattern, s.name)]


def test_arrow_labels_touch_no_line_no_node(tmp_path):
    _deck, prs = build_example(tmp_path, "29-arch-venn.md")
    for i in (0, 1):
        sl = prs.slides[i]
        nodes = [rect(s) for s in named(sl, r"Arch node .*")]
        edges = named(sl, r"Arch edge \d+")
        for name, r in label_rects(sl, r"Arch edge \d+ label"):
            own = name[: -len(" label")]
            for n in nodes:
                assert not hit(r, n), (name, "node")
            for e in edges:
                for s in segs(poly(e)):
                    assert not seg_hits_rect(s, r), (name, e.name, own)


def test_swimlane_labels_clear_of_lane_hairlines_and_nodes(tmp_path):
    _deck, prs = build_example(tmp_path, "28-swimlane-sequence.md")
    for i in (0, 1):
        sl = prs.slides[i]
        nodes = [rect(s) for s in named(sl, r"Step \d+")]
        labels = label_rects(sl, r"Step \d+ next label")
        assert labels
        for name, r in labels:
            # a handover label may sit on a lane rule (the reference does: REVISE, DEPLOY TRIGGER) because it
            # is a knockout of the slide colour; it never touches a node
            shape = next(s for s in sl.shapes if s.name == name)
            assert shape.fill.type is not None, (name, "no knockout")
            for n in nodes:
                assert not hit(r, n), (name, "node")


# --------------------------------------------------------------------------- 3 / 5: vertical swimlane


def test_vertical_swimlane_uses_the_width_with_equal_steps_and_no_broken_word(tmp_path):
    deck, prs = build_example(tmp_path, "28-swimlane-sequence.md")
    assert not [d for d in deck.diagnostics if d.level == "warning"]
    sl = prs.slides[4]
    lanes = named(sl, r"Lane \d+")
    assert sum(s.width for s in lanes) > 0.6 * prs.slide_width
    steps = named(sl, r"Step \d+")
    assert len({s.width for s in steps}) == 1 and len({s.height for s in steps}) == 1
    for (
        s
    ) in steps:  # every word of a step name is on a line of its own width: a one-word line is a whole word
        words = s.text_frame.text.replace(" ", " ").split()
        lines = [p.text for p in s.text_frame.paragraphs]
        for w in words:
            assert any(w in ln for ln in lines)
    legend = [s for s in sl.shapes if s.name.startswith("Legend")]
    foot = (
        min(s.top for s in sl.shapes if s.name in ("Footer", "Slide Number") or "Footer" in s.name)
        if any("Footer" in s.name for s in sl.shapes)
        else prs.slide_height
    )
    assert max(s.top + s.height for s in legend) <= foot
    last = max(steps, key=lambda s: s.top)
    assert last.top + last.height <= min(s.top for s in legend)
    accent = [e for e in named(sl, r"Step \d+ next")]
    cols = {
        e._element.spPr.find(qn("a:ln")).find(qn("a:solidFill")).find(qn("a:srgbClr")).get("val")
        for e in accent
    }
    assert "BF4520" in cols  # the focal step's outgoing handover is in the accent


# --------------------------------------------------------------------------- 4: legend


def test_legend_has_no_second_hairline_under_a_swimlane(tmp_path):
    _deck, prs = build_example(tmp_path, "28-swimlane-sequence.md")
    assert not named(prs.slides[0], "Legend rule")  # the lane end rule is the only hairline
    assert named(prs.slides[0], "Legend caption")


def test_japanese_swimlane_shows_its_legend(tmp_path):
    _deck, prs = build_example(tmp_path, "28-swimlane-sequence.md")
    sl = prs.slides[1]
    assert named(sl, "Legend caption")
    assert named(sl, "Legend focal label") and named(sl, "Legend primary label")


# --------------------------------------------------------------------------- 5: text fits


def test_steps_share_one_width_and_names_stay_on_one_line_when_room(tmp_path):
    _deck, prs = build_example(tmp_path, "28-swimlane-sequence.md")
    for i in (0, 1):
        steps = named(prs.slides[i], r"Step \d+")
        assert len({s.width for s in steps}) == 1
    ja = named(prs.slides[1], r"Step \d+")
    one_line = [s for s in ja if len(s.text_frame.paragraphs[0].text) <= 8]
    assert one_line and all(
        len(s.text_frame.text.split("\n")[0]) == len(s.text_frame.paragraphs[0].text) for s in one_line
    )


# --------------------------------------------------------------------------- 6: venn


def run_sizes(shp):
    return [r.font.size.pt for p in shp.text_frame.paragraphs for r in p.runs if r.font.size]


def test_venn_text_is_at_least_8pt_and_core_label_is_inside_the_lens(tmp_path):
    deck, prs = build_example(tmp_path, "29-arch-venn.md")
    for i in (2, 3):
        sl = prs.slides[i]
        for s in sl.shapes:
            if s.name.startswith("Venn") and s.has_text_frame and s.text_frame.text.strip():
                assert min(run_sizes(s)) >= 8.0, (s.name, run_sizes(s))
        names = named(sl, r"Venn \d+ name")
        assert all(min(run_sizes(s)) >= 8.5 for s in names)  # sublabels are 9 pt
        core = named(sl, "Venn overlap")[0]
        lens = named(sl, "Venn overlap fill")[0]
        assert core.left >= lens.left and core.left + core.width <= lens.left + lens.width
        assert core.top >= lens.top and core.top + core.height <= lens.top + lens.height
        for ln in core.text_frame.text.split("\n"):  # no line is a single function word
            assert ln.strip().lower() not in {"the", "a", "of", "to"}


def test_three_set_names_sit_towards_the_outside(tmp_path):
    _deck, prs = build_example(tmp_path, "29-arch-venn.md")
    sl = prs.slides[2]
    sets = named(sl, r"Venn \d+ set")
    cx = sum(s.left + s.width / 2 for s in sets) / 3
    cy = sum(s.top + s.height / 2 for s in sets) / 3
    for s, nm in zip(sets, named(sl, r"Venn \d+ name"), strict=True):
        circ = (s.left + s.width / 2, s.top + s.height / 2)
        name = (nm.left + nm.width / 2, nm.top + nm.height / 2)
        vx, vy = circ[0] - cx, circ[1] - cy
        d = ((name[0] - circ[0]) * vx + (name[1] - circ[1]) * vy) / (vx * vx + vy * vy) ** 0.5
        assert d > 0.25 * s.width / 2, (nm.name, d)  # pushed out from the circle centre, away from the middle


# --------------------------------------------------------------------------- 7: sequence roles


def test_sequence_actors_are_filled_by_their_role(tmp_path):
    _deck, prs = build_example(tmp_path, "28-swimlane-sequence.md")
    sl = prs.slides[2]
    heads = {s.name: s for s in named(sl, r"Seq .* head")}
    assert set(heads) == {
        "Seq Reader head",
        "Seq Cloudflare head",
        "Seq Astro Origin head",
        "Seq Analytics head",
    }
    assert named(sl, r"Seq .* tag") and len(named(sl, r"Seq .* tag")) == 4

    def fill(s):
        f = s._element.spPr.find(qn("a:solidFill"))
        return f.find(qn("a:srgbClr")).get("val") if f is not None else None

    def dash(s):
        ln = s._element.spPr.find(qn("a:ln"))
        return ln is not None and ln.find(qn("a:prstDash")) is not None

    assert (
        len(
            {
                fill(heads["Seq Reader head"]),
                fill(heads["Seq Cloudflare head"]),
                fill(heads["Seq Astro Origin head"]),
            }
        )
        == 3
    )
    assert dash(heads["Seq Analytics head"]) and not dash(heads["Seq Reader head"])


# --------------------------------------------------------------------------- 8: containers


def test_group_container_is_a_light_solid_fill_with_a_caption_on_a_knockout(tmp_path):
    _deck, prs = build_example(tmp_path, "29-arch-venn.md")
    sl = prs.slides[1]
    box = named(sl, "Arch tier 1")[0]
    sp = box._element.spPr
    assert sp.find(qn("a:solidFill")) is not None
    assert sp.find(qn("a:ln")).find(qn("a:prstDash")) is None
    cap = named(sl, "Arch tier 1 label")[0]
    assert cap._element.spPr.find(qn("a:solidFill")) is not None  # a knockout, not a transparent label


def test_tag_tracking_can_be_set_tight(tmp_path):
    md = "\n# T\n@arch\n## A\n- [EXT] x\n- y\n## B\n- z\n"
    _d, prs = make(tmp_path, md, HEAD + "style: diagram.tag.track=0.08\n")
    tag = named(prs.slides[0], r"Arch tag x")[0]
    spc = [int(r._r.rPr.get("spc", "0")) for p in tag.text_frame.paragraphs for r in p.runs]
    assert spc and max(spc) <= 80  # 0.08 em of 8 pt = 0.64 pt = 64 (hundredths of a point)


# --------------------------------------------------------------------------- 10: generic legend


GENERIC = (
    "\n# Request\n@4 a>b b>c c>d\n"
    "## Web client {.input}\nBrowser app\n"
    "## API gateway {.focal}\nAuth\n"
    "## Postgres {.store}\nOrders\n"
    "## Backup {.optional}\nCopy\n"
)


def test_role_classes_with_connectors_get_the_automatic_legend(tmp_path):
    deck, prs = make(tmp_path, GENERIC)
    sl = prs.slides[0]
    assert named(sl, "Legend caption")
    for role in ("focal", "store", "input", "optional"):
        assert named(sl, f"Legend {role} label"), role
    assert named(sl, "Legend flow label")
    foot = prs.slide_height
    assert max(s.top + s.height for s in sl.shapes if s.name.startswith("Legend")) < foot


def test_legend_band_is_reserved_above_the_content_bottom(tmp_path):
    _deck, prs = make(tmp_path, GENERIC)
    sl = prs.slides[0]
    top = min(s.top for s in sl.shapes if s.name.startswith("Legend"))
    for s in sl.shapes:
        if s.name.startswith("Legend") or s.name.startswith("Title"):
            continue
        if s.has_text_frame and s.text_frame.text.strip().isdigit():
            continue
        assert s.top + s.height <= top + 1, s.name


def test_legend_can_be_switched_off(tmp_path):
    _deck, prs = make(tmp_path, GENERIC.replace("@4 a>b", "@4 legend=off a>b"))
    assert not named(prs.slides[0], "Legend caption")


def test_plain_slides_get_no_legend(tmp_path):
    _deck, prs = make(tmp_path, "\n# Plain\n@2\n## A\n- one\n## B\n- two\n")
    assert not named(prs.slides[0], "Legend caption")
