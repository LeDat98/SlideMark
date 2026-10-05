"""Skill docs: token budgets, and every SlideMark example in them parses without warnings."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from slidemark.parser import parse

tiktoken = pytest.importorskip("tiktoken")
SKILL = Path(__file__).resolve().parent.parent / "src" / "slidemark" / "skill"
FENCE = re.compile(r"^(`{3,})markdown\n(.*?)^\1\s*$", re.S | re.M)


def _tokens(text: str) -> int:
    return len(tiktoken.get_encoding("o200k_base").encode(text))


def test_budgets():
    # SKILL.md is the only document an agent reads (docs/AGENT_COST.md): budget for completeness, not brevity
    assert _tokens((SKILL / "SKILL.md").read_text(encoding="utf-8")) <= 3000
    refs = sorted((SKILL / "reference").glob("*.md"))
    assert len(refs) >= 5
    for p in refs:
        assert _tokens(p.read_text(encoding="utf-8")) <= 800, p.name


def test_examples_parse_clean():
    files = [SKILL / "SKILL.md", *sorted((SKILL / "reference").glob("*.md"))]
    count = 0
    for p in files:
        for m in FENCE.finditer(p.read_text(encoding="utf-8")):
            body = m.group(2)
            if not body.lstrip().startswith(("#", "theme:", "@", "{", "|", ">")) and "```" not in body:
                continue
            src = body if body.lstrip().startswith(("#", "theme:")) else "# T\n" + body
            deck = parse(src)
            bad = [str(d) for d in deck.diagnostics if d.level != "info"]
            assert not bad, f"{p.name}: {bad}"
            count += 1
    assert count >= 6
