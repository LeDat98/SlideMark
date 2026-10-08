"""SlideMark: token-efficient Markdown -> native, editable PowerPoint for AI agents."""

from .build import build
from .ir import Deck, Slide
from .parser import parse

__all__ = ["Deck", "Slide", "build", "parse"]
__version__ = "0.1.1"
