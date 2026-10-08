"""Diagnostic collector shared by the parser modules."""

from __future__ import annotations

import difflib
from collections.abc import Iterable
from typing import Any

from ..ir import Diagnostic


def closest(word: str, options: Iterable[str], cutoff: float = 0.7) -> str | None:
    """The valid option nearest to ``word`` (difflib), or ``None``."""
    m = difflib.get_close_matches(word.lower(), list(options), n=1, cutoff=cutoff)
    return m[0] if m else None


def within_one(a: str, b: str) -> bool:
    """``a`` and ``b`` differ by one insertion, deletion, substitution or swap of two neighbours."""
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        d = [i for i in range(len(a)) if a[i] != b[i]]
        return len(d) == 1 or (len(d) == 2 and d[1] == d[0] + 1 and a[d[0]] == b[d[1]] and a[d[1]] == b[d[0]])
    s, t = (a, b) if len(a) < len(b) else (b, a)
    i = next((i for i in range(len(s)) if s[i] != t[i]), len(s))
    return s[i:] == t[i + 1 :]


def unique_near(word: str, options: Iterable[str]) -> str | None:
    """The one option within edit distance 1 of ``word``, or ``None`` when none or several are (a safe fix:
    ``eye`` is not ``yen``, ``refresh`` is not ``briefcase``)."""
    w = word.strip().lower()
    hits = [o for o in dict.fromkeys(options) if within_one(w, o.lower())]
    return hits[0] if len(hits) == 1 else None


class Ctx:
    """Collects diagnostics; ``slide`` is the 1-based index of the slide being parsed."""

    def __init__(self, diagnostics: list[Diagnostic]):
        self.diagnostics = diagnostics
        self.slide: int | None = None
        self.lang: str | None = None  # deck lang, set once the header is read
        self.colors: set[str] = set()  # color names the deck declares in `colors:` (chart `colors=`)
        self.box_links: list[
            tuple[Any, list[Any]]
        ] = []  # (Container, raw `@` connectors) of the current slide

    def add(self, level: str, message: str, line: int | None, rule: str, hint: str) -> None:
        self.diagnostics.append(
            Diagnostic(
                level=level,  # type: ignore[arg-type]
                message=message,
                line=line,
                slide=self.slide,
                rule=rule,
                hint=hint,
            )
        )

    def warn(self, message: str, line: int | None, rule: str, hint: str) -> None:
        self.add("warning", message, line, rule, hint)

    def error(self, message: str, line: int | None, rule: str, hint: str) -> None:
        self.add("error", message, line, rule, hint)
