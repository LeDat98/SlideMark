"""Slide -> list[Placed] with absolute EMU boxes. Owner: layout workstream."""

from __future__ import annotations

from ..ir import Deck, Placed, Slide
from ..theme import Theme


def layout_slide(slide: Slide, deck: Deck, theme: Theme, index: int) -> list[Placed]:
    """Return every visible item of ``slide`` (title included) in z-order, with final boxes and merged styles.

    ``index`` is the 0-based slide index (used for footer / slide number items).
    Problems (overflow, unknown layout, ...) are appended to ``deck.diagnostics``.
    """
    raise NotImplementedError
