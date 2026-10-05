"""End-to-end pipeline: text -> Deck -> layout -> .pptx."""

from __future__ import annotations

from pathlib import Path

from .ir import Deck
from .layout import layout_slide
from .lint import lint
from .parser import parse
from .render import render
from .theme import get_theme


def build(source: str | Path, out: str | Path, *, base_dir: str | Path | None = None) -> Deck:
    """Build a .pptx from Markdown text or a path to a .md file. Returns the Deck (with diagnostics)."""
    is_path = isinstance(source, Path) or ("\n" not in source and source.endswith(".md"))
    if is_path:
        path = Path(source)
        text = path.read_text(encoding="utf-8")
        base_dir = base_dir or path.parent
    else:
        text = str(source)
    deck = parse(text)
    deck.attrs.setdefault("base_dir", str(base_dir or Path.cwd()))
    theme = get_theme(deck.theme)
    placed = [layout_slide(slide, deck, theme, i) for i, slide in enumerate(deck.slides)]
    seen = {(d.rule, d.slide) for d in deck.diagnostics}
    deck.diagnostics.extend(d for d in lint(deck, placed, theme) if (d.rule, d.slide) not in seen)
    render(deck, placed, theme, out)
    return deck
