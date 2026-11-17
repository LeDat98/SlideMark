"""`dead-space` warning: one block floating in a large body (the rubric G-05 soft gate, same measure)."""

from __future__ import annotations

from slidemark import build
from slidemark.fit import _bands

TABLE = "| Service | Cost |\n|---|---|\n| Gateway | $4,200 |\n| Search | $2,900 |\n"
CARDS = "## A\n- one\n## B\n- two\n## C\n- three\n"


def _dead(src: str, tmp_path) -> list:
    deck = build(src, tmp_path / "d.pptx")
    return [d for d in deck.diagnostics if d.rule == "dead-space"]


def test_a_lone_small_table_in_the_editorial_body_warns_with_a_content_hint(tmp_path):
    got = _dead("theme: editorial\n\n# Gateway cost grew fastest\n@1\n" + TABLE, tmp_path)
    assert len(got) == 1 and got[0].level == "warning" and "empty bands" in got[0].message
    assert "second block" in got[0].hint and "bigger sizes do not fix it" in got[0].hint


def test_a_second_block_from_the_same_content_clears_it(tmp_path):
    chart = '```bar {title="Cost ($k)"}\n,Gateway,Search\nCost,4.2,2.9\n```\n> Gateway is the largest line\n'
    assert not _dead("theme: editorial\n\n# Gateway cost grew fastest\n@3:2\n" + TABLE + chart, tmp_path)


def test_cards_with_a_table_under_them_are_not_dead_space(tmp_path):
    cards = "".join(
        f"## {h}\n- first point of {h}\n- second point of {h}\n- third point of {h}\n" for h in "ABC"
    )
    rows = "".join(f"| Line {i} | {h} | $1,{i}00 |\n" for i, h in enumerate("ABCD"))
    src = (
        "theme: editorial\n\n# Plan\n> lead\n@3\n"
        + cards
        + "@end\n| Line | Card | Cost |\n|---|---|---|\n"
        + rows
    )
    assert not _dead(src, tmp_path)
    assert _dead("theme: editorial\n\n# Plan\n> lead\n@3\n" + CARDS, tmp_path)  # the cards alone float


def test_covers_statements_and_the_token_are_exempt(tmp_path):
    assert not _dead("theme: editorial\n\n# Cover\n## sub\n@cover\n", tmp_path)
    assert not _dead("theme: editorial\n\n# Margin\n\n[+6pt]{size=96}\n\nfrom 12% to 18%\n", tmp_path)
    off = "theme: editorial\nstyle: layout.dead_space=0\n\n# Gateway\n@1\n" + TABLE
    assert not _dead(off, tmp_path)


def test_only_wide_bands_count():
    assert _bands([(0, 40), (45, 100)], 0, 100, 0.1) == 0  # a 5% gutter is not dead space
    assert abs(_bands([(30, 60)], 0, 100, 0.1) - 0.7) < 1e-9  # 30% above + 40% below
