"""Shared test helpers."""

from __future__ import annotations

import shutil

import pytest

needs_soffice = pytest.mark.skipif(shutil.which("soffice") is None, reason="LibreOffice not installed")


def top_anchored(theme):
    """A copy of ``theme`` without the vertical body fill (tests of growth / hugging pin that geometry)."""
    th = theme.model_copy(deep=True)
    th.layout.body_valign = "top"
    return th
