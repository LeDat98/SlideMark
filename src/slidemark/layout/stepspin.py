"""``@steps`` exact geometry (DL3d part 2): ``steps-arrow.h`` ``steps-card.h`` ``steps.gap``.

The layout chooses the arrow height, the card height and the gap itself (aspect, sparse growth, stretch to the
conclusion bar). A deck that states one of the three tokens wants that number: this pass runs last (after the
growth and stretch passes, after ``_restore_pins``), so no earlier pass can change what the token says.

* ``steps-arrow.h``  every arrow is that tall (the point keeps its share of the height);
* ``steps-arrow.point`` every arrow's point is that share of its shorter side deep (the preset's ``adj``);
* the group starts at the body top when a height is stated and nothing sits above the arrows;
* ``steps.gap``      the cards start that far under the arrows (the token is also ``layout.steps_gap``);
* ``steps-card.h``   every card is that tall; without it the card keeps its bottom edge (a stretched card
  follows the arrows' new height).

The text of a card keeps its distances to the card edges (one text: it follows the new height).
"""

from __future__ import annotations

from ..ir import Placed, Shape, Text
from ..units import to_emu
from .vfill import _contains


def _arrow(p: Placed) -> bool:
    return isinstance(p.element, Shape) and str(p.element.attrs.get("shape_name", "")).endswith(" arrow")


def _chevron(p: Placed) -> bool:
    return isinstance(p.element, Shape) and p.element.shape == "chevron"


def pin_point(out: list[Placed], theme) -> list[Placed]:
    """Every chevron / pentagon of ``out`` with ``steps-arrow.point`` as its point depth (the share of the
    shorter side that is the preset's ``adj``): a growth pass that rescaled it is undone."""
    point = getattr(theme, "steps_arrow_point", None)
    if not point:
        return out
    return [
        p.model_copy(
            update={"element": p.element.model_copy(update={"attrs": {**p.element.attrs, "adj": point}})}
        )
        if _chevron(p)
        else p
        for p in out
    ]


def _card(p: Placed) -> bool:
    return "steps-card" in getattr(p.element, "classes", ()) and not isinstance(p.element, Shape)


def _len(v) -> int | None:
    try:
        return to_emu(v) if v else None
    except (ValueError, TypeError):
        return None


def pinned(theme) -> bool:
    """True when the deck states an exact arrow or card height."""
    return bool(theme.steps_arrow_h or theme.steps_card_h)


def pin_steps(out: list[Placed], theme, body_top: int | None = None) -> list[Placed]:
    """The ``@steps`` arrows and cards of ``out`` at the height, gap and point of the tokens (no raise)."""
    try:
        return _pin(pin_point(out, theme), theme, body_top)
    except Exception:
        return out


def _pin(out: list[Placed], theme, body_top: int | None = None) -> list[Placed]:
    arrow_h, card_h, gap = _len(theme.steps_arrow_h), _len(theme.steps_card_h), _len(theme.steps_gap)
    if not (arrow_h or card_h or gap):
        return out
    arrows = [p for p in out if _arrow(p)]
    cards = [p for p in out if _card(p)]
    if not arrows or not cards:
        return out
    top = min(a.y for a in arrows)
    if body_top is not None and pinned(theme) and min(p.y for p in out) >= top - 2:
        top = body_top  # exact heights: the group the author placed starts at the body top (no centring pass)
    old_bottom = max(a.y + a.h for a in arrows)
    old_gap = min(c.y for c in cards) - old_bottom
    new_h = arrow_h or max(a.h for a in arrows)
    new_gap = gap if gap is not None else max(old_gap, 0)
    ctop = top + new_h + new_gap
    res: dict[int, Placed] = {}
    for a in arrows:
        res[id(a)] = a.model_copy(update={"y": top, "h": new_h})
    for c in cards:
        height = card_h or max(c.y + c.h - ctop, 1)
        res[id(c)] = c.model_copy(update={"y": ctop, "h": height})
        kids = [p for p in out if p is not c and not _arrow(p) and not _card(p) and _contains(c, p)]
        dy, dh = ctop - c.y, height - c.h
        texts = [k for k in kids if isinstance(k.element, Text)]
        for k in kids:
            upd = {"y": k.y + dy}
            if len(kids) == 1 and texts:
                upd["h"] = max(k.h + dh, 1)  # one text: it keeps its margins to the card edges
            res[id(k)] = k.model_copy(update=upd)
    return [res.get(id(p), p) for p in out]


def bar_follows(out: list[Placed], tail: list[Placed], air: int) -> list[Placed]:
    """The conclusion bar of ``tail`` moves up to ``air`` under the (pinned) step cards; never down."""
    cards = [p for p in out if _card(p)]
    if not cards:
        return tail
    want = max(c.y + c.h for c in cards) + air
    return [
        p.model_copy(update={"y": want})
        if isinstance(p.element, Text) and p.element.role == "conclusion" and want < p.y
        else p
        for p in tail
    ]
