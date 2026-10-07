"""Card shadows of a foreign deck (DL3d part 2): ``card.shadow=`` deck-wide, else ``{shadow=}`` per box.

``read.py`` reads the outer shadow of every shape (``Item.shadow``, ``"x y blur #RRGGBB[AA]"`` in pt). A deck
whose cards mostly share one shadow states it once as the ``card`` class token; the boxes that differ keep a
``{shadow=}`` of their own (``off`` for a card without any), see ``structure._control_attrs``.
"""

from __future__ import annotations

from collections import Counter

from .read import Item, SlideData

MIN_AREA = 0.004  # a card covers at least this share of the slide (badges and rules are smaller)
MAX_AREA = 0.62  # ... and at most this share (a backdrop is not a card)
MAX_W = 0.97  # ... and is narrower than the slide (a band is chrome)
SHARE = 0.5  # the deck-wide shadow is on at least this share of the cards


def is_card(it: Item, W: int, H: int) -> bool:
    """A filled rectangle or rounded rectangle of card size, not a placeholder."""
    return (
        it.kind in ("shape", "text")
        and not it.ph
        and bool(it.fill)
        and it.prst in (None, "rect", "roundRect")
        and MIN_AREA <= it.area / max(W * H, 1) <= MAX_AREA
        and it.w <= MAX_W * W
    )


def card_shadow(datas: list[SlideData], W: int, H: int) -> str | None:
    """The shadow most cards of the deck share (>= 2 cards and at least ``SHARE`` of all), else ``None``."""
    seen: Counter[str | None] = Counter()
    for sd in datas:
        for it in sd.items:
            if is_card(it, W, H):
                seen[it.shadow] += 1
    total = sum(seen.values())
    shadows = Counter({k: n for k, n in seen.items() if k})
    if not shadows or total == 0:
        return None
    best, n = shadows.most_common(1)[0]
    return best if n >= 2 and n >= SHARE * total else None
