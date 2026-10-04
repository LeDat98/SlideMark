"""Shared test helpers."""

from __future__ import annotations

import shutil

import pytest

needs_soffice = pytest.mark.skipif(shutil.which("soffice") is None, reason="LibreOffice not installed")
