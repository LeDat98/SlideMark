"""Markdown+ -> IR. Owner: parser workstream. See docs/SYNTAX.md for the syntax."""

from __future__ import annotations

from ..ir import Deck


def parse(text: str) -> Deck:
    """Parse SlideMark Markdown into a Deck. Never raises: problems go to ``deck.diagnostics``."""
    raise NotImplementedError
