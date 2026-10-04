"""Diagnostic collector shared by the parser modules."""

from __future__ import annotations

from ..ir import Diagnostic


class Ctx:
    """Collects diagnostics; ``slide`` is the 1-based index of the slide being parsed."""

    def __init__(self, diagnostics: list[Diagnostic]):
        self.diagnostics = diagnostics
        self.slide: int | None = None

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
