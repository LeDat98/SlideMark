"""Token gate: the SlideMark source of each corpus deck must not grow more than the baseline tolerance."""

import json
from pathlib import Path

import pytest

tiktoken = pytest.importorskip("tiktoken")

BENCH = Path(__file__).resolve().parent.parent / "bench"


def test_slidemark_tokens_within_baseline():
    base = json.loads((BENCH / "BASELINE.json").read_text())
    enc = tiktoken.get_encoding("o200k_base")
    for deck, limit in base["slidemark_tokens"].items():
        text = (BENCH / "corpus" / deck / "slidemark.md").read_text(encoding="utf-8")
        n = len(enc.encode(text))
        assert n <= limit * (1 + base["tolerance"]), f"{deck}: {n} tokens > baseline {limit} (+3%)"
