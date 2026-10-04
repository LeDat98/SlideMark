"""Markdown+ -> IR. Owner: parser workstream. See docs/SYNTAX.md for the syntax."""

from __future__ import annotations

from ..ir import Deck, Diagnostic
from .core import parse_deck


def parse(text: str) -> Deck:
    """Parse SlideMark Markdown into a Deck. Never raises: problems go to ``deck.diagnostics``."""
    try:
        return parse_deck(text)
    except Exception as e:  # last-resort guard: bad input must never crash the caller
        deck = Deck()
        deck.diagnostics.append(
            Diagnostic(
                level="error",
                message=f"internal error: {type(e).__name__}: {e}",
                rule="internal",
                hint="simplify the input or report it as a parser bug",
            )
        )
        return deck


__all__ = ["parse"]
