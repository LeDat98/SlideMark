"""``##`` box cards at an exact height and anchor (DL3d part 2): ``box.h`` and ``box.anchor``.

The layout sizes a row of box cards by their content (and the growth passes stretch them) and centres the row
in the body. A deck that states ``box.h=4.2in`` wants every box card that tall, and ``box.anchor=top`` the
row at the top of the body (a foreign deck draws tall cards from the top edge, with the text under the header
band). Like ``stepspin`` this pass runs last (after ``_restore_pins``), so no earlier pass can change what the
token says; a card with its own ``{h=}`` / ``{y=}`` pin is left alone.

* ``box.h``       every box card of the slide is that tall; the rows keep their gaps;
* ``box.anchor``  ``top`` / ``center`` / ``bottom``: the block (the cards and the items stacked around them)
  sits at that edge of the body; without it the block keeps its top edge (it is moved up only to stay in the
  body);
* the children of a card keep their distance to the card top (heading, band, badge, icon), the last text grows
  or shrinks with the card (its distance to the card bottom is kept), and the items under the cards (a note)
  follow the last row.
"""

from __future__ import annotations

from ..forms3 import anchor_of
from ..ir import Container, Placed, Text
from ..units import to_emu
from .vfill import _contains

_NOT_BOX = frozenset({"kpi", "item", "steps", "steps-card", "chevron", "rows", "flow"})


def _len(v) -> int | None:
    try:
        return to_emu(v) if v else None
    except (ValueError, TypeError):
        return None


def wanted(theme) -> bool:
    """True when the deck states an exact box height or an anchor."""
    return bool(theme.box_h or theme.box_anchor)


def _card(p: Placed) -> bool:
    return isinstance(p.element, Container) and p.pin is None and not (set(p.element.classes) & _NOT_BOX)


def pin_boxes(out: list[Placed], theme, body) -> list[Placed]:
    """The ``##`` box cards of ``out`` at ``box.h`` and ``box.anchor``. Never raises."""
    try:
        return _pin(out, theme, body)
    except Exception:
        return out


def _rows(cards: list[Placed]) -> list[list[Placed]]:
    rows: list[list[Placed]] = []
    for c in sorted(cards, key=lambda c: (c.y, c.x)):
        for row in rows:
            if c.y < max(r.y + r.h for r in row) and c.y + c.h > min(r.y for r in row):
                row.append(c)
                break
        else:
            rows.append([c])
    return rows


def _pin(out: list[Placed], theme, body) -> list[Placed]:
    height, anchor = _len(theme.box_h), anchor_of(theme.box_anchor)
    if not (height or anchor):
        return out
    cards = [p for p in out if _card(p)]
    # top-level cards only (a card inside a card is a sub-box the parent places)
    cards = [c for c in cards if not any(o is not c and _contains(o, c) for o in cards)]
    if not cards:
        return out
    rows = _rows(cards)
    old_top = min(c.y for c in cards)
    old_bottom = max(c.y + c.h for c in cards)
    hs = [height or max(c.h for c in row) for row in rows]
    gaps = [
        max(min(c.y for c in b) - max(c.y + c.h for c in a), 0) for a, b in zip(rows, rows[1:], strict=False)
    ]
    block = sum(hs) + sum(gaps)
    in_row = {id(c) for c in cards}
    top_items = [p for p in out if id(p) not in in_row and p.y + p.h <= old_top + 2 and _in_body(p, body)]
    new_top = _top(old_top, block, anchor, body, top_items)
    ys: list[int] = []
    y = new_top
    for h, g in zip(hs, [*gaps, 0], strict=True):
        ys.append(y)
        y += h + g
    new_bottom = new_top + block
    res: dict[int, Placed] = {}
    for row, rh, ry in zip(rows, hs, ys, strict=True):
        for c in row:
            new = c.model_copy(update={"y": ry, "h": rh})
            res[id(c)] = new
            kids = [k for k in out if id(k) not in in_row and _contains(c, k)]
            dy, dh = ry - c.y, rh - c.h
            texts = sorted((k for k in kids if isinstance(k.element, Text)), key=lambda k: k.y + k.h)
            last = texts[-1] if texts and (len(texts) > 1 or texts[0].element.role != "heading") else None
            for k in kids:
                upd = {"y": k.y + dy}
                if k is last and dh:
                    upd["h"] = max(k.h + dh, 1)
                res[id(k)] = k.model_copy(update=upd)
    below = new_bottom - old_bottom
    for p in out:
        if id(p) in res or id(p) in in_row or not _in_body(p, body):
            continue
        if p.y >= old_bottom - 2:
            res[id(p)] = p.model_copy(update={"y": p.y + below})
        elif p.y + p.h <= old_top + 2:
            res[id(p)] = p.model_copy(update={"y": p.y + (new_top - old_top)})
    return [res.get(id(p), p) for p in out]


def _in_body(p: Placed, body) -> bool:
    """A body item: its box lies inside the body (the title, footer and bars are outside)."""
    return body is None or (p.y >= body.y - 2 and p.y + p.h <= body.bottom + 2)


def _top(old_top: int, block: int, anchor: str | None, body, top_items: list[Placed]) -> int:
    if body is None:
        return old_top
    lead = max(old_top - min((p.y for p in top_items), default=old_top), 0)  # items stacked above the cards
    area_top, area_bottom = body.y, body.bottom
    if anchor == "top":
        return area_top + lead
    if anchor == "center":
        return area_top + max((area_bottom - area_top - block - lead) // 2, 0) + lead
    if anchor == "bottom":
        return max(area_bottom - block, area_top + lead)
    return (
        max(min(old_top, area_bottom - block), area_top + lead) if old_top + block > area_bottom else old_top
    )
