"""Import of a ``{header=2}`` table with ``^`` header cells: lossless, nothing explicit for defaults."""

from __future__ import annotations

from slidemark import build
from slidemark.importer import import_pptx

MD = """# Plan
{header=2}
| Item | 2027 | < | 2028 |
|-|-|-|-|
| ^ | H1 | H2 | Total |
| A | x | y | 12 [ok]{.badge .success} |
| B | z | w | 3 |
"""


def _import(tmp_path, md):
    a = tmp_path / "a.pptx"
    build(md, a)
    text, _ = import_pptx(a, tmp_path)
    return text


def test_header_rows_are_restored_and_no_align_is_invented(tmp_path):
    text = _import(tmp_path, MD)
    assert "{header=2}" in text
    assert "align=" not in text
    assert "| ^ | H1 | H2 | Total |" in text  # header cells bold by default: no `**`
    assert "{.badge .success}" in text


def test_plain_continuation_row_stays_a_body_row(tmp_path):
    md = "# T\n| Item | Q |\n|-|-|\n| ^ | one |\n| A | two |\n"
    assert "header=2" not in _import(tmp_path, md)
