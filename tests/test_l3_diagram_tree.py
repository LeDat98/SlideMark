"""Org charts / issue trees (slide-level a>b links) grow down the body; connectors stay attached."""

from __future__ import annotations

from slidemark.ir import Container, Shape, Text
from slidemark.layout import layout_slide
from slidemark.parser import parse
from slidemark.theme import get_theme

TREE = """theme: jp-business
lang: ja

# 推進体制
> CEO 直轄の推進委員会のもと、分科会で推進する
@a>b b>c b>d b>e
## DX推進委員会
委員長：代表取締役社長　月1回開催
## PMO（DX推進室）
進捗・予算・リスクの一元管理
## WMS分科会
物流本部　8名
## 配車分科会
DX推進室　6名
## 需要予測分科会
商品本部　5名
※ 各分科会は隔週でPMOへ報告
"""


def lay(md: str, off: bool = False):
    deck = parse(md)
    th = get_theme(deck.theme).model_copy(deep=True)
    if off:
        th.layout.tree_fill = 0
    return deck, th, layout_slide(deck.slides[0], deck, th, 0)


def boxes(placed):
    return [p for p in placed if isinstance(p.element, Container)]


def lines(placed):
    return [p for p in placed if isinstance(p.element, Shape) and p.element.attrs.get("src_box")]


def span(placed):
    bx = boxes(placed)
    return max(p.y + p.h for p in bx) - min(p.y for p in bx)


def head_pt(placed):
    return max(
        p.style.font_size * p.font_scale
        for p in placed
        if isinstance(p.element, Text) and p.element.role == "heading"
    )


def test_tree_height_share_grows_top_anchored():
    _, _, before = lay(TREE, off=True)
    _, _, after = lay(TREE)
    assert span(after) > span(before) * 1.12
    assert span(after) > 0.65 * 7.5 * 914400
    assert min(p.y for p in boxes(after)) <= min(p.y for p in boxes(before)) + 2


def test_tree_text_steps_up_and_root_widens():
    _, _, before = lay(TREE, off=True)
    _, _, after = lay(TREE)
    assert head_pt(after) > head_pt(before)
    assert boxes(after)[0].w > boxes(before)[0].w


def test_tree_connectors_attach_to_box_edges():
    _, _, pl = lay(TREE)
    rects = {(p.x, p.y, p.w, p.h) for p in boxes(pl)}
    ls = lines(pl)
    assert len(ls) == 4
    for ln in ls:
        a = ln.element.attrs
        s, d = tuple(a["src_box"]), tuple(a["dst_box"])
        assert s in rects and d in rects
        x0, y0 = s[0] + s[2] // 2, s[1] + s[3]  # parent bottom-middle
        x1, y1 = d[0] + d[2] // 2, d[1]  # child top-middle
        assert ln.y == y0 and ln.y + ln.h == y1
        assert {ln.x, ln.x + ln.w} == {x0, x1}
        assert a["flip_h"] == (x1 < x0)
        assert not a["flip_v"]


def test_tree_text_stays_inside_boxes():
    deck, _, pl = lay(TREE)
    for b in boxes(pl):
        for p in pl:
            if p is b or not isinstance(p.element, Text) or p.element.role not in ("heading", "body"):
                continue
            if b.x <= p.x < b.x + b.w and b.y <= p.y < b.y + b.h:
                assert p.y + p.h <= b.y + b.h + 2
                assert p.x + p.w <= b.x + b.w + 2
    assert max(p.y + p.h for p in boxes(pl)) < 7.5 * 914400 * 0.93
    assert not [d for d in deck.diagnostics if d.level == "error"]


def test_dense_tree_without_slack_unchanged():
    dense = "# T\n@a>b a>c a>d a>e a>f a>g\n" + "".join(
        f"## N{i}\n" + "".join(f"- point {i} item {k} with a long line of text here\n" for k in range(7))
        for i in range(7)
    )
    _, _, before = lay(dense, off=True)
    _, _, after = lay(dense)
    assert [(p.x, p.y, p.w, p.h) for p in before] == [(p.x, p.y, p.w, p.h) for p in after]


def test_tree_odd_inputs_do_not_crash():
    for md in (
        "# T\n@a>b b>a\n## A\nx\n## B\ny\n",
        "# T\n@a>z\n## A\nx\n",
        "# T\n@ab/c a>c b>c\n## A\nx\n## B\ny\n## C\nz\n",
        "# T\n@a>b\n## A {icon=target}\nx\n## B\ny\n",
    ):
        _, _, pl = lay(md)
        assert pl
