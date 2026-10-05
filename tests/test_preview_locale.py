"""Previews of a decimal-comma deck render chart numbers in the deck's locale (3,6 like PowerPoint in vi)."""

from __future__ import annotations

import pytest

from slidemark import build
from slidemark.preview import _deck_locale, have_soffice


def _deck(tmp_path, lang: str):
    src = tmp_path / f"{lang}.md"
    src.write_text(
        f'lang: {lang}\n\n# T\n```column {{labels=on}}\n,a,b\nX,"3,6","3,9"\n```\n', encoding="utf-8"
    )
    build(src, tmp_path / f"{lang}.pptx")
    return tmp_path / f"{lang}.pptx"


def test_locale_only_for_decimal_comma_decks(tmp_path):
    assert _deck_locale(_deck(tmp_path, "vi")).startswith("vi")
    assert _deck_locale(_deck(tmp_path, "ja")) is None
    assert _deck_locale(tmp_path / "missing.pptx") is None


@pytest.mark.skipif(not have_soffice(), reason="LibreOffice missing")
def test_preview_pdf_uses_decimal_comma(tmp_path):
    pdfium = pytest.importorskip("pypdfium2")
    from slidemark.preview import pptx_to_pdf

    pdf = pptx_to_pdf(_deck(tmp_path, "vi"), tmp_path / "out")
    text = pdfium.PdfDocument(str(pdf))[0].get_textpage().get_text_range()
    assert "3,6" in text and "3.6" not in text
