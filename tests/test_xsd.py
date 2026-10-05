"""Schema validation of generated decks (ECMA-376 XSDs, downloaded once; skipped offline)."""

from __future__ import annotations

from pathlib import Path

import pytest

from slidemark.build import build_deck
from slidemark.parser import parse
from slidemark.xsd import _load_schema, validate_pptx

ROOT = Path(__file__).resolve().parent.parent

needs_schemas = pytest.mark.skipif(_load_schema() is None, reason="ECMA-376 schemas not available")


def test_long_title_does_not_crash(tmp_path):
    out = tmp_path / "t.pptx"
    build_deck(parse("# " + "x" * 400 + "\n- a\n- b\n"), out)
    assert out.exists()


@needs_schemas
@pytest.mark.parametrize("name", ["04-jp-kpi", "05-jp-process", "07-jp-org", "08-jp-roadmap"])
def test_example_is_schema_valid(tmp_path, name):
    out = tmp_path / f"{name}.pptx"
    deck = parse((ROOT / "examples" / f"{name}.md").read_text(encoding="utf-8"))
    build_deck(deck, out, base_dir=ROOT / "examples")
    assert validate_pptx(out) == []
