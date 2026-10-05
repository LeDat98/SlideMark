"""End-to-end pipeline: text -> Deck -> layout -> .pptx."""

from __future__ import annotations

from pathlib import Path

from .ir import Deck
from .layout import layout_slide
from .lint import lint
from .parser import parse
from .template import resolve_theme, template_size


def build(source: str | Path, out: str | Path, *, base_dir: str | Path | None = None) -> Deck:
    """Build a .pptx from text or a .md/.json/.html path. Returns the Deck (with diagnostics)."""
    exts = (".md", ".json", ".html")
    is_path = isinstance(source, Path) or ("\n" not in source and str(source).endswith(exts))
    if is_path:
        path = Path(source)
        base_dir = base_dir or path.parent
        if path.suffix == ".json":
            from .jsonio import load_deck

            deck = load_deck(path)
            if any(d.rule == "bad-json" for d in deck.diagnostics):
                return deck
            return build_deck(deck, out, base_dir)
        text = path.read_text(encoding="utf-8")
    else:
        text = str(source)
    return build_deck(parse(text), out, base_dir)


def build_deck(deck: Deck, out: str | Path, base_dir: str | Path | None = None) -> Deck:
    """Layout + lint + render a parsed Deck. Lint findings already reported by layout are deduped."""
    deck.attrs.setdefault("base_dir", str(base_dir or Path.cwd()))
    theme, diags = resolve_theme(deck.theme, deck.attrs["base_dir"])
    deck.diagnostics.extend(diags)
    if size := template_size(theme):
        deck.size = size  # the template's slide size wins
    placed = [layout_slide(slide, deck, theme, i) for i, slide in enumerate(deck.slides)]
    seen = {(d.rule, d.slide) for d in deck.diagnostics}
    deck.diagnostics.extend(d for d in lint(deck, placed, theme) if (d.rule, d.slide) not in seen)
    from .render import render  # python-pptx loads only when a file is written

    render(deck, placed, theme, out)
    return deck
