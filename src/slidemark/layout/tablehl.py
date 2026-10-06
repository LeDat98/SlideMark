"""Emphasised table rows (``hl=`` on a table): which body rows a list of first-cell values selects.

Parser (validation), layout (bold measuring), CSS (``tr.hl``), renderer, lint and importer share these.
"""

from __future__ import annotations

import csv
import io
import re
import unicodedata

from ..ir import Table


def norm_key(text: str) -> str:
    """Comparable form of a first-cell value: NFKC, no joiners, one space between words, case-folded."""
    s = unicodedata.normalize("NFKC", text.replace("⁠", ""))
    return " ".join(s.split()).casefold()


def split_names(value: str) -> list[str]:
    """``a, b`` -> ``[a, b]``; a quoted name may hold commas (``"Metro, East",Other``). Never raises."""
    raw = value.strip()
    if not raw:
        return []
    try:
        row = next(csv.reader(io.StringIO(raw), skipinitialspace=True), [])
    except csv.Error:
        row = re.split(r"[,;]", raw)
    return [c.strip() for c in row if c.strip()]


def join_names(names: list[str]) -> str:
    """Inverse of ``split_names`` (CSV quoting for names holding a comma or a quote)."""
    return ",".join('"' + n.replace('"', '""') + '"' if any(ch in n for ch in ',"') else n for n in names)


def first_cells(t: Table) -> list[tuple[int, str]]:
    """``(row, text)`` of the first cell of every body row; rows covered by a row span share its text."""
    from .tables import table_grid  # lazy: tables imports css, which imports this module

    nrows, _ncols, anchors = table_grid(t)
    out: dict[int, str] = {}
    for r, c, cell in anchors:
        if c == 0 and r >= t.header_rows:
            text = "".join(p.plain for p in cell.paragraphs).strip()
            for rr in range(r, min(r + max(cell.rowspan, 1), nrows)):
                out[rr] = text
    return sorted(out.items())


def hl_names(t: Table) -> list[str]:
    """The first-cell values ``t.attrs['hl']`` names (a list from the parser, or the raw option text)."""
    raw = t.attrs.get("hl")
    if not raw:
        return []
    return [str(n) for n in raw] if isinstance(raw, (list, tuple)) else split_names(str(raw))


def hl_rows(t: Table) -> frozenset[int]:
    """Indexes of the body rows that ``t.attrs['hl']`` (first-cell values) emphasises."""
    names = hl_names(t)
    if not names or not t.rows:
        return frozenset()
    keys = {norm_key(n) for n in names}
    return frozenset(r for r, text in first_cells(t) if text and norm_key(text) in keys)
