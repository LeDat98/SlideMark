"""Example 30 (html kit diagrams): builds with 0 warnings, native shapes only, one eyebrow per slide."""

from __future__ import annotations

from pathlib import Path

import pytest
from pptx import Presentation

from slidemark.build import build
from slidemark.render.htmlimg import HtmlRenderer
from slidemark.theme import get_theme


@pytest.fixture(scope="module")
def chromium():
    """Skip when Chromium is missing. The probe browser is closed: only one sync Playwright per process."""
    pytest.importorskip("playwright.sync_api")
    r = HtmlRenderer()
    try:
        ok = r.render("<p>x</p>", 40, 20, get_theme("editorial")) is not None
    finally:
        r.close()
    if not ok:
        pytest.skip("Chromium cannot be launched")


def test_example_30_builds_clean_native(tmp_path, chromium):
    src = Path(__file__).resolve().parent.parent / "examples" / "30-html-diagrams.md"
    deck = build(src, tmp_path / "e.pptx")
    bad = [d for d in deck.diagnostics if d.level == "warning" or d.rule == "html-element-image"]
    assert not bad, [str(d) for d in bad]
    prs = Presentation(tmp_path / "e.pptx")
    assert sum(1 for s in prs.slides for sh in s.shapes if sh.shape_type == 13) == 0  # no pictures
    eyebrows = [sh.text_frame.text for s in prs.slides for sh in s.shapes if sh.name == "Eyebrow"]
    assert len(eyebrows) == 5 and all(e == e.upper() for e in eyebrows)
