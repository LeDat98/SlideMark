"""Markdown+ -> IR. Owner: parser workstream. See docs/SYNTAX.md for the syntax."""

from __future__ import annotations

from ..ir import Deck, Diagnostic
from .core import parse_deck
from .html import parse_html


def _looks_like_html(text: str) -> bool:
    head = text.lstrip("\ufeff \t\r\n")[:20].lower()
    return head.startswith(("<!doctype html", "<html", "<section", "<style", "<head", "<body"))


def parse(text: str) -> Deck:
    """Parse SlideMark Markdown into a Deck. Never raises: problems go to ``deck.diagnostics``."""
    try:
        if _looks_like_html(text):
            return parse_html(text)
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


__all__ = ["parse", "parse_html"]
