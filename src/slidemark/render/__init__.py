"""IR + Placed -> .pptx. Owner: renderer workstream."""

from __future__ import annotations

from pathlib import Path

from ..ir import Deck, Placed
from ..theme import Theme


def render(deck: Deck, placed: list[list[Placed]], theme: Theme, out: str | Path) -> Path:
    """Write ``deck`` to ``out``. ``placed[i]`` is the layout result for ``deck.slides[i]``."""
    raise NotImplementedError
